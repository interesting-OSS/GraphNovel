import { api } from './client';
import type { Outline } from '../types/outline';

export function listOutlines(projectId: string) { return api.get<{ items: Outline[]; total: number }>(`/outlines/project/${projectId}`); }
export function createOutline(data: Record<string, unknown>) { return api.post<{ id: string }>('/outlines', data); }
export function updateOutline(id: string, data: Partial<Outline>) { return api.put<{ id: string; updated: boolean }>(`/outlines/${id}`, data); }
export function deleteOutline(id: string) { return api.delete<{ deleted: boolean }>(`/outlines/${id}`); }
export function reorderOutlines(items: { id: string; chapter_index: number; volume?: number }[]) { return api.post<{ status: string }>('/outlines/reorder', { items }); }
