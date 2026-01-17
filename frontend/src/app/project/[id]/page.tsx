'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { ArrowLeft, Upload, Zap, Box, Layers, Cuboid, Grid3X3 } from 'lucide-react';
import { useProject, useUploadFile } from '@/lib/hooks';
import {
  FileUpload,
  FloorPlanViewer,
  FloorPlan3DViewer,
  Button,
  Modal,
  ModalFooter,
  Card,
  Badge,
  Tabs,
  TabList,
  TabTrigger,
  TabContent,
  SkeletonFloorPlan,
  Skeleton,
} from '@/components';
import { formatDate, formatArea } from '@/lib/utils';

export default function ProjectPage() {
  const params = useParams();
  const projectId = params.id as string;

  // React Query hooks
  const { data: project, isLoading: loading, error: queryError } = useProject(projectId);
  const uploadFileMutation = useUploadFile(projectId);

  const [showUpload, setShowUpload] = useState(false);

  const handleUpload = async (file: File) => {
    await uploadFileMutation.mutateAsync(file);
    setShowUpload(false);
  };

  const error = queryError instanceof Error ? queryError.message : null;

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-surface-base">
        <div className="max-w-7xl mx-auto px-4 py-8">
          {/* Header skeleton */}
          <div className="flex items-center gap-4 mb-6">
            <Skeleton variant="rectangular" width={40} height={40} />
            <div className="flex-1">
              <Skeleton variant="text" width={200} height={28} className="mb-2" />
              <Skeleton variant="text" width={150} height={16} />
            </div>
          </div>

          {/* Content skeleton */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <SkeletonFloorPlan />
            </div>
            <div className="space-y-6">
              <Card variant="static">
                <Skeleton variant="text" width={100} height={20} className="mb-4" />
                <div className="space-y-3">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={i} variant="text" />
                  ))}
                </div>
              </Card>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !project) {
    return (
      <div className="min-h-screen bg-surface-base">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <Card className="text-center py-12">
            <p className="text-red-600 mb-4">{error || 'Project not found'}</p>
            <Button variant="primary" onClick={() => (window.location.href = '/')}>
              Back to Projects
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  const canRender = project.status === 'parsed' && project.floor_plan;

  const statusConfig: Record<string, { variant: 'success' | 'warning' | 'error' | 'info' | 'neutral'; label: string }> = {
    created: { variant: 'neutral', label: 'No File' },
    uploaded: { variant: 'info', label: 'Processing' },
    parsed: { variant: 'success', label: 'Ready' },
    parse_error: { variant: 'error', label: 'Parse Error' },
  };

  const config = statusConfig[project.status] || statusConfig.created;

  return (
    <div className="min-h-screen bg-surface-base">
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
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-2xl font-bold text-gray-900">{project.name}</h1>
              <Badge variant={config.variant}>{config.label}</Badge>
            </div>
            {project.description && (
              <p className="text-gray-500">{project.description}</p>
            )}
          </div>
          <div className="flex items-center gap-3">
            {!project.file_name && (
              <Button
                variant="secondary"
                icon={<Upload className="w-4 h-4" />}
                onClick={() => setShowUpload(true)}
              >
                Upload File
              </Button>
            )}
            {canRender && (
              <Button
                variant="primary"
                icon={<Zap className="w-4 h-4" />}
                onClick={() => (window.location.href = `/project/${project.id}/render`)}
              >
                Open Studio
              </Button>
            )}
          </div>
        </div>

        {/* Upload Modal */}
        <Modal
          open={showUpload}
          onClose={() => setShowUpload(false)}
          title="Upload Floor Plan"
          description="Upload a DWG or DXF file for this project"
          size="lg"
        >
          <FileUpload onUpload={handleUpload} />
          <ModalFooter>
            <Button variant="secondary" onClick={() => setShowUpload(false)}>
              Close
            </Button>
          </ModalFooter>
        </Modal>

        {/* Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content */}
          <div className="lg:col-span-2">
            {project.status === 'parsed' && project.floor_plan ? (
              <Tabs defaultValue="preview">
                <TabList className="mb-4">
                  <TabTrigger value="preview" icon={<Box className="w-4 h-4" />}>
                    2D View
                  </TabTrigger>
                  <TabTrigger value="3d" icon={<Cuboid className="w-4 h-4" />}>
                    3D View
                  </TabTrigger>
                  <TabTrigger value="details" icon={<Layers className="w-4 h-4" />}>
                    Details
                  </TabTrigger>
                </TabList>

                <TabContent value="preview">
                  <FloorPlanViewer projectId={project.id} />
                </TabContent>

                <TabContent value="3d">
                  <FloorPlan3DViewer floorPlan={project.floor_plan} />
                </TabContent>

                <TabContent value="details">
                  <Card variant="static">
                    <h3 className="font-semibold text-gray-900 mb-4">Floor Plan Details</h3>

                    {/* Rooms */}
                    {project.floor_plan.rooms && project.floor_plan.rooms.length > 0 && (
                      <div className="mb-6">
                        <h4 className="text-sm font-medium text-gray-700 mb-3">
                          Rooms ({project.floor_plan.rooms.length})
                        </h4>
                        <div className="space-y-2">
                          {project.floor_plan.rooms.map((room: any) => (
                            <div
                              key={room.id}
                              className="flex items-center justify-between p-3 bg-surface-base rounded-lg"
                            >
                              <div>
                                <span className="font-medium text-gray-900">
                                  {room.name || room.room_type}
                                </span>
                                <span className="text-xs text-gray-400 ml-2 uppercase">
                                  {room.room_type}
                                </span>
                              </div>
                              <span className="text-dimensions">
                                {formatArea(room.area)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Summary */}
                    <div className="grid grid-cols-2 gap-3">
                      <div className="p-4 bg-surface-base rounded-lg text-center">
                        <div className="text-2xl font-bold text-gray-900">
                          {project.floor_plan.walls?.length || 0}
                        </div>
                        <div className="text-sm text-gray-500">Walls</div>
                      </div>
                      <div className="p-4 bg-surface-base rounded-lg text-center">
                        <div className="text-2xl font-bold text-gray-900">
                          {project.floor_plan.doors?.length || 0}
                        </div>
                        <div className="text-sm text-gray-500">Doors</div>
                      </div>
                      <div className="p-4 bg-surface-base rounded-lg text-center">
                        <div className="text-2xl font-bold text-gray-900">
                          {project.floor_plan.windows?.length || 0}
                        </div>
                        <div className="text-sm text-gray-500">Windows</div>
                      </div>
                      <div className="p-4 bg-surface-base rounded-lg text-center">
                        <div className="text-2xl font-bold text-gray-900">
                          {project.floor_plan.rooms?.length || 0}
                        </div>
                        <div className="text-sm text-gray-500">Rooms</div>
                      </div>
                    </div>
                  </Card>
                </TabContent>
              </Tabs>
            ) : (
              <Card className="text-center py-12">
                <div className="w-16 h-16 bg-gradient-to-br from-primary-100 to-oak-light rounded-xl flex items-center justify-center mx-auto mb-4">
                  <Upload className="w-8 h-8 text-primary-600" />
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  No floor plan yet
                </h3>
                <p className="text-gray-500 mb-4">
                  Upload a DWG or DXF file to see the floor plan
                </p>
                <Button
                  variant="primary"
                  icon={<Upload className="w-4 h-4" />}
                  onClick={() => setShowUpload(true)}
                >
                  Upload File
                </Button>
              </Card>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Project Info */}
            <Card variant="static">
              <h3 className="font-semibold text-gray-900 mb-4">Project Info</h3>
              <dl className="space-y-4 text-sm">
                <div>
                  <dt className="text-gray-500 mb-1">Status</dt>
                  <dd>
                    <Badge variant={config.variant}>{config.label}</Badge>
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500 mb-1">File</dt>
                  <dd className="font-medium text-gray-900">
                    {project.file_name || 'None'}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500 mb-1">Created</dt>
                  <dd className="font-medium text-gray-900">
                    {formatDate(project.created_at)}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500 mb-1">Updated</dt>
                  <dd className="font-medium text-gray-900">
                    {formatDate(project.updated_at)}
                  </dd>
                </div>
                {project.floor_plan?.metadata && (
                  <>
                    <div>
                      <dt className="text-gray-500 mb-1">Total Area</dt>
                      <dd className="font-medium text-gray-900 text-dimensions">
                        {formatArea(project.floor_plan.metadata.total_area)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-gray-500 mb-1">Units</dt>
                      <dd className="font-medium text-gray-900">
                        {project.floor_plan.metadata.units}
                      </dd>
                    </div>
                  </>
                )}
              </dl>
            </Card>

            {/* Quick Actions */}
            <Card variant="static">
              <h3 className="font-semibold text-gray-900 mb-4">Quick Actions</h3>
              <div className="space-y-2">
                <Button
                  variant="secondary"
                  icon={<Upload className="w-4 h-4" />}
                  onClick={() => setShowUpload(true)}
                  className="w-full justify-start"
                >
                  {project.file_name ? 'Replace File' : 'Upload File'}
                </Button>
                <Button
                  variant={canRender ? 'primary' : 'secondary'}
                  icon={<Zap className="w-4 h-4" />}
                  disabled={!canRender}
                  onClick={() => canRender && (window.location.href = `/project/${project.id}/render`)}
                  className="w-full justify-start"
                >
                  Open Render Studio
                </Button>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
