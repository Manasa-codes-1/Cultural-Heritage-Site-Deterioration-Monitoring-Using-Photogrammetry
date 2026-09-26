import React, { useEffect, useState } from 'react';
import {
  FolderKanban,
  Plus,
  Calendar,
  Camera,
  CloudSun,
  Image as ImageIcon,
  Trash2,
  ArrowRight,
  Filter,
} from 'lucide-react';
import type { Survey, Site, SurveyCreate } from '../types';
import { api } from '../api/client';
import { StatusBadge } from '../components/common/StatusBadge';
import { Modal } from '../components/common/Modal';

interface SurveysPageProps {
  initialSiteId?: string;
  onSelectSurvey: (surveyId: string) => void;
}

export const SurveysPage: React.FC<SurveysPageProps> = ({ initialSiteId, onSelectSurvey }) => {
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [sites, setSites] = useState<Site[]>([]);
  const [selectedSiteFilter, setSelectedSiteFilter] = useState<string>(initialSiteId || '');
  const [loading, setLoading] = useState<boolean>(true);
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);

  const [formData, setFormData] = useState<SurveyCreate>({
    site_id: initialSiteId || '',
    survey_code: '',
    survey_date: new Date().toISOString().slice(0, 16),
    description: '',
    operator: '',
    camera_info: 'Smartphone / Mirrorless (e.g. Sony A7 IV / iPhone)',
    environmental_info: {
      temp_c: 28.0,
      humidity_pct: 55.0,
      rainfall_mm: 0.0,
      uv_index: 6.0,
      notes: '',
    },
  });

  const loadData = async () => {
    setLoading(true);
    try {
      const [sData, srvData] = await Promise.all([
        api.getSites(),
        api.getSurveys(selectedSiteFilter || undefined),
      ]);
      setSites(sData);
      setSurveys(srvData);
      if (!formData.site_id && sData.length > 0) {
        setFormData((prev) => ({ ...prev, site_id: sData[0].id }));
      }
    } catch (err) {
      console.error('Failed to load surveys data', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedSiteFilter]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.site_id || !formData.survey_code.trim()) {
      alert('Please select a site and enter a survey code.');
      return;
    }

    setSubmitting(true);
    try {
      const created = await api.createSurvey(formData);
      setModalOpen(false);
      await loadData();
      onSelectSurvey(created.id);
    } catch (err) {
      alert(`Error creating survey: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (surveyId: string, code: string) => {
    if (!confirm(`Delete survey "${code}" and all associated images?`)) return;
    try {
      await api.deleteSurvey(surveyId);
      await loadData();
    } catch (err) {
      alert(`Failed to delete survey: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header">
        <div>
          <h2 className="page-title">Photogrammetric Surveys</h2>
          <p className="page-description">
            Multi-temporal capture campaigns, sensor metadata, and ambient environmental logs.
          </p>
        </div>
        <button onClick={() => setModalOpen(true)} className="btn-primary" disabled={sites.length === 0}>
          <Plus size={16} />
          <span>New Survey Epoch</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="filter-bar">
        <div className="flex items-center gap-2">
          <Filter size={15} className="text-slate-400" />
          <span className="text-xs font-semibold text-slate-300">Filter by Heritage Site:</span>
        </div>
        <select
          value={selectedSiteFilter}
          onChange={(e) => setSelectedSiteFilter(e.target.value)}
          className="form-select text-xs py-1 max-w-xs"
        >
          <option value="">All Registered Sites</option>
          {sites.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name} ({s.location})
            </option>
          ))}
        </select>
        {selectedSiteFilter && (
          <button
            onClick={() => setSelectedSiteFilter('')}
            className="text-xs text-amber-400 hover:underline"
          >
            Clear Filter
          </button>
        )}
      </div>

      {loading ? (
        <div className="empty-box">
          <p className="text-slate-400">Loading surveys...</p>
        </div>
      ) : surveys.length === 0 ? (
        <div className="empty-box">
          <FolderKanban size={36} className="text-slate-500 mb-2" />
          <p className="text-slate-300 font-medium">No surveys recorded.</p>
          <p className="text-slate-500 text-xs mt-1">
            {sites.length === 0
              ? 'First register a heritage site before logging surveys.'
              : 'Create a survey epoch to upload field images.'}
          </p>
          {sites.length > 0 && (
            <button onClick={() => setModalOpen(true)} className="btn-primary mt-4 text-xs">
              <Plus size={14} /> Create Survey
            </button>
          )}
        </div>
      ) : (
        <div className="surveys-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Survey Code</th>
                <th>Capture Epoch</th>
                <th>Operator</th>
                <th>Sensor / Optics</th>
                <th>Environmental Log</th>
                <th>Images</th>
                <th>Quality Score</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {surveys.map((survey) => {
                const env = survey.environmental_info;
                return (
                  <tr key={survey.id} className="hover:bg-slate-800/40 transition-colors">
                    <td>
                      <span className="font-semibold text-slate-200">{survey.survey_code}</span>
                      {survey.description && (
                        <p className="text-xs text-slate-400 truncate max-w-xs">{survey.description}</p>
                      )}
                    </td>
                    <td>
                      <div className="flex items-center gap-1.5 text-xs text-slate-300">
                        <Calendar size={13} className="text-slate-400" />
                        <span>{new Date(survey.survey_date).toLocaleDateString()}</span>
                      </div>
                    </td>
                    <td>
                      <span className="text-xs text-slate-300">{survey.operator || 'Field Team'}</span>
                    </td>
                    <td>
                      <div className="flex items-center gap-1 text-xs text-slate-400">
                        <Camera size={12} className="text-slate-400" />
                        <span className="truncate max-w-[140px]" title={survey.camera_info}>
                          {survey.camera_info || 'Standard DSLR/Phone'}
                        </span>
                      </div>
                    </td>
                    <td>
                      {env ? (
                        <div className="flex items-center gap-1.5 text-xs text-slate-300" title={`Rain: ${env.rainfall_mm ?? 0}mm, UV: ${env.uv_index ?? 'N/A'}`}>
                          <CloudSun size={13} className="text-amber-400" />
                          <span>{env.temp_c ?? '--'}°C / {env.humidity_pct ?? '--'}%</span>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-500">Not recorded</span>
                      )}
                    </td>
                    <td>
                      <div className="flex items-center gap-1 text-xs font-semibold text-slate-200">
                        <ImageIcon size={13} className="text-sky-400" />
                        <span>{survey.image_count}</span>
                      </div>
                    </td>
                    <td>
                      {survey.average_quality_score !== null && survey.average_quality_score !== undefined ? (
                        <span className={`font-mono text-xs font-semibold ${
                          survey.average_quality_score >= 70 ? 'text-emerald-400' : 'text-amber-400'
                        }`}>
                          {survey.average_quality_score}%
                        </span>
                      ) : (
                        <span className="text-xs text-slate-500">Pending</span>
                      )}
                    </td>
                    <td>
                      <StatusBadge status={survey.status} />
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => onSelectSurvey(survey.id)}
                          className="btn-primary text-xs py-1 px-2.5"
                          title="Open survey images and inspection"
                        >
                          <span>Manage</span>
                          <ArrowRight size={12} />
                        </button>
                        <button
                          onClick={() => handleDelete(survey.id, survey.survey_code)}
                          className="text-slate-500 hover:text-rose-400 p-1 rounded"
                          title="Delete survey"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Survey Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Initialize Survey Campaign"
        subtitle="Establish a new photogrammetric capture epoch with environmental parameters."
      >
        <form onSubmit={handleSubmit} className="form-space">
          <div className="form-group">
            <label className="form-label">Target Heritage Site *</label>
            <select
              required
              value={formData.site_id}
              onChange={(e) => setFormData({ ...formData, site_id: e.target.value })}
              className="form-select"
            >
              <option value="" disabled>Select Site...</option>
              {sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.location})
                </option>
              ))}
            </select>
          </div>

          <div className="form-row-2">
            <div className="form-group">
              <label className="form-label">Survey Code / Campaign Identifier *</label>
              <input
                type="text"
                required
                placeholder="e.g. SRV-2026-Q1-RAMPART"
                value={formData.survey_code}
                onChange={(e) => setFormData({ ...formData, survey_code: e.target.value })}
                className="form-input"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Survey Date & Time</label>
              <input
                type="datetime-local"
                value={formData.survey_date}
                onChange={(e) => setFormData({ ...formData, survey_date: e.target.value })}
                className="form-input"
              />
            </div>
          </div>

          <div className="form-row-2">
            <div className="form-group">
              <label className="form-label">Lead Surveyor / Operator</label>
              <input
                type="text"
                placeholder="e.g. Dr. A. Verma"
                value={formData.operator}
                onChange={(e) => setFormData({ ...formData, operator: e.target.value })}
                className="form-input"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Camera & Sensor Description</label>
              <input
                type="text"
                placeholder="e.g. Sony A7 IV / iPhone 15 Pro 48MP"
                value={formData.camera_info}
                onChange={(e) => setFormData({ ...formData, camera_info: e.target.value })}
                className="form-input"
              />
            </div>
          </div>

          {/* Environmental parameters section */}
          <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800 space-y-3">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-amber-400">
              <CloudSun size={14} />
              <span>Optional Field Environmental Metadata (No Expensive Sensors Required)</span>
            </div>
            <div className="grid grid-cols-4 gap-2">
              <div>
                <label className="text-[11px] text-slate-400 block mb-1">Temp (°C)</label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.environmental_info?.temp_c ?? ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      environmental_info: {
                        ...formData.environmental_info,
                        temp_c: e.target.value ? parseFloat(e.target.value) : undefined,
                      },
                    })
                  }
                  className="form-input text-xs py-1"
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-400 block mb-1">Humidity (%)</label>
                <input
                  type="number"
                  step="0.5"
                  value={formData.environmental_info?.humidity_pct ?? ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      environmental_info: {
                        ...formData.environmental_info,
                        humidity_pct: e.target.value ? parseFloat(e.target.value) : undefined,
                      },
                    })
                  }
                  className="form-input text-xs py-1"
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-400 block mb-1">Rain (mm)</label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.environmental_info?.rainfall_mm ?? ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      environmental_info: {
                        ...formData.environmental_info,
                        rainfall_mm: e.target.value ? parseFloat(e.target.value) : undefined,
                      },
                    })
                  }
                  className="form-input text-xs py-1"
                />
              </div>
              <div>
                <label className="text-[11px] text-slate-400 block mb-1">UV Index</label>
                <input
                  type="number"
                  step="0.5"
                  value={formData.environmental_info?.uv_index ?? ''}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      environmental_info: {
                        ...formData.environmental_info,
                        uv_index: e.target.value ? parseFloat(e.target.value) : undefined,
                      },
                    })
                  }
                  className="form-input text-xs py-1"
                />
              </div>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Survey Scope & Observations</label>
            <textarea
              rows={2}
              placeholder="Notes on lighting conditions, access constraints, scaffold positions..."
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="form-textarea"
            />
          </div>

          <div className="modal-actions">
            <button type="button" onClick={() => setModalOpen(false)} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={submitting} className="btn-primary">
              {submitting ? 'Creating...' : 'Initialize Survey'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
