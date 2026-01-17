'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { ArrowLeft, Zap, Palette, Settings2, Image } from 'lucide-react';
import { getProject, getRenderStyles, createRenderJob, getStylePresets } from '@/lib/api';
import type { Project, RenderStyle, StylePreset } from '@/types';

export default function RenderPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [styles, setStyles] = useState<RenderStyle[]>([]);
  const [presets, setPresets] = useState<StylePreset[]>([]);
  const [loading, setLoading] = useState(true);
  const [rendering, setRendering] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Render settings
  const [selectedStyle, setSelectedStyle] = useState('modern_minimalist');
  const [resolution, setResolution] = useState(1024);
  const [upscale, setUpscale] = useState(true);
  const [views, setViews] = useState(['default']);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [projectData, stylesData, presetsData] = await Promise.all([
          getProject(projectId),
          getRenderStyles(),
          getStylePresets(),
        ]);
        setProject(projectData);
        setStyles(stylesData.styles);
        setPresets(presetsData.presets);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [projectId]);

  const handleStartRender = async () => {
    try {
      setRendering(true);
      setError(null);
      const job = await createRenderJob({
        project_id: projectId,
        style: selectedStyle,
        resolution,
        upscale,
        views,
      });
      // Redirect to render job status page or show success
      alert(`Render job created: ${job.id}\nStatus: ${job.status}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start render');
    } finally {
      setRendering(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="card text-center py-12">
          <p className="text-red-600 mb-4">{error || 'Project not found'}</p>
          <a href="/" className="btn-primary">
            Back to Projects
          </a>
        </div>
      </div>
    );
  }

  const selectedPreset = presets.find((p) => p.id === selectedStyle);

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <a
          href={`/project/${project.id}`}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-600" />
        </a>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">Create Render</h1>
          <p className="text-gray-500">{project.name}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Style Selection */}
        <div className="lg:col-span-2 space-y-6">
          {/* Render Styles */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <Palette className="w-5 h-5 text-primary-600" />
              <h2 className="text-lg font-semibold text-gray-900">Render Style</h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {styles.map((style) => (
                <button
                  key={style.id}
                  onClick={() => setSelectedStyle(style.id)}
                  className={`p-4 rounded-lg border-2 text-left transition-colors ${
                    selectedStyle === style.id
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="font-medium text-gray-900">{style.name}</div>
                  <div className="text-sm text-gray-500 mt-1">{style.description}</div>
                </button>
              ))}
            </div>
          </div>

          {/* Material Preset Preview */}
          {selectedPreset && (
            <div className="card">
              <div className="flex items-center gap-2 mb-4">
                <Image className="w-5 h-5 text-primary-600" />
                <h2 className="text-lg font-semibold text-gray-900">
                  Material Preset: {selectedPreset.name}
                </h2>
              </div>
              <p className="text-gray-500 mb-4">{selectedPreset.description}</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(selectedPreset.materials).map(([surface, materialId]) => (
                  <div key={surface} className="p-3 bg-gray-50 rounded-lg">
                    <div className="text-xs text-gray-500 uppercase">{surface}</div>
                    <div className="font-medium text-gray-900 text-sm mt-1">
                      {materialId.replace(/_/g, ' ')}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Settings Sidebar */}
        <div className="space-y-6">
          {/* Render Settings */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <Settings2 className="w-5 h-5 text-primary-600" />
              <h2 className="text-lg font-semibold text-gray-900">Settings</h2>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Resolution
                </label>
                <select
                  value={resolution}
                  onChange={(e) => setResolution(Number(e.target.value))}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                >
                  <option value={512}>512 x 512 (Fast)</option>
                  <option value={1024}>1024 x 1024 (Standard)</option>
                  <option value={2048}>2048 x 2048 (High Quality)</option>
                </select>
              </div>

              <div>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={upscale}
                    onChange={(e) => setUpscale(e.target.checked)}
                    className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                  />
                  <span className="text-sm font-medium text-gray-700">
                    AI Upscale (4x)
                  </span>
                </label>
                <p className="text-xs text-gray-500 mt-1 ml-6">
                  Enhance output resolution with AI upscaling
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Camera Views
                </label>
                <div className="space-y-2">
                  {['default', 'corner', 'aerial', 'eye_level'].map((view) => (
                    <label key={view} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={views.includes(view)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setViews([...views, view]);
                          } else {
                            setViews(views.filter((v) => v !== view));
                          }
                        }}
                        className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                      />
                      <span className="text-sm text-gray-700 capitalize">
                        {view.replace('_', ' ')}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Start Render */}
          <div className="card">
            <button
              onClick={handleStartRender}
              disabled={rendering || views.length === 0}
              className="w-full btn-primary flex items-center justify-center gap-2 py-3"
            >
              {rendering ? (
                <>
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Zap className="w-5 h-5" />
                  Start Render
                </>
              )}
            </button>
            <p className="text-xs text-gray-500 text-center mt-3">
              Estimated time: 2-5 minutes per view
            </p>
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
