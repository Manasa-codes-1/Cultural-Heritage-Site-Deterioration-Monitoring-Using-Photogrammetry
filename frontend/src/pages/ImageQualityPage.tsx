import React, { useEffect, useState } from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Sparkles,
  RefreshCw,
  Info,
  Network,
  Split,
  Layers,
  ShieldAlert,
  Play,
  Share2,
} from 'lucide-react';
import type {
  Survey,
  QualitySummary,
  ImageRecord,
  SurveyReadiness,
  PairMatchRecord,
} from '../types';
import { api } from '../api/client';
import { StatusBadge } from '../components/common/StatusBadge';

interface ImageQualityPageProps {
  initialSurveyId?: string;
  onSelectSurvey: (surveyId: string) => void;
}

type SubTab = 'readiness' | 'pairs' | 'individual';

export const ImageQualityPage: React.FC<ImageQualityPageProps> = ({
  initialSurveyId,
  onSelectSurvey,
}) => {
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [selectedSurveyId, setSelectedSurveyId] = useState<string>(initialSurveyId || '');
  const [currentSubTab, setCurrentSubTab] = useState<SubTab>('readiness');

  // Phase 1 data
  const [summary, setSummary] = useState<QualitySummary | null>(null);
  const [images, setImages] = useState<ImageRecord[]>([]);

  // Phase 2 data
  const [readiness, setReadiness] = useState<SurveyReadiness | null>(null);
  const [pairs, setPairs] = useState<PairMatchRecord[]>([]);
  const [pairsFilter, setPairsFilter] = useState<string>('ALL');

  // Pair matcher interactive state
  const [pairImageA, setPairImageA] = useState<string>('');
  const [pairImageB, setPairImageB] = useState<string>('');
  const [pairMatchingLoading, setPairMatchingLoading] = useState<boolean>(false);
  const [activePairResult, setActivePairResult] = useState<PairMatchRecord | null>(null);

  const [loading, setLoading] = useState<boolean>(false);
  const [analyzingCollection, setAnalyzingCollection] = useState<boolean>(false);

  useEffect(() => {
    const fetchSurveys = async () => {
      try {
        const list = await api.getSurveys();
        setSurveys(list);
        if (!selectedSurveyId && list.length > 0) {
          setSelectedSurveyId(list[0].id);
        }
      } catch (err) {
        console.error('Failed to load surveys', err);
      }
    };
    fetchSurveys();
  }, []);

  const loadAllData = async (surveyId: string) => {
    if (!surveyId) return;
    setLoading(true);
    try {
      // 1. Load Phase 1 individual quality data
      const [sumData, detailData] = await Promise.all([
        api.getSurveyQualitySummary(surveyId).catch(() => null),
        api.getSurveyDetail(surveyId).catch(() => null),
      ]);
      if (sumData) setSummary(sumData);
      if (detailData && detailData.images) {
        setImages(detailData.images);
        if (detailData.images.length >= 2) {
          setPairImageA(detailData.images[0].id);
          setPairImageB(detailData.images[1].id);
        }
      }

      // 2. Load Phase 2 readiness & pairs if available
      try {
        const readData = await api.getSurveyReadiness(surveyId);
        setReadiness(readData);
      } catch {
        setReadiness(null);
      }

      try {
        const pairsData = await api.getSurveyPairs(surveyId);
        setPairs(pairsData);
      } catch {
        setPairs([]);
      }
    } catch (err) {
      console.error('Failed to load quality and readiness data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedSurveyId) {
      loadAllData(selectedSurveyId);
    }
  }, [selectedSurveyId]);

  const handleRunCollectionAnalysis = async () => {
    if (!selectedSurveyId) return;
    setAnalyzingCollection(true);
    try {
      const result = await api.analyzeSurveyCollection(selectedSurveyId);
      setReadiness(result);
      const updatedPairs = await api.getSurveyPairs(selectedSurveyId);
      setPairs(updatedPairs);
    } catch (err) {
      alert(`Collection analysis failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setAnalyzingCollection(false);
    }
  };

  const handleMatchSelectedPair = async () => {
    if (!pairImageA || !pairImageB) return;
    if (pairImageA === pairImageB) {
      alert('Please select two distinct images to compare.');
      return;
    }
    setPairMatchingLoading(true);
    try {
      const res = await api.matchPair({ image_a_id: pairImageA, image_b_id: pairImageB });
      setActivePairResult(res);
      // Refresh pairs list
      const updatedPairs = await api.getSurveyPairs(selectedSurveyId);
      setPairs(updatedPairs);
    } catch (err) {
      alert(`Pair match failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setPairMatchingLoading(false);
    }
  };

  const filteredPairs = pairs.filter((p) => {
    if (pairsFilter === 'ALL') return true;
    return p.status === pairsFilter;
  });

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <div>
          <div className="flex items-center gap-2">
            <span className="navbar-badge">Phase 2 Active</span>
            <span className="text-xs text-amber-400 font-semibold">Dual-Layer Optical & Pairwise Pipeline</span>
          </div>
          <h2 className="page-title mt-1">Image Quality & Photogrammetry Readiness</h2>
          <p className="page-description">
            Evaluates individual image clarity (blur, exposure, features) and collection-level feature correspondence connectivity.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="text-xs font-semibold text-slate-300">Survey Epoch:</label>
          <select
            value={selectedSurveyId}
            onChange={(e) => setSelectedSurveyId(e.target.value)}
            className="form-select text-xs py-1.5 min-w-[200px]"
          >
            {surveys.map((s) => (
              <option key={s.id} value={s.id}>
                {s.survey_code} ({s.image_count} images)
              </option>
            ))}
          </select>
          <button
            onClick={() => selectedSurveyId && loadAllData(selectedSurveyId)}
            className="btn-secondary text-xs"
            title="Refresh assessment"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Sub-tab navigation */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-3 mb-6">
        <button
          onClick={() => setCurrentSubTab('readiness')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            currentSubTab === 'readiness'
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
              : 'text-slate-400 hover:text-slate-200 bg-slate-900/60'
          }`}
        >
          <Network size={14} />
          <span>Collection Readiness & Graph</span>
          {readiness && (
            <span className="ml-1 text-[10px] px-1.5 py-0.2 rounded bg-slate-800 font-mono">
              {readiness.readiness_status}
            </span>
          )}
        </button>

        <button
          onClick={() => setCurrentSubTab('pairs')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            currentSubTab === 'pairs'
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
              : 'text-slate-400 hover:text-slate-200 bg-slate-900/60'
          }`}
        >
          <Split size={14} />
          <span>Pairwise Feature Matching</span>
          {pairs.length > 0 && (
            <span className="ml-1 text-[10px] px-1.5 py-0.2 rounded bg-slate-800 font-mono">
              {pairs.length} pairs
            </span>
          )}
        </button>

        <button
          onClick={() => setCurrentSubTab('individual')}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            currentSubTab === 'individual'
              ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
              : 'text-slate-400 hover:text-slate-200 bg-slate-900/60'
          }`}
        >
          <Layers size={14} />
          <span>Individual Optical Checks</span>
          <span className="ml-1 text-[10px] px-1.5 py-0.2 rounded bg-slate-800 font-mono">
            {images.length}
          </span>
        </button>
      </div>

      {loading && !readiness && !summary ? (
        <div className="empty-box">
          <p className="text-slate-400">Evaluating optical and matching parameters...</p>
        </div>
      ) : images.length === 0 ? (
        <div className="empty-box">
          <Info size={32} className="text-slate-500 mb-2" />
          <p className="text-slate-300 font-medium">No survey images available to evaluate.</p>
          <p className="text-slate-500 text-xs mt-1">Upload images to this survey epoch to run the OpenCV assessment.</p>
          {selectedSurveyId && (
            <button
              onClick={() => onSelectSurvey(selectedSurveyId)}
              className="btn-primary mt-3 text-xs"
            >
              Upload Images Now
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-6">
          {/* ==================================================== */}
          {/* SUB-TAB 1: COLLECTION READINESS & CONNECTIVITY GRAPH */}
          {/* ==================================================== */}
          {currentSubTab === 'readiness' && (
            <div className="space-y-6">
              {/* Top Action & Status Banner */}
              <div className="card p-5 bg-gradient-to-r from-slate-900 via-slate-900 to-slate-950 border border-slate-800">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                      Photogrammetric Collection Suitability
                    </span>
                    <div className="flex items-center gap-3 mt-1">
                      <h3 className="text-xl font-bold text-slate-100">
                        {readiness?.readiness_status.replace(/_/g, ' ') || 'ANALYSIS REQUIRED'}
                      </h3>
                      <StatusBadge status={readiness?.readiness_status || 'pending'} />
                    </div>
                    <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
                      Evaluates whether image viewpoints possess sufficient overlap and feature density to form a connected reconstruction graph in Structure-from-Motion.
                    </p>
                  </div>

                  <button
                    onClick={handleRunCollectionAnalysis}
                    disabled={analyzingCollection || images.length < 2}
                    className="btn-primary text-xs shrink-0 self-start md:self-center"
                  >
                    <Play size={14} className={analyzingCollection ? 'animate-spin' : ''} />
                    <span>{analyzingCollection ? 'Extracting & Matching ORB...' : 'Run Collection Analysis'}</span>
                  </button>
                </div>
              </div>

              {readiness ? (
                <>
                  {/* Readiness Metrics Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="metric-card">
                      <div className="metric-icon-wrap bg-sky-950/40 text-sky-400">
                        <Layers size={20} />
                      </div>
                      <div className="metric-content">
                        <p className="metric-label">Images Analyzed</p>
                        <p className="metric-value font-mono">{readiness.images_analyzed}</p>
                      </div>
                    </div>

                    <div className="metric-card">
                      <div className="metric-icon-wrap bg-emerald-950/40 text-emerald-400">
                        <CheckCircle2 size={20} />
                      </div>
                      <div className="metric-content">
                        <p className="metric-label">Good Pairs</p>
                        <p className="metric-value font-mono text-emerald-400">
                          {readiness.good_pairs}{' '}
                          <span className="text-xs text-slate-400 font-normal">
                            ({readiness.pairs_analyzed > 0 ? ((readiness.good_pairs / readiness.pairs_analyzed) * 100).toFixed(0) : 0}%)
                          </span>
                        </p>
                      </div>
                    </div>

                    <div className="metric-card">
                      <div className="metric-icon-wrap bg-amber-950/40 text-amber-400">
                        <AlertTriangle size={20} />
                      </div>
                      <div className="metric-content">
                        <p className="metric-label">Warning / Poor Pairs</p>
                        <p className="metric-value font-mono text-amber-400">
                          {readiness.warning_pairs + readiness.poor_pairs}
                        </p>
                      </div>
                    </div>

                    <div className="metric-card">
                      <div className="metric-icon-wrap bg-rose-950/40 text-rose-400">
                        <Network size={20} />
                      </div>
                      <div className="metric-content">
                        <p className="metric-label">Isolated / Weak Views</p>
                        <p className={`metric-value font-mono ${readiness.isolated_image_ids.length > 0 ? 'text-rose-400' : 'text-slate-200'}`}>
                          {readiness.isolated_image_ids.length + readiness.weakly_connected_image_ids.length}
                        </p>
                      </div>
                    </div>
                  </div>

                  {/* Recommendations Box */}
                  {readiness.recommendations.length > 0 && (
                    <div className={`p-4 rounded-lg border ${
                      readiness.readiness_status === 'READY'
                        ? 'bg-emerald-950/20 border-emerald-800/60 text-emerald-200'
                        : readiness.readiness_status === 'READY_WITH_WARNINGS'
                        ? 'bg-amber-950/20 border-amber-800/60 text-amber-200'
                        : 'bg-rose-950/20 border-rose-800/60 text-rose-200'
                    }`}>
                      <div className="flex items-start gap-2.5">
                        <Info size={17} className="mt-0.5 shrink-0" />
                        <div className="space-y-1.5">
                          <h4 className="font-semibold text-xs uppercase tracking-wide">
                            Photogrammetric Recovery & Field Recommendations
                          </h4>
                          <ul className="text-xs space-y-1 list-disc list-inside">
                            {readiness.recommendations.map((rec, idx) => (
                              <li key={idx} className="leading-relaxed">{rec}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Image Connectivity Network Visualization */}
                  <div className="card">
                    <div className="card-header">
                      <div className="flex items-center gap-2">
                        <Share2 size={16} className="text-amber-400" />
                        <h3 className="card-title">Image Viewpoint Connectivity Network</h3>
                      </div>
                      <span className="text-xs text-slate-400">
                        {readiness.connectivity_nodes.length} Viewpoint Nodes • {readiness.connectivity_edges.length} Match Edges
                      </span>
                    </div>

                    <div className="card-body space-y-4">
                      {/* Visual Graph Representation */}
                      <div className="p-4 bg-slate-950/80 rounded-lg border border-slate-800">
                        <div className="text-xs text-slate-400 mb-3 flex items-center justify-between">
                          <span>Verified Feature Overlap Topology (Engineering Graph):</span>
                          <div className="flex items-center gap-3 text-[11px]">
                            <span className="flex items-center gap-1">
                              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" /> Well Connected (≥2 matches)
                            </span>
                            <span className="flex items-center gap-1">
                              <span className="w-2.5 h-2.5 rounded-full bg-amber-400" /> Weakly Connected (1 match)
                            </span>
                            <span className="flex items-center gap-1">
                              <span className="w-2.5 h-2.5 rounded-full bg-rose-400" /> Isolated (0 matches)
                            </span>
                          </div>
                        </div>

                        {/* Interactive Node Badges */}
                        <div className="flex flex-wrap gap-2.5 p-3 bg-slate-900/50 rounded border border-slate-800/80">
                          {readiness.connectivity_nodes.map((node) => {
                            let nodeBg = 'bg-emerald-950/50 border-emerald-700/60 text-emerald-300';
                            let dot = 'bg-emerald-400';
                            if (node.status === 'weakly_connected') {
                              nodeBg = 'bg-amber-950/50 border-amber-700/60 text-amber-300';
                              dot = 'bg-amber-400';
                            } else if (node.status === 'isolated') {
                              nodeBg = 'bg-rose-950/50 border-rose-700/60 text-rose-300';
                              dot = 'bg-rose-400';
                            }
                            return (
                              <div
                                key={node.id}
                                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono ${nodeBg}`}
                                title={`${node.filename}: ${node.degree} verified matching edge(s)`}
                              >
                                <span className={`w-2 h-2 rounded-full ${dot}`} />
                                <span className="font-semibold">{node.filename}</span>
                                <span className="text-[10px] opacity-80">({node.degree} edges)</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* Nodes Summary Table */}
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Viewpoint / Image</th>
                            <th>Verified Overlap Edges</th>
                            <th>Connectivity Status</th>
                            <th>Pre-Processing Assessment</th>
                          </tr>
                        </thead>
                        <tbody>
                          {readiness.connectivity_nodes.map((node) => (
                            <tr key={node.id}>
                              <td className="font-medium text-slate-200 font-mono text-xs">
                                {node.filename}
                              </td>
                              <td className="text-xs font-mono font-semibold">
                                {node.degree} connected view(s)
                              </td>
                              <td>
                                <StatusBadge status={node.status} />
                              </td>
                              <td className="text-xs text-slate-400">
                                {node.status === 'well_connected' && 'Adequate multi-view overlap for camera resection.'}
                                {node.status === 'weakly_connected' && 'Only one valid connection; vulnerable to tracking loss.'}
                                {node.status === 'isolated' && 'Isolated viewpoint; will fail triangulation without intermediate captures.'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              ) : (
                <div className="empty-box">
                  <Network size={32} className="text-slate-500 mb-2" />
                  <p className="text-slate-300 font-medium">Collection analysis has not been executed yet.</p>
                  <p className="text-slate-500 text-xs mt-1">
                    Click "Run Collection Analysis" above to extract ORB descriptors, evaluate pairwise correspondence, and construct the viewpoint connectivity graph.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* ==================================================== */}
          {/* SUB-TAB 2: PAIRWISE FEATURE MATCHING INSPECTOR      */}
          {/* ==================================================== */}
          {currentSubTab === 'pairs' && (
            <div className="space-y-6">
              {/* Interactive Pair Selector Card */}
              <div className="card">
                <div className="card-header">
                  <div className="flex items-center gap-2">
                    <Split size={16} className="text-amber-400" />
                    <h3 className="card-title">Test Interactive Pairwise Match</h3>
                  </div>
                  <span className="text-xs text-slate-400">ORB + BFMatcher (Hamming) + Lowe's Ratio (0.75)</span>
                </div>

                <div className="card-body space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 items-end">
                    <div>
                      <label className="text-xs font-semibold text-slate-300 block mb-1">Image A:</label>
                      <select
                        value={pairImageA}
                        onChange={(e) => setPairImageA(e.target.value)}
                        className="form-select text-xs py-1.5 w-full"
                      >
                        {images.map((img) => (
                          <option key={img.id} value={img.id}>
                            {img.filename}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-slate-300 block mb-1">Image B:</label>
                      <select
                        value={pairImageB}
                        onChange={(e) => setPairImageB(e.target.value)}
                        className="form-select text-xs py-1.5 w-full"
                      >
                        {images.map((img) => (
                          <option key={img.id} value={img.id}>
                            {img.filename}
                          </option>
                        ))}
                      </select>
                    </div>

                    <button
                      onClick={handleMatchSelectedPair}
                      disabled={pairMatchingLoading || !pairImageA || !pairImageB}
                      className="btn-primary text-xs h-[34px] justify-center"
                    >
                      <Play size={13} className={pairMatchingLoading ? 'animate-spin' : ''} />
                      <span>{pairMatchingLoading ? 'Computing Matches...' : 'Match Selected Pair'}</span>
                    </button>
                  </div>

                  {/* Active pair result card */}
                  {activePairResult && (
                    <div className="mt-4 p-4 bg-slate-900 rounded-lg border border-slate-800 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-xs text-slate-200">
                            {activePairResult.image_a_filename} ⟷ {activePairResult.image_b_filename}
                          </span>
                          <StatusBadge status={activePairResult.status} />
                        </div>
                        <span className="text-xs font-mono text-amber-400 font-semibold">
                          {activePairResult.estimated_overlap}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs bg-slate-950/60 p-3 rounded border border-slate-800/80">
                        <div>
                          <span className="text-slate-400 block text-[11px]">Keypoints (A / B)</span>
                          <span className="font-mono text-slate-200">
                            {activePairResult.keypoints_a} / {activePairResult.keypoints_b}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[11px]">Candidate Matches</span>
                          <span className="font-mono text-slate-200">{activePairResult.candidate_matches}</span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[11px]">Good Matches (Lowe)</span>
                          <span className="font-mono text-emerald-400 font-bold">
                            {activePairResult.good_matches}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-400 block text-[11px]">Match Ratio</span>
                          <span className="font-mono text-sky-400 font-bold">
                            {(activePairResult.match_ratio * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>

                      {activePairResult.recommendation && (
                        <p className="text-xs text-slate-300 italic">
                          💡 {activePairResult.recommendation}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {/* Analyzed Pairs Table */}
              <div className="card">
                <div className="card-header">
                  <div className="flex items-center gap-3">
                    <h3 className="card-title">Analyzed Survey Pairs</h3>
                    <div className="flex items-center gap-1">
                      {['ALL', 'GOOD', 'WARNING', 'POOR'].map((status) => (
                        <button
                          key={status}
                          onClick={() => setPairsFilter(status)}
                          className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-colors ${
                            pairsFilter === status
                              ? 'bg-amber-500 text-black'
                              : 'text-slate-400 hover:text-slate-200 bg-slate-800'
                          }`}
                        >
                          {status}
                        </button>
                      ))}
                    </div>
                  </div>
                  <span className="text-xs text-slate-400">{filteredPairs.length} pair(s)</span>
                </div>

                <div className="card-body p-0">
                  {filteredPairs.length === 0 ? (
                    <div className="empty-box">
                      <p className="text-slate-400 text-xs">
                        No pairs found matching filter "{pairsFilter}". Run collection analysis or test a pair above.
                      </p>
                    </div>
                  ) : (
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Image A</th>
                          <th>Image B</th>
                          <th>Keypoints (A/B)</th>
                          <th>Good Matches</th>
                          <th>Match Ratio</th>
                          <th>Correspondence Indicator</th>
                          <th>Status</th>
                          <th>Actionable Guidance</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredPairs.map((p, idx) => (
                          <tr key={p.id || idx}>
                            <td className="font-mono text-xs text-slate-200 font-medium">
                              {p.image_a_filename || p.image_a_id.slice(0, 8)}
                            </td>
                            <td className="font-mono text-xs text-slate-200 font-medium">
                              {p.image_b_filename || p.image_b_id.slice(0, 8)}
                            </td>
                            <td className="text-xs font-mono text-slate-400">
                              {p.keypoints_a} / {p.keypoints_b}
                            </td>
                            <td className="text-xs font-mono font-bold text-emerald-400">
                              {p.good_matches}
                            </td>
                            <td className="text-xs font-mono text-sky-400">
                              {(p.match_ratio * 100).toFixed(1)}%
                            </td>
                            <td className="text-xs text-slate-300">
                              {p.estimated_overlap}
                            </td>
                            <td>
                              <StatusBadge status={p.status} />
                            </td>
                            <td className="text-xs text-slate-400 max-w-xs truncate" title={p.recommendation}>
                              {p.recommendation || '--'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* ==================================================== */}
          {/* SUB-TAB 3: INDIVIDUAL IMAGE OPTICAL QUALITY (PHASE 1) */}
          {/* ==================================================== */}
          {currentSubTab === 'individual' && (
            <div className="space-y-6">
              {/* Summary Cards */}
              {summary && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="metric-card">
                    <div className="metric-icon-wrap bg-emerald-950/40 text-emerald-400">
                      <CheckCircle2 size={20} />
                    </div>
                    <div className="metric-content">
                      <p className="metric-label">Pass Rate</p>
                      <p className="metric-value font-mono">{summary.pass_percentage}%</p>
                    </div>
                  </div>

                  <div className="metric-card">
                    <div className="metric-icon-wrap bg-rose-950/40 text-rose-400">
                      <XCircle size={20} />
                    </div>
                    <div className="metric-content">
                      <p className="metric-label">Blur Failures</p>
                      <p className="metric-value font-mono">{summary.blur_failures}</p>
                    </div>
                  </div>

                  <div className="metric-card">
                    <div className="metric-icon-wrap bg-amber-950/40 text-amber-400">
                      <AlertTriangle size={20} />
                    </div>
                    <div className="metric-content">
                      <p className="metric-label">Exposure Warnings</p>
                      <p className="metric-value font-mono">{summary.brightness_failures}</p>
                    </div>
                  </div>

                  <div className="metric-card">
                    <div className="metric-icon-wrap bg-sky-950/40 text-sky-400">
                      <Sparkles size={20} />
                    </div>
                    <div className="metric-content">
                      <p className="metric-label">Optical Quality Score</p>
                      <p className="metric-value font-mono text-emerald-400">
                        {summary.average_quality_score}/100
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Detailed Image Table */}
              <div className="card">
                <div className="card-header">
                  <h3 className="card-title">Per-Image Quality Breakdown</h3>
                  <span className="text-xs text-slate-400">Threshold: Blur Var ≥ 100 | Lum ∈ [40, 220]</span>
                </div>
                <div className="card-body p-0">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Filename</th>
                        <th>Resolution</th>
                        <th>Laplacian Blur</th>
                        <th>Luminance</th>
                        <th>ORB Features</th>
                        <th>Composite Score</th>
                        <th>Status</th>
                        <th>Actionable Recommendation</th>
                      </tr>
                    </thead>
                    <tbody>
                      {images.map((img) => (
                        <tr key={img.id}>
                          <td className="font-medium text-slate-200">{img.filename}</td>
                          <td className="text-xs text-slate-300 font-mono">
                            {img.width && img.height ? `${img.width}x${img.height}` : '--'}
                          </td>
                          <td>
                            <span className={`text-xs font-mono font-semibold ${
                              img.blur_status === 'pass' ? 'text-emerald-400' : 'text-rose-400'
                            }`}>
                              {img.blur_score?.toFixed(1) ?? '--'} ({img.blur_status ?? '--'})
                            </span>
                          </td>
                          <td>
                            <span className={`text-xs font-mono font-semibold ${
                              img.brightness_status === 'pass' ? 'text-emerald-400' : 'text-amber-400'
                            }`}>
                              {img.brightness_score?.toFixed(1) ?? '--'} ({img.brightness_status ?? '--'})
                            </span>
                          </td>
                          <td className="text-xs font-mono text-sky-400">
                            {img.feature_count ?? '--'}
                          </td>
                          <td className="font-mono font-bold text-slate-100">
                            {img.quality_score?.toFixed(1) ?? '--'}%
                          </td>
                          <td>
                            <StatusBadge status={img.quality_status} />
                          </td>
                          <td className="text-xs text-slate-400 max-w-xs truncate" title={img.quality_details?.overall_recommendation}>
                            {img.quality_details?.overall_recommendation || 'Evaluated'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Research Scientific Disclaimer Note */}
          <div className="p-3.5 bg-slate-900/60 rounded-lg border border-slate-800 flex items-start gap-2.5 text-xs text-slate-400">
            <ShieldAlert size={16} className="text-amber-400 mt-0.5 shrink-0" />
            <p>
              <strong className="text-slate-200">Scientific Preprocessing Note:</strong> This module provides an engineering-level image-quality and feature-correspondence assessment intended to support photogrammetric preprocessing. Its thresholds are configurable heuristics and should not be interpreted as universally validated photogrammetry quality criteria or guarantees of numerical convergence in dense multi-view stereo reconstruction.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
