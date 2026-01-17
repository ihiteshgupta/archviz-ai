'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getProject,
  listProjects,
  createProject,
  deleteProject,
  uploadFile,
  getFloorPlan,
  getPreview,
  getMaterialLibrary,
  getMaterial,
  getMaterialsByCategory,
  getCategories,
  getStylePresets,
  getRenderStyles,
  getPipelineStatus,
  startBatchRender,
  getBatchJob,
  cancelBatchJob,
  listBatchJobs,
  renderSingleRoom,
} from './api';
import type {
  Project,
  Material,
  StylePreset,
  RenderStyle,
  BatchRenderJob,
  MaterialAssignment,
  PipelineStatus,
} from '@/types';

// Query Keys - centralized for cache invalidation
export const queryKeys = {
  projects: ['projects'] as const,
  project: (id: string) => ['project', id] as const,
  floorPlan: (projectId: string) => ['floorPlan', projectId] as const,
  preview: (projectId: string) => ['preview', projectId] as const,
  materials: ['materials'] as const,
  material: (id: string) => ['material', id] as const,
  materialsByCategory: (category: string) => ['materials', 'category', category] as const,
  categories: ['categories'] as const,
  stylePresets: ['stylePresets'] as const,
  renderStyles: ['renderStyles'] as const,
  pipelineStatus: ['pipelineStatus'] as const,
  batchJob: (id: string) => ['batchJob', id] as const,
  batchJobs: (params?: { floor_plan_id?: string; status?: string }) =>
    ['batchJobs', params] as const,
};

// ============ Project Hooks ============

export function useProjects() {
  return useQuery({
    queryKey: queryKeys.projects,
    queryFn: listProjects,
  });
}

export function useProject(projectId: string) {
  return useQuery({
    queryKey: queryKeys.project(projectId),
    queryFn: () => getProject(projectId),
    enabled: !!projectId,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ name, description }: { name: string; description?: string }) =>
      createProject(name, description),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.projects });
    },
  });
}

export function useDeleteProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) => deleteProject(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.projects });
    },
  });
}

export function useUploadFile(projectId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => uploadFile(projectId, file),
    onSuccess: () => {
      // Invalidate project to refetch with new floor plan
      queryClient.invalidateQueries({ queryKey: queryKeys.project(projectId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.floorPlan(projectId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.preview(projectId) });
    },
  });
}

export function useFloorPlan(projectId: string) {
  return useQuery({
    queryKey: queryKeys.floorPlan(projectId),
    queryFn: () => getFloorPlan(projectId),
    enabled: !!projectId,
  });
}

export function usePreview(projectId: string) {
  return useQuery({
    queryKey: queryKeys.preview(projectId),
    queryFn: () => getPreview(projectId),
    enabled: !!projectId,
  });
}

// ============ Material Hooks ============

export function useMaterials() {
  return useQuery({
    queryKey: queryKeys.materials,
    queryFn: getMaterialLibrary,
    staleTime: 5 * 60 * 1000, // Materials don't change often
  });
}

export function useMaterial(materialId: string) {
  return useQuery({
    queryKey: queryKeys.material(materialId),
    queryFn: () => getMaterial(materialId),
    enabled: !!materialId,
  });
}

export function useMaterialsByCategory(category: string) {
  return useQuery({
    queryKey: queryKeys.materialsByCategory(category),
    queryFn: () => getMaterialsByCategory(category),
    enabled: !!category,
  });
}

export function useCategories() {
  return useQuery({
    queryKey: queryKeys.categories,
    queryFn: getCategories,
    staleTime: 5 * 60 * 1000,
  });
}

export function useStylePresets() {
  return useQuery({
    queryKey: queryKeys.stylePresets,
    queryFn: getStylePresets,
    staleTime: 5 * 60 * 1000,
  });
}

// ============ Render Hooks ============

export function useRenderStyles() {
  return useQuery({
    queryKey: queryKeys.renderStyles,
    queryFn: getRenderStyles,
    staleTime: 5 * 60 * 1000,
  });
}

export function usePipelineStatus() {
  return useQuery({
    queryKey: queryKeys.pipelineStatus,
    queryFn: getPipelineStatus,
    retry: false, // Don't retry if pipeline not available
  });
}

export function useBatchJob(jobId: string | null, options?: { polling?: boolean }) {
  return useQuery({
    queryKey: queryKeys.batchJob(jobId || ''),
    queryFn: () => getBatchJob(jobId!),
    enabled: !!jobId,
    // Poll every 2 seconds while job is running
    refetchInterval: options?.polling ? 2000 : false,
  });
}

export function useBatchJobs(params?: { floor_plan_id?: string; status?: string; limit?: number }) {
  return useQuery({
    queryKey: queryKeys.batchJobs(params),
    queryFn: () => listBatchJobs(params),
  });
}

export function useStartBatchRender() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (params: Parameters<typeof startBatchRender>[0]) => startBatchRender(params),
    onSuccess: (data) => {
      // Add the new job to the cache
      queryClient.setQueryData(queryKeys.batchJob(data.id), data);
    },
  });
}

export function useCancelBatchJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) => cancelBatchJob(jobId),
    onSuccess: (_, jobId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.batchJob(jobId) });
    },
  });
}

export function useRenderSingleRoom() {
  return useMutation({
    mutationFn: (params: Parameters<typeof renderSingleRoom>[0]) => renderSingleRoom(params),
  });
}
