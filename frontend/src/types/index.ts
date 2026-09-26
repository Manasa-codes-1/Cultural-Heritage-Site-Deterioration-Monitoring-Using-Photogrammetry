export interface SystemInfo {
  python_version: string;
  colmap_available: boolean;
  colmap_path: string | null;
  cuda_available: boolean;
  gpu_name: string | null;
  mock_photogrammetry_enabled: boolean;
  mock_ml_enabled: boolean;
  environment: string;
}

export interface HealthResponse {
  status: string;
  app_name: string;
  version: string;
  timestamp: string;
  system_info: SystemInfo;
  database_connected: boolean;
}

export interface Site {
  id: string;
  name: string;
  location: string;
  description?: string;
  historical_period?: string;
  primary_material?: string;
  latitude?: number;
  longitude?: number;
  created_at: string;
  updated_at: string;
  survey_count: number;
}

export interface SiteCreate {
  name: string;
  location: string;
  description?: string;
  historical_period?: string;
  primary_material?: string;
  latitude?: number;
  longitude?: number;
}

export interface EnvironmentalInfo {
  temp_c?: number;
  humidity_pct?: number;
  rainfall_mm?: number;
  uv_index?: number;
  notes?: string;
}

export interface Survey {
  id: string;
  site_id: string;
  survey_code: string;
  survey_date: string;
  description?: string;
  operator?: string;
  camera_info?: string;
  environmental_info?: EnvironmentalInfo;
  status: string;
  created_at: string;
  updated_at: string;
  image_count: number;
  average_quality_score?: number | null;
}

export interface SurveyCreate {
  site_id: string;
  survey_code: string;
  survey_date: string;
  description?: string;
  operator?: string;
  camera_info?: string;
  environmental_info?: EnvironmentalInfo;
}

export interface QualityDetail {
  score?: number;
  status?: string;
  threshold?: number;
  recommendation?: string;
  count?: number;
  width?: number;
  height?: number;
}

export interface ImageRecord {
  id: string;
  survey_id: string;
  filename: string;
  file_size_bytes: number;
  width?: number;
  height?: number;
  channels?: number;
  quality_score?: number;
  quality_status: 'pass' | 'warning' | 'fail' | 'pending';
  blur_score?: number;
  blur_status?: 'pass' | 'fail';
  brightness_score?: number;
  brightness_status?: 'pass' | 'fail';
  resolution_status?: 'pass' | 'fail';
  feature_count?: number;
  quality_details?: {
    valid: boolean;
    quality_score: number;
    quality_status: string;
    overall_recommendation: string;
    blur: QualityDetail;
    brightness: QualityDetail;
    resolution: QualityDetail;
    features: QualityDetail;
  };
  download_url?: string;
  captured_at?: string;
  created_at: string;
}

export interface SurveyDetail extends Survey {
  images: ImageRecord[];
}

export interface ImageUploadResponse {
  uploaded_images: ImageRecord[];
  failed_images: Array<{ filename: string; reason: string }>;
  total_uploaded: number;
  total_failed: number;
}

export interface QualitySummary {
  survey_id: string;
  total_images: number;
  average_quality_score: number;
  pass_count: number;
  warning_count: number;
  fail_count: number;
  pass_percentage: number;
  blur_failures: number;
  brightness_failures: number;
  resolution_failures: number;
  recommendation: string;
  ready_for_photogrammetry: boolean;
}

export interface PairMatchRequest {
  image_a_id: string;
  image_b_id: string;
}

export interface PairMatchRecord {
  id?: string;
  survey_id?: string;
  image_a_id: string;
  image_b_id: string;
  image_a_filename?: string;
  image_b_filename?: string;
  keypoints_a: number;
  keypoints_b: number;
  candidate_matches: number;
  good_matches: number;
  match_ratio: number;
  estimated_overlap: string;
  status: 'GOOD' | 'WARNING' | 'POOR' | 'INSUFFICIENT_FEATURES';
  recommendation?: string;
  algorithm: string;
  created_at?: string;
}

