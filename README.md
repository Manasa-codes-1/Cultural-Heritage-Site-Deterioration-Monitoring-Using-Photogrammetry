# Cultural Heritage Site Deterioration Monitoring Using Photogrammetry

A low-cost, non-contact, material-aware cultural heritage monitoring platform integrating photogrammetric 3D reconstruction, computer vision, machine learning, and multi-temporal risk assessment.

---

## 🎯 Core Research Concept

$$\text{Material} \longrightarrow \text{Deterioration} \longrightarrow \text{3D Location} \longrightarrow \text{Temporal Change} \longrightarrow \text{Reliability} \longrightarrow \text{Risk} \longrightarrow \text{Recommendation}$$

Traditional heritage conservation often relies on subjective visual inspections or isolated 2D crack detectors that lack spatial context and material awareness. This system bridges that gap by:
1. Reconstructing accurate 3D geometry from standard consumer camera/smartphone photography using Structure-from-Motion (SfM) and Multi-View Stereo (MVS).
2. Classifying construction substrates (brick, sandstone, granite, lime mortar) via transfer learning.
3. Detecting and segmenting surface deterioration patterns (cracks, spalling, erosion, biological growth).
4. Projecting 2D detections onto registered 3D coordinates.
5. Computing multi-temporal changes (e.g. geometric deformation, defect growth) across recurring surveys.
6. Quantifying measurement reliability and recommending prioritized conservation actions.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.11+ / 3.14, FastAPI, Pydantic v2, SQLAlchemy, Uvicorn |
| **Database** | SQLite (ORM-abstracted for simple PostgreSQL migration) |
| **Computer Vision** | OpenCV, NumPy, Pillow |
| **Photogrammetry & 3D** | Open3D, COLMAP abstraction layer (with development Mock Engine) |
| **Machine Learning** | PyTorch, torchvision, scikit-learn (CPU and optional CUDA) |
| **Frontend** | React 18 / 19, TypeScript, Vite, TailwindCSS / Lucide Icons |
| **Reporting** | Automated summary and export engine |

---

## 📁 Repository Organization

```
heritage-deterioration-monitoring/
├── backend/
│   ├── app/
│   │   ├── api/          # REST route handlers
│   │   ├── core/         # Config, Database engine, Security
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── services/     # Business logic layer
│   │   ├── ml/           # Material & Deterioration ML pipelines
│   │   ├── photogrammetry/# SfM/MVS interfaces & engines
│   │   ├── processing/   # Quality assessment & geometry processing
│   │   └── main.py       # FastAPI application entrypoint
│   ├── tests/            # Pytest test suite
│   └── requirements.txt
├── frontend/             # React + TypeScript + Vite UI
├── data/                 # Raw uploads, processed imagery, survey storage
├── models/               # Model weights and checkpoints
├── outputs/              # 3D models, reports, and temporal analysis results
├── docs/                 # Research documentation, methodology, schemas
├── scripts/              # Utility and deployment scripts
├── DEVELOPMENT_PLAN.md   # Detailed multi-phase research and technical roadmap
├── README.md             # This document
└── .env.example          # Environment variable template
```

---

## 🚀 Quickstart Guide (Phase 1)

### Prerequisites
- Python 3.11+ (Python 3.14 supported)
- Node.js v18+ and npm
- (Optional) COLMAP for native photogrammetry processing

### 1. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create virtual environment (if not already done)
python -m venv venv
.\venv\Scripts\activate   # Windows
# or: source venv/bin/activate # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```
- API Documentation (Swagger): `http://localhost:8000/docs`
- Health check: `http://localhost:8000/api/health`

### 2. Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
- Frontend Web App: `http://localhost:5173`

---

## 🔬 Phase 2: Advanced Image Quality & Photogrammetry Readiness

Phase 2 upgrades the quality assessment layer from isolated single-image checks into an engineering-grade collection evaluation suite:

1. **Pairwise Feature Matching:**
   - Detects ORB invariant keypoints and computes binary descriptors.
   - Matches descriptor sets via Brute-Force Matcher (`cv2.NORM_HAMMING`).
   - Filters candidate matches using Lowe's ratio test ($d_1 < 0.75 \times d_2$).
   - Returns keypoints, candidate matches, good matches, match ratio, heuristic overlap indicators, and classification (`GOOD`, `WARNING`, `POOR`, `INSUFFICIENT_FEATURES`).

