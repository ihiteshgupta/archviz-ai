'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { ArrowLeft, Upload, Zap, Box, Layers, Cuboid } from 'lucide-react';
import { getProject, uploadFile } from '@/lib/api';
import { FileUpload, FloorPlanViewer, FloorPlan3DViewer } from '@/components';
import { formatDate, formatArea } from '@/lib/utils';
import type { Project } from '@/types';

export default function ProjectPage() {
  const params = useParams();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);
  const [activeTab, setActiveTab] = useState<'preview' | '3d' | 'details'>('preview');

  useEffect(() => {
    async function loadProject() {
      try {
        setLoading(true);
        const data = await getProject(projectId);
        setProject(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load project');
      } finally {
        setLoading(false);
      }
    }

    loadProject();
  }, [projectId]);

  const handleUpload = async (file: File) => {
    try {
      const result = await uploadFile(projectId, file);
      setProject((prev) =>
        prev
          ? {
              ...prev,
              status: 'parsed',
              file_name: result.file_name,
              floor_plan: result.floor_plan,
            }
          : null
      );
      setShowUpload(false);
    } catch (err) {
      throw err;
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

  const canRender = project.status === 'parsed' && project.floor_plan;

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <a
          href="/"
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5 text-gray-600" />
        </a>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
          {project.description && (
            <p className="text-gray-500">{project.description}</p>
          )}
        </div>
        <div className="flex items-center gap-3">
          {!project.file_name && (
            <button
              onClick={() => setShowUpload(true)}
              className="btn-secondary flex items-center gap-2"
            >
              <Upload className="w-4 h-4" />
              Upload File
            </button>
          )}
          {canRender && (
            <a
              href={`/project/${project.id}/render`}
              className="btn-primary flex items-center gap-2"
            >
              <Zap className="w-4 h-4" />
              Create Render
            </a>
          )}
        </div>
      </div>

      {/* Upload Modal */}
      {showUpload && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg">
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              Upload Floor Plan
            </h2>
            <p className="text-gray-500 mb-6">
              Upload a DWG or DXF file for this project
            </p>
            <FileUpload onUpload={handleUpload} />
            <div className="flex justify-end mt-6">
              <button onClick={() => setShowUpload(false)} className="btn-secondary">
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-2">
          {/* Tabs */}
          <div className="flex items-center gap-4 mb-4">
            <button
              onClick={() => setActiveTab('preview')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                activeTab === 'preview'
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Box className="w-4 h-4" />
              2D View
            </button>
            <button
              onClick={() => setActiveTab('3d')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                activeTab === '3d'
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Cuboid className="w-4 h-4" />
              3D View
            </button>
            <button
              onClick={() => setActiveTab('details')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                activeTab === 'details'
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              <Layers className="w-4 h-4" />
              Details
            </button>
          </div>

          {/* Tab Content */}
          {project.status === 'parsed' && project.floor_plan ? (
            activeTab === 'preview' ? (
              <FloorPlanViewer projectId={project.id} />
            ) : activeTab === '3d' ? (
              <FloorPlan3DViewer floorPlan={project.floor_plan} />
            ) : (
              <div className="card">
                <h3 className="font-semibold text-gray-900 mb-4">Floor Plan Details</h3>

                {/* Rooms */}
                {project.floor_plan.rooms && project.floor_plan.rooms.length > 0 && (
                  <div className="mb-6">
                    <h4 className="text-sm font-medium text-gray-700 mb-2">Rooms</h4>
                    <div className="space-y-2">
                      {project.floor_plan.rooms.map((room: any) => (
                        <div
                          key={room.id}
                          className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                        >
                          <span className="font-medium text-gray-900">
                            {room.name || room.room_type}
                          </span>
                          <span className="text-gray-500">
                            {formatArea(room.area)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Summary */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <div className="text-2xl font-bold text-gray-900">
                      {project.floor_plan.walls?.length || 0}
                    </div>
                    <div className="text-sm text-gray-500">Walls</div>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <div className="text-2xl font-bold text-gray-900">
                      {project.floor_plan.doors?.length || 0}
                    </div>
                    <div className="text-sm text-gray-500">Doors</div>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <div className="text-2xl font-bold text-gray-900">
                      {project.floor_plan.windows?.length || 0}
                    </div>
                    <div className="text-sm text-gray-500">Windows</div>
                  </div>
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <div className="text-2xl font-bold text-gray-900">
                      {project.floor_plan.rooms?.length || 0}
                    </div>
                    <div className="text-sm text-gray-500">Rooms</div>
                  </div>
                </div>
              </div>
            )
          ) : (
            <div className="card text-center py-12">
              <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No floor plan yet
              </h3>
              <p className="text-gray-500 mb-4">
                Upload a DWG or DXF file to see the floor plan
              </p>
              <button onClick={() => setShowUpload(true)} className="btn-primary">
                Upload File
              </button>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Project Info */}
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-4">Project Info</h3>
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-gray-500">Status</dt>
                <dd className="font-medium text-gray-900 capitalize">
                  {project.status.replace('_', ' ')}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">File</dt>
                <dd className="font-medium text-gray-900">
                  {project.file_name || 'None'}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Created</dt>
                <dd className="font-medium text-gray-900">
                  {formatDate(project.created_at)}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Updated</dt>
                <dd className="font-medium text-gray-900">
                  {formatDate(project.updated_at)}
                </dd>
              </div>
              {project.floor_plan?.metadata && (
                <>
                  <div>
                    <dt className="text-gray-500">Total Area</dt>
                    <dd className="font-medium text-gray-900">
                      {formatArea(project.floor_plan.metadata.total_area)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Units</dt>
                    <dd className="font-medium text-gray-900">
                      {project.floor_plan.metadata.units}
                    </dd>
                  </div>
                </>
              )}
            </dl>
          </div>

          {/* Quick Actions */}
          <div className="card">
            <h3 className="font-semibold text-gray-900 mb-4">Quick Actions</h3>
            <div className="space-y-2">
              <button
                onClick={() => setShowUpload(true)}
                className="w-full btn-secondary text-left flex items-center gap-2"
              >
                <Upload className="w-4 h-4" />
                {project.file_name ? 'Replace File' : 'Upload File'}
              </button>
              <a
                href={canRender ? `/project/${project.id}/render` : '#'}
                className={`w-full btn-secondary text-left flex items-center gap-2 ${
                  !canRender ? 'opacity-50 cursor-not-allowed' : ''
                }`}
              >
                <Zap className="w-4 h-4" />
                Create Render
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
