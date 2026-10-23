import React from 'react';
import {
  Landmark,
  FolderKanban,
  UploadCloud,
  CheckSquare,
  Box,
  Layers,
  Flame,
  Crosshair,
  History,
  FileText,
  ChevronRight,
  CheckCircle2,
} from 'lucide-react';
import type {
  Site,
  Survey,
  Reconstruction,
  SurveyMaterialAnalysisSummary,
  SurveyDeteriorationAnalysisSummary,
  Survey3DMappingSummary,
  TemporalComparisonSummary,
} from '../../types';

export interface SurveyWorkflowBarProps {
  site?: Site | null;
  survey?: Survey | null;
  reconstruction?: Reconstruction | null;
  materialSummary?: SurveyMaterialAnalysisSummary | null;
  deteriorationSummary?: SurveyDeteriorationAnalysisSummary | null;
  mappingSummary?: Survey3DMappingSummary | null;
  comparison?: TemporalComparisonSummary | null;
  activeStep?: string;
  onNavigateStep?: (stepId: string) => void;
}

export const SurveyWorkflowBar: React.FC<SurveyWorkflowBarProps> = ({
  site,
  survey,
  reconstruction,
  materialSummary,
  deteriorationSummary,
  mappingSummary,
  comparison,
  activeStep,
  onNavigateStep,
}) => {
  // Determine completion of each step
  const hasSite = Boolean(site?.id);
  const hasSurvey = Boolean(survey?.id);
  const hasImages = Boolean(survey && (survey.image_count ?? 0) > 0);
  const hasQuality = Boolean(survey && survey.status !== 'created' && (survey.image_count ?? 0) > 0);
  const hasReconstruction = Boolean(reconstruction && reconstruction.status === 'completed');
  const hasMaterials = Boolean(materialSummary && (materialSummary.analyzed_images ?? 0) > 0);
  const hasDeterioration = Boolean(deteriorationSummary && (deteriorationSummary.total_detections ?? 0) >= 0 && deteriorationSummary.analyzed_images > 0);
  const hasMapping = Boolean(mappingSummary && (mappingSummary.mapped_detections ?? 0) > 0);
  const hasTemporal = Boolean(comparison && comparison.id);
  const hasReport = hasSurvey && (hasReconstruction || hasDeterioration);


  const steps = [
    { id: 'site', label: '1. Select Site', icon: Landmark, completed: hasSite, navTab: 'sites' },
    { id: 'survey', label: '2. Create Survey', icon: FolderKanban, completed: hasSurvey, navTab: 'surveys' },
    { id: 'images', label: '3. Upload Images', icon: UploadCloud, completed: hasImages, navTab: 'surveys' },
    { id: 'quality', label: '4. Check Quality', icon: CheckSquare, completed: hasQuality, navTab: 'quality' },
    { id: 'reconstruction', label: '5. Reconstruct 3D', icon: Box, completed: hasReconstruction, navTab: 'viewer' },
    { id: 'materials', label: '6. Analyze Materials', icon: Layers, completed: hasMaterials, navTab: 'materials' },
    { id: 'deterioration', label: '7. Detect Defects', icon: Flame, completed: hasDeterioration, navTab: 'deterioration' },
    { id: 'mapping', label: '8. Map Damage', icon: Crosshair, completed: hasMapping, navTab: 'damage-mapping' },
    { id: 'temporal', label: '9. Compare Surveys', icon: History, completed: hasTemporal, navTab: 'temporal' },
    { id: 'report', label: '10. Generate Report', icon: FileText, completed: hasReport, navTab: 'reports' },
  ];

  return (
    <div
      style={{
        background: 'rgba(15, 23, 42, 0.75)',
        border: '1px solid rgba(51, 65, 85, 0.6)',
        borderRadius: '10px',
        padding: '10px 14px',
        marginBottom: '20px',
        backdropFilter: 'blur(8px)',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '8px',
          borderBottom: '1px solid rgba(51, 65, 85, 0.4)',
          paddingBottom: '6px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              fontSize: '10px',
              fontWeight: 800,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: '#f59e0b',
              background: 'rgba(245, 158, 11, 0.12)',
              padding: '2px 8px',
              borderRadius: '4px',
              border: '1px solid rgba(245, 158, 11, 0.25)',
            }}
          >
            Survey Workflow Pipeline
          </span>
          <span style={{ fontSize: '11px', color: '#94a3b8' }}>
            Phases 1–7 Integrated Non-Destructive Conservation Assessment
          </span>
        </div>
        <div style={{ fontSize: '11px', color: '#64748b' }}>
          {steps.filter((s) => s.completed).length} of 10 steps ready
        </div>
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          overflowX: 'auto',
          gap: '4px',
          paddingBottom: '4px',
          scrollbarWidth: 'thin',
        }}
      >
        {steps.map((step, idx) => {
          const Icon = step.icon;
          const isActive = activeStep === step.id;
          const isDone = step.completed;

          return (
            <React.Fragment key={step.id}>
              <button
                onClick={() => onNavigateStep && onNavigateStep(step.navTab)}
                title={step.label}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '5px 9px',
                  borderRadius: '6px',
                  background: isActive
                    ? 'rgba(245, 158, 11, 0.2)'
                    : isDone
                    ? 'rgba(16, 185, 129, 0.1)'
                    : 'rgba(30, 41, 59, 0.5)',
                  border: isActive
                    ? '1px solid #f59e0b'
                    : isDone
                    ? '1px solid rgba(16, 185, 129, 0.35)'
                    : '1px solid rgba(51, 65, 85, 0.5)',
                  color: isActive
                    ? '#fde68a'
                    : isDone
                    ? '#6ee7b7'
                    : '#94a3b8',
                  fontSize: '11px',
                  fontWeight: isActive ? 700 : 600,
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.15s ease',
                  flexShrink: 0,
                }}
              >
                {isDone ? (
                  <CheckCircle2 size={12} className="text-emerald-400" />
                ) : (
                  <Icon size={12} className={isActive ? 'text-amber-400' : 'text-slate-400'} />
                )}
                <span>{step.label}</span>
              </button>
              {idx < steps.length - 1 && (
                <ChevronRight size={12} style={{ color: '#475569', flexShrink: 0 }} />
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