2. **Survey Collection Connectivity Graph:**
   - Maps images as nodes and verified correspondences ($G \ge 30$) as edges.
   - Evaluates node degree to identify well-connected, weakly connected, and isolated viewpoints.
   - Classifies overall dataset readiness: `READY`, `READY_WITH_WARNINGS`, `INSUFFICIENT_IMAGE_CONNECTIVITY`, `RECAPTURE_REQUIRED`.
   - Generates actionable, data-driven recapture advice specifically naming isolated viewpoints.

3. **Phase 2 REST Endpoints:**
   - `POST /api/image-quality/match`: Pairwise match between two image IDs.
   - `POST /api/image-quality/surveys/{survey_id}/analyze`: Run collection feature matching & graph construction.
   - `GET /api/image-quality/surveys/{survey_id}/readiness`: Retrieve cached survey readiness and connectivity topology.
   - `GET /api/image-quality/surveys/{survey_id}/pairs`: Retrieve evaluated image pairs with optional status filter.
   - `GET /api/surveys/{survey_id}/quality-summary`: Preserved Phase 1 optical summary.

> **Research Note:**
> *"This module provides an engineering-level image-quality and feature-correspondence assessment intended to support photogrammetric preprocessing. Its thresholds are configurable heuristics and should not be interpreted as universally validated photogrammetry quality criteria or mathematical guarantees of bundle adjustment convergence."*

---

## 🏛️ Phase 3: Photogrammetry & 3D Reconstruction

Phase 3 introduces modular 3D spatial reconstruction capabilities, converting calibrated survey image sets into dense 3D point clouds and polygonal heritage surface meshes with full research transparency:

1. **Modular Engine Architecture:**
   - **`ColmapEngine`:** Safe Windows/Linux subprocess wrapper executing the full COLMAP pipeline (`feature_extractor`, `exhaustive_matcher`, `mapper`, `image_undistorter`, `patch_match_stereo`, `stereo_fusion`, `poisson_mesher`). Handles CPU-only environments gracefully when CUDA is absent.
   - **`MockPhotogrammetryEngine`:** Deterministic, procedural heritage stone architecture generator for offline development and testing. Produces realistic sandstone ashlar masonry facades with recessed mortar joints, surface undulation, camera frustum trajectories, and bounding dimensions.
   - **Engine Factory:** `auto` mode automatically detects whether COLMAP is installed on system `PATH` and falls back cleanly to the mock engine.

2. **Open3D Geometry & Point Cloud Processing (`PointCloudProcessor`):**
   - Precise geometric inspection: computes point counts, vertex counts, triangle counts, bounding boxes ($X \times Y \times Z$ in meters), centroids, and volumetric densities ($\text{pts/m}^3$).
   - Statistical outlier removal to filter floater noise.
   - Voxel grid downsampling for high-framerate WebGL streaming.
   - Normal estimation and camera orientation alignment.

3. **Interactive Three.js WebGL 3D Viewer (`ModelViewer3D`):**
   - Full 3D navigation with OrbitControls (left-click rotate, right-click pan, scroll zoom, damping).
   - Display modes: Shaded Surface Mesh, Wireframe Triangles, Dense Point Cloud, and Hybrid.
   - Camera frustum markers showing registered photo stations in 3D space.
   - View presets: Front, Isometric, Top, Side, and Reset.
   - Spatial ground grid and coordinate axes.
   - Bounding dimensions helper and real-time HUD telemetry.
   - **Prominent Academic Safety Banner:** Explicitly displays amber banner when viewing synthetic/demo models (`DEMO MODEL — NOT A REAL PHOTOGRAMMETRIC RECONSTRUCTION`) and emerald banner for certified photogrammetric models.

4. **Phase 3 REST Endpoints:**
   - `GET /api/photogrammetry/availability`: COLMAP binary detection, version, CUDA capability, and Open3D status.
   - `POST /api/photogrammetry/surveys/{survey_id}/reconstruct`: Trigger background reconstruction task.
   - `GET /api/photogrammetry/surveys/{survey_id}/reconstruction`: Retrieve survey reconstruction record and geometry metrics.
   - `GET /api/photogrammetry/reconstructions/{id}/status`: Lightweight polling endpoint for stage and progress percentage.
   - `GET /api/photogrammetry/reconstructions/{id}/model`: Securely streams 3D model files (`.ply`, `.obj`).
   - `GET /api/photogrammetry/reconstructions/{id}/logs`: Retrieve full execution logs for auditing.

---

## 🧱 Phase 4: Material Classification ML Pipeline

