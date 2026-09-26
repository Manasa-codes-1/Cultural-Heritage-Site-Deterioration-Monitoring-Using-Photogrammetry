from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.site import SiteCreate, SiteUpdate, SiteRead
from app.services.site_service import SiteService

router = APIRouter(prefix="/sites", tags=["Sites"])


@router.get("", response_model=List[SiteRead])
def list_sites(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve list of registered cultural heritage sites."""
    return SiteService.get_sites(db, skip=skip, limit=limit)


@router.post("", response_model=SiteRead, status_code=status.HTTP_201_CREATED)
def create_site(site_in: SiteCreate, db: Session = Depends(get_db)):
    """Register a new cultural heritage site."""
    return SiteService.create_site(db, site_in)


@router.get("/{site_id}", response_model=SiteRead)
def get_site(site_id: str, db: Session = Depends(get_db)):
    """Retrieve detailed information for a specific heritage site."""
    site = SiteService.get_site_by_id(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site '{site_id}' not found.")
    return site


@router.put("/{site_id}", response_model=SiteRead)
def update_site(site_id: str, site_in: SiteUpdate, db: Session = Depends(get_db)):
    """Update heritage site details."""
    site = SiteService.update_site(db, site_id, site_in)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site '{site_id}' not found.")
    return site


@router.delete("/{site_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_site(site_id: str, db: Session = Depends(get_db)):
    """Delete a heritage site and its cascading surveys/data."""
    success = SiteService.delete_site(db, site_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Site '{site_id}' not found.")
    return None
