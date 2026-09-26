import React from 'react';
import {
  Box,
  Layers,
  Flame,
  Crosshair,
  History,
  ShieldCheck,
  AlertTriangle,
  Lightbulb,
  FileText,
  Clock,
  ArrowRight,
} from 'lucide-react';
import type { NavTab } from '../components/layout/Sidebar';

interface PipelinePlaceholderPageProps {
  tab: NavTab;
  onNavigateToSurveys: () => void;
}

interface PhaseDetail {
  title: string;
  phase: string;
  icon: any;
  concept: string;
  description: string;
  inputs: string[];
  plannedTechniques: string[];
  formulaOrArchitecture: string;
  researchGoal: string;
}

const PHASE_DETAILS: Record<string, PhaseDetail> = {
  viewer: {
    title: '3D Photogrammetric Model Viewer',
    phase: 'Phase 3 Roadmap',
    icon: Box,
    concept: 'Multi-View 3D Spatial Representation',
    description:
      'Interactive WebGL/Three.js 3D viewer rendering sparse and dense point clouds and textured meshes produced by the COLMAP / Open3D pipeline.',
    inputs: ['Approved quality survey imagery', 'Camera intrinsics & poses (SfM)', 'Dense point cloud (.ply/.pcd)'],
    plannedTechniques: ['Structure-from-Motion (SfM)', 'Multi-View Stereo (MVS)', 'Open3D point cloud filtering', 'Three.js / Potree WebGL rendering'],
    formulaOrArchitecture: 'Reprojection Error: E(P, C) = ∑ ||x_{ij} - π(C_i, P_j)||^2',
    researchGoal: 'Provide a metric 3D digital twin of the heritage structure allowing spatial navigation and damage overlay.',
  },
  materials: {
    title: 'Modular ML Material Classification',
    phase: 'Phase 4 Roadmap',
    icon: Layers,
    concept: 'Substrate Identification for Vulnerability Context',
    description:
      'Transfer-learning classifier identifying construction materials (sandstone, granite, brick, lime mortar) to assess chemical and weathering vulnerability.',
    inputs: ['High-resolution 2D surface patches', 'Configurable material taxonomy'],
    plannedTechniques: ['PyTorch MobileNetV3 / ResNet-18 lightweight backbone', 'Softmax class probabilities', 'CPU-optimized inference'],
    formulaOrArchitecture: 'P(material_k | patch) = softmax(W^T f(patch) + b)',
    researchGoal: 'Associate structural deterioration with the substrate material rather than treating defects in isolation.',
  },
  deterioration: {
    title: 'Modular Deterioration Detection & Segmentation',
    phase: 'Phase 5 Roadmap',
    icon: Flame,
    concept: 'Multi-Class Surface Defect Detection',
    description:
      'Computer vision detection of cracks, erosion/material loss, spalling, discoloration, and biological growth.',
    inputs: ['Survey imagery passing optical quality checks', 'Configurable deterioration classes'],
    plannedTechniques: ['Lightweight YOLO / Mask R-CNN transfer learning', 'Binary mask generation', 'Confidence thresholding'],
    formulaOrArchitecture: 'Detection: { damage_type, confidence, bbox, segmentation_mask }',
    researchGoal: 'Automate visual inspection and extract precise bounding coordinates for 3D projection.',
  },
  'damage-mapping': {
    title: '2D → 3D Damage Mapping Layer',
    phase: 'Phase 6 Roadmap',
    icon: Crosshair,
    concept: 'Spatial Projection from Image Pixels to Metric 3D Geometry',
    description:
      'Ray-casting and pose inversion associating 2D detected defects with reconstructed 3D surface point clusters and calculating physical dimensions.',
    inputs: ['2D detection bounding boxes/masks', 'Camera extrinsic matrices [R|t]', '3D dense point cloud'],
    plannedTechniques: ['Camera ray projection: X = C + λ R^T K^{-1} [u, v, 1]^T', 'KD-Tree nearest surface search', 'Metric surface area estimation'],
    formulaOrArchitecture: 'Unified Record: Material + Damage + 3D Coordinates (X, Y, Z) + Severity + Survey ID',
    researchGoal: 'Transform 2D image coordinates into real-world millimeter/centimeter spatial measurements.',
  },
  temporal: {
    title: 'Multi-Temporal Monitoring & Change Detection',
    phase: 'Phase 7 Roadmap',
    icon: History,
    concept: 'Epoch-to-Epoch Comparative Progression Tracking',
    description:
      'Multi-survey alignment and point cloud distance calculations to quantify crack propagation, erosion depth, and volumetric material loss over time.',
    inputs: ['Baseline Survey Epoch 3D Model', 'Current Survey Epoch 3D Model'],
    plannedTechniques: ['Iterative Closest Point (ICP) co-registration', 'Multiscale Model-to-Model Cloud Comparison (M3C2)', 'Differential distance histograms'],
    formulaOrArchitecture: 'Δ_t = ||P_{current}(t_2) - P_{baseline}(t_1)||',
    researchGoal: 'Measure the true rate of deterioration between recurring inspections.',
  },
  reliability: {
    title: 'Scientific Reliability & Uncertainty Assessment',
    phase: 'Phase 8 Roadmap',
    icon: ShieldCheck,
    concept: 'Measurement Uncertainty Quantification',
    description:
      'Mathematical scoring module computing confidence bounds by combining image quality scores, ML inference probabilities, and photogrammetric registration residuals.',
    inputs: ['OpenCV image quality score', 'ML detection confidence', 'Registration RMSE', 'SfM reprojection error'],
    plannedTechniques: ['Multi-factor weighted reliability index R ∈ [0.0, 1.0]', 'Low/Medium/High confidence thresholds', 'Transparent audit trail'],
    formulaOrArchitecture: 'R = w_1 Q_{image} + w_2 C_{ml} + w_3 (1 - E_{reg}) + w_4 (1 - E_{reproj})',
    researchGoal: 'Distinguish verifiable physical deterioration from imaging noise and algorithmic uncertainty.',
  },
  risk: {
    title: 'Condition & Risk Prioritization Matrix',
    phase: 'Phase 8 Roadmap',
    icon: AlertTriangle,
    concept: 'Vulnerability-Weighted Urgency Categorization',
    description:
      'Transparent rule-based risk prioritization combining substrate vulnerability, defect magnitude, progression rate, and environmental exposure.',
    inputs: ['Material type (e.g. vulnerable sandstone vs. durable granite)', 'Defect severity & rate', 'Reliability score'],
    plannedTechniques: ['Multi-criteria risk scoring', 'Urgency tiers: High Priority, Moderate Priority, Low Priority'],
    formulaOrArchitecture: 'Risk Score = f(Substrate Vulnerability, Defect Severity, Rate of Change, Reliability)',
    researchGoal: 'Provide conservation teams with an actionable triage priority list for urgent interventions.',
  },
  recommendations: {
    title: 'Rule-Based Conservation Recommendations',
    phase: 'Phase 8 Roadmap',
    icon: Lightbulb,
    concept: 'Actionable Conservation Decision Support',
    description:
      'Automated generation of specific monitoring actions (e.g., closer inspection intervals, non-destructive depth testing, additional angular imagery).',
    inputs: ['Risk priority classification', 'Measurement reliability bounds', 'Image coverage analysis'],
    plannedTechniques: ['Transparent rule engine based on ICOMOS guidelines', 'Strict non-replacement of licensed structural engineers'],
    formulaOrArchitecture: 'Rule: IF Risk == High AND Reliability == High THEN Action = "Schedule expert inspection within 30 days"',
    researchGoal: 'Bridge computational analysis with practical heritage management protocols.',
  },
  reports: {
    title: 'Automated Academic & Technical Reports',
    phase: 'Phase 9 Roadmap',
    icon: FileText,
    concept: 'Comprehensive Inspection Dossier Generation',
    description:
      'Exportable PDF reports compiling site profiles, survey epoch timelines, optical quality diagnostics, 3D metrics, and conservation recommendations.',
    inputs: ['All survey records, detections, and risk assessments for a target heritage site'],
    plannedTechniques: ['Structured PDF generation', 'High-resolution visual damage figures', 'Academic citation ready format'],
    formulaOrArchitecture: 'Dossier Output: Executive Summary + 3D Metrics + Temporal Comparison + Risk Matrix + Recommendations',
    researchGoal: 'Generate publication-ready dossiers and archival inspection reports for heritage authorities.',
  },
};

