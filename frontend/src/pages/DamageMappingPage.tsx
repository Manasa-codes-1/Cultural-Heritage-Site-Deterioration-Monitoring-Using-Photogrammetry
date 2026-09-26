import React, { useState, useEffect, useMemo } from 'react';
import {
  Crosshair,
  Layers,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Play,
  Filter,
  ShieldCheck,
  Target,
  Image as ImageIcon,
} from 'lucide-react';
import { api } from '../api/client';
import type {
  Survey,
  Reconstruction,
  Deterioration3DMappingItem,
  Survey3DMappingSummary,
  MappingValidationResponse,
} from '../types';
import { ModelViewer3D } from '../components/viewer/ModelViewer3D';

interface DamageMappingPageProps {
  initialSurveyId?: string;
  onNavigateToSurveys?: () => void;
}

export const DamageMappingPage: React.FC<DamageMappingPageProps> = ({
  initialSurveyId,
}) => {
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [selectedSurveyId, setSelectedSurveyId] = useState<string>(initialSurveyId || '');
  const [reconstruction, setReconstruction] = useState<Reconstruction | null>(null);
  const [summary, setSummary] = useState<Survey3DMappingSummary | null>(null);
  const [mappings, setMappings] = useState<Deterioration3DMappingItem[]>([]);
  const [selectedMapping, setSelectedMapping] = useState<Deterioration3DMappingItem | null>(null);

  // Loading & Action states
  const [loading, setLoading] = useState<boolean>(true);
  const [mappingInProgress, setMappingInProgress] = useState<boolean>(false);
  const [validating, setValidating] = useState<boolean>(false);
  const [validationResult, setValidationResult] = useState<MappingValidationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Settings for mapping trigger
  const [samplingStrategy, setSamplingStrategy] = useState<string>('CENTER_ONLY');
  const [reprojThreshold, setReprojThreshold] = useState<number>(5.0);

  // Filter states
  const [filterType, setFilterType] = useState<string>('ALL');
  const [filterMaterial, setFilterMaterial] = useState<string>('ALL');
  const [filterStatus, setFilterStatus] = useState<string>('ALL');
  const [minConfidence, setMinConfidence] = useState<number>(0.0);

  // Load initial surveys list
  useEffect(() => {
    const fetchSurveys = async () => {
      try {
        setLoading(true);
        const data = await api.getSurveys();
        setSurveys(data);
        if (!selectedSurveyId && data.length > 0) {
          setSelectedSurveyId(data[0].id);
        }
      } catch (err: unknown) {
        setError(`Failed to load surveys: ${(err as Error).message}`);
      } finally {
        setLoading(false);
      }
    };
    fetchSurveys();
  }, [selectedSurveyId]);

  // Load Reconstruction and Mappings when selected survey changes
  useEffect(() => {
    if (!selectedSurveyId) return;

    const loadSurveyData = async () => {
      try {
        setLoading(true);
        setError(null);
        setSelectedMapping(null);
        setValidationResult(null);

        // 1. Get Reconstruction
        try {
          const recon = await api.getSurveyReconstruction(selectedSurveyId);
          setReconstruction(recon);
        } catch {
          setReconstruction(null);
        }

        // 2. Get 3D Mappings
        try {
          const sum = await api.getSurvey3DMappings(selectedSurveyId);
          setSummary(sum);
          setMappings(sum.mappings || []);
          if (sum.mappings && sum.mappings.length > 0) {
            setSelectedMapping(sum.mappings[0]);
          }
        } catch {
          setSummary(null);
          setMappings([]);
        }
      } catch (err: unknown) {
        setError(`Failed to load 3D mapping data: ${(err as Error).message}`);
      } finally {
        setLoading(false);
      }
    };

    loadSurveyData();
  }, [selectedSurveyId]);

  // Handle batch mapping execution
  const handleRunBatchMapping = async () => {
    if (!selectedSurveyId) return;
    try {
      setMappingInProgress(true);
      setError(null);
      const res = await api.mapSurvey3D(selectedSurveyId, {
        sampling_strategy: samplingStrategy,
        reprojection_threshold_px: reprojThreshold,
        force: true,
      });
      setSummary(res);
      setMappings(res.mappings || []);
      if (res.mappings && res.mappings.length > 0) {
        setSelectedMapping(res.mappings[0]);
      }
    } catch (err: unknown) {
      setError(`3D Mapping failed: ${(err as Error).message}`);
    } finally {
      setMappingInProgress(false);
    }
  };

  // Validate single mapping reprojection
  const handleValidateMapping = async (mappingId: string) => {
    try {
      setValidating(true);
      const res = await api.validate3DMapping(mappingId, reprojThreshold);
      setValidationResult(res);
    } catch (err: unknown) {
      setError(`Validation failed: ${(err as Error).message}`);
    } finally {
      setValidating(false);
    }
  };

  // Filtered Mappings
  const filteredMappings = useMemo(() => {
    return mappings.filter((m) => {
      if (filterType !== 'ALL' && m.deterioration_type.toLowerCase() !== filterType.toLowerCase()) {
        return false;
      }
      if (filterMaterial !== 'ALL' && (m.material_class || 'UNKNOWN').toLowerCase() !== filterMaterial.toLowerCase()) {
        return false;
      }
      if (filterStatus !== 'ALL' && m.mapping_status !== filterStatus) {
        return false;
      }
      if (m.deterioration_confidence < minConfidence) {
        return false;
      }
      return true;
    });
  }, [mappings, filterType, filterMaterial, filterStatus, minConfidence]);

  // Color helper for defect badges
  const getDefectColorClass = (type: string) => {
    switch (type.toLowerCase()) {
      case 'crack': return 'bg-rose-500/20 text-rose-300 border-rose-500/30';
      case 'erosion': return 'bg-amber-500/20 text-amber-300 border-amber-500/30';
      case 'spalling': return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30';
      case 'discoloration': return 'bg-purple-500/20 text-purple-300 border-purple-500/30';
      case 'biological_growth': return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
      default: return 'bg-sky-500/20 text-sky-300 border-sky-500/30';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'MAPPED':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">MAPPED</span>;
      case 'PARTIALLY_MAPPED':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">PARTIALLY MAPPED</span>;
      case 'NO_SURFACE_INTERSECTION':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-500/20 text-slate-300 border border-slate-500/30">NO INTERSECTION</span>;
      case 'MAPPING_REQUIRES_CALIBRATION':
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">REQUIRES CALIBRATION</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-700 text-slate-300">{status}</span>;
    }
  };

  const selectedSurvey = surveys.find((s) => s.id === selectedSurveyId);
  const isDemo = Boolean(summary?.is_demo || reconstruction?.is_demo);

  return (
    <div className="space-y-6 pb-12">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30 uppercase tracking-wider">
              Phase 6: Spatial Localization
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Material → Deterioration → 3D Location
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2.5 mt-1.5">
            <Crosshair className="text-amber-500" size={26} />
            2D-to-3D Deterioration Mapping
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Raycasting 2D defect detections onto reconstructed photogrammetric surfaces with camera model inversion and reprojection verification.
            {selectedSurvey && (
              <span className="text-slate-500 ml-2">
                (Survey: {selectedSurvey.survey_code})
              </span>
            )}
          </p>
        </div>

        {/* Survey Selector */}
        <div className="flex items-center gap-3">
          <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Survey:
          </label>
          <select
            value={selectedSurveyId}
            onChange={(e) => setSelectedSurveyId(e.target.value)}
            className="bg-slate-900 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 focus:ring-2 focus:ring-amber-500 focus:outline-none"
          >
            {surveys.map((s) => (
              <option key={s.id} value={s.id}>
                {s.survey_code} ({new Date(s.survey_date).toLocaleDateString()})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Error Alert Banner */}
      {error && (
        <div className="bg-rose-950/40 border border-rose-800 p-3 rounded-lg flex items-center justify-between text-xs text-rose-300">
          <div className="flex items-center gap-2">
            <AlertTriangle size={16} className="text-rose-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-200 text-xs font-bold px-2 py-0.5">
            Dismiss
          </button>
        </div>
      )}

      {/* Prominent Demo Mode Disclaimer Banner */}
      {isDemo && (
        <div className="bg-amber-500/10 border-l-4 border-amber-500 p-4 rounded-r-lg shadow-sm">
          <div className="flex items-center gap-2.5 text-amber-400 font-semibold text-sm">
            <AlertTriangle size={18} />
            <span>DEMO 3D DAMAGE MAPPING — BASED ON DEMO DETECTIONS & RECONSTRUCTION</span>
          </div>
          <p className="text-slate-300 text-xs mt-1.5 leading-relaxed">
            This survey uses synthetic procedural geometry or heuristic demo detections. 3D coordinates reflect local demo workspace units and must not be cited as physical metric measurements of an actual heritage structure.
          </p>
        </div>
      )}

      {/* Photogrammetry Readiness Check */}
      {!reconstruction && !loading && (
        <div className="bg-rose-950/30 border border-rose-800/50 rounded-xl p-5 text-center">
          <AlertTriangle size={36} className="mx-auto text-rose-400 mb-2" />
          <h3 className="text-lg font-bold text-rose-200">Reconstruction Missing</h3>
          <p className="text-slate-400 text-sm max-w-lg mx-auto mt-1">
            This survey does not have a completed 3D photogrammetric reconstruction. Run Phase 3 Reconstruction before mapping deterioration into 3D.
          </p>
        </div>
      )}

      {/* Action / Trigger Banner */}
      {reconstruction && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-4">
            <div>
              <span className="text-xs text-slate-400 block font-medium">Sampling Strategy:</span>
              <select
                value={samplingStrategy}
                onChange={(e) => setSamplingStrategy(e.target.value)}
                className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded px-2.5 py-1.5 mt-1 focus:ring-1 focus:ring-amber-500"
              >
                <option value="CENTER_ONLY">Center Only (Fastest)</option>
                <option value="BOX_GRID">Box Grid (9 Sample Points)</option>
                <option value="POLYGON_VERTICES">Polygon Vertices (Detailed)</option>
              </select>
            </div>

            <div>
              <span className="text-xs text-slate-400 block font-medium">Reproj Threshold:</span>
              <div className="flex items-center gap-2 mt-1">
                <input
                  type="range"
                  min="1"
                  max="15"
                  step="0.5"
                  value={reprojThreshold}
                  onChange={(e) => setReprojThreshold(parseFloat(e.target.value))}
                  className="w-24 accent-amber-500"
                />
                <span className="text-xs font-mono text-slate-300">{reprojThreshold} px</span>
              </div>
            </div>

            <div className="border-l border-slate-800 pl-4 hidden md:block">
              <span className="text-xs text-slate-400 block">Reconstruction Surface:</span>
              <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1 mt-1">
                <CheckCircle2 size={13} />
                {reconstruction.engine.toUpperCase()} {reconstruction.mesh_triangle_count > 0 ? 'Surface Mesh' : 'Point Cloud'}
              </span>
            </div>
          </div>

          <button
            onClick={handleRunBatchMapping}
            disabled={mappingInProgress}
            className={`px-4 py-2 rounded-lg font-semibold text-sm flex items-center gap-2 transition-all ${
              mappingInProgress
                ? 'bg-slate-800 text-slate-400 cursor-not-allowed'
                : 'bg-amber-600 hover:bg-amber-500 text-slate-950 font-bold shadow-lg shadow-amber-950/30'
            }`}
          >
            {mappingInProgress ? (
              <>
                <RefreshCw size={16} className="animate-spin" />
                <span>Raycasting 3D Surface...</span>
              </>
            ) : (
              <>
                <Play size={16} />
                <span>Map Survey Detections to 3D</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* Summary KPI Cards */}
      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3.5">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
            <span className="text-xs text-slate-400 font-medium">Total Detections</span>
            <div className="text-2xl font-bold text-slate-100 font-mono mt-1">
              {summary.total_eligible_detections}
            </div>
            <span className="text-[11px] text-slate-500">From Phase 5 Detector</span>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
            <span className="text-xs text-emerald-400 font-medium">Mapped to 3D</span>
            <div className="text-2xl font-bold text-emerald-400 font-mono mt-1">
              {summary.mapped_detections}
            </div>
            <span className="text-[11px] text-slate-500">
              {summary.total_eligible_detections > 0
                ? `${Math.round((summary.mapped_detections / summary.total_eligible_detections) * 100)}% mapped`
                : '0%'}
            </span>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
            <span className="text-xs text-amber-400 font-medium">Partially Mapped</span>
            <div className="text-2xl font-bold text-amber-400 font-mono mt-1">
              {summary.partially_mapped_detections}
            </div>
            <span className="text-[11px] text-slate-500">Exceeds reproj threshold</span>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
            <span className="text-xs text-slate-400 font-medium">Mapping Coverage</span>
            <div className="text-2xl font-bold text-sky-400 font-mono mt-1">
              {summary.mapping_success_rate}%
            </div>
            <span className="text-[11px] text-slate-500">Geometric hit rate (not ML accuracy)</span>
          </div>

          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3.5">
            <span className="text-xs text-slate-400 font-medium">Mean Reproj Error</span>
            <div className="text-2xl font-bold text-indigo-400 font-mono mt-1">
              {summary.mean_reprojection_error_px != null ? `${summary.mean_reprojection_error_px}px` : 'N/A'}
            </div>
            <span className="text-[11px] text-slate-500">Camera-plane residual</span>
          </div>
        </div>
      )}

      {/* Main Workspace: 3D Viewer & Bidirectional Inspection Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Side: 3D Viewer & Filters (8 Cols) */}
        <div className="lg:col-span-8 space-y-4">
          {/* Filters Bar */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-1.5 text-slate-400">
                <Filter size={14} />
                <span>Filters:</span>
              </div>

              {/* Type Filter */}
              <select
                value={filterType}
                onChange={(e) => setFilterType(e.target.value)}
                className="bg-slate-800 border border-slate-700 text-slate-200 rounded px-2 py-1"
              >
                <option value="ALL">All Deterioration Types</option>
                <option value="crack">Crack</option>
                <option value="erosion">Erosion</option>
                <option value="spalling">Spalling</option>
                <option value="discoloration">Discoloration</option>
                <option value="biological_growth">Biological Growth</option>
              </select>

              {/* Material Filter */}
              <select
                value={filterMaterial}
                onChange={(e) => setFilterMaterial(e.target.value)}
                className="bg-slate-800 border border-slate-700 text-slate-200 rounded px-2 py-1"
              >
                <option value="ALL">All Materials</option>
                <option value="sandstone">Sandstone</option>
                <option value="granite">Granite</option>
                <option value="brick">Brick</option>
                <option value="lime_mortar">Lime Mortar</option>
                <option value="UNKNOWN">UNKNOWN</option>
              </select>

              {/* Status Filter */}
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="bg-slate-800 border border-slate-700 text-slate-200 rounded px-2 py-1"
              >
                <option value="ALL">All Statuses</option>
                <option value="MAPPED">MAPPED</option>
                <option value="PARTIALLY_MAPPED">PARTIALLY MAPPED</option>
                <option value="NO_SURFACE_INTERSECTION">NO INTERSECTION</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-slate-400">Min Conf:</span>
              <input
                type="range"
                min="0"
                max="0.95"
                step="0.05"
                value={minConfidence}
                onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
                className="w-16 accent-amber-500"
              />
              <span className="font-mono text-slate-300">{(minConfidence * 100).toFixed(0)}%</span>
            </div>
          </div>

          {/* 3D Model Viewer with Mapped Damage Markers */}
          {reconstruction ? (
            <div className="relative rounded-2xl overflow-hidden border border-slate-800 bg-slate-950 min-h-[520px]">
              <ModelViewer3D
                modelUrl={`/api/photogrammetry/reconstructions/${reconstruction.id}/download?model_type=mesh`}
                isDemo={reconstruction.is_demo}
                modelType="mesh"
                cameraPoses={reconstruction.camera_poses || []}
                boundingBox={reconstruction.bounding_box}
                pointCount={reconstruction.point_count}
                vertexCount={reconstruction.mesh_vertex_count}
                triangleCount={reconstruction.mesh_triangle_count}
                reprojectionError={reconstruction.mean_reprojection_error}
                damageMappings={filteredMappings}
                selectedMappingId={selectedMapping?.id}
                onSelectDamagePoint={(item) => setSelectedMapping(item)}
                showDamageMarkers={true}
              />
            </div>
          ) : (
            <div className="h-[520px] bg-slate-950 border border-slate-800 rounded-2xl flex items-center justify-center text-slate-500">
              No 3D Model available for selected survey.
            </div>
          )}

          {/* Filter count indicator */}
          <div className="flex justify-between items-center text-xs text-slate-400 px-1">
            <span>
              Showing <strong className="text-slate-200">{filteredMappings.length}</strong> of{' '}
              <strong className="text-slate-200">{mappings.length}</strong> 3D damage points
            </span>
            <span className="italic">
              Click any colored damage marker on the 3D surface to inspect details.
            </span>
          </div>
        </div>

        {/* Right Side: Bidirectional Inspection Panel (4 Cols) */}
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
            <h2 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2 border-b border-slate-800 pb-3">
              <Target size={16} className="text-amber-500" />
              Damage Traceability Inspector
            </h2>

            {selectedMapping ? (
              <div className="space-y-4">
                {/* Defect & Material Headers */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2.5 py-1 rounded-md text-xs font-bold border uppercase tracking-wider ${getDefectColorClass(
                        selectedMapping.deterioration_type
                      )}`}
                    >
                      {selectedMapping.deterioration_type}
                    </span>
                    <span className="text-xs font-semibold text-slate-400">
                      {(selectedMapping.deterioration_confidence * 100).toFixed(0)}% conf
                    </span>
                  </div>
                  {getStatusBadge(selectedMapping.mapping_status)}
                </div>

                {/* Substrate Material Propagation */}
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                  <div className="text-[11px] text-slate-400 uppercase font-semibold">
                    Underlying Substrate:
                  </div>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-sm font-bold text-slate-200 capitalize">
                      {selectedMapping.material_class || 'UNKNOWN'}
                    </span>
                    <span className="text-xs text-slate-400 font-mono">
                      {selectedMapping.material_confidence != null
                        ? `${(selectedMapping.material_confidence * 100).toFixed(0)}% conf`
                        : 'Unrated'}
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-500 mt-1">
                    Association: {selectedMapping.material_association_status}
                  </div>
                </div>

                {/* 3D Coordinates Grid */}
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
                  <div className="text-[11px] text-slate-400 uppercase font-semibold flex items-center justify-between">
                    <span>3D World Coordinates:</span>
                    <span className="text-[10px] text-amber-400 font-normal">
                      {selectedMapping.scale_status} UNITS
                    </span>
                  </div>
                  {selectedMapping.world_point ? (
                    <div className="grid grid-cols-3 gap-2 font-mono text-center text-xs">
                      <div className="bg-slate-900 p-1.5 rounded">
                        <span className="text-[10px] text-slate-500 block">X</span>
                        <span className="text-slate-200 font-semibold">{selectedMapping.world_point.x}</span>
                      </div>
                      <div className="bg-slate-900 p-1.5 rounded">
                        <span className="text-[10px] text-slate-500 block">Y</span>
                        <span className="text-slate-200 font-semibold">{selectedMapping.world_point.y}</span>
                      </div>
                      <div className="bg-slate-900 p-1.5 rounded">
                        <span className="text-[10px] text-slate-500 block">Z</span>
                        <span className="text-slate-200 font-semibold">{selectedMapping.world_point.z}</span>
                      </div>
                    </div>
                  ) : (
                    <div className="text-xs text-rose-400 italic">No 3D surface intersection.</div>
                  )}
                  <div className="text-[10px] text-slate-500 italic mt-1">
                    Method: {selectedMapping.mapping_method} ({selectedMapping.surface_source})
                  </div>
                </div>

                {/* Reprojection & Quality Validation */}
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
                  <div className="text-[11px] text-slate-400 uppercase font-semibold flex items-center justify-between">
                    <span>Reprojection Residual:</span>
                    <button
                      onClick={() => handleValidateMapping(selectedMapping.id)}
                      disabled={validating}
                      className="text-[10px] text-amber-400 hover:text-amber-300 font-semibold flex items-center gap-1"
                    >
                      <RefreshCw size={11} className={validating ? 'animate-spin' : ''} />
                      Verify Reprojection
                    </button>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-slate-300 font-mono">
                      {selectedMapping.reprojection_error_px != null
                        ? `${selectedMapping.reprojection_error_px} px`
                        : 'Uncalculated'}
                    </span>
                    <span className="text-[11px] text-slate-500">
                      Threshold: {reprojThreshold} px
                    </span>
                  </div>

                  {validationResult && validationResult.mapping_id === selectedMapping.id && (
                    <div
                      className={`text-[11px] p-2 rounded mt-2 border ${
                        validationResult.is_valid
                          ? 'bg-emerald-950/30 border-emerald-800/50 text-emerald-300'
                          : 'bg-rose-950/30 border-rose-800/50 text-rose-300'
                      }`}
                    >
                      {validationResult.notes}
                    </div>
                  )}
                </div>

                {/* Source 2D Photo Reference */}
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-2">
                  <div className="text-[11px] text-slate-400 uppercase font-semibold flex items-center gap-1.5">
                    <ImageIcon size={13} />
                    <span>Source 2D Image Reference:</span>
                  </div>
                  <div className="text-xs font-mono text-slate-300 truncate">
                    {selectedMapping.image_filename || selectedMapping.image_id}
                  </div>
                  <div className="text-[11px] text-slate-500">
                    Image Point: (u: {selectedMapping.image_point.x}, v: {selectedMapping.image_point.y})
                  </div>
                  {selectedMapping.bounding_box && (
                    <div className="text-[10px] text-slate-500 font-mono">
                      Box: [{selectedMapping.bounding_box.x}, {selectedMapping.bounding_box.y},{' '}
                      {selectedMapping.bounding_box.w}×{selectedMapping.bounding_box.h}]
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center py-10 text-slate-500 text-xs italic">
                Select a damage marker on the 3D model or choose from the list below to inspect provenance.
              </div>
            )}
          </div>

          {/* Detections Quick List */}
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 space-y-2 max-h-72 overflow-y-auto">
            <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block mb-2">
              Detections in Survey ({filteredMappings.length}):
            </span>
            {filteredMappings.map((m) => (
              <button
                key={m.id}
                onClick={() => setSelectedMapping(m)}
                className={`w-full text-left p-2.5 rounded-lg border text-xs flex items-center justify-between transition-colors ${
                  selectedMapping?.id === m.id
                    ? 'bg-amber-500/10 border-amber-500/40 text-amber-200'
                    : 'bg-slate-950 border-slate-800 text-slate-300 hover:bg-slate-800'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`w-2.5 h-2.5 rounded-full ${
                      m.mapping_status === 'MAPPED'
                        ? 'bg-emerald-400'
                        : m.mapping_status === 'PARTIALLY_MAPPED'
                        ? 'bg-amber-400'
                        : 'bg-rose-400'
                    }`}
                  />
                  <span className="font-semibold capitalize">{m.deterioration_type}</span>
                  <span className="text-slate-500">({m.material_class})</span>
                </div>
                <span className="font-mono text-slate-400">
                  {(m.deterioration_confidence * 100).toFixed(0)}%
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Survey Material x Deterioration Cross-Tabulation Matrix */}
      {summary && summary.material_deterioration_cross_tabulation && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
              <Layers size={16} className="text-amber-500" />
              Substrate Vulnerability Matrix: Material × Deterioration
            </h3>
            <span className="text-xs text-slate-400">
              Aggregated across all {summary.total_eligible_detections} detections
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 bg-slate-950/50">
                  <th className="py-2.5 px-3">Substrate Class</th>
                  <th className="py-2.5 px-3">Cracks</th>
                  <th className="py-2.5 px-3">Erosion</th>
                  <th className="py-2.5 px-3">Spalling</th>
                  <th className="py-2.5 px-3">Discoloration</th>
                  <th className="py-2.5 px-3">Biological Growth</th>
                  <th className="py-2.5 px-3 font-semibold">Total Defects</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {Object.entries(summary.material_deterioration_cross_tabulation).map(
                  ([mat, defects]) => {
                    const rowTotal = Object.values(defects).reduce((a, b) => a + b, 0);
                    return (
                      <tr key={mat} className="hover:bg-slate-800/40">
                        <td className="py-2.5 px-3 font-semibold text-slate-200 capitalize">
                          {mat}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-slate-300">
                          {defects['crack'] || 0}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-slate-300">
                          {defects['erosion'] || 0}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-slate-300">
                          {defects['spalling'] || 0}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-slate-300">
                          {defects['discoloration'] || 0}
                        </td>
                        <td className="py-2.5 px-3 font-mono text-slate-300">
                          {defects['biological_growth'] || 0}
                        </td>
                        <td className="py-2.5 px-3 font-mono font-bold text-amber-400">
                          {rowTotal}
                        </td>
                      </tr>
                    );
                  }
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Research Methodology & Academic Notice Footer */}
      <div className="bg-slate-900/50 border border-slate-800/80 rounded-xl p-4 text-xs text-slate-400 space-y-1.5">
        <div className="font-semibold text-slate-300 flex items-center gap-1.5">
          <ShieldCheck size={14} className="text-amber-500" />
          <span>Research Limitation & Traceability Guarantee</span>
        </div>
        <p className="leading-relaxed">
          {summary?.research_disclaimer ||
            '2D-to-3D mapping quality depends on the accuracy and completeness of photogrammetric camera calibration, camera poses, reconstruction geometry, and source deterioration localization. Mapped coordinates should therefore be interpreted within the documented reconstruction coordinate system and scale.'}
        </p>
      </div>
    </div>
  );
};
