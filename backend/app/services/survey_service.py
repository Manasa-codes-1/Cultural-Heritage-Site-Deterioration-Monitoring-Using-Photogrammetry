from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.heritage import Survey, Image, Site
from app.schemas.survey import SurveyCreate, SurveyUpdate


class SurveyService:

    @staticmethod
    def get_surveys(db: Session, site_id: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Survey]:
        query = db.query(Survey)
        if site_id:
            query = query.filter(Survey.site_id == site_id)
        surveys = query.order_by(Survey.survey_date.desc()).offset(skip).limit(limit).all()
        for survey in surveys:
            survey.image_count = db.query(func.count(Image.id)).filter(Image.survey_id == survey.id).scalar() or 0
            avg_q = db.query(func.avg(Image.quality_score)).filter(Image.survey_id == survey.id).scalar()
            survey.average_quality_score = round(float(avg_q), 1) if avg_q is not None else None
        return surveys

    @staticmethod
    def get_survey_by_id(db: Session, survey_id: str) -> Optional[Survey]:
        survey = db.query(Survey).filter(Survey.id == survey_id).first()
        if survey:
            survey.image_count = db.query(func.count(Image.id)).filter(Image.survey_id == survey.id).scalar() or 0
            avg_q = db.query(func.avg(Image.quality_score)).filter(Image.survey_id == survey.id).scalar()
            survey.average_quality_score = round(float(avg_q), 1) if avg_q is not None else None
        return survey

    @staticmethod
    def create_survey(db: Session, survey_in: SurveyCreate) -> Optional[Survey]:
        # Validate that site exists
        site = db.query(Site).filter(Site.id == survey_in.site_id).first()
        if not site:
            return None

        db_survey = Survey(
            site_id=survey_in.site_id,
            survey_code=survey_in.survey_code,
            survey_date=survey_in.survey_date,
            description=survey_in.description,
            operator=survey_in.operator,
            camera_info=survey_in.camera_info,
            environmental_info=survey_in.environmental_info,
            status="created",
        )
        db.add(db_survey)
        db.commit()
        db.refresh(db_survey)
        db_survey.image_count = 0
        db_survey.average_quality_score = None
        return db_survey

    @staticmethod
    def update_survey(db: Session, survey_id: str, survey_in: SurveyUpdate) -> Optional[Survey]:
        survey = db.query(Survey).filter(Survey.id == survey_id).first()
        if not survey:
            return None

        update_data = survey_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(survey, field, value)

        db.commit()
        db.refresh(survey)
        survey.image_count = db.query(func.count(Image.id)).filter(Image.survey_id == survey.id).scalar() or 0
        avg_q = db.query(func.avg(Image.quality_score)).filter(Image.survey_id == survey.id).scalar()
        survey.average_quality_score = round(float(avg_q), 1) if avg_q is not None else None
        return survey

    @staticmethod
    def delete_survey(db: Session, survey_id: str) -> bool:
        survey = db.query(Survey).filter(Survey.id == survey_id).first()
        if not survey:
            return False
        db.delete(survey)
        db.commit()
        return True
