"""
2D-to-3D Damage Mapping Service.
Orchestrates camera ray generation, surface intersection, reprojection validation,
spatial persistence, and survey-level statistics.
"""
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
import math
import numpy as np
import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.heritage import (
    Survey,
    Image,
    Reconstruction,
    DeteriorationDetection,
    Deterioration3DMapping,
    Deterioration3DMappingPoint,
)
from app.schemas.damage_mapping import (
    Point2D,
    Point3D,
    Deterioration3DMappingItem,
    Deterioration3DMappingPointItem,
    Deterioration3DMappingRequest,
    Survey3DMappingSummary,
    MappingValidationResponse,
)
from app.services.camera_model import CameraModel
from app.services.surface_raycaster import SurfaceRaycaster
from app.services.damage_sampler import DamagePointSampler

logger = logging.getLogger(__name__)


class DamageMappingService:
    """Core service for 2D-to-3D deterioration localization."""

    @staticmethod
    def _convert_mapping_to_item(m: Deterioration3DMapping) -> Deterioration3DMappingItem:
        """Converts an ORM Deterioration3DMapping to Pydantic Deterioration3DMappingItem."""
        points = []
        if m.points:
            for pt in m.points:
                world_pt = None
                if pt.world_x is not None and pt.world_y is not None and pt.world_z is not None:
                    world_pt = Point3D(x=round(pt.world_x, 4), y=round(pt.world_y, 4), z=round(pt.world_z, 4))
                
                points.append(
                    Deterioration3DMappingPointItem(
                        id=pt.id,
                        mapping_id=pt.mapping_id,
                        point_type=pt.point_type,
                        image_point=Point2D(x=round(pt.image_x, 1), y=round(pt.image_y, 1)),
                        world_point=world_pt,
                        intersection_distance=round(pt.intersection_distance, 4) if pt.intersection_distance is not None else None,
                        reprojection_error_px=round(pt.reprojection_error_px, 2) if pt.reprojection_error_px is not None else None,
                        mapping_status=pt.mapping_status,
                        created_at=pt.created_at,
                    )
                )

        world_pt = None
        if m.world_x is not None and m.world_y is not None and m.world_z is not None:
            world_pt = Point3D(x=round(m.world_x, 4), y=round(m.world_y, 4), z=round(m.world_z, 4))

        img_pt = Point2D(x=round(m.image_x, 1) if m.image_x is not None else 0.0, y=round(m.image_y, 1) if m.image_y is not None else 0.0)

        filename = None
        if m.image:
            filename = m.image.filename

        bbox = None
        if m.detection:
            bbox = m.detection.bounding_box

        return Deterioration3DMappingItem(
            id=m.id,
            mapping_id=m.id,
            detection_id=m.detection_id,
            image_id=m.image_id,
            image_filename=filename,
            survey_id=m.survey_id,
            reconstruction_id=m.reconstruction_id,
            material_class=m.material_class or "UNKNOWN",
            material=m.material_class or "UNKNOWN",
            material_confidence=round(m.material_confidence, 3) if m.material_confidence is not None else None,
            material_association_status=m.material_association_status,
            deterioration_type=m.deterioration_type,
            deterioration_confidence=round(m.deterioration_confidence, 3),
            severity_hint=m.severity_hint,
            image_point=img_pt,
            world_point=world_pt,
            ray_origin=m.ray_origin,
            ray_direction=m.ray_direction,
            intersection_distance=round(m.intersection_distance, 4) if m.intersection_distance is not None else None,
            mapping_method=m.mapping_method,
            surface_source=m.surface_source,
            mapping_status=m.mapping_status,
            reprojection_error_px=round(m.reprojection_error_px, 2) if m.reprojection_error_px is not None else None,
            scale_status=m.scale_status,
            sampling_strategy=m.sampling_strategy,
            sample_point_count=m.sample_point_count,
            mapped_point_count=m.mapped_point_count,
            is_demo=bool(m.is_demo),
            inference_mode=m.inference_mode,
            notes=m.notes,
            points=points,
            bounding_box=bbox,
            created_at=m.created_at,
        )

    def map_detection(
        self,
        detection_id: str,
        db: Session,
        sampling_strategy: str = "CENTER_ONLY",
        reprojection_threshold_px: float = 5.0,
        cached_raycaster: Optional[SurfaceRaycaster] = None,
        cached_camera: Optional[CameraModel] = None,
    ) -> Deterioration3DMapping:
        """
        Maps a single 2D DeteriorationDetection onto the 3D reconstructed surface.
        Validates camera geometry, performs ray-surface intersection, computes reprojection error,
        and persists the 3D mapping record.
        """
        detection = db.query(DeteriorationDetection).filter(DeteriorationDetection.id == detection_id).first()
        if not detection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deterioration detection '{detection_id}' not found.",
            )

        survey = detection.survey
        image = detection.image
        if not survey or not image:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Detection is missing associated survey or image.",
            )

        # Retrieve reconstruction for the survey
        reconstruction = db.query(Reconstruction).filter(Reconstruction.survey_id == survey.id).first()
        if not reconstruction or reconstruction.status != "completed":
            # Record an explicit unavailable mapping without inventing coordinates
            return self._record_failed_mapping(
                db=db,
                detection=detection,
                reconstruction_id=reconstruction.id if reconstruction else "UNKNOWN",
                status="MAPPING_UNAVAILABLE",
                notes="Reconstruction is missing or not completed for this survey.",
            )

        # Resolve or reuse CameraModel
        camera = cached_camera
        if not camera:
            cam_model, status_msg = CameraModel.from_reconstruction_and_image(reconstruction, image)
            if not cam_model:
                return self._record_failed_mapping(
                    db=db,
                    detection=detection,
                    reconstruction_id=reconstruction.id,
                    status="MAPPING_REQUIRES_CALIBRATION",
                    notes=status_msg,
                )
            camera = cam_model

        # Resolve or reuse SurfaceRaycaster
        raycaster = cached_raycaster
        if not raycaster:
            raycaster = SurfaceRaycaster.from_reconstruction(
                reconstruction=reconstruction,
                proximity_tolerance=settings.SURFACE_RAYCAST_TOLERANCE,
            )

        # Sample 2D points from detection
        sample_points = DamagePointSampler.sample_points(detection, strategy=sampling_strategy)

        # Clear existing mapping for this detection if re-mapping
        existing = db.query(Deterioration3DMapping).filter(Deterioration3DMapping.detection_id == detection.id).first()
        if existing:
            db.delete(existing)
            db.flush()

        # Raycast all sampled points
        mapped_point_records: List[Deterioration3DMappingPoint] = []
        best_point: Optional[Tuple[str, float, float, np.ndarray, float, float, str, str]] = None
        mapped_count = 0
        surface_source_used = "NONE"
        mapping_method_used = "NONE"
        ray_origin_used = None
        ray_direction_used = None

        for pt_type, u, v in sample_points:
            origin, direction = camera.pixel_to_ray(u, v)
            hit_pos, dist, surf_src, map_method = raycaster.cast_ray(origin, direction)

            pt_status = "NO_SURFACE_INTERSECTION"
            reproj_err = None

            if hit_pos is not None:
                surface_source_used = surf_src
                mapping_method_used = map_method
                reproj_err = camera.compute_reprojection_error(hit_pos, u, v)

                if reproj_err is not None and reproj_err <= reprojection_threshold_px:
                    pt_status = "MAPPED"
                    mapped_count += 1
                else:
                    pt_status = "PARTIALLY_MAPPED"
                    mapped_count += 1

                # Prioritize center point or lowest reprojection error
                if best_point is None or pt_type == "center" or (best_point[0] != "center" and reproj_err is not None and (best_point[5] is None or reproj_err < best_point[5])):
                    best_point = (pt_type, u, v, hit_pos, dist, reproj_err, surf_src, map_method)
                    ray_origin_used = [round(float(c), 4) for c in origin]
                    ray_direction_used = [round(float(c), 4) for c in direction]

            point_record = Deterioration3DMappingPoint(
                point_type=pt_type,
                image_x=float(u),
                image_y=float(v),
                world_x=float(hit_pos[0]) if hit_pos is not None else None,
                world_y=float(hit_pos[1]) if hit_pos is not None else None,
                world_z=float(hit_pos[2]) if hit_pos is not None else None,
                intersection_distance=float(dist) if dist is not None else None,
                reprojection_error_px=float(reproj_err) if reproj_err is not None else None,
                mapping_status=pt_status,
            )
            mapped_point_records.append(point_record)

        # Determine overall mapping status
        if mapped_count == 0:
            overall_status = "NO_SURFACE_INTERSECTION"
            notes = "Camera rays did not intersect the reconstructed 3D surface."
        elif best_point and best_point[5] is not None and best_point[5] > reprojection_threshold_px:
            overall_status = "PARTIALLY_MAPPED"
            notes = f"Mapped with reprojection residual of {best_point[5]:.2f}px (exceeds {reprojection_threshold_px}px threshold)."
        else:
            overall_status = "MAPPED"
            notes = f"Successfully mapped {mapped_count}/{len(sample_points)} sample points to 3D surface."

        # Research provenance
        is_demo_flag = bool(detection.is_demo or reconstruction.is_demo)
        inference_mode_flag = "demo" if is_demo_flag else "real_trained"

        mapping = Deterioration3DMapping(
            detection_id=detection.id,
            reconstruction_id=reconstruction.id,
            survey_id=survey.id,
            image_id=image.id,
            world_x=float(best_point[3][0]) if best_point else None,
            world_y=float(best_point[3][1]) if best_point else None,
            world_z=float(best_point[3][2]) if best_point else None,
            image_x=float(best_point[1]) if best_point else float(sample_points[0][1]),
            image_y=float(best_point[2]) if best_point else float(sample_points[0][2]),
            ray_origin=ray_origin_used,
            ray_direction=ray_direction_used,
            intersection_distance=float(best_point[4]) if best_point else None,
            mapping_method=mapping_method_used if mapping_method_used != "NONE" else "MESH_RAYCAST",
            mapping_status=overall_status,
            surface_source=surface_source_used if surface_source_used != "NONE" else "DENSE_MESH",
            reprojection_error_px=float(best_point[5]) if best_point and best_point[5] is not None else None,
            scale_status=settings.RECONSTRUCTION_DEFAULT_SCALE_STATUS,
            sampling_strategy=sampling_strategy,
            sample_point_count=len(sample_points),
            mapped_point_count=mapped_count,
            deterioration_type=detection.damage_type,
            deterioration_confidence=detection.confidence,
            severity_hint=detection.severity_hint or "moderate",
            material_class=detection.material_class or "UNKNOWN",
            material_confidence=detection.material_confidence,
            material_association_status=detection.material_association_status or "MATERIAL_ASSOCIATION_UNAVAILABLE",
            is_demo=is_demo_flag,
            inference_mode=inference_mode_flag,
            notes=notes,
            created_at=datetime.now(timezone.utc),
        )

        for pt_rec in mapped_point_records:
            mapping.points.append(pt_rec)

        db.add(mapping)
        db.commit()
        db.refresh(mapping)
        return mapping

    def _record_failed_mapping(
        self,
        db: Session,
        detection: DeteriorationDetection,
        reconstruction_id: str,
        status: str,
        notes: str,
    ) -> Deterioration3DMapping:
        """Persists a failed or uncalibrated mapping state without inventing fake coordinates."""
        existing = db.query(Deterioration3DMapping).filter(Deterioration3DMapping.detection_id == detection.id).first()
        if existing:
            db.delete(existing)
            db.flush()

        bbox = detection.bounding_box or {}
        cx = float(bbox.get("x", 0)) + float(bbox.get("w", 0)) / 2.0
        cy = float(bbox.get("y", 0)) + float(bbox.get("h", 0)) / 2.0

        mapping = Deterioration3DMapping(
            detection_id=detection.id,
            reconstruction_id=reconstruction_id,
            survey_id=detection.survey_id,
            image_id=detection.image_id,
            world_x=None,
            world_y=None,
            world_z=None,
            image_x=cx,
            image_y=cy,
            mapping_method="NONE",
            mapping_status=status,
            surface_source="NONE",
            reprojection_error_px=None,
            scale_status="UNKNOWN",
            sampling_strategy="CENTER_ONLY",
            sample_point_count=1,
            mapped_point_count=0,
            deterioration_type=detection.damage_type,
            deterioration_confidence=detection.confidence,
            severity_hint=detection.severity_hint or "moderate",
            material_class=detection.material_class or "UNKNOWN",
            material_confidence=detection.material_confidence,
            material_association_status=detection.material_association_status or "MATERIAL_ASSOCIATION_UNAVAILABLE",
            is_demo=bool(detection.is_demo),
            inference_mode=detection.inference_mode or "demo",
            notes=notes,
            created_at=datetime.now(timezone.utc),
        )
        db.add(mapping)
        db.commit()
        db.refresh(mapping)
        return mapping

    def map_survey_detections(
        self,
        survey_id: str,
        db: Session,
        request: Deterioration3DMappingRequest,
    ) -> Survey3DMappingSummary:
        """
        Batch maps all deterioration detections in a survey to the survey's 3D reconstruction.
        Caches camera models and 3D surface geometry for high-efficiency CPU execution.
        """
        survey = db.query(Survey).filter(Survey.id == survey_id).first()
        if not survey:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Survey '{survey_id}' not found.",
            )

        reconstruction = db.query(Reconstruction).filter(Reconstruction.survey_id == survey_id).first()
        if not reconstruction:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Survey '{survey_id}' has no 3D reconstruction. Run photogrammetry before 3D damage mapping.",
            )

        detections = db.query(DeteriorationDetection).filter(DeteriorationDetection.survey_id == survey_id).all()
        if not detections:
            return Survey3DMappingSummary(
                survey_id=survey_id,
                reconstruction_id=reconstruction.id,
                total_eligible_detections=0,
                scale_status=settings.RECONSTRUCTION_DEFAULT_SCALE_STATUS,
                is_demo=bool(reconstruction.is_demo),
                inference_mode="demo" if reconstruction.is_demo else "real_trained",
            )

        # Cache geometry across the survey
        raycaster = SurfaceRaycaster.from_reconstruction(
            reconstruction=reconstruction,
            proximity_tolerance=settings.SURFACE_RAYCAST_TOLERANCE,
        )

        # Cache camera models by image ID
        camera_cache: Dict[str, Optional[CameraModel]] = {}
        for img in survey.images:
            cam, _ = CameraModel.from_reconstruction_and_image(reconstruction, img)
            camera_cache[img.id] = cam

        # Map each detection
        mappings: List[Deterioration3DMapping] = []
        for det in detections:
            cached_cam = camera_cache.get(det.image_id)
            mapping = self.map_detection(
                detection_id=det.id,
                db=db,
                sampling_strategy=request.sampling_strategy or "CENTER_ONLY",
                reprojection_threshold_px=request.reprojection_threshold_px or 5.0,
                cached_raycaster=raycaster,
                cached_camera=cached_cam,
            )
            mappings.append(mapping)

        return self._compute_summary(survey_id, reconstruction.id, mappings)

    def get_survey_mapping_summary(self, survey_id: str, db: Session) -> Survey3DMappingSummary:
        """Retrieves cached survey-level 3D damage mappings and computes aggregate metrics."""
        survey = db.query(Survey).filter(Survey.id == survey_id).first()
        if not survey:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Survey '{survey_id}' not found.",
            )

        recon = db.query(Reconstruction).filter(Reconstruction.survey_id == survey_id).first()
        recon_id = recon.id if recon else None

        mappings = db.query(Deterioration3DMapping).filter(Deterioration3DMapping.survey_id == survey_id).all()
        return self._compute_summary(survey_id, recon_id, mappings)

    def _compute_summary(
        self,
        survey_id: str,
        reconstruction_id: Optional[str],
        mappings: List[Deterioration3DMapping],
    ) -> Survey3DMappingSummary:
        """Aggregates metrics and cross-tabulations across mapped detections."""
        total = len(mappings)
        mapped = 0
        partially_mapped = 0
        no_intersection = 0
        unavailable = 0

        det_by_type: Dict[str, int] = {}
        det_by_material: Dict[str, int] = {}
        mat_det_matrix: Dict[str, Dict[str, int]] = {}
        surf_breakdown: Dict[str, int] = {}
        reproj_errors: List[float] = []

        is_demo_survey = False
        all_items = []

        for m in mappings:
            all_items.append(self._convert_mapping_to_item(m))
            if m.is_demo:
                is_demo_survey = True

            # Status counts
            if m.mapping_status == "MAPPED":
                mapped += 1
            elif m.mapping_status == "PARTIALLY_MAPPED":
                partially_mapped += 1
            elif m.mapping_status == "NO_SURFACE_INTERSECTION":
                no_intersection += 1
            else:
                unavailable += 1

            # Defect counts
            dtype = m.deterioration_type
            det_by_type[dtype] = det_by_type.get(dtype, 0) + 1

            # Material counts
            mat = m.material_class or "UNKNOWN"
            det_by_material[mat] = det_by_material.get(mat, 0) + 1

            # Cross-tabulation matrix: Material x Deterioration
            if mat not in mat_det_matrix:
                mat_det_matrix[mat] = {}
            mat_det_matrix[mat][dtype] = mat_det_matrix[mat].get(dtype, 0) + 1

            # Surface sources
            if m.surface_source and m.surface_source != "NONE":
                surf_breakdown[m.surface_source] = surf_breakdown.get(m.surface_source, 0) + 1

            # Reprojection errors
            if m.reprojection_error_px is not None:
                reproj_errors.append(m.reprojection_error_px)

        # Mapping success rate: mapped / total (clearly mapping rate, NOT accuracy)
        success_rate = round((mapped / total * 100.0), 2) if total > 0 else 0.0
        mean_reproj = round(float(np.mean(reproj_errors)), 2) if reproj_errors else None

        return Survey3DMappingSummary(
            survey_id=survey_id,
            reconstruction_id=reconstruction_id,
            total_eligible_detections=total,
            mapped_detections=mapped,
            partially_mapped_detections=partially_mapped,
            no_intersection_detections=no_intersection,
            unavailable_mappings=unavailable,
            mapping_success_rate=success_rate,
            detections_by_type=det_by_type,
            detections_by_material=det_by_material,
            material_deterioration_cross_tabulation=mat_det_matrix,
            mean_reprojection_error_px=mean_reproj,
            surface_source_breakdown=surf_breakdown,
            scale_status=settings.RECONSTRUCTION_DEFAULT_SCALE_STATUS,
            is_demo=is_demo_survey,
            inference_mode="demo" if is_demo_survey else "real_trained",
            mappings=all_items,
        )

    def validate_mapping(
        self,
        mapping_id: str,
        db: Session,
        tolerance_px: float = 5.0,
    ) -> MappingValidationResponse:
        """
        Validates an existing 3D mapping by reprojecting its 3D world coordinates
        back into the camera and computing the pixel residual error.
        """
        mapping = db.query(Deterioration3DMapping).filter(Deterioration3DMapping.id == mapping_id).first()
        if not mapping:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"3D Mapping '{mapping_id}' not found.",
            )

        orig_pt = Point2D(x=mapping.image_x or 0.0, y=mapping.image_y or 0.0)

        if mapping.world_x is None or mapping.world_y is None or mapping.world_z is None:
            return MappingValidationResponse(
                mapping_id=mapping.id,
                status=mapping.mapping_status,
                reprojection_error_px=None,
                is_valid=False,
                original_point=orig_pt,
                reprojected_point=None,
                world_point=None,
                tolerance_px=tolerance_px,
                notes="Mapping does not have 3D coordinates (failed or no surface intersection).",
            )

        world_np = np.array([mapping.world_x, mapping.world_y, mapping.world_z], dtype=np.float64)
        world_pt = Point3D(x=round(mapping.world_x, 4), y=round(mapping.world_y, 4), z=round(mapping.world_z, 4))

        recon = mapping.reconstruction
        img = mapping.image
        if not recon or not img:
            return MappingValidationResponse(
                mapping_id=mapping.id,
                status=mapping.mapping_status,
                reprojection_error_px=None,
                is_valid=False,
                original_point=orig_pt,
                world_point=world_pt,
                tolerance_px=tolerance_px,
                notes="Cannot validate: associated image or reconstruction not found.",
            )

        cam, msg = CameraModel.from_reconstruction_and_image(recon, img)
        if not cam:
            return MappingValidationResponse(
                mapping_id=mapping.id,
                status=mapping.mapping_status,
                reprojection_error_px=None,
                is_valid=False,
                original_point=orig_pt,
                world_point=world_pt,
                tolerance_px=tolerance_px,
                notes=f"Camera validation failed: {msg}",
            )

        u_proj, v_proj, z_cam = cam.world_to_pixel(world_np)
        if u_proj is None or v_proj is None:
            return MappingValidationResponse(
                mapping_id=mapping.id,
                status="PARTIALLY_MAPPED",
                reprojection_error_px=None,
                is_valid=False,
                original_point=orig_pt,
                world_point=world_pt,
                tolerance_px=tolerance_px,
                notes="Projected point lies behind the camera plane.",
            )

        du = u_proj - mapping.image_x
        dv = v_proj - mapping.image_y
        err = math.sqrt(du * du + dv * dv)
        is_val = err <= tolerance_px

        return MappingValidationResponse(
            mapping_id=mapping.id,
            status="MAPPED" if is_val else "PARTIALLY_MAPPED",
            reprojection_error_px=round(err, 2),
            is_valid=is_val,
            original_point=orig_pt,
            reprojected_point=Point2D(x=round(u_proj, 1), y=round(v_proj, 1)),
            world_point=world_pt,
            tolerance_px=tolerance_px,
            notes=f"Reprojection error: {err:.2f}px (threshold: {tolerance_px}px).",
        )
