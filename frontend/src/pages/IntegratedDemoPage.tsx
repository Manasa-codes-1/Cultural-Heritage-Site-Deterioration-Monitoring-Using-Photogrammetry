import React, { useState, useEffect } from 'react';
import {
  PlayCircle,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Info,
  Layers,
  Box,
  Flame,
  Crosshair,
  History,
  ShieldCheck,
  Camera,
  Download,
} from 'lucide-react';
import { apiClient } from '../api/client';
import type {
  IntegratedDemoResponse,
  DemoStatusResponse,
} from '../types';
import { ModelViewer3D } from '../components/viewer/ModelViewer3D';

interface IntegratedDemoPageProps {
  onNavigateToSurveys?: () => void;
}

export const IntegratedDemoPage: React.FC<IntegratedDemoPageProps> = () => {
  const [status, setStatus] = useState<DemoStatusResponse | null>(null);
  const [demoData, setDemoData] = useState<IntegratedDemoResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [resetting, setResetting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [activePhase, setActivePhase] = useState<number>(1);
  const [executionSeconds, setExecutionSeconds] = useState<number | null>(null);
  const [selectedImageIndex, setSelectedImageIndex] = useState<number>(0);
  const [selectedMappingId, setSelectedMappingId] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const res = await apiClient.getDemoStatus();
      setStatus(res);
    } catch (err: any) {
      console.error('Failed to fetch demo status:', err);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleRunDemo = async () => {
    setLoading(true);
    setError(null);
    const start = performance.now();
    try {
      const res = await apiClient.runIntegratedDemo();
      const elapsed = ((performance.now() - start) / 1000).toFixed(1);
      setExecutionSeconds(parseFloat(elapsed));
      setDemoData(res);
      await fetchStatus();
    } catch (err: any) {
      setError(err.message || 'Failed to execute integrated demo pipeline.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Reset demo state? This will remove generated demo models and reset the pipeline for a fresh demonstration run.')) {
      return;
    }
    setResetting(true);
    setError(null);
    try {
      await apiClient.resetDemo();
      setDemoData(null);
      setExecutionSeconds(null);
      await fetchStatus();
    } catch (err: any) {
      setError(err.message || 'Failed to reset demo.');
    } finally {
      setResetting(false);
    }
  };

  const phases = [
    { num: 1, title: 'Quality Assessment', icon: Camera, badge: 'Real DeepCrack' },
    { num: 2, title: 'Feature Matching', icon: Layers, badge: 'Real Optical' },
    { num: 3, title: '3D Photogrammetry', icon: Box, badge: 'Synthetic Mesh' },
    { num: 4, title: 'Material Classification', icon: Layers, badge: 'Heritage AI' },
    { num: 5, title: 'Deterioration Detection', icon: Flame, badge: 'Real GT Masks' },
    { num: 6, title: '2D → 3D Damage Mapping', icon: Crosshair, badge: 'Raycast Facade' },
    { num: 7, title: 'Multi-Temporal Change', icon: History, badge: 'T1 vs T2 ICP' },
  ];

  return (
    <div className="page-container" style={{ padding: '24px', maxWidth: '1440px', margin: '0 auto' }}>
      {/* Header Banner */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span
                style={{
                  background: '#f59e0b',
                  color: '#0f172a',
                  fontWeight: 800,
                  fontSize: '11px',
                  padding: '3px 8px',
                  borderRadius: '4px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                }}
              >
                Demonstration Mode
              </span>
              <h1 style={{ fontSize: '24px', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                End-to-End Integrated Demonstration (Phases 1–7)
              </h1>
            </div>
            <p style={{ color: '#94a3b8', fontSize: '14px', marginTop: '6px' }}>
              Continuous academic demonstration pipeline for mentor evaluation: Optical Quality → Image Matching → 3D Reconstruction → Material Classification → Damage Detection → Spatial Mapping → Multi-Temporal Change Tracking.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              onClick={handleReset}
              disabled={loading || resetting}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '9px 16px',
                borderRadius: '8px',
                backgroundColor: 'rgba(51, 65, 85, 0.6)',
                border: '1px solid rgba(100, 116, 139, 0.4)',
                color: '#cbd5e1',
                fontSize: '13px',
                fontWeight: 600,
                cursor: loading || resetting ? 'not-allowed' : 'pointer',
              }}
            >
              <RotateCcw size={15} className={resetting ? 'animate-spin' : ''} />
              {resetting ? 'Resetting...' : 'Reset Demo'}
            </button>

            <button
              onClick={handleRunDemo}
              disabled={loading || resetting}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 20px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #f59e0b, #d97706)',
                color: '#0f172a',
                fontSize: '14px',
                fontWeight: 700,
                border: 'none',
                cursor: loading || resetting ? 'not-allowed' : 'pointer',
                boxShadow: '0 4px 14px rgba(245, 158, 11, 0.35)',
              }}
            >
              <PlayCircle size={18} className={loading ? 'animate-spin' : ''} />
              {loading ? 'Executing Pipeline (Phases 1–7)...' : demoData ? 'Re-run Complete Demo' : 'Run Complete Demo'}
            </button>
          </div>
        </div>

        {/* Academic Integrity & Provenance Notice */}
        <div
          style={{
            marginTop: '16px',
            padding: '12px 16px',
            borderRadius: '8px',
            background: 'rgba(30, 41, 59, 0.7)',
            border: '1px solid rgba(59, 130, 246, 0.3)',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '12px',
          }}
        >
          <Info size={18} style={{ color: '#60a5fa', flexShrink: 0, marginTop: '2px' }} />
          <div style={{ fontSize: '13px', color: '#cbd5e1', lineHeight: '1.5' }}>
            <span style={{ fontWeight: 600, color: '#93c5fd' }}>Research Provenance & Integrity Notice: </span>
            This demonstration pairs <strong>real DeepCrack optical images and ground-truth crack segmentation masks</strong> (Phases 1, 2, 4, 5) with <strong>synthetic photogrammetric 3D geometry and ICP multi-temporal tracking</strong> (Phases 3, 6, 7). All synthetic attributes are explicitly tagged with <code style={{ color: '#f59e0b', background: 'rgba(0,0,0,0.3)', padding: '2px 4px', borderRadius: '3px' }}>is_demo = True</code>. Millimeter physical progression claims are not fabricated.
          </div>
        </div>

        {error && (
          <div
            style={{
              marginTop: '12px',
              padding: '12px 16px',
              borderRadius: '8px',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              color: '#fca5a5',
              fontSize: '13px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
            }}
          >
            <AlertTriangle size={18} />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Progress & Stepper */}
      <div style={{ marginBottom: '24px' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
            gap: '10px',
            background: 'rgba(15, 23, 42, 0.6)',
            padding: '12px',
            borderRadius: '12px',
            border: '1px solid rgba(51, 65, 85, 0.5)',
          }}
        >
          {phases.map((p) => {
            const Icon = p.icon;
            const isCurrent = activePhase === p.num;
            const isDone = !!demoData;
            return (
              <button
                key={p.num}
                onClick={() => setActivePhase(p.num)}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'flex-start',
                  padding: '10px 12px',
                  borderRadius: '8px',
                  border: isCurrent
                    ? '1px solid #f59e0b'
                    : isDone
                    ? '1px solid rgba(16, 185, 129, 0.3)'
                    : '1px solid rgba(51, 65, 85, 0.4)',
                  background: isCurrent
                    ? 'rgba(245, 158, 11, 0.15)'
                    : isDone
                    ? 'rgba(16, 185, 129, 0.05)'
                    : 'rgba(30, 41, 59, 0.4)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.2s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', marginBottom: '6px' }}>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      color: isCurrent ? '#f59e0b' : '#94a3b8',
                      textTransform: 'uppercase',
                    }}
                  >
                    Phase {p.num}
                  </span>
                  {isDone && <CheckCircle2 size={14} style={{ color: '#10b981' }} />}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                  <Icon size={14} style={{ color: isCurrent ? '#fbbf24' : '#cbd5e1' }} />
                  <span style={{ fontSize: '12px', fontWeight: 600, color: '#f1f5f9' }}>{p.title}</span>
                </div>
                <span
                  style={{
                    fontSize: '10px',
                    color: isCurrent ? '#fde68a' : '#64748b',
                    fontWeight: 500,
                  }}
                >
                  {p.badge}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Execution View */}
      {loading ? (
        <div
          style={{
            background: 'rgba(30, 41, 59, 0.5)',
            border: '1px solid rgba(51, 65, 85, 0.6)',
            borderRadius: '12px',
            padding: '48px 24px',
            textAlign: 'center',
          }}
        >
          <div
            style={{
              width: '48px',
              height: '48px',
              border: '4px solid rgba(245, 158, 11, 0.2)',
              borderTopColor: '#f59e0b',
              borderRadius: '50%',
              margin: '0 auto 16px',
              animation: 'spin 1s linear infinite',
            }}
          />
          <h3 style={{ fontSize: '18px', fontWeight: 600, color: '#f8fafc', marginBottom: '8px' }}>
            Executing Integrated Demonstration Pipeline...
          </h3>
          <p style={{ color: '#94a3b8', fontSize: '14px', maxWidth: '540px', margin: '0 auto' }}>
            Processing DeepCrack images through Phase 1 Quality Assessor → Phase 2 Graph Matcher → Phase 3 SfM Reconstruction → Phase 4 Material Classifier → Phase 5 Damage Detector → Phase 6 Surface Raycaster → Phase 7 Multi-Temporal ICP Change Tracker.
          </p>
        </div>
      ) : !demoData ? (
        /* Empty / Not Run State */
        <div
          style={{
            background: 'rgba(30, 41, 59, 0.5)',
            border: '1px dashed rgba(71, 85, 105, 0.6)',
            borderRadius: '12px',
            padding: '48px 24px',
            textAlign: 'center',
          }}
        >
          <PlayCircle size={48} style={{ color: '#f59e0b', margin: '0 auto 16px' }} />
          <h3 style={{ fontSize: '20px', fontWeight: 700, color: '#f8fafc', marginBottom: '8px' }}>
            Ready for Mentor Presentation
          </h3>
          <p style={{ color: '#94a3b8', fontSize: '14px', maxWidth: '600px', margin: '0 auto 20px', lineHeight: '1.6' }}>
            Click <strong>"Run Complete Demo"</strong> above to launch the full 7-phase research chain. The system will automatically provision the demonstration site, load verified DeepCrack imagery and ground truth masks, run procedural 3D photogrammetry, and compute multi-temporal change tracking.
          </p>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#38bdf8', background: 'rgba(56, 189, 248, 0.1)', padding: '6px 14px', borderRadius: '20px' }}>
            <ShieldCheck size={16} />
            <span>DeepCrack Dataset Available: {status?.deepcrack_image_count ?? 'Detecting'} sample images ready</span>
          </div>
        </div>
      ) : (
        /* Executed Demo View */
        <div>
          {/* Top Quick Metrics */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '12px',
              marginBottom: '20px',
            }}
          >
            <div style={{ background: 'rgba(30, 41, 59, 0.6)', border: '1px solid rgba(51, 65, 85, 0.6)', borderRadius: '8px', padding: '12px 16px' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Heritage Site</div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc', marginTop: '4px' }}>{demoData.site_name}</div>
              <div style={{ fontSize: '11px', color: '#64748b' }}>DEMO-SRV-T1 vs T2</div>
            </div>

            <div style={{ background: 'rgba(30, 41, 59, 0.6)', border: '1px solid rgba(51, 65, 85, 0.6)', borderRadius: '8px', padding: '12px 16px' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Optical Images</div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc', marginTop: '4px' }}>
                {demoData.phase1_quality.total_images} DeepCrack ({demoData.phase1_quality.usable_images} usable)
              </div>
              <div style={{ fontSize: '11px', color: '#10b981' }}>Avg Blur: {demoData.phase1_quality.average_blur}</div>
            </div>

            <div style={{ background: 'rgba(30, 41, 59, 0.6)', border: '1px solid rgba(51, 65, 85, 0.6)', borderRadius: '8px', padding: '12px 16px' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>3D Mesh & Points</div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc', marginTop: '4px' }}>
                {demoData.phase3_reconstruction.point_count.toLocaleString()} pts / {demoData.phase3_reconstruction.mesh_face_count.toLocaleString()} faces
              </div>
              <div style={{ fontSize: '11px', color: '#f59e0b' }}>Scale: {demoData.phase3_reconstruction.scale_status} (Mock)</div>
            </div>

            <div style={{ background: 'rgba(30, 41, 59, 0.6)', border: '1px solid rgba(51, 65, 85, 0.6)', borderRadius: '8px', padding: '12px 16px' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Detections & Mapping</div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc', marginTop: '4px' }}>
                {demoData.phase5_deterioration.total_detections} Dets → {demoData.phase6_damage_mapping.total_mapped} Mapped
              </div>
              <div style={{ fontSize: '11px', color: '#38bdf8' }}>Material: {demoData.phase4_materials.primary_material}</div>
            </div>

            <div style={{ background: 'rgba(30, 41, 59, 0.6)', border: '1px solid rgba(51, 65, 85, 0.6)', borderRadius: '8px', padding: '12px 16px' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>Temporal Tracking</div>
              <div style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc', marginTop: '4px' }}>
                {demoData.phase7_temporal.total_changes} Change Events
              </div>
              <div style={{ fontSize: '11px', color: '#a855f7' }}>Execution: {executionSeconds ? `${executionSeconds}s` : 'Instant'}</div>
            </div>
          </div>

          {/* Tab Content Panel */}
          <div
            style={{
              background: 'rgba(30, 41, 59, 0.5)',
              border: '1px solid rgba(51, 65, 85, 0.6)',
              borderRadius: '12px',
              padding: '24px',
              marginBottom: '24px',
            }}
          >
            {/* PHASE 1: IMAGE QUALITY */}
            {activePhase === 1 && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div>
                    <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                      Phase 1: Advanced Image Quality Assessment
                    </h3>
                    <p style={{ color: '#94a3b8', fontSize: '13px', margin: '4px 0 0' }}>
                      Individual image-level assessment on DeepCrack optical inputs using Laplacian variance, luminance histograms, and feature density.
                    </p>
                  </div>
                  <span style={{ fontSize: '12px', color: '#10b981', background: 'rgba(16, 185, 129, 0.1)', padding: '4px 10px', borderRadius: '4px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                    Real DeepCrack Imagery
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
                  {demoData.phase1_quality.images.map((img) => (
                    <div
                      key={img.id}
                      style={{
                        background: 'rgba(15, 23, 42, 0.6)',
                        border: '1px solid rgba(51, 65, 85, 0.6)',
                        borderRadius: '8px',
                        overflow: 'hidden',
                      }}
                    >
                      <div style={{ height: '140px', background: '#0b1120', position: 'relative', overflow: 'hidden' }}>
                        <img
                          src={img.download_url}
                          alt={img.filename}
                          style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                          onError={(e) => {
                            (e.target as HTMLElement).style.display = 'none';
                          }}
                        />
                        <div
                          style={{
                            position: 'absolute',
                            top: '8px',
                            right: '8px',
                            background: img.is_usable ? 'rgba(16, 185, 129, 0.85)' : 'rgba(239, 68, 68, 0.85)',
                            color: '#ffffff',
                            fontSize: '10px',
                            fontWeight: 700,
                            padding: '2px 6px',
                            borderRadius: '4px',
                          }}
                        >
                          {img.is_usable ? 'USABLE' : 'UNUSABLE'}
                        </div>
                      </div>
                      <div style={{ padding: '12px' }}>
                        <div style={{ fontSize: '13px', fontWeight: 600, color: '#f1f5f9', marginBottom: '6px' }}>
                          {img.filename}
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '11px', color: '#94a3b8' }}>
                          <div>Blur Score: <strong style={{ color: '#cbd5e1' }}>{img.blur_score}</strong></div>
                          <div>Blur Status: <strong style={{ color: '#cbd5e1' }}>{img.blur_status}</strong></div>
                          <div>Brightness: <strong style={{ color: '#cbd5e1' }}>{img.brightness_score}</strong></div>
                          <div>Dimensions: <strong style={{ color: '#cbd5e1' }}>{img.width}x{img.height}</strong></div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* PHASE 2: MATCHING & READINESS */}
            {activePhase === 2 && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div>
                    <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                      Phase 2: Image Matching & Collection Network Graph
                    </h3>
                    <p style={{ color: '#94a3b8', fontSize: '13px', margin: '4px 0 0' }}>
                      Evaluates pairwise feature correspondence and determines whether the image collection has sufficient overlap for reconstruction.
                    </p>
                  </div>
                  <span
                    style={{
                      fontSize: '12px',
                      fontWeight: 700,
                      color: demoData.phase2_matching.readiness_status === 'RECAPTURE_REQUIRED' ? '#f59e0b' : '#10b981',
                      background: demoData.phase2_matching.readiness_status === 'RECAPTURE_REQUIRED' ? 'rgba(245, 158, 11, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                      padding: '4px 10px',
                      borderRadius: '4px',
                      border: '1px solid rgba(245, 158, 11, 0.3)',
                    }}
                  >
                    {demoData.phase2_matching.readiness_status}
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '20px' }}>
                  <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.5)' }}>
                    <div style={{ fontSize: '11px', color: '#94a3b8' }}>Pairs Analyzed</div>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: '#f8fafc', marginTop: '4px' }}>
                      {demoData.phase2_matching.pairs_analyzed}
                    </div>
                  </div>
                  <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.5)' }}>
                    <div style={{ fontSize: '11px', color: '#94a3b8' }}>Good Matching Pairs</div>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: '#10b981', marginTop: '4px' }}>
                      {demoData.phase2_matching.good_pairs}
                    </div>
                  </div>
                  <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.5)' }}>
                    <div style={{ fontSize: '11px', color: '#94a3b8' }}>Warning / Poor Pairs</div>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: '#f59e0b', marginTop: '4px' }}>
                      {demoData.phase2_matching.warning_pairs} / {demoData.phase2_matching.poor_pairs}
                    </div>
                  </div>
                  <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.5)' }}>
                    <div style={{ fontSize: '11px', color: '#94a3b8' }}>Avg Good Matches</div>
                    <div style={{ fontSize: '20px', fontWeight: 700, color: '#38bdf8', marginTop: '4px' }}>
                      {demoData.phase2_matching.average_good_matches}
                    </div>
                  </div>
                </div>

                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.5)' }}>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: '#e2e8f0', marginBottom: '8px' }}>
                    Photogrammetric Recommendations:
                  </div>
                  <ul style={{ margin: 0, paddingLeft: '20px', color: '#94a3b8', fontSize: '13px', lineHeight: '1.6' }}>
                    {demoData.phase2_matching.recommendations.map((rec, i) => (
                      <li key={i}>{rec}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}

            {/* PHASE 3: 3D PHOTOGRAMMETRIC RECONSTRUCTION */}
            {activePhase === 3 && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div>
                    <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                      Phase 3: Photogrammetry & 3D Reconstruction
                    </h3>
                    <p style={{ color: '#94a3b8', fontSize: '13px', margin: '4px 0 0' }}>
                      Structure-from-Motion (SfM) and Dense Multi-View Stereo (MVS) generation producing textured point clouds and triangle meshes.
                    </p>
                  </div>
                  <span style={{ fontSize: '12px', color: '#f59e0b', background: 'rgba(245, 158, 11, 0.1)', padding: '4px 10px', borderRadius: '4px', border: '1px solid rgba(245, 158, 11, 0.3)' }}>
                    Synthetic Heritage Facade Geometry
                  </span>
                </div>

                <div style={{ height: '420px', borderRadius: '8px', overflow: 'hidden', border: '1px solid rgba(51, 65, 85, 0.8)', marginBottom: '16px', position: 'relative' }}>
                  <ModelViewer3D
                    modelUrl={demoData.phase3_reconstruction.ply_url}
                    isDemo={true}
                    pointCount={demoData.phase3_reconstruction.point_count}
                    vertexCount={demoData.phase3_reconstruction.mesh_vertex_count}
                    triangleCount={demoData.phase3_reconstruction.mesh_face_count}
                  />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', background: 'rgba(15, 23, 42, 0.6)', padding: '12px 16px', borderRadius: '8px' }}>
                  <div style={{ display: 'flex', gap: '20px', fontSize: '13px', color: '#cbd5e1' }}>
                    <span>Points: <strong>{demoData.phase3_reconstruction.point_count.toLocaleString()}</strong></span>
                    <span>Vertices: <strong>{demoData.phase3_reconstruction.mesh_vertex_count.toLocaleString()}</strong></span>
                    <span>Triangles: <strong>{demoData.phase3_reconstruction.mesh_face_count.toLocaleString()}</strong></span>
                    <span>Scale: <strong style={{ color: '#f59e0b' }}>{demoData.phase3_reconstruction.scale_status}</strong></span>
                  </div>

                  <div style={{ display: 'flex', gap: '8px' }}>
                    <a
                      href={demoData.phase3_reconstruction.ply_url}
                      download="dense.ply"
                      style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#38bdf8', background: 'rgba(56, 189, 248, 0.1)', padding: '6px 12px', borderRadius: '6px', textDecoration: 'none' }}
                    >
                      <Download size={14} /> Download PLY
                    </a>
                    <a
                      href={demoData.phase3_reconstruction.obj_url}
                      download="mesh.obj"
                      style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#38bdf8', background: 'rgba(56, 189, 248, 0.1)', padding: '6px 12px', borderRadius: '6px', textDecoration: 'none' }}
                    >
                      <Download size={14} /> Download OBJ
                    </a>
                  </div>
                </div>
              </div>
            )}

            {/* PHASE 4: MATERIAL CLASSIFICATION */}
            {activePhase === 4 && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div>
                    <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                      Phase 4: Material Classification Pipeline
                    </h3>
                    <p style={{ color: '#94a3b8', fontSize: '13px', margin: '4px 0 0' }}>
                      Identifies probable architectural substrate materials (sandstone, limestone, brick, lime mortar) for contextual deterioration modeling.
                    </p>
                  </div>
                  <span style={{ fontSize: '12px', color: '#10b981', background: 'rgba(16, 185, 129, 0.1)', padding: '4px 10px', borderRadius: '4px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                    Material Association Active
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginBottom: '20px' }}>
                  <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.5)' }}>
                    <div style={{ fontSize: '12px', color: '#94a3b8' }}>Dominant Material</div>
                    <div style={{ fontSize: '22px', fontWeight: 700, color: '#f59e0b', marginTop: '4px', textTransform: 'capitalize' }}>
                      {demoData.phase4_materials.primary_material.replace('_', ' ')}
                    </div>
                  </div>

                  <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.5)' }}>
                    <div style={{ fontSize: '12px', color: '#94a3b8' }}>Average Confidence</div>
                    <div style={{ fontSize: '22px', fontWeight: 700, color: '#10b981', marginTop: '4px' }}>
                      {(demoData.phase4_materials.average_confidence * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>

                <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.5)' }}>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: '#e2e8f0', marginBottom: '12px' }}>
                    Material Class Distribution:
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {Object.entries(demoData.phase4_materials.material_distribution).map(([mat, count]) => {
                      const total = Object.values(demoData.phase4_materials.material_distribution).reduce((a, b) => a + b, 0);
                      const pct = total > 0 ? Math.round((count / total) * 100) : 0;
                      return (
                        <div key={mat}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#cbd5e1', marginBottom: '4px' }}>
                            <span style={{ textTransform: 'capitalize' }}>{mat.replace('_', ' ')}</span>
                            <span>{count} detections ({pct}%)</span>
                          </div>
                          <div style={{ height: '8px', background: 'rgba(51, 65, 85, 0.5)', borderRadius: '4px', overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${pct}%`, background: '#f59e0b', borderRadius: '4px' }} />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}

            {/* PHASE 5: DETERIORATION DETECTION & GT MASKS */}
            {activePhase === 5 && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
                  <div>
                    <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                      Phase 5: Deterioration Detection with Real Ground-Truth Masks
                    </h3>
                    <p style={{ color: '#94a3b8', fontSize: '13px', margin: '4px 0 0' }}>
                      Comparing raw optical field imagery with verified DeepCrack ground-truth binary defect masks.
                    </p>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '12px', color: '#10b981', background: 'rgba(16, 185, 129, 0.1)', padding: '4px 10px', borderRadius: '4px', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
                      Verified Ground Truth Masks
                    </span>
                  </div>
                </div>

                {/* Image Selection Carousel */}
                <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '10px', marginBottom: '16px' }}>
                  {demoData.phase1_quality.images.map((img, idx) => (
                    <button
                      key={img.id}
                      onClick={() => setSelectedImageIndex(idx)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        padding: '8px 12px',
                        borderRadius: '6px',
                        background: selectedImageIndex === idx ? 'rgba(245, 158, 11, 0.2)' : 'rgba(15, 23, 42, 0.5)',
                        border: selectedImageIndex === idx ? '1px solid #f59e0b' : '1px solid rgba(51, 65, 85, 0.5)',
                        color: '#f8fafc',
                        fontSize: '12px',
                        cursor: 'pointer',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      <Camera size={14} />
                      <span>{img.filename}</span>
                      {img.mask_filename && (
                        <span style={{ fontSize: '10px', background: '#10b981', color: '#0f172a', padding: '1px 5px', borderRadius: '3px', fontWeight: 700 }}>
                          GT Mask
                        </span>
                      )}
                    </button>
                  ))}
                </div>

                {/* Side-by-Side Image vs Mask Display */}
                {demoData.phase1_quality.images[selectedImageIndex] && (() => {
                  const currImg = demoData.phase1_quality.images[selectedImageIndex];
                  const matchingDets = demoData.phase5_deterioration.detections.filter(
                    (d) => d.image_id === currImg.id || d.image_filename === currImg.filename
                  );

                  return (
                    <div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px', marginBottom: '16px' }}>
                        {/* Raw Image */}
                        <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(51, 65, 85, 0.6)', borderRadius: '8px', overflow: 'hidden' }}>
                          <div style={{ padding: '10px 14px', background: 'rgba(30, 41, 59, 0.8)', borderBottom: '1px solid rgba(51, 65, 85, 0.5)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontSize: '12px', fontWeight: 600, color: '#f1f5f9' }}>1. Raw Optical DeepCrack Image</span>
                            <span style={{ fontSize: '11px', color: '#94a3b8' }}>{currImg.filename}</span>
                          </div>
                          <div style={{ height: '320px', background: '#0b1120', position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <img
                              src={currImg.download_url}
                              alt={currImg.filename}
                              style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
                            />
                            {matchingDets.map((d, dIdx) => (
                              <div
                                key={d.id || dIdx}
                                style={{
                                  position: 'absolute',
                                  border: '2px solid #ef4444',
                                  backgroundColor: 'rgba(239, 68, 68, 0.15)',
                                  pointerEvents: 'none',
                                  left: '20%',
                                  top: '25%',
                                  width: '50%',
                                  height: '40%',
                                }}
                              >
                                <span style={{ position: 'absolute', top: '-18px', left: '0', background: '#ef4444', color: '#ffffff', fontSize: '10px', padding: '1px 5px', fontWeight: 700, borderRadius: '2px' }}>
                                  {d.damage_type} ({Math.round(d.confidence * 100)}%)
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>

                        {/* Ground-Truth Binary Mask */}
                        <div style={{ background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(51, 65, 85, 0.6)', borderRadius: '8px', overflow: 'hidden' }}>
                          <div style={{ padding: '10px 14px', background: 'rgba(30, 41, 59, 0.8)', borderBottom: '1px solid rgba(51, 65, 85, 0.5)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontSize: '12px', fontWeight: 600, color: '#f1f5f9' }}>2. Real DeepCrack Ground-Truth Mask</span>
                            <span style={{ fontSize: '11px', color: '#10b981', fontWeight: 600 }}>{currImg.mask_filename || 'No Mask'}</span>
                          </div>
                          <div style={{ height: '320px', background: '#000000', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            {currImg.mask_url ? (
                              <img
                                src={currImg.mask_url}
                                alt={`Mask for ${currImg.filename}`}
                                style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain', filter: 'brightness(1.2)' }}
                              />
                            ) : (
                              <div style={{ color: '#64748b', fontSize: '13px' }}>Mask not available for this image</div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Associated Details Card */}
                      <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '14px 16px', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.5)' }}>
                        <div style={{ fontSize: '13px', fontWeight: 600, color: '#e2e8f0', marginBottom: '8px' }}>
                          Research Defect Traceability:
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px', fontSize: '12px', color: '#94a3b8' }}>
                          <div>Defect Category: <strong style={{ color: '#cbd5e1' }}>Crack (Structural Discontinuity)</strong></div>
                          <div>Associated Substrate: <strong style={{ color: '#cbd5e1' }}>{demoData.phase4_materials.primary_material}</strong></div>
                          <div>Total Detections in Survey: <strong style={{ color: '#cbd5e1' }}>{demoData.phase5_deterioration.total_detections}</strong></div>
                          <div>Annotation Source: <strong style={{ color: '#10b981' }}>DeepCrack Benchmark Ground Truth</strong></div>
                        </div>
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}

            {/* PHASE 6: 2D-TO-3D DAMAGE MAPPING */}
            {activePhase === 6 && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div>
                    <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                      Phase 6: 2D-to-3D Damage Mapping (Spatial Localization)
                    </h3>
                    <p style={{ color: '#94a3b8', fontSize: '13px', margin: '4px 0 0' }}>
                      Projects 2D image detections through calibrated pinhole camera rays into the 3D surface mesh with reprojection residual validation.
                    </p>
                  </div>
                  <span style={{ fontSize: '12px', color: '#38bdf8', background: 'rgba(56, 189, 248, 0.1)', padding: '4px 10px', borderRadius: '4px', border: '1px solid rgba(56, 189, 248, 0.3)' }}>
                    {demoData.phase6_damage_mapping.total_mapped} Spatial Points Mapped
                  </span>
                </div>

                {/* 3D Viewport with Damage Markers */}
                <div style={{ height: '420px', borderRadius: '8px', overflow: 'hidden', border: '1px solid rgba(51, 65, 85, 0.8)', marginBottom: '16px', position: 'relative' }}>
                  <ModelViewer3D
                    modelUrl={demoData.phase3_reconstruction.ply_url}
                    isDemo={true}
                    pointCount={demoData.phase3_reconstruction.point_count}
                    vertexCount={demoData.phase3_reconstruction.mesh_vertex_count}
                    triangleCount={demoData.phase3_reconstruction.mesh_face_count}
                    showDamageMarkers={true}
                    selectedMappingId={selectedMappingId}
                    onSelectDamagePoint={(item) => setSelectedMappingId(item.id)}
                  />
                </div>

                {/* Mappings Table */}
                <div style={{ background: 'rgba(15, 23, 42, 0.6)', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.5)', overflow: 'hidden' }}>
                  <div style={{ padding: '12px 16px', background: 'rgba(30, 41, 59, 0.8)', borderBottom: '1px solid rgba(51, 65, 85, 0.5)', fontSize: '13px', fontWeight: 600, color: '#f1f5f9' }}>
                    Spatially Mapped Defect Coordinates (Survey T1)
                  </div>
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                      <thead>
                        <tr style={{ borderBottom: '1px solid rgba(51, 65, 85, 0.4)', color: '#94a3b8' }}>
                          <th style={{ padding: '10px 14px' }}>Image</th>
                          <th style={{ padding: '10px 14px' }}>Defect Type</th>
                          <th style={{ padding: '10px 14px' }}>Material</th>
                          <th style={{ padding: '10px 14px' }}>3D Coordinates (X, Y, Z)</th>
                          <th style={{ padding: '10px 14px' }}>Status</th>
                          <th style={{ padding: '10px 14px' }}>Reproj. Error</th>
                        </tr>
                      </thead>
                      <tbody>
                        {demoData.phase6_damage_mapping.mappings.map((m) => {
                          const isSel = selectedMappingId === m.id;
                          return (
                            <tr
                              key={m.id}
                              onClick={() => setSelectedMappingId(m.id)}
                              style={{
                                borderBottom: '1px solid rgba(51, 65, 85, 0.2)',
                                cursor: 'pointer',
                                background: isSel ? 'rgba(245, 158, 11, 0.15)' : 'transparent',
                              }}
                            >
                              <td style={{ padding: '10px 14px', color: '#f1f5f9' }}>{m.image_filename}</td>
                              <td style={{ padding: '10px 14px', color: '#fbbf24', textTransform: 'capitalize' }}>{m.damage_type}</td>
                              <td style={{ padding: '10px 14px', color: '#94a3b8', textTransform: 'capitalize' }}>{m.material_class || 'sandstone'}</td>
                              <td style={{ padding: '10px 14px', fontFamily: 'monospace', color: '#cbd5e1' }}>
                                {m.world_point ? `(${m.world_point.x.toFixed(3)}, ${m.world_point.y.toFixed(3)}, ${m.world_point.z.toFixed(3)})` : '—'}
                              </td>
                              <td style={{ padding: '10px 14px' }}>
                                <span style={{ color: '#10b981', background: 'rgba(16, 185, 129, 0.1)', padding: '2px 6px', borderRadius: '4px', fontSize: '11px', fontWeight: 600 }}>
                                  {m.mapping_status}
                                </span>
                              </td>
                              <td style={{ padding: '10px 14px', color: '#94a3b8' }}>
                                {m.reprojection_error_px != null ? `${m.reprojection_error_px} px` : '—'}
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

            {/* PHASE 7: MULTI-TEMPORAL MONITORING */}
            {activePhase === 7 && (
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <div>
                    <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                      Phase 7: Multi-Temporal Monitoring & Change Tracking
                    </h3>
                    <p style={{ color: '#94a3b8', fontSize: '13px', margin: '4px 0 0' }}>
                      Rigid ICP point-cloud co-registration across epochs (T1 baseline vs T2 follow-up) and automated defect evolution classification.
                    </p>
                  </div>
                  <span style={{ fontSize: '12px', color: '#a855f7', background: 'rgba(168, 85, 247, 0.1)', padding: '4px 10px', borderRadius: '4px', border: '1px solid rgba(168, 85, 247, 0.3)' }}>
                    ICP Co-Registration: {demoData.phase7_temporal.alignment_status}
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '20px' }}>
                  <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.5)' }}>
                    <div style={{ fontSize: '11px', color: '#94a3b8' }}>Baseline Epoch (T1)</div>
                    <div style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc', marginTop: '4px' }}>DEMO-SRV-T1</div>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>Initial Inspection</div>
                  </div>

                  <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.5)' }}>
                    <div style={{ fontSize: '11px', color: '#94a3b8' }}>Follow-up Epoch (T2)</div>
                    <div style={{ fontSize: '15px', fontWeight: 700, color: '#f8fafc', marginTop: '4px' }}>DEMO-SRV-T2</div>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>Post-weathering Epoch</div>
                  </div>

                  <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.5)' }}>
                    <div style={{ fontSize: '11px', color: '#94a3b8' }}>Alignment RMSE Residual</div>
                    <div style={{ fontSize: '18px', fontWeight: 700, color: '#10b981', marginTop: '4px' }}>
                      {demoData.phase7_temporal.alignment_rmse ? `${demoData.phase7_temporal.alignment_rmse.toFixed(4)} m` : '0.0000 m (Local)'}
                    </div>
                  </div>

                  <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '14px', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.5)' }}>
                    <div style={{ fontSize: '11px', color: '#94a3b8' }}>Total Change Records</div>
                    <div style={{ fontSize: '18px', fontWeight: 700, color: '#38bdf8', marginTop: '4px' }}>
                      {demoData.phase7_temporal.total_changes} Events
                    </div>
                  </div>
                </div>

                {/* Change Breakdown & Evolution Cards */}
                <div style={{ background: 'rgba(15, 23, 42, 0.6)', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.5)', overflow: 'hidden' }}>
                  <div style={{ padding: '12px 16px', background: 'rgba(30, 41, 59, 0.8)', borderBottom: '1px solid rgba(51, 65, 85, 0.5)', fontSize: '13px', fontWeight: 600, color: '#f1f5f9' }}>
                    Defect Evolution Classification Across Epochs
                  </div>
                  <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {demoData.phase7_temporal.changes.map((c, idx) => {
                      let tagColor = '#38bdf8';
                      let tagBg = 'rgba(56, 189, 248, 0.1)';
                      if (c.change_type === 'PERSISTING') {
                        tagColor = '#f59e0b';
                        tagBg = 'rgba(245, 158, 11, 0.1)';
                      } else if (c.change_type === 'NEW') {
                        tagColor = '#ef4444';
                        tagBg = 'rgba(239, 68, 68, 0.1)';
                      } else if (c.change_type.includes('RESOLVED')) {
                        tagColor = '#10b981';
                        tagBg = 'rgba(16, 185, 129, 0.1)';
                      }

                      return (
                        <div
                          key={idx}
                          style={{
                            background: 'rgba(30, 41, 59, 0.4)',
                            border: '1px solid rgba(51, 65, 85, 0.4)',
                            borderRadius: '8px',
                            padding: '12px 16px',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            flexWrap: 'wrap',
                            gap: '10px',
                          }}
                        >
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <span style={{ fontSize: '12px', fontWeight: 700, color: tagColor, background: tagBg, padding: '2px 8px', borderRadius: '4px' }}>
                                {c.change_type}
                              </span>
                              <span style={{ fontSize: '13px', fontWeight: 600, color: '#f1f5f9', textTransform: 'capitalize' }}>
                                {c.damage_type} ({c.material_class || 'sandstone'})
                              </span>
                            </div>
                            <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>
                              {c.notes || 'Temporal evolution state recorded by spatial proximity matching.'}
                            </div>
                          </div>

                          <div style={{ textAlign: 'right', fontSize: '12px', color: '#cbd5e1' }}>
                            <div>Spatial Distance: <strong>{c.spatial_distance_m != null ? `${c.spatial_distance_m.toFixed(3)} m` : '—'}</strong></div>
                            <div style={{ fontSize: '11px', color: '#64748b' }}>Scale: {c.scale_status}</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Final Summary Card & Data Provenance */}
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              borderRadius: '12px',
              padding: '24px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
              <ShieldCheck size={22} style={{ color: '#3b82f6' }} />
              <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                Academic Pipeline Summary & Data Provenance
              </h3>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px', marginBottom: '20px' }}>
              <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.4)' }}>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#38bdf8', marginBottom: '10px' }}>
                  Complete 7-Phase Execution Chain
                </div>
                <ul style={{ margin: 0, paddingLeft: '18px', color: '#cbd5e1', fontSize: '12px', lineHeight: '1.8' }}>
                  {demoData.summary.key_findings.map((kf, i) => (
                    <li key={i}>{kf}</li>
                  ))}
                </ul>
              </div>

              <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: '16px', borderRadius: '8px', border: '1px solid rgba(51, 65, 85, 0.4)' }}>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#f59e0b', marginBottom: '10px' }}>
                  Data Provenance Matrix
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(51, 65, 85, 0.3)', paddingBottom: '4px' }}>
                    <span style={{ color: '#94a3b8' }}>Optical Imagery:</span>
                    <span style={{ color: '#10b981', fontWeight: 600 }}>{demoData.provenance.image_data}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(51, 65, 85, 0.3)', paddingBottom: '4px' }}>
                    <span style={{ color: '#94a3b8' }}>Deterioration Masks:</span>
                    <span style={{ color: '#10b981', fontWeight: 600 }}>{demoData.provenance.image_masks}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(51, 65, 85, 0.3)', paddingBottom: '4px' }}>
                    <span style={{ color: '#94a3b8' }}>3D Photogrammetry:</span>
                    <span style={{ color: '#f59e0b', fontWeight: 600 }}>{demoData.provenance.photogrammetry_3d}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid rgba(51, 65, 85, 0.3)', paddingBottom: '4px' }}>
                    <span style={{ color: '#94a3b8' }}>Temporal Alignment:</span>
                    <span style={{ color: '#f59e0b', fontWeight: 600 }}>{demoData.provenance.temporal_alignment}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', paddingTop: '2px' }}>
                    <span style={{ color: '#94a3b8' }}>Classification:</span>
                    <span style={{ color: '#38bdf8', fontWeight: 700 }}>{demoData.provenance.overall_classification}</span>
                  </div>
                </div>
              </div>
            </div>

            <div style={{ fontSize: '12px', color: '#94a3b8', fontStyle: 'italic', borderTop: '1px solid rgba(51, 65, 85, 0.4)', paddingTop: '12px' }}>
              {demoData.summary.safety_statement}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
export default IntegratedDemoPage;
