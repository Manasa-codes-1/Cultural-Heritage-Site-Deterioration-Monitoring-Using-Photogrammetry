import type {
  HealthResponse,
  Site,
  SiteCreate,
  Survey,
  SurveyCreate,
  SurveyDetail,
  ImageRecord,
  ImageUploadResponse,
  QualitySummary,
  PairMatchRequest,
  PairMatchRecord,
  SurveyReadiness,
  PhotogrammetryAvailability,
  Reconstruction,
  ReconstructionTrigger,
  MaterialClassItem,
  MaterialClassCreate,
  MaterialClassUpdate,
  MaterialPredictionResponse,
  SurveyMaterialAnalysisSummary,
  MaterialModelSummary,
  DatasetValidationReport,
  DeteriorationClassItem,
  DeteriorationClassCreate,
  DeteriorationClassUpdate,
  DeteriorationPredictionResponse,
  SurveyDeteriorationAnalysisSummary,
  DeteriorationDatasetValidationReport,
  DeteriorationModelSummary,
  Deterioration3DMappingItem,
  Survey3DMappingSummary,
  MappingValidationResponse,
  TemporalComparisonSummary,
  TemporalChangeRecordItem,
  TemporalComparisonCreateRequest,
  TemporalAlignmentRequest,
  TemporalChangeDetectRequest,
  TemporalDamageTrackRequest,
  TemporalTimelineItem,
  DemoStatusResponse,
  IntegratedDemoResponse,
} from '../types';




const API_BASE = '/api';


async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errMsg = `Request failed with status ${res.status}`;
    try {
      const errData = await res.json();
      if (errData && errData.detail) {
        errMsg = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errMsg);
  }
  return res.json();
}

