/* ===== Core Domain Types ===== */

export interface Project {
  id: string;
  title: string;
  description: string | null;
  genre: string;
  target_words: number;
  narrative_perspective: string;
  status: 'planning' | 'writing' | 'revising' | 'completed';
  total_word_count: number;
  outline_mode: 'one-to-one' | 'one-to-many';
  world_setting: string | null;
  cover_prompt: string | null;
  cover_url: string | null;
  writing_style_id: string | null;
  prompt_template_id: string | null;
  active_skill: string | null;
  generation_config: string | null;
  created_at: string;
  updated_at: string;
}

export interface Outline {
  id: string;
  project_id: string;
  volume: number;
  chapter_num: number;
  title: string;
  summary: string | null;
  key_points: string | null;
  mode: 'one-to-one' | 'one-to-many';
  expansion_strategy: 'balanced' | 'climax' | 'detail';
  expansion_plan: string | null;
  parent_id: string | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface Character {
  id: string;
  project_id: string;
  name: string;
  gender: string;
  age: number | null;
  role_type: 'protagonist' | 'antagonist' | 'supporting';
  appearance: string | null;
  personality: string | null;
  background: string | null;
  goals: string | null;
  secrets: string | null;
  mental_state: string | null;
  career_id: string | null;
  organization_id: string | null;
  avatar_url: string | null;
  power_level: string | null;
  current_location: string | null;
  motto: string | null;
  ui_color: string;
  traits: string | null;
  sort_order: number;
}

export interface Chapter {
  id: string;
  project_id: string;
  outline_id: string | null;
  title: string;
  content: string | null;
  word_count: number;
  chapter_index: number;
  status: 'draft' | 'polished' | 'final';
  writing_style_id: string | null;
  model_override: string | null;
  skill_override: string | null;
  narrative_perspective_override: string | null;
  expansion_plan: string | null;
  continuation_mode: 'auto' | 'new' | 'continue';
  created_at: string;
  updated_at: string;
}

export interface CharacterRelationship {
  id: string;
  project_id: string;
  char_a_id: string;
  char_b_id: string;
  relation_type: string;
  description: string | null;
  intimacy: number;
  status: string;
  source: 'manual' | 'ai_generated';
}

export interface Organization {
  id: string;
  project_id: string;
  name: string;
  org_type: string;
  leader_id: string | null;
  goal: string | null;
  hierarchy: string | null;
  description: string | null;
}

export interface Career {
  id: string;
  project_id: string;
  name: string;
  description: string | null;
  levels: string | null;
}

export interface Foreshadow {
  id: string;
  project_id: string;
  description: string;
  status: 'pending' | 'set' | 'resolved' | 'abandoned';
  category: string;
  set_chapter_id: string | null;
  target_chapter_index: number | null;
  resolved_chapter_id: string | null;
  remind_deadline: number | null;
  importance: number;
}

export interface WritingStyle {
  id: string;
  name: string;
  description: string | null;
  content: string | null;
  is_preset: boolean;
}

export interface MCPPlugin {
  id: string;
  name: string;
  description: string | null;
  transport: 'http' | 'streamable_http' | 'sse';
  url: string;
  enabled: boolean;
  config: string | null;
}

export interface BackgroundTask {
  id: string;
  project_id: string;
  task_type: string;
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  config: string | null;
  result: string | null;
  error_message: string | null;
  can_pause: boolean;
  can_cancel: boolean;
  created_at: string;
  updated_at: string;
}

export interface Inspiration {
  id: string;
  idea: string;
  genre_tags: string | null;
  status: 'draft' | 'saved' | 'converted_to_project';
  project_id: string | null;
  created_at: string;
}

export interface GenerationHistory {
  id: string;
  project_id: string;
  chapter_id: string;
  version: number;
  content: string | null;
  diff: string | null;
  word_count: number;
  created_at: string;
}

/* ===== API Types ===== */

export interface PaginationResponse<T> {
  items: T[];
  total: number;
  page?: number;
  page_size?: number;
  total_pages?: number;
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface ApiError {
  response?: {
    data?: {
      detail?: string;
    };
  };
  message?: string;
}

/* ===== Wizard Types ===== */

export interface WizardBasicInfo {
  title: string;
  description: string;
  genre: string;
  narrative_perspective: string;
  target_words: number;
  outline_mode: 'one-to-one' | 'one-to-many';
  character_count: number;
}

export interface WorldSetting {
  time_period: string;
  geography: string;
  power_system: string;
  factions: string;
  culture: string;
  rules?: string;
}

/* ===== Chapter Analysis Types ===== */

export interface PlotPoint {
  description: string;
  importance: number;
  impact: number;
}

export interface ConflictInfo {
  type: string;
  participants: string[];
  level: number;
  resolution_progress: number;
}

export interface EmotionalArc {
  primary_emotion: string;
  intensity: number;
  trajectory: string;
  secondary_emotions: string[];
}

export interface ChapterAnalysis {
  plot_points: PlotPoint[];
  conflict_info: ConflictInfo | null;
  emotional_arc: EmotionalArc | null;
  character_arcs: Record<string, string>;
  pacing_score: number | null;
  engagement_score: number | null;
  coherence_score: number | null;
  quality_score: number | null;
  suggestions: string[];
  report: string | null;
  dialogue_ratio: number | null;
  description_ratio: number | null;
  narrative_ratio: number | null;
}

/* ===== SSE Event Types ===== */

export interface SSEProgress {
  type: 'progress';
  message: string;
  progress: number;
  status: string;
  wordCount?: number;
}

export interface SSEChunk {
  type: 'chunk';
  content: string;
}

export interface SSEResult {
  type: 'result';
  data: Record<string, unknown>;
}

export interface SSEError {
  type: 'error';
  message: string;
  code?: string;
}

export interface SSEDone {
  type: 'done';
  message: string;
}

export type SSEEvent = SSEProgress | SSEChunk | SSEResult | SSEError | SSEDone;