export interface ConnectivityNode {
  id: string;
  filename: string;
  degree: number;
  status: 'well_connected' | 'weakly_connected' | 'isolated';
}

export interface ConnectivityEdge {
  source: string;
  target: string;
  good_matches: number;
  match_ratio: number;
  status: 'GOOD' | 'WARNING' | 'POOR';
}

export interface SurveyReadiness {
  survey_id: string;
  images_analyzed: number;
  pairs_analyzed: number;
  good_pairs: number;
  warning_pairs: number;
  poor_pairs: number;
  average_good_matches: number;
  readiness_status: 'READY' | 'READY_WITH_WARNINGS' | 'INSUFFICIENT_IMAGE_CONNECTIVITY' | 'RECAPTURE_REQUIRED';
  isolated_image_ids: string[];
  weakly_connected_image_ids: string[];
  connectivity_nodes: ConnectivityNode[];
  connectivity_edges: ConnectivityEdge[];
  recommendations: string[];
  is_heuristic: boolean;
  updated_at?: string;
}

// Phase 3: Photogrammetry & 3D Reconstruction Types
export interface PhotogrammetryAvailability {
  colmap_available: boolean;
  colmap_path: string | null;
  colmap_version: string | null;
  cuda_available: boolean;
  gpu_info: string | null;
  open3d_available: boolean;
  open3d_version: string | null;
  recommended_engine: string;
  system_notes: string[];
}

export interface CameraPose {
  camera_index?: number;
  image_id?: string;
  image_name?: string;
  position: [number, number, number];
  rotation_quaternion?: [number, number, number, number];
  reprojection_error?: number;
}

export interface BoundingBox3D {
  min: [number, number, number];
  max: [number, number, number];
  centroid: [number, number, number];
  dimensions: [number, number, number];
}

