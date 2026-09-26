import React, { useState, useEffect, useMemo } from 'react';
import {
  History,
  AlertTriangle,
  Play,
  Layers,
  Calendar,
  Crosshair,
  Sliders,
  Filter,
  RefreshCw,
  Search,
  Clock,
  ExternalLink,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { ModelViewer3D } from '../components/viewer/ModelViewer3D';
import type {
  Site,
  Survey,
  Reconstruction,
  TemporalComparisonSummary,
  TemporalChangeRecordItem,
  TemporalTimelineItem,
} from '../types';

interface TemporalMonitoringPageProps {
  initialSiteId?: string;
  onNavigateToSurveys?: () => void;
}

export const TemporalMonitoringPage: React.FC<TemporalMonitoringPageProps> = ({
  initialSiteId,
  onNavigateToSurveys,
}) => {
  // Sites & Surveys State
  const [sites, setSites] = useState<Site[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState<string>(initialSiteId || '');
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [timeline, setTimeline] = useState<TemporalTimelineItem[]>([]);
  const [baselineSurveyId, setBaselineSurveyId] = useState<string>('');
  const [comparisonSurveyId, setComparisonSurveyId] = useState<string>('');

  // Reconstructions for 3D URLs
  const [baselineRecon, setBaselineRecon] = useState<Reconstruction | null>(null);
  const [comparisonRecon, setComparisonRecon] = useState<Reconstruction | null>(null);

  // Active Comparison & Change Records
  const [activeComparison, setActiveComparison] = useState<TemporalComparisonSummary | null>(null);
  const [changeRecords, setChangeRecords] = useState<TemporalChangeRecordItem[]>([]);
  const [selectedRecord, setSelectedRecord] = useState<TemporalChangeRecordItem | null>(null);

  // Filter States
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [materialFilter, setMaterialFilter] = useState<string>('ALL');
  const [defectFilter, setDefectFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  // 3D Viewer Temporal Display Mode
  const [temporalMode, setTemporalMode] = useState<'t1_only' | 't2_only' | 'both' | 'difference'>('difference');

  // ICP Configuration Parameters
  const [icpMethod, setIcpMethod] = useState<string>('ICP_POINT_TO_POINT');
  const [changeThreshold, setChangeThreshold] = useState<number>(0.02);
  const [damageMatchingThreshold, setDamageMatchingThreshold] = useState<number>(0.15);

  // Loading States
  const [loading, setLoading] = useState<boolean>(false);
  const [processingStage, setProcessingStage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load Sites
  useEffect(() => {
    apiClient
      .getSites()
      .then((data: Site[]) => {
        setSites(data);
        if (!selectedSiteId && data.length > 0) {
          setSelectedSiteId(data[0].id);
        }
      })
      .catch((err: any) => setError(`Failed to fetch sites: ${err.message}`));
  }, []);

  // Load Surveys and Timeline when Site changes
  useEffect(() => {
    if (!selectedSiteId) return;

    setLoading(true);
    setError(null);
    Promise.all([
      apiClient.getSurveys(selectedSiteId),
      apiClient.getSiteTimeline(selectedSiteId).catch(() => []),
    ])
      .then(([srvList, tlList]: [Survey[], TemporalTimelineItem[]]) => {
        setSurveys(srvList);
        setTimeline(tlList);
        // Default T1 to earliest, T2 to latest
        if (srvList.length >= 2) {
          const sorted = [...srvList].sort(
            (a, b) => new Date(a.survey_date).getTime() - new Date(b.survey_date).getTime()
          );
          setBaselineSurveyId(sorted[0].id);
          setComparisonSurveyId(sorted[sorted.length - 1].id);
        } else if (srvList.length === 1) {
          setBaselineSurveyId(srvList[0].id);
          setComparisonSurveyId('');
        }
      })
      .catch((err: any) => setError(`Failed to load surveys: ${err.message}`))
      .finally(() => setLoading(false));
  }, [selectedSiteId]);

  // Load Reconstructions and Existing Comparison
  useEffect(() => {
    if (!baselineSurveyId || !comparisonSurveyId) {
      setBaselineRecon(null);
      setComparisonRecon(null);
      return;
    }

    Promise.all([
      apiClient.getSurveyReconstruction(baselineSurveyId).catch(() => null),
      apiClient.getSurveyReconstruction(comparisonSurveyId).catch(() => null),
      apiClient.getSiteComparisons(selectedSiteId).catch(() => []),
    ]).then(([bRec, cRec, comparisons]: [Reconstruction | null, Reconstruction | null, TemporalComparisonSummary[]]) => {
      setBaselineRecon(bRec);
      setComparisonRecon(cRec);

      // Find existing comparison for this pair
      const matched = comparisons.find(
        (c: TemporalComparisonSummary) =>
          c.baseline_survey_id === baselineSurveyId && c.comparison_survey_id === comparisonSurveyId
      );
      if (matched) {
        setActiveComparison(matched);
        loadChangeRecords(matched.id);
      } else {
        setActiveComparison(null);
        setChangeRecords([]);
        setSelectedRecord(null);
      }
    });
  }, [baselineSurveyId, comparisonSurveyId, selectedSiteId]);

  // Load change records helper
  const loadChangeRecords = (comparisonId: string) => {
    apiClient
      .getTemporalComparisonChanges(comparisonId)
      .then((records: TemporalChangeRecordItem[]) => {
        setChangeRecords(records);
        if (records.length > 0) {
          setSelectedRecord(records[0]);
        }
      })
      .catch((err: any) => console.error('Error fetching change records:', err));
  };

  // Run End-to-End Pipeline
  const handleRunFullPipeline = async () => {
    if (!selectedSiteId || !baselineSurveyId || !comparisonSurveyId) return;
    setLoading(true);
    setError(null);
    setProcessingStage('Validating Survey Pair & Initializing Registration...');

    try {
      // 1. Initialize comparison
      const comp = await apiClient.createTemporalComparison({
        site_id: selectedSiteId,
        baseline_survey_id: baselineSurveyId,
        comparison_survey_id: comparisonSurveyId,
        alignment_method: icpMethod,
        change_threshold: changeThreshold,
        damage_matching_distance_threshold: damageMatchingThreshold,
      });

      setProcessingStage('Executing Open3D ICP Reconstruction Alignment...');
      await apiClient.alignReconstructions(comp.id, {
        alignment_method: icpMethod,
        max_correspondence_distance: 0.08,
        max_iterations: 50,
      });

      setProcessingStage('Quantifying Point-to-Point Geometric Distance Field...');
      await apiClient.detectGeometricChange(comp.id, {
        change_threshold: changeThreshold,
      });

      setProcessingStage('Matching Phase 6 Defects & Categorizing Evolution...');
      const trackRes = await apiClient.trackDeterioration(comp.id, {
        damage_matching_distance_threshold: damageMatchingThreshold,
      });

      setActiveComparison(trackRes.comparison_summary);
      loadChangeRecords(comp.id);
      setProcessingStage(null);
    } catch (err: any) {
      setError(err?.message || 'Temporal comparison execution failed.');
      setProcessingStage(null);
    } finally {
      setLoading(false);
    }
  };

  // Filtered change records
  const filteredRecords = useMemo(() => {
    return changeRecords.filter((rec) => {
      if (statusFilter !== 'ALL' && rec.change_status !== statusFilter) return false;
      if (materialFilter !== 'ALL' && rec.material_class.toLowerCase() !== materialFilter.toLowerCase()) return false;
      if (defectFilter !== 'ALL' && rec.deterioration_type.toLowerCase() !== defectFilter.toLowerCase()) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchType = rec.deterioration_type.toLowerCase().includes(q);
        const matchMat = rec.material_class.toLowerCase().includes(q);
        const matchNotes = (rec.notes || '').toLowerCase().includes(q);
        if (!matchType && !matchMat && !matchNotes) return false;
      }
      return true;
    });
  }, [changeRecords, statusFilter, materialFilter, defectFilter, searchQuery]);

  // Model URLs for 3D Viewer
  const baselineModelUrl = baselineRecon ? apiClient.getReconstructionModelUrl(baselineRecon.id, 'dense') : '';
  const comparisonModelUrl = comparisonRecon ? apiClient.getReconstructionModelUrl(comparisonRecon.id, 'dense') : '';

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-700/60 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">
              Phase 7 Complete
            </span>
            <span className="text-xs text-slate-400 font-mono">Multi-Temporal Monitoring</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2.5 mt-1">
            <History className="text-amber-400" size={26} />
            Multi-Temporal Monitoring & Change Detection
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Quantify 3D surface deviation, perform ICP co-registration, track deterioration evolution, and preserve material provenance across survey dates.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {onNavigateToSurveys && (
            <button
              onClick={onNavigateToSurveys}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs border border-slate-700"
            >
              <ExternalLink size={14} />
              <span>Surveys</span>
            </button>
          )}

          <button
            onClick={handleRunFullPipeline}
            disabled={loading || !baselineSurveyId || !comparisonSurveyId}
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-semibold shadow-lg shadow-amber-500/20 disabled:opacity-50 transition-all text-sm"
          >
            {loading ? (
              <>
                <RefreshCw size={16} className="animate-spin" />
                <span>Processing Pipeline...</span>
              </>
            ) : (
              <>
                <Play size={16} />
                <span>Run Temporal Change Pipeline</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Research Methodology Notice */}
      <div className="bg-amber-950/25 border border-amber-500/30 rounded-xl p-4 flex items-start gap-3.5">
        <AlertTriangle className="text-amber-400 shrink-0 mt-0.5" size={20} />
        <div className="space-y-1 text-xs text-slate-300 leading-relaxed">
          <p className="font-semibold text-amber-300 uppercase tracking-wide">
            Academic Research Notice — Geometric Change Candidates
          </p>
          <p>
            Temporal change measurements depend on reconstruction quality, survey overlap, registration quality, camera geometry, image quality, reconstruction scale, and detection consistency. Observed geometric differences are strictly designated as <strong>change candidates</strong> and do not certify physical structural volume loss or repair without calibrated physical scale bars.
          </p>
        </div>
      </div>

      {/* Processing Status Banner */}
      {processingStage && (
        <div className="bg-blue-950/40 border border-blue-500/30 rounded-xl p-4 flex items-center gap-3 animate-pulse">
          <RefreshCw className="text-blue-400 animate-spin shrink-0" size={18} />
          <span className="text-sm text-blue-200 font-medium">{processingStage}</span>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="bg-rose-950/40 border border-rose-500/40 rounded-xl p-4 flex items-center gap-3 text-rose-200 text-sm">
          <AlertTriangle className="text-rose-400 shrink-0" size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* Survey Pairing & Configuration Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* Site & Survey Selection Card */}
        <div className="lg:col-span-5 bg-slate-800/60 border border-slate-700/60 rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Calendar size={16} className="text-amber-400" />
            1. Survey Pairing Setup
          </h2>

          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-slate-400 block mb-1">Heritage Site</label>
              <select
                value={selectedSiteId}
                onChange={(e) => setSelectedSiteId(e.target.value)}
                className="w-full bg-slate-900/80 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-amber-400"
              >
                {sites.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.location})
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-slate-400 block mb-1">Baseline Survey (T1)</label>
                <select
                  value={baselineSurveyId}
                  onChange={(e) => setBaselineSurveyId(e.target.value)}
                  className="w-full bg-slate-900/80 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-amber-400"
                >
                  <option value="">Select Baseline</option>
                  {surveys.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.survey_code} ({new Date(s.survey_date).toLocaleDateString()})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-400 block mb-1">Comparison Survey (T2)</label>
                <select
                  value={comparisonSurveyId}
                  onChange={(e) => setComparisonSurveyId(e.target.value)}
                  className="w-full bg-slate-900/80 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-amber-400"
                >
                  <option value="">Select Target</option>
                  {surveys
                    .filter((s) => s.id !== baselineSurveyId)
                    .map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.survey_code} ({new Date(s.survey_date).toLocaleDateString()})
                      </option>
                    ))}
                </select>
              </div>
            </div>

            {/* Time Delta & Scale Badge */}
            <div className="p-3 bg-slate-900/70 border border-slate-700/50 rounded-lg flex items-center justify-between text-xs">
              <div className="flex items-center gap-2 text-slate-300">
                <Clock size={14} className="text-amber-400" />
                <span>Elapsed Interval:</span>
                <span className="font-semibold text-slate-100">
                  {activeComparison?.elapsed_time_formatted || 'Pending Pairing'}
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-slate-400">Scale Status:</span>
                <span className={`px-2 py-0.5 rounded text-xs font-mono font-medium ${
                  activeComparison?.scale_status === 'METRIC'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                }`}>
                  {activeComparison?.scale_status || 'LOCAL'}
                </span>
              </div>
            </div>

            {/* Timeline Mini-Indicator */}
            {timeline.length > 0 && (
              <div className="text-[11px] text-slate-400 pt-1">
                <span>Timeline Records: </span>
                <span className="font-mono text-slate-200">{timeline.length} site surveys recorded</span>
              </div>
            )}
          </div>
        </div>

        {/* Registration & Change Parameters Card */}
        <div className="lg:col-span-7 bg-slate-800/60 border border-slate-700/60 rounded-xl p-5 space-y-4">
          <h2 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <Sliders size={16} className="text-amber-400" />
            2. ICP Alignment & Change Thresholds
          </h2>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-medium text-slate-400 block mb-1">Registration Method</label>
              <select
                value={icpMethod}
                onChange={(e) => setIcpMethod(e.target.value)}
                className="w-full bg-slate-900/80 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-amber-400"
              >
                <option value="ICP_POINT_TO_POINT">Point-to-Point ICP</option>
                <option value="ICP_POINT_TO_PLANE">Point-to-Plane ICP</option>
                <option value="CENTROID_INIT">Centroid Translation Only</option>
                <option value="IDENTITY">Identity (Already Registered)</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-medium text-slate-400 block mb-1">
                Change Threshold: <span className="font-mono text-amber-400">{changeThreshold} units</span>
              </label>
              <input
                type="range"
                min="0.005"
                max="0.10"
                step="0.005"
                value={changeThreshold}
                onChange={(e) => setChangeThreshold(parseFloat(e.target.value))}
                className="w-full accent-amber-400 mt-2"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-slate-400 block mb-1">
                Damage Match Radius: <span className="font-mono text-amber-400">{damageMatchingThreshold} units</span>
              </label>
              <input
                type="range"
                min="0.05"
                max="0.50"
                step="0.01"
                value={damageMatchingThreshold}
                onChange={(e) => setDamageMatchingThreshold(parseFloat(e.target.value))}
                className="w-full accent-amber-400 mt-2"
              />
            </div>
          </div>

          {/* Registration Quality HUD */}
          <div className="grid grid-cols-4 gap-2 pt-2 border-t border-slate-700/50">
            <div className="p-2.5 bg-slate-900/50 rounded-lg text-center">
              <span className="text-[11px] text-slate-400 block">Alignment Status</span>
              <span className={`text-xs font-semibold uppercase tracking-wider ${
                activeComparison?.alignment_status === 'ALIGNED'
                  ? 'text-emerald-400'
                  : activeComparison?.alignment_status === 'ALIGNMENT_REQUIRES_REVIEW'
                  ? 'text-amber-400'
                  : 'text-slate-400'
              }`}>
                {activeComparison?.alignment_status || 'PENDING'}
              </span>
            </div>

            <div className="p-2.5 bg-slate-900/50 rounded-lg text-center">
              <span className="text-[11px] text-slate-400 block">Inlier Fitness</span>
              <span className="text-xs font-mono font-semibold text-slate-100">
                {activeComparison?.fitness != null ? `${(activeComparison.fitness * 100).toFixed(1)}%` : '—'}
              </span>
            </div>

            <div className="p-2.5 bg-slate-900/50 rounded-lg text-center">
              <span className="text-[11px] text-slate-400 block">Inlier RMSE</span>
              <span className="text-xs font-mono font-semibold text-slate-100">
                {activeComparison?.rmse != null ? activeComparison.rmse.toFixed(5) : '—'}
              </span>
            </div>

            <div className="p-2.5 bg-slate-900/50 rounded-lg text-center">
              <span className="text-[11px] text-slate-400 block">Inlier Pairs</span>
              <span className="text-xs font-mono font-semibold text-slate-100">
                {activeComparison?.correspondence_count || 0}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3.5">
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
          <span className="text-xs text-slate-400 block">Persisting Defects</span>
          <div className="flex items-center justify-between mt-1">
            <span className="text-xl font-bold text-rose-400 font-mono">
              {activeComparison?.summary_metrics?.persisting_deteriorations ?? 0}
            </span>
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
          </div>
          <span className="text-[10px] text-slate-400">Tracked in T1 & T2</span>
        </div>

        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
          <span className="text-xs text-slate-400 block">New Detections</span>
          <div className="flex items-center justify-between mt-1">
            <span className="text-xl font-bold text-cyan-400 font-mono">
              {activeComparison?.summary_metrics?.new_deteriorations ?? 0}
            </span>
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
          </div>
          <span className="text-[10px] text-slate-400">Newly formed at T2</span>
        </div>

        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
          <span className="text-xs text-slate-400 block">Possibly Resolved</span>
          <div className="flex items-center justify-between mt-1">
            <span className="text-xl font-bold text-indigo-400 font-mono">
              {activeComparison?.summary_metrics?.possibly_resolved_or_undetected ?? 0}
            </span>
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
          </div>
          <span className="text-[10px] text-slate-400">T1 absent at T2</span>
        </div>

        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
          <span className="text-xs text-slate-400 block">Geometric Change</span>
          <div className="flex items-center justify-between mt-1">
            <span className="text-xl font-bold text-amber-400 font-mono">
              {activeComparison?.summary_metrics?.geometric_change_candidates_only ?? 0}
            </span>
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
          </div>
          <span className="text-[10px] text-slate-400">Unlabeled deviations</span>
        </div>

        <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3.5">
          <span className="text-xs text-slate-400 block">Material Changes</span>
          <div className="flex items-center justify-between mt-1">
            <span className="text-xl font-bold text-purple-400 font-mono">
              {activeComparison?.summary_metrics?.material_label_changed_count ?? 0}
            </span>
            <span className="w-2.5 h-2.5 rounded-full bg-purple-500" />
          </div>
          <span className="text-[10px] text-slate-400">Requires review</span>
        </div>
      </div>

      {/* Main 3D Workspace and Traceability Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        {/* 3D Model Viewer with Temporal Overlay */}
        <div className="lg:col-span-8 bg-slate-800/60 border border-slate-700/60 rounded-xl p-4 flex flex-col space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-700/50 pb-2.5">
            <div className="flex items-center gap-2">
              <Layers size={17} className="text-amber-400" />
              <span className="text-sm font-semibold text-slate-200">Temporal 3D Co-Registration Viewer</span>
            </div>

            {/* Display Mode Tabs */}
            <div className="flex items-center bg-slate-900/80 p-0.5 rounded-lg border border-slate-700 text-xs">
              <button
                onClick={() => setTemporalMode('t1_only')}
                className={`px-2.5 py-1 rounded font-medium transition-colors ${
                  temporalMode === 't1_only' ? 'bg-amber-500 text-slate-950 font-semibold' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                T1 Baseline
              </button>
              <button
                onClick={() => setTemporalMode('t2_only')}
                className={`px-2.5 py-1 rounded font-medium transition-colors ${
                  temporalMode === 't2_only' ? 'bg-amber-500 text-slate-950 font-semibold' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                T2 Target
              </button>
              <button
                onClick={() => setTemporalMode('difference')}
                className={`px-2.5 py-1 rounded font-medium transition-colors ${
                  temporalMode === 'difference' ? 'bg-amber-500 text-slate-950 font-semibold' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Difference Map
              </button>
            </div>
          </div>

          {/* 3D Viewport Component */}
          <div className="h-[460px] rounded-lg overflow-hidden bg-slate-950 relative border border-slate-800">
            {baselineModelUrl ? (
              <ModelViewer3D
                modelUrl={baselineModelUrl}
                comparisonModelUrl={comparisonModelUrl}
                temporalMode={temporalMode}
                temporalChangeRecords={changeRecords}
                selectedChangeRecordId={selectedRecord?.id}
                onSelectChangeRecord={(rec: TemporalChangeRecordItem) => setSelectedRecord(rec)}
                isDemo={activeComparison?.is_demo ?? true}
                pointCount={activeComparison?.summary_metrics?.total_points_evaluated}
              />
            ) : (
              <div className="h-full flex flex-col items-center justify-center p-6 text-center text-slate-500">
                <Layers size={36} className="mb-2 opacity-50" />
                <p className="text-sm font-medium">Reconstruction asset not loaded.</p>
                <p className="text-xs text-slate-500 mt-1">
                  Ensure baseline survey T1 has a completed 3D photogrammetric model.
                </p>
              </div>
            )}
          </div>

          {/* Visual Legend */}
          <div className="flex flex-wrap items-center gap-4 text-xs pt-1 border-t border-slate-700/50">
            <span className="text-slate-400 font-medium">Status Legend:</span>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
              <span className="text-slate-300">Persisting</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-400" />
              <span className="text-slate-300">New Defect</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" />
              <span className="text-slate-300">Possibly Resolved / Undetected</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
              <span className="text-slate-300">Geometric Deviation Only</span>
            </div>
          </div>
        </div>

        {/* Traceability & Defect Evolution Inspector Drawer */}
        <div className="lg:col-span-4 bg-slate-800/60 border border-slate-700/60 rounded-xl p-4 flex flex-col space-y-4">
          <div className="flex items-center justify-between border-b border-slate-700/50 pb-2.5">
            <div className="flex items-center gap-2">
              <Crosshair size={16} className="text-amber-400" />
              <span className="text-sm font-semibold text-slate-200">Temporal Defect Inspector</span>
            </div>
            {selectedRecord && (
              <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${
                selectedRecord.change_status === 'PERSISTING_DETERIORATION'
                  ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                  : selectedRecord.change_status === 'NEW_DETERIORATION'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                  : selectedRecord.change_status === 'POSSIBLY_RESOLVED_OR_UNDETECTED'
                  ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                  : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
              }`}>
                {selectedRecord.change_status.replace(/_/g, ' ')}
              </span>
            )}
          </div>

          {selectedRecord ? (
            <div className="space-y-3.5 text-xs text-slate-300">
              {/* Defect & Substrate Attributes */}
              <div className="grid grid-cols-2 gap-2 p-3 bg-slate-900/60 rounded-lg border border-slate-700/50">
                <div>
                  <span className="text-slate-400 text-[11px] block">Deterioration Type</span>
                  <span className="font-semibold text-slate-100 capitalize">
                    {selectedRecord.deterioration_type}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 text-[11px] block">Material Substrate</span>
                  <span className="font-semibold text-slate-100 capitalize">
                    {selectedRecord.material_class}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 text-[11px] block">Material Label State</span>
                  <span className={`font-semibold ${
                    selectedRecord.material_status === 'CONSISTENT' ? 'text-emerald-400' : 'text-purple-400'
                  }`}>
                    {selectedRecord.material_status}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 text-[11px] block">Measured Displacement</span>
                  <span className="font-mono font-semibold text-amber-400">
                    {selectedRecord.spatial_distance != null ? `${selectedRecord.spatial_distance.toFixed(4)} units` : 'N/A'}
                  </span>
                </div>
              </div>

              {/* 3D World Coordinates */}
              <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-700/50 space-y-1.5">
                <span className="text-[11px] font-semibold text-slate-400 block uppercase tracking-wider">
                  Baseline (T1) Coordinates (X, Y, Z)
                </span>
                <p className="font-mono text-xs text-slate-200">
                  {selectedRecord.baseline_x != null
                    ? `[${selectedRecord.baseline_x.toFixed(3)}, ${selectedRecord.baseline_y?.toFixed(3)}, ${selectedRecord.baseline_z?.toFixed(3)}]`
                    : 'Unmapped in Baseline'}
                </p>
                <span className="text-[11px] font-semibold text-slate-400 block uppercase tracking-wider pt-1">
                  Target (T2) Coordinates (Aligned Frame)
                </span>
                <p className="font-mono text-xs text-slate-200">
                  {selectedRecord.comparison_x != null
                    ? `[${selectedRecord.comparison_x.toFixed(3)}, ${selectedRecord.comparison_y?.toFixed(3)}, ${selectedRecord.comparison_z?.toFixed(3)}]`
                    : 'Unmapped in Comparison'}
                </p>
              </div>

              {/* Research Notes & Scientific Interpretation */}
              <div className="p-3 bg-slate-900/40 rounded-lg border border-slate-700/40 space-y-1">
                <span className="text-[11px] font-semibold text-slate-400 block">Scientific Provenance</span>
                <p className="text-xs text-slate-400 leading-relaxed italic">
                  {selectedRecord.notes || 'Automated spatial correspondence match within configured tolerance radius.'}
                </p>
              </div>

              {/* Demo Mode Badge */}
              {selectedRecord.is_demo && (
                <div className="flex items-center gap-1.5 text-[11px] text-amber-400 bg-amber-950/20 px-2.5 py-1.5 rounded border border-amber-500/20">
                  <AlertTriangle size={14} className="shrink-0" />
                  <span>Demo Model — Synthetic test geometry & coordinates</span>
                </div>
              )}
            </div>
          ) : (
            <div className="h-64 flex flex-col items-center justify-center p-4 text-center text-slate-500">
              <Crosshair size={32} className="mb-2 opacity-40" />
              <p className="text-sm font-medium">No Defect Selected</p>
              <p className="text-xs text-slate-500 mt-1">
                Click any 3D defect marker or select a record from the table below to inspect multi-temporal change parameters.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Filterable Change Records Table */}
      <div className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-5 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-700/50 pb-3">
          <div className="flex items-center gap-2">
            <Filter size={16} className="text-amber-400" />
            <h3 className="text-sm font-semibold text-slate-200">
              Temporal Change Records ({filteredRecords.length})
            </h3>
          </div>

          <div className="flex flex-wrap items-center gap-2.5 text-xs">
            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-900/80 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200"
            >
              <option value="ALL">All Statuses</option>
              <option value="PERSISTING_DETERIORATION">Persisting Defects</option>
              <option value="NEW_DETERIORATION">New Defects</option>
              <option value="POSSIBLY_RESOLVED_OR_UNDETECTED">Possibly Resolved</option>
              <option value="GEOMETRIC_CHANGE_WITHOUT_DETERIORATION_LABEL">Geometric Changes Only</option>
            </select>

            {/* Material Filter */}
            <select
              value={materialFilter}
              onChange={(e) => setMaterialFilter(e.target.value)}
              className="bg-slate-900/80 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200"
            >
              <option value="ALL">All Materials</option>
              <option value="sandstone">Sandstone</option>
              <option value="brick">Brick</option>
              <option value="granite">Granite</option>
              <option value="limestone">Limestone</option>
              <option value="mortar">Mortar</option>
            </select>

            {/* Defect Filter */}
            <select
              value={defectFilter}
              onChange={(e) => setDefectFilter(e.target.value)}
              className="bg-slate-900/80 border border-slate-700 rounded-lg px-2.5 py-1.5 text-slate-200"
            >
              <option value="ALL">All Defects</option>
              <option value="crack">Crack</option>
              <option value="erosion">Erosion</option>
              <option value="spalling">Spalling</option>
              <option value="discoloration">Discoloration</option>
              <option value="biological_growth">Biological Growth</option>
            </select>

            {/* Search Box */}
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-2 text-slate-400" />
              <input
                type="text"
                placeholder="Search defects..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-slate-900/80 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-slate-200 text-xs w-44 focus:outline-none focus:border-amber-400"
              />
            </div>
          </div>
        </div>

        {/* Records Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-700 text-slate-400 uppercase tracking-wider text-[10px]">
                <th className="py-2.5 px-3">Status</th>
                <th className="py-2.5 px-3">Defect Type</th>
                <th className="py-2.5 px-3">Material Substrate</th>
                <th className="py-2.5 px-3">Material Consistency</th>
                <th className="py-2.5 px-3 text-right">Displacement</th>
                <th className="py-2.5 px-3">3D Location</th>
                <th className="py-2.5 px-3 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 text-slate-300">
              {filteredRecords.length > 0 ? (
                filteredRecords.map((rec) => {
                  const isSelected = selectedRecord?.id === rec.id;
                  return (
                    <tr
                      key={rec.id}
                      onClick={() => setSelectedRecord(rec)}
                      className={`hover:bg-slate-700/40 cursor-pointer transition-colors ${
                        isSelected ? 'bg-amber-500/10' : ''
                      }`}
                    >
                      <td className="py-2.5 px-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider ${
                          rec.change_status === 'PERSISTING_DETERIORATION'
                            ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                            : rec.change_status === 'NEW_DETERIORATION'
                            ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                            : rec.change_status === 'POSSIBLY_RESOLVED_OR_UNDETECTED'
                            ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                            : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                        }`}>
                          {rec.change_status.replace(/_/g, ' ')}
                        </span>
                      </td>

                      <td className="py-2.5 px-3 font-medium text-slate-100 capitalize">
                        {rec.deterioration_type}
                      </td>

                      <td className="py-2.5 px-3 capitalize">
                        {rec.material_class}
                      </td>

                      <td className="py-2.5 px-3">
                        <span className={`font-mono ${
                          rec.material_status === 'CONSISTENT' ? 'text-emerald-400' : 'text-purple-400'
                        }`}>
                          {rec.material_status}
                        </span>
                      </td>

                      <td className="py-2.5 px-3 text-right font-mono text-amber-400">
                        {rec.spatial_distance != null ? rec.spatial_distance.toFixed(4) : '—'}
                      </td>

                      <td className="py-2.5 px-3 font-mono text-[11px] text-slate-400">
                        {rec.comparison_x != null
                          ? `[${rec.comparison_x.toFixed(2)}, ${rec.comparison_y?.toFixed(2)}, ${rec.comparison_z?.toFixed(2)}]`
                          : rec.baseline_x != null
                          ? `[${rec.baseline_x.toFixed(2)}, ${rec.baseline_y?.toFixed(2)}, ${rec.baseline_z?.toFixed(2)}]`
                          : 'N/A'}
                      </td>

                      <td className="py-2.5 px-3 text-center">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedRecord(rec);
                          }}
                          className="px-2 py-1 rounded bg-slate-700/60 hover:bg-slate-700 text-slate-300 text-[11px]"
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500">
                    No temporal change records found matching current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
