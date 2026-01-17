'use client';

import { useState } from 'react';
import { Plus, RefreshCw, Upload, FolderOpen, Sparkles } from 'lucide-react';
import { FileUpload, ProjectCard, Button, Modal, ModalFooter, SkeletonProjectCard } from '@/components';
import { useProjects, useCreateProject, useDeleteProject } from '@/lib/hooks';
import { uploadFile } from '@/lib/api';
import type { Project } from '@/types';

export default function Home() {
  // React Query hooks
  const { data: projects = [], isLoading: loading, error: queryError, refetch } = useProjects();
  const createProjectMutation = useCreateProject();
  const deleteProjectMutation = useDeleteProject();

  const [showNewProject, setShowNewProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDesc, setNewProjectDesc] = useState('');
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Get greeting based on time of day
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  // Quick stats
  const totalProjects = projects.length;
  const readyProjects = projects.filter((p) => p.status === 'parsed').length;

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return;

    try {
      const project = await createProjectMutation.mutateAsync({
        name: newProjectName,
        description: newProjectDesc || undefined,
      });
      setCurrentProject(project);
      setShowNewProject(false);
      setNewProjectName('');
      setNewProjectDesc('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    }
  };

  const handleQuickUpload = async (file: File) => {
    try {
      // Create a project with the file name
      const projectName = file.name.replace(/\.(dwg|dxf)$/i, '');
      const project = await createProjectMutation.mutateAsync({
        name: projectName,
      });
      await uploadFile(project.id, file);
      refetch();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload file');
    }
  };

  const handleUpload = async (file: File) => {
    if (!currentProject) return;

    try {
      await uploadFile(currentProject.id, file);
      refetch();
      setCurrentProject(null);
    } catch (err) {
      throw err;
    }
  };

  const handleDeleteProject = async (project: Project) => {
    if (!confirm(`Delete project "${project.name}"?`)) return;

    try {
      await deleteProjectMutation.mutateAsync(project.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete project');
    }
  };

  const handleViewProject = (project: Project) => {
    window.location.href = `/project/${project.id}`;
  };

  const handleRenderProject = (project: Project) => {
    window.location.href = `/project/${project.id}/render`;
  };

  return (
    <div className="min-h-screen bg-surface-base">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{getGreeting()}</h1>
            <p className="text-gray-500 mt-1">
              {totalProjects > 0
                ? `${totalProjects} project${totalProjects !== 1 ? 's' : ''} • ${readyProjects} ready to render`
                : 'Upload your first DWG to get started'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              icon={<RefreshCw className="w-4 h-4" />}
              onClick={() => refetch()}
            >
              Refresh
            </Button>
            <Button
              variant="primary"
              icon={<Plus className="w-4 h-4" />}
              onClick={() => setShowNewProject(true)}
            >
              New Project
            </Button>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 animate-slide-up">
            <div className="flex justify-between items-start">
              <p className="text-red-700">{error}</p>
              <button
                onClick={() => setError(null)}
                className="text-red-500 hover:text-red-700 text-sm"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        {/* Quick Upload Zone */}
        <div className="card mb-8 bg-gradient-to-br from-primary-50/50 to-oak-light/30 border-primary-100">
          <div className="flex items-center gap-6">
            <div className="flex-shrink-0 w-16 h-16 rounded-xl bg-primary-100 flex items-center justify-center">
              <Upload className="w-8 h-8 text-primary-600" />
            </div>
            <div className="flex-1">
              <h2 className="text-lg font-semibold text-gray-900 mb-1">Quick Upload</h2>
              <p className="text-gray-600 text-sm">
                Drop a DWG or DXF file to create a new project instantly
              </p>
            </div>
            <div className="flex-shrink-0">
              <FileUpload onUpload={handleQuickUpload} compact />
            </div>
          </div>
        </div>

        {/* New Project Modal */}
        <Modal
          open={showNewProject}
          onClose={() => {
            setShowNewProject(false);
            setNewProjectName('');
            setNewProjectDesc('');
          }}
          title="New Project"
          description="Create a new project to upload and render floor plans"
          size="md"
        >
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Project Name
              </label>
              <input
                type="text"
                value={newProjectName}
                onChange={(e) => setNewProjectName(e.target.value)}
                placeholder="My Architecture Project"
                className="input"
                autoFocus
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">
                Description <span className="text-gray-400">(optional)</span>
              </label>
              <textarea
                value={newProjectDesc}
                onChange={(e) => setNewProjectDesc(e.target.value)}
                placeholder="Brief description of the project..."
                rows={3}
                className="input resize-none"
              />
            </div>
          </div>
          <ModalFooter>
            <Button
              variant="secondary"
              onClick={() => {
                setShowNewProject(false);
                setNewProjectName('');
                setNewProjectDesc('');
              }}
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              onClick={handleCreateProject}
              disabled={!newProjectName.trim()}
              loading={createProjectMutation.isPending}
            >
              Create Project
            </Button>
          </ModalFooter>
        </Modal>

        {/* Upload Modal */}
        <Modal
          open={!!currentProject}
          onClose={() => setCurrentProject(null)}
          title="Upload Floor Plan"
          description={`Upload a DWG or DXF file for "${currentProject?.name}"`}
          size="lg"
        >
          <FileUpload onUpload={handleUpload} />
          <ModalFooter>
            <Button variant="secondary" onClick={() => setCurrentProject(null)}>
              Close
            </Button>
          </ModalFooter>
        </Modal>

        {/* Projects Grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[...Array(3)].map((_, i) => (
              <SkeletonProjectCard key={i} />
            ))}
          </div>
        ) : projects.length === 0 ? (
          <div className="card text-center py-16 animate-fade-in">
            <div className="w-20 h-20 bg-gradient-to-br from-primary-100 to-oak-light rounded-2xl flex items-center justify-center mx-auto mb-6">
              <FolderOpen className="w-10 h-10 text-primary-600" />
            </div>
            <h3 className="text-xl font-semibold text-gray-900 mb-2">
              Your workspace is ready
            </h3>
            <p className="text-gray-500 mb-6 max-w-md mx-auto">
              Upload your first DWG file to create stunning architectural renders in minutes
            </p>
            <div className="flex items-center justify-center gap-3">
              <Button
                variant="primary"
                icon={<Plus className="w-4 h-4" />}
                onClick={() => setShowNewProject(true)}
              >
                Create Project
              </Button>
              <Button
                variant="secondary"
                icon={<Sparkles className="w-4 h-4" />}
                onClick={() => {
                  // TODO: Load demo project
                }}
              >
                Try Demo
              </Button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {projects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onView={handleViewProject}
                onDelete={handleDeleteProject}
                onRender={handleRenderProject}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
