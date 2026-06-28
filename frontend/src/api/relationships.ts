import { api } from './client';
import type { CharacterRelationship } from '../types/organization';

export function listRelationships(projectId: string) { return api.get<{ items: CharacterRelationship[]; total: number }>(`/relationships/project/${projectId}`); }
export function createRelationship(data: Record<string, unknown>) { return api.post<{ id: string }>('/relationships', data); }
export function updateRelationship(id: string, data: Partial<CharacterRelationship>) { return api.put<{ id: string; updated: boolean }>(`/relationships/${id}`, data); }
export function deleteRelationship(id: string) { return api.delete<{ deleted: boolean }>(`/relationships/${id}`); }
