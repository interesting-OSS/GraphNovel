export interface Outline {
  id: string; project_id: string; volume: number; chapter_index: number;
  title: string; summary: string | null; key_points: string | null;
  mode: string; expansion_strategy: string; target_words?: number;
  parent_id?: string | null; sort_order?: number;
}
export interface OutlineCreateData {
  project_id: string; volume?: number; chapter_index?: number;
  title?: string; summary?: string; key_points?: string;
  mode?: string; expansion_strategy?: string; target_words?: number;
}
