from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.heritage import Site, Survey
from app.schemas.site import SiteCreate, SiteUpdate


class SiteService:

    @staticmethod
    def get_sites(db: Session, skip: int = 0, limit: int = 100) -> List[Site]:
        sites = db.query(Site).order_by(Site.created_at.desc()).offset(skip).limit(limit).all()
        # Populate survey_count
        for site in sites:
            site.survey_count = db.query(func.count(Survey.id)).filter(Survey.site_id == site.id).scalar() or 0
        return sites

    @staticmethod
    def get_site_by_id(db: Session, site_id: str) -> Optional[Site]:
        site = db.query(Site).filter(Site.id == site_id).first()
        if site:
            site.survey_count = db.query(func.count(Survey.id)).filter(Survey.site_id == site.id).scalar() or 0
        return site

    @staticmethod
    def create_site(db: Session, site_in: SiteCreate) -> Site:
        db_site = Site(
            name=site_in.name,
            location=site_in.location,
            description=site_in.description,
            historical_period=site_in.historical_period,
            primary_material=site_in.primary_material,
            latitude=site_in.latitude,
            longitude=site_in.longitude,
        )
        db.add(db_site)
        db.commit()
        db.refresh(db_site)
        db_site.survey_count = 0
        return db_site

    @staticmethod
    def update_site(db: Session, site_id: str, site_in: SiteUpdate) -> Optional[Site]:
        site = db.query(Site).filter(Site.id == site_id).first()
        if not site:
            return None

        update_data = site_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(site, field, value)

        db.commit()
        db.refresh(site)
        site.survey_count = db.query(func.count(Survey.id)).filter(Survey.site_id == site.id).scalar() or 0
        return site

    @staticmethod
    def delete_site(db: Session, site_id: str) -> bool:
        site = db.query(Site).filter(Site.id == site_id).first()
        if not site:
            return False
        db.delete(site)
        db.commit()
        return True