export interface Reconstruction {
  id: string;
  survey_id: string;
  engine: string;
  engine_version?: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  current_stage: string;
  progress_percent: number;
  sparse_point_cloud_path?: string;
  dense_point_cloud_path?: string;
  mesh_path?: string;
  texture_path?: string;
  workspace_path?: string;
  log_path?: string;
  camera_count: number;
  registered_image_count: number;
  point_count: number;
  sparse_point_count: number;
  dense_point_count: number;
  mesh_vertex_count: number;
  mesh_triangle_count: number;
  mean_reprojection_error?: number;
  camera_poses?: CameraPose[];
  bounding_box?: BoundingBox3D;
  metadata_json?: Record<string, unknown>;
  is_demo: boolean;
  error_message?: string;
  processing_logs?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface ReconstructionTrigger {
  engine?: string;
  dense?: boolean;
  generate_mesh?: boolean;
  force?: boolean;
}

// Phase 4: Material Classification ML Pipeline Types
export interface MaterialClassItem {
  id: string;
  name: string;
  description?: string;
  color: string;
  enabled: boolean;
  is_default: boolean;
}

export interface MaterialClassCreate {
  id: string;
  name: string;
  description?: string;
  color?: string;
}

export interface MaterialClassUpdate {
  name?: string;
  description?: string;
  color?: string;
  enabled?: boolean;
}

export interface TopKPrediction {
  material: string;
  confidence: number;
}

export interface MaterialPredictionResponse {
  material: string;
  confidence: number;
  status: 'CONFIDENT' | 'LOW_CONFIDENCE';
  recommendation?: string;
  top_k: TopKPrediction[];
  model_name: string;
  model_version?: string;
  inference_mode: 'real_trained' | 'demo';
  is_demo: boolean;
  region?: { x: number; y: number; w: number; h: number };
  image_id?: string;
  disclaimer: string;
}

export interface MaterialDetectionRecord {
  id: string;
  survey_id: string;
  image_id?: string;
  reconstruction_id?: string;
  material_class: string;
  confidence: number;
  status: string;
  top_k_predictions?: TopKPrediction[];
  bounding_box?: { x: number; y: number; w: number; h: number };
  model_name?: string;
  model_version?: string;
  inference_mode: string;
  is_demo: boolean;
  notes?: string;
  created_at: string;
}

export interface SurveyMaterialAnalysisSummary {
  survey_id: string;
  total_images: number;
  analyzed_images: number;
  detections_count: number;
  dominant_material?: string;
  distribution: Record<string, number>;
  distribution_percentage: Record<string, number>;
  average_confidences: Record<string, number>;
  overall_average_confidence: number;
  low_confidence_count: number;
  is_demo: boolean;
  model_used: string;
  detections: MaterialDetectionRecord[];
  disclaimer: string;
}

export interface MaterialModelSummary {
  id: string;
  name: string;
  architecture: string;
  version: string;
  training_date?: string;
  dataset_identifier?: string;
  classes: string[];
  is_demo: boolean;
  is_active: boolean;
  metrics?: {
    accuracy?: number;
    macro_precision?: number;
    macro_recall?: number;
    macro_f1?: number;
    total_evaluated_samples?: number;
    confusion_matrix?: number[][];
    class_labels?: string[];
    per_class?: Record<string, { precision: number; recall: number; f1_score: number; support: number }>;
  };
  path?: string;
  disclaimer?: string;
}

export interface DatasetValidationReport {
  status: 'VALID' | 'WARNING' | 'INVALID';
  dataset_path: string;
  class_counts: Record<string, Record<string, number>>;
  total_samples: number;
  num_classes: number;
  classes_found: string[];
  missing_classes: string[];
  imbalance_ratio?: number;
  warnings: string[];
  errors: string[];
  recommendation: string;
  research_note: string;
}

// Phase 5: Deterioration Detection / Segmentation Types
export interface DeteriorationClassItem {
  id: string;
  name: string;
  description?: string;
  color: string;
  enabled: boolean;
  is_default: boolean;
  severity_weight: number;
}

export interface DeteriorationClassCreate {
  id: string;
  name: string;
  description?: string;
  color?: string;
  severity_weight?: number;
}

export interface DeteriorationClassUpdate {
  name?: string;
  description?: string;
  color?: string;
  enabled?: boolean;
  severity_weight?: number;
}

export interface CandidateMaterialInfo {
  material_id?: string;
  material: string;
  coverage_ratio: number;
  iou: number;
  confidence?: number;
}

export interface DeteriorationItem {
  id: string;
  image_id?: string;
  survey_id?: string;
  damage_type: string;
  confidence: number;
  status: 'CONFIDENT' | 'LOW_CONFIDENCE';
  severity_hint?: string;
  bounding_box?: { x: number; y: number; w: number; h: number };
  polygon?: { x: number; y: number }[];
  mask_reference?: string;
  material_class: string;
  material_confidence?: number;
  material_association_status: 'ASSOCIATED' | 'OVERLAPPING_MULTIPLE' | 'MATERIAL_ASSOCIATION_UNAVAILABLE';
  candidate_materials?: CandidateMaterialInfo[];
  notes?: string;
  model_name?: string;
  model_version?: string;
  inference_mode: string;
  is_demo: boolean;
  created_at?: string;
}

export interface DeteriorationPredictionResponse {
  image_id?: string;
  detections: DeteriorationItem[];
  detections_count: number;
  model_name: string;
  model_version?: string;
  inference_mode: 'real_trained' | 'demo';
  is_demo: boolean;
  disclaimer: string;
}

export interface SurveyDeteriorationAnalysisSummary {
  survey_id: string;
  total_images: number;
  analyzed_images: number;
  total_detections: number;
  class_distribution: Record<string, number>;
  class_distribution_percentage: Record<string, number>;
  material_damage_crosstab: Record<string, Record<string, number>>;
  average_confidence: number;
  low_confidence_count: number;
  is_demo: boolean;
  model_used: string;
  detections: DeteriorationItem[];
  disclaimer: string;
}

export interface DeteriorationDatasetValidationReport {
  status: 'VALID' | 'WARNING' | 'INVALID';
  dataset_path: string;
  total_images: number;
  total_annotations: number;
  num_classes: number;
  classes_found: string[];
  missing_classes: string[];
  invalid_boxes_count: number;
  imbalance_ratio?: number;
  warnings: string[];
  errors: string[];
  recommendation: string;
  research_note: string;
}

export interface DeteriorationModelSummary {
  id: string;
  name: string;
  architecture: string;
  version: string;
  classes: string[];
  is_demo: boolean;
  is_active: boolean;
  metrics?: {
    mAP_50?: number;
    macro_precision?: number;
    macro_recall?: number;
    total_evaluated_images?: number;
    per_class?: Record<string, { precision: number; recall: number; f1_score: number; ap_50: number; ground_truth_count: number }>;
  };
  disclaimer?: string;
}

// Phase 6: 2D-to-3D Damage Mapping Types
export interface Point2D {
  x: number;
  y: number;
}

export interface Point3D {
  x: number;
  y: number;
  z: number;
}

export interface Deterioration3DMappingPointItem {
  id: string;
  mapping_id: string;
  point_type: string;
  image_point: Point2D;
  world_point?: Point3D | null;
  intersection_distance?: number | null;
  reprojection_error_px?: number | null;
  mapping_status: string;
  created_at?: string;
}

export interface Deterioration3DMappingItem {
  id: string;
  mapping_id?: string;
  detection_id: string;
  image_id: string;
  image_filename?: string;
  survey_id: string;
  reconstruction_id: string;

