import { api } from './client';
import type { Career } from '../types/organization';

export function listCareers(projectId: string) { return api.get<{ items: Career[]; total: number }>(`/careers/project/${projectId}`); }
export function createCareer(data: Record<string, unknown>) { return api.post<{ id: string }>('/careers', data); }
export function updateCareer(id: string, data: Record<string, unknown>) { return api.put<{ id: string; updated: boolean }>(`/careers/${id}`, data); }
export function deleteCareer(id: string) { return api.delete<{ deleted: boolean }>(`/careers/${id}`); }