Phase 4 establishes the construction substrate classification module, linking detected physical surfaces with specific materials to contextualize later deterioration rates and conservation risks:

1. **Configurable Substrate Taxonomy:**
   - JSON-backed registry (`data/config/material_classes.json`) initialized with baseline heritage classes: `sandstone`, `granite`, `brick`, `lime_mortar`, and `other`.
   - Dynamic management: Add custom substrates, toggle enabled/disabled states, edit descriptions, adjust hex color swatches, and reset to defaults.

2. **Dual-Engine Inference Architecture:**
   - **`PyTorchMaterialClassifier`:** Transfer learning model (MobileNetV3 / ResNet-18) optimized for CPU inference on laptops and optional CUDA acceleration. Generates top-$k$ prediction distributions.
   - **`DemoMaterialClassifier`:** Deterministic chromatic and texture heuristic engine for development and offline testing when no trained weights are present.
   - **Strict Research Transparency:** Explicitly tags every prediction with `is_demo = True` or `False`, `inference_mode = 'demo'` or `'real_trained'`, and attaches academic disclaimers. Never refers to outputs as "certainty", always "model confidence".

3. **Low-Confidence & Risk-Aware Advisory:**
   - Predictions falling below the configurable threshold (default `0.60`) are categorized as `LOW_CONFIDENCE`.
   - Automatically attaches actionable advice: *"Material classification requires verification or additional imagery."*

4. **Survey-Level Substrate Analysis:**
   - Batch processes all images in a survey and persists `MaterialDetection` records into SQLite.
   - Computes aggregated distribution statistics: image counts, percentage share, average confidence per substrate, and dominant material.

5. **Dataset Validation & Training Framework:**
   - **`DatasetValidator`:** Scans dataset directories for train/val/test splits, detects missing classes, catches unreadable/corrupted files, and calculates class imbalance ratios.
   - **`MaterialModelTrainer`:** Fine-tunes transfer learning backbones with conservative augmentations (`RandomHorizontalFlip`, `RandomRotation`, `ColorJitter`).
   - **Strict Scientific Integrity:** Evaluates accuracy, macro precision, macro recall, macro F1, and confusion matrix strictly on real samples. Never fabricates synthetic evaluation metrics.
   - Packages complete model directories: `weights.pt`, `classes.json`, `config.json`, `metrics.json`, and `README.md`.
   - CLI script available at `scripts/train_material_model.py`.

6. **Phase 4 REST Endpoints:**
   - `GET /api/materials/classes`: List configured substrate classes.
   - `POST /api/materials/classes`: Register new substrate class.
   - `PUT /api/materials/classes/{id}`: Update substrate class properties.
   - `POST /api/materials/classes/reset`: Reset taxonomy to baseline categories.
   - `GET /api/materials/models`: Introspect registered models, architectures, and genuine evaluation metrics.
   - `POST /api/materials/predict`: Classify uploaded photo or database image (supports optional ROI bounding box crop).
   - `POST /api/materials/surveys/{survey_id}/analyze`: Batch classify all survey images and persist detections.
   - `GET /api/materials/surveys/{survey_id}/results`: Retrieve cached survey material distribution summary.
   - `POST /api/materials/dataset/validate`: Validate dataset directory structure, splits, and balance.
   - `POST /api/materials/models/train`: Trigger model training and genuine evaluation.

---

## 🔍 Phase 5: Deterioration Detection / Segmentation ML Pipeline

Phase 5 establishes the deterioration-detection layer of the research pipeline, identifying visible defects on heritage imagery and associating each defect with its underlying construction substrate:

$$\text{Material} \longrightarrow \text{Deterioration} \longrightarrow \text{3D Location} \longrightarrow \text{Temporal Change} \longrightarrow \text{Reliability} \longrightarrow \text{Risk} \longrightarrow \text{Recommendation}$$

1. **Configurable Defect Taxonomy:**
   - JSON-backed registry (`data/config/deterioration_classes.json`) initialized with baseline heritage defect classes: `crack`, `erosion`, `spalling`, `discoloration`, and `biological_growth`.
   - Dynamic management: Add custom defect types, toggle enabled/disabled status, edit descriptions, adjust severity weights ($1$ to $5$), and reset to defaults.

2. **Material-Aware Defect Association:**
   - Evaluates spatial overlap ($\text{IoA} \ge 0.10$) between 2D defect bounding boxes and material classifications detected on the same image during Phase 4.
   - Image-level fallback: when bounding-box material masks are absent, defaults to the image's dominant material substrate.
   - Honest fallback: when no material detections exist, explicitly marks `material_class = "UNKNOWN"` with status `"MATERIAL_ASSOCIATION_UNAVAILABLE"`. **Never fabricates substrate labels.**

