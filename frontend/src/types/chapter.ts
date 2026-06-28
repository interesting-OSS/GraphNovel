export interface ChapterSummary {
  id: string; index: number; title: string; word_count: number; status: string;
}
export interface Chapter {
  id: string; project_id: string; chapter_index: number; title: string;
  content: string | null; word_count: number; status: string;
  outline_id?: string | null; writing_style_id?: string | null;
  created_at?: string; updated_at?: string;
}
export interface ChapterGenerateRequest {
  project_id: string; current_chapter_index?: number; title?: string;
  genre?: string; description?: string; outlines?: Record<string, unknown>[];
  characters?: Record<string, unknown>[]; chapters?: Record<string, unknown>[];
  world_setting?: Record<string, unknown>; foreshadows?: Record<string, unknown>[];
  plot_memory?: Record<string, unknown>[]; chapter_analyses?: Record<string, unknown>[];
  generation_config?: Record<string, unknown>; writing_style_id?: string | null;
  active_skill?: string | null; human_feedback?: string | null;
}
