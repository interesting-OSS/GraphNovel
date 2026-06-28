export interface Character {
  id: string; project_id: string; name: string; gender: string; age: number | null;
  role_type: string; appearance: string | null; personality: string | null;
  background: string | null; goals: string | null; secrets: string | null;
  mental_state: string | null; power_level: string | null; career_id: string | null;
  organization_id: string | null; current_location: string | null; motto: string | null;
  ui_color: string; avatar_url: string | null; created_at: string; updated_at: string;
}
export interface CharacterCreateData {
  project_id: string; name?: string | null; gender?: string | null; age?: number | null;
  role_type?: string | null; appearance?: string | null; personality?: string | null;
  background?: string | null; goals?: string | null; secrets?: string | null;
  mental_state?: string | null; power_level?: string | null;
  career_id?: string | null; organization_id?: string | null;
  current_location?: string | null; motto?: string | null;
  ui_color?: string | null; avatar_url?: string | null;
}