  material_class: string;
  material?: string;
  material_confidence?: number | null;
  material_association_status: string;

  deterioration_type: string;
  deterioration_confidence: number;
  severity_hint?: string;

  image_point: Point2D;
  world_point?: Point3D | null;
  ray_origin?: number[] | null;
  ray_direction?: number[] | null;
  intersection_distance?: number | null;

  mapping_method: string;
  surface_source: string;
  mapping_status: 'MAPPED' | 'PARTIALLY_MAPPED' | 'NO_SURFACE_INTERSECTION' | 'MAPPING_UNAVAILABLE' | 'MAPPING_REQUIRES_CALIBRATION' | 'MAPPING_REQUIRES_REVIEW';
  reprojection_error_px?: number | null;
  scale_status: 'LOCAL' | 'METRIC' | 'UNKNOWN';
  sampling_strategy: string;
  sample_point_count: number;
  mapped_point_count: number;

  is_demo: boolean;
  inference_mode: 'real_trained' | 'demo';
  notes?: string;

  points?: Deterioration3DMappingPointItem[];
  bounding_box?: { x: number; y: number; w: number; h: number } | null;
  created_at?: string;
}

export interface Survey3DMappingSummary {
  survey_id: string;
  reconstruction_id?: string | null;
  total_eligible_detections: number;
  mapped_detections: number;
  partially_mapped_detections: number;
  no_intersection_detections: number;
  unavailable_mappings: number;
  mapping_success_rate: number;

  detections_by_type: Record<string, number>;
  detections_by_material: Record<string, number>;
  material_deterioration_cross_tabulation: Record<string, Record<string, number>>;

  mean_reprojection_error_px?: number | null;
  surface_source_breakdown: Record<string, number>;
  scale_status: string;

