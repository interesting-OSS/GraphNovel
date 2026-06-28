export interface ProjectSummary {
  id: string; title: string; description: string | null; genre: string;
  status: string; total_word_count: number; narrative_perspective: string;
  outline_mode: string; cover_url: string | null; created_at: string; updated_at: string;
}
export interface Project {
  id: string; title: string; description: string | null; genre: string;
  target_words: number; narrative_perspective: string; status: string;
  total_word_count: number; outline_mode: string;
  world_setting: Record<string, unknown> | null; cover_prompt: string | null;
  cover_url: string | null; writing_style_id: string | null;
  active_skill: string | null; generation_config: Record<string, unknown> | null;
  created_at: string; updated_at: string;
}
export interface CreateProjectData {
  title: string; description?: string; genre?: string; target_words?: number;
  narrative_perspective?: string; outline_mode?: string;
  world_setting?: Record<string, unknown>; writing_style_id?: string;
  generation_config?: Record<string, unknown>;
}
