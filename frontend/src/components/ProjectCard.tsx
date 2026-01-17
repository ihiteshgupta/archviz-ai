'use client';

import { Trash2, Eye, Zap, FileText } from 'lucide-react';
import type { Project } from '@/types';
import { formatDate, formatArea } from '@/lib/utils';
import { cn } from '@/lib/utils';

interface ProjectCardProps {
  project: Project;
  onView: (project: Project) => void;
  onDelete: (project: Project) => void;
  onRender: (project: Project) => void;
}

const statusColors: Record<string, string> = {
  created: 'bg-gray-100 text-gray-600',
  uploaded: 'bg-blue-100 text-blue-600',
  parsed: 'bg-green-100 text-green-600',
  parse_error: 'bg-red-100 text-red-600',
};

const statusLabels: Record<string, string> = {
  created: 'Created',
  uploaded: 'Uploaded',
  parsed: 'Ready',
  parse_error: 'Error',
};

export default function ProjectCard({
  project,
  onView,
  onDelete,
  onRender,
}: ProjectCardProps) {
  const canRender = project.status === 'parsed' && project.floor_plan;

  return (
    <div className="card hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="font-semibold text-gray-900 text-lg">{project.name}</h3>
          {project.description && (
            <p className="text-gray-500 text-sm mt-1">{project.description}</p>
          )}
        </div>
        <span
          className={cn(
            'px-2 py-1 rounded-full text-xs font-medium',
            statusColors[project.status]
          )}
        >
          {statusLabels[project.status]}
        </span>
      </div>

      <div className="space-y-2 text-sm text-gray-500 mb-4">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4" />
          <span>{project.file_name || 'No file uploaded'}</span>
        </div>
        {project.floor_plan?.metadata && (
          <>
            <div>
              Rooms: {project.floor_plan.metadata.room_count} | Area:{' '}
              {formatArea(project.floor_plan.metadata.total_area)}
            </div>
          </>
        )}
        <div className="text-xs text-gray-400">
          Updated: {formatDate(project.updated_at)}
        </div>
      </div>

      <div className="flex items-center gap-2 pt-4 border-t border-gray-100">
        <button
          onClick={() => onView(project)}
          className="flex items-center gap-1 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <Eye className="w-4 h-4" />
          View
        </button>
        <button
          onClick={() => onRender(project)}
          disabled={!canRender}
          className={cn(
            'flex items-center gap-1 px-3 py-2 text-sm rounded-lg transition-colors',
            canRender
              ? 'text-primary-600 hover:text-primary-700 hover:bg-primary-50'
              : 'text-gray-400 cursor-not-allowed'
          )}
        >
          <Zap className="w-4 h-4" />
          Render
        </button>
        <div className="flex-1" />
        <button
          onClick={() => onDelete(project)}
          className="flex items-center gap-1 px-3 py-2 text-sm text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
