import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Site(Base):
    __tablename__ = "sites"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, index=True)
    location = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    historical_period = Column(String(100), nullable=True)
    primary_material = Column(String(100), nullable=True)  # e.g., "Sandstone", "Brick & Lime Mortar"
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    surveys = relationship("Survey", back_populates="site", cascade="all, delete-orphan")
    temporal_changes = relationship("TemporalChange", back_populates="site", cascade="all, delete-orphan")
    temporal_comparisons = relationship("TemporalComparison", back_populates="site", cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="site", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="site", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="site", cascade="all, delete-orphan")


class Survey(Base):
    __tablename__ = "surveys"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    site_id = Column(String(36), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    survey_code = Column(String(50), nullable=False, index=True)  # e.g., "SRV-2026-001"
    survey_date = Column(DateTime, nullable=False, default=utc_now)
    description = Column(Text, nullable=True)
    operator = Column(String(100), nullable=True)
    camera_info = Column(String(255), nullable=True)  # e.g. "Sony Alpha 7 IV 24-70mm" or "iPhone 15 Pro"
    environmental_info = Column(JSON, nullable=True)  # {"temp_c": 28, "humidity_pct": 65, "rainfall_mm": 0, "uv_index": 7}
    status = Column(String(50), default="created")  # created, uploaded, quality_checked, reconstructed, analyzed

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    site = relationship("Site", back_populates="surveys")
    images = relationship("Image", back_populates="survey", cascade="all, delete-orphan")
    reconstruction = relationship("Reconstruction", back_populates="survey", uselist=False, cascade="all, delete-orphan")
    material_detections = relationship("MaterialDetection", back_populates="survey", cascade="all, delete-orphan")
    deterioration_detections = relationship("DeteriorationDetection", back_populates="survey", cascade="all, delete-orphan")
    damage_locations = relationship("DamageLocation", back_populates="survey", cascade="all, delete-orphan")
    deterioration_3d_mappings = relationship("Deterioration3DMapping", back_populates="survey", cascade="all, delete-orphan")
    reliability_assessments = relationship("ReliabilityAssessment", back_populates="survey", cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="survey", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="survey", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="survey", cascade="all, delete-orphan")
    match_analyses = relationship("ImageMatchAnalysis", back_populates="survey", cascade="all, delete-orphan")
    readiness_analysis = relationship("SurveyReadinessAnalysis", back_populates="survey", uselist=False, cascade="all, delete-orphan")
    baseline_comparisons = relationship("TemporalComparison", foreign_keys="[TemporalComparison.baseline_survey_id]", back_populates="baseline_survey", cascade="all, delete-orphan")
    comparison_comparisons = relationship("TemporalComparison", foreign_keys="[TemporalComparison.comparison_survey_id]", back_populates="comparison_survey", cascade="all, delete-orphan")


class Image(Base):
    __tablename__ = "images"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    survey_id = Column(String(36), ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    relative_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    channels = Column(Integer, default=3)

    # Image Quality Assessment Metrics
    quality_score = Column(Float, nullable=True)  # 0 to 100
    quality_status = Column(String(20), default="pending")  # pass, warning, fail, pending
    blur_score = Column(Float, nullable=True)  # Laplacian variance
    blur_status = Column(String(20), nullable=True)  # pass, fail
    brightness_score = Column(Float, nullable=True)  # Mean grayscale
    brightness_status = Column(String(20), nullable=True)  # pass, fail
    resolution_status = Column(String(20), nullable=True)  # pass, fail
    feature_count = Column(Integer, nullable=True)  # Estimated keypoint count
    quality_details = Column(JSON, nullable=True)  # Detailed dictionary with diagnostics & recommendations

    captured_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    survey = relationship("Survey", back_populates="images")
    material_detections = relationship("MaterialDetection", back_populates="image", cascade="all, delete-orphan")
    deterioration_detections = relationship("DeteriorationDetection", back_populates="image", cascade="all, delete-orphan")
    deterioration_3d_mappings = relationship("Deterioration3DMapping", back_populates="image", cascade="all, delete-orphan")


class Reconstruction(Base):
    __tablename__ = "reconstructions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    survey_id = Column(String(36), ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, unique=True)
    engine = Column(String(50), default="mock")  # colmap, mock, open3d
    engine_version = Column(String(100), nullable=True)
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    current_stage = Column(String(50), default="IDLE")  # PENDING, PREPARING, FEATURE_EXTRACTION, FEATURE_MATCHING, SPARSE_RECONSTRUCTION, DENSE_RECONSTRUCTION, MESH_GENERATION, COMPLETED, FAILED
    progress_percent = Column(Integer, default=0)

    # Output file paths (relative to project root or survey workspace)
    sparse_point_cloud_path = Column(String(500), nullable=True)
    dense_point_cloud_path = Column(String(500), nullable=True)
    mesh_path = Column(String(500), nullable=True)
    texture_path = Column(String(500), nullable=True)
    workspace_path = Column(String(500), nullable=True)
    log_path = Column(String(500), nullable=True)

    # Scientific & Reconstruction Metrics (Strictly recorded from actual engine execution or explicitly marked demo)
    camera_count = Column(Integer, default=0)
    registered_image_count = Column(Integer, default=0)
    point_count = Column(Integer, default=0)
    sparse_point_count = Column(Integer, default=0)
    dense_point_count = Column(Integer, default=0)
    mesh_vertex_count = Column(Integer, default=0)
    mesh_triangle_count = Column(Integer, default=0)
    mean_reprojection_error = Column(Float, nullable=True)

    # Geometry & Visualizations
    camera_poses = Column(JSON, nullable=True)  # List of camera poses: [{"image_id": ..., "pos": [x,y,z], "rot": [qx,qy,qz,qw]}]
    bounding_box = Column(JSON, nullable=True)  # {"min": [x,y,z], "max": [x,y,z], "centroid": [x,y,z], "dimensions": [w,h,d]}
    metadata_json = Column(JSON, nullable=True)  # Detailed metrics, timings per stage, sensor info

    # Execution tracking & safety
    is_demo = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    processing_logs = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    survey = relationship("Survey", back_populates="reconstruction")
    deterioration_3d_mappings = relationship("Deterioration3DMapping", back_populates="reconstruction", cascade="all, delete-orphan")



class MaterialDetection(Base):
    __tablename__ = "material_detections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    survey_id = Column(String(36), ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, index=True)
    image_id = Column(String(36), ForeignKey("images.id", ondelete="SET NULL"), nullable=True, index=True)
    reconstruction_id = Column(String(36), ForeignKey("reconstructions.id", ondelete="SET NULL"), nullable=True, index=True)

    # Material classification (material_class is primary, material_type preserved for backwards compatibility)
    material_class = Column(String(50), nullable=False, default="sandstone")
    material_type = Column(String(50), nullable=False, default="sandstone")

    # ML Inference & Confidence metrics
    confidence = Column(Float, nullable=False)  # 0.0 - 1.0 (model confidence, never certainty)
    status = Column(String(50), default="CONFIDENT")  # CONFIDENT, LOW_CONFIDENCE, REQUIRES_VERIFICATION
    top_k_predictions = Column(JSON, nullable=True)  # [{"material": "sandstone", "confidence": 0.82}, ...]

    # Region / spatial location
    bounding_box = Column(JSON, nullable=True)  # {"x": int, "y": int, "w": int, "h": int}
    region_data = Column(JSON, nullable=True)  # Polygon or crop coordinates for Phase 6 3D projection

    # Model provenance & Research integrity
    model_name = Column(String(100), default="DemoMaterialClassifier")
    model_version = Column(String(50), default="v1.0-demo")
    inference_mode = Column(String(50), default="demo")  # "demo", "real_trained"
    is_demo = Column(Boolean, default=True)
    is_mock = Column(Boolean, default=True)  # Legacy alias
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now)

    # Relationships
    survey = relationship("Survey", back_populates="material_detections")
    image = relationship("Image", back_populates="material_detections")
    deteriorations = relationship("DeteriorationDetection", back_populates="material")



class DeteriorationDetection(Base):
    __tablename__ = "deterioration_detections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    survey_id = Column(String(36), ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, index=True)
    image_id = Column(String(36), ForeignKey("images.id", ondelete="SET NULL"), nullable=True, index=True)
    reconstruction_id = Column(String(36), ForeignKey("reconstructions.id", ondelete="SET NULL"), nullable=True, index=True)
    material_id = Column(String(36), ForeignKey("material_detections.id", ondelete="SET NULL"), nullable=True)

    # Material-aware defect association
    material_class = Column(String(50), nullable=True, default="UNKNOWN")  # brick, sandstone, granite, etc.
    material_type = Column(String(50), nullable=True, default="UNKNOWN")  # Backwards compatibility
    material_confidence = Column(Float, nullable=True)
    material_association_status = Column(String(50), default="MATERIAL_ASSOCIATION_UNAVAILABLE")  # ASSOCIATED, OVERLAPPING_MULTIPLE, MATERIAL_ASSOCIATION_UNAVAILABLE
    candidate_materials = Column(JSON, nullable=True)  # Overlapping material candidates with IoU/coverage

    # Defect classification & model confidence
    damage_type = Column(String(50), nullable=False)  # crack, erosion, spalling, discoloration, biological_growth
    confidence = Column(Float, nullable=False)  # 0.0 - 1.0 (model confidence, never certainty)
    status = Column(String(50), default="CONFIDENT")  # CONFIDENT, LOW_CONFIDENCE, REQUIRES_VERIFICATION
    severity_hint = Column(String(50), nullable=True, default="moderate")  # minor, moderate, severe

    # Spatial representation (object detection box + optional segmentation polygon/mask)
    bounding_box = Column(JSON, nullable=True)  # {"x": int, "y": int, "w": int, "h": int}
    polygon = Column(JSON, nullable=True)  # [{"x": int, "y": int}, ...]
    mask_path = Column(String(500), nullable=True)
    mask_reference = Column(String(500), nullable=True)

    # Model provenance & research integrity
    model_name = Column(String(100), default="DemoDeteriorationDetector")
    model_version = Column(String(50), default="v1.0-demo")
    inference_mode = Column(String(50), default="demo")  # "demo", "real_trained"
    is_demo = Column(Boolean, default=True)
    is_mock = Column(Boolean, default=True)  # Legacy alias
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now)

    # Relationships
    survey = relationship("Survey", back_populates="deterioration_detections")
    image = relationship("Image", back_populates="deterioration_detections")
    material = relationship("MaterialDetection", back_populates="deteriorations")
    damage_location = relationship("DamageLocation", back_populates="deterioration", uselist=False, cascade="all, delete-orphan")
    mapping_3d = relationship("Deterioration3DMapping", back_populates="detection", uselist=False, cascade="all, delete-orphan")



