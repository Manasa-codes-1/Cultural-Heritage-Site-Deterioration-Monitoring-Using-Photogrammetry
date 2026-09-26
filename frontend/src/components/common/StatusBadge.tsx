import React from 'react';

interface StatusBadgeProps {
  status: string | null | undefined;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  if (!status) return null;

  const normalized = status.toLowerCase();

  let bgClass = 'bg-slate-800 text-slate-300 border-slate-700';
  let dotClass = 'bg-slate-400';

  if (
    normalized === 'pass' ||
    normalized === 'healthy' ||
    normalized === 'completed' ||
    normalized === 'low priority' ||
    normalized === 'good' ||
    normalized === 'ready' ||
    normalized === 'well_connected'
  ) {
    bgClass = 'bg-emerald-950/60 text-emerald-300 border-emerald-800/80';
    dotClass = 'bg-emerald-400';
  } else if (
    normalized === 'warning' ||
    normalized === 'moderate priority' ||
    normalized === 'degraded' ||
    normalized === 'ready_with_warnings' ||
    normalized === 'weakly_connected'
  ) {
    bgClass = 'bg-amber-950/60 text-amber-300 border-amber-800/80';
    dotClass = 'bg-amber-400';
  } else if (
    normalized === 'fail' ||
    normalized === 'high priority' ||
    normalized === 'failed' ||
    normalized === 'poor' ||
    normalized === 'insufficient_features' ||
    normalized === 'insufficient_image_connectivity' ||
    normalized === 'recapture_required' ||
    normalized === 'isolated'
  ) {
    bgClass = 'bg-rose-950/60 text-rose-300 border-rose-800/80';
    dotClass = 'bg-rose-400';
  } else if (normalized === 'pending' || normalized === 'created' || normalized === 'images_uploaded') {
    bgClass = 'bg-sky-950/60 text-sky-300 border-sky-800/80';
    dotClass = 'bg-sky-400';
  }

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border ${bgClass}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotClass}`} />
      <span className="capitalize">{status.replace(/_/g, ' ')}</span>
    </span>
  );
};
