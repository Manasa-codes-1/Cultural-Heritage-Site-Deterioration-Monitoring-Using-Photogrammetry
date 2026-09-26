import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Cpu,
  Play,
  RotateCw,
  AlertTriangle,
  FileCode,
  Download,
  Terminal,
  Activity,
  Layers,
  Sparkles,
  Clock,
  HardDrive,
} from 'lucide-react';

import { api } from '../api/client';
import type {
  Survey,
  PhotogrammetryAvailability,
  Reconstruction,
  ReconstructionTrigger,
} from '../types';
import { ModelViewer3D } from '../components/viewer/ModelViewer3D';

interface PhotogrammetryPageProps {
  initialSurveyId?: string;
  onNavigateToQuality?: (surveyId: string) => void;
}

export const PhotogrammetryPage: React.FC<PhotogrammetryPageProps> = ({
  initialSurveyId,
  onNavigateToQuality,
}) => {
  // Data states
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [selectedSurveyId, setSelectedSurveyId] = useState<string>(initialSurveyId || '');
  const [availability, setAvailability] = useState<PhotogrammetryAvailability | null>(null);
  const [reconstruction, setReconstruction] = useState<Reconstruction | null>(null);
  const [selectedModelType, setSelectedModelType] = useState<'mesh' | 'dense' | 'sparse'>('mesh');

  // Execution states
  const [engineChoice, setEngineChoice] = useState<string>('auto');
  const [denseMVS, setDenseMVS] = useState<boolean>(true);
  const [generateMesh, setGenerateMesh] = useState<boolean>(true);
  const [triggering, setTriggering] = useState<boolean>(false);
  const [loadingRecon, setLoadingRecon] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [showLogsModal, setShowLogsModal] = useState<boolean>(false);
  const [logsText, setLogsText] = useState<string>('');

  const pollingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);


  // Load system diagnostics and survey list
  useEffect(() => {
    const init = async () => {
      try {
        const [availData, surveysData] = await Promise.all([
          api.getPhotogrammetryAvailability(),
          api.getSurveys(),
        ]);
        setAvailability(availData);
        setSurveys(surveysData);

        if (!selectedSurveyId && surveysData.length > 0) {
          // Default to survey with most images or first
          const sorted = [...surveysData].sort((a, b) => b.image_count - a.image_count);
          setSelectedSurveyId(sorted[0].id);
        }
      } catch (err: unknown) {
        const error = err as Error;
        setErrorMsg(`Failed to initialize photogrammetry workspace: ${error.message}`);
      }
    };
    init();
  }, []);

  // Fetch reconstruction for selected survey
  const loadSurveyReconstruction = useCallback(async (surveyId: string) => {
    if (!surveyId) return;
    setLoadingRecon(true);
    try {
      const recon = await api.getSurveyReconstruction(surveyId);
      setReconstruction(recon);
      setErrorMsg(null);
    } catch {
      // 404 is normal if survey has not been reconstructed yet
      setReconstruction(null);
    } finally {
      setLoadingRecon(false);
    }
  }, []);

  useEffect(() => {
    if (selectedSurveyId) {
      loadSurveyReconstruction(selectedSurveyId);
    }
  }, [selectedSurveyId, loadSurveyReconstruction]);

  // Polling when reconstruction is pending or running
  useEffect(() => {
    if (!reconstruction || (reconstruction.status !== 'running' && reconstruction.status !== 'pending')) {
      if (pollingTimerRef.current) clearInterval(pollingTimerRef.current);
      return;
    }

    pollingTimerRef.current = setInterval(async () => {
      try {
        const status = await api.getReconstructionStatus(reconstruction.id);
        setReconstruction((prev) => (prev ? { ...prev, ...status } : null));

        if (status.status === 'completed' || status.status === 'failed') {
          if (pollingTimerRef.current) clearInterval(pollingTimerRef.current);
          // Reload full model record
          loadSurveyReconstruction(selectedSurveyId);
        }
      } catch (e) {
        console.error('Reconstruction polling error:', e);
      }
    }, 1500);

    return () => {
      if (pollingTimerRef.current) clearInterval(pollingTimerRef.current);
    };
  }, [reconstruction?.id, reconstruction?.status, selectedSurveyId, loadSurveyReconstruction]);

  // Trigger reconstruction
  const handleTriggerReconstruction = async () => {
    if (!selectedSurveyId) return;
    setTriggering(true);
    setErrorMsg(null);

    const payload: ReconstructionTrigger = {
      engine: engineChoice,
      dense: denseMVS,
      generate_mesh: generateMesh,
      force: true,
    };

    try {
      const recon = await api.triggerReconstruction(selectedSurveyId, payload);
      setReconstruction(recon);
    } catch (err: unknown) {
      const error = err as Error;
      setErrorMsg(`Reconstruction trigger failed: ${error.message}`);
    } finally {
      setTriggering(false);
    }
  };

  // View Logs
  const handleOpenLogs = async () => {
    if (!reconstruction) return;
    try {
      const logs = await api.getReconstructionLogs(reconstruction.id);
      setLogsText(logs);
      setShowLogsModal(true);
    } catch (e: unknown) {
      const error = e as Error;
      setLogsText(`Could not load logs: ${error.message}`);
      setShowLogsModal(true);
    }
  };

  const currentSurvey = surveys.find((s) => s.id === selectedSurveyId);
  const isRunning = reconstruction?.status === 'running' || reconstruction?.status === 'pending';

  return (
    <div className="page-container p-6 space-y-6 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-700/60 pb-5">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-amber-500 mb-1">
            <span>Phase 3</span>
            <span>•</span>
            <span>3D Geometric Modeling</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <Box className="text-amber-500" size={26} />
            Photogrammetry & 3D Reconstruction
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Convert calibrated multi-view optical survey photographs into research-grade 3D point
            clouds and polygonal heritage surface meshes.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          {reconstruction && (
            <button
              onClick={handleOpenLogs}
              className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-sm flex items-center gap-2 transition"
            >
              <Terminal size={15} className="text-sky-400" />
              <span>Audit Logs</span>
            </button>
          )}

          <button
            onClick={() => loadSurveyReconstruction(selectedSurveyId)}
            className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg transition"
            title="Refresh Reconstruction Status"
          >
            <RotateCw size={16} className={loadingRecon ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Error banner */}
      {errorMsg && (
        <div className="p-4 bg-rose-950/60 border border-rose-800 text-rose-200 rounded-xl flex items-start gap-3">
          <AlertTriangle className="text-rose-400 shrink-0 mt-0.5" size={18} />
          <div className="text-sm">
            <span className="font-semibold">Operation Error: </span>
            {errorMsg}
          </div>
        </div>
      )}

      {/* System Diagnostics & Capabilities */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* COLMAP Status */}
        <div className="bg-slate-800/60 border border-slate-700/80 rounded-xl p-4 flex items-start gap-3">
          <Cpu className={availability?.colmap_available ? 'text-emerald-400' : 'text-amber-400'} size={24} />
          <div>
            <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold">COLMAP Engine</div>
            <div className="text-sm font-semibold text-slate-200 mt-0.5">
              {availability?.colmap_available ? 'Available (Real SfM)' : 'Not in PATH (Demo Active)'}
            </div>
            <div className="text-xs text-slate-400 mt-1">
              {availability?.colmap_version || 'Built-in procedural engine'}
            </div>
          </div>
        </div>

        {/* Hardware & GPU Acceleration */}
        <div className="bg-slate-800/60 border border-slate-700/80 rounded-xl p-4 flex items-start gap-3">
          <Activity className={availability?.cuda_available ? 'text-emerald-400' : 'text-sky-400'} size={24} />
          <div>
            <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Hardware Accelerator</div>
            <div className="text-sm font-semibold text-slate-200 mt-0.5">
              {availability?.cuda_available ? 'NVIDIA CUDA GPU' : 'CPU / Intel Iris Xe'}
            </div>
            <div className="text-xs text-slate-400 mt-1">
              {availability?.cuda_available ? 'Dense stereo accelerated' : 'Multi-thread CPU processing'}
            </div>
          </div>
        </div>

        {/* Open3D Geometry Library */}
        <div className="bg-slate-800/60 border border-slate-700/80 rounded-xl p-4 flex items-start gap-3">
          <Layers className={availability?.open3d_available ? 'text-emerald-400' : 'text-amber-400'} size={24} />
          <div>
            <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Open3D Processor</div>
            <div className="text-sm font-semibold text-slate-200 mt-0.5">
              {availability?.open3d_available ? `v${availability.open3d_version}` : 'Unavailable'}
            </div>
            <div className="text-xs text-slate-400 mt-1">
              Voxel filter, normals & bounding box
            </div>
          </div>
        </div>

        {/* Mode & Research Integrity */}
        <div className="bg-slate-800/60 border border-slate-700/80 rounded-xl p-4 flex items-start gap-3">
          <Sparkles className="text-amber-400" size={24} />
          <div>
            <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Pipeline Integrity</div>
            <div className="text-sm font-semibold text-amber-300 mt-0.5">
              {reconstruction?.is_demo ? 'Demo Mode (Labeled)' : reconstruction ? 'Real Photogrammetry' : 'Ready'}
            </div>
            <div className="text-xs text-slate-400 mt-1">
              Zero fabricated measurements
            </div>
          </div>
        </div>
      </div>

      {/* Survey Selection & Trigger Workspace */}
      <div className="bg-slate-800/50 border border-slate-700/70 rounded-xl p-5">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-end">
          {/* Survey Selector */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Select Field Survey
            </label>
            <select
              value={selectedSurveyId}
              onChange={(e) => setSelectedSurveyId(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-amber-500"
            >
              {surveys.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.survey_code} — {s.image_count} photos ({s.status})
                </option>
              ))}
            </select>
            {currentSurvey && (
              <div className="flex items-center gap-3 mt-2 text-xs text-slate-400">
                <span>Photos: <strong className="text-slate-300">{currentSurvey.image_count}</strong></span>
                <span>•</span>
                <span>Avg Quality: <strong className="text-slate-300">{currentSurvey.average_quality_score ? `${currentSurvey.average_quality_score.toFixed(1)}/100` : 'Pending'}</strong></span>
                {onNavigateToQuality && (
                  <>
                    <span>•</span>
                    <button
                      onClick={() => onNavigateToQuality(currentSurvey.id)}
                      className="text-amber-400 hover:underline"
                    >
                      Check Overlap
                    </button>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Engine & Configuration Options */}
          <div className="space-y-2">
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Reconstruction Pipeline Options
            </label>
            <div className="grid grid-cols-2 gap-2">
              <select
                value={engineChoice}
                onChange={(e) => setEngineChoice(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
              >
                <option value="auto">Auto (COLMAP or Mock)</option>
                <option value="mock">Mock Engine (Offline Demo)</option>
                {availability?.colmap_available && <option value="colmap">COLMAP Only</option>}
              </select>

              <div className="flex items-center gap-4 text-xs text-slate-300 px-2">
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={denseMVS}
                    onChange={(e) => setDenseMVS(e.target.checked)}
                    className="rounded text-amber-500 bg-slate-900 border-slate-700"
                  />
                  <span>Dense MVS</span>
                </label>
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={generateMesh}
                    onChange={(e) => setGenerateMesh(e.target.checked)}
                    className="rounded text-amber-500 bg-slate-900 border-slate-700"
                  />
                  <span>3D Mesh</span>
                </label>
              </div>
            </div>
          </div>

          {/* Launch Button */}
          <div>
            <button
              onClick={handleTriggerReconstruction}
              disabled={triggering || isRunning || !currentSurvey || currentSurvey.image_count === 0}
              className={`w-full py-2.5 px-4 rounded-lg font-semibold text-sm flex items-center justify-center gap-2 transition ${
                isRunning
                  ? 'bg-amber-600/50 text-amber-200 cursor-not-allowed'
                  : currentSurvey && currentSurvey.image_count > 0
                  ? 'bg-amber-600 hover:bg-amber-500 text-white shadow-lg shadow-amber-950/40'
                  : 'bg-slate-700 text-slate-400 cursor-not-allowed'
              }`}
            >
              {isRunning ? (
                <>
                  <div className="loading-spinner w-4 h-4 border-2" />
                  <span>Processing Stage ({reconstruction?.current_stage || 'RUNNING'})...</span>
                </>
              ) : (
                <>
                  <Play size={16} />
                  <span>
                    {reconstruction ? 'Re-run 3D Reconstruction' : 'Start 3D Reconstruction'}
                  </span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Live Progress Bar when running */}
        {isRunning && reconstruction && (
          <div className="mt-4 pt-4 border-t border-slate-700/60">
            <div className="flex justify-between items-center text-xs mb-1.5">
              <span className="font-semibold text-amber-400 flex items-center gap-2">
                <Activity size={14} className="animate-pulse" />
                Pipeline Stage: {reconstruction.current_stage}
              </span>
              <span className="font-mono text-slate-300">{reconstruction.progress_percent}%</span>
            </div>
            <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-700">
              <div
                className="bg-amber-500 h-full transition-all duration-300"
                style={{ width: `${reconstruction.progress_percent}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Main 3D Model Display or Placeholder */}
      {reconstruction && reconstruction.status === 'completed' ? (
        <div className="space-y-4">
          {/* Model Asset Type Selector & Downloader */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-800/40 border border-slate-700/60 rounded-xl px-4 py-3">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mr-1">
                Active 3D Asset:
              </span>
              <button
                onClick={() => setSelectedModelType('mesh')}
                className={`px-3 py-1.5 text-xs rounded-lg font-medium transition ${
                  selectedModelType === 'mesh'
                    ? 'bg-amber-500 text-slate-900 font-semibold'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                Surface Mesh (.ply)
              </button>
              <button
                onClick={() => setSelectedModelType('dense')}
                className={`px-3 py-1.5 text-xs rounded-lg font-medium transition ${
                  selectedModelType === 'dense'
                    ? 'bg-amber-500 text-slate-900 font-semibold'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                Dense Cloud ({reconstruction.dense_point_count.toLocaleString()} pts)
              </button>
              <button
                onClick={() => setSelectedModelType('sparse')}
                className={`px-3 py-1.5 text-xs rounded-lg font-medium transition ${
                  selectedModelType === 'sparse'
                    ? 'bg-amber-500 text-slate-900 font-semibold'
                    : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                }`}
              >
                Sparse Tie Cloud ({reconstruction.sparse_point_count.toLocaleString()} pts)
              </button>
            </div>

            {/* Direct File Downloads */}
            <div className="flex items-center gap-2">
              <a
                href={api.getReconstructionModelUrl(reconstruction.id, selectedModelType)}
                download={`survey_${selectedSurveyId}_${selectedModelType}.ply`}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs flex items-center gap-1.5 transition"
              >
                <Download size={13} className="text-amber-400" />
                <span>Export {selectedModelType.toUpperCase()}</span>
              </a>
              <a
                href={api.getReconstructionModelUrl(reconstruction.id, 'obj')}
                download={`survey_${selectedSurveyId}_mesh.obj`}
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs flex items-center gap-1.5 transition"
              >
                <FileCode size={13} className="text-sky-400" />
                <span>Export OBJ</span>
              </a>
            </div>
          </div>

          {/* Three.js Interactive WebGL Viewport */}
          <ModelViewer3D
            modelUrl={api.getReconstructionModelUrl(reconstruction.id, selectedModelType)}
            isDemo={reconstruction.is_demo}
            modelType={selectedModelType}
            cameraPoses={reconstruction.camera_poses || []}
            boundingBox={reconstruction.bounding_box}
            pointCount={reconstruction.point_count}
            vertexCount={reconstruction.mesh_vertex_count}
            triangleCount={reconstruction.mesh_triangle_count}
            reprojectionError={reconstruction.mean_reprojection_error}
          />

          {/* Reconstruction Scientific Metrics Details */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-4">
              <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase tracking-wider">
                <Sparkles size={14} className="text-amber-400" />
                <span>Total 3D Points</span>
              </div>
              <div className="text-2xl font-bold font-mono text-slate-100 mt-2">
                {reconstruction.point_count.toLocaleString()}
              </div>
              <div className="text-xs text-slate-400 mt-1">
                Dense: {reconstruction.dense_point_count.toLocaleString()} • Sparse: {reconstruction.sparse_point_count.toLocaleString()}
              </div>
            </div>

            <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-4">
              <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase tracking-wider">
                <Box size={14} className="text-sky-400" />
                <span>Mesh Polygonal Topology</span>
              </div>
              <div className="text-2xl font-bold font-mono text-slate-100 mt-2">
                {reconstruction.mesh_triangle_count.toLocaleString()}
              </div>
              <div className="text-xs text-slate-400 mt-1">
                Vertices: {reconstruction.mesh_vertex_count.toLocaleString()} triangles
              </div>
            </div>

            <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-4">
              <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase tracking-wider">
                <Clock size={14} className="text-emerald-400" />
                <span>Mean Reprojection Error</span>
              </div>
              <div className="text-2xl font-bold font-mono text-slate-100 mt-2">
                {reconstruction.mean_reprojection_error
                  ? `${reconstruction.mean_reprojection_error.toFixed(2)} px`
                  : 'N/A'}
              </div>
              <div className="text-xs text-slate-400 mt-1">
                Registered: {reconstruction.registered_image_count} of {reconstruction.camera_count} images
              </div>
            </div>

            <div className="bg-slate-800/40 border border-slate-700/60 rounded-xl p-4">
              <div className="flex items-center gap-2 text-slate-400 text-xs font-semibold uppercase tracking-wider">
                <HardDrive size={14} className="text-purple-400" />
                <span>Physical Enclosure</span>
              </div>
              <div className="text-base font-bold font-mono text-slate-100 mt-2">
                {reconstruction.bounding_box
                  ? `${reconstruction.bounding_box.dimensions[0]}m × ${reconstruction.bounding_box.dimensions[1]}m`
                  : 'Calculated in meters'}
              </div>
              <div className="text-xs text-slate-400 mt-1">
                Depth: {reconstruction.bounding_box ? `${reconstruction.bounding_box.dimensions[2]}m` : 'N/A'}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-slate-800/30 border border-dashed border-slate-700 rounded-2xl p-12 text-center">
          <Box size={48} className="mx-auto text-slate-600 mb-4" />
          <h3 className="text-lg font-semibold text-slate-300">
            {reconstruction?.status === 'failed'
              ? 'Reconstruction Failed'
              : 'No 3D Model Generated Yet'}
          </h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto mt-2">
            {reconstruction?.status === 'failed'
              ? `Pipeline error: ${reconstruction.error_message || 'Review execution logs.'}`
              : 'Select a survey above with uploaded imagery and click "Start 3D Reconstruction" to trigger the photogrammetric pipeline.'}
          </p>
        </div>
      )}

      {/* Execution Logs Modal */}
      {showLogsModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-4xl max-h-[85vh] flex flex-col shadow-2xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Terminal size={18} className="text-amber-500" />
                <h3 className="font-semibold text-slate-200">Reconstruction Pipeline Audit Logs</h3>
              </div>
              <button
                onClick={() => setShowLogsModal(false)}
                className="text-slate-400 hover:text-slate-200 text-sm font-semibold px-2 py-1 rounded"
              >
                ✕ Close
              </button>
            </div>
            <div className="p-6 overflow-y-auto flex-1 font-mono text-xs text-slate-300 bg-slate-950 rounded-b-2xl whitespace-pre-wrap select-text leading-relaxed">
              {logsText}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
