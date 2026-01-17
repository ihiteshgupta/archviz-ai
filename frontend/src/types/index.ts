export interface Project {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  status: 'created' | 'uploaded' | 'parsed' | 'parse_error';
  file_name: string | null;
  floor_plan: FloorPlan | null;
}

export interface FloorPlan {
  walls: Wall[];
  doors: Door[];
  windows: Window[];
  rooms: Room[];
  dimensions: Dimension[];
  metadata: FloorPlanMetadata;
}

export interface FloorPlanMetadata {
  units: string;
  total_area: number;
  room_count: number;
  bounds: {
    min: [number, number];
    max: [number, number];
  };
}

export interface Wall {
  id: string;
  points: [number, number][];
  thickness: number;
  height: number;
  layer: string;
  is_exterior: boolean;
}

export interface Door {
  id: string;
  position: [number, number];
  width: number;
  height: number;
  swing_angle: number;
  door_type: string;
  layer: string;
}

export interface Window {
  id: string;
  position: [number, number];
  width: number;
  height: number;
  sill_height: number;
  layer: string;
}

export interface Room {
  id: string;
  name: string;
  room_type: string;
  polygon: [number, number][];
  area: number;
  perimeter: number;
  layer: string;
}

export interface Dimension {
  id: string;
  start: [number, number];
  end: [number, number];
  value: number;
  text: string;
  layer: string;
}

export interface Material {
  id: string;
  name: string;
  category: string;
  subcategory: string;
  color_hex: string;
  roughness: number;
  metallic: number;
  description: string;
  style_tags: string[];
  preview_url: string | null;
}

export interface StylePreset {
  id: string;
  name: string;
  description: string;
  materials: Record<string, string>;
}

export interface RenderJob {
  id: string;
  project_id: string;
  style: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
  completed_at: string | null;
  renders: RenderOutput[];
  error: string | null;
}

export interface RenderOutput {
  view: string;
  url: string;
  thumbnail_url: string;
}

export interface RenderStyle {
  id: string;
  name: string;
  description: string;
}

// Batch Render Pipeline Types
export interface BatchRenderJob {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  floor_plan_id: string;
  total_rooms: number;
  completed_rooms: number;
  progress: number;
  successful_renders: number;
  failed_renders: number;
  results: BatchRenderResult[];
  errors: BatchRenderError[];
  created_at: string;
  completed_at: string | null;
}

export interface BatchRenderResult {
  room_id: string;
  room_name: string;
  image_url: string;
  revised_prompt: string;
  created_at: string;
  config: RenderConfig;
}

export interface BatchRenderError {
  room_id: string;
  room_name: string;
  error_type: string;
  message: string;
  retryable: boolean;
}

export interface RenderConfig {
  size: string;
  quality: string;
  style_preset: string;
  lighting: string;
  time_of_day: string;
  additional_prompt: string;
}

export interface MaterialAssignment {
  surface_id: string;
  material_id: string;
  room_id: string;
  surface_type: 'floor' | 'wall' | 'ceiling';
}

export interface RoomMaterials {
  floor?: string;
  wall?: string;
  ceiling?: string;
}

export interface PipelineStatus {
  available: boolean;
  provider: string | null;
  materials_loaded: number;
  active_jobs: number;
  pending_jobs: number;
}
