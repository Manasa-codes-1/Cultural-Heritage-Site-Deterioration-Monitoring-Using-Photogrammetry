"""
Seed demonstration script for Cultural Heritage Deterioration Monitoring.
Creates an initial heritage monument and a sample survey epoch for immediate evaluation.
"""
import sys
from pathlib import Path

# Add backend to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.database import SessionLocal, Base, engine
from app.models.heritage import Site, Survey, Image
from datetime import datetime, timezone
import numpy as np
import cv2

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Check if sites exist
        existing = db.query(Site).first()
        if existing:
            print(f"[+] Database already contains sites: {existing.name}")
            return

        print("[*] Seeding sample heritage site: Amber Fort Outer Rampart...")
        site = Site(
            name="Amber Fort Outer Rampart",
            location="Jaipur, Rajasthan, India",
            description="Massive 16th-century fortification constructed from local yellow and red sandstone with lime mortar pointing. Subject to intense thermal cycles, solar radiation, and monsoonal rainfall.",
            historical_period="16th Century (Raja Man Singh I)",
            primary_material="Sandstone & Lime Mortar",
            latitude=26.9855,
            longitude=75.8513,
        )
        db.add(site)
        db.commit()
        db.refresh(site)

        print(f"[+] Created site ID: {site.id}")

        print("[*] Creating baseline survey epoch AMB-2026-BASELINE...")
        survey = Survey(
            site_id=site.id,
            survey_code="AMB-2026-BASELINE",
            survey_date=datetime(2026, 2, 10, 10, 30, tzinfo=timezone.utc),
            description="Initial baseline photogrammetric capture of the southeastern bastion masonry facade.",
            operator="Heritage Conservation Field Team",
            camera_info="Sony Alpha 7 IV, 35mm f/2.8 Prime (Smartphone backup: iPhone 15 Pro)",
            environmental_info={
                "temp_c": 32.4,
                "humidity_pct": 38.0,
                "rainfall_mm": 0.0,
                "uv_index": 7.5,
                "notes": "Clear morning skies, low diffuse shadows."
            },
            status="images_uploaded",
        )
        db.add(survey)
        db.commit()
        db.refresh(survey)

        print(f"[+] Created survey ID: {survey.id}")

        # Generate 3 synthetic demo images to demonstrate immediate optical assessment
        from app.core.config import settings
        from app.processing.quality_assessor import quality_assessor

        survey_img_dir = settings.UPLOAD_DIR / survey.id / "images"
        survey_img_dir.mkdir(parents=True, exist_ok=True)

        samples = [
            ("bastion_facade_01.jpg", "sharp"),
            ("bastion_facade_02.jpg", "sharp"),
            ("bastion_facade_03_blur.jpg", "blur"),
        ]

        for fname, condition in samples:
            target_path = survey_img_dir / fname
            
            # Create synthetic textured stone masonry image (1200x900)
            img = np.zeros((900, 1200, 3), dtype=np.uint8)
            # Stone texture simulation: noise + mortar lines
            noise = np.random.randint(140, 200, (900, 1200, 3), dtype=np.uint8)
            img = cv2.addWeighted(img, 0.2, noise, 0.8, 0)
            
            # Add masonry mortar grid
            for y in range(0, 900, 100):
                cv2.line(img, (0, y), (1200, y), (110, 110, 110), 3)
            for x in range(0, 1200, 200):
                cv2.line(img, (x, 0), (x, 900), (110, 110, 110), 3)

            if condition == "blur":
                # Apply heavy Gaussian blur to test Laplacian blur detector
                img = cv2.GaussianBlur(img, (31, 31), 10.0)

            cv2.imwrite(str(target_path), img)
            assessment = quality_assessor.assess_file(target_path)
            rel_path = str(target_path.relative_to(settings.DATA_DIR)).replace("\\", "/")

            db_img = Image(
                survey_id=survey.id,
                filename=fname,
                relative_path=rel_path,
                file_size_bytes=target_path.stat().st_size,
                width=assessment.get("width"),
                height=assessment.get("height"),
                channels=3,
                quality_score=assessment.get("quality_score"),
                quality_status=assessment.get("quality_status"),
                blur_score=assessment.get("blur", {}).get("score"),
                blur_status=assessment.get("blur", {}).get("status"),
                brightness_score=assessment.get("brightness", {}).get("score"),
                brightness_status=assessment.get("brightness", {}).get("status"),
                resolution_status=assessment.get("resolution", {}).get("status"),
                feature_count=assessment.get("features", {}).get("count"),
                quality_details=assessment,
            )
            db.add(db_img)

        db.commit()
        print("[+] Seed completed successfully with 3 demonstration survey images.")

    finally:
        db.close()

if __name__ == "__main__":
    seed()
