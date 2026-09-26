import React, { useState, useEffect } from 'react';
import {
  Layers,
  Sparkles,
  AlertTriangle,
  RefreshCw,
  FolderKanban,
  Sliders,
  Cpu,
  BarChart3,
  Plus,
  RotateCcw,
  Upload,
  Info,
  ShieldAlert,
} from 'lucide-react';
import { api } from '../api/client';
import type {
  Survey,
  MaterialClassItem,
  MaterialModelSummary,
  MaterialPredictionResponse,
  SurveyMaterialAnalysisSummary,
  DatasetValidationReport,
} from '../types';

interface MaterialClassificationPageProps {
  initialSurveyId?: string;
  onNavigateToSurveys?: () => void;
}

export const MaterialClassificationPage: React.FC<MaterialClassificationPageProps> = ({
  initialSurveyId,
}) => {
  const [activeTab, setActiveTab] = useState<'single' | 'survey' | 'taxonomy' | 'models' | 'dataset'>('single');
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [selectedSurveyId, setSelectedSurveyId] = useState<string>(initialSurveyId || '');
  const [classes, setClasses] = useState<MaterialClassItem[]>([]);
  const [models, setModels] = useState<MaterialModelSummary[]>([]);
  const [error, setError] = useState<string | null>(null);


  // Single Prediction State
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [useCrop, setUseCrop] = useState(false);
  const [cropBox, setCropBox] = useState({ x: 20, y: 20, w: 200, h: 200 });
  const [singleResult, setSingleResult] = useState<MaterialPredictionResponse | null>(null);
  const [predicting, setPredicting] = useState(false);

  // Survey Analysis State
  const [surveySummary, setSurveySummary] = useState<SurveyMaterialAnalysisSummary | null>(null);
  const [analyzingSurvey, setAnalyzingSurvey] = useState(false);

  // Taxonomy Form State
  const [newClassId, setNewClassId] = useState('');
  const [newClassName, setNewClassName] = useState('');
  const [newClassColor, setNewClassColor] = useState('#38bdf8');
  const [newClassDesc, setNewClassDesc] = useState('');
  const [showAddClass, setShowAddClass] = useState(false);

  // Dataset Validator State
  const [datasetPathInput, setDatasetPathInput] = useState('data/datasets/materials');
  const [datasetReport, setDatasetReport] = useState<DatasetValidationReport | null>(null);
  const [validatingDataset, setValidatingDataset] = useState(false);

  // Initial load
  useEffect(() => {
    loadSurveys();
    loadClasses();
    loadModels();
  }, []);

  useEffect(() => {
    if (selectedSurveyId) {
      loadSurveyResults(selectedSurveyId);
    }
  }, [selectedSurveyId]);

  const loadSurveys = async () => {
    try {
      const data = await api.getSurveys();
      setSurveys(data);
      if (!selectedSurveyId && data.length > 0) {
        setSelectedSurveyId(data[0].id);
      }
    } catch (err: any) {
      console.error('Failed to load surveys', err);
    }
  };

  const loadClasses = async () => {
    try {
      const data = await api.getMaterialClasses();
      setClasses(data);
    } catch (err: any) {
      console.error('Failed to load classes', err);
    }
  };

  const loadModels = async () => {
    try {
      const data = await api.getMaterialModels();
      setModels(data);
    } catch (err: any) {
      console.error('Failed to load models', err);
    }
  };

  const loadSurveyResults = async (srvId: string) => {
    try {
      const res = await api.getSurveyMaterialResults(srvId);
      setSurveySummary(res);
    } catch {
      // Not yet analyzed
      setSurveySummary(null);
    }
  };

  // Image Upload for Testing
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
      setSingleResult(null);
    }
  };

  const handlePredictSingle = async () => {
    if (!selectedFile) return;
    setPredicting(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      if (useCrop) {
        formData.append('region_json', JSON.stringify(cropBox));
      }
      const res = await api.predictMaterial(formData);
      setSingleResult(res);
    } catch (err: any) {
      setError(err.message || 'Prediction failed');
    } finally {
      setPredicting(false);
    }
  };

  // Analyze Entire Survey
  const handleAnalyzeSurvey = async () => {
    if (!selectedSurveyId) return;
    setAnalyzingSurvey(true);
    setError(null);
    try {
      const summary = await api.analyzeSurveyMaterials(selectedSurveyId);
      setSurveySummary(summary);
    } catch (err: any) {
      setError(err.message || 'Survey material analysis failed');
    } finally {
      setAnalyzingSurvey(false);
    }
  };

  // Taxonomy Handlers
  const handleAddClass = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newClassId.trim() || !newClassName.trim()) return;
    try {
      await api.createMaterialClass({
        id: newClassId.trim(),
        name: newClassName.trim(),
        color: newClassColor,
        description: newClassDesc.trim(),
      });
      setNewClassId('');
      setNewClassName('');
      setNewClassDesc('');
      setShowAddClass(false);
      loadClasses();
    } catch (err: any) {
      setError(err.message || 'Failed to add class');
    }
  };

  const handleToggleClass = async (item: MaterialClassItem) => {
    try {
      await api.updateMaterialClass(item.id, { enabled: !item.enabled });
      loadClasses();
    } catch (err: any) {
      setError(err.message || 'Failed to update class');
    }
  };

  const handleResetClasses = async () => {
    if (!window.confirm('Reset material taxonomy to baseline heritage categories?')) return;
    try {
      await api.resetMaterialClasses();
      loadClasses();
    } catch (err: any) {
      setError(err.message || 'Failed to reset classes');
    }
  };

  // Dataset Validation Handler
  const handleValidateDataset = async () => {
    setValidatingDataset(true);
    setError(null);
    try {
      const rep = await api.validateDataset(datasetPathInput);
      setDatasetReport(rep);
    } catch (err: any) {
      setError(err.message || 'Dataset validation failed');
    } finally {
      setValidatingDataset(false);
    }
  };

  const activeModel = models.find((m) => m.is_active) || models[0];

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* 1. Header with Research Safety Notice */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-700/60 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <Layers className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
                Phase 4: Material Classification
                <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  ML Pipeline
                </span>
              </h1>
              <p className="text-sm text-slate-400">
                Identify probable construction substrates (sandstone, brick, lime mortar) for deterioration and temporal mapping.
              </p>
            </div>
          </div>
        </div>

        {/* Active Model Indicator Badge */}
        <div className="flex items-center gap-2 bg-slate-800/80 border border-slate-700 rounded-lg p-2 px-3 text-xs">
          <Cpu className="w-4 h-4 text-cyan-400" />
          <div>
            <div className="text-slate-400">Active Engine:</div>
            <div className="font-semibold text-slate-200">
              {activeModel?.name || 'Demo Heuristic Engine'}
              {activeModel?.is_demo ? (
                <span className="ml-1.5 px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px]">
                  DEMO MODE
                </span>
              ) : (
                <span className="ml-1.5 px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 text-[10px]">
                  REAL TRAINED
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 2. Mandatory Research Safety Disclaimer Alert */}
      <div className="p-3.5 rounded-xl bg-amber-950/20 border border-amber-500/30 text-xs text-amber-200/90 flex items-start gap-3">
        <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-semibold text-amber-300 uppercase tracking-wide text-[11px]">
            Academic & Field Research Safety Notice
          </div>
          <div>
            Material classification outputs represent probabilistic model predictions and associated confidence values.
            They should not be interpreted as definitive physical material identification without expert architectural conservator verification.
          </div>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-950/30 border border-red-500/30 text-red-300 text-sm rounded-lg flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-xs text-red-400 hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {/* 3. Navigation Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-slate-800 pb-2">
        <button
          onClick={() => setActiveTab('single')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'single'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
              : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
          }`}
        >
          <Sparkles className="w-4 h-4" />
          Single Image & Crop Inspector
        </button>

        <button
          onClick={() => setActiveTab('survey')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'survey'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
              : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          Survey Substrate Distribution
        </button>

        <button
          onClick={() => setActiveTab('taxonomy')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'taxonomy'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
              : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
          }`}
        >
          <Sliders className="w-4 h-4" />
          Configurable Taxonomy ({classes.length})
        </button>

        <button
          onClick={() => setActiveTab('models')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'models'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
              : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
          }`}
        >
          <Cpu className="w-4 h-4" />
          Model Provenance & Metrics
        </button>

        <button
          onClick={() => setActiveTab('dataset')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'dataset'
              ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
              : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
          }`}
        >
          <FolderKanban className="w-4 h-4" />
          Dataset Validator & Training
        </button>
      </div>

      {/* ============================================================== */}
      {/* TAB 1: Single Image & Crop Classifier                          */}
      {/* ============================================================== */}
      {activeTab === 'single' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left: Input & Preview */}
          <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-200 text-sm">Image Input & Substrate Region</h3>
              <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useCrop}
                  onChange={(e) => setUseCrop(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-800 text-cyan-500 focus:ring-cyan-500/20"
                />
                Define Sub-Region (Crop ROI)
              </label>
            </div>

            {/* Upload Area */}
            <div className="border-2 border-dashed border-slate-700 hover:border-slate-600 rounded-xl p-6 text-center cursor-pointer relative bg-slate-950/40">
              <input
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                className="absolute inset-0 opacity-0 cursor-pointer w-full h-full"
              />
              <Upload className="w-8 h-8 text-slate-400 mx-auto mb-2" />
              <div className="text-sm font-medium text-slate-200">
                {selectedFile ? selectedFile.name : 'Upload Heritage Site Photo'}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                Supports JPG, PNG, WebP masonry and substrate surface photographs
              </div>
            </div>

            {/* Preview & Crop Coordinates */}
            {previewUrl && (
              <div className="space-y-3">
                <div className="relative rounded-lg overflow-hidden border border-slate-800 bg-black/40 flex justify-center max-h-80">
                  <img src={previewUrl} alt="Preview" className="object-contain max-h-80 w-auto" />
                  {useCrop && (
                    <div
                      className="absolute border-2 border-amber-400 bg-amber-400/20 pointer-events-none"
                      style={{
                        top: `${cropBox.y}px`,
                        left: `${cropBox.x}px`,
                        width: `${cropBox.w}px`,
                        height: `${cropBox.h}px`,
                      }}
                    >
                      <span className="text-[10px] bg-amber-500 text-black px-1 font-bold absolute -top-4 left-0">
                        ROI Crop
                      </span>
                    </div>
                  )}
                </div>

                {useCrop && (
                  <div className="grid grid-cols-4 gap-2 text-xs bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                    <div>
                      <span className="text-slate-400">X Offset:</span>
                      <input
                        type="number"
                        value={cropBox.x}
                        onChange={(e) => setCropBox({ ...cropBox, x: parseInt(e.target.value) || 0 })}
                        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200 mt-0.5"
                      />
                    </div>
                    <div>
                      <span className="text-slate-400">Y Offset:</span>
                      <input
                        type="number"
                        value={cropBox.y}
                        onChange={(e) => setCropBox({ ...cropBox, y: parseInt(e.target.value) || 0 })}
                        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200 mt-0.5"
                      />
                    </div>
                    <div>
                      <span className="text-slate-400">Width:</span>
                      <input
                        type="number"
                        value={cropBox.w}
                        onChange={(e) => setCropBox({ ...cropBox, w: parseInt(e.target.value) || 100 })}
                        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200 mt-0.5"
                      />
                    </div>
                    <div>
                      <span className="text-slate-400">Height:</span>
                      <input
                        type="number"
                        value={cropBox.h}
                        onChange={(e) => setCropBox({ ...cropBox, h: parseInt(e.target.value) || 100 })}
                        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200 mt-0.5"
                      />
                    </div>
                  </div>
                )}

                <button
                  onClick={handlePredictSingle}
                  disabled={predicting}
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-white rounded-lg font-medium text-sm transition-all shadow-md shadow-amber-900/30 disabled:opacity-50"
                >
                  {predicting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Classifying Substrate...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Run Material Classification
                    </>
                  )}
                </button>
              </div>
            )}
          </div>

          {/* Right: Classification Results */}
          <div className="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <h3 className="font-semibold text-slate-200 text-sm">Classification Results</h3>

            {singleResult ? (
              <div className="space-y-4">
                {/* Primary Prediction Card */}
                <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-400 uppercase tracking-wide">Predicted Material</span>
                    <span
                      className={`text-xs px-2.5 py-0.5 rounded-full font-semibold ${
                        singleResult.status === 'CONFIDENT'
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                          : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      }`}
                    >
                      {singleResult.status}
                    </span>
                  </div>

                  <div className="flex items-center gap-3">
                    <div
                      className="w-5 h-5 rounded-md border border-white/20 shrink-0"
                      style={{
                        backgroundColor:
                          classes.find((c) => c.id === singleResult.material)?.color || '#38bdf8',
                      }}
                    />
                    <div className="text-xl font-bold text-slate-100 capitalize">
                      {classes.find((c) => c.id === singleResult.material)?.name || singleResult.material}
                    </div>
                  </div>

                  {/* Confidence Bar */}
                  <div>
                    <div className="flex justify-between text-xs text-slate-400 mb-1">
                      <span>Model Confidence:</span>
                      <span className="font-mono text-cyan-300 font-semibold">
                        {(singleResult.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                      <div
                        className="bg-gradient-to-r from-cyan-500 to-amber-400 h-2 rounded-full transition-all"
                        style={{ width: `${Math.min(100, singleResult.confidence * 100)}%` }}
                      />
                    </div>
                  </div>

                  {/* Low Confidence Warning */}
                  {singleResult.status === 'LOW_CONFIDENCE' && (
                    <div className="p-2.5 rounded-lg bg-amber-950/40 border border-amber-500/40 text-xs text-amber-200 flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold">Verification Recommended: </span>
                        {singleResult.recommendation || 'Material classification requires verification or additional imagery.'}
                      </div>
                    </div>
                  )}
                </div>

                {/* Top-K Probability Distribution */}
                {singleResult.top_k && singleResult.top_k.length > 0 && (
                  <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/80 space-y-2.5">
                    <div className="text-xs font-semibold text-slate-300 uppercase tracking-wide">
                      Top Candidate Substrates
                    </div>
                    <div className="space-y-2">
                      {singleResult.top_k.map((cand, idx) => {
                        const classDef = classes.find((c) => c.id === cand.material);
                        return (
                          <div key={idx} className="space-y-1">
                            <div className="flex justify-between text-xs">
                              <span className="text-slate-300 flex items-center gap-1.5 capitalize">
                                <span
                                  className="w-2.5 h-2.5 rounded-full inline-block"
                                  style={{ backgroundColor: classDef?.color || '#94a3b8' }}
                                />
                                {classDef?.name || cand.material}
                              </span>
                              <span className="text-slate-400 font-mono">
                                {(cand.confidence * 100).toFixed(1)}%
                              </span>
                            </div>
                            <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                              <div
                                className="h-1.5 rounded-full"
                                style={{
                                  width: `${Math.min(100, cand.confidence * 100)}%`,
                                  backgroundColor: classDef?.color || '#38bdf8',
                                }}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Model Provenance Footer */}
                <div className="text-[11px] text-slate-400 bg-slate-950/30 p-3 rounded-lg border border-slate-800/60 space-y-1">
                  <div className="flex justify-between">
                    <span>Engine:</span>
                    <span className="text-slate-200 font-medium">{singleResult.model_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Inference Mode:</span>
                    <span className="text-slate-200 font-medium">
                      {singleResult.is_demo ? 'Demo Heuristic Simulation' : 'Trained Deep Learning'}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="h-64 flex flex-col items-center justify-center text-center p-6 border border-slate-800/80 rounded-xl bg-slate-950/20 text-slate-500 space-y-2">
                <Sparkles className="w-8 h-8 text-slate-600" />
                <div className="text-sm font-medium text-slate-400">No Classification Performed Yet</div>
                <div className="text-xs max-w-xs">
                  Upload an image on the left and run classification to evaluate construction substrate.
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 2: Survey Material Analysis & Distribution Breakdown       */}
      {/* ============================================================== */}
      {activeTab === 'survey' && (
        <div className="space-y-6">
          {/* Survey Selector Bar */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3 w-full sm:w-auto">
              <FolderKanban className="w-5 h-5 text-cyan-400 shrink-0" />
              <div className="text-sm font-medium text-slate-300">Target Survey:</div>
              <select
                value={selectedSurveyId}
                onChange={(e) => setSelectedSurveyId(e.target.value)}
                className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-1.5 focus:ring-1 focus:ring-cyan-500"
              >
                {surveys.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.survey_code} — {s.description || 'Survey'} ({s.image_count} images)
                  </option>
                ))}
              </select>
            </div>

            <button
              onClick={handleAnalyzeSurvey}
              disabled={analyzingSurvey || !selectedSurveyId}
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-4 py-2 bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-white rounded-lg text-sm font-medium shadow-md shadow-amber-900/30 disabled:opacity-50"
            >
              {analyzingSurvey ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Analyzing All Images...
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4" />
                  Run Survey Substrate Analysis
                </>
              )}
            </button>
          </div>

          {/* Results Summary Cards */}
          {surveySummary ? (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                  <div className="text-xs text-slate-400 uppercase tracking-wide">Analyzed Images</div>
                  <div className="text-2xl font-bold text-slate-100 mt-1">
                    {surveySummary.analyzed_images} / {surveySummary.total_images}
                  </div>
                </div>

                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                  <div className="text-xs text-slate-400 uppercase tracking-wide">Dominant Substrate</div>
                  <div className="text-2xl font-bold text-amber-400 mt-1 capitalize">
                    {surveySummary.dominant_material || 'None'}
                  </div>
                </div>

                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                  <div className="text-xs text-slate-400 uppercase tracking-wide">Average Confidence</div>
                  <div className="text-2xl font-bold text-cyan-400 mt-1 font-mono">
                    {(surveySummary.overall_average_confidence * 100).toFixed(1)}%
                  </div>
                </div>

                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                  <div className="text-xs text-slate-400 uppercase tracking-wide">Low Confidence Count</div>
                  <div className="text-2xl font-bold text-slate-100 mt-1 flex items-center gap-2">
                    {surveySummary.low_confidence_count}
                    {surveySummary.low_confidence_count > 0 && (
                      <span className="text-xs font-normal text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                        Needs check
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Substrate Distribution Breakdown */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                <h3 className="font-semibold text-slate-200 text-sm flex items-center justify-between">
                  <span>Substrate Distribution</span>
                  <span className="text-xs font-normal text-slate-400">
                    Engine: {surveySummary.model_used} ({surveySummary.is_demo ? 'Demo' : 'Trained'})
                  </span>
                </h3>

                <div className="space-y-3">
                  {Object.entries(surveySummary.distribution_percentage).map(([matKey, pct]) => {
                    const count = surveySummary.distribution[matKey] || 0;
                    const avgConf = surveySummary.average_confidences[matKey] || 0;
                    const classDef = classes.find((c) => c.id === matKey);
                    const color = classDef?.color || '#38bdf8';

                    return (
                      <div key={matKey} className="space-y-1.5">
                        <div className="flex items-center justify-between text-xs">
                          <div className="flex items-center gap-2">
                            <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: color }} />
                            <span className="font-medium text-slate-200 capitalize">
                              {classDef?.name || matKey}
                            </span>
                          </div>
                          <div className="flex items-center gap-4 text-slate-400">
                            <span>{count} images ({pct}%)</span>
                            <span className="font-mono text-cyan-300">Avg Conf: {(avgConf * 100).toFixed(0)}%</span>
                          </div>
                        </div>

                        <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden">
                          <div
                            className="h-2.5 rounded-full transition-all"
                            style={{
                              width: `${pct}%`,
                              backgroundColor: color,
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Detections Records Table */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <div className="p-4 border-b border-slate-800 font-semibold text-sm text-slate-200">
                  Individual Image Detections ({surveySummary.detections.length})
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wide border-b border-slate-800">
                      <tr>
                        <th className="px-4 py-3">Detection ID</th>
                        <th className="px-4 py-3">Material Class</th>
                        <th className="px-4 py-3">Model Confidence</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3">Inference Mode</th>
                        <th className="px-4 py-3">Notes</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {surveySummary.detections.map((det) => (
                        <tr key={det.id} className="hover:bg-slate-800/30">
                          <td className="px-4 py-2.5 font-mono text-[11px] text-slate-400">
                            {det.id.slice(0, 8)}...
                          </td>
                          <td className="px-4 py-2.5 font-medium text-slate-200 capitalize">
                            <span
                              className="inline-block w-2.5 h-2.5 rounded-full mr-2"
                              style={{
                                backgroundColor:
                                  classes.find((c) => c.id === det.material_class)?.color || '#94a3b8',
                              }}
                            />
                            {det.material_class}
                          </td>
                          <td className="px-4 py-2.5 font-mono text-cyan-300">
                            {(det.confidence * 100).toFixed(1)}%
                          </td>
                          <td className="px-4 py-2.5">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                det.status === 'CONFIDENT'
                                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                  : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                              }`}
                            >
                              {det.status}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 text-slate-400">
                            {det.is_demo ? 'Demo Simulation' : 'Trained Model'}
                          </td>
                          <td className="px-4 py-2.5 text-slate-400 truncate max-w-xs">
                            {det.notes || '—'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center space-y-3">
              <BarChart3 className="w-10 h-10 text-slate-600 mx-auto" />
              <div className="text-slate-300 font-medium">No Survey Analysis Results Yet</div>
              <div className="text-xs text-slate-500 max-w-sm mx-auto">
                Click "Run Survey Substrate Analysis" above to process all images in this survey and compute material distribution.
              </div>
            </div>
          )}
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 3: Configurable Substrate Taxonomy (Class Registry)         */}
      {/* ============================================================== */}
      {activeTab === 'taxonomy' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="font-semibold text-slate-200 text-base">Heritage Material Substrate Classes</h3>
              <p className="text-xs text-slate-400">
                Configurable taxonomy of masonry materials. Classes can be enabled, added, or disabled per project context.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowAddClass(!showAddClass)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-medium transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add Substrate Class
              </button>
              <button
                onClick={handleResetClasses}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-xs font-medium transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                Reset Defaults
              </button>
            </div>
          </div>

          {/* Add Class Form Modal / Collapsible */}
          {showAddClass && (
            <form onSubmit={handleAddClass} className="bg-slate-900 border border-cyan-500/30 rounded-xl p-4 space-y-4">
              <div className="text-sm font-semibold text-cyan-300">Add New Substrate Class</div>
              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                <div>
                  <label className="text-xs text-slate-400">Identifier (id):</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. travertine"
                    value={newClassId}
                    onChange={(e) => setNewClassId(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 mt-1"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400">Display Name:</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Travertine Stone"
                    value={newClassName}
                    onChange={(e) => setNewClassName(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 mt-1"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400">Color Swatch:</label>
                  <div className="flex items-center gap-2 mt-1">
                    <input
                      type="color"
                      value={newClassColor}
                      onChange={(e) => setNewClassColor(e.target.value)}
                      className="w-8 h-8 rounded border-0 cursor-pointer bg-transparent"
                    />
                    <span className="font-mono text-xs text-slate-300">{newClassColor}</span>
                  </div>
                </div>
                <div>
                  <label className="text-xs text-slate-400">Description:</label>
                  <input
                    type="text"
                    placeholder="e.g. Calcareous sedimentary rock"
                    value={newClassDesc}
                    onChange={(e) => setNewClassDesc(e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 mt-1"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddClass(false)}
                  className="px-3 py-1.5 rounded text-xs text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded text-xs font-medium"
                >
                  Save Class
                </button>
              </div>
            </form>
          )}

          {/* Classes Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {classes.map((cls) => (
              <div
                key={cls.id}
                className={`p-4 rounded-xl border transition-all ${
                  cls.enabled
                    ? 'bg-slate-900 border-slate-800'
                    : 'bg-slate-950/40 border-slate-800/40 opacity-60'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2.5">
                    <span
                      className="w-4 h-4 rounded-md shrink-0 border border-white/20 shadow-sm"
                      style={{ backgroundColor: cls.color }}
                    />
                    <div>
                      <h4 className="font-semibold text-slate-100 text-sm">{cls.name}</h4>
                      <span className="font-mono text-[11px] text-slate-500">{cls.id}</span>
                    </div>
                  </div>

                  <button
                    onClick={() => handleToggleClass(cls)}
                    className={`text-xs px-2.5 py-1 rounded font-medium transition-colors ${
                      cls.enabled
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-slate-800 text-slate-400 border border-slate-700'
                    }`}
                  >
                    {cls.enabled ? 'Enabled' : 'Disabled'}
                  </button>
                </div>

                <p className="text-xs text-slate-400 mt-3 line-clamp-2">
                  {cls.description || 'No description provided.'}
                </p>

                {cls.is_default && (
                  <div className="mt-3 pt-2 border-t border-slate-800/60 text-[10px] text-slate-500">
                    Baseline heritage taxonomy class
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 4: Model Provenance & Real Evaluation Metrics              */}
      {/* ============================================================== */}
      {activeTab === 'models' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-slate-200 text-base">Registered Material Models</h3>
              <p className="text-xs text-slate-400">
                Introspect machine learning models, architecture backbones, and genuinely computed test metrics.
              </p>
            </div>
            <button
              onClick={loadModels}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-xs font-medium"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Refresh Registry
            </button>
          </div>

          <div className="space-y-4">
            {models.map((mod) => (
              <div
                key={mod.id}
                className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800/80 pb-3">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <h4 className="font-bold text-slate-100 text-base">{mod.name}</h4>
                      <span className="text-xs font-mono bg-slate-800 text-slate-300 px-2 py-0.5 rounded">
                        {mod.version}
                      </span>
                      {mod.is_active && (
                        <span className="text-xs bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded font-medium">
                          Active
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-slate-400 mt-1">
                      Architecture: <span className="text-slate-300 font-mono">{mod.architecture}</span> | Mode:{' '}
                      <span className="text-slate-300 font-medium">
                        {mod.is_demo ? 'Demo Heuristic Simulation' : 'Deep Transfer Learning'}
                      </span>
                    </div>
                  </div>

                  <div className="text-xs text-slate-400">
                    Classes: <span className="text-slate-200 font-medium">{mod.classes.length}</span>
                  </div>
                </div>

                {/* Genuine Metrics Section */}
                {mod.metrics ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                        <div className="text-[11px] text-slate-400 uppercase">Test Accuracy</div>
                        <div className="text-xl font-bold text-emerald-400 font-mono mt-0.5">
                          {((mod.metrics.accuracy || 0) * 100).toFixed(1)}%
                        </div>
                      </div>
                      <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                        <div className="text-[11px] text-slate-400 uppercase">Macro F1 Score</div>
                        <div className="text-xl font-bold text-cyan-400 font-mono mt-0.5">
                          {(mod.metrics.macro_f1 || 0).toFixed(3)}
                        </div>
                      </div>
                      <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                        <div className="text-[11px] text-slate-400 uppercase">Macro Precision</div>
                        <div className="text-xl font-bold text-slate-200 font-mono mt-0.5">
                          {(mod.metrics.macro_precision || 0).toFixed(3)}
                        </div>
                      </div>
                      <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                        <div className="text-[11px] text-slate-400 uppercase">Evaluated Samples</div>
                        <div className="text-xl font-bold text-slate-200 font-mono mt-0.5">
                          {mod.metrics.total_evaluated_samples || 0}
                        </div>
                      </div>
                    </div>

                    {/* Per-class Metrics Table */}
                    {mod.metrics.per_class && (
                      <div className="overflow-x-auto">
                        <table className="w-full text-left text-xs text-slate-300">
                          <thead className="bg-slate-950/40 text-slate-400 uppercase tracking-wide">
                            <tr>
                              <th className="px-3 py-2">Class</th>
                              <th className="px-3 py-2">Precision</th>
                              <th className="px-3 py-2">Recall</th>
                              <th className="px-3 py-2">F1 Score</th>
                              <th className="px-3 py-2">Support</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/40">
                            {Object.entries(mod.metrics.per_class).map(([cName, cm]) => (
                              <tr key={cName}>
                                <td className="px-3 py-2 font-medium capitalize text-slate-200">{cName}</td>
                                <td className="px-3 py-2 font-mono">{cm.precision.toFixed(3)}</td>
                                <td className="px-3 py-2 font-mono">{cm.recall.toFixed(3)}</td>
                                <td className="px-3 py-2 font-mono text-cyan-300">{cm.f1_score.toFixed(3)}</td>
                                <td className="px-3 py-2 font-mono text-slate-400">{cm.support}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="bg-slate-950/40 p-4 rounded-lg border border-slate-800/60 text-xs text-slate-400 flex items-center gap-2">
                    <Info className="w-4 h-4 text-cyan-400 shrink-0" />
                    <span>
                      {mod.is_demo
                        ? 'Operating in Demo Heuristic Mode: No synthetic evaluation metrics fabricated. System uses calibrated chromatic and texture rule sets.'
                        : 'No validated test evaluation metrics available for this checkpoint.'}
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 5: Dataset Structure & Imbalance Validator                 */}
      {/* ============================================================== */}
      {activeTab === 'dataset' && (
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <h3 className="font-semibold text-slate-200 text-sm">Heritage Substrate Dataset Validation</h3>
            <p className="text-xs text-slate-400">
              Scans dataset directories for proper train/val/test splits, image corruptions, and class imbalance before model fine-tuning.
            </p>

            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                value={datasetPathInput}
                onChange={(e) => setDatasetPathInput(e.target.value)}
                placeholder="data/datasets/materials"
                className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200"
              />
              <button
                onClick={handleValidateDataset}
                disabled={validatingDataset}
                className="flex items-center justify-center gap-2 px-5 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm font-medium disabled:opacity-50"
              >
                {validatingDataset ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Validating Structure...
                  </>
                ) : (
                  'Validate Dataset'
                )}
              </button>
            </div>
          </div>

          {datasetReport && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="font-semibold text-slate-200 text-sm">Validation Diagnostic Report</h4>
                <span
                  className={`text-xs px-2.5 py-0.5 rounded-full font-bold ${
                    datasetReport.status === 'VALID'
                      ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      : datasetReport.status === 'WARNING'
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                      : 'bg-red-500/20 text-red-300 border border-red-500/30'
                  }`}
                >
                  STATUS: {datasetReport.status}
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                  <span className="text-slate-400">Total Samples:</span>
                  <div className="text-lg font-bold text-slate-100 mt-0.5">{datasetReport.total_samples}</div>
                </div>
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                  <span className="text-slate-400">Classes Identified:</span>
                  <div className="text-lg font-bold text-slate-100 mt-0.5">{datasetReport.num_classes}</div>
                </div>
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                  <span className="text-slate-400">Imbalance Ratio:</span>
                  <div className="text-lg font-bold text-amber-400 mt-0.5 font-mono">
                    {datasetReport.imbalance_ratio !== null && datasetReport.imbalance_ratio !== undefined
                      ? `${datasetReport.imbalance_ratio.toFixed(2)}x`
                      : 'N/A'}
                  </div>
                </div>
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                  <span className="text-slate-400">Errors Detected:</span>
                  <div className="text-lg font-bold text-red-400 mt-0.5">{datasetReport.errors.length}</div>
                </div>
              </div>

              {/* Errors & Warnings */}
              {datasetReport.errors.length > 0 && (
                <div className="p-3 bg-red-950/30 border border-red-500/30 rounded-lg text-xs text-red-300 space-y-1">
                  <div className="font-semibold">Errors:</div>
                  {datasetReport.errors.map((err, i) => (
                    <div key={i}>• {err}</div>
                  ))}
                </div>
              )}

              {datasetReport.warnings.length > 0 && (
                <div className="p-3 bg-amber-950/30 border border-amber-500/30 rounded-lg text-xs text-amber-300 space-y-1">
                  <div className="font-semibold">Warnings:</div>
                  {datasetReport.warnings.map((w, i) => (
                    <div key={i}>• {w}</div>
                  ))}
                </div>
              )}

              {/* Recommendation */}
              <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg text-xs text-slate-300">
                <span className="font-semibold text-cyan-400">Recommendation: </span>
                {datasetReport.recommendation}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
