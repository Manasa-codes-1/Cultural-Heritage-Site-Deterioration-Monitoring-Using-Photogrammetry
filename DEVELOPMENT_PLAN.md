# Heritage Deterioration Monitoring Using Photogrammetry
## Comprehensive Development & Research Plan

### 1. Executive Summary & Project Vision
This project implements a non-contact, low-cost, material-aware cultural heritage deterioration monitoring system. The core scientific insight is:

$$\text{Material} \longrightarrow \text{Deterioration} \longrightarrow \text{3D Location} \longrightarrow \text{Temporal Change} \longrightarrow \text{Reliability} \longrightarrow \text{Risk} \longrightarrow \text{Recommendation}$$

Rather than treating deterioration (e.g., cracks, spalling, erosion) as isolated 2D image detections, the system anchors detections onto reconstructed 3D surface geometry, contextualizes them with the substrate building material (e.g., brick vs. sandstone vs. mortar), tracks changes across multi-temporal surveys, quantifies measurement uncertainty, and derives actionable conservation risk priorities.

---

### 2. Multi-Phase Implementation Roadmap

#### Phase 1: Foundation & Core Infrastructure (COMPLETED & VERIFIED)
- **Objective:** Establish production-grade backend, frontend, database schema, and project structure.
- **Deliverables:**
  - FastAPI modular application structure with Pydantic v2 schemas and SQLAlchemy ORM.
  - SQLite database for local, zero-cost deployment (readily migratable to PostgreSQL).
  - React + TypeScript + Vite frontend with research-grade UI structure.
  - CRUD for Sites and Surveys.
  - Multi-image upload workflow with disk storage abstraction.
  - Initial OpenCV image quality assessment module (blur, brightness, resolution, validity).
  - Health check and environment inspection endpoints.

#### Phase 2: Advanced Image Quality Assessment & Photogrammetric Collection Readiness (COMPLETED & VERIFIED)
- **Objective:** Evaluate whether a collection of images is suitable for photogrammetric reconstruction by analyzing pairwise feature correspondence and viewpoint connectivity topology.
- **Methodology & Algorithms:**
  - **Feature Extraction:** OpenCV ORB (Oriented FAST and Rotated BRIEF) invariant keypoint detection and binary descriptor extraction (`nfeatures=1500`, 8 pyramid levels).
  - **Descriptor Matching:** Brute-Force Matcher with Hamming distance norm (`cv2.NORM_HAMMING`) and k-nearest neighbors ($k=2$).
  - **Match Filtering:** Lowe's ratio test ($d_{\text{best}} < 0.75 \times d_{\text{second}}$) to eliminate ambiguous false matches.
  - **Pair Selection Strategy:** Full exhaustive combinations $\frac{N(N-1)}{2}$ for $N \le 12$; contiguous sequential ($i \leftrightarrow i+1$) and stride neighbors ($i \leftrightarrow i+2, i+3$) up to configurable upper limit (`max_pairs=60`) to avoid combinatorial explosion on laptop CPUs.
  - **Collection Connectivity Graph:** Images mapped as vertices $V$; robust matches ($G \ge 30$) mapped as undirected edges $E$. Viewpoint degrees identify well-connected ($\text{deg} \ge 2$), weakly connected ($\text{deg}=1$), and isolated ($\text{deg}=0$) camera poses.
  - **Readiness Classification:** `READY`, `READY_WITH_WARNINGS`, `INSUFFICIENT_IMAGE_CONNECTIVITY`, `RECAPTURE_REQUIRED`.
  - **Configurable Heuristic Thresholds:**
    - `MATCHING_MAX_FEATURES`: 1500
    - `MATCHING_RATIO_THRESH`: 0.75
    - `MATCHING_MIN_GOOD_MATCHES`: 30 (for `GOOD` status)
    - `MATCHING_WARN_GOOD_MATCHES`: 15 (for `WARNING` status)
    - `MATCHING_MIN_KEYPOINTS`: 100
    - `MATCHING_MAX_PAIRS_PER_SURVEY`: 60
    - `MATCHING_IMAGE_MAX_DIM`: 1280 px
- **Differences Clarified:**
  - *Individual Quality vs. Pairwise Matching:* Individual IQA verifies optical clarity (blur, exposure, resolution, keypoint density) of single files; pairwise matching verifies spatial overlap and geometric correspondence between differing camera viewpoints.
  - *Readiness Analysis vs. SfM Reconstruction:* Readiness analysis is a lightweight 2D preprocessing check on feature connectivity; actual photogrammetry performs iterative bundle adjustment, camera pose estimation, and epipolar geometry triangulation (Phase 3).
