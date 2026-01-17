import type {
  Project,
  Material,
  StylePreset,
  RenderJob,
  RenderStyle,
  BatchRenderJob,
  MaterialAssignment,
  PipelineStatus,
  Room,
} from '@/types';

const API_BASE = '/api';

async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Projects API
export async function createProject(
  name: string,
  description?: string
): Promise<Project> {
  return fetchAPI<Project>('/projects/', {
    method: 'POST',
    body: JSON.stringify({ name, description }),
  });
}

export async function listProjects(): Promise<Project[]> {
  return fetchAPI<Project[]>('/projects/');
}

export async function getProject(projectId: string): Promise<Project> {
  return fetchAPI<Project>(`/projects/${projectId}`);
}

export async function deleteProject(projectId: string): Promise<void> {
  await fetchAPI(`/projects/${projectId}`, { method: 'DELETE' });
}

export async function uploadFile(
  projectId: string,
  file: File
): Promise<{ status: string; project_id: string; file_name: string; floor_plan: any }> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/projects/${projectId}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export async function getFloorPlan(projectId: string): Promise<any> {
  return fetchAPI(`/projects/${projectId}/floor-plan`);
}

export async function getPreview(
  projectId: string
): Promise<{ svg: string; project_id: string }> {
  return fetchAPI(`/projects/${projectId}/preview`);
}

// Materials API
export async function getMaterialLibrary(): Promise<{ materials: Material[] }> {
  return fetchAPI('/materials/library');
}

export async function getMaterial(materialId: string): Promise<Material> {
  return fetchAPI(`/materials/library/${materialId}`);
}

export async function getMaterialsByCategory(
  category: string
): Promise<{ category: string; materials: Material[] }> {
  return fetchAPI(`/materials/category/${category}`);
}

export async function getCategories(): Promise<{
  categories: { id: string; name: string }[];
}> {
  return fetchAPI('/materials/categories');
}

export async function getStylePresets(): Promise<{ presets: StylePreset[] }> {
  return fetchAPI('/materials/presets');
}

export async function getStylePreset(presetId: string): Promise<StylePreset> {
  return fetchAPI(`/materials/presets/${presetId}`);
}

// Render API
export async function createRenderJob(params: {
  project_id: string;
  style?: string;
  views?: string[];
  resolution?: number;
  upscale?: boolean;
}): Promise<RenderJob> {
  return fetchAPI<RenderJob>('/render/', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function getRenderJob(jobId: string): Promise<RenderJob> {
  return fetchAPI<RenderJob>(`/render/${jobId}`);
}

export async function getProjectRenders(projectId: string): Promise<RenderJob[]> {
  return fetchAPI<RenderJob[]>(`/render/project/${projectId}`);
}

export async function cancelRenderJob(
  jobId: string
): Promise<{ status: string; id: string }> {
  return fetchAPI(`/render/${jobId}/cancel`, { method: 'POST' });
}

export async function getRenderStyles(): Promise<{ styles: RenderStyle[] }> {
  return fetchAPI('/render/styles');
}

// Render Pipeline API (Batch Rendering)
export async function getPipelineStatus(): Promise<PipelineStatus> {
  return fetchAPI('/render/pipeline/status');
}

export async function startBatchRender(params: {
  floor_plan_id: string;
  rooms: Array<{
    id: string;
    name: string;
    room_type?: string;
    polygon?: [number, number][];
  }>;
  material_assignments?: MaterialAssignment[];
  size?: string;
  quality?: string;
  style_preset?: string;
  lighting?: string;
  time_of_day?: string;
  additional_prompt?: string;
  room_ids?: string[];
}): Promise<BatchRenderJob> {
  return fetchAPI<BatchRenderJob>('/render/batch', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

export async function getBatchJob(jobId: string): Promise<BatchRenderJob> {
  return fetchAPI<BatchRenderJob>(`/render/batch/${jobId}`);
}

export async function cancelBatchJob(
  jobId: string
): Promise<{ status: string; id: string }> {
  return fetchAPI(`/render/batch/${jobId}/cancel`, { method: 'POST' });
}

export async function listBatchJobs(params?: {
  floor_plan_id?: string;
  status?: string;
  limit?: number;
}): Promise<{ jobs: BatchRenderJob[]; total: number }> {
  const searchParams = new URLSearchParams();
  if (params?.floor_plan_id) searchParams.set('floor_plan_id', params.floor_plan_id);
  if (params?.status) searchParams.set('status', params.status);
  if (params?.limit) searchParams.set('limit', params.limit.toString());

  const query = searchParams.toString();
  return fetchAPI(`/render/batch/jobs/list${query ? `?${query}` : ''}`);
}

export async function deleteBatchJob(
  jobId: string
): Promise<{ status: string; id: string }> {
  return fetchAPI(`/render/batch/${jobId}`, { method: 'DELETE' });
}

// Single Room Render
export async function renderSingleRoom(params: {
  room_id: string;
  room_name: string;
  room_type?: string;
  area?: number;
  polygon?: [number, number][];
  floor_material_id?: string;
  wall_material_id?: string;
  ceiling_material_id?: string;
  size?: string;
  quality?: string;
  style_preset?: string;
  lighting?: string;
  time_of_day?: string;
  additional_prompt?: string;
}): Promise<{
  room_id: string;
  room_name: string;
  image_url: string;
  revised_prompt: string;
  created_at: string;
}> {
  return fetchAPI('/render/room', {
    method: 'POST',
    body: JSON.stringify(params),
  });
}