  is_demo: boolean;
  inference_mode: string;
  mappings: Deterioration3DMappingItem[];
  research_disclaimer: string;
}

export interface MappingValidationResponse {
  mapping_id: string;
  status: string;
  reprojection_error_px?: number | null;
  is_valid: boolean;
  original_point: Point2D;
  reprojected_point?: Point2D | null;
  world_point?: Point3D | null;
  tolerance_px: number;
  notes: string;
}

// Phase 7: Multi-Temporal Monitoring & Change Detection Types
export interface TemporalComparisonCreateRequest {
  site_id: string;
  baseline_survey_id: string;
  comparison_survey_id: string;
  alignment_method?: string;
  change_threshold?: number;
  damage_matching_distance_threshold?: number;
}

export interface TemporalAlignmentRequest {
  alignment_method?: string;
  max_correspondence_distance?: number;
  max_iterations?: number;
  voxel_size?: number;
}

export interface TemporalChangeDetectRequest {
  change_threshold?: number;
  voxel_size?: number;
}

export interface TemporalDamageTrackRequest {
  damage_matching_distance_threshold?: number;
}

export interface TemporalChangeRecordItem {
  id: string;
  comparison_id: string;
  site_id: string;
  baseline_survey_id: string;
  comparison_survey_id: string;
  change_status:
    | 'NEW_DETERIORATION'
    | 'PERSISTING_DETERIORATION'
    | 'POSSIBLY_RESOLVED_OR_UNDETECTED'
    | 'GEOMETRIC_CHANGE_WITHOUT_DETERIORATION_LABEL'
    | 'NO_SIGNIFICANT_CHANGE'
    | 'ALIGNMENT_UNCERTAIN';
  deterioration_type: string;
  material_class: string;
  material_status: 'CONSISTENT' | 'MATERIAL_LABEL_CHANGED' | 'UNKNOWN';
  baseline_mapping_id?: string | null;
  comparison_mapping_id?: string | null;
  baseline_x?: number | null;
  baseline_y?: number | null;
  baseline_z?: number | null;
  comparison_x?: number | null;
  comparison_y?: number | null;
  comparison_z?: number | null;
  spatial_distance?: number | null;
  geometry_distance?: number | null;
  baseline_image_id?: string | null;
  comparison_image_id?: string | null;
  baseline_confidence?: number | null;
  comparison_confidence?: number | null;
  baseline_material_class?: string | null;
  comparison_material_class?: string | null;
  scale_status: string;
  is_demo: boolean;
  notes?: string | null;
  created_at?: string | null;
}

export interface TemporalComparisonSummary {
  id: string;
  site_id: string;
  site_name?: string | null;
  baseline_survey_id: string;
  baseline_survey_code?: string | null;
  baseline_survey_date?: string | null;
  comparison_survey_id: string;
  comparison_survey_code?: string | null;
  comparison_survey_date?: string | null;
  elapsed_days?: number | null;
  elapsed_time_formatted: string;
  baseline_reconstruction_id?: string | null;
  comparison_reconstruction_id?: string | null;
  alignment_status: string;
  alignment_method: string;
  transformation_matrix?: number[][] | null;
  fitness?: number | null;
  rmse?: number | null;
  correspondence_count: number;
  scale_status: string;
  change_detection_method: string;
  change_threshold: number;
  damage_matching_distance_threshold: number;
  status: string;
  summary_metrics: Record<string, any>;
  is_demo: boolean;
  inference_mode: string;
  notes?: string | null;
  error_message?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface TemporalTimelineItem {
  survey_id: string;
  survey_code: string;
  survey_date?: string | null;
  operator?: string | null;
  status: string;
  reconstruction_id?: string | null;
  reconstruction_status?: string | null;
  image_count: number;
  deterioration_count: number;
  mapped_3d_count: number;
}

// Integrated Demo Mode Types (Phases 1–7)
export interface DemoStatusResponse {
  initialized: boolean;
  site_id?: string | null;
  survey_t1_id?: string | null;
  survey_t2_id?: string | null;
  comparison_id?: string | null;
  last_run_at?: string | null;
  deepcrack_available: boolean;
  deepcrack_image_count: number;
}

export interface DemoImageItem {
  id: string;
  filename: string;
  width?: number | null;
  height?: number | null;
  blur_score?: number | null;
  blur_status?: string | null;
  brightness_score?: number | null;
  brightness_status?: string | null;
  quality_score?: number | null;
  is_usable: boolean;
  download_url: string;
  mask_filename?: string | null;
  mask_url?: string | null;
}

export interface DemoPhase1Quality {
  total_images: number;
  usable_images: number;
  average_blur: number;
  images: DemoImageItem[];
  research_note: string;
}

export interface DemoPhase2Matching {
  readiness_status: string;
  pairs_analyzed: number;
  good_pairs: number;
  warning_pairs: number;
  poor_pairs: number;
  average_good_matches: number;
  recommendations: string[];
  research_note: string;
}

export interface DemoPhase3Reconstruction {
  reconstruction_id: string;
  point_count: number;
  mesh_vertex_count: number;
  mesh_face_count: number;
  ply_url: string;
  obj_url: string;
  scale_status: string;
  is_demo: boolean;
  disclaimer: string;
}

export interface DemoPhase4Materials {
  primary_material: string;
  average_confidence: number;
  material_distribution: Record<string, number>;
  is_demo: boolean;
  inference_mode: string;
  disclaimer: string;
}

export interface DemoDetectionItem {
  id: string;
  image_id: string;
  image_filename: string;
  damage_type: string;
  confidence: number;
  status: string;
  bounding_box: Record<string, any>;
  polygon?: number[][] | null;
  material_class?: string | null;
  material_confidence?: number | null;
  mask_filename?: string | null;
  mask_url?: string | null;
  is_demo: boolean;
}

export interface DemoPhase5Deterioration {
  total_detections: number;
  detections: DemoDetectionItem[];
  damage_distribution: Record<string, number>;
  is_demo: boolean;
  disclaimer: string;
}

export interface DemoMappingItem {
  id: string;
  detection_id: string;
  image_filename: string;
  damage_type: string;
  material_class?: string | null;
  world_point?: { x: number; y: number; z: number } | null;
  mapping_status: string;
  reprojection_error_px?: number | null;
  is_demo: boolean;
}

export interface DemoPhase6DamageMapping {
  total_mapped: number;
  mappings: DemoMappingItem[];
  scale_status: string;
  is_demo: boolean;
  disclaimer: string;
}

export interface DemoChangeItem {
  change_type: string;
  damage_type: string;
  material_class?: string | null;
  confidence: number;
  spatial_distance_m?: number | null;
  scale_status: string;
  notes?: string | null;
}

export interface DemoPhase7Temporal {
  comparison_id: string;
  alignment_status: string;
  alignment_rmse?: number | null;
  total_changes: number;
  change_breakdown: Record<string, number>;
  changes: DemoChangeItem[];
  scale_status: string;
  is_demo: boolean;
  disclaimer: string;
}

export interface DemoFinalSummary {
  pipeline_complete: boolean;
  total_phases_executed: number;
  key_findings: string[];
  safety_statement: string;
}

export interface DataProvenance {
  image_data: string;
  image_masks: string;
  photogrammetry_3d: string;
  temporal_alignment: string;
  overall_classification: string;
}

export interface IntegratedDemoResponse {
  success: boolean;
  site_id: string;
  site_name: string;
  survey_t1_id: string;
  survey_t1_name: string;
  survey_t2_id: string;
  survey_t2_name: string;
  comparison_id: string;
  provenance: DataProvenance;
  phase1_quality: DemoPhase1Quality;
  phase2_matching: DemoPhase2Matching;
  phase3_reconstruction: DemoPhase3Reconstruction;
  phase4_materials: DemoPhase4Materials;
  phase5_deterioration: DemoPhase5Deterioration;
  phase6_damage_mapping: DemoPhase6DamageMapping;
  phase7_temporal: DemoPhase7Temporal;
  summary: DemoFinalSummary;
  executed_at: string;
}