3. **Dual-Engine Inference Architecture:**
   - **`PyTorchDeteriorationDetector`:** Faster R-CNN with MobileNetV3-Large FPN backbone for real deep-learning object detection and fine-tuning.
   - **`DemoDeteriorationDetector`:** Deterministic computer-vision heuristic engine based on edge gradient magnitude, local luminance variance, and HSV saturation analysis for offline development and local environments without trained weights.
   - **Strict Research Transparency:** Explicitly tags every prediction with `is_demo = True` or `False`, `inference_mode = 'demo'` or `'real_trained'`, and attaches prominent disclaimers (`"DEMO DETERIORATION DETECTION — NOT A VALIDATED RESEARCH PREDICTION"`).
   - Terminology standard: always refers to model outputs as `"model confidence"`, never `"damage certainty"`.

4. **Low-Confidence & Risk-Aware Advisory:**
   - Predictions with confidence scores below the configurable threshold (default `0.60`) are tagged as `LOW_CONFIDENCE`.
   - Automatically attaches actionable advice: *"Detection requires verification or additional imagery."*

5. **Survey Deterioration Analysis & Cross-Tabulation:**
   - Batch processes all images within a survey, linking defects to material substrates and persisting records to `DeteriorationDetection`.
   - Computes aggregated distribution statistics: defect counts, severity breakdowns, and a two-dimensional cross-tabulation table ($\text{Material} \times \text{Damage Type}$) illustrating defect prevalence by substrate.

6. **Dataset Validation & Training Framework:**
   - **`DeteriorationDatasetValidator`:** Scans dataset directories (Pascal VOC, YOLO, or COCO formats), verifies positive bounding box coordinates, identifies corrupt/unreadable files, and flags severe class imbalances.
   - **`DeteriorationModelTrainer`:** Fine-tunes object detection backbones with conservative spatial augmentations.
   - **Non-Fabricated Metrics:** Evaluates genuine mAP@0.50, Precision, and Recall strictly on real labeled test sets via `calculate_detection_metrics`. Never fabricates synthetic evaluation metrics.
   - Standalone CLI script available at `scripts/train_deterioration_model.py`.

7. **Phase 5 REST Endpoints:**
   - `GET /api/deterioration/classes`: List configured deterioration defect classes.
   - `POST /api/deterioration/classes`: Register new defect class.
   - `PUT /api/deterioration/classes/{id}`: Update defect class properties or severity weight.
   - `POST /api/deterioration/classes/reset`: Reset taxonomy to baseline defects.
   - `GET /api/deterioration/models`: Introspect registered detection models and genuine evaluation metrics.
   - `POST /api/deterioration/predict`: Detect defects on uploaded photo or database image (with material association).
   - `POST /api/deterioration/surveys/{survey_id}/analyze`: Batch analyze all survey images and persist defect records.
   - `GET /api/deterioration/surveys/{survey_id}/results`: Retrieve cached survey deterioration summary and cross-tabulation.
   - `POST /api/deterioration/dataset/validate`: Validate dataset directory structure, annotations, and split balance.
   - `POST /api/deterioration/models/train`: Trigger detection model training and genuine evaluation.

---

## 🎯 Phase 6: 2D-to-3D Damage Mapping

Phase 6 implements the spatial localization stage, translating 2D image detections into 3D world coordinates on the reconstructed photogrammetric surface:

$$\text{2D Image }(u, v) \xrightarrow{\text{Camera Model}} \text{Camera Ray }(O + t\hat{d}) \xrightarrow{\text{Surface Raycast}} \text{3D Surface }(X, Y, Z)$$

Unified research representation:
$$\mathbf{Material} + \mathbf{Deterioration} + \mathbf{3D\ Location} + \mathbf{Survey} + \mathbf{Image} + \mathbf{Confidence}$$

1. **Pinhole Camera Abstraction (`CameraModel`):**
   - Implements full camera pose inversion and optical ray generation from pixel coordinates $(u, v)$ to world-space unit rays.
   - Pinhole parameters: focal lengths ($f_x, f_y$), principal point ($c_x, c_y$), image dimensions ($W, H$), camera center ($C$), and orientation ($R_{c2w}$ or quaternion).
   - Coordinate convention: Camera local $+X$ right, $+Y$ down, $+Z$ forward; World coordinate system matches Phase 3 photogrammetric reconstruction.
   - Strict validation: Rejects missing camera poses or incomplete calibration with `MAPPING_UNAVAILABLE` or `MAPPING_REQUIRES_CALIBRATION`. Never substitutes arbitrary/default camera poses.

