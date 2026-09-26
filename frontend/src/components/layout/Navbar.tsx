import React, { useEffect, useState } from 'react';
import { Landmark, Activity, Server, Cpu, Database } from 'lucide-react';
import type { HealthResponse } from '../../types';
import { api } from '../../api/client';

export const Navbar: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const check = async () => {
      try {
        const data = await api.getHealth();
        setHealth(data);
      } catch (err) {
        setHealth(null);
      } finally {
        setLoading(false);
      }
    };
    check();
    const interval = setInterval(check, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="app-navbar">
      <div className="navbar-left">
        <div className="navbar-brand-icon">
          <Landmark size={22} className="text-amber-400" />
        </div>
        <div>
          <div className="navbar-title-row">
            <h1 className="navbar-title">Heritage Photogrammetry Monitor</h1>
            <span className="navbar-badge">Research Lab</span>
          </div>
          <p className="navbar-subtitle">Material-Aware Cultural Heritage Deterioration System</p>
        </div>
      </div>

      <div className="navbar-right">
        {loading ? (
          <div className="system-pill">
            <Activity size={14} className="animate-spin text-sky-400" />
            <span>Connecting...</span>
          </div>
        ) : health ? (
          <>
            <div className="system-pill" title={`Python ${health.system_info.python_version}`}>
              <Server size={13} className="text-emerald-400" />
              <span>API: v{health.version}</span>
            </div>

            <div className="system-pill" title={health.system_info.colmap_available ? "COLMAP Native" : "Mock Photogrammetry Engine Active"}>
              <Cpu size={13} className={health.system_info.colmap_available ? "text-emerald-400" : "text-amber-400"} />
              <span>SfM: {health.system_info.colmap_available ? "COLMAP" : "Mock/Open3D"}</span>
            </div>

            <div className="system-pill" title="Local SQLite Active">
              <Database size={13} className="text-sky-400" />
              <span>SQLite</span>
            </div>

            <div className="status-live-pill">
              <span className="status-dot-pulse" />
              <span>Online</span>
            </div>
          </>
        ) : (
          <div className="status-error-pill">
            <span className="status-dot-red" />
            <span>Backend Offline</span>
          </div>
        )}
      </div>
    </header>
  );
};
