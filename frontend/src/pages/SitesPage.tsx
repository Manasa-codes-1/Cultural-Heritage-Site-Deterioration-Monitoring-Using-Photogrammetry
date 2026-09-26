import React, { useEffect, useState } from 'react';
import { Landmark, Plus, MapPin, Calendar, Layers, Trash2, ArrowRight } from 'lucide-react';
import type { Site, SiteCreate } from '../types';
import { api } from '../api/client';
import { Modal } from '../components/common/Modal';

interface SitesPageProps {
  onSelectSite: (siteId: string) => void;
}

export const SitesPage: React.FC<SitesPageProps> = ({ onSelectSite }) => {
  const [sites, setSites] = useState<Site[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [modalOpen, setModalOpen] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [formData, setFormData] = useState<SiteCreate>({
    name: '',
    location: '',
    description: '',
    historical_period: '',
    primary_material: 'Sandstone',
    latitude: undefined,
    longitude: undefined,
  });

  const loadSites = async () => {
    setLoading(true);
    try {
      const data = await api.getSites();
      setSites(data);
    } catch (err) {
      console.error('Failed to load sites', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSites();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim() || !formData.location.trim()) return;

    setSubmitting(true);
    try {
      await api.createSite(formData);
      setModalOpen(false);
      setFormData({
        name: '',
        location: '',
        description: '',
        historical_period: '',
        primary_material: 'Sandstone',
        latitude: undefined,
        longitude: undefined,
      });
      await loadSites();
    } catch (err) {
      alert(`Error creating site: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (siteId: string, name: string) => {
    if (!confirm(`Are you sure you want to delete site "${name}" and all its surveys?`)) return;
    try {
      await api.deleteSite(siteId);
      await loadSites();
    } catch (err) {
      alert(`Failed to delete site: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h2 className="page-title">Cultural Heritage Sites</h2>
          <p className="page-description">
            Register and manage architectural monuments, historical facades, and baseline site profiles.
          </p>
        </div>
        <button onClick={() => setModalOpen(true)} className="btn-primary">
          <Plus size={16} />
          <span>Register New Site</span>
        </button>
      </div>

      {loading ? (
        <div className="empty-box">
          <p className="text-slate-400">Loading heritage sites...</p>
        </div>
      ) : sites.length === 0 ? (
        <div className="empty-box">
          <Landmark size={36} className="text-slate-500 mb-2" />
          <p className="text-slate-300 font-medium">No heritage sites registered yet.</p>
          <p className="text-slate-500 text-xs mt-1">Register a heritage monument to begin logging multi-temporal surveys.</p>
          <button onClick={() => setModalOpen(true)} className="btn-primary mt-4 text-xs">
            <Plus size={14} /> Add First Site
          </button>
        </div>
      ) : (
        <div className="sites-grid">
          {sites.map((site) => (
            <div key={site.id} className="card site-card">
              <div className="site-card-top">
                <div>
                  <h3 className="site-card-title">{site.name}</h3>
                  <p className="site-card-location">
                    <MapPin size={13} className="text-amber-400" />
                    <span>{site.location}</span>
                  </p>
                </div>
                <button
                  onClick={() => handleDelete(site.id, site.name)}
                  className="text-slate-500 hover:text-rose-400 p-1 rounded"
                  title="Delete site"
                >
                  <Trash2 size={15} />
                </button>
              </div>

              {site.description && (
                <p className="site-card-desc">{site.description}</p>
              )}

              <div className="site-card-meta">
                {site.historical_period && (
                  <div className="meta-tag">
                    <Calendar size={12} className="text-slate-400" />
                    <span>{site.historical_period}</span>
                  </div>
                )}
                {site.primary_material && (
                  <div className="meta-tag">
                    <Layers size={12} className="text-amber-400" />
                    <span>{site.primary_material}</span>
                  </div>
                )}
              </div>

              <div className="site-card-footer">
                <span className="text-xs text-slate-400">
                  <strong className="text-slate-200">{site.survey_count}</strong> surveys
                </span>
                <button
                  onClick={() => onSelectSite(site.id)}
                  className="btn-link"
                >
                  <span>View Surveys</span>
                  <ArrowRight size={13} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Register Site Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title="Register Cultural Heritage Site"
        subtitle="Specify the architectural identity, geographical location, and primary substrate material."
      >
        <form onSubmit={handleSubmit} className="form-space">
          <div className="form-group">
            <label className="form-label">Site Name *</label>
            <input
              type="text"
              required
              placeholder="e.g. Amber Fort Bastion IV"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Geographic Location *</label>
            <input
              type="text"
              required
              placeholder="e.g. Jaipur, Rajasthan, India"
              value={formData.location}
              onChange={(e) => setFormData({ ...formData, location: e.target.value })}
              className="form-input"
            />
          </div>

          <div className="form-row-2">
            <div className="form-group">
              <label className="form-label">Historical Period / Era</label>
              <input
                type="text"
                placeholder="e.g. 16th Century Rajput"
                value={formData.historical_period}
                onChange={(e) => setFormData({ ...formData, historical_period: e.target.value })}
                className="form-input"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Primary Substrate Material</label>
              <select
                value={formData.primary_material}
                onChange={(e) => setFormData({ ...formData, primary_material: e.target.value })}
                className="form-select"
              >
                <option value="Sandstone">Sandstone</option>
                <option value="Granite">Granite</option>
                <option value="Brick & Lime Mortar">Brick & Lime Mortar</option>
                <option value="Marble">Marble</option>
                <option value="Limestone">Limestone</option>
                <option value="Mixed Masonry">Mixed Masonry</option>
              </select>
            </div>
          </div>

          <div className="form-row-2">
            <div className="form-group">
              <label className="form-label">Latitude (optional)</label>
              <input
                type="number"
                step="any"
                placeholder="e.g. 26.9855"
                value={formData.latitude ?? ''}
                onChange={(e) => setFormData({ ...formData, latitude: e.target.value ? parseFloat(e.target.value) : undefined })}
                className="form-input"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Longitude (optional)</label>
              <input
                type="number"
                step="any"
                placeholder="e.g. 75.8513"
                value={formData.longitude ?? ''}
                onChange={(e) => setFormData({ ...formData, longitude: e.target.value ? parseFloat(e.target.value) : undefined })}
                className="form-input"
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Site Architectural Description</label>
            <textarea
              rows={3}
              placeholder="Notes on conservation history, environmental exposure, masonry construction details..."
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
              {submitting ? 'Registering...' : 'Register Site'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