- **Research Note:**
  > *"This module provides an engineering-level image-quality and feature-correspondence assessment intended to support photogrammetric preprocessing. Its thresholds are configurable heuristics and should not be interpreted as universally validated photogrammetry quality criteria."*

#### Phase 3: Photogrammetry & 3D Reconstruction Layer (COMPLETED & VERIFIED)
- **Objective:** Convert multi-view 2D surveys into registered 3D spatial representations with strict research transparency.
- **Deliverables & Architecture:**
  - **Pluggable Engine Abstraction:** `PhotogrammetryEngine` base class defining `check_availability()`, `run_reconstruction()`, and structured return schemas.
  - **Real COLMAP Engine (`ColmapEngine`):**
    - Windows-safe subprocess pipeline with granular progress tracking: Feature Extraction (`feature_extractor`), Exhaustive Matching (`exhaustive_matcher`), Sparse SfM (`mapper`), Image Undistortion (`image_undistorter`), Dense Stereo (`patch_match_stereo`), and Poisson Meshing (`poisson_mesher`).
    - Robust hardware detection: queries binary version and CUDA GPU acceleration support; gracefully falls back to CPU processing and logs limitations.
  - **Deterministic Procedural Mock Engine (`MockPhotogrammetryEngine`):**
    - Offline/CPU fallback producing authentic synthetic sandstone ashlar masonry wall geometries with mortar joints and relief.
    - Generates sparse point clouds (`sparse.ply`), dense point clouds (`dense.ply`), and 3D surface meshes (`mesh.ply`, `mesh.obj`).
    - Produces realistic orbital camera trajectories and accurately computed bounding boxes ($X \times Y \times Z$ in meters).
    - Strictly sets `is_demo = True` and prepends academic disclaimers to execution logs.
  - **Open3D Geometry Processor (`PointCloudProcessor`):**
    - Analyzes point clouds and meshes for exact point/vertex/face counts, centroids, bounding boxes, and volumetric densities ($\text{pts/m}^3$).
    - Voxel grid downsampling, statistical outlier removal, and surface normal estimation.
  - **Asynchronous Service & Database Layer:**
    - Background task reconstruction trigger (`POST /api/photogrammetry/surveys/{survey_id}/reconstruct`).
    - Granular stage tracking (`PREPARING` $\to$ `FEATURE_EXTRACTION` $\to$ `FEATURE_MATCHING` $\to$ `SPARSE_RECONSTRUCTION` $\to$ `DENSE_RECONSTRUCTION` $\to$ `MESH_GENERATION` $\to$ `COMPLETED`).
    - Lightweight status polling endpoint and secure 3D file streaming (`GET /api/photogrammetry/reconstructions/{id}/model`).
  - **Three.js Interactive 3D WebGL Viewer (`ModelViewer3D` & `PhotogrammetryPage`):**
    - OrbitControls (rotate, pan, zoom, damping), lighting, ground grid, and orientation axes.
    - Shading modes: Shaded Surface Mesh, Wireframe Triangles, Dense Point Cloud, and Hybrid.
    - Camera frustum markers showing registered viewpoints in 3D space.
    - View presets: Front, Isometric, Top, Side, and Reset.
    - Prominent Research Safety Banner distinguishing certified photogrammetric models from synthetic demo models.


