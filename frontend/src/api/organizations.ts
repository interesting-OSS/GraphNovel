import { api } from './client';
import type { Organization } from '../types/organization';

export function listOrganizations(projectId: string) { return api.get<{ items: Organization[]; total: number }>(`/organizations/project/${projectId}`); }
export function getOrganization(id: string) { return api.get<Organization>(`/organizations/${id}`); }
export function createOrganization(data: Record<string, unknown>) { return api.post<{ id: string }>('/organizations', data); }
export function updateOrganization(id: string, data: Record<string, unknown>) { return api.put<{ id: string; updated: boolean }>(`/organizations/${id}`, data); }
export function deleteOrganization(id: string) { return api.delete<{ deleted: boolean }>(`/organizations/${id}`); }
