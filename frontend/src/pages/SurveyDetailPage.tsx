import React, { useEffect, useState, useRef } from 'react';
import {
  UploadCloud,
  ArrowLeft,
  Calendar,
  Camera,
  CloudSun,
  Trash2,
  RefreshCw,
  Eye,
  Layers,
  Sparkles,
  Box,
} from 'lucide-react';
import type { SurveyDetail, ImageRecord } from '../types';
import { api } from '../api/client';
import { StatusBadge } from '../components/common/StatusBadge';
import { Modal } from '../components/common/Modal';

interface SurveyDetailPageProps {
  surveyId: string;
  onBack: () => void;
  onNavigateToQuality: (surveyId: string) => void;
  onNavigateToReconstruction?: (surveyId: string) => void;
}

export const SurveyDetailPage: React.FC<SurveyDetailPageProps> = ({
  surveyId,
  onBack,
  onNavigateToQuality,
  onNavigateToReconstruction,
}) => {

  const [survey, setSurvey] = useState<SurveyDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadFeedback, setUploadFeedback] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState<ImageRecord | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadSurvey = async () => {
    setLoading(true);
    try {
      const data = await api.getSurveyDetail(surveyId);
      setSurvey(data);
    } catch (err) {
      console.error('Failed to load survey detail', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSurvey();
  }, [surveyId]);

  const handleFiles = async (files: FileList | File[]) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setUploadFeedback(null);
    try {
      const fileArray = Array.from(files);
      const res = await api.uploadImages(surveyId, fileArray);
      setUploadFeedback(
        `Successfully uploaded ${res.total_uploaded} image(s). ${
          res.total_failed > 0 ? `(${res.total_failed} skipped due to format issues)` : ''
        }`
      );
      await loadSurvey();
    } catch (err) {
      alert(`Upload error: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleDeleteImage = async (imageId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Delete this image from storage?')) return;
    try {
      await api.deleteImage(imageId);
      if (selectedImage?.id === imageId) setSelectedImage(null);
      await loadSurvey();
    } catch (err) {
      alert(`Delete error: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleReassess = async (imageId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const updated = await api.reassessImage(imageId);
      if (selectedImage?.id === imageId) setSelectedImage(updated);
      await loadSurvey();
    } catch (err) {
      alert(`Re-assessment error: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  if (loading && !survey) {
    return (
      <div className="page-container">
        <div className="empty-box">
          <p className="text-slate-400">Loading survey details & imagery...</p>
        </div>
      </div>
    );
  }

  if (!survey) {
    return (
      <div className="page-container">
        <div className="empty-box">
          <p className="text-rose-400">Survey not found.</p>
          <button onClick={onBack} className="btn-secondary mt-3">
            <ArrowLeft size={14} /> Back to Surveys
          </button>
        </div>
      </div>
    );
  }

  const env = survey.environmental_info;
  const passCount = survey.images.filter((img) => img.quality_status === 'pass').length;
  const failCount = survey.images.filter((img) => img.quality_status === 'fail').length;

  return (
    <div className="page-container">
      {/* Top Navigation & Actions */}
      <div className="flex items-center justify-between mb-4">
        <button onClick={onBack} className="btn-secondary text-xs">
          <ArrowLeft size={14} />
          <span>All Surveys</span>
        </button>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onNavigateToQuality(survey.id)}
            className="btn-secondary text-xs"
            disabled={survey.images.length === 0}
          >
            <Sparkles size={14} className="text-amber-400" />
            <span>Overlap & Quality</span>
          </button>
          {onNavigateToReconstruction && (
            <button
              onClick={() => onNavigateToReconstruction(survey.id)}
              className="btn-secondary text-xs text-amber-300 border-amber-600/40 hover:bg-amber-950/30"
              disabled={survey.images.length === 0}
            >
              <Box size={14} className="text-amber-400" />
              <span>3D Reconstruction</span>
            </button>
          )}
          <button onClick={loadSurvey} className="btn-secondary text-xs">
            <RefreshCw size={13} />
            <span>Reload</span>
          </button>

        </div>
      </div>

      {/* Survey Info Header Card */}
      <div className="card mb-6">
        <div className="card-header border-b border-slate-800 pb-3">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-slate-100">{survey.survey_code}</h2>
              <StatusBadge status={survey.status} />
            </div>
            <p className="text-xs text-slate-400 mt-1">
              {survey.description || 'Routine baseline photogrammetric survey'}
            </p>
          </div>
          <div className="text-right">
            <span className="text-xs text-slate-400 block">Photogrammetry Readiness</span>
            <span className={`text-xs font-semibold ${
              passCount >= 3 ? 'text-emerald-400' : 'text-amber-400'
            }`}>
              {passCount >= 3 ? 'Dataset Viable (≥3 clean images)' : 'Awaiting additional images'}
            </span>
          </div>
        </div>

        <div className="p-4 grid grid-cols-1 md:grid-cols-4 gap-4 bg-slate-900/40">
          <div className="flex items-center gap-2 text-xs">
            <Calendar size={15} className="text-amber-400" />
            <div>
              <span className="text-slate-400 block">Capture Date</span>
              <span className="text-slate-200 font-medium">
                {new Date(survey.survey_date).toLocaleString()}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <Camera size={15} className="text-sky-400" />
            <div>
              <span className="text-slate-400 block">Sensor / Camera</span>
              <span className="text-slate-200 font-medium truncate max-w-[180px]" title={survey.camera_info}>
                {survey.camera_info || 'Smartphone / Standard Camera'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <CloudSun size={15} className="text-amber-400" />
            <div>
              <span className="text-slate-400 block">Environment</span>
              <span className="text-slate-200 font-medium">
                {env ? `${env.temp_c ?? '--'}°C • ${env.humidity_pct ?? '--'}% RH` : 'Not recorded'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <Layers size={15} className="text-emerald-400" />
            <div>
              <span className="text-slate-400 block">Image Quality Ratio</span>
              <span className="text-slate-200 font-mono">
                {passCount} Pass / {failCount} Issues ({survey.images.length} Total)
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Upload Dropzone */}
      <div
        className={`upload-dropzone ${uploading ? 'upload-dropzone-active' : ''}`}
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*,.jpg,.jpeg,.png,.tif,.tiff"
          className="hidden"
          onChange={(e) => e.target.files && handleFiles(e.target.files)}
        />
        <div className="upload-dropzone-content">
          <div className="upload-icon-circle">
            <UploadCloud size={24} className="text-amber-400" />
          </div>
          <div>
            <h4 className="font-semibold text-slate-200">
              {uploading ? 'Uploading & Evaluating Quality with OpenCV...' : 'Upload Survey Imagery'}
            </h4>
            <p className="text-xs text-slate-400 mt-1">
              Drag and drop smartphone, DSLR, or UAV photos here, or click to browse.
            </p>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Instant automated checks: Laplacian blur variance, dynamic range, and ORB keypoint density.
            </p>
          </div>
        </div>
      </div>

      {uploadFeedback && (
        <div className="mt-3 p-3 bg-slate-900 border border-slate-800 rounded text-xs text-emerald-400">
          {uploadFeedback}
        </div>
      )}

      {/* Image Gallery */}
      <div className="mt-6">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
            <span>Survey Image Collection</span>
            <span className="text-xs font-normal text-slate-400">({survey.images.length} images)</span>
          </h3>
        </div>

        {survey.images.length === 0 ? (
          <div className="empty-box">
            <p className="text-slate-400 text-xs">No images uploaded for this survey epoch yet.</p>
          </div>
        ) : (
          <div className="image-cards-grid">
            {survey.images.map((img) => (
              <div
                key={img.id}
                className="image-card"
                onClick={() => setSelectedImage(img)}
              >
                <div className="image-card-thumb-wrap">
                  <img
                    src={img.download_url || `/api/images/${img.id}/file`}
                    alt={img.filename}
                    className="image-card-thumb"
                    loading="lazy"
                  />
                  <div className="image-card-badge-overlay">
                    <StatusBadge status={img.quality_status} />
                  </div>
                </div>

                <div className="image-card-info">
                  <p className="image-card-title truncate" title={img.filename}>
                    {img.filename}
                  </p>
                  <div className="image-card-metrics">
                    <span>{img.width && img.height ? `${img.width}x${img.height}` : 'Dimensions N/A'}</span>
                    <span>{(img.file_size_bytes / 1024).toFixed(0)} KB</span>
                  </div>

                  <div className="image-card-quality-strip">
                    <span
                      className={`quality-indicator ${img.blur_status === 'pass' ? 'text-emerald-400' : 'text-rose-400'}`}
                      title={`Blur variance: ${img.blur_score?.toFixed(1) ?? '--'}`}
                    >
                      Blur: {img.blur_status ?? '--'}
                    </span>
                    <span
                      className={`quality-indicator ${img.brightness_status === 'pass' ? 'text-emerald-400' : 'text-amber-400'}`}
                      title={`Brightness: ${img.brightness_score?.toFixed(1) ?? '--'}`}
                    >
                      Light: {img.brightness_status ?? '--'}
                    </span>
                    <span className="quality-indicator text-sky-400" title="Keypoints for photogrammetry">
                      Feat: {img.feature_count ?? '--'}
                    </span>
                  </div>

                  <div className="image-card-actions">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedImage(img);
                      }}
                      className="btn-icon-sm"
                      title="Inspect OpenCV diagnostics"
                    >
                      <Eye size={13} />
                    </button>
                    <button
                      onClick={(e) => handleReassess(img.id, e)}
                      className="btn-icon-sm"
                      title="Re-run quality assessment"
                    >
                      <RefreshCw size={13} />
                    </button>
                    <button
                      onClick={(e) => handleDeleteImage(img.id, e)}
                      className="btn-icon-sm text-slate-500 hover:text-rose-400"
                      title="Delete image"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Image Inspection Modal */}
      {selectedImage && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedImage(null)}
          title={`Image Quality Diagnostics: ${selectedImage.filename}`}
          subtitle="OpenCV optical validation results for photogrammetric reconstruction."
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <img
                src={selectedImage.download_url || `/api/images/${selectedImage.id}/file`}
                alt={selectedImage.filename}
                className="w-full h-auto rounded border border-slate-700 object-cover max-h-72"
              />
              <div className="mt-3 flex items-center justify-between text-xs text-slate-400">
                <span>Resolution: {selectedImage.width} x {selectedImage.height}</span>
                <span>Size: {(selectedImage.file_size_bytes / 1024).toFixed(1)} KB</span>
              </div>
            </div>

            <div className="space-y-3">
              <div className="p-3 bg-slate-900 rounded border border-slate-800">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-slate-300">Overall Quality Score</span>
                  <StatusBadge status={selectedImage.quality_status} />
                </div>
                <div className="text-2xl font-bold font-mono text-amber-400">
                  {selectedImage.quality_score?.toFixed(1) ?? '--'}/100
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  {selectedImage.quality_details?.overall_recommendation ||
                    'Optical assessment complete.'}
                </p>
              </div>

              {/* Detailed metrics table */}
              <div className="space-y-2 text-xs">
                <div className="p-2.5 bg-slate-900/60 rounded border border-slate-800 flex justify-between items-start">
                  <div>
                    <span className="font-semibold text-slate-200">Laplacian Blur Variance</span>
                    <p className="text-[11px] text-slate-400">
                      Score: {selectedImage.blur_score?.toFixed(1) ?? '--'} (Threshold: 100.0)
                    </p>
                  </div>
                  <span className={selectedImage.blur_status === 'pass' ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
                    {selectedImage.blur_status?.toUpperCase() ?? '--'}
                  </span>
                </div>

                <div className="p-2.5 bg-slate-900/60 rounded border border-slate-800 flex justify-between items-start">
                  <div>
                    <span className="font-semibold text-slate-200">Luminance / Brightness</span>
                    <p className="text-[11px] text-slate-400">
                      Mean: {selectedImage.brightness_score?.toFixed(1) ?? '--'} / 255 (Range: 40-220)
                    </p>
                  </div>
                  <span className={selectedImage.brightness_status === 'pass' ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
                    {selectedImage.brightness_status?.toUpperCase() ?? '--'}
                  </span>
                </div>

                <div className="p-2.5 bg-slate-900/60 rounded border border-slate-800 flex justify-between items-start">
                  <div>
                    <span className="font-semibold text-slate-200">ORB Feature Keypoints</span>
                    <p className="text-[11px] text-slate-400">
                      {selectedImage.feature_count ?? 0} features (Min. 300 recommended for SfM matching)
                    </p>
                  </div>
                  <span className={(selectedImage.feature_count ?? 0) >= 300 ? 'text-emerald-400 font-semibold' : 'text-amber-400 font-semibold'}>
                    {(selectedImage.feature_count ?? 0) >= 300 ? 'PASS' : 'WARN'}
                  </span>
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setSelectedImage(null)}
                  className="btn-secondary text-xs"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