#### Phase 4: Material Classification Pipeline (COMPLETED & VERIFIED)
- **Objective:** Identify heritage substrates to inform deterioration risk with complete research integrity and transparency.
- **Deliverables & Architecture:**
  - **Configurable Material Registry (`material_config.py`):**
    - JSON-persisted taxonomy (`data/config/material_classes.json`) initialized with baseline classes (`sandstone`, `granite`, `brick`, `lime_mortar`, `other`).
    - Full CRUD capability: add custom site substrates, toggle enabled/disabled, edit descriptions and hex colors, and reset to defaults.
  - **Abstract Base Classifier (`MaterialClassifier`):**
    - Contract decoupling inference pipelines from specific ML frameworks, supporting full images and region bounding-box crops.
  - **PyTorch Transfer Learning Engine (`PyTorchMaterialClassifier`):**
    - Lightweight CPU/GPU inference using MobileNetV3 or ResNet-18 backbones with softmax class probabilities.
    - Top-$k$ prediction generation and input tensor normalization.
  - **Heuristic Demo Simulation Engine (`DemoMaterialClassifier`):**
    - Deterministic chromatic and texture variance heuristic inference when no trained weights exist.
    - Explicitly tags all outputs with `is_demo = True`, `inference_mode = 'demo'`, and displays prominent academic disclaimers.
  - **Model Trainer & Packaging (`MaterialModelTrainer` & `train_material_model.py`):**
    - Transfer learning fine-tuning loop with data augmentations (`RandomHorizontalFlip`, `RandomRotation(10)`, `ColorJitter`).
    - Genuinely computes overall accuracy, macro precision, macro recall, macro F1, and confusion matrix on real test/validation samples.
    - Strict research safety: Never invents or fabricates performance metrics.
    - Packages artifacts with `weights.pt`, `classes.json`, `config.json`, `metrics.json`, and `README.md`.
  - **Dataset Structure & Imbalance Validator (`DatasetValidator`):**
    - Verifies train/val/test splits, checks for missing classes, detects corrupted or unreadable images, and computes class imbalance ratios.
  - **Domain Service Layer (`MaterialService`):**
    - Direct image and ROI crop prediction.
    - Survey-level batch analysis: executes classifier on all survey images, records `MaterialDetection` entries in SQLite database, and computes substrate distribution percentages and average confidences.
    - Low-confidence handling: Flags predictions below threshold (e.g. 0.60) as `LOW_CONFIDENCE` with advice: *"Material classification requires verification or additional imagery."*
  - **FastAPI Endpoints (`/api/materials/*`):**
    - `/classes`, `/classes/{id}`, `/classes/reset`, `/models`, `/predict`, `/surveys/{survey_id}/analyze`, `/surveys/{survey_id}/results`, `/dataset/validate`, `/models/train`.
  - **Interactive Frontend Dashboard (`MaterialClassificationPage.tsx`):**
    - Real-time substrate classification with preview canvas and ROI crop selector.
    - Survey substrate distribution breakdown charts and image detections gallery.
    - Configurable taxonomy manager (add, toggle, color pick, reset).
    - Model provenance card showing architecture, version, and genuine evaluation metrics or demo status.
    - Dataset validator tool.


#### Phase 5: Deterioration Detection / Segmentation ML Pipeline (COMPLETED & VERIFIED)
- **Objective:** Detect visible deterioration classes on heritage-site imagery, associate each defect with its underlying construction material ($\text{Material} \to \text{Deterioration}$), track spatial regions with bounding boxes/polygons, and enforce rigorous research safety.
- **Implemented & Verified Components:**
  - **Configurable Defect Taxonomy (`backend/app/core/deterioration_config.py`):**
    - JSON-backed registry (`data/config/deterioration_classes.json`) initialized with baseline heritage defect classes: `crack`, `erosion`, `spalling`, `discoloration`, and `biological_growth`.
    - Dynamic management: Add custom defects, toggle enabled/disabled status, edit descriptions, adjust severity weights (1-5), and restore defaults.
  - **Material-Aware Defect Association (`backend/app/services/material_association.py`):**
    - Spatial overlap resolution: associates 2D defect bounding boxes with material detections on the same image via Intersection-over-Area ($\text{IoA} \ge 0.10$).
    - Image-level fallback: links image-dominant material when bounding-box-level material annotations are absent.
    - Honest fallback: assigns `material_class = "UNKNOWN"` with `material_association_status = "MATERIAL_ASSOCIATION_UNAVAILABLE"` when no material data exists. **Never fabricates material labels.**
  - **Dual-Engine Inference Architecture (`backend/app/ml/`):**
    - `DeteriorationDetector` abstract base class defining standard contract (`load_model`, `predict`, `predict_batch`, `get_classes`, `get_model_info`, `is_available`).
    - `PyTorchDeteriorationDetector`: Faster R-CNN with MobileNetV3-Large FPN backbone for CPU/GPU object detection and fine-tuning.
    - `DemoDeteriorationDetector`: Deterministic computer-vision heuristic engine based on edge gradient analysis, local variance, and HSV thresholding for offline development without trained weights.
    - Strict research transparency: explicit `is_demo = True/False`, `inference_mode = 'demo'/'real_trained'`, and prominent disclaimers (`"DEMO DETERIORATION DETECTION — NOT A VALIDATED RESEARCH PREDICTION"`).
    - Always uses the term `"model confidence"`, never `"damage certainty"`.
  - **Low-Confidence & Risk-Aware Advisory:**
    - Flags detections below configurable threshold (default `0.60`) as `LOW_CONFIDENCE` with advice: *"Detection requires verification or additional imagery."*
  - **Deterioration Dataset Validator & Trainer (`backend/app/ml/`):**
    - `DeteriorationDatasetValidator`: inspects COCO/YOLO/Pascal VOC annotation formats, verifies positive dimensions ($w, h > 0, x, y \ge 0$), catches corrupt/unreadable images, and assesses class balance.
    - `DeteriorationModelTrainer` & `calculate_detection_metrics`: computes genuine mAP@0.50, Precision, and Recall on real test sets. **Never fabricates synthetic metrics.**
    - Standalone training script: `scripts/train_deterioration_model.py`.
  - **Database & Services (`backend/app/models/heritage.py`, `backend/app/services/deterioration_service.py`):**
    - Extended SQLite schema for `deterioration_detections` with material association, polygon, mask reference, model provenance, and demo flags.
    - Cross-tabulation matrices ($\text{Material} \times \text{Damage Type}$) computed per survey.
  - **REST API Endpoints (`/api/deterioration/*`):**
    - `/classes`, `/classes/{id}`, `/classes/reset`, `/models`, `/predict`, `/surveys/{survey_id}/analyze`, `/surveys/{survey_id}/results`, `/dataset/validate`, `/models/train`.
  - **Interactive Frontend Dashboard (`DeteriorationDetectionPage.tsx`):**
    - Single image analysis with interactive SVG bounding boxes, polygon contours, label/confidence toggles, and damage-type filters.
    - Survey-wide deterioration analysis with defect count distributions, severity breakdown, and material-damage cross-tabulation table.
    - Taxonomy manager, model provenance cards, and dataset validator tool.
  - **Verification:**
    - 34 automated unit & integration tests passing cleanly in `backend/tests/` (including 9 dedicated Phase 5 tests in `test_deterioration_detection.py`).
    - Production frontend build verified with 0 TypeScript/compilation errors.

