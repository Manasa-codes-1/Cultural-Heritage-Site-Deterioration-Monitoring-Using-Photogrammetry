"""
Photogrammetry Service.
Coordinates reconstruction job triggers, background pipeline execution,
workspace management, database persistence, and model file delivery.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
import logging

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings, BASE_DIR
from app.core.database import SessionLocal

from app.models.heritage import Survey, Image, Reconstruction
from app.schemas.photogrammetry import ReconstructionTriggerRequest
from app.photogrammetry import get_photogrammetry_engine, check_photogrammetry_system
from app.processing.pointcloud_processor import PointCloudProcessor

logger = logging.getLogger(__name__)


class PhotogrammetryService:
    """Manages the full lifecycle of 3D reconstruction tasks."""

    def get_system_diagnostics(self) -> Dict[str, Any]:
        """Returns COLMAP and Open3D installation status and capabilities."""
        return check_photogrammetry_system()

    def get_reconstruction_by_survey(self, survey_id: str, db: Session) -> Optional[Reconstruction]:
        """Returns the reconstruction record associated with a survey, if any."""
        return db.query(Reconstruction).filter(Reconstruction.survey_id == survey_id).first()

    def get_reconstruction_by_id(self, reconstruction_id: str, db: Session) -> Optional[Reconstruction]:
        """Returns reconstruction record by its primary key."""
        return db.query(Reconstruction).filter(Reconstruction.id == reconstruction_id).first()

    def trigger_reconstruction(
        self,
        survey_id: str,
        request: ReconstructionTriggerRequest,
        db: Session,
        background_tasks: BackgroundTasks,
    ) -> Reconstruction:
        """
        Validates survey imagery and schedules the 3D reconstruction pipeline.
        """
        survey = db.query(Survey).filter(Survey.id == survey_id).first()
        if not survey:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Survey '{survey_id}' not found.",
            )

        images = db.query(Image).filter(Image.survey_id == survey_id).all()
        if not images or len(images) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Survey '{survey_id}' has 0 images. Upload survey photos before running reconstruction.",
            )

        # Check existing reconstruction
        existing = db.query(Reconstruction).filter(Reconstruction.survey_id == survey_id).first()
        if existing:
            if existing.status in ["running", "pending"] and not request.force:
                return existing
            # If re-running or forcing, reset existing record
            reconstruction = existing
            reconstruction.engine = request.engine
            reconstruction.status = "pending"
            reconstruction.current_stage = "QUEUED"
            reconstruction.progress_percent = 0
            reconstruction.error_message = None
            reconstruction.started_at = datetime.now(timezone.utc)
            reconstruction.completed_at = None
        else:
            reconstruction = Reconstruction(
                survey_id=survey_id,
                engine=request.engine,
                status="pending",
                current_stage="QUEUED",
                progress_percent=0,
                started_at=datetime.now(timezone.utc),
            )
            db.add(reconstruction)

        db.commit()
        db.refresh(reconstruction)

        # Schedule background worker
        background_tasks.add_task(
            self._execute_reconstruction_pipeline,
            reconstruction_id=reconstruction.id,
            survey_id=survey_id,
            engine_name=request.engine,
            dense=request.dense,
            generate_mesh=request.generate_mesh,
        )

        return reconstruction

    @classmethod
    def _execute_reconstruction_pipeline(
        cls,
        reconstruction_id: str,
        survey_id: str,
        engine_name: str,
        dense: bool,
        generate_mesh: bool,
        db_session: Optional[Session] = None,
    ):
        """
        Background task worker executing the photogrammetry pipeline.
        Runs inside an isolated DB session or uses provided session.
        """
        owns_session = False
        if db_session is None:
            db = SessionLocal()
            owns_session = True
        else:
            db = db_session

        try:
            recon = db.query(Reconstruction).filter(Reconstruction.id == reconstruction_id).first()
            survey = db.query(Survey).filter(Survey.id == survey_id).first()
            if not recon or not survey:
                logger.error(f"Reconstruction {reconstruction_id} or survey {survey_id} missing during background task.")
                return

            # Update initial status
            recon.status = "running"
            recon.current_stage = "INITIALIZING"
            recon.progress_percent = 5
            recon.processing_logs = "Starting photogrammetric reconstruction pipeline...\n"
            db.commit()

            # Prepare workspace
            workspace_dir = settings.DATA_DIR / "surveys" / survey_id / "reconstruction"
            workspace_dir.mkdir(parents=True, exist_ok=True)

            images = db.query(Image).filter(Image.survey_id == survey_id).all()
            image_paths = []
            for img in images:
                full_path = settings.DATA_DIR / img.relative_path
                if not full_path.exists():
                    full_path = BASE_DIR / img.relative_path
                if full_path.exists():
                    image_paths.append(full_path)

            if len(image_paths) == 0:
                raise ValueError("None of the survey image files exist on the filesystem storage.")

            engine = get_photogrammetry_engine(engine_name)
            recon.engine = engine.name

            # Callback for granular progress updates
            def progress_cb(stage: str, percent: int, log_line: str):
                recon.current_stage = stage
                recon.progress_percent = percent
                if recon.processing_logs:
                    recon.processing_logs += f"{log_line}\n"
                else:
                    recon.processing_logs = f"{log_line}\n"
                db.commit()

            # Execute reconstruction
            result = engine.run_reconstruction(
                survey_id=survey_id,
                image_paths=image_paths,
                workspace_dir=workspace_dir,
                progress_callback=progress_cb,
                dense=dense,
                generate_mesh=generate_mesh,
            )

            # Analyze geometric results with Open3D if available
            sparse_stats = {}
            dense_stats = {}
            mesh_stats = {}

            if result.get("sparse_point_cloud_path") and Path(result["sparse_point_cloud_path"]).exists():
                try:
                    sparse_stats = PointCloudProcessor.inspect_point_cloud(Path(result["sparse_point_cloud_path"]))
                except Exception as ex:
                    logger.warning(f"Could not inspect sparse point cloud: {ex}")

            if result.get("dense_point_cloud_path") and Path(result["dense_point_cloud_path"]).exists():
                try:
                    dense_stats = PointCloudProcessor.inspect_point_cloud(Path(result["dense_point_cloud_path"]))
                except Exception as ex:
                    logger.warning(f"Could not inspect dense point cloud: {ex}")

            if result.get("mesh_path") and Path(result["mesh_path"]).exists():
                try:
                    mesh_stats = PointCloudProcessor.inspect_mesh(Path(result["mesh_path"]))
                except Exception as ex:
                    logger.warning(f"Could not inspect mesh: {ex}")

            # Populate database fields
            recon.status = "completed"
            recon.current_stage = "COMPLETED"
            recon.progress_percent = 100
            recon.completed_at = datetime.now(timezone.utc)
            recon.is_demo = result["is_demo"]
            recon.engine_version = result.get("engine_version")

            recon.sparse_point_cloud_path = result.get("sparse_point_cloud_path")
            recon.dense_point_cloud_path = result.get("dense_point_cloud_path")
            recon.mesh_path = result.get("mesh_path")
            recon.workspace_path = result.get("workspace_path")
            recon.log_path = result.get("log_path")

            recon.camera_count = len(image_paths)
            recon.registered_image_count = result.get("registered_image_count", len(image_paths))

            # Point counts
            recon.sparse_point_count = sparse_stats.get("point_count", result.get("sparse_point_count", 0))
            recon.dense_point_count = dense_stats.get("point_count", result.get("dense_point_count", 0))
            recon.point_count = recon.dense_point_count if recon.dense_point_count > 0 else recon.sparse_point_count

            # Mesh stats
            recon.mesh_vertex_count = mesh_stats.get("vertex_count", result.get("mesh_vertex_count", 0))
            recon.mesh_triangle_count = mesh_stats.get("triangle_count", result.get("mesh_triangle_count", 0))

            recon.mean_reprojection_error = result.get("mean_reprojection_error")
            recon.camera_poses = result.get("camera_poses", [])

            # Bounding box
            if dense_stats.get("centroid"):
                recon.bounding_box = {
                    "min": dense_stats["min_bound"],
                    "max": dense_stats["max_bound"],
                    "centroid": dense_stats["centroid"],
                    "dimensions": dense_stats["dimensions"],
                }
            else:
                recon.bounding_box = result.get("bounding_box", {})

            recon.metadata_json = result.get("metadata", {})
            recon.processing_logs = result.get("logs", recon.processing_logs)

            survey.status = "reconstructed"
            db.commit()

        except Exception as e:
            logger.exception("Photogrammetry reconstruction pipeline failed.")
            db.rollback()
            recon = db.query(Reconstruction).filter(Reconstruction.id == reconstruction_id).first()
            if recon:
                recon.status = "failed"
                recon.current_stage = "FAILED"
                recon.error_message = str(e)
                recon.processing_logs = (recon.processing_logs or "") + f"\n[ERROR] {str(e)}\n"
                recon.completed_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            if owns_session:
                db.close()


    def get_model_file(
        self,
        reconstruction_id: str,
        model_type: str,
        db: Session,
    ) -> Tuple[Path, str, str]:
        """
        Safely resolves a 3D asset file from a reconstruction.
        Validates file existence and prevents directory traversal attacks.
        Returns: (file_path, media_type, filename)
        """
        recon = db.query(Reconstruction).filter(Reconstruction.id == reconstruction_id).first()
        if not recon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reconstruction '{reconstruction_id}' not found.",
            )

        if recon.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Reconstruction is currently '{recon.status}', not completed.",
            )

        target_path: Optional[str] = None
        media_type = "application/octet-stream"

        if model_type == "mesh":
            target_path = recon.mesh_path
        elif model_type == "dense":
            target_path = recon.dense_point_cloud_path
        elif model_type == "sparse":
            target_path = recon.sparse_point_cloud_path
        elif model_type == "obj":
            if recon.workspace_path:
                cand = Path(recon.workspace_path) / "mesh.obj"
                if cand.exists():
                    target_path = str(cand)
        elif model_type == "log":
            target_path = recon.log_path

        # Fallback if preferred dense or mesh is not present
        if not target_path:
            target_path = recon.mesh_path or recon.dense_point_cloud_path or recon.sparse_point_cloud_path

        if not target_path or not Path(target_path).exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"3D asset file for type '{model_type}' does not exist on disk.",
            )

        path_obj = Path(target_path).resolve()
        # Security check: ensure path is within DATA_DIR
        data_root = settings.DATA_DIR.resolve()
        if not str(path_obj).startswith(str(data_root)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Security validation error: requested file is outside project data root.",
            )

        ext = path_obj.suffix.lower()
        if ext == ".ply":
            media_type = "application/octet-stream"
        elif ext == ".obj":
            media_type = "text/plain"
        elif ext == ".log" or ext == ".txt":
            media_type = "text/plain"

        return path_obj, media_type, path_obj.name


photogrammetry_service = PhotogrammetryService()
