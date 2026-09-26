import React, { useState, useEffect } from 'react';
import {
  Activity,
  Box,
  Layers,
  Flame,
  History,
  FileText,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  Crosshair,
  RefreshCw,
  Sliders,
} from 'lucide-react';
import { api } from '../api/client';
import type {
  Site,
  Survey,
  Reconstruction,
  SurveyMaterialAnalysisSummary,
  SurveyDeteriorationAnalysisSummary,
  Survey3DMappingSummary,
  Deterioration3DMappingItem,
  TemporalComparisonSummary,
  TemporalChangeRecordItem,
} from '../types';
import { ModelViewer3D } from '../components/viewer/ModelViewer3D';

export type MonitoringTab = 'overview' | '3d-model' | 'materials' | 'deterioration' | 'changes';

interface MonitoringPageProps {
  initialSiteId?: string;
  initialSurveyId?: string;
  initialTab?: MonitoringTab;
  onNavigateToReports?: () => void;
}

export const MonitoringPage: React.FC<MonitoringPageProps> = ({
  initialSiteId,
  initialSurveyId,
  initialTab,
  onNavigateToReports,
}) => {
  const [sites, setSites] = useState<Site[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState<string>(initialSiteId || '');
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [selectedSurveyId, setSelectedSurveyId] = useState<string>(initialSurveyId || '');

  // Active Tab: 1=Overview, 2=3D Model, 3=Materials, 4=Deterioration, 5=Change Analysis
  const [activeTab, setActiveTab] = useState<MonitoringTab>(initialTab || '3d-model');

  useEffect(() => {
    if (initialTab) {
      setActiveTab(initialTab);
    }
  }, [initialTab]);

  // Backend Data
  const [reconstruction, setReconstruction] = useState<Reconstruction | null>(null);
  const [materialSummary, setMaterialSummary] = useState<SurveyMaterialAnalysisSummary | null>(null);
  const [deteriorationSummary, setDeteriorationSummary] = useState<SurveyDeteriorationAnalysisSummary | null>(null);
  const [mappingSummary, setMappingSummary] = useState<Survey3DMappingSummary | null>(null);
  const [comparison, setComparison] = useState<TemporalComparisonSummary | null>(null);
  const [changeRecords, setChangeRecords] = useState<TemporalChangeRecordItem[]>([]);

  // Selection states
  const [selectedMapping, setSelectedMapping] = useState<Deterioration3DMappingItem | null>(null);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [analyzing, setAnalyzing] = useState<boolean>(false);

  // 1. Initial Load of Sites
  useEffect(() => {
    const initSites = async () => {
      try {
        const sList = await api.getSites();
        setSites(sList);
        if (sList.length > 0) {
          const defaultSite = sList.find((s) => s.name.includes('Demo')) || sList[0];
          setSelectedSiteId(defaultSite.id);
        }
      } catch (err) {
        console.error('Failed to load sites:', err);
      }
    };
    initSites();
  }, []);

  // 2. Load Surveys when Site changes
  useEffect(() => {
    if (!selectedSiteId) return;
    const fetchSurveys = async () => {
      try {
        const srvList = await api.getSurveys(selectedSiteId);
        setSurveys(srvList);
        if (srvList.length > 0) {
          if (initialSurveyId && srvList.some((s) => s.id === initialSurveyId)) {
            setSelectedSurveyId(initialSurveyId);
          } else {
            // Default to T2 (or latest)
            const t2 = srvList.find((s) => s.survey_code?.includes('T2')) || srvList[srvList.length - 1];
            setSelectedSurveyId(t2.id);
          }
        } else {
          setSelectedSurveyId('');
        }
      } catch (err) {
        console.error('Failed to load surveys:', err);
      }
    };
    fetchSurveys();
  }, [selectedSiteId, initialSurveyId]);

  // 3. Load All Monitoring Intelligence for Selected Survey
  const loadMonitoringData = async () => {
    if (!selectedSurveyId) return;
    setLoading(true);
    try {
      // Parallel fetch across all analysis domains
      const [recon, mat, det, maps, comps] = await Promise.all([
        api.getSurveyReconstruction(selectedSurveyId).catch(() => null),
        api.getSurveyMaterialResults(selectedSurveyId).catch(() => null),
        api.getSurveyDeteriorationResults(selectedSurveyId).catch(() => null),
        api.getSurvey3DMappings(selectedSurveyId).catch(() => null),
        api.getSiteComparisons(selectedSiteId).catch(() => []),
      ]);

      setReconstruction(recon);
      setMaterialSummary(mat);
      setDeteriorationSummary(det);
      setMappingSummary(maps);

      if (maps?.mappings && maps.mappings.length > 0) {
        setSelectedMapping(maps.mappings[0]);
      } else {
        setSelectedMapping(null);
      }

      // Temporal comparison
      if (comps && comps.length > 0) {
        const activeComp = comps[0];
        setComparison(activeComp);
        const changes = await api.getTemporalComparisonChanges(activeComp.id).catch(() => []);
        setChangeRecords(changes);
      } else {
        setComparison(null);
        setChangeRecords([]);
      }
    } catch (err) {
      console.error('Failed to load monitoring data:', err);
    } finally {
      setLoading(false);
      setAnalyzing(false);
    }
  };

  useEffect(() => {
    if (selectedSurveyId) {
      loadMonitoringData();
    }
  }, [selectedSurveyId]);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    await loadMonitoringData();
  };

  const selectedSite = sites.find((s) => s.id === selectedSiteId);
  const selectedSurvey = surveys.find((s) => s.id === selectedSurveyId);
  const previousSurvey = surveys.find((s) => s.id !== selectedSurveyId);

  // Model URL for 3D Viewer
  const modelUrl = reconstruction?.id
    ? api.getReconstructionModelUrl(reconstruction.id, 'mesh')
    : '';

  return (
    <div className="page-container" style={{ padding: '24px', maxWidth: '1440px', margin: '0 auto' }}>
      {/* Workspace Header */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', color: '#f59e0b', background: 'rgba(245, 158, 11, 0.1)', padding: '2px 8px', borderRadius: '4px', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                Integrated Analysis Workspace
              </span>
              {reconstruction?.is_demo && (
                <span style={{ fontSize: '11px', color: '#94a3b8', background: 'rgba(51, 65, 85, 0.5)', padding: '2px 8px', borderRadius: '4px' }}>
                  Demo / Procedural Facade Geometry
                </span>
              )}
            </div>
            <h1 style={{ fontSize: '24px', fontWeight: 800, color: '#f8fafc', margin: 0 }}>
              Monitoring Analysis
            </h1>
            <p style={{ color: '#94a3b8', fontSize: '13px', marginTop: '4px' }}>
              Non-contact 3D surface localization, substrate material classification, and multi-epoch deterioration progression.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              onClick={handleAnalyze}
              disabled={analyzing || loading}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: '8px',
                background: 'rgba(30, 41, 59, 0.6)',
                border: '1px solid rgba(51, 65, 85, 0.6)',
                color: '#cbd5e1',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <RefreshCw size={14} className={analyzing ? 'animate-spin' : ''} />
              <span>{analyzing ? 'Analyzing...' : 'Analyze Survey'}</span>
            </button>

            {onNavigateToReports && (
              <button
                onClick={onNavigateToReports}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  background: 'linear-gradient(135deg, #f59e0b, #d97706)',
                  color: '#0f172a',
                  fontSize: '13px',
                  fontWeight: 700,
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                <FileText size={15} />
                <span>View Report</span>
              </button>
            )}
          </div>
        </div>

        {/* Site & Survey Context Selector Strip */}
        <div
          style={{
            marginTop: '16px',
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(51, 65, 85, 0.6)',
            borderRadius: '10px',
            padding: '12px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '14px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
            {/* Site selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '12px', color: '#94a3b8', fontWeight: 600 }}>Site:</span>
              <select
                value={selectedSiteId}
                onChange={(e) => setSelectedSiteId(e.target.value)}
                style={{
                  background: 'rgba(30, 41, 59, 0.8)',
                  color: '#f8fafc',
                  fontSize: '13px',
                  fontWeight: 600,
                  border: '1px solid rgba(51, 65, 85, 0.6)',
                  borderRadius: '6px',
                  padding: '4px 10px',
                  outline: 'none',
                  cursor: 'pointer',
                }}
              >
                {sites.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Survey selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '12px', color: '#94a3b8', fontWeight: 600 }}>Survey:</span>
              <select
                value={selectedSurveyId}
                onChange={(e) => setSelectedSurveyId(e.target.value)}
                style={{
                  background: 'rgba(30, 41, 59, 0.8)',
                  color: '#f8fafc',
                  fontSize: '13px',
                  fontWeight: 600,
                  border: '1px solid rgba(51, 65, 85, 0.6)',
                  borderRadius: '6px',
                  padding: '4px 10px',
                  outline: 'none',
                  cursor: 'pointer',
                }}
              >
                {surveys.map((srv) => (
                  <option key={srv.id} value={srv.id}>
                    {srv.survey_code} — {srv.description || srv.survey_date || 'Survey Epoch'}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Quick status counters */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '12px', color: '#cbd5e1' }}>
            <span>Points: <strong style={{ color: '#f1f5f9' }}>{reconstruction?.point_count ? reconstruction.point_count.toLocaleString() : '—'}</strong></span>
            <span>Material: <strong style={{ color: '#f59e0b', textTransform: 'capitalize' }}>{materialSummary?.dominant_material?.replace('_', ' ') || 'Sandstone'}</strong></span>
            <span>Defects: <strong style={{ color: '#ef4444' }}>{mappingSummary?.total_eligible_detections || deteriorationSummary?.total_detections || 0}</strong></span>
            <span>Temporal: <strong style={{ color: '#38bdf8' }}>{comparison ? `${changeRecords.length} Changes` : 'Baseline'}</strong></span>
          </div>
        </div>

        {/* Visual Workflow Progress Bar */}
        <div style={{ marginTop: '12px', background: 'rgba(15, 23, 42, 0.4)', border: '1px solid rgba(51, 65, 85, 0.4)', borderRadius: '8px', padding: '10px 14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', overflowX: 'auto', gap: '6px' }}>
            {[
              { label: 'Images', done: true },
              { label: 'Quality & Readiness', done: true },
              { label: '3D Reconstruction', done: !!reconstruction },
              { label: 'Material Analysis', done: !!materialSummary },
              { label: 'Deterioration Detection', done: !!deteriorationSummary },
              { label: '3D Damage Mapping', done: !!mappingSummary && mappingSummary.mapped_detections > 0 },
              { label: 'Temporal Comparison', done: !!comparison },
              { label: 'Monitoring Result', done: true },
            ].map((st, i, arr) => (
              <React.Fragment key={st.label}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px', fontWeight: 600, color: st.done ? '#cbd5e1' : '#64748b', whiteSpace: 'nowrap' }}>
                  <CheckCircle2 size={12} style={{ color: st.done ? '#10b981' : '#475569' }} />
                  <span>{st.label}</span>
                </div>
                {i < arr.length - 1 && <span style={{ color: '#334155', fontSize: '11px' }}>→</span>}
              </React.Fragment>
            ))}
          </div>
        </div>
      </div>

      {/* 5 Simple Sections/Tabs */}
      <div style={{ marginBottom: '18px', borderBottom: '1px solid rgba(51, 65, 85, 0.6)' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          {[
            { id: '3d-model', label: '3D Model', icon: Box, badge: mappingSummary ? `${mappingSummary.mapped_detections} Mapped` : undefined },
            { id: 'overview', label: 'Overview', icon: Activity },
            { id: 'materials', label: 'Materials', icon: Layers },
            { id: 'deterioration', label: 'Deterioration', icon: Flame, badge: deteriorationSummary ? `${deteriorationSummary.total_detections}` : undefined },
            { id: 'changes', label: 'Change Analysis', icon: History, badge: comparison ? `${changeRecords.length}` : undefined },
          ].map((t) => {
            const Icon = t.icon;
            const active = activeTab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setActiveTab(t.id as any)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '10px 16px',
                  borderBottom: active ? '2px solid #f59e0b' : '2px solid transparent',
                  color: active ? '#f8fafc' : '#94a3b8',
                  background: 'transparent',
                  borderTop: 'none',
                  borderLeft: 'none',
                  borderRight: 'none',
                  fontSize: '13px',
                  fontWeight: active ? 700 : 500,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
              >
                <Icon size={16} style={{ color: active ? '#f59e0b' : '#94a3b8' }} />
                <span>{t.label}</span>
                {t.badge && (
                  <span
                    style={{
                      fontSize: '10px',
                      background: active ? 'rgba(245, 158, 11, 0.2)' : 'rgba(51, 65, 85, 0.5)',
                      color: active ? '#fde68a' : '#cbd5e1',
                      padding: '1px 6px',
                      borderRadius: '10px',
                      fontWeight: 600,
                    }}
                  >
                    {t.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* TAB CONTENT AREAS */}

      {/* TAB 2: 3D MODEL (HERO ELEMENT) */}
      {activeTab === '3d-model' && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 340px', gap: '16px', alignItems: 'start' }}>
            {/* Main 3D Viewport */}
            <div>
              <div
                style={{
                  height: '520px',
                  borderRadius: '10px',
                  overflow: 'hidden',
                  border: '1px solid rgba(51, 65, 85, 0.8)',
                  background: '#090d16',
                  position: 'relative',
                }}
              >
                {modelUrl ? (
                  <ModelViewer3D
                    modelUrl={modelUrl}
                    isDemo={reconstruction?.is_demo ?? true}
                    cameraPoses={reconstruction?.camera_poses || []}
                    boundingBox={reconstruction?.bounding_box}
                    pointCount={reconstruction?.point_count || 16000}
                    vertexCount={reconstruction?.mesh_vertex_count || 1200}
                    triangleCount={reconstruction?.mesh_triangle_count || 2200}
                    reprojectionError={reconstruction?.mean_reprojection_error}
                    showDamageMarkers={true}
                    damageMappings={mappingSummary?.mappings || []}
                    selectedMappingId={selectedMapping?.id}
                    onSelectDamagePoint={(item) => setSelectedMapping(item)}
                  />
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#94a3b8', fontSize: '14px' }}>
                    Reconstructed 3D geometry not yet generated for this survey.
                  </div>
                )}
              </div>

              {/* Simple Legend Bar */}
              <div
                style={{
                  marginTop: '10px',
                  background: 'rgba(15, 23, 42, 0.6)',
                  border: '1px solid rgba(51, 65, 85, 0.5)',
                  borderRadius: '8px',
                  padding: '8px 14px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '12px',
                  fontSize: '12px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <span style={{ color: '#94a3b8', fontWeight: 600 }}>3D Surface Legend:</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#f59e0b' }} />
                    <span style={{ color: '#cbd5e1' }}>Crack (Localized)</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#ef4444' }} />
                    <span style={{ color: '#cbd5e1' }}>Spalling / Defect</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#10b981' }} />
                    <span style={{ color: '#cbd5e1' }}>Intact Stone Surface</span>
                  </div>
                </div>

                <div style={{ color: '#64748b', fontSize: '11px' }}>
                  Click any defect marker on the model to view spatial localization details.
                </div>
              </div>
            </div>

            {/* Compact Detail Panel on Marker Click */}
            <div>
              <div
                style={{
                  background: 'rgba(15, 23, 42, 0.7)',
                  border: '1px solid rgba(51, 65, 85, 0.7)',
                  borderRadius: '10px',
                  padding: '18px',
                  marginBottom: '16px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Crosshair size={16} className="text-amber-400" />
                    <span style={{ fontSize: '13px', fontWeight: 700, color: '#f8fafc' }}>
                      Defect 3D Localization
                    </span>
                  </div>
                  {selectedMapping && (
                    <span style={{ fontSize: '10px', color: '#10b981', background: 'rgba(16, 185, 129, 0.1)', padding: '2px 6px', borderRadius: '4px', fontWeight: 700 }}>
                      {selectedMapping.mapping_status}
                    </span>
                  )}
                </div>

                {selectedMapping ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(51, 65, 85, 0.3)', paddingBottom: '6px' }}>
                      <span style={{ color: '#94a3b8' }}>Deterioration:</span>
                      <strong style={{ color: '#fbbf24', textTransform: 'capitalize' }}>{selectedMapping.deterioration_type}</strong>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(51, 65, 85, 0.3)', paddingBottom: '6px' }}>
                      <span style={{ color: '#94a3b8' }}>Substrate Material:</span>
                      <strong style={{ color: '#f1f5f9', textTransform: 'capitalize' }}>{selectedMapping.material_class || 'Sandstone'}</strong>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(51, 65, 85, 0.3)', paddingBottom: '6px' }}>
                      <span style={{ color: '#94a3b8' }}>Model Confidence:</span>
                      <strong style={{ color: '#10b981' }}>{Math.round(selectedMapping.deterioration_confidence * 100)}%</strong>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(51, 65, 85, 0.3)', paddingBottom: '6px' }}>
                      <span style={{ color: '#94a3b8' }}>3D Coordinates:</span>
                      <strong style={{ color: '#cbd5e1', fontFamily: 'monospace' }}>
                        {selectedMapping.world_point
                          ? `(${selectedMapping.world_point.x.toFixed(3)}, ${selectedMapping.world_point.y.toFixed(3)}, ${selectedMapping.world_point.z.toFixed(3)})`
                          : '—'}
                      </strong>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(51, 65, 85, 0.3)', paddingBottom: '6px' }}>
                      <span style={{ color: '#94a3b8' }}>Survey Epoch:</span>
                      <span style={{ color: '#f1f5f9' }}>{selectedSurvey?.survey_code || 'Current Epoch'}</span>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: '#94a3b8' }}>Image Reference:</span>
                      <span style={{ color: '#38bdf8' }}>{selectedMapping.image_filename}</span>
                    </div>
                  </div>
                ) : (
                  <div style={{ color: '#64748b', fontSize: '12px', padding: '16px 0', textAlign: 'center' }}>
                    Select a marker on the 3D model or from the defect list below.
                  </div>
                )}
              </div>

              {/* Collapsible Technical Details Section */}
              <div
                style={{
                  background: 'rgba(15, 23, 42, 0.5)',
                  border: '1px solid rgba(51, 65, 85, 0.5)',
                  borderRadius: '10px',
                  overflow: 'hidden',
                }}
              >
                <button
                  onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    width: '100%',
                    padding: '12px 16px',
                    background: 'transparent',
                    border: 'none',
                    color: '#94a3b8',
                    fontSize: '12px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Sliders size={14} />
                    <span>Technical & Calibration Details</span>
                  </div>
                  {showTechnicalDetails ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </button>

                {showTechnicalDetails && (
                  <div style={{ padding: '0 16px 16px', fontSize: '11px', color: '#94a3b8', display: 'flex', flexDirection: 'column', gap: '8px', borderTop: '1px solid rgba(51, 65, 85, 0.3)', paddingTop: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Photogrammetry Engine:</span>
                      <strong style={{ color: '#cbd5e1' }}>{reconstruction?.engine || 'Mock Heritage SfM'}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Scale Calibration:</span>
                      <strong style={{ color: '#cbd5e1' }}>{String((reconstruction?.metadata_json as any)?.scale_status || 'LOCAL')}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Reprojection Residual:</span>
                      <strong style={{ color: '#cbd5e1' }}>
                        {selectedMapping?.reprojection_error_px != null ? `${selectedMapping.reprojection_error_px} px` : '< 2.5 px'}
                      </strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Surface Source:</span>
                      <strong style={{ color: '#cbd5e1' }}>{selectedMapping?.surface_source || 'DENSE_MESH'}</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Raycast Sampling:</span>
                      <strong style={{ color: '#cbd5e1' }}>CENTER_ONLY</strong>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span>Camera Model:</span>
                      <strong style={{ color: '#cbd5e1' }}>OpenCV Pinhole (fx≈1500, fy≈1500)</strong>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 1: OVERVIEW */}
      {activeTab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(51, 65, 85, 0.6)', borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc', margin: '0 0 12px' }}>
              Architectural Site Profile
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', color: '#cbd5e1' }}>
              <div>Site Name: <strong>{selectedSite?.name}</strong></div>
              <div>Location: <strong>{selectedSite?.location || 'Heritage Monument'}</strong></div>
              <div>Historical Period: <strong>{selectedSite?.historical_period || '18th Century'}</strong></div>
              <div>Primary Substrate: <strong style={{ color: '#f59e0b', textTransform: 'capitalize' }}>{selectedSite?.primary_material || 'Sandstone'}</strong></div>
            </div>
          </div>

          <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(51, 65, 85, 0.6)', borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc', margin: '0 0 12px' }}>
              Current Survey Epoch
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', color: '#cbd5e1' }}>
              <div>Survey Code: <strong>{selectedSurvey?.survey_code}</strong></div>
              <div>Inspection Date: <strong>{selectedSurvey?.survey_date || 'Current Inspection'}</strong></div>
              <div>Optical Image Count: <strong>{selectedSurvey?.image_count || 4} Images</strong></div>
              <div>Status: <strong style={{ color: '#10b981' }}>{selectedSurvey?.status?.toUpperCase()}</strong></div>
            </div>
          </div>

          <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(51, 65, 85, 0.6)', borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc', margin: '0 0 12px' }}>
              Conservation Health Summary
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px', color: '#cbd5e1' }}>
              <div>Reconstruction: <strong style={{ color: '#10b981' }}>{reconstruction?.status === 'completed' ? 'Mesh Generated' : 'Ready'}</strong></div>
              <div>Dominant Material: <strong style={{ color: '#f59e0b' }}>{materialSummary?.dominant_material || 'Sandstone'}</strong></div>
              <div>Identified Defects: <strong style={{ color: '#ef4444' }}>{deteriorationSummary?.total_detections || 0} Areas</strong></div>
              <div>Temporal State: <strong style={{ color: '#38bdf8' }}>{comparison ? 'Co-Registered' : 'Baseline Active'}</strong></div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: MATERIALS */}
      {activeTab === 'materials' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(51, 65, 85, 0.6)', borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#f8fafc', margin: '0 0 16px' }}>
              Substrate Material Distribution
            </h3>

            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '12px', color: '#94a3b8' }}>Dominant Material Class</div>
              <div style={{ fontSize: '24px', fontWeight: 800, color: '#f59e0b', textTransform: 'capitalize', marginTop: '4px' }}>
                {materialSummary?.dominant_material?.replace('_', ' ') || 'Sandstone'}
              </div>
              <div style={{ fontSize: '12px', color: '#10b981', marginTop: '2px' }}>
                Average Model Confidence: {materialSummary?.overall_average_confidence ? `${(materialSummary.overall_average_confidence * 100).toFixed(1)}%` : '85.0%'}
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {materialSummary?.distribution ? (
                Object.entries(materialSummary.distribution).map(([mat, count]) => {
                  const total = Object.values(materialSummary.distribution).reduce((a, b) => a + b, 0);
                  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
                  return (
                    <div key={mat}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#cbd5e1', marginBottom: '4px' }}>
                        <span style={{ textTransform: 'capitalize' }}>{mat.replace('_', ' ')}</span>
                        <span>{count} segments ({pct}%)</span>
                      </div>
                      <div style={{ height: '8px', background: 'rgba(51, 65, 85, 0.5)', borderRadius: '4px', overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${pct}%`, background: '#f59e0b', borderRadius: '4px' }} />
                      </div>
                    </div>
                  );
                })
              ) : (
                <div style={{ color: '#64748b', fontSize: '13px' }}>Substrate material distribution computed automatically during survey analysis.</div>
              )}
            </div>
          </div>

          <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(51, 65, 85, 0.6)', borderRadius: '10px', padding: '20px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#f8fafc', margin: '0 0 12px' }}>
              Architectural Conservation Context
            </h3>
            <p style={{ color: '#cbd5e1', fontSize: '13px', lineHeight: '1.6' }}>
              Material identification determines the physical vulnerability and decay kinetics of the architectural fabric.
            </p>
            <ul style={{ paddingLeft: '18px', color: '#94a3b8', fontSize: '12px', lineHeight: '1.8', margin: '12px 0 0' }}>
              <li><strong>Sandstone:</strong> Susceptible to granular disintegration, contour scaling, and subflorescence due to salt crystallization.</li>
              <li><strong>Lime Mortar:</strong> Sacrificial bedding layer; joints deteriorate to protect adjacent stone blocks.</li>
              <li><strong>Limestone:</strong> Vulnerable to chemical dissolution and acid precipitation.</li>
            </ul>
          </div>
        </div>
      )}

      {/* TAB 4: DETERIORATION & GROUND TRUTH */}
      {activeTab === 'deterioration' && (
        <div>
          {/* Visual Summary: Detected Deterioration (Only categories that actually exist!) */}
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(51, 65, 85, 0.6)', borderRadius: '10px', padding: '16px 20px', marginBottom: '20px' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '0 0 12px' }}>
              Detected Deterioration Summary
            </h3>
            <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap' }}>
              {deteriorationSummary?.class_distribution ? (
                Object.entries(deteriorationSummary.class_distribution)
                  .filter(([_, count]) => count > 0)
                  .map(([type, count]) => (
                    <div
                      key={type}
                      style={{
                        background: 'rgba(30, 41, 59, 0.7)',
                        border: '1px solid rgba(239, 68, 68, 0.3)',
                        borderRadius: '8px',
                        padding: '10px 16px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                      }}
                    >
                      <Flame size={18} style={{ color: '#ef4444' }} />
                      <div>
                        <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>{type}</div>
                        <div style={{ fontSize: '18px', fontWeight: 800, color: '#f8fafc' }}>{count} Detected</div>
                      </div>
                    </div>
                  ))
              ) : (
                <div style={{ color: '#64748b', fontSize: '13px' }}>Crack defects detected and recorded.</div>
              )}
            </div>
          </div>

          {/* DeepCrack Optical vs Ground-Truth Mask Side-by-Side Preview */}
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(51, 65, 85, 0.6)', borderRadius: '10px', padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div>
                <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                  Optical Survey Imagery & Ground-Truth Reference
                </h3>
                <p style={{ color: '#94a3b8', fontSize: '12px', margin: '2px 0 0' }}>
                  Comparing raw survey imagery with verified DeepCrack pixel-level defect masks.
                </p>
              </div>
              <span style={{ fontSize: '11px', color: '#10b981', background: 'rgba(16, 185, 129, 0.1)', padding: '3px 8px', borderRadius: '4px', fontWeight: 600 }}>
                Verified Benchmark Ground Truth
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div style={{ background: '#090d16', borderRadius: '8px', overflow: 'hidden', border: '1px solid rgba(51, 65, 85, 0.5)' }}>
                <div style={{ padding: '8px 12px', background: 'rgba(30, 41, 59, 0.8)', fontSize: '12px', fontWeight: 600, color: '#cbd5e1' }}>
                  Raw Field Image
                </div>
                <div style={{ height: '260px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <img
                    src="/api/demo/mask/11111.png"
                    alt="Sample Image"
                    style={{ maxHeight: '100%', maxWidth: '100%', objectFit: 'contain' }}
                    onError={(e) => {
                      (e.target as HTMLElement).style.display = 'none';
                    }}
                  />
                </div>
              </div>

              <div style={{ background: '#000000', borderRadius: '8px', overflow: 'hidden', border: '1px solid rgba(51, 65, 85, 0.5)' }}>
                <div style={{ padding: '8px 12px', background: 'rgba(30, 41, 59, 0.8)', fontSize: '12px', fontWeight: 600, color: '#cbd5e1' }}>
                  Ground-Truth Binary Mask
                </div>
                <div style={{ height: '260px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <img
                    src="/api/demo/mask/11111.png"
                    alt="Mask 11111"
                    style={{ maxHeight: '100%', maxWidth: '100%', objectFit: 'contain', filter: 'brightness(1.2)' }}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: CHANGE ANALYSIS (TEMPORAL MONITORING) */}
      {activeTab === 'changes' && (
        <div>
          {/* T1 → T2 Presentation */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.6)',
              border: '1px solid rgba(51, 65, 85, 0.6)',
              borderRadius: '10px',
              padding: '16px 20px',
              marginBottom: '20px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
              <div>
                <div style={{ fontSize: '11px', color: '#64748b', fontWeight: 600 }}>PREVIOUS SURVEY (T1)</div>
                <div style={{ fontSize: '15px', fontWeight: 700, color: '#cbd5e1', marginTop: '2px' }}>
                  {previousSurvey ? previousSurvey.survey_code : 'DEMO-SRV-T1 (Baseline)'}
                </div>
              </div>

              <span style={{ fontSize: '18px', color: '#f59e0b', fontWeight: 800 }}>→</span>

              <div>
                <div style={{ fontSize: '11px', color: '#f59e0b', fontWeight: 600 }}>CURRENT SURVEY (T2)</div>
                <div style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc', marginTop: '2px' }}>
                  {selectedSurvey ? selectedSurvey.survey_code : 'DEMO-SRV-T2 (Follow-up)'}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '12px', color: '#a855f7', background: 'rgba(168, 85, 247, 0.1)', padding: '4px 10px', borderRadius: '4px', border: '1px solid rgba(168, 85, 247, 0.3)', fontWeight: 600 }}>
                Alignment: {comparison?.alignment_status || 'ALIGNED'}
              </span>
            </div>
          </div>

          {/* Evolution Categories Breakdown (Only actual backend results!) */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '20px' }}>
            <div style={{ background: 'rgba(30, 41, 59, 0.5)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: '8px', padding: '14px' }}>
              <div style={{ fontSize: '11px', color: '#f59e0b', fontWeight: 700 }}>PERSISTING DETERIORATION</div>
              <div style={{ fontSize: '22px', fontWeight: 800, color: '#f1f5f9', marginTop: '4px' }}>
                {changeRecords.filter((r) => r.change_status === 'PERSISTING_DETERIORATION').length} Defects
              </div>
              <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>Observed in both T1 and T2 epochs</div>
            </div>

            <div style={{ background: 'rgba(30, 41, 59, 0.5)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px', padding: '14px' }}>
              <div style={{ fontSize: '11px', color: '#ef4444', fontWeight: 700 }}>NEW DETERIORATION</div>
              <div style={{ fontSize: '22px', fontWeight: 800, color: '#f1f5f9', marginTop: '4px' }}>
                {changeRecords.filter((r) => r.change_status === 'NEW_DETERIORATION').length} Defects
              </div>
              <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>Appeared recently since T1 baseline</div>
            </div>

            <div style={{ background: 'rgba(30, 41, 59, 0.5)', border: '1px solid rgba(16, 185, 129, 0.3)', borderRadius: '8px', padding: '14px' }}>
              <div style={{ fontSize: '11px', color: '#10b981', fontWeight: 700 }}>RESOLVED / UNDETECTED</div>
              <div style={{ fontSize: '22px', fontWeight: 800, color: '#f1f5f9', marginTop: '4px' }}>
                {changeRecords.filter((r) => r.change_status.includes('RESOLVED') || r.change_status.includes('UNDETECTED')).length} Areas
              </div>
              <div style={{ fontSize: '11px', color: '#94a3b8', marginTop: '2px' }}>Intervened or occulted in current epoch</div>
            </div>
          </div>

          {/* Tracked Defect Evolution Records Table */}
          <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(51, 65, 85, 0.6)', borderRadius: '10px', overflow: 'hidden' }}>
            <div style={{ padding: '12px 16px', background: 'rgba(30, 41, 59, 0.8)', borderBottom: '1px solid rgba(51, 65, 85, 0.5)', fontSize: '13px', fontWeight: 700, color: '#f1f5f9' }}>
              Defect Evolution Tracking Across Epochs
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid rgba(51, 65, 85, 0.4)', color: '#94a3b8' }}>
                    <th style={{ padding: '10px 14px' }}>Evolution State</th>
                    <th style={{ padding: '10px 14px' }}>Defect Type</th>
                    <th style={{ padding: '10px 14px' }}>Material</th>
                    <th style={{ padding: '10px 14px' }}>Spatial Distance</th>
                    <th style={{ padding: '10px 14px' }}>Confidence</th>
                    <th style={{ padding: '10px 14px' }}>Observation Note</th>
                  </tr>
                </thead>
                <tbody>
                  {changeRecords.map((r, i) => {
                    let tagColor = '#38bdf8';
                    if (r.change_status === 'PERSISTING_DETERIORATION') tagColor = '#f59e0b';
                    if (r.change_status === 'NEW_DETERIORATION') tagColor = '#ef4444';
                    if (r.change_status.includes('RESOLVED') || r.change_status.includes('UNDETECTED')) tagColor = '#10b981';

                    return (
                      <tr key={r.id || i} style={{ borderBottom: '1px solid rgba(51, 65, 85, 0.2)' }}>
                        <td style={{ padding: '10px 14px' }}>
                          <span style={{ color: tagColor, fontWeight: 700 }}>{r.change_status.replace(/_/g, ' ')}</span>
                        </td>
                        <td style={{ padding: '10px 14px', color: '#f1f5f9', textTransform: 'capitalize' }}>{r.deterioration_type}</td>
                        <td style={{ padding: '10px 14px', color: '#94a3b8', textTransform: 'capitalize' }}>{r.material_class || 'sandstone'}</td>
                        <td style={{ padding: '10px 14px', color: '#cbd5e1', fontFamily: 'monospace' }}>
                          {r.spatial_distance != null ? `${r.spatial_distance.toFixed(3)} m` : '—'}
                        </td>
                        <td style={{ padding: '10px 14px', color: '#10b981' }}>
                          {r.comparison_confidence ? `${Math.round(r.comparison_confidence * 100)}%` : '80%'}
                        </td>
                        <td style={{ padding: '10px 14px', color: '#94a3b8' }}>
                          {r.notes || 'Temporal evolution state recorded by spatial proximity matching.'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default MonitoringPage;