2. **3D Surface Raycasting (`SurfaceRaycaster`):**
   - **Primary Engine:** Open3D `RaycastingScene` for high-performance ray-triangle mesh intersection (`MESH_RAYCAST`).
   - **Fallback Engine:** Point-cloud proximity approximation (`POINT_CLOUD_APPROXIMATION`) finding nearest points along the ray when mesh geometry is absent.
   - If no surface intersection is found: assigns explicit status `NO_SURFACE_INTERSECTION`.

3. **Reprojection Residual Validation:**
   - Projects calculated 3D coordinates back into the camera coordinate system and computes Euclidean pixel error:
     $$\text{error}_{\text{px}} = \sqrt{(u_{\text{proj}} - u_{\text{orig}})^2 + (v_{\text{proj}} - v_{\text{orig}})^2}$$
   - Evaluates against configurable threshold (default `5.0 px`). If residual exceeds threshold, mapping status becomes `PARTIALLY_MAPPED` or `MAPPING_REQUIRES_REVIEW`.

4. **Multi-Point Damage Sampling (`DamagePointSampler`):**
   - Supports configurable 2D sampling: `CENTER_ONLY` (default), `BOX_GRID` (9 points), `POLYGON_VERTICES`, and `MASK_SAMPLES`.
   - Persists all sample points in `deterioration_3d_mapping_points` for geometric extent tracking.

5. **Coordinate System & Scale Handling:**
   - Preserves `scale_status`: `LOCAL` (default), `METRIC`, or `UNKNOWN`.
   - Explicitly displays: *"3D coordinates are in reconstruction-local units"* unless metric scale constraint is independently established.

6. **Phase 6 REST Endpoints (`/api/damage-mapping/*`):**
   - `POST /api/damage-mapping/detections/{id}/map`: Map individual detection to 3D surface.
   - `POST /api/damage-mapping/surveys/{id}/map`: Batch map all survey detections to 3D.
   - `GET /api/damage-mapping/detections/{id}`: Retrieve 3D mapping for a detection.
   - `GET /api/damage-mapping/surveys/{id}`: Retrieve survey-level 3D mapping summary and substrate vulnerability matrix.
   - `GET /api/damage-mapping/reconstructions/{id}`: Retrieve all 3D mapped points for 3D viewer rendering.
   - `POST /api/damage-mapping/validate/{id}`: Validate camera reprojection.

7. **Interactive 3D WebGL Dashboard (`DamageMappingPage.tsx`):**
   - Interactive Three.js 3D viewer rendering mapped defect spheres color-coded by deterioration type (`crack`: red, `erosion`: orange, `spalling`: yellow, `discoloration`: purple, `biological_growth`: green).
   - Click interaction selects damage points and highlights them with outer halo rings.
   - Bidirectional traceability drawer connecting 3D world coordinates to source 2D image crops.
   - Substrate vulnerability matrix ($\text{Material} \times \text{Damage Type}$).

> [!IMPORTANT]
> **Research Limitation:** 2D-to-3D mapping quality depends on the accuracy and completeness of photogrammetric camera calibration, camera poses, reconstruction geometry, and source deterioration localization. Mapped coordinates should therefore be interpreted within the documented reconstruction coordinate system and scale.

---

## 🎯 Phase 7: Multi-Temporal Monitoring & Change Detection

Phase 7 implements multi-temporal geometric registration, nearest-neighbor change quantification, and defect evolution tracking between survey epochs $T_1$ (baseline) and $T_2$ (comparison).

### Key Methodologies & Modules

1. **Survey Pair Validation (`TemporalService.validate_survey_pair`):**
   - Enforces same-site integrity, distinct survey identifiers, chronological ordering, reconstruction availability, and scale compatibility.
   - Calculates true elapsed days ($|T_2 - T_1|$) without fabricating timestamps.
   - Rejects mismatched sites with `INVALID_SURVEY_PAIR`.