class Deterioration3DMapping(Base):
    __tablename__ = "deterioration_3d_mappings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    detection_id = Column(String(36), ForeignKey("deterioration_detections.id", ondelete="CASCADE"), nullable=False, index=True)
    reconstruction_id = Column(String(36), ForeignKey("reconstructions.id", ondelete="CASCADE"), nullable=False, index=True)
    survey_id = Column(String(36), ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, index=True)
    image_id = Column(String(36), ForeignKey("images.id", ondelete="CASCADE"), nullable=False, index=True)

    # Primary 3D representative point (world space)
    world_x = Column(Float, nullable=True)
    world_y = Column(Float, nullable=True)
    world_z = Column(Float, nullable=True)

    # Primary 2D source pixel coordinates
    image_x = Column(Float, nullable=True)
    image_y = Column(Float, nullable=True)

    # Ray data (JSON lists [x, y, z])
    ray_origin = Column(JSON, nullable=True)
    ray_direction = Column(JSON, nullable=True)
    intersection_distance = Column(Float, nullable=True)

    # Mapping diagnostics & provenance
    mapping_method = Column(String(50), default="MESH_RAYCAST")  # MESH_RAYCAST, POINT_CLOUD_APPROXIMATION
    mapping_status = Column(String(50), default="MAPPED")  # MAPPED, PARTIALLY_MAPPED, NO_SURFACE_INTERSECTION, MAPPING_UNAVAILABLE, MAPPING_REQUIRES_CALIBRATION, MAPPING_REQUIRES_REVIEW
    surface_source = Column(String(50), default="DENSE_MESH")  # DENSE_MESH, SPARSE_MESH, DENSE_POINT_CLOUD, SPARSE_POINT_CLOUD, NONE
    reprojection_error_px = Column(Float, nullable=True)
    scale_status = Column(String(50), default="LOCAL")  # LOCAL, METRIC, UNKNOWN
    sampling_strategy = Column(String(50), default="CENTER_ONLY")  # CENTER_ONLY, BOX_GRID, POLYGON_VERTICES, MASK_SAMPLES
    sample_point_count = Column(Integer, default=1)
    mapped_point_count = Column(Integer, default=1)

    # Propagated deterioration defect info from Phase 5
    deterioration_type = Column(String(50), nullable=False)
    deterioration_confidence = Column(Float, nullable=False)
    severity_hint = Column(String(50), nullable=True, default="moderate")

    # Propagated material info from Phase 4/5
    material_class = Column(String(50), default="UNKNOWN")
    material_confidence = Column(Float, nullable=True)
    material_association_status = Column(String(50), default="MATERIAL_ASSOCIATION_UNAVAILABLE")

    # Research transparency & demo flags
    is_demo = Column(Boolean, default=True)
    inference_mode = Column(String(50), default="demo")
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now)

    # Relationships
    survey = relationship("Survey", back_populates="deterioration_3d_mappings")
    image = relationship("Image", back_populates="deterioration_3d_mappings")
    reconstruction = relationship("Reconstruction", back_populates="deterioration_3d_mappings")
    detection = relationship("DeteriorationDetection", back_populates="mapping_3d")
    points = relationship("Deterioration3DMappingPoint", back_populates="mapping", cascade="all, delete-orphan")
    baseline_change_records = relationship("TemporalChangeRecord", foreign_keys="[TemporalChangeRecord.baseline_mapping_id]", back_populates="baseline_mapping")
    comparison_change_records = relationship("TemporalChangeRecord", foreign_keys="[TemporalChangeRecord.comparison_mapping_id]", back_populates="comparison_mapping")