export const api = {
  // Health
  async getHealth(): Promise<HealthResponse> {
    const res = await fetch(`${API_BASE}/health`);
    return handleResponse<HealthResponse>(res);
  },

  // Sites
  async getSites(): Promise<Site[]> {
    const res = await fetch(`${API_BASE}/sites`);
    return handleResponse<Site[]>(res);
  },

  async createSite(site: SiteCreate): Promise<Site> {
    const res = await fetch(`${API_BASE}/sites`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(site),
    });
    return handleResponse<Site>(res);
  },

  async getSite(siteId: string): Promise<Site> {
    const res = await fetch(`${API_BASE}/sites/${siteId}`);
    return handleResponse<Site>(res);
  },

  async deleteSite(siteId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/sites/${siteId}`, { method: 'DELETE' });
    if (!res.ok && res.status !== 204) {
      throw new Error(`Failed to delete site (${res.status})`);
    }
  },

  // Surveys
  async getSurveys(siteId?: string): Promise<Survey[]> {
    const url = siteId ? `${API_BASE}/surveys?site_id=${siteId}` : `${API_BASE}/surveys`;
    const res = await fetch(url);
    return handleResponse<Survey[]>(res);
  },

  async createSurvey(survey: SurveyCreate): Promise<Survey> {
    const res = await fetch(`${API_BASE}/surveys`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(survey),
    });
    return handleResponse<Survey>(res);
  },

  async getSurveyDetail(surveyId: string): Promise<SurveyDetail> {
    const res = await fetch(`${API_BASE}/surveys/${surveyId}`);
    return handleResponse<SurveyDetail>(res);
  },

  async deleteSurvey(surveyId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/surveys/${surveyId}`, { method: 'DELETE' });
    if (!res.ok && res.status !== 204) {
      throw new Error(`Failed to delete survey (${res.status})`);
    }
  },

  // Images & Quality
  async uploadImages(surveyId: string, files: File[]): Promise<ImageUploadResponse> {
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    const res = await fetch(`${API_BASE}/surveys/${surveyId}/images/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<ImageUploadResponse>(res);
  },

  async getImage(imageId: string): Promise<ImageRecord> {
    const res = await fetch(`${API_BASE}/images/${imageId}`);
    return handleResponse<ImageRecord>(res);
  },

  async reassessImage(imageId: string): Promise<ImageRecord> {
    const res = await fetch(`${API_BASE}/images/${imageId}/reassess`, {
      method: 'POST',
    });
    return handleResponse<ImageRecord>(res);
  },

  async deleteImage(imageId: string): Promise<void> {
    const res = await fetch(`${API_BASE}/images/${imageId}`, { method: 'DELETE' });
    if (!res.ok && res.status !== 204) {
      throw new Error(`Failed to delete image (${res.status})`);
    }
  },

  async getSurveyQualitySummary(surveyId: string): Promise<QualitySummary> {
    const res = await fetch(`${API_BASE}/surveys/${surveyId}/quality-summary`);
    return handleResponse<QualitySummary>(res);
  },

  // Phase 2: Feature Matching & Photogrammetric Collection Readiness
  async matchPair(req: PairMatchRequest): Promise<PairMatchRecord> {
    const res = await fetch(`${API_BASE}/image-quality/match`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return handleResponse<PairMatchRecord>(res);
  },

  async analyzeSurveyCollection(surveyId: string): Promise<SurveyReadiness> {
    const res = await fetch(`${API_BASE}/image-quality/surveys/${surveyId}/analyze`, {
      method: 'POST',
    });
    return handleResponse<SurveyReadiness>(res);
  },

  async getSurveyReadiness(surveyId: string): Promise<SurveyReadiness> {
    const res = await fetch(`${API_BASE}/image-quality/surveys/${surveyId}/readiness`);
    return handleResponse<SurveyReadiness>(res);
  },

  async getSurveyPairs(surveyId: string, status?: string): Promise<PairMatchRecord[]> {
    const url = status
      ? `${API_BASE}/image-quality/surveys/${surveyId}/pairs?status=${status}`
      : `${API_BASE}/image-quality/surveys/${surveyId}/pairs`;
    const res = await fetch(url);
    return handleResponse<PairMatchRecord[]>(res);
  },

  // Phase 3: Photogrammetry & 3D Reconstruction
  async getPhotogrammetryAvailability(): Promise<PhotogrammetryAvailability> {
    const res = await fetch(`${API_BASE}/photogrammetry/availability`);
    return handleResponse<PhotogrammetryAvailability>(res);
  },

  async triggerReconstruction(surveyId: string, req: ReconstructionTrigger = {}): Promise<Reconstruction> {
    const res = await fetch(`${API_BASE}/photogrammetry/surveys/${surveyId}/reconstruct`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    return handleResponse<Reconstruction>(res);
  },

  async getSurveyReconstruction(surveyId: string): Promise<Reconstruction> {
    const res = await fetch(`${API_BASE}/photogrammetry/surveys/${surveyId}/reconstruction`);
    return handleResponse<Reconstruction>(res);
  },

  async getReconstruction(reconstructionId: string): Promise<Reconstruction> {
    const res = await fetch(`${API_BASE}/photogrammetry/reconstructions/${reconstructionId}`);
    return handleResponse<Reconstruction>(res);
  },

  async getReconstructionStatus(reconstructionId: string): Promise<Reconstruction> {
    const res = await fetch(`${API_BASE}/photogrammetry/reconstructions/${reconstructionId}/status`);
    return handleResponse<Reconstruction>(res);
  },

  getReconstructionModelUrl(reconstructionId: string, modelType: string = 'mesh'): string {
    return `${API_BASE}/photogrammetry/reconstructions/${reconstructionId}/model?model_type=${modelType}`;
  },

  async getReconstructionLogs(reconstructionId: string): Promise<string> {
    const res = await fetch(`${API_BASE}/photogrammetry/reconstructions/${reconstructionId}/logs`);
    if (!res.ok) {
      throw new Error(`Failed to load logs (${res.status})`);
    }
    return res.text();
  },

  // Phase 4: Material Classification ML Pipeline
  async getMaterialClasses(): Promise<MaterialClassItem[]> {
    const res = await fetch(`${API_BASE}/materials/classes`);
    return handleResponse<MaterialClassItem[]>(res);
  },

  async createMaterialClass(data: MaterialClassCreate): Promise<MaterialClassItem> {
    const res = await fetch(`${API_BASE}/materials/classes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse<MaterialClassItem>(res);
  },

  async updateMaterialClass(classId: string, data: MaterialClassUpdate): Promise<MaterialClassItem> {
    const res = await fetch(`${API_BASE}/materials/classes/${classId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse<MaterialClassItem>(res);
  },

  async resetMaterialClasses(): Promise<MaterialClassItem[]> {
    const res = await fetch(`${API_BASE}/materials/classes/reset`, {
      method: 'POST',
    });
    return handleResponse<MaterialClassItem[]>(res);
  },

  async getMaterialModels(): Promise<MaterialModelSummary[]> {
    const res = await fetch(`${API_BASE}/materials/models`);
    return handleResponse<MaterialModelSummary[]>(res);
  },

  async predictMaterial(formData: FormData): Promise<MaterialPredictionResponse> {
    const res = await fetch(`${API_BASE}/materials/predict`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<MaterialPredictionResponse>(res);
  },

  async analyzeSurveyMaterials(
    surveyId: string,
    modelId?: string,
    confidenceThreshold?: number
  ): Promise<SurveyMaterialAnalysisSummary> {
    const params = new URLSearchParams();
    if (modelId) params.append('model_id', modelId);
    if (confidenceThreshold !== undefined) params.append('confidence_threshold', String(confidenceThreshold));
    const url = `${API_BASE}/materials/surveys/${surveyId}/analyze?${params.toString()}`;
    const res = await fetch(url, { method: 'POST' });
    return handleResponse<SurveyMaterialAnalysisSummary>(res);
  },

  async getSurveyMaterialResults(surveyId: string): Promise<SurveyMaterialAnalysisSummary> {
    const res = await fetch(`${API_BASE}/materials/surveys/${surveyId}/results`);
    return handleResponse<SurveyMaterialAnalysisSummary>(res);
  },

  async validateDataset(datasetPath: string): Promise<DatasetValidationReport> {
    const res = await fetch(`${API_BASE}/materials/dataset/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_path: datasetPath }),
    });
    return handleResponse<DatasetValidationReport>(res);
  },

  async trainMaterialModel(config: {
    dataset_dir: string;
    output_dir?: string;
    architecture?: string;
    epochs?: number;
    batch_size?: number;
    lr?: number;
  }): Promise<Record<string, unknown>> {
    const res = await fetch(`${API_BASE}/materials/models/train`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    return handleResponse<Record<string, unknown>>(res);
  },

  // Phase 5: Deterioration Detection / Segmentation Pipeline
  async getDeteriorationClasses(): Promise<DeteriorationClassItem[]> {
    const res = await fetch(`${API_BASE}/deterioration/classes`);
    return handleResponse<DeteriorationClassItem[]>(res);
  },

  async createDeteriorationClass(data: DeteriorationClassCreate): Promise<DeteriorationClassItem> {
    const res = await fetch(`${API_BASE}/deterioration/classes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse<DeteriorationClassItem>(res);
  },

  async updateDeteriorationClass(classId: string, data: DeteriorationClassUpdate): Promise<DeteriorationClassItem> {
    const res = await fetch(`${API_BASE}/deterioration/classes/${classId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    return handleResponse<DeteriorationClassItem>(res);
  },

  async resetDeteriorationClasses(): Promise<DeteriorationClassItem[]> {
    const res = await fetch(`${API_BASE}/deterioration/classes/reset`, {
      method: 'POST',
    });
    return handleResponse<DeteriorationClassItem[]>(res);
  },

  async getDeteriorationModels(): Promise<DeteriorationModelSummary[]> {
    const res = await fetch(`${API_BASE}/deterioration/models`);
    return handleResponse<DeteriorationModelSummary[]>(res);
  },

  async predictDeterioration(formData: FormData): Promise<DeteriorationPredictionResponse> {
    const res = await fetch(`${API_BASE}/deterioration/predict`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse<DeteriorationPredictionResponse>(res);
  },

  async analyzeSurveyDeterioration(
    surveyId: string,
    modelId?: string,
    confidenceThreshold?: number
  ): Promise<SurveyDeteriorationAnalysisSummary> {
    const params = new URLSearchParams();
    if (modelId) params.append('model_id', modelId);
    if (confidenceThreshold !== undefined) params.append('confidence_threshold', String(confidenceThreshold));
    const url = `${API_BASE}/deterioration/surveys/${surveyId}/analyze?${params.toString()}`;
    const res = await fetch(url, { method: 'POST' });
    return handleResponse<SurveyDeteriorationAnalysisSummary>(res);
  },

  async getSurveyDeteriorationResults(surveyId: string): Promise<SurveyDeteriorationAnalysisSummary> {
    const res = await fetch(`${API_BASE}/deterioration/surveys/${surveyId}/results`);
    return handleResponse<SurveyDeteriorationAnalysisSummary>(res);
  },

  async validateDeteriorationDataset(datasetPath: string): Promise<DeteriorationDatasetValidationReport> {
    const res = await fetch(`${API_BASE}/deterioration/dataset/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset_path: datasetPath }),
    });
    return handleResponse<DeteriorationDatasetValidationReport>(res);
  },

  async trainDeteriorationModel(config: {
    dataset_dir: string;
    output_dir?: string;
    architecture?: string;
    epochs?: number;
    batch_size?: number;
    lr?: number;
  }): Promise<Record<string, unknown>> {
    const res = await fetch(`${API_BASE}/deterioration/models/train`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    return handleResponse<Record<string, unknown>>(res);
  },

  // Phase 6: 2D-to-3D Damage Mapping
  async mapDetection3D(
    detectionId: string,
    samplingStrategy: string = 'CENTER_ONLY',
    reprojectionThresholdPx: number = 5.0
  ): Promise<Deterioration3DMappingItem> {
    const params = new URLSearchParams({
      sampling_strategy: samplingStrategy,
      reprojection_threshold_px: String(reprojectionThresholdPx),
    });
    const res = await fetch(`${API_BASE}/damage-mapping/detections/${detectionId}/map?${params.toString()}`, {
      method: 'POST',
    });
    return handleResponse<Deterioration3DMappingItem>(res);
  },

  async mapSurvey3D(
    surveyId: string,
    options?: { sampling_strategy?: string; reprojection_threshold_px?: number; force?: boolean }
  ): Promise<Survey3DMappingSummary> {
    const res = await fetch(`${API_BASE}/damage-mapping/surveys/${surveyId}/map`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(options || {}),
    });
    return handleResponse<Survey3DMappingSummary>(res);
  },

  async getDetection3DMapping(detectionId: string): Promise<Deterioration3DMappingItem> {
    const res = await fetch(`${API_BASE}/damage-mapping/detections/${detectionId}`);
    return handleResponse<Deterioration3DMappingItem>(res);
  },

  async getSurvey3DMappings(surveyId: string): Promise<Survey3DMappingSummary> {
    const res = await fetch(`${API_BASE}/damage-mapping/surveys/${surveyId}`);
    return handleResponse<Survey3DMappingSummary>(res);
  },

  async getReconstruction3DMappings(reconstructionId: string): Promise<Deterioration3DMappingItem[]> {
    const res = await fetch(`${API_BASE}/damage-mapping/reconstructions/${reconstructionId}`);
    return handleResponse<Deterioration3DMappingItem[]>(res);
  },

  async validate3DMapping(mappingId: string, tolerancePx: number = 5.0): Promise<MappingValidationResponse> {
    const res = await fetch(`${API_BASE}/damage-mapping/validate/${mappingId}?tolerance_px=${tolerancePx}`, {
      method: 'POST',
    });
    return handleResponse<MappingValidationResponse>(res);
  },

  // Phase 7: Multi-Temporal Monitoring & Change Detection
  async createTemporalComparison(payload: TemporalComparisonCreateRequest): Promise<TemporalComparisonSummary> {
    const res = await fetch(`${API_BASE}/temporal/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse<TemporalComparisonSummary>(res);
  },

  async alignReconstructions(
    comparisonId: string,
    options?: TemporalAlignmentRequest
  ): Promise<{ status: string; alignment_result: Record<string, any>; comparison_summary: TemporalComparisonSummary }> {
    const res = await fetch(`${API_BASE}/temporal/${comparisonId}/align`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(options || {}),
    });
    return handleResponse<{ status: string; alignment_result: Record<string, any>; comparison_summary: TemporalComparisonSummary }>(res);
  },

  async detectGeometricChange(
    comparisonId: string,
    options?: TemporalChangeDetectRequest
  ): Promise<{ status: string; geometric_change_report: Record<string, any>; comparison_summary: TemporalComparisonSummary }> {
    const res = await fetch(`${API_BASE}/temporal/${comparisonId}/detect-change`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(options || {}),
    });
    return handleResponse<{ status: string; geometric_change_report: Record<string, any>; comparison_summary: TemporalComparisonSummary }>(res);
  },

  async trackDeterioration(
    comparisonId: string,
    options?: TemporalDamageTrackRequest
  ): Promise<{ status: string; records_created: number; comparison_summary: TemporalComparisonSummary }> {
    const res = await fetch(`${API_BASE}/temporal/${comparisonId}/track-deterioration`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(options || {}),
    });
    return handleResponse<{ status: string; records_created: number; comparison_summary: TemporalComparisonSummary }>(res);
  },

  async runFullTemporalPipeline(
    comparisonId: string,
    options?: {
      alignment?: TemporalAlignmentRequest;
      change?: TemporalChangeDetectRequest;
      track?: TemporalDamageTrackRequest;
    }
  ): Promise<TemporalComparisonSummary> {
    const res = await fetch(`${API_BASE}/temporal/${comparisonId}/run-full-pipeline`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        alignment_req: options?.alignment,
        change_req: options?.change,
        track_req: options?.track,
      }),
    });
    return handleResponse<TemporalComparisonSummary>(res);
  },

  async getTemporalComparison(comparisonId: string): Promise<TemporalComparisonSummary> {
    const res = await fetch(`${API_BASE}/temporal/${comparisonId}`);
    return handleResponse<TemporalComparisonSummary>(res);
  },

  async getTemporalComparisonChanges(
    comparisonId: string,
    filters?: { change_status?: string; material_class?: string; deterioration_type?: string }
  ): Promise<TemporalChangeRecordItem[]> {
    const params = new URLSearchParams();
    if (filters?.change_status) params.append('change_status', filters.change_status);
    if (filters?.material_class) params.append('material_class', filters.material_class);
    if (filters?.deterioration_type) params.append('deterioration_type', filters.deterioration_type);

    const qs = params.toString();
    const url = `${API_BASE}/temporal/${comparisonId}/changes${qs ? `?${qs}` : ''}`;
    const res = await fetch(url);
    return handleResponse<TemporalChangeRecordItem[]>(res);
  },

  async getSiteTimeline(siteId: string): Promise<TemporalTimelineItem[]> {
    const res = await fetch(`${API_BASE}/temporal/site/${siteId}/timeline`);
    return handleResponse<TemporalTimelineItem[]>(res);
  },

  async getSiteComparisons(siteId: string): Promise<TemporalComparisonSummary[]> {
    const res = await fetch(`${API_BASE}/temporal/site/${siteId}/comparisons`);
    return handleResponse<TemporalComparisonSummary[]>(res);
  },

  // Integrated Demo (Phases 1–7)
  async getDemoStatus(): Promise<DemoStatusResponse> {
    const res = await fetch(`${API_BASE}/demo/status`);
    return handleResponse<DemoStatusResponse>(res);
  },

  async runIntegratedDemo(): Promise<IntegratedDemoResponse> {
    const res = await fetch(`${API_BASE}/demo/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse<IntegratedDemoResponse>(res);
  },

  async resetDemo(): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE}/demo/reset`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    return handleResponse<{ success: boolean; message: string }>(res);
  },

  getDemoMaskUrl(filename: string): string {
    return `${API_BASE}/demo/mask/${filename}`;
  },
};

export const apiClient = api;



