export type ProjectStatus =
  | "created"
  | "planning"
  | "queued"
  | "generating"
  | "rendering"
  | "completed"
  | "failed";

export type ProjectQuality = "draft" | "final";
export type SceneStatus = "waiting" | "queued" | "generating" | "completed" | "failed";

export interface SceneContext {
  character: string | null;
  environment: string | null;
  visual_style: string | null;
  lighting: string | null;
  camera: string | null;
  colors: string[];
  reference_images: string[];
  seed: number | null;
}

export interface Scene {
  id: string;
  order: number;
  duration_seconds: number;
  prompt: string;
  status: SceneStatus;
  context: SceneContext;
}

export interface Project {
  id: string;
  prompt: string;
  duration_seconds: number;
  quality: ProjectQuality;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
  scenes: Scene[];
}

export interface CreateProjectInput {
  prompt: string;
  duration_seconds: number;
  quality: ProjectQuality;
}
