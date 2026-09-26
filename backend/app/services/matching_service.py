from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.heritage import Image, Survey, ImageMatchAnalysis, SurveyReadinessAnalysis
from app.processing.feature_matcher import feature_matcher
from app.services.image_service import ImageService
from app.schemas.matching import (
    PairMatchResponse,
    SurveyReadinessResponse,
    ConnectivityNode,
    ConnectivityEdge,
)


class MatchingService:

    @staticmethod
    def match_two_images(
        db: Session, image_a_id: str, image_b_id: str, save_to_db: bool = True
    ) -> PairMatchResponse:
        """
        Extracts features and performs pairwise matching between two images.
        """
        img_a = db.query(Image).filter(Image.id == image_a_id).first()
        img_b = db.query(Image).filter(Image.id == image_b_id).first()

        if not img_a or not img_b:
            raise ValueError(f"One or both images not found: {image_a_id}, {image_b_id}")

        path_a = ImageService.get_absolute_file_path(img_a)
        path_b = ImageService.get_absolute_file_path(img_b)

        if not path_a or not path_a.exists():
            raise ValueError(f"Image A file missing from storage: {img_a.filename}")
        if not path_b or not path_b.exists():
            raise ValueError(f"Image B file missing from storage: {img_b.filename}")

        kps_a, descs_a, _ = feature_matcher.extract_features(path_a)
        kps_b, descs_b, _ = feature_matcher.extract_features(path_b)

        match_data = feature_matcher.match_descriptors(kps_a, descs_a, kps_b, descs_b)

        db_record = None
        if save_to_db:
            # Check if this pair was already analyzed
            db_record = (
                db.query(ImageMatchAnalysis)
                .filter(
                    ((ImageMatchAnalysis.image_a_id == image_a_id) & (ImageMatchAnalysis.image_b_id == image_b_id))
                    | ((ImageMatchAnalysis.image_a_id == image_b_id) & (ImageMatchAnalysis.image_b_id == image_a_id))
                )
                .first()
            )

            if db_record:
                db_record.keypoints_a = match_data["keypoints_a"]
                db_record.keypoints_b = match_data["keypoints_b"]
                db_record.candidate_matches = match_data["candidate_matches"]
                db_record.good_matches = match_data["good_matches"]
                db_record.match_ratio = match_data["match_ratio"]
                db_record.estimated_overlap = match_data["estimated_overlap"]
                db_record.status = match_data["status"]
                db_record.recommendation = match_data["recommendation"]
            else:
                db_record = ImageMatchAnalysis(
                    survey_id=img_a.survey_id,
                    image_a_id=image_a_id,
                    image_b_id=image_b_id,
                    keypoints_a=match_data["keypoints_a"],
                    keypoints_b=match_data["keypoints_b"],
                    candidate_matches=match_data["candidate_matches"],
                    good_matches=match_data["good_matches"],
                    match_ratio=match_data["match_ratio"],
                    estimated_overlap=match_data["estimated_overlap"],
                    status=match_data["status"],
                    recommendation=match_data["recommendation"],
                    algorithm="ORB+BFMatcher(Hamming)+LoweRatio(0.75)",
                )
                db.add(db_record)

            db.commit()
            db.refresh(db_record)

        return PairMatchResponse(
            id=db_record.id if db_record else None,
            survey_id=img_a.survey_id,
            image_a_id=image_a_id,
            image_b_id=image_b_id,
            image_a_filename=img_a.filename,
            image_b_filename=img_b.filename,
            keypoints_a=match_data["keypoints_a"],
            keypoints_b=match_data["keypoints_b"],
            candidate_matches=match_data["candidate_matches"],
            good_matches=match_data["good_matches"],
            match_ratio=match_data["match_ratio"],
            estimated_overlap=match_data["estimated_overlap"],
            status=match_data["status"],
            recommendation=match_data["recommendation"],
            algorithm="ORB+BFMatcher(Hamming)+LoweRatio(0.75)",
            created_at=db_record.created_at if db_record else None,
        )

    @staticmethod
    def analyze_survey_collection(db: Session, survey_id: str) -> SurveyReadinessResponse:
        """
        Extracts features for all images in the survey, matches pairs, builds connectivity graph,
        and saves results to database.
        """
        survey = db.query(Survey).filter(Survey.id == survey_id).first()
        if not survey:
            raise ValueError(f"Survey with id {survey_id} does not exist.")

        images = db.query(Image).filter(Image.survey_id == survey_id).all()
        if not images:
            raise ValueError(f"Survey '{survey_id}' contains no uploaded images.")

        images_info = []
        for img in images:
            abs_path = ImageService.get_absolute_file_path(img)
            if abs_path and abs_path.exists():
                images_info.append({"id": img.id, "filename": img.filename, "path": abs_path})

        if not images_info:
            raise ValueError("None of the survey image files exist on disk storage.")

        # Execute survey-level feature matching & graph analysis
        analysis_result = feature_matcher.analyze_survey_collection(images_info)

        # Clear previously recorded pair matches for this survey to keep database fresh
        db.query(ImageMatchAnalysis).filter(ImageMatchAnalysis.survey_id == survey_id).delete()

        # Save pair match results
        for p in analysis_result["pair_results"]:
            match_entry = ImageMatchAnalysis(
                survey_id=survey_id,
                image_a_id=p["image_a_id"],
                image_b_id=p["image_b_id"],
                keypoints_a=p["keypoints_a"],
                keypoints_b=p["keypoints_b"],
                candidate_matches=p["candidate_matches"],
                good_matches=p["good_matches"],
                match_ratio=p["match_ratio"],
                estimated_overlap=p["estimated_overlap"],
                status=p["status"],
                recommendation=p["recommendation"],
                algorithm="ORB+BFMatcher(Hamming)+LoweRatio(0.75)",
            )
            db.add(match_entry)

        # Save or update SurveyReadinessAnalysis record
        readiness_record = (
            db.query(SurveyReadinessAnalysis)
            .filter(SurveyReadinessAnalysis.survey_id == survey_id)
            .first()
        )

        if readiness_record:
            readiness_record.images_analyzed = analysis_result["images_analyzed"]
            readiness_record.pairs_analyzed = analysis_result["pairs_analyzed"]
            readiness_record.good_pairs = analysis_result["good_pairs"]
            readiness_record.warning_pairs = analysis_result["warning_pairs"]
            readiness_record.poor_pairs = analysis_result["poor_pairs"]
            readiness_record.average_good_matches = analysis_result["average_good_matches"]
            readiness_record.readiness_status = analysis_result["readiness_status"]
            readiness_record.isolated_image_ids = analysis_result["isolated_image_ids"]
            readiness_record.weakly_connected_image_ids = analysis_result["weakly_connected_image_ids"]
            readiness_record.connectivity_graph = {
                "nodes": analysis_result["connectivity_nodes"],
                "edges": analysis_result["connectivity_edges"],
            }
            readiness_record.recommendations = analysis_result["recommendations"]
        else:
            readiness_record = SurveyReadinessAnalysis(
                survey_id=survey_id,
                images_analyzed=analysis_result["images_analyzed"],
                pairs_analyzed=analysis_result["pairs_analyzed"],
                good_pairs=analysis_result["good_pairs"],
                warning_pairs=analysis_result["warning_pairs"],
                poor_pairs=analysis_result["poor_pairs"],
                average_good_matches=analysis_result["average_good_matches"],
                readiness_status=analysis_result["readiness_status"],
                isolated_image_ids=analysis_result["isolated_image_ids"],
                weakly_connected_image_ids=analysis_result["weakly_connected_image_ids"],
                connectivity_graph={
                    "nodes": analysis_result["connectivity_nodes"],
                    "edges": analysis_result["connectivity_edges"],
                },
                recommendations=analysis_result["recommendations"],
                is_heuristic=True,
            )
            db.add(readiness_record)

        db.commit()
        db.refresh(readiness_record)

        nodes = [ConnectivityNode(**n) for n in analysis_result["connectivity_nodes"]]
        edges = [ConnectivityEdge(**e) for e in analysis_result["connectivity_edges"]]

        return SurveyReadinessResponse(
            survey_id=survey_id,
            images_analyzed=analysis_result["images_analyzed"],
            pairs_analyzed=analysis_result["pairs_analyzed"],
            good_pairs=analysis_result["good_pairs"],
            warning_pairs=analysis_result["warning_pairs"],
            poor_pairs=analysis_result["poor_pairs"],
            average_good_matches=analysis_result["average_good_matches"],
            readiness_status=analysis_result["readiness_status"],
            isolated_image_ids=analysis_result["isolated_image_ids"],
            weakly_connected_image_ids=analysis_result["weakly_connected_image_ids"],
            connectivity_nodes=nodes,
            connectivity_edges=edges,
            recommendations=analysis_result["recommendations"],
            is_heuristic=True,
            updated_at=readiness_record.updated_at,
        )

    @staticmethod
    def get_survey_readiness(db: Session, survey_id: str) -> Optional[SurveyReadinessResponse]:
        """
        Retrieves the latest cached readiness analysis for a survey.
        If none exists, executes on-the-fly analysis.
        """
        record = (
            db.query(SurveyReadinessAnalysis)
            .filter(SurveyReadinessAnalysis.survey_id == survey_id)
            .first()
        )
        if not record:
            # Check if survey has images
            img_count = db.query(Image).filter(Image.survey_id == survey_id).count()
            if img_count >= 2:
                return MatchingService.analyze_survey_collection(db, survey_id)
            return None

        graph = record.connectivity_graph or {}
        raw_nodes = graph.get("nodes", [])
        raw_edges = graph.get("edges", [])

        nodes = [ConnectivityNode(**n) for n in raw_nodes]
        edges = [ConnectivityEdge(**e) for e in raw_edges]

        return SurveyReadinessResponse(
            survey_id=record.survey_id,
            images_analyzed=record.images_analyzed,
            pairs_analyzed=record.pairs_analyzed,
            good_pairs=record.good_pairs,
            warning_pairs=record.warning_pairs,
            poor_pairs=record.poor_pairs,
            average_good_matches=record.average_good_matches,
            readiness_status=record.readiness_status,
            isolated_image_ids=record.isolated_image_ids or [],
            weakly_connected_image_ids=record.weakly_connected_image_ids or [],
            connectivity_nodes=nodes,
            connectivity_edges=edges,
            recommendations=record.recommendations or [],
            is_heuristic=record.is_heuristic,
            updated_at=record.updated_at,
        )

    @staticmethod
    def get_survey_pair_matches(
        db: Session, survey_id: str, status_filter: Optional[str] = None
    ) -> List[PairMatchResponse]:
        """
        Returns analyzed pairs for a survey, optionally filtered by status (GOOD, WARNING, POOR).
        """
        query = db.query(ImageMatchAnalysis).filter(ImageMatchAnalysis.survey_id == survey_id)
        if status_filter:
            query = query.filter(ImageMatchAnalysis.status == status_filter.upper())

        matches = query.order_by(ImageMatchAnalysis.good_matches.desc()).all()
        results = []

        # Pre-fetch image filenames for fast lookup
        images = db.query(Image).filter(Image.survey_id == survey_id).all()
        id_to_name = {img.id: img.filename for img in images}

        for m in matches:
            results.append(
                PairMatchResponse(
                    id=m.id,
                    survey_id=m.survey_id,
                    image_a_id=m.image_a_id,
                    image_b_id=m.image_b_id,
                    image_a_filename=id_to_name.get(m.image_a_id, "Unknown"),
                    image_b_filename=id_to_name.get(m.image_b_id, "Unknown"),
                    keypoints_a=m.keypoints_a,
                    keypoints_b=m.keypoints_b,
                    candidate_matches=m.candidate_matches,
                    good_matches=m.good_matches,
                    match_ratio=m.match_ratio,
                    estimated_overlap=m.estimated_overlap,
                    status=m.status,
                    recommendation=m.recommendation,
                    algorithm=m.algorithm,
                    created_at=m.created_at,
                )
            )
        return results
