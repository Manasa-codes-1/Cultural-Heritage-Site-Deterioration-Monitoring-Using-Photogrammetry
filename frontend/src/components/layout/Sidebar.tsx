import React from 'react';
import {
  LayoutDashboard,
  Landmark,
  FolderKanban,
  Activity,
  FileText,
  PlayCircle,
  ShieldCheck,
} from 'lucide-react';

export type NavTab =
  | 'overview'
  | 'sites'
  | 'surveys'
  | 'monitoring'
  | 'reports'
  | 'integrated-demo'
  | 'quality'
  | 'viewer'
  | 'materials'
  | 'deterioration'
  | 'damage-mapping'
  | 'temporal';

interface SidebarProps {
  currentTab: NavTab;
  onSelectTab: (tab: NavTab) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, onSelectTab }) => {
  const mainNav = [
    { id: 'overview', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'sites', label: 'Sites', icon: Landmark },
    { id: 'surveys', label: 'Surveys', icon: FolderKanban },
    { id: 'monitoring', label: 'Monitoring', icon: Activity, badge: '3D Workspace' },
    { id: 'reports', label: 'Reports', icon: FileText },
  ];

  return (
    <aside className="app-sidebar">
      <div className="sidebar-group">
        <h3 className="sidebar-group-title">Conservation Platform</h3>
        <nav className="sidebar-nav">
          {mainNav.map((item) => {
            const Icon = item.icon;
            const active = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id as NavTab)}
                className={`sidebar-nav-item ${active ? 'sidebar-nav-active' : ''}`}
              >
                <Icon size={18} className={active ? 'text-amber-400' : 'text-slate-400'} />
                <span className="sidebar-label">{item.label}</span>
                {item.badge && (
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 600,
                      color: active ? '#fde68a' : '#94a3b8',
                      background: active ? 'rgba(245, 158, 11, 0.2)' : 'rgba(51, 65, 85, 0.4)',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      marginLeft: 'auto',
                    }}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      <div style={{ marginTop: 'auto', padding: '16px 8px 8px' }}>
        <button
          onClick={() => onSelectTab('integrated-demo')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            width: '100%',
            padding: '9px 12px',
            borderRadius: '8px',
            background: currentTab === 'integrated-demo'
              ? 'linear-gradient(135deg, rgba(245, 158, 11, 0.25), rgba(217, 119, 6, 0.15))'
              : 'rgba(245, 158, 11, 0.08)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            color: '#fef3c7',
            fontSize: '12px',
            fontWeight: 600,
            cursor: 'pointer',
            textAlign: 'left',
          }}
        >
          <PlayCircle size={16} className="text-amber-400" />
          <span>Integrated Demo</span>
          <span
            style={{
              marginLeft: 'auto',
              fontSize: '10px',
              background: '#f59e0b',
              color: '#0f172a',
              padding: '1px 5px',
              borderRadius: '3px',
              fontWeight: 700,
            }}
          >
            Demo
          </span>
        </button>

        <div className="sidebar-footer" style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid rgba(51, 65, 85, 0.5)' }}>
          <div className="sidebar-paper-note">
            <p className="paper-note-title" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <ShieldCheck size={12} className="text-amber-400" />
              Integrated Pipeline
            </p>
            <p className="paper-note-desc" style={{ fontSize: '11px', lineHeight: '1.4' }}>
              Material → Deterioration → 3D → Change Tracking
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
};