export const PipelinePlaceholderPage: React.FC<PipelinePlaceholderPageProps> = ({
  tab,
  onNavigateToSurveys,
}) => {
  const info = PHASE_DETAILS[tab] || {
    title: 'Pipeline Module',
    phase: 'Planned Phase',
    icon: Box,
    concept: 'Core Research Component',
    description: 'This module is scheduled for implementation in upcoming development phases.',
    inputs: [],
    plannedTechniques: [],
    formulaOrArchitecture: '',
    researchGoal: 'Advancing heritage monitoring capabilities.',
  };

  const Icon = info.icon;

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <div className="flex items-center gap-2">
            <span className="navbar-badge">{info.phase}</span>
            <span className="text-xs text-amber-400 font-semibold">{info.concept}</span>
          </div>
          <h2 className="page-title mt-1">{info.title}</h2>
          <p className="page-description">{info.description}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left Card: Input Pipeline & Methodology */}
        <div className="card">
          <div className="card-header">
            <div className="flex items-center gap-2">
              <Icon size={18} className="text-amber-400" />
              <h3 className="card-title">Technical Pipeline Specification</h3>
            </div>
          </div>
          <div className="card-body space-y-4">
            <div>
              <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Upstream Inputs (From Phase 1 & 2)
              </h4>
              <ul className="space-y-1.5 text-xs text-slate-400">
                {info.inputs.map((inp, idx) => (
                  <li key={idx} className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                    <span>{inp}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Algorithms & Libraries
              </h4>
              <ul className="space-y-1.5 text-xs text-slate-400">
                {info.plannedTechniques.map((tech, idx) => (
                  <li key={idx} className="flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-sky-400" />
                    <span>{tech}</span>
                  </li>
                ))}
              </ul>
            </div>

            {info.formulaOrArchitecture && (
              <div>
                <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                  Governing Formulation / Architecture
                </h4>
                <div className="p-3 bg-slate-900 rounded font-mono text-xs text-amber-300 border border-slate-800">
                  {info.formulaOrArchitecture}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Card: Research Significance & Phase 1 Data Source */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title">Research Contribution & Continuity</h3>
          </div>
          <div className="card-body space-y-4">
            <div className="p-3 bg-slate-900/60 rounded border border-slate-800 text-xs space-y-2">
              <p className="font-semibold text-slate-200">Scientific Objective:</p>
              <p className="text-slate-400 leading-relaxed">{info.researchGoal}</p>
            </div>

            <div className="p-3 bg-slate-900/60 rounded border border-slate-800 text-xs space-y-2">
              <div className="flex items-center gap-1.5 text-slate-200 font-semibold">
                <Clock size={14} className="text-sky-400" />
                <span>Phase 1 Readiness</span>
              </div>
              <p className="text-slate-400 leading-relaxed">
                The database schema, REST API endpoints, image storage abstraction, and OpenCV optical validation created in Phase 1 provide the exact inputs needed for this module.
              </p>
            </div>

            <div className="pt-2">
              <button onClick={onNavigateToSurveys} className="btn-primary text-xs w-full justify-center">
                <span>Manage Phase 1 Surveys & Imagery</span>
                <ArrowRight size={13} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