class Deterioration3DMappingPoint(Base):
    __tablename__ = "deterioration_3d_mapping_points"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    mapping_id = Column(String(36), ForeignKey("deterioration_3d_mappings.id", ondelete="CASCADE"), nullable=False, index=True)
    point_type = Column(String(50), default="center")  # center, box_corner, polygon_vertex, grid_point, mask_sample
    image_x = Column(Float, nullable=False)
    image_y = Column(Float, nullable=False)
    world_x = Column(Float, nullable=True)
    world_y = Column(Float, nullable=True)
    world_z = Column(Float, nullable=True)
    intersection_distance = Column(Float, nullable=True)
    reprojection_error_px = Column(Float, nullable=True)
    mapping_status = Column(String(50), default="MAPPED")
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    mapping = relationship("Deterioration3DMapping", back_populates="points")



class DamageLocation(Base):
    __tablename__ = "damage_locations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    survey_id = Column(String(36), ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, index=True)
    deterioration_id = Column(String(36), ForeignKey("deterioration_detections.id", ondelete="CASCADE"), nullable=False, unique=True)
    coord_x = Column(Float, nullable=False)
    coord_y = Column(Float, nullable=False)
    coord_z = Column(Float, nullable=False)
    normal_x = Column(Float, nullable=True)
    normal_y = Column(Float, nullable=True)
    normal_z = Column(Float, nullable=True)
    surface_area_cm2 = Column(Float, nullable=True)
    length_cm = Column(Float, nullable=True)
    confidence = Column(Float, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    survey = relationship("Survey", back_populates="damage_locations")
    deterioration = relationship("DeteriorationDetection", back_populates="damage_location")


class TemporalChange(Base):
    __tablename__ = "temporal_changes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    site_id = Column(String(36), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    survey_baseline_id = Column(String(36), ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False)
    survey_current_id = Column(String(36), ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False)
    damage_type = Column(String(50), nullable=False)
    material_type = Column(String(50), nullable=True)
    baseline_measurement = Column(Float, nullable=False)  # e.g., 3.2 cm crack length or 14.5 cm2 spalling area
    current_measurement = Column(Float, nullable=False)   # e.g., 4.1 cm crack length
    change_delta = Column(Float, nullable=False)          # +0.9 cm
    change_rate_per_month = Column(Float, nullable=True)
    change_status = Column(String(50), default="progressing")  # progressing, stable, accelerating
    location_3d = Column(JSON, nullable=True)  # {"x": 1.2, "y": 0.5, "z": -0.8}
    registration_rmse = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    site = relationship("Site", back_populates="temporal_changes")


class TemporalComparison(Base):
    __tablename__ = "temporal_comparisons"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    site_id = Column(String(36), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    baseline_survey_id = Column(String(36), ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, index=True)
    comparison_survey_id = Column(String(36), ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, index=True)
    baseline_reconstruction_id = Column(String(36), ForeignKey("reconstructions.id", ondelete="SET NULL"), nullable=True)
    comparison_reconstruction_id = Column(String(36), ForeignKey("reconstructions.id", ondelete="SET NULL"), nullable=True)

    # Alignment / Registration
    alignment_status = Column(String(50), default="PENDING")  # PENDING, ALIGNING, ALIGNED, ALIGNMENT_REQUIRES_REVIEW, FAILED, INVALID_SURVEY_PAIR
    alignment_method = Column(String(50), default="ICP_POINT_TO_POINT")  # IDENTITY, CENTROID_INIT, ICP_POINT_TO_POINT, ICP_POINT_TO_PLANE
    transformation_matrix = Column(JSON, nullable=True)  # 4x4 matrix
    fitness = Column(Float, nullable=True)  # ICP inlier correspondence ratio (0.0 to 1.0)
    rmse = Column(Float, nullable=True)  # ICP inlier RMSE
    correspondence_count = Column(Integer, default=0)

    # Scale & Units
    scale_status = Column(String(50), default="LOCAL")  # LOCAL, METRIC, SCALE_MISMATCH, UNKNOWN

    # Geometric Change Detection
    change_detection_method = Column(String(50), default="POINT_TO_POINT_DISTANCE")  # POINT_TO_POINT_DISTANCE, CLOUD_TO_MESH
    change_threshold = Column(Float, default=0.02)
    damage_matching_distance_threshold = Column(Float, default=0.15)

    # Workflow Status
    status = Column(String(50), default="PENDING")  # PENDING, PREPARING, ALIGNING, CHANGE_DETECTION, DAMAGE_TRACKING, COMPLETED, PARTIALLY_COMPLETED, FAILED, INVALID_SURVEY_PAIR
    elapsed_days = Column(Integer, nullable=True)

    # Summary Statistics
    summary_metrics = Column(JSON, nullable=True)

    # Research transparency & demo flags
    is_demo = Column(Boolean, default=True)
    inference_mode = Column(String(50), default="demo")
    notes = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    site = relationship("Site", back_populates="temporal_comparisons")
    baseline_survey = relationship("Survey", foreign_keys=[baseline_survey_id], back_populates="baseline_comparisons")
    comparison_survey = relationship("Survey", foreign_keys=[comparison_survey_id], back_populates="comparison_comparisons")
    change_records = relationship("TemporalChangeRecord", back_populates="comparison", cascade="all, delete-orphan")


class TemporalChangeRecord(Base):
    __tablename__ = "temporal_change_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    comparison_id = Column(String(36), ForeignKey("temporal_comparisons.id", ondelete="CASCADE"), nullable=False, index=True)
    site_id = Column(String(36), nullable=False, index=True)
    baseline_survey_id = Column(String(36), nullable=False)
    comparison_survey_id = Column(String(36), nullable=False)

    # Temporal defect categorization
    change_status = Column(String(50), nullable=False)  # NEW_DETERIORATION, PERSISTING_DETERIORATION, POSSIBLY_RESOLVED_OR_UNDETECTED, GEOMETRIC_CHANGE_WITHOUT_DETERIORATION_LABEL, NO_SIGNIFICANT_CHANGE, ALIGNMENT_UNCERTAIN
    deterioration_type = Column(String(50), nullable=False)  # crack, erosion, spalling, discoloration, biological_growth, none
    material_class = Column(String(50), default="UNKNOWN")
    material_status = Column(String(50), default="CONSISTENT")  # CONSISTENT, MATERIAL_LABEL_CHANGED, UNKNOWN

    # Mapped 3D locations (in baseline reference frame)
    baseline_mapping_id = Column(String(36), ForeignKey("deterioration_3d_mappings.id", ondelete="SET NULL"), nullable=True)
    comparison_mapping_id = Column(String(36), ForeignKey("deterioration_3d_mappings.id", ondelete="SET NULL"), nullable=True)

    baseline_x = Column(Float, nullable=True)
    baseline_y = Column(Float, nullable=True)
    baseline_z = Column(Float, nullable=True)

    comparison_x = Column(Float, nullable=True)
    comparison_y = Column(Float, nullable=True)
    comparison_z = Column(Float, nullable=True)

    # Metric / distance evaluation
    spatial_distance = Column(Float, nullable=True)  # Distance between matched 3D damage centers
    geometry_distance = Column(Float, nullable=True)  # Local point-to-point / surface distance

    # 2D source image traceability
    baseline_image_id = Column(String(36), nullable=True)
    comparison_image_id = Column(String(36), nullable=True)

    # Confidences & provenance
    baseline_confidence = Column(Float, nullable=True)
    comparison_confidence = Column(Float, nullable=True)
    baseline_material_class = Column(String(50), nullable=True)
    comparison_material_class = Column(String(50), nullable=True)

    scale_status = Column(String(50), default="LOCAL")
    is_demo = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    comparison = relationship("TemporalComparison", back_populates="change_records")
    baseline_mapping = relationship("Deterioration3DMapping", foreign_keys=[baseline_mapping_id], back_populates="baseline_change_records")
    comparison_mapping = relationship("Deterioration3DMapping", foreign_keys=[comparison_mapping_id], back_populates="comparison_change_records")


class ReliabilityAssessment(Base):
    __tablename__ = "reliability_assessments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    survey_id = Column(String(36), ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type = Column(String(50), nullable=False)  # survey, image, damage, temporal_change
    target_id = Column(String(36), nullable=False)
    reliability_score = Column(Float, nullable=False)  # 0.0 to 1.0
    reliability_level = Column(String(50), nullable=False)  # High confidence, Medium confidence, Low confidence
    factors = Column(JSON, nullable=False)  # {"ml_confidence": 0.91, "image_quality": 88.0, "registration_error": 0.02}
    explanation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    survey = relationship("Survey", back_populates="reliability_assessments")


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    site_id = Column(String(36), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    survey_id = Column(String(36), ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, index=True)
    damage_id = Column(String(36), ForeignKey("deterioration_detections.id", ondelete="SET NULL"), nullable=True)
    risk_priority = Column(String(50), nullable=False)  # High priority, Moderate priority, Low priority
    risk_score = Column(Float, nullable=False)  # 0.0 to 100.0
    material_vulnerability = Column(String(50), nullable=False)
    rate_of_progression = Column(String(50), nullable=True)
    governing_factors = Column(JSON, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    site = relationship("Site", back_populates="risk_assessments")
    survey = relationship("Survey", back_populates="risk_assessments")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    site_id = Column(String(36), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    survey_id = Column(String(36), ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_id = Column(String(36), ForeignKey("risk_assessments.id", ondelete="SET NULL"), nullable=True)
    category = Column(String(50), nullable=False)  # monitoring, inspection, imagery, urgent_intervention
    action_text = Column(Text, nullable=False)
    urgency = Column(String(50), nullable=False)  # immediate, within_1_month, routine_quarterly, routine_annual
    basis = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    site = relationship("Site", back_populates="recommendations")
    survey = relationship("Survey", back_populates="recommendations")


class Report(Base):
    __tablename__ = "reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    site_id = Column(String(36), ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    survey_id = Column(String(36), ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    report_type = Column(String(50), default="survey_summary")  # survey_summary, temporal_progression, risk_evaluation
    file_path = Column(String(500), nullable=True)
    summary_content = Column(JSON, nullable=True)
    generated_at = Column(DateTime, default=utc_now)

    # Relationships
    site = relationship("Site", back_populates="reports")
    survey = relationship("Survey", back_populates="reports")


class ImageMatchAnalysis(Base):
    __tablename__ = "image_match_analyses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    survey_id = Column(String(36), ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, index=True)
    image_a_id = Column(String(36), ForeignKey("images.id", ondelete="CASCADE"), nullable=False, index=True)
    image_b_id = Column(String(36), ForeignKey("images.id", ondelete="CASCADE"), nullable=False, index=True)
    keypoints_a = Column(Integer, nullable=False)
    keypoints_b = Column(Integer, nullable=False)
    candidate_matches = Column(Integer, nullable=False)
    good_matches = Column(Integer, nullable=False)
    match_ratio = Column(Float, nullable=False)
    estimated_overlap = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)  # GOOD, WARNING, POOR, INSUFFICIENT_FEATURES
    recommendation = Column(Text, nullable=True)
    algorithm = Column(String(100), default="ORB+BFMatcher(Hamming)+LoweRatio")
    created_at = Column(DateTime, default=utc_now)

    # Relationships
    survey = relationship("Survey", back_populates="match_analyses")
    image_a = relationship("Image", foreign_keys=[image_a_id])
    image_b = relationship("Image", foreign_keys=[image_b_id])


class SurveyReadinessAnalysis(Base):
    __tablename__ = "survey_readiness_analyses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    survey_id = Column(String(36), ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, unique=True)
    images_analyzed = Column(Integer, nullable=False, default=0)
    pairs_analyzed = Column(Integer, nullable=False, default=0)
    good_pairs = Column(Integer, nullable=False, default=0)
    warning_pairs = Column(Integer, nullable=False, default=0)
    poor_pairs = Column(Integer, nullable=False, default=0)
    average_good_matches = Column(Float, nullable=False, default=0.0)
    readiness_status = Column(String(50), nullable=False, default="INSUFFICIENT_IMAGE_CONNECTIVITY")
    isolated_image_ids = Column(JSON, nullable=True)
    weakly_connected_image_ids = Column(JSON, nullable=True)
    connectivity_graph = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    is_heuristic = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    survey = relationship("Survey", back_populates="readiness_analysis")
