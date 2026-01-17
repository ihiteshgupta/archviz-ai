'use client';

import { Trash2, Eye, Zap, FileText, Box } from 'lucide-react';
import type { Project } from '@/types';
import { formatDate, formatArea } from '@/lib/utils';
import { Badge, Button } from './ui';

interface ProjectCardProps {
  project: Project;
  onView: (project: Project) => void;
  onDelete: (project: Project) => void;
  onRender: (project: Project) => void;
}

const statusConfig: Record<string, { variant: 'success' | 'warning' | 'error' | 'info' | 'neutral'; label: string }> = {
  created: { variant: 'neutral', label: 'No File' },
  uploaded: { variant: 'info', label: 'Processing' },
  parsed: { variant: 'success', label: 'Ready' },
  parse_error: { variant: 'error', label: 'Error' },
};

export default function ProjectCard({
  project,
  onView,
  onDelete,
  onRender,
}: ProjectCardProps) {
  const canRender = project.status === 'parsed' && project.floor_plan;
  const config = statusConfig[project.status] || statusConfig.created;
  const roomCount = project.floor_plan?.metadata?.room_count || 0;

  return (
    <div className="card group">
      {/* Thumbnail / Preview */}
      <div className="relative -mx-6 -mt-6 mb-4 aspect-[16/9] bg-surface-base overflow-hidden">
        {project.floor_plan ? (
          <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-primary-50 to-oak-light">
            <Box className="w-12 h-12 text-primary-600/30" />
          </div>
        ) : (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-50">
            <FileText className="w-12 h-12 text-gray-300" />
          </div>
        )}

        {/* Overlay actions on hover */}
        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              icon={<Eye className="w-4 h-4" />}
              onClick={() => onView(project)}
              className="bg-white/90 hover:bg-white"
            >
              View
            </Button>
            {canRender && (
              <Button
                variant="primary"
                size="sm"
                icon={<Zap className="w-4 h-4" />}
                onClick={() => onRender(project)}
              >
                Render
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 truncate">{project.name}</h3>
          {project.description && (
            <p className="text-sm text-gray-500 truncate mt-0.5">{project.description}</p>
          )}
        </div>
        <Badge variant={config.variant} size="sm">
          {config.label}
        </Badge>
      </div>

      {/* Stats */}
      <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
        {project.floor_plan?.metadata ? (
          <>
            <div className="flex items-center gap-1.5">
              <Box className="w-3.5 h-3.5" />
              <span>{roomCount} rooms</span>
            </div>
            <div className="flex items-center gap-1.5 text-dimensions">
              <span>{Math.round(project.floor_plan.metadata.total_area).toLocaleString()} {project.floor_plan.metadata.units}</span>
            </div>
          </>
        ) : (
          <div className="flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5" />
            <span>{project.file_name || 'No file uploaded'}</span>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-3 border-t border-border">
        <span className="text-xs text-gray-400">
          Updated {formatDate(project.updated_at)}
        </span>
        <button
          onClick={() => onDelete(project)}
          className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          title="Delete project"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
