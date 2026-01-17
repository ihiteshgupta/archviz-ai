import type {
  Project,
  Material,
  StylePreset,
  RenderJob,
  RenderStyle,
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
