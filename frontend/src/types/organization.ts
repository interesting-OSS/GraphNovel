export interface Organization {
  id: string; project_id: string; name: string; org_type: string;
  leader_id: string | null; goal: string | null; description: string | null;
  hierarchy: string | null; alignment: string; created_at: string; updated_at: string;
  members?: { id: string; character_id: string; role: string | null }[];
}
export interface Career {
  id: string; project_id: string; name: string; career_type: string;
  description: string | null; levels: CareerLevel[] | null;
  created_at?: string; updated_at?: string;
}
export interface CareerLevel { name: string; index: number; description: string; abilities: string[]; }
export interface CharacterRelationship {
  id: string; project_id: string; char_a_id: string; char_b_id: string;
  relation_type: string; description: string | null; intimacy: number;
  status: string; source: string; created_at: string; updated_at: string;
}