#### Phase 6: 2D-to-3D Damage Mapping (COMPLETED & VERIFIED)
- **Objective:** Convert 2D deterioration detections produced in Phase 5 into spatially localized 3D damage representations on the photogrammetric reconstructions produced in Phase 3.
- **Core Research Data Model:**
  $$\mathbf{Material} + \mathbf{Deterioration} + \mathbf{3D\ Location} + \mathbf{Survey} + \mathbf{Image} + \mathbf{Confidence}$$
- **Implemented & Verified Components:**
  - **Camera Model & Validation (`backend/app/services/camera_model.py`):**
    - Calibrated pinhole camera abstraction with focal length ($f_x, f_y$), principal point ($c_x, c_y$), image dimensions ($W, H$), camera center ($C$), and orientation ($R_{c2w}$ or quaternion).
    - Coordinate convention: Camera local $+X$ right, $+Y$ down, $+Z$ forward into scene; World coordinate system matches Phase 3 reconstruction.
    - Pixel-to-ray generation: Normalized optical coordinates transformed to world space unit direction vectors.
    - World-to-pixel reprojection: Validates 3D points against camera plane ($z_{cam} > 0$) and computes Euclidean pixel residuals.
    - Safe camera validation: Rejects missing poses or corrupt dimensions with explicit statuses (`MAPPING_UNAVAILABLE` or `MAPPING_REQUIRES_CALIBRATION`). Never invents arbitrary camera poses.
  - **Surface Raycasting Engine (`backend/app/services/surface_raycaster.py`):**
    - High-performance Open3D `RaycastingScene` for triangle mesh intersection (`MESH_RAYCAST`).
    - Point-cloud ray proximity approximation fallback (`POINT_CLOUD_APPROXIMATION`) when mesh geometry is absent.
    - Analytic synthetic plane / geometry support for deterministic unit tests.
    - Geometry caching across survey runs for CPU efficiency.
  - **Damage Point Sampling (`backend/app/services/damage_sampler.py`):**
    - Configurable point sampling: `CENTER_ONLY` (default), `BOX_GRID` (9 points inside bounding box), `POLYGON_VERTICES` (vertices + centroid), and `MASK_SAMPLES`.
  - **Spatial Persistence & Schemas (`backend/app/models/heritage.py`, `backend/app/schemas/damage_mapping.py`):**
    - Dedicated database tables: `deterioration_3d_mappings` and `deterioration_3d_mapping_points` in SQLite.
    - Tracks primary 3D point $(X, Y, Z)$, image coordinates $(u, v)$, ray origin/direction, intersection distance, mapping method, surface source, reprojection error, scale status (`LOCAL`), and multi-point samples.
    - Propagates defect type and confidence, material class and confidence, and demo provenance (`is_demo = True/False`).
  - **REST API Endpoints (`/api/damage-mapping/*`):**
    - `POST /detections/{id}/map`: Maps individual detection to 3D surface.
    - `POST /surveys/{id}/map`: Batch maps all detections across survey and generates cross-tabulations.
    - `GET /detections/{id}`: Retrieves single 3D mapping.
    - `GET /surveys/{id}`: Retrieves survey mapping summary, status counts, and $\text{Material} \times \text{Damage}$ matrix.
    - `GET /reconstructions/{id}`: Returns all 3D mapped damage points for 3D viewer rendering.
    - `POST /validate/{id}`: Re-calculates camera reprojection error.
  - **Interactive 3D Frontend (`ModelViewer3D.tsx`, `DamageMappingPage.tsx`):**
    - Upgraded Three.js 3D viewer with interactive damage markers (spheres) color-coded by deterioration type.
    - Raycaster click interaction: clicking a 3D marker selects the damage item and highlights it with an outer halo ring.
    - Bidirectional traceability: inspect 3D coordinates, material association, defect confidence, reprojection residual, and source 2D image crop.
    - Comprehensive filters: by defect type, material substrate, confidence slider, and mapping status.
    - Prominent demo banners and research limitation disclaimers.
  - **Verification:**
    - 43 automated backend tests passing cleanly in `backend/tests/` (including 9 dedicated Phase 6 tests in `test_damage_mapping.py`).
    - Production frontend build verified with 0 TypeScript/compilation errors.

