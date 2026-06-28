export interface GlobalSettings {
  ai_provider: string; ai_model: string; temperature: number;
  max_tokens: number; theme: string; active_preset_id: string | null;
  openai_api_key_set: boolean; anthropic_api_key_set: boolean;
  google_api_key_set: boolean; qwen_api_key_set: boolean; kimi_api_key_set: boolean;
}
export interface WritingStyle {
  id: string; name: string; description: string | null;
  content: string | null; is_preset: boolean; created_at: string; updated_at: string;
}
export interface Inspiration {
  id: string; idea: string; genre_tags: string | null;
  status: string; project_id: string | null; created_at: string;
}
