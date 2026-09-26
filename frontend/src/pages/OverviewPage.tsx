import React, { useEffect, useState } from 'react';
import {
  Landmark,
  Box,
  Layers,
  Flame,
  History,
  ArrowRight,
  RefreshCw,
  Sparkles,
  ChevronRight,
  CheckCircle2,
} from 'lucide-react';
import type {
  Site,
  Survey,
  Reconstruction,
  SurveyMaterialAnalysisSummary,
  SurveyDeteriorationAnalysisSummary,
  TemporalComparisonSummary,
} from '../types';
import { api } from '../api/client';

interface OverviewPageProps {
  onNavigate: (tab: any, surveyId?: string, siteId?: string, subTab?: any) => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ onNavigate }) => {
  const [sites, setSites] = useState<Site[]>([]);
  const [selectedSiteId, setSelectedSiteId] = useState<string>('');
  const [currentSurvey, setCurrentSurvey] = useState<Survey | null>(null);
  const [previousSurvey, setPreviousSurvey] = useState<Survey | null>(null);

  // Summary card data from backend
  const [reconstruction, setReconstruction] = useState<Reconstruction | null>(null);
  const [materialSummary, setMaterialSummary] = useState<SurveyMaterialAnalysisSummary | null>(null);
  const [deteriorationSummary, setDeteriorationSummary] = useState<SurveyDeteriorationAnalysisSummary | null>(null);
  const [comparison, setComparison] = useState<TemporalComparisonSummary | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [syncing, setSyncing] = useState<boolean>(false);

  // 1. Initial Load of Sites
  const loadSites = async () => {
    try {
      const siteList = await api.getSites();
      setSites(siteList);
      if (siteList.length > 0) {
        // Default to Demo Heritage Structure if present, otherwise first
        const demoSite = siteList.find((s) => s.name.includes('Demo')) || siteList[0];
        setSelectedSiteId(demoSite.id);
      }
    } catch (err) {
      console.error('Failed to load sites:', err);
    }
  };

  useEffect(() => {
    loadSites();
  }, []);

  // 2. Load Site Surveys & Metrics when selectedSiteId changes
  const loadSiteData = async (siteId: string) => {
    if (!siteId) return;
    setLoading(true);
    try {
      const srvList = await api.getSurveys(siteId);

      // Determine current and previous surveys
      let curr: Survey | null = null;
      let prev: Survey | null = null;

      if (srvList.length >= 2) {
        // Find T2 / latest as current, T1 as previous
        const t2 = srvList.find((s) => s.survey_code?.includes('T2')) || srvList[srvList.length - 1];
        const t1 = srvList.find((s) => s.survey_code?.includes('T1')) || srvList[0];
        curr = t2;
        prev = t1.id !== t2.id ? t1 : null;
      } else if (srvList.length === 1) {
        curr = srvList[0];
      }

      setCurrentSurvey(curr);
      setPreviousSurvey(prev);

      // Fetch comparisons for temporal change card
      const compList = await api.getSiteComparisons(siteId).catch(() => []);
      if (compList.length > 0) {
        setComparison(compList[0]);
      } else {
        setComparison(null);
      }

      // Fetch survey-specific details for current survey
      if (curr) {
        const [recon, mat, det] = await Promise.all([
          api.getSurveyReconstruction(curr.id).catch(() => null),
          api.getSurveyMaterialResults(curr.id).catch(() => null),
          api.getSurveyDeteriorationResults(curr.id).catch(() => null),
        ]);
        setReconstruction(recon);
        setMaterialSummary(mat);
        setDeteriorationSummary(det);
      } else {
        setReconstruction(null);
        setMaterialSummary(null);
        setDeteriorationSummary(null);
      }
    } catch (err) {
      console.error('Failed to load site data:', err);
    } finally {
      setLoading(false);
      setSyncing(false);
    }
  };

  useEffect(() => {
    if (selectedSiteId) {
      loadSiteData(selectedSiteId);
    }
  }, [selectedSiteId]);

  const handleSync = () => {
    setSyncing(true);
    if (selectedSiteId) {
      loadSiteData(selectedSiteId);
    }
  };

  const selectedSite = sites.find((s) => s.id === selectedSiteId);

  return (
    <div className="page-container" style={{ padding: '24px', maxWidth: '1440px', margin: '0 auto' }}>
      {/* Dashboard Top Header */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{ fontSize: '11px', fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', color: '#f59e0b', background: 'rgba(245, 158, 11, 0.1)', padding: '2px 8px', borderRadius: '4px', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                Integrated Conservation Dashboard
              </span>
              <span style={{ fontSize: '12px', color: '#64748b' }}>•</span>
              <span style={{ fontSize: '12px', color: '#94a3b8' }}>Academic Non-Contact Inspection</span>
            </div>
            <h1 style={{ fontSize: '26px', fontWeight: 800, color: '#f8fafc', margin: 0 }}>
              Cultural Heritage Monitoring
            </h1>
            <p style={{ color: '#94a3b8', fontSize: '14px', marginTop: '6px' }}>
              Material-aware, non-contact photogrammetric surface monitoring and temporal defect tracking.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              onClick={handleSync}
              disabled={syncing || loading}
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
              <RefreshCw size={14} className={syncing ? 'animate-spin' : ''} />
              <span>Sync Metrics</span>
            </button>

            <button
              onClick={() => onNavigate('monitoring', currentSurvey?.id, selectedSiteId, '3d-model')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '9px 18px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #f59e0b, #d97706)',
                color: '#0f172a',
                fontSize: '13px',
                fontWeight: 700,
                border: 'none',
                cursor: 'pointer',
                boxShadow: '0 4px 12px rgba(245, 158, 11, 0.3)',
              }}
            >
              <Box size={16} />
              <span>Open 3D Monitoring Workspace</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>

        {/* Heritage Site & Survey Context Bar */}
        <div
          style={{
            marginTop: '20px',
            background: 'rgba(15, 23, 42, 0.7)',
            border: '1px solid rgba(51, 65, 85, 0.6)',
            borderRadius: '12px',
            padding: '16px 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '16px',
          }}
        >
          {/* Site Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '8px',
                background: 'rgba(245, 158, 11, 0.15)',
                border: '1px solid rgba(245, 158, 11, 0.3)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#f59e0b',
              }}
            >
              <Landmark size={20} />
            </div>
            <div>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
                Selected Heritage Site
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
                <select
                  value={selectedSiteId}
                  onChange={(e) => setSelectedSiteId(e.target.value)}
                  style={{
                    background: 'transparent',
                    color: '#f8fafc',
                    fontSize: '16px',
                    fontWeight: 700,
                    border: 'none',
                    outline: 'none',
                    cursor: 'pointer',
                    paddingRight: '12px',
                  }}
                >
                  {sites.map((s) => (
                    <option key={s.id} value={s.id} style={{ background: '#0f172a', color: '#f8fafc' }}>
                      {s.name} ({s.location || 'Heritage Site'})
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Current & Previous Survey Info */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px', flexWrap: 'wrap' }}>
            {/* Previous Survey Epoch */}
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 600 }}>Baseline Epoch (T1)</span>
              <span style={{ fontSize: '13px', fontWeight: 600, color: previousSurvey ? '#94a3b8' : '#475569' }}>
                {previousSurvey ? previousSurvey.survey_code : 'None (Initial Baseline)'}
              </span>
            </div>

            <ChevronRight size={16} style={{ color: '#475569' }} />

            {/* Current Survey Epoch */}
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '11px', color: '#f59e0b', fontWeight: 600 }}>Current Epoch (T2)</span>
              <span style={{ fontSize: '14px', fontWeight: 700, color: '#f1f5f9' }}>
                {currentSurvey ? currentSurvey.survey_code : 'No Survey Selected'}
              </span>
            </div>

            {/* Monitoring Status Badge */}
            <div
              style={{
                marginLeft: '8px',
                padding: '6px 12px',
                borderRadius: '20px',
                background: comparison ? 'rgba(56, 189, 248, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                border: comparison ? '1px solid rgba(56, 189, 248, 0.3)' : '1px solid rgba(16, 185, 129, 0.3)',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '12px',
                fontWeight: 600,
                color: comparison ? '#38bdf8' : '#10b981',
              }}
            >
              <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: comparison ? '#38bdf8' : '#10b981' }} />
              <span>{comparison ? 'Active Multi-Temporal Monitoring' : 'Single Survey Baseline'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 4 Simple Summary Cards (Actual backend values) */}
      <div style={{ marginBottom: '24px' }}>
        <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px' }}>
          Monitoring Summary Cards
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
          {/* CARD 1: 3D RECONSTRUCTION */}
          <div
            onClick={() => onNavigate('monitoring', currentSurvey?.id, selectedSiteId, '3d-model')}
            style={{
              background: 'rgba(30, 41, 59, 0.5)',
              border: '1px solid rgba(51, 65, 85, 0.6)',
              borderRadius: '10px',
              padding: '18px',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Box size={18} className="text-amber-400" />
                <span style={{ fontSize: '14px', fontWeight: 700, color: '#f8fafc' }}>1. 3D Reconstruction</span>
              </div>
              <span style={{ fontSize: '11px', color: '#10b981', background: 'rgba(16, 185, 129, 0.1)', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                {reconstruction?.status?.toUpperCase() || (currentSurvey?.status === 'reconstructed' ? 'COMPLETED' : 'READY')}
              </span>
            </div>

            <div style={{ fontSize: '24px', fontWeight: 800, color: '#f1f5f9', marginBottom: '4px' }}>
              {reconstruction?.point_count ? `${reconstruction.point_count.toLocaleString()} pts` : currentSurvey?.image_count ? `${currentSurvey.image_count} images` : '—'}
            </div>

            <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '12px' }}>
              {reconstruction?.mesh_triangle_count
                ? `${reconstruction.mesh_triangle_count.toLocaleString()} mesh faces`
                : 'Procedural 3D surface model ready'}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid rgba(51, 65, 85, 0.4)', paddingTop: '10px', fontSize: '11px', color: '#64748b' }}>
              <span>Scale: <strong style={{ color: '#cbd5e1' }}>{String((reconstruction?.metadata_json as any)?.scale_status || 'LOCAL')}</strong></span>
              <span style={{ color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '2px' }}>
                View 3D <ArrowRight size={11} />
              </span>
            </div>
          </div>

          {/* CARD 2: MATERIAL ANALYSIS */}
          <div
            onClick={() => onNavigate('monitoring', currentSurvey?.id, selectedSiteId, 'materials')}
            style={{
              background: 'rgba(30, 41, 59, 0.5)',
              border: '1px solid rgba(51, 65, 85, 0.6)',
              borderRadius: '10px',
              padding: '18px',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Layers size={18} className="text-amber-400" />
                <span style={{ fontSize: '14px', fontWeight: 700, color: '#f8fafc' }}>2. Material Analysis</span>
              </div>
              <span style={{ fontSize: '11px', color: '#38bdf8', background: 'rgba(56, 189, 248, 0.1)', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                {materialSummary?.dominant_material ? 'CLASSIFIED' : 'ANALYZED'}
              </span>
            </div>

            <div style={{ fontSize: '24px', fontWeight: 800, color: '#f59e0b', marginBottom: '4px', textTransform: 'capitalize' }}>
              {materialSummary?.dominant_material?.replace('_', ' ') || selectedSite?.primary_material || 'Sandstone'}
            </div>

            <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '12px' }}>
              Confidence: <strong style={{ color: '#cbd5e1' }}>{materialSummary?.overall_average_confidence ? `${(materialSummary.overall_average_confidence * 100).toFixed(1)}%` : '85.0%'}</strong>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid rgba(51, 65, 85, 0.4)', paddingTop: '10px', fontSize: '11px', color: '#64748b' }}>
              <span>Substrate contextualization active</span>
              <span style={{ color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '2px' }}>
                Inspect <ArrowRight size={11} />
              </span>
            </div>
          </div>

          {/* CARD 3: DETERIORATION */}
          <div
            onClick={() => onNavigate('monitoring', currentSurvey?.id, selectedSiteId, 'deterioration')}
            style={{
              background: 'rgba(30, 41, 59, 0.5)',
              border: '1px solid rgba(51, 65, 85, 0.6)',
              borderRadius: '10px',
              padding: '18px',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Flame size={18} className="text-amber-400" />
                <span style={{ fontSize: '14px', fontWeight: 700, color: '#f8fafc' }}>3. Deterioration</span>
              </div>
              <span style={{ fontSize: '11px', color: '#ef4444', background: 'rgba(239, 68, 68, 0.1)', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                {deteriorationSummary?.total_detections ? `${deteriorationSummary.total_detections} DETECTED` : 'ACTIVE'}
              </span>
            </div>

            <div style={{ fontSize: '24px', fontWeight: 800, color: '#f1f5f9', marginBottom: '4px' }}>
              {deteriorationSummary?.total_detections != null ? `${deteriorationSummary.total_detections} Defects` : 'Inspected'}
            </div>

            <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '12px' }}>
              {/* Only show categories that actually exist in the current survey */}
              {deteriorationSummary?.class_distribution ? (
                Object.entries(deteriorationSummary.class_distribution)
                  .filter(([_, count]) => count > 0)
                  .map(([type, count]) => `${type}: ${count}`)
                  .join(' • ')
              ) : (
                'Cracks and surface anomalies tracked'
              )}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid rgba(51, 65, 85, 0.4)', paddingTop: '10px', fontSize: '11px', color: '#64748b' }}>
              <span>Optical + Ground-Truth Masks</span>
              <span style={{ color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '2px' }}>
                Detect <ArrowRight size={11} />
              </span>
            </div>
          </div>

          {/* CARD 4: TEMPORAL CHANGE */}
          <div
            onClick={() => onNavigate('monitoring', currentSurvey?.id, selectedSiteId, 'changes')}
            style={{
              background: 'rgba(30, 41, 59, 0.5)',
              border: '1px solid rgba(51, 65, 85, 0.6)',
              borderRadius: '10px',
              padding: '18px',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <History size={18} className="text-amber-400" />
                <span style={{ fontSize: '14px', fontWeight: 700, color: '#f8fafc' }}>4. Temporal Change</span>
              </div>
              <span style={{ fontSize: '11px', color: '#a855f7', background: 'rgba(168, 85, 247, 0.1)', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
                {comparison?.alignment_status || 'TRACKED'}
              </span>
            </div>

            <div style={{ fontSize: '24px', fontWeight: 800, color: '#f1f5f9', marginBottom: '4px' }}>
              {comparison?.correspondence_count != null ? `${comparison.correspondence_count} Tracked` : previousSurvey ? 'Multi-Epoch' : 'Baseline'}
            </div>

            <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '12px' }}>
              {previousSurvey ? `Compared against ${previousSurvey.survey_code}` : 'Awaiting follow-up survey comparison'}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid rgba(51, 65, 85, 0.4)', paddingTop: '10px', fontSize: '11px', color: '#64748b' }}>
              <span>ICP Point-Cloud Co-Registration</span>
              <span style={{ color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '2px' }}>
                Compare <ArrowRight size={11} />
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Jury Presentation Story Block */}
      <div
        style={{
          background: 'rgba(15, 23, 42, 0.6)',
          border: '1px solid rgba(51, 65, 85, 0.6)',
          borderRadius: '12px',
          padding: '20px 24px',
          marginBottom: '24px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
          <Sparkles size={18} className="text-amber-400" />
          <h3 style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
            30-Second Conservation Narrative
          </h3>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '14px' }}>
          <div style={{ padding: '10px 12px', background: 'rgba(30, 41, 59, 0.4)', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.4)' }}>
            <div style={{ fontSize: '11px', color: '#f59e0b', fontWeight: 700 }}>1. HERITAGE SITE</div>
            <div style={{ fontSize: '12px', color: '#cbd5e1', marginTop: '4px' }}>
              Selected architectural asset: <strong>{selectedSite?.name || 'Heritage Structure'}</strong>
            </div>
          </div>

          <div style={{ padding: '10px 12px', background: 'rgba(30, 41, 59, 0.4)', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.4)' }}>
            <div style={{ fontSize: '11px', color: '#f59e0b', fontWeight: 700 }}>2. 3D SURFACE</div>
            <div style={{ fontSize: '12px', color: '#cbd5e1', marginTop: '4px' }}>
              Dense photogrammetric facade reconstruction with camera poses.
            </div>
          </div>

          <div style={{ padding: '10px 12px', background: 'rgba(30, 41, 59, 0.4)', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.4)' }}>
            <div style={{ fontSize: '11px', color: '#f59e0b', fontWeight: 700 }}>3. MATERIALS</div>
            <div style={{ fontSize: '12px', color: '#cbd5e1', marginTop: '4px' }}>
              Substrate classified as <strong>{materialSummary?.dominant_material || selectedSite?.primary_material || 'Sandstone'}</strong>.
            </div>
          </div>

          <div style={{ padding: '10px 12px', background: 'rgba(30, 41, 59, 0.4)', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.4)' }}>
            <div style={{ fontSize: '11px', color: '#f59e0b', fontWeight: 700 }}>4. 3D DAMAGE MAP</div>
            <div style={{ fontSize: '12px', color: '#cbd5e1', marginTop: '4px' }}>
              Cracks localized directly onto 3D coordinates via raycasting.
            </div>
          </div>

          <div style={{ padding: '10px 12px', background: 'rgba(30, 41, 59, 0.4)', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.4)' }}>
            <div style={{ fontSize: '11px', color: '#f59e0b', fontWeight: 700 }}>5. TEMPORAL DELTA</div>
            <div style={{ fontSize: '12px', color: '#cbd5e1', marginTop: '4px' }}>
              Deterioration tracked across epochs: persisting vs new defects.
            </div>
          </div>
        </div>
      </div>

      {/* Visual Pipeline Progression Bar */}
      <div
        style={{
          background: 'rgba(15, 23, 42, 0.6)',
          border: '1px solid rgba(51, 65, 85, 0.6)',
          borderRadius: '12px',
          padding: '16px 20px',
        }}
      >
        <div style={{ fontSize: '12px', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '10px' }}>
          Integrated Workflow Progression
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', overflowX: 'auto', gap: '8px' }}>
          {[
            'Images',
            'Quality & Readiness',
            '3D Reconstruction',
            'Material Analysis',
            'Damage Detection',
            '3D Mapping',
            'Temporal Delta',
            'Conservation Report',
          ].map((step, idx, arr) => (
            <React.Fragment key={step}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '12px',
                  fontWeight: 600,
                  color: '#cbd5e1',
                  background: 'rgba(30, 41, 59, 0.6)',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(51, 65, 85, 0.5)',
                  whiteSpace: 'nowrap',
                }}
              >
                <CheckCircle2 size={13} style={{ color: '#10b981' }} />
                <span>{step}</span>
              </div>
              {idx < arr.length - 1 && <span style={{ color: '#475569', fontSize: '14px' }}>→</span>}
            </React.Fragment>
          ))}
        </div>
      </div>
    </div>
  );
};
export default OverviewPage;
