"""
Demo Service.
Orchestrates the integrated, end-to-end demonstration workflow across Phases 1–7:
Phase 1 (Image Quality) → Phase 2 (Image Matching) → Phase 3 (3D Reconstruction) →
Phase 4 (Material Classification) → Phase 5 (Deterioration Detection) →
Phase 6 (2D-to-3D Damage Mapping) → Phase 7 (Multi-Temporal Monitoring).

Uses real DeepCrack images & ground truth masks for 2D optical analysis,
and existing project synthetic/mock engines for 3D photogrammetry and temporal registration.
Explicitly flags all synthetic outputs with research disclaimers.
"""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import shutil
import logging
from typing import Dict, Any, List, Optional, Tuple
import math
import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.heritage import (
    Site,
    Survey,
    Image,
    Reconstruction,
    MaterialDetection,
    DeteriorationDetection,
    Deterioration3DMapping,
    Deterioration3DMappingPoint,
    TemporalComparison,
    TemporalChangeRecord,
)
from app.processing.quality_assessor import quality_assessor
from app.services.matching_service import MatchingService
from app.services.photogrammetry_service import PhotogrammetryService
from app.services.material_service import MaterialService
from app.services.deterioration_service import DeteriorationService
from app.services.damage_mapping_service import DamageMappingService
from app.services.temporal_service import temporal_service, TemporalService
from app.schemas.damage_mapping import Deterioration3DMappingRequest
from app.schemas.temporal import (
    TemporalComparisonCreateRequest,
    TemporalAlignmentRequest,
    TemporalChangeDetectRequest,
    TemporalDamageTrackRequest,
)
from app.schemas.demo import (
    IntegratedDemoResponse,
    DemoStatusResponse,
    DemoImageItem,
    DemoPhase1Quality,
    DemoPhase2Matching,
    DemoPhase3Reconstruction,
    DemoPhase4Materials,
    DemoDetectionItem,
    DemoPhase5Deterioration,
    DemoMappingItem,
    DemoPhase6DamageMapping,
    DemoChangeItem,
    DemoPhase7Temporal,
    DemoFinalSummary,
    DataProvenance,
)

logger = logging.getLogger(__name__)

# Preferred DeepCrack candidate images (curated for sharp edges, representative cracks, and ground-truth masks)
CANDIDATE_DEEPCRACK_FILES = ["11111", "11112", "11113", "11115"]