#### Phase 7: Multi-Temporal Monitoring & Change Detection (COMPLETED & VERIFIED)
- **Objective:** Compare the same heritage structure across multiple surveys/dates, align multi-epoch 3D reconstructions, identify measurable spatial changes, and track deterioration evolution while preserving material substrate associations.
- **Core Research Data Model:**
  $$\mathbf{Material} + \mathbf{Deterioration} + \mathbf{3D\ Location} + \mathbf{Survey\ Date} + \mathbf{Temporal\ Change} + \mathbf{Confidence\ /\ Provenance}$$
- **Implemented & Verified Components:**
  - **Survey Pair Validation (`TemporalService.validate_survey_pair`):**
    - Enforces same-site integrity, distinct survey IDs, actual timestamp verification, reconstruction availability, and scale compatibility.
    - Rejects cross-site comparisons with `INVALID_SURVEY_PAIR`. Calculates true elapsed days ($|T_2 - T_1|$). Never invents timestamps.
  - **3D Reconstruction Alignment (`TemporalAlignmentService`):**
    - Multi-method registration: `IDENTITY`, `CENTROID_INIT`, `ICP_POINT_TO_POINT`, and `ICP_POINT_TO_PLANE`.
    - Open3D ICP refinement with convergence criteria, max correspondence distance, and inlier metric logging.
    - Computes inlier correspondence ratio (`fitness`) and inlier root-mean-squared error (`rmse`).
    - If fitness $< 0.60$: assigns `ALIGNMENT_REQUIRES_REVIEW` rather than silently continuing with poor registration.
  - **Geometric Change Quantification (`TemporalChangeDetector`):**
    - Calculates nearest-neighbor Euclidean distance fields from aligned comparison point cloud ($T \cdot P_2$) to reference target ($P_1$).
    - Segments deviations against configurable threshold (`TEMPORAL_CHANGE_THRESHOLD = 0.02`): `NO_SIGNIFICANT_CHANGE` vs `GEOMETRIC_CHANGE_CANDIDATE`.
    - Spatial clustering (DBSCAN/voxel grouping) extracts localized geometric change candidate clusters.
  - **Deterioration Evolution Tracking (`TemporalService.run_deterioration_tracking`):**
    - Matches Phase 6 3D mapped damage points across epochs using spatial proximity in common reference frame ($T \cdot P_2$) and defect type compatibility.
    - Categorizes observations:
      - `PERSISTING_DETERIORATION`: Defect detected at both epochs with measured spatial displacement. Checks material consistency: if materials differ, flags `material_status = "MATERIAL_LABEL_CHANGED"`.
      - `NEW_DETERIORATION`: Newly detected at $T_2$ without baseline counterpart.
      - `POSSIBLY_RESOLVED_OR_UNDETECTED`: Observed at $T_1$ but unmapped at $T_2$. Research transparency: explicitly notes absence may stem from occlusion, lighting, or detection limits, never claiming certified cure.
      - `GEOMETRIC_CHANGE_WITHOUT_DETERIORATION_LABEL`: Measurable geometric deviation where no 2D defect was detected.
  - **Scale & Provenance Integrity:**
    - Flags local vs metric scale (`LOCAL` vs `METRIC`). Rejects false precision (no millimeter claims under `LOCAL` scale).
    - Preserves `is_demo` and `inference_mode`.
  - **REST API Endpoints (`/api/temporal/*`):**
    - `POST /api/temporal/compare`: Initialize survey pair comparison.
    - `POST /api/temporal/{id}/align`: Run ICP registration.
    - `POST /api/temporal/{id}/detect-change`: Run geometric change detection.
    - `POST /api/temporal/{id}/track-deterioration`: Match damage points across epochs.
    - `POST /api/temporal/{id}/run-full-pipeline`: Run full multi-temporal pipeline end-to-end.
    - `GET /api/temporal/{id}`: Retrieve comparison summary and metrics.
    - `GET /api/temporal/{id}/changes`: Retrieve filtered temporal change records.
    - `GET /api/temporal/site/{site_id}/timeline`: Retrieve chronological survey history.
    - `GET /api/temporal/site/{site_id}/comparisons`: List all comparisons for a site.
  - **Interactive Frontend Workspace (`TemporalMonitoringPage.tsx`):**
    - Survey pair selector with elapsed days calculation and scale badge.
    - Interactive 3D model viewer with T1, T2, and Difference Map modes and color-coded evolution spheres.
    - Bidirectional defect inspector drawer with before/after coordinates, measured displacement, and material consistency.
    - Multi-parameter filterable change table (status, material, defect type, text search).
  - **Verification:**
    - 51 automated backend unit & integration tests passing cleanly in `backend/tests/` (including 8 dedicated Phase 7 tests in `test_temporal_monitoring.py`).
    - Production frontend build verified with 0 TypeScript/compilation errors.

