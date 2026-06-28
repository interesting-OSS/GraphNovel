export interface Foreshadow {
  id: string; project_id: string; description: string; status: string;
  category: string; set_chapter_id: string | null;
  target_chapter_index: number | null; resolved_chapter_id: string | null;
  remind_deadline: number | null; importance: number;
  created_at: string; updated_at: string;
}
export interface ForeshadowStatistics {
  total: number; by_status: Record<string, number>;
  by_category: Record<string, number>; resolution_rate: number;
  warnings: Record<string, unknown>[];
}
