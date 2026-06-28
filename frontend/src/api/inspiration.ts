import { api } from './client';
import type { Inspiration } from '../types/settings';

export function listInspirations() { return api.get<{ items: Inspiration[]; total: number }>('/inspiration/saved'); }
export function saveInspiration(data: Record<string, unknown>) { return api.post<{ id: string; saved: boolean }>('/inspiration/save', data); }
export function convertToProject(id: string) { return api.post<{ project_id: string; message: string }>(`/inspiration/${id}/convert-to-project`); }