2. **3D Reconstruction Alignment (`TemporalAlignmentService`):**
   - Multi-method rigid registration using Open3D:
     - `IDENTITY`: Baseline reference identity matrix.
     - `CENTROID_INIT`: Center-of-mass translation alignment.
     - `ICP_POINT_TO_POINT`: Besl & McKay Iterative Closest Point algorithm.
     - `ICP_POINT_TO_PLANE`: Chen & Medioni normal-constrained registration.
   - Computes registration metrics:
     - Inlier Correspondence Ratio (`fitness` $\in [0, 1]$): Fraction of point correspondences within max distance.
     - Root-Mean-Squared Inlier Error (`rmse`): Residual distance between corresponding points.
     - Correspondence Count: Absolute count of matched points.
   - Threshold-driven review: If fitness $< 0.60$, flags `ALIGNMENT_REQUIRES_REVIEW` to guard against false change detections.
   - Coordinates: Transforms comparison points $P_2$ into baseline reference frame $T_1$ via $P_{2,\text{aligned}} = T \cdot P_2$.

3. **Geometric Change Quantification (`TemporalChangeDetector`):**
   - Nearest-neighbor Euclidean distance computation from aligned comparison cloud to baseline cloud using KD-Tree.
   - Deviation segmentation against configurable threshold (`TEMPORAL_CHANGE_THRESHOLD = 0.02`):
     - $\Delta \le \tau$: `NO_SIGNIFICANT_CHANGE`
     - $\Delta > \tau$: `GEOMETRIC_CHANGE_CANDIDATE`
   - Spatial clustering (DBSCAN / voxel grouping) extracts contiguous defect regions without artificial fabrication.

4. **Deterioration Evolution Tracking (`TemporalService.run_deterioration_tracking`):**
   - Matches Phase 6 3D mapped defect centers across epochs using spatial proximity in common reference frame and defect type compatibility.
   - Distinguishes rigorous observational states:
     - `PERSISTING_DETERIORATION`: Defect observed at both epochs; computes spatial displacement. Checks substrate consistency: if material classes differ, records `material_status = "MATERIAL_LABEL_CHANGED"`.
     - `NEW_DETERIORATION`: Defect detected at $T_2$ with no baseline counterpart.
     - `POSSIBLY_RESOLVED_OR_UNDETECTED`: Defect observed at $T_1$ but unmapped at $T_2$. Research transparency: notes absence may reflect occlusion, lighting, or detection limits—never claiming certified cure.
     - `GEOMETRIC_CHANGE_WITHOUT_DETERIORATION_LABEL`: Measurable geometric displacement where 2D detector did not flag an anomaly.

5. **Phase 7 REST Endpoints (`/api/temporal/*`):**
   - `POST /api/temporal/compare`: Initialize survey pair comparison.
   - `POST /api/temporal/{id}/align`: Run ICP point cloud alignment.
   - `POST /api/temporal/{id}/detect-change`: Run nearest-neighbor geometric change detection.
   - `POST /api/temporal/{id}/track-deterioration`: Match damage points and classify evolution.
   - `POST /api/temporal/{id}/run-full-pipeline`: Execute full multi-temporal analysis end-to-end.
   - `GET /api/temporal/{id}`: Retrieve comparison record and summary statistics.
   - `GET /api/temporal/{id}/changes`: Retrieve filtered temporal change records.
   - `GET /api/temporal/site/{site_id}/timeline`: Retrieve chronological survey history for a site.
   - `GET /api/temporal/site/{site_id}/comparisons`: List all comparisons for a site.

6. **Interactive Multi-Temporal Dashboard (`TemporalMonitoringPage.tsx`):**
   - Survey pair selector with elapsed days calculation and scale badge.
   - Interactive Three.js 3D viewer supporting $T_1$ Baseline, $T_2$ Comparison, Both, and Difference modes.
   - Color-coded defect markers: Cyan (`NEW`), Rose (`PERSISTING`), Indigo (`POSSIBLY RESOLVED / UNDETECTED`), Amber (`GEOMETRIC CHANGE`).
   - Bidirectional defect inspector drawer with before/after coordinates, measured displacement, and material consistency.
   - Filterable change table by status, material, defect type, and search query.

> [!IMPORTANT]
> **Research Limitation:** Multi-temporal change detection accuracy is bounded by photogrammetric reconstruction density, surface point noise, and registration fitness. Unscaled models are strictly reported in reconstruction-local units; metric millimetric progression requires calibrated scale bars.

---

## ⚠️ Academic & Conservation Notice
This platform is an academic research and decision-support system. It is designed to assist conservators, researchers, and engineers by prioritizing monitoring attention and quantifying change over time. It does **not** provide certified structural safety guarantees or replace on-site physical evaluation by licensed heritage conservators.


