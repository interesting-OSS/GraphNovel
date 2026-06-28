import { api } from './client';
import type { Chapter } from '../types/chapter';

export function listChapters(projectId: string) { return api.get<{ items: Chapter[]; total: number }>(`/chapters/project/${projectId}`); }
export function getChapter(id: string) { return api.get<Chapter>(`/chapters/${id}`); }
export function createChapter(data: { project_id: string; chapter_index: number; title?: string; content?: string; word_count?: number; status?: string }) { return api.post<{ id: string; created: boolean }>('/chapters', data); }
export function updateChapter(id: string, data: Partial<Chapter>) { return api.put<{ id: string; updated: boolean }>(`/chapters/${id}`, data); }
export function deleteChapter(id: string) { return api.delete<{ deleted: boolean }>(`/chapters/${id}`); }
export function analyzeChapter(id: string, data: Record<string, unknown>) { return api.post<{ analysis: Record<string, unknown>; status: string }>(`/chapters/${id}/analyze`, data); }
export function rewriteChapter(id: string, data: Record<string, unknown>) { return api.post<{ rewritten_content: string; status: string }>(`/chapters/${id}/rewrite`, data); }
export function reviewChapter(id: string) { return api.post<Record<string, unknown>>(`/chapters/${id}/review`); }
export function batchGenerate(projectId: string, data: Record<string, unknown>) { return api.post<{ task_id: string; message: string }>(`/chapters/project/${projectId}/batch-generate`, data); }