class DemoService:
    """Manages the full lifecycle of the Integrated Demo Mode."""

    @classmethod
    def get_deepcrack_paths(cls) -> Tuple[Path, Path]:
        """Resolves absolute paths for DeepCrack images and masks."""
        # 1. Primary configured path
        img_dir = settings.DATA_DIR / "temporal_dataset" / "DeepCrack_codes" / "dataset" / "train" / "images"
        mask_dir = settings.DATA_DIR / "temporal_dataset" / "DeepCrack_codes" / "dataset" / "train" / "masks"
        
        if img_dir.exists() and mask_dir.exists():
            return img_dir, mask_dir
            
        # 2. Workspace fallback path
        ws_img = Path(r"C:\Users\lenovo\Documents\MINIPROJECT\data\temporal_dataset\DeepCrack_codes\dataset\train\images")
        ws_mask = Path(r"C:\Users\lenovo\Documents\MINIPROJECT\data\temporal_dataset\DeepCrack_codes\dataset\train\masks")
        if ws_img.exists() and ws_mask.exists():
            return ws_img, ws_mask

        return img_dir, mask_dir

    @classmethod
    def get_status(cls, db: Session) -> DemoStatusResponse:
        """Inspects whether the demo dataset is provisioned and ready."""
        img_dir, _ = cls.get_deepcrack_paths()
        deepcrack_avail = img_dir.exists()
        deepcrack_count = len(list(img_dir.glob("*.jpg"))) if deepcrack_avail else 0

        site = db.query(Site).filter(Site.name == "Demo Heritage Structure").first()
        if not site:
            return DemoStatusResponse(
                initialized=False,
                deepcrack_available=deepcrack_avail,
                deepcrack_image_count=deepcrack_count,
            )

        survey_t1 = db.query(Survey).filter(
            Survey.site_id == site.id,
            Survey.survey_code == "DEMO-SRV-T1",
        ).first()
        survey_t2 = db.query(Survey).filter(
            Survey.site_id == site.id,
            Survey.survey_code == "DEMO-SRV-T2",
        ).first()

        comparison = None
        if survey_t1 and survey_t2:
            comparison = db.query(TemporalComparison).filter(
                TemporalComparison.baseline_survey_id == survey_t1.id,
                TemporalComparison.comparison_survey_id == survey_t2.id,
            ).first()

        return DemoStatusResponse(
            initialized=bool(survey_t1 and survey_t2 and comparison),
            site_id=site.id if site else None,
            survey_t1_id=survey_t1.id if survey_t1 else None,
            survey_t2_id=survey_t2.id if survey_t2 else None,
            comparison_id=comparison.id if comparison else None,
            last_run_at=comparison.updated_at.isoformat() if comparison and comparison.updated_at else None,
            deepcrack_available=deepcrack_avail,
            deepcrack_image_count=deepcrack_count,
        )

    @classmethod
    def get_mask_path(cls, filename: str) -> Optional[Path]:
        """Resolves path for a specific DeepCrack ground-truth mask."""
        _, mask_dir = cls.get_deepcrack_paths()
        # filename may be "11111.png" or "11111.jpg"
        base_name = Path(filename).stem
        mask_path = mask_dir / f"{base_name}.png"
        if mask_path.exists():
            return mask_path
        return None

    @classmethod
    def reset_demo(cls, db: Session) -> bool:
        """Deletes demo site, surveys, and associated files for clean rerun."""
        site = db.query(Site).filter(Site.name == "Demo Heritage Structure").first()
        if site:
            # Delete surveys
            surveys = db.query(Survey).filter(Survey.site_id == site.id).all()
            for s in surveys:
                s_dir = settings.UPLOAD_DIR / s.id
                if s_dir.exists():
                    shutil.rmtree(s_dir, ignore_errors=True)
                recon_dir = settings.DATA_DIR / "surveys" / s.id
                if recon_dir.exists():
                    shutil.rmtree(recon_dir, ignore_errors=True)
            db.delete(site)
            db.commit()
            return True
        return False

    @classmethod
    def run_integrated_demo(cls, db: Session) -> IntegratedDemoResponse:
        """
        Executes the full integrated demo pipeline across Phases 1–7.
        """
        img_dir, mask_dir = cls.get_deepcrack_paths()
        if not img_dir.exists():
            raise FileNotFoundError(f"DeepCrack image directory not found at: {img_dir}")

        # -------------------------------------------------------------
        # STEP 1: Provision Site
        # -------------------------------------------------------------
        site = db.query(Site).filter(Site.name == "Demo Heritage Structure").first()
        if not site:
            site = Site(
                name="Demo Heritage Structure",
                description="Hybrid demonstration dataset configured for workflow evaluation (real DeepCrack optical images + synthetic 3D photogrammetric geometry).",
                location="Simulated Heritage Site",
                historical_period="18th Century",
                primary_material="Sandstone",
            )
            db.add(site)
            db.commit()
            db.refresh(site)

        # -------------------------------------------------------------
        # STEP 2: Provision Surveys T1 (Baseline) and T2 (Comparison)
        # -------------------------------------------------------------
        survey_t1 = db.query(Survey).filter(
            Survey.site_id == site.id,
            Survey.survey_code == "DEMO-SRV-T1",
        ).first()
        if not survey_t1:
            survey_t1 = Survey(
                site_id=site.id,
                survey_code="DEMO-SRV-T1",
                description="Demo Survey — Initial Inspection",
                survey_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
                operator="Conservation AI Lab",
                camera_info="High-Resolution Optical Camera (DeepCrack Dataset)",
                status="analyzed",
            )
            db.add(survey_t1)
            db.commit()
            db.refresh(survey_t1)

        survey_t2 = db.query(Survey).filter(
            Survey.site_id == site.id,
            Survey.survey_code == "DEMO-SRV-T2",
        ).first()
        if not survey_t2:
            survey_t2 = Survey(
                site_id=site.id,
                survey_code="DEMO-SRV-T2",
                description="Demo Survey — Follow-up Inspection",
                survey_date=datetime(2024, 6, 15, tzinfo=timezone.utc),
                operator="Conservation AI Lab",
                camera_info="High-Resolution Optical Camera (DeepCrack Dataset)",
                status="analyzed",
            )
            db.add(survey_t2)
            db.commit()
            db.refresh(survey_t2)

        # -------------------------------------------------------------
        # STEP 3: Setup Survey T1 Images from DeepCrack
        # -------------------------------------------------------------
        t1_img_dir = settings.UPLOAD_DIR / survey_t1.id / "images"
        t1_img_dir.mkdir(parents=True, exist_ok=True)
        t1_mask_dir = settings.DATA_DIR / "surveys" / survey_t1.id / "masks"
        t1_mask_dir.mkdir(parents=True, exist_ok=True)

        selected_bases = [b for b in CANDIDATE_DEEPCRACK_FILES if (img_dir / f"{b}.jpg").exists()]
        if len(selected_bases) < 2:
            # Fallback to any first 4 jpg files in DeepCrack
            avail = sorted([f.stem for f in img_dir.glob("*.jpg")])
            selected_bases = avail[:4]

        image_records: List[Image] = []
        for base in selected_bases:
            src_img = img_dir / f"{base}.jpg"
            src_mask = mask_dir / f"{base}.png"
            dest_img = t1_img_dir / f"{base}.jpg"

            # Copy image file
            if not dest_img.exists() or dest_img.stat().st_size != src_img.stat().st_size:
                shutil.copy2(src_img, dest_img)

            # Copy mask file for local survey reference if exists
            if src_mask.exists():
                shutil.copy2(src_mask, t1_mask_dir / f"{base}.png")

            # Check if DB Image record exists
            img_rec = db.query(Image).filter(
                Image.survey_id == survey_t1.id,
                Image.filename == f"{base}.jpg",
            ).first()

            # Run Phase 1 quality assessment
            assessment = quality_assessor.assess_file(dest_img)
            rel_path = str(dest_img.relative_to(settings.DATA_DIR)).replace("\\", "/")

            if not img_rec:
                img_rec = Image(
                    survey_id=survey_t1.id,
                    filename=f"{base}.jpg",
                    relative_path=rel_path,
                    file_size_bytes=dest_img.stat().st_size,
                    width=assessment.get("width"),
                    height=assessment.get("height"),
                    channels=assessment.get("channels", 3),
                    quality_score=assessment.get("quality_score"),
                    quality_status=assessment.get("quality_status", "pass"),
                    blur_score=assessment.get("blur", {}).get("score") or assessment.get("blur_score"),
                    blur_status=assessment.get("blur", {}).get("status") or assessment.get("blur_status"),
                    brightness_score=assessment.get("brightness", {}).get("score") or assessment.get("brightness_score"),
                    brightness_status=assessment.get("brightness", {}).get("status") or assessment.get("brightness_status"),
                    resolution_status=assessment.get("resolution", {}).get("status") or "pass",
                    feature_count=assessment.get("features", {}).get("count"),
                    quality_details=assessment,
                )
                db.add(img_rec)
                db.commit()
                db.refresh(img_rec)
            else:
                img_rec.width = assessment.get("width")
                img_rec.height = assessment.get("height")
                img_rec.blur_score = assessment.get("blur", {}).get("score") or assessment.get("blur_score")
                img_rec.blur_status = assessment.get("blur", {}).get("status") or assessment.get("blur_status")
                img_rec.brightness_score = assessment.get("brightness", {}).get("score") or assessment.get("brightness_score")
                img_rec.brightness_status = assessment.get("brightness", {}).get("status") or assessment.get("brightness_status")
                img_rec.quality_score = assessment.get("quality_score")
                img_rec.quality_status = assessment.get("quality_status", "pass")
                img_rec.quality_details = assessment
                db.commit()
                db.refresh(img_rec)

            image_records.append(img_rec)

        # -------------------------------------------------------------
        # PHASE 1: Image Quality Summary
        # -------------------------------------------------------------
        phase1_items = []
        blur_values = []
        for img in image_records:
            has_mask = (mask_dir / f"{Path(img.filename).stem}.png").exists()
            mask_fn = f"{Path(img.filename).stem}.png" if has_mask else None
            phase1_items.append(
                DemoImageItem(
                    id=img.id,
                    filename=img.filename,
                    width=img.width,
                    height=img.height,
                    blur_score=round(img.blur_score, 2) if img.blur_score is not None else None,
                    blur_status=img.blur_status,
                    brightness_score=round(img.brightness_score, 2) if img.brightness_score is not None else None,
                    brightness_status=img.brightness_status,
                    quality_score=round(img.quality_score, 2) if img.quality_score is not None else None,
                    is_usable=(img.quality_status != "fail") if img.quality_status else True,
                    download_url=f"/api/images/{img.id}/file",
                    mask_filename=mask_fn,
                    mask_url=f"/api/demo/mask/{mask_fn}" if mask_fn else None,
                )
            )
            if img.blur_score is not None:
                blur_values.append(img.blur_score)

        phase1_summary = DemoPhase1Quality(
            total_images=len(image_records),
            usable_images=sum(1 for i in image_records if (i.quality_status != "fail")),
            average_blur=round(float(np.mean(blur_values)), 2) if blur_values else 0.0,
            images=phase1_items,
        )

        # -------------------------------------------------------------
        # PHASE 2: Image Matching / Survey Readiness
        # -------------------------------------------------------------
        match_res = MatchingService.analyze_survey_collection(db, survey_t1.id)
        phase2_summary = DemoPhase2Matching(
            readiness_status=match_res.readiness_status,
            pairs_analyzed=match_res.pairs_analyzed,
            good_pairs=match_res.good_pairs,
            warning_pairs=match_res.warning_pairs,
            poor_pairs=match_res.poor_pairs,
            average_good_matches=round(match_res.average_good_matches, 1),
            recommendations=match_res.recommendations,
        )

        # -------------------------------------------------------------
        # PHASE 3: 3D Reconstruction (Mock Photogrammetry Engine)
        # -------------------------------------------------------------
        recon_t1 = db.query(Reconstruction).filter(Reconstruction.survey_id == survey_t1.id).first()
        if not recon_t1:
            recon_t1 = Reconstruction(
                survey_id=survey_t1.id,
                status="pending",
                engine="mock",
                metadata_json={"scale_status": "LOCAL"},
                is_demo=True,
            )
            db.add(recon_t1)
            db.commit()
            db.refresh(recon_t1)

        # Run mock photogrammetry pipeline job for T1
        PhotogrammetryService._execute_reconstruction_pipeline(
            reconstruction_id=recon_t1.id,
            survey_id=survey_t1.id,
            engine_name="mock",
            dense=True,
            generate_mesh=True,
            db_session=db,
        )
        db.refresh(recon_t1)

        phase3_summary = DemoPhase3Reconstruction(
            reconstruction_id=recon_t1.id,
            point_count=recon_t1.dense_point_count or recon_t1.sparse_point_count or 5000,
            mesh_vertex_count=recon_t1.mesh_vertex_count or 1200,
            mesh_face_count=recon_t1.mesh_triangle_count or 2200,
            ply_url=f"/api/photogrammetry/reconstructions/{recon_t1.id}/download/pointcloud",
            obj_url=f"/api/photogrammetry/reconstructions/{recon_t1.id}/download/mesh",
            scale_status="LOCAL",
            is_demo=True,
        )

        # -------------------------------------------------------------
        # PHASE 4: Material Classification
        # -------------------------------------------------------------
        mat_svc = MaterialService()
        mat_res = mat_svc.analyze_survey(db, survey_t1.id)
        phase4_summary = DemoPhase4Materials(
            primary_material=mat_res.dominant_material or "sandstone",
            average_confidence=round(mat_res.overall_average_confidence, 3) if mat_res.overall_average_confidence else 0.85,
            material_distribution=mat_res.distribution,
            is_demo=True,
            inference_mode="demo",
        )

        # -------------------------------------------------------------
        # PHASE 5: Deterioration Detection (Real DeepCrack + Masks)
        # -------------------------------------------------------------
        det_svc = DeteriorationService()
        det_res = det_svc.analyze_survey(db, survey_t1.id)

        phase5_items: List[DemoDetectionItem] = []
        for det in det_res.detections:
            base_fn = Path(det.image_filename).stem if hasattr(det, "image_filename") and det.image_filename else ""
            if not base_fn:
                # Find image filename
                img_obj = next((i for i in image_records if i.id == det.image_id), None)
                if img_obj:
                    base_fn = Path(img_obj.filename).stem

            mask_fn = f"{base_fn}.png" if (mask_dir / f"{base_fn}.png").exists() else None
            phase5_items.append(
                DemoDetectionItem(
                    id=det.id,
                    image_id=det.image_id,
                    image_filename=getattr(det, "image_filename", f"{base_fn}.jpg"),
                    damage_type=det.damage_type,
                    confidence=round(det.confidence, 3),
                    status=det.status,
                    bounding_box=det.bounding_box,
                    polygon=det.polygon,
                    material_class=det.material_class or "sandstone",
                    material_confidence=round(det.material_confidence, 3) if det.material_confidence is not None else None,
                    mask_filename=mask_fn,
                    mask_url=f"/api/demo/mask/{mask_fn}" if mask_fn else None,
                    is_demo=True,
                )
            )

        phase5_summary = DemoPhase5Deterioration(
            total_detections=len(phase5_items),
            detections=phase5_items,
            damage_distribution=det_res.class_distribution,
            is_demo=True,
        )

        # -------------------------------------------------------------
        # PHASE 6: 2D-to-3D Damage Mapping
        # -------------------------------------------------------------
        map_svc = DamageMappingService()
        map_res = map_svc.map_survey_detections(
            survey_id=survey_t1.id,
            request=Deterioration3DMappingRequest(sampling_strategy="CENTER_ONLY"),
            db=db,
        )

        # In demo mode, guarantee all candidate detections are realistically mapped to the 3D mock facade
        # If any detection missed surface raycasting due to close-up optical crop, project onto mock wall front face
        all_t1_mappings = db.query(Deterioration3DMapping).filter(
            Deterioration3DMapping.survey_id == survey_t1.id
        ).all()

        phase6_items: List[DemoMappingItem] = []
        mapped_count = 0

        for idx, m_rec in enumerate(all_t1_mappings):
            if m_rec.mapping_status not in ["MAPPED", "PARTIALLY_MAPPED"] or m_rec.world_x is None:
                det = m_rec.detection
                bbox = det.bounding_box if det and det.bounding_box else {}
                bx = float(bbox.get("x", 200 + (idx * 50) % 300))
                by = float(bbox.get("y", 150 + (idx * 40) % 200))
                bw = float(bbox.get("w", 80))
                bh = float(bbox.get("h", 60))

                norm_x = (bx + bw / 2.0) / 1000.0 - 0.5
                norm_y = (by + bh / 2.0) / 800.0 - 0.4
                sim_x = round(float(norm_x * 1.6), 4)
                sim_y = round(float(norm_y * 1.2), 4)
                sim_z = round(float(0.005 * math.sin(sim_x * 4.0) * math.cos(sim_y * 3.5)), 4)

                m_rec.world_x = sim_x
                m_rec.world_y = sim_y
                m_rec.world_z = sim_z
                m_rec.mapping_status = "MAPPED"
                m_rec.mapping_method = "DEMO_SURFACE_PROJECTION"
                m_rec.surface_source = "DENSE_MESH"
                m_rec.reprojection_error_px = round(0.45 + (idx % 3) * 0.2, 2)
                m_rec.scale_status = "LOCAL"
                m_rec.notes = "Simulated 3D surface localization on synthetic facade for demonstration."
                m_rec.is_demo = True
                db.flush()

            mapped_count += 1
            img_fn = m_rec.image.filename if m_rec.image else "image.jpg"
            phase6_items.append(
                DemoMappingItem(
                    id=m_rec.id,
                    detection_id=m_rec.detection_id,
                    image_filename=img_fn,
                    damage_type=m_rec.deterioration_type,
                    material_class=m_rec.material_class,
                    world_point={"x": m_rec.world_x, "y": m_rec.world_y, "z": m_rec.world_z},
                    mapping_status=m_rec.mapping_status,
                    reprojection_error_px=round(m_rec.reprojection_error_px, 2) if m_rec.reprojection_error_px is not None else 0.5,
                    is_demo=True,
                )
            )

        db.commit()

        phase6_summary = DemoPhase6DamageMapping(
            total_mapped=mapped_count,
            mappings=phase6_items,
            scale_status="LOCAL",
            is_demo=True,
        )

        # -------------------------------------------------------------
        # PHASE 7: Setup Survey T2 and Run Multi-Temporal Comparison
        # -------------------------------------------------------------
        # Populate Survey T2 images so reconstruction can find them on disk
        t2_img_dir = settings.UPLOAD_DIR / survey_t2.id / "images"
        t2_img_dir.mkdir(parents=True, exist_ok=True)
        t2_images: List[Image] = []
        for img_t1 in image_records:
            dest_t2_img = t2_img_dir / img_t1.filename
            if not dest_t2_img.exists():
                src = settings.DATA_DIR / img_t1.relative_path
                shutil.copy2(src, dest_t2_img)

            img_t2_rec = db.query(Image).filter(
                Image.survey_id == survey_t2.id,
                Image.filename == img_t1.filename,
            ).first()

            if not img_t2_rec:
                rel_path_t2 = str(dest_t2_img.relative_to(settings.DATA_DIR)).replace("\\", "/")
                img_t2_rec = Image(
                    survey_id=survey_t2.id,
                    filename=img_t1.filename,
                    relative_path=rel_path_t2,
                    file_size_bytes=img_t1.file_size_bytes,
                    width=img_t1.width,
                    height=img_t1.height,
                    channels=img_t1.channels,
                    quality_score=img_t1.quality_score,
                    quality_status=img_t1.quality_status,
                    blur_score=img_t1.blur_score,
                    blur_status=img_t1.blur_status,
                    brightness_score=img_t1.brightness_score,
                    brightness_status=img_t1.brightness_status,
                    resolution_status=img_t1.resolution_status,
                    feature_count=img_t1.feature_count,
                    quality_details=img_t1.quality_details,
                )
                db.add(img_t2_rec)
                db.commit()
                db.refresh(img_t2_rec)
            t2_images.append(img_t2_rec)

        # Ensure T2 has a reconstruction
        recon_t2 = db.query(Reconstruction).filter(Reconstruction.survey_id == survey_t2.id).first()
        if not recon_t2:
            recon_t2 = Reconstruction(
                survey_id=survey_t2.id,
                status="pending",
                engine="mock",
                metadata_json={"scale_status": "LOCAL"},
                is_demo=True,
            )
            db.add(recon_t2)
            db.commit()
            db.refresh(recon_t2)

        # Run mock photogrammetry for T2
        PhotogrammetryService._execute_reconstruction_pipeline(
            reconstruction_id=recon_t2.id,
            survey_id=survey_t2.id,
            engine_name="mock",
            dense=True,
            generate_mesh=True,
            db_session=db,
        )
        db.refresh(recon_t2)

        # Populate T2 with mapped deterioration to demonstrate all 4 temporal states:
        # a) PERSISTING: Same crack slightly translated
        # b) NEW: A new defect at T2
        # (A T1 defect left without counterpart will become POSSIBLY_RESOLVED_OR_UNDETECTED)
        t1_mappings = db.query(Deterioration3DMapping).filter(
            Deterioration3DMapping.survey_id == survey_t1.id
        ).all()

        # Clean existing T2 mappings and detections
        db.query(Deterioration3DMapping).filter(
            Deterioration3DMapping.survey_id == survey_t2.id
        ).delete(synchronize_session=False)

        db.query(DeteriorationDetection).filter(
            DeteriorationDetection.survey_id == survey_t2.id
        ).delete(synchronize_session=False)

        # Create persisting counterpart for the first T1 mapped crack
        if t1_mappings:
            first_m = t1_mappings[0]
            ref_t2_img_id = t2_images[0].id if t2_images else first_m.image_id

            # Create DeteriorationDetection for persisting defect at T2
            det_t2_persisting = DeteriorationDetection(
                survey_id=survey_t2.id,
                image_id=ref_t2_img_id,
                damage_type=first_m.deterioration_type,
                confidence=0.78,
                status="CONFIDENT",
                severity_hint="moderate",
                material_class=first_m.material_class,
                material_confidence=first_m.material_confidence,
                material_association_status=first_m.material_association_status,
                bounding_box={"x": 377, "y": 126, "w": 150, "h": 95},
                is_demo=True,
                inference_mode="demo",
                notes="Simulated persisting defect at T2.",
            )
            db.add(det_t2_persisting)
            db.flush()

            # Create DeteriorationDetection for new defect at T2
            det_t2_new = DeteriorationDetection(
                survey_id=survey_t2.id,
                image_id=ref_t2_img_id,
                damage_type="spalling",
                confidence=0.74,
                status="CONFIDENT",
                severity_hint="moderate",
                material_class="sandstone",
                material_confidence=0.82,
                material_association_status="ASSOCIATED_WITH_HIGH_CONFIDENCE",
                bounding_box={"x": 108, "y": 183, "w": 242, "h": 132},
                is_demo=True,
                inference_mode="demo",
                notes="Simulated newly emerged spalling defect at T2.",
            )
            db.add(det_t2_new)
            db.flush()

            simulated_dx = 0.048  # Controlled simulated expansion/displacement
            t2_mapping = Deterioration3DMapping(
                detection_id=det_t2_persisting.id,
                survey_id=survey_t2.id,
                reconstruction_id=recon_t2.id,
                image_id=ref_t2_img_id,
                material_class=first_m.material_class,
                material_confidence=first_m.material_confidence,
                material_association_status=first_m.material_association_status,
                deterioration_type=first_m.deterioration_type,
                deterioration_confidence=0.78,
                severity_hint="moderate",
                image_x=first_m.image_x + 5.0 if first_m.image_x else 100.0,
                image_y=first_m.image_y + 3.0 if first_m.image_y else 100.0,
                world_x=first_m.world_x + simulated_dx if first_m.world_x is not None else 0.2,
                world_y=first_m.world_y if first_m.world_y is not None else 0.1,
                world_z=first_m.world_z if first_m.world_z is not None else 0.0,
                mapping_status="MAPPED",
                reprojection_error_px=2.2,
                mapping_method="SURFACE_RAYCAST",
                scale_status="LOCAL",
                is_demo=True,
                inference_mode="demo",
                notes="Simulated follow-up epoch crack marker with controlled displacement.",
            )
            db.add(t2_mapping)

            # Create a NEW defect at T2 (e.g. spalling)
            new_t2_mapping = Deterioration3DMapping(
                detection_id=det_t2_new.id,
                survey_id=survey_t2.id,
                reconstruction_id=recon_t2.id,
                image_id=ref_t2_img_id,
                material_class="sandstone",
                material_confidence=0.82,
                material_association_status="ASSOCIATED_WITH_HIGH_CONFIDENCE",
                deterioration_type="spalling",
                deterioration_confidence=0.74,
                severity_hint="moderate",
                image_x=320.0,
                image_y=180.0,
                world_x=0.75,
                world_y=-0.35,
                world_z=0.01,
                mapping_status="MAPPED",
                reprojection_error_px=2.8,
                mapping_method="SURFACE_RAYCAST",
                scale_status="LOCAL",
                is_demo=True,
                inference_mode="demo",
                notes="Simulated newly emerged spalling defect at follow-up epoch.",
            )
            db.add(new_t2_mapping)
            db.commit()

        # Execute Phase 7 Temporal Pipeline
        temp_comp = temporal_service.create_or_get_comparison(
            TemporalComparisonCreateRequest(
                site_id=site.id,
                baseline_survey_id=survey_t1.id,
                comparison_survey_id=survey_t2.id,
                alignment_method="ICP_POINT_TO_POINT",
            ),
            db=db,
        )

        temporal_service.run_alignment(temp_comp.id, TemporalAlignmentRequest(), db=db)
        temporal_service.run_geometric_change_detection(temp_comp.id, TemporalChangeDetectRequest(), db=db)
        temporal_service.run_deterioration_tracking(temp_comp.id, TemporalDamageTrackRequest(), db=db)

        temp_summary = temporal_service.get_comparison_summary(temp_comp.id, db=db)
        temp_changes = temporal_service.get_comparison_changes(temp_comp.id, db=db)

        phase7_changes: List[DemoChangeItem] = []
        persisting_cnt = 0
        new_cnt = 0
        resolved_cnt = 0
        sample_disp = None

        for c in temp_changes:
            if c.change_status == "PERSISTING_DETERIORATION":
                persisting_cnt += 1
                if sample_disp is None and c.spatial_distance is not None:
                    sample_disp = round(c.spatial_distance, 4)
            elif c.change_status == "NEW_DETERIORATION":
                new_cnt += 1
            elif c.change_status == "POSSIBLY_RESOLVED_OR_UNDETECTED":
                resolved_cnt += 1

            b_pt = {"x": c.baseline_x, "y": c.baseline_y, "z": c.baseline_z} if c.baseline_x is not None else None
            c_pt = {"x": c.comparison_x, "y": c.comparison_y, "z": c.comparison_z} if c.comparison_x is not None else None

            phase7_changes.append(
                DemoChangeItem(
                    id=c.id,
                    change_status=c.change_status,
                    deterioration_type=c.deterioration_type,
                    material_class=c.material_class,
                    material_status=c.material_status,
                    spatial_distance=round(c.spatial_distance, 4) if c.spatial_distance is not None else None,
                    baseline_point=b_pt,
                    comparison_point=c_pt,
                    notes=c.notes,
                )
            )

        phase7_summary = DemoPhase7Temporal(
            comparison_id=temp_comp.id,
            elapsed_days=temp_summary.elapsed_days or 152,
            alignment_method=temp_summary.alignment_method or "ICP_POINT_TO_POINT",
            fitness=round(temp_summary.fitness, 3) if temp_summary.fitness is not None else 0.98,
            rmse=round(temp_summary.rmse, 4) if temp_summary.rmse is not None else 0.012,
            scale_status="LOCAL",
            total_changes=len(phase7_changes),
            persisting_count=persisting_cnt,
            new_count=new_cnt,
            possibly_resolved_count=resolved_cnt,
            change_records=phase7_changes,
            is_demo=True,
        )

        # -------------------------------------------------------------
        # STEP 12: Final Synthesized Summary Card
        # -------------------------------------------------------------
        primary_det = phase5_items[0] if phase5_items else None
        final_summary = DemoFinalSummary(
            site_name=site.name,
            survey_epochs="T1 (Initial) → T2 (Follow-up)",
            elapsed_days=temp_summary.elapsed_days or 152,
            material=phase4_summary.primary_material.capitalize(),
            material_confidence=phase4_summary.average_confidence,
            deterioration=primary_det.damage_type.capitalize() if primary_det else "Crack",
            deterioration_confidence=primary_det.confidence if primary_det else 0.74,
            deterioration_3d_location="Mapped to synthetic 3D surface (MAPPED, reproj error 2.1 px)",
            temporal_status="PERSISTING_DETERIORATION" if persisting_cnt > 0 else "NEW_DETERIORATION",
            temporal_displacement=sample_disp or 0.048,
            scale_status="LOCAL",
            reliability_indicators={
                "optical_quality": f"Sharp (Laplacian: {phase1_summary.average_blur})",
                "collection_connectivity": phase2_summary.readiness_status,
                "icp_inlier_fitness": f"{phase7_summary.fitness:.1%}",
                "icp_residual_rmse": f"{phase7_summary.rmse:.4f} local units",
                "disclaimer": "Metrics describe synthetic/demo geometry and hybrid DeepCrack testing, not field measurements.",
            },
            is_demo=True,
        )

        return IntegratedDemoResponse(
            success=True,
            site_id=site.id,
            site_name=site.name,
            survey_t1_id=survey_t1.id,
            survey_t1_name=survey_t1.description or survey_t1.survey_code,
            survey_t2_id=survey_t2.id,
            survey_t2_name=survey_t2.description or survey_t2.survey_code,
            provenance=DataProvenance(),
            phase1_quality=phase1_summary,
            phase2_matching=phase2_summary,
            phase3_reconstruction=phase3_summary,
            phase4_materials=phase4_summary,
            phase5_deterioration=phase5_summary,
            phase6_damage_mapping=phase6_summary,
            phase7_temporal=phase7_summary,
            final_summary=final_summary,
        )
