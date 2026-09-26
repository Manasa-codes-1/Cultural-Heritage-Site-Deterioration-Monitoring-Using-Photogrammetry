import os
import shutil
import uuid
from pathlib import Path
from typing import List, Tuple, Optional
from fastapi import UploadFile
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.heritage import Image, Survey
from app.processing.quality_assessor import quality_assessor


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}


class ImageService:

    @staticmethod
    def get_survey_images(db: Session, survey_id: str) -> List[Image]:
        return db.query(Image).filter(Image.survey_id == survey_id).order_by(Image.created_at.asc()).all()

    @staticmethod
    def get_image_by_id(db: Session, image_id: str) -> Optional[Image]:
        return db.query(Image).filter(Image.id == image_id).first()

    @staticmethod
    async def upload_survey_images(
        db: Session, survey_id: str, files: List[UploadFile]
    ) -> Tuple[List[Image], List[dict]]:
        """
        Saves uploaded images to the survey's disk folder, immediately runs image quality
        assessment, and records metadata in the database.
        """
        survey = db.query(Survey).filter(Survey.id == survey_id).first()
        if not survey:
            raise ValueError(f"Survey with id {survey_id} does not exist.")

        # Survey image directory: data/surveys/{survey_id}/images
        survey_img_dir = settings.UPLOAD_DIR / survey_id / "images"
        survey_img_dir.mkdir(parents=True, exist_ok=True)

        saved_images: List[Image] = []
        failed_files: List[dict] = []

        for file in files:
            orig_filename = file.filename or "unnamed.jpg"
            ext = Path(orig_filename).suffix.lower()

            if ext not in ALLOWED_EXTENSIONS:
                failed_files.append({
                    "filename": orig_filename,
                    "reason": f"Unsupported extension '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
                })
                continue

            # Generate unique safe filename
            unique_name = f"{uuid.uuid4().hex[:12]}_{orig_filename}"
            target_path = survey_img_dir / unique_name

            try:
                # Write to disk
                with open(target_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)

                file_size = target_path.stat().st_size

                # Run immediate OpenCV Image Quality Assessment
                assessment = quality_assessor.assess_file(target_path)

                # Store relative path relative to settings.DATA_DIR for portability
                rel_path = str(target_path.relative_to(settings.DATA_DIR)).replace("\\", "/")

                img_record = Image(
                    survey_id=survey_id,
                    filename=orig_filename,
                    relative_path=rel_path,
                    file_size_bytes=file_size,
                    width=assessment.get("width"),
                    height=assessment.get("height"),
                    channels=assessment.get("channels", 3),
                    quality_score=assessment.get("quality_score"),
                    quality_status=assessment.get("quality_status", "pending"),
                    blur_score=assessment.get("blur", {}).get("score"),
                    blur_status=assessment.get("blur", {}).get("status"),
                    brightness_score=assessment.get("brightness", {}).get("score"),
                    brightness_status=assessment.get("brightness", {}).get("status"),
                    resolution_status=assessment.get("resolution", {}).get("status"),
                    feature_count=assessment.get("features", {}).get("count"),
                    quality_details=assessment,
                )

                db.add(img_record)
                db.commit()
                db.refresh(img_record)
                saved_images.append(img_record)

            except Exception as e:
                # Clean up if partially written
                if target_path.exists():
                    target_path.unlink()
                failed_files.append({
                    "filename": orig_filename,
                    "reason": f"Processing error: {str(e)}"
                })

        # Update survey status
        if saved_images and survey.status == "created":
            survey.status = "images_uploaded"
            db.commit()

        return saved_images, failed_files

    @staticmethod
    def get_absolute_file_path(image: Image) -> Optional[Path]:
        """Resolves the safe absolute path for file streaming/download."""
        abs_path = settings.DATA_DIR / image.relative_path
        if abs_path.exists() and abs_path.is_file():
            return abs_path
        return None

    @staticmethod
    def run_quality_reassessment(db: Session, image_id: str) -> Optional[Image]:
        """Manually rerun quality assessment for a specific image."""
        img = db.query(Image).filter(Image.id == image_id).first()
        if not img:
            return None

        abs_path = ImageService.get_absolute_file_path(img)
        if not abs_path:
            return None

        assessment = quality_assessor.assess_file(abs_path)
        img.width = assessment.get("width")
        img.height = assessment.get("height")
        img.quality_score = assessment.get("quality_score")
        img.quality_status = assessment.get("quality_status")
        img.blur_score = assessment.get("blur", {}).get("score")
        img.blur_status = assessment.get("blur", {}).get("status")
        img.brightness_score = assessment.get("brightness", {}).get("score")
        img.brightness_status = assessment.get("brightness", {}).get("status")
        img.resolution_status = assessment.get("resolution", {}).get("status")
        img.feature_count = assessment.get("features", {}).get("count")
        img.quality_details = assessment

        db.commit()
        db.refresh(img)
        return img

    @staticmethod
    def delete_image(db: Session, image_id: str) -> bool:
        img = db.query(Image).filter(Image.id == image_id).first()
        if not img:
            return False

        abs_path = ImageService.get_absolute_file_path(img)
        if abs_path and abs_path.exists():
            try:
                abs_path.unlink()
            except OSError:
                pass

        db.delete(img)
        db.commit()
        return True
