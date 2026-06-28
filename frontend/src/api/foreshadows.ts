import { api } from './client';
import type { Foreshadow, ForeshadowStatistics } from '../types/foreshadow';

export function listForeshadows(projectId: string) { return api.get<{ items: Foreshadow[]; total: number }>(`/foreshadows/project/${projectId}`); }
export function createForeshadow(data: Record<string, unknown>) { return api.post<{ id: string }>('/foreshadows', data); }
export function updateForeshadow(id: string, data: Partial<Foreshadow>) { return api.put<{ id: string; updated: boolean }>(`/foreshadows/${id}`, data); }
export function deleteForeshadow(id: string) { return api.delete<{ deleted: boolean }>(`/foreshadows/${id}`); }
export function plantForeshadow(id: string) { return api.post<{ id: string; status: string }>(`/foreshadows/${id}/plant`); }
export function resolveForeshadow(id: string) { return api.post<{ id: string; status: string }>(`/foreshadows/${id}/resolve`); }
export function getForeshadowStats(projectId: string) { return api.get<{ statistics: ForeshadowStatistics }>(`/foreshadows/project/${projectId}/statistics`); }
