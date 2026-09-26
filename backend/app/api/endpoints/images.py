from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.image import ImageRead, ImageUploadResponse
from app.services.image_service import ImageService

router = APIRouter(tags=["Images"])


@router.get("/surveys/{survey_id}/images", response_model=List[ImageRead])
def list_survey_images(survey_id: str, db: Session = Depends(get_db)):
    """List all images associated with a survey."""
    images = ImageService.get_survey_images(db, survey_id)
    results = []
    for img in images:
        img_dto = ImageRead.model_validate(img)
        img_dto.download_url = f"/api/images/{img.id}/file"
        results.append(img_dto)
    return results


@router.post("/surveys/{survey_id}/images/upload", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_images(
    survey_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """
    Upload one or more images (smartphone, DSLR, UAV) for a survey.
    Automatically runs image quality assessment (blur, exposure, resolution, features).
    """
    try:
        saved, failed = await ImageService.upload_survey_images(db, survey_id, files)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))

    read_list = []
    for img in saved:
        dto = ImageRead.model_validate(img)
        dto.download_url = f"/api/images/{img.id}/file"
        read_list.append(dto)

    return ImageUploadResponse(
        uploaded_images=read_list,
        failed_images=failed,
        total_uploaded=len(saved),
        total_failed=len(failed),
    )


@router.get("/images/{image_id}", response_model=ImageRead)
def get_image(image_id: str, db: Session = Depends(get_db)):
    """Get metadata and full quality assessment diagnostics for an image."""
    img = ImageService.get_image_by_id(db, image_id)
    if not img:
        raise HTTPException(status_code=404, detail=f"Image '{image_id}' not found.")
    dto = ImageRead.model_validate(img)
    dto.download_url = f"/api/images/{img.id}/file"
    return dto


@router.get("/images/{image_id}/file")
def get_image_file(image_id: str, db: Session = Depends(get_db)):
    """Safely stream the image file to the client without exposing system disk paths."""
    img = ImageService.get_image_by_id(db, image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Image not found.")

    abs_path = ImageService.get_absolute_file_path(img)
    if not abs_path or not abs_path.exists():
        raise HTTPException(status_code=404, detail="Image file missing from storage.")

    # Determine media type
    suffix = abs_path.suffix.lower()
    media_type = "image/jpeg"
    if suffix == ".png":
        media_type = "image/png"
    elif suffix in (".tif", ".tiff"):
        media_type = "image/tiff"
    elif suffix == ".webp":
        media_type = "image/webp"

    return FileResponse(path=str(abs_path), media_type=media_type, filename=img.filename)


@router.post("/images/{image_id}/reassess", response_model=ImageRead)
def reassess_image_quality(image_id: str, db: Session = Depends(get_db)):
    """Re-run OpenCV image quality checks with updated thresholds."""
    img = ImageService.run_quality_reassessment(db, image_id)
    if not img:
        raise HTTPException(status_code=404, detail="Image not found or missing from storage.")
    dto = ImageRead.model_validate(img)
    dto.download_url = f"/api/images/{img.id}/file"
    return dto


@router.delete("/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(image_id: str, db: Session = Depends(get_db)):
    """Delete image from database and storage."""
    success = ImageService.delete_image(db, image_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Image '{image_id}' not found.")
    return None