#### Phase 8: Reliability Assessment & Risk Prioritization
- **Objective:** Assess scientific certainty and prioritize urgent conservation interventions.
- **Deliverables:**
  - **Reliability Index ($R \in [0, 1]$):**
    - Function of ML confidence, image quality score, registration residual error, and photogrammetric reprojection error.
    - Transparent, customizable scoring formula without claiming clinical certification.
  - **Risk / Severity Matrix:**
    - Inputs: Material vulnerability (e.g., lime mortar/sandstone vs. granite), defect severity, progression rate, reliability.
    - Transparent classification: `Low Priority`, `Moderate Priority`, `High Priority`.
  - **Recommendation Engine:**
    - Rule-based generation of practical monitoring advice (e.g., "Schedule follow-up photogrammetry in 3 months", "Verify crack depth with ultrasound").

#### Phase 9: Reporting, Visualization & Academic Presentation
- **Objective:** Synthesize findings into exportable research and inspection artifacts.
- **Deliverables:**
  - Automated PDF report generator (ReportLab / WeasyPrint) summarizing surveys, 3D metrics, charts, and recommendations.
  - Interactive research dashboard with timeline charts, material distribution pies, and risk heatmaps.
  - Structured data export (JSON/CSV) for scientific benchmarking.

#### Phase 10: Validation, Benchmark & Research Evaluation
- **Objective:** Prepare the project for academic publication.
- **Deliverables:**
  - Evaluation framework for Precision, Recall, F1, IoU, and mAP.
  - Repeatability and measurement error benchmarking.
  - Complete technical documentation, user manual, and dataset guide.

---

### 3. Hardware Accessibility Principles
- **CPU First:** Full functionality on standard consumer laptops with integrated graphics.
- **Zero Cost Dependencies:** 100% open-source tools (FastAPI, React, OpenCV, Open3D, PyTorch, SQLite).
- **Graceful Degradation:** Automatic fallback when external tools (e.g., COLMAP) or dedicated GPUs are absent.
- **Modular Services:** Every component communicates through documented REST interfaces and Pydantic schemas.
