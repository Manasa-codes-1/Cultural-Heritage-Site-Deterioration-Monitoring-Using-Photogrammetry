import React, { useState, useEffect } from 'react';
import {
  Flame,
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
  Eye,
  EyeOff,
  Link,
  Table,
} from 'lucide-react';
import { api } from '../api/client';
import type {
  Survey,
  DeteriorationClassItem,
  DeteriorationModelSummary,
  DeteriorationPredictionResponse,
  SurveyDeteriorationAnalysisSummary,
  DeteriorationDatasetValidationReport,
} from '../types';

interface DeteriorationDetectionPageProps {
  initialSurveyId?: string;
  onNavigateToSurveys?: () => void;
}

export const DeteriorationDetectionPage: React.FC<DeteriorationDetectionPageProps> = ({
  initialSurveyId,
}) => {
  const [activeTab, setActiveTab] = useState<'single' | 'survey' | 'taxonomy' | 'models' | 'dataset'>('single');
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [selectedSurveyId, setSelectedSurveyId] = useState<string>(initialSurveyId || '');
  const [classes, setClasses] = useState<DeteriorationClassItem[]>([]);
  const [models, setModels] = useState<DeteriorationModelSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Single Prediction & Visual Overlay Controls
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [singleResult, setSingleResult] = useState<DeteriorationPredictionResponse | null>(null);
  const [predicting, setPredicting] = useState(false);
  const [showOverlays, setShowOverlays] = useState(true);
  const [showLabels, setShowLabels] = useState(true);
  const [filterClass, setFilterClass] = useState<string>('all');
  const [minConfidenceFilter, setMinConfidenceFilter] = useState<number>(0.20);

  // Survey Analysis State
  const [surveySummary, setSurveySummary] = useState<SurveyDeteriorationAnalysisSummary | null>(null);
  const [analyzingSurvey, setAnalyzingSurvey] = useState(false);

  // Taxonomy Form State
  const [newClassId, setNewClassId] = useState('');
  const [newClassName, setNewClassName] = useState('');
  const [newClassColor, setNewClassColor] = useState('#ef4444');
  const [newClassDesc, setNewClassDesc] = useState('');
  const [newClassSeverity, setNewClassSeverity] = useState(0.5);
  const [showAddClass, setShowAddClass] = useState(false);

  // Dataset Validator State
  const [datasetPathInput, setDatasetPathInput] = useState('data/datasets/deterioration');
  const [datasetReport, setDatasetReport] = useState<DeteriorationDatasetValidationReport | null>(null);
  const [validatingDataset, setValidatingDataset] = useState(false);

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
      const data = await api.getDeteriorationClasses();
      setClasses(data);
    } catch (err: any) {
      console.error('Failed to load classes', err);
    }
  };

  const loadModels = async () => {
    try {
      const data = await api.getDeteriorationModels();
      setModels(data);
    } catch (err: any) {
      console.error('Failed to load models', err);
    }
  };

  const loadSurveyResults = async (srvId: string) => {
    try {
      const res = await api.getSurveyDeteriorationResults(srvId);
      setSurveySummary(res);
    } catch {
      setSurveySummary(null);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
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
      const res = await api.predictDeterioration(formData);
      setSingleResult(res);
    } catch (err: any) {
      setError(err.message || 'Defect detection failed');
    } finally {
      setPredicting(false);
    }
  };

  const handleAnalyzeSurvey = async () => {
    if (!selectedSurveyId) return;
    setAnalyzingSurvey(true);
    setError(null);
    try {
      const summary = await api.analyzeSurveyDeterioration(selectedSurveyId);
      setSurveySummary(summary);
    } catch (err: any) {
      setError(err.message || 'Survey deterioration analysis failed');
    } finally {
      setAnalyzingSurvey(false);
    }
  };

  const handleAddClass = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newClassId.trim() || !newClassName.trim()) return;
    try {
      await api.createDeteriorationClass({
        id: newClassId.trim(),
        name: newClassName.trim(),
        color: newClassColor,
        description: newClassDesc.trim(),
        severity_weight: newClassSeverity,
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

  const handleToggleClass = async (item: DeteriorationClassItem) => {
    try {
      await api.updateDeteriorationClass(item.id, { enabled: !item.enabled });
      loadClasses();
    } catch (err: any) {
      setError(err.message || 'Failed to update class');
    }
  };

  const handleResetClasses = async () => {
    if (!window.confirm('Reset defect taxonomy to baseline heritage categories?')) return;
    try {
      await api.resetDeteriorationClasses();
      loadClasses();
    } catch (err: any) {
      setError(err.message || 'Failed to reset classes');
    }
  };

  const handleValidateDataset = async () => {
    setValidatingDataset(true);
    setError(null);
    try {
      const rep = await api.validateDeteriorationDataset(datasetPathInput);
      setDatasetReport(rep);
    } catch (err: any) {
      setError(err.message || 'Dataset validation failed');
    } finally {
      setValidatingDataset(false);
    }
  };

  const activeModel = models.find((m) => m.is_active) || models[0];

  const visibleDetections = (singleResult?.detections || []).filter((d) => {
    if (filterClass !== 'all' && d.damage_type !== filterClass) return false;
    if (d.confidence < minConfidenceFilter) return false;
    return true;
  });

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* 1. Header with Research Safety Notice */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-700/60 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
              <Flame className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
                Phase 5: Deterioration Detection
                <span className="text-xs px-2.5 py-0.5 rounded-full font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
                  ML Pipeline
                </span>
              </h1>
              <p className="text-sm text-slate-400">
                Localize physical defects (cracks, erosion, spalling) and link them directly to substrate construction materials.
              </p>
            </div>
          </div>
        </div>

        {/* Active Model Indicator Badge */}
        <div className="flex items-center gap-2 bg-slate-800/80 border border-slate-700 rounded-lg p-2 px-3 text-xs">
          <Cpu className="w-4 h-4 text-rose-400" />
          <div>
            <div className="text-slate-400">Active Engine:</div>
            <div className="font-semibold text-slate-200">
              {activeModel?.name || 'Demo Defect Detector'}
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
            Deterioration predictions represent probabilistic computer vision outputs and associated model confidence values.
            They require architectural conservator validation and should not be interpreted as definitive physical or structural assessments.
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
              ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
              : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
          }`}
        >
          <Flame className="w-4 h-4" />
          Single Image & Defect Overlays
        </button>

        <button
          onClick={() => setActiveTab('survey')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'survey'
              ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
              : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
          }`}
        >
          <Table className="w-4 h-4" />
          Survey Cross-Tabulation (Material × Damage)
        </button>

        <button
          onClick={() => setActiveTab('taxonomy')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'taxonomy'
              ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
              : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
          }`}
        >
          <Sliders className="w-4 h-4" />
          Defect Taxonomy ({classes.length})
        </button>

        <button
          onClick={() => setActiveTab('models')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'models'
              ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
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
              ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
              : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
          }`}
        >
          <FolderKanban className="w-4 h-4" />
          Defect Dataset Validator
        </button>
      </div>

      {/* ============================================================== */}
      {/* TAB 1: Single Image Defect Inspector & Visual Overlay          */}
      {/* ============================================================== */}
      {activeTab === 'single' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left: Input & Canvas Preview with Overlays */}
          <div className="lg:col-span-7 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-200 text-sm">Masonry Photo & Defect Overlays</h3>
              {singleResult && (
                <div className="flex items-center gap-3 text-xs text-slate-300">
                  <button
                    onClick={() => setShowOverlays(!showOverlays)}
                    className="flex items-center gap-1 hover:text-rose-400"
                  >
                    {showOverlays ? <Eye className="w-3.5 h-3.5" /> : <EyeOff className="w-3.5 h-3.5" />}
                    <span>Overlays</span>
                  </button>
                  <button
                    onClick={() => setShowLabels(!showLabels)}
                    className="flex items-center gap-1 hover:text-rose-400"
                  >
                    <span>Labels: {showLabels ? 'On' : 'Off'}</span>
                  </button>
                </div>
              )}
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
                {selectedFile ? selectedFile.name : 'Upload Heritage Masonry Photo'}
              </div>
              <div className="text-xs text-slate-500 mt-1">
                Supports high-resolution JPG, PNG, and WebP surface images
              </div>
            </div>

            {/* Visual Display with Bounding Boxes */}
            {previewUrl && (
              <div className="space-y-3">
                <div className="relative rounded-lg overflow-hidden border border-slate-800 bg-black/50 flex justify-center max-h-96">
                  <img
                    id="preview-defect-img"
                    src={previewUrl}
                    alt="Preview"
                    className="object-contain max-h-96 w-auto block"
                  />

                  {/* SVG Overlay for Bounding Boxes and Polygons */}
                  {showOverlays && singleResult && (
                    <svg className="absolute inset-0 w-full h-full pointer-events-none">
                      {visibleDetections.map((d, i) => {
                        const bbox = d.bounding_box;
                        if (!bbox) return null;
                        const classDef = classes.find((c) => c.id === d.damage_type);
                        const strokeColor = classDef?.color || '#ef4444';

                        return (
                          <g key={d.id || i}>
                            <rect
                              x={`${bbox.x}px`}
                              y={`${bbox.y}px`}
                              width={`${bbox.w}px`}
                              height={`${bbox.h}px`}
                              fill={`${strokeColor}25`}
                              stroke={strokeColor}
                              strokeWidth="2"
                              strokeDasharray={d.status === 'LOW_CONFIDENCE' ? '4,4' : undefined}
                            />
                            {showLabels && (
                              <text
                                x={`${bbox.x + 4}px`}
                                y={`${bbox.y - 4}px`}
                                fill="#ffffff"
                                fontSize="11"
                                fontWeight="bold"
                                style={{
                                  textShadow: '0 1px 3px rgba(0,0,0,0.9)',
                                  backgroundColor: strokeColor,
                                }}
                              >
                                {classDef?.name || d.damage_type} ({(d.confidence * 100).toFixed(0)}%)
                              </text>
                            )}
                          </g>
                        );
                      })}
                    </svg>
                  )}
                </div>

                {/* Filter and threshold sliders */}
                {singleResult && (
                  <div className="grid grid-cols-2 gap-3 text-xs bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                    <div>
                      <span className="text-slate-400">Filter Defect Type:</span>
                      <select
                        value={filterClass}
                        onChange={(e) => setFilterClass(e.target.value)}
                        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-200 mt-1"
                      >
                        <option value="all">All Defect Types</option>
                        {classes.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <div className="flex justify-between text-slate-400">
                        <span>Min Confidence:</span>
                        <span className="font-mono text-rose-300">{(minConfidenceFilter * 100).toFixed(0)}%</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.05"
                        value={minConfidenceFilter}
                        onChange={(e) => setMinConfidenceFilter(parseFloat(e.target.value))}
                        className="w-full mt-2 accent-rose-500"
                      />
                    </div>
                  </div>
                )}

                <button
                  onClick={handlePredictSingle}
                  disabled={predicting}
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-gradient-to-r from-rose-600 to-rose-500 hover:from-rose-500 hover:to-rose-400 text-white rounded-lg font-medium text-sm transition-all shadow-md shadow-rose-900/30 disabled:opacity-50"
                >
                  {predicting ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      Analyzing Deterioration...
                    </>
                  ) : (
                    <>
                      <Flame className="w-4 h-4" />
                      Detect Physical Deterioration
                    </>
                  )}
                </button>
              </div>
            )}
          </div>

          {/* Right: Detections & Material Association Results */}
          <div className="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-slate-200 text-sm">Detected Deterioration Items</h3>
              {singleResult && (
                <span className="text-xs text-slate-400">
                  Showing {visibleDetections.length} of {singleResult.detections_count}
                </span>
              )}
            </div>

            {singleResult ? (
              <div className="space-y-3 max-h-[520px] overflow-y-auto pr-1">
                {visibleDetections.length > 0 ? (
                  visibleDetections.map((det, idx) => {
                    const classDef = classes.find((c) => c.id === det.damage_type);
                    const color = classDef?.color || '#ef4444';

                    return (
                      <div
                        key={det.id || idx}
                        className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-2.5 hover:border-slate-700 transition-colors"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-2">
                            <span className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: color }} />
                            <div className="font-semibold text-sm text-slate-100 capitalize">
                              {classDef?.name || det.damage_type}
                            </div>
                          </div>
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                              det.status === 'CONFIDENT'
                                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                                : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                            }`}
                          >
                            {det.status}
                          </span>
                        </div>

                        {/* Model Confidence Bar */}
                        <div>
                          <div className="flex justify-between text-xs text-slate-400 mb-1">
                            <span>Model Confidence:</span>
                            <span className="font-mono text-rose-300 font-semibold">
                              {(det.confidence * 100).toFixed(1)}%
                            </span>
                          </div>
                          <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                            <div
                              className="h-1.5 rounded-full transition-all"
                              style={{
                                width: `${Math.min(100, det.confidence * 100)}%`,
                                backgroundColor: color,
                              }}
                            />
                          </div>
                        </div>

                        {/* Material-Damage Association Badge (The Core Research Link!) */}
                        <div className="bg-slate-900/80 p-2 rounded-lg border border-slate-800 text-xs space-y-1">
                          <div className="flex items-center justify-between text-[11px] text-slate-400">
                            <span className="flex items-center gap-1">
                              <Link className="w-3 h-3 text-cyan-400" />
                              Associated Substrate:
                            </span>
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                                det.material_association_status === 'ASSOCIATED'
                                  ? 'bg-cyan-500/10 text-cyan-300 border border-cyan-500/20'
                                  : det.material_association_status === 'OVERLAPPING_MULTIPLE'
                                  ? 'bg-amber-500/10 text-amber-300 border border-amber-500/20'
                                  : 'bg-slate-800 text-slate-400'
                              }`}
                            >
                              {det.material_association_status}
                            </span>
                          </div>

                          <div className="flex items-center justify-between font-medium">
                            <span className="text-slate-200 capitalize">
                              {det.material_class !== 'UNKNOWN' ? det.material_class : 'Substrate Unknown'}
                            </span>
                            {det.material_confidence !== null && det.material_confidence !== undefined && (
                              <span className="font-mono text-cyan-400 text-[11px]">
                                Mat Conf: {(det.material_confidence * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Low-confidence advice */}
                        {det.status === 'LOW_CONFIDENCE' && (
                          <div className="p-2 rounded bg-amber-950/30 border border-amber-500/30 text-[11px] text-amber-200 flex items-start gap-1.5">
                            <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                            <span>Detection requires verification or additional imagery.</span>
                          </div>
                        )}
                      </div>
                    );
                  })
                ) : (
                  <div className="p-6 text-center text-xs text-slate-500 bg-slate-950/30 rounded-xl border border-slate-800">
                    No detections match current filter criteria.
                  </div>
                )}
              </div>
            ) : (
              <div className="h-64 flex flex-col items-center justify-center text-center p-6 border border-slate-800/80 rounded-xl bg-slate-950/20 text-slate-500 space-y-2">
                <Flame className="w-8 h-8 text-slate-600" />
                <div className="text-sm font-medium text-slate-400">No Deterioration Detected Yet</div>
                <div className="text-xs max-w-xs">
                  Upload an image on the left and run detection to locate physical cracks and surface defects.
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 2: Survey Cross-Tabulation (Material x Damage)             */}
      {/* ============================================================== */}
      {activeTab === 'survey' && (
        <div className="space-y-6">
          {/* Survey Selector Bar */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3 w-full sm:w-auto">
              <FolderKanban className="w-5 h-5 text-rose-400 shrink-0" />
              <div className="text-sm font-medium text-slate-300">Target Survey:</div>
              <select
                value={selectedSurveyId}
                onChange={(e) => setSelectedSurveyId(e.target.value)}
                className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-1.5 focus:ring-1 focus:ring-rose-500"
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
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-4 py-2 bg-gradient-to-r from-rose-600 to-rose-500 hover:from-rose-500 hover:to-rose-400 text-white rounded-lg text-sm font-medium shadow-md shadow-rose-900/30 disabled:opacity-50"
            >
              {analyzingSurvey ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Analyzing All Images...
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4" />
                  Run Survey Defect Analysis
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
                  <div className="text-xs text-slate-400 uppercase tracking-wide">Total Defects Located</div>
                  <div className="text-2xl font-bold text-rose-400 mt-1">
                    {surveySummary.total_detections}
                  </div>
                </div>

                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                  <div className="text-xs text-slate-400 uppercase tracking-wide">Average Confidence</div>
                  <div className="text-2xl font-bold text-cyan-400 mt-1 font-mono">
                    {(surveySummary.average_confidence * 100).toFixed(1)}%
                  </div>
                </div>

                <div className="bg-slate-900 border border-slate-800 p-4 rounded-xl">
                  <div className="text-xs text-slate-400 uppercase tracking-wide">Low Confidence Count</div>
                  <div className="text-2xl font-bold text-slate-100 mt-1 flex items-center gap-2">
                    {surveySummary.low_confidence_count}
                    {surveySummary.low_confidence_count > 0 && (
                      <span className="text-xs font-normal text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                        Needs verify
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* CORE RESEARCH COMPONENT: Material x Damage Cross-Tabulation Matrix */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-slate-200 text-sm flex items-center gap-2">
                      <Table className="w-4 h-4 text-cyan-400" />
                      Material-Aware Cross-Tabulation Matrix (Material × Deterioration Type)
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Quantifies defect occurrences anchored to identified construction substrates.
                    </p>
                  </div>
                  <span className="text-xs font-mono text-slate-400">
                    Engine: {surveySummary.model_used}
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wide border-b border-slate-800">
                      <tr>
                        <th className="px-4 py-3">Substrate Material</th>
                        {classes.map((cls) => (
                          <th key={cls.id} className="px-4 py-3 text-center">
                            <span className="inline-block w-2 h-2 rounded-full mr-1.5" style={{ backgroundColor: cls.color }} />
                            {cls.name}
                          </th>
                        ))}
                        <th className="px-4 py-3 text-right">Row Total</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {Object.keys(surveySummary.material_damage_crosstab).length > 0 ? (
                        Object.entries(surveySummary.material_damage_crosstab).map(([mat, row]) => {
                          const rowTotal = Object.values(row).reduce((a, b) => a + b, 0);
                          return (
                            <tr key={mat} className="hover:bg-slate-800/30">
                              <td className="px-4 py-2.5 font-semibold text-slate-200 capitalize">
                                {mat}
                              </td>
                              {classes.map((cls) => {
                                const count = row[cls.id] || 0;
                                return (
                                  <td
                                    key={cls.id}
                                    className={`px-4 py-2.5 text-center font-mono ${
                                      count > 0 ? 'text-rose-300 font-bold bg-rose-500/10' : 'text-slate-600'
                                    }`}
                                  >
                                    {count}
                                  </td>
                                );
                              })}
                              <td className="px-4 py-2.5 text-right font-bold text-slate-100 font-mono">
                                {rowTotal}
                              </td>
                            </tr>
                          );
                        })
                      ) : (
                        <tr>
                          <td colSpan={classes.length + 2} className="px-4 py-6 text-center text-slate-500">
                            No material-deterioration associations recorded yet.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Detections Records Table */}
              <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
                <div className="p-4 border-b border-slate-800 font-semibold text-sm text-slate-200">
                  Individual Defect Records ({surveySummary.detections.length})
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wide border-b border-slate-800">
                      <tr>
                        <th className="px-4 py-3">ID</th>
                        <th className="px-4 py-3">Defect Type</th>
                        <th className="px-4 py-3">Confidence</th>
                        <th className="px-4 py-3">Substrate Material</th>
                        <th className="px-4 py-3">Association Status</th>
                        <th className="px-4 py-3">Bounding Box</th>
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
                              className="inline-block w-2 h-2 rounded-full mr-2"
                              style={{
                                backgroundColor:
                                  classes.find((c) => c.id === det.damage_type)?.color || '#ef4444',
                              }}
                            />
                            {det.damage_type}
                          </td>
                          <td className="px-4 py-2.5 font-mono text-rose-300">
                            {(det.confidence * 100).toFixed(1)}%
                          </td>
                          <td className="px-4 py-2.5 capitalize text-slate-200">
                            {det.material_class}
                          </td>
                          <td className="px-4 py-2.5">
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                                det.material_association_status === 'ASSOCIATED'
                                  ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/20'
                                  : 'bg-slate-800 text-slate-400'
                              }`}
                            >
                              {det.material_association_status}
                            </span>
                          </td>
                          <td className="px-4 py-2.5 font-mono text-[11px] text-slate-400">
                            {det.bounding_box
                              ? `[${det.bounding_box.x}, ${det.bounding_box.y}, ${det.bounding_box.w}x${det.bounding_box.h}]`
                              : 'None'}
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
              <div className="text-slate-300 font-medium">No Survey Defect Analysis Results Yet</div>
              <div className="text-xs text-slate-500 max-w-sm mx-auto">
                Click "Run Survey Defect Analysis" above to process all images in this survey and build the material-defect cross-tabulation.
              </div>
            </div>
          )}
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 3: Configurable Defect Taxonomy                             */}
      {/* ============================================================== */}
      {activeTab === 'taxonomy' && (
        <div className="space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h3 className="font-semibold text-slate-200 text-base">Physical Deterioration Taxonomy</h3>
              <p className="text-xs text-slate-400">
                Configurable taxonomy of physical defect classes. Classes can be added, disabled, or tuned with severity weights.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowAddClass(!showAddClass)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-medium transition-colors"
              >
                <Plus className="w-4 h-4" />
                Add Defect Class
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

          {showAddClass && (
            <form onSubmit={handleAddClass} className="bg-slate-900 border border-rose-500/30 rounded-xl p-4 space-y-4">
              <div className="text-sm font-semibold text-rose-300">Add New Deterioration Class</div>
              <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
                <div>
                  <label className="text-xs text-slate-400">Identifier (id):</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. detachment"
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
                    placeholder="e.g. Mortar Detachment"
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
                  <label className="text-xs text-slate-400">Severity Weight (0-1):</label>
                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.05"
                    value={newClassSeverity}
                    onChange={(e) => setNewClassSeverity(parseFloat(e.target.value) || 0.5)}
                    className="w-full bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 mt-1"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400">Description:</label>
                  <input
                    type="text"
                    placeholder="e.g. Flaking mortar bedding"
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
                  className="px-4 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded text-xs font-medium"
                >
                  Save Class
                </button>
              </div>
            </form>
          )}

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

                <div className="mt-3 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-500">
                  <span>Severity Weight:</span>
                  <span className="font-mono text-rose-300 font-semibold">{cls.severity_weight}</span>
                </div>
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
              <h3 className="font-semibold text-slate-200 text-base">Registered Deterioration Models</h3>
              <p className="text-xs text-slate-400">
                Inspect physical defect localization backbones and genuine mAP evaluation metrics.
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
              <div key={mod.id} className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
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
                        {mod.is_demo ? 'Demo Heuristic Simulation' : 'Deep Object Detection'}
                      </span>
                    </div>
                  </div>

                  <div className="text-xs text-slate-400">
                    Classes: <span className="text-slate-200 font-medium">{mod.classes.length}</span>
                  </div>
                </div>

                {mod.metrics ? (
                  <div className="space-y-4">
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                        <div className="text-[11px] text-slate-400 uppercase">mAP @ 0.50 IoU</div>
                        <div className="text-xl font-bold text-emerald-400 font-mono mt-0.5">
                          {((mod.metrics.mAP_50 || 0) * 100).toFixed(1)}%
                        </div>
                      </div>
                      <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                        <div className="text-[11px] text-slate-400 uppercase">Macro Precision</div>
                        <div className="text-xl font-bold text-cyan-400 font-mono mt-0.5">
                          {(mod.metrics.macro_precision || 0).toFixed(3)}
                        </div>
                      </div>
                      <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                        <div className="text-[11px] text-slate-400 uppercase">Macro Recall</div>
                        <div className="text-xl font-bold text-slate-200 font-mono mt-0.5">
                          {(mod.metrics.macro_recall || 0).toFixed(3)}
                        </div>
                      </div>
                      <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                        <div className="text-[11px] text-slate-400 uppercase">Evaluated Images</div>
                        <div className="text-xl font-bold text-slate-200 font-mono mt-0.5">
                          {mod.metrics.total_evaluated_images || 0}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="bg-slate-950/40 p-4 rounded-lg border border-slate-800/60 text-xs text-slate-400 flex items-center gap-2">
                    <Info className="w-4 h-4 text-rose-400 shrink-0" />
                    <span>
                      {mod.is_demo
                        ? 'Operating in Demo Heuristic Mode: No synthetic evaluation metrics fabricated. Uses deterministic edge and gradient localization.'
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
      {/* TAB 5: Defect Dataset Validator                                 */}
      {/* ============================================================== */}
      {activeTab === 'dataset' && (
        <div className="space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <h3 className="font-semibold text-slate-200 text-sm">Physical Defect Dataset Validation</h3>
            <p className="text-xs text-slate-400">
              Validates annotation coordinates, bounding box boundaries ([x, y, w, h]), corrupt files, and class balance.
            </p>

            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                value={datasetPathInput}
                onChange={(e) => setDatasetPathInput(e.target.value)}
                placeholder="data/datasets/deterioration"
                className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200"
              />
              <button
                onClick={handleValidateDataset}
                disabled={validatingDataset}
                className="flex items-center justify-center gap-2 px-5 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-sm font-medium disabled:opacity-50"
              >
                {validatingDataset ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Validating Geometry...
                  </>
                ) : (
                  'Validate Defect Dataset'
                )}
              </button>
            </div>
          </div>

          {datasetReport && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="font-semibold text-slate-200 text-sm">Annotation Validation Report</h4>
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
                  <span className="text-slate-400">Total Images:</span>
                  <div className="text-lg font-bold text-slate-100 mt-0.5">{datasetReport.total_images}</div>
                </div>
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                  <span className="text-slate-400">Annotations:</span>
                  <div className="text-lg font-bold text-slate-100 mt-0.5">{datasetReport.total_annotations}</div>
                </div>
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                  <span className="text-slate-400">Invalid Boxes:</span>
                  <div className="text-lg font-bold text-rose-400 mt-0.5">{datasetReport.invalid_boxes_count}</div>
                </div>
                <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                  <span className="text-slate-400">Errors Detected:</span>
                  <div className="text-lg font-bold text-red-400 mt-0.5">{datasetReport.errors.length}</div>
                </div>
              </div>

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

              <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg text-xs text-slate-300">
                <span className="font-semibold text-rose-400">Recommendation: </span>
                {datasetReport.recommendation}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
