import { api } from './client';
import type { Character, CharacterCreateData } from '../types/character';

export function listCharacters(projectId: string) { return api.get<{ items: Character[]; total: number }>(`/characters/project/${projectId}`); }
export function getCharacter(id: string) { return api.get<Character>(`/characters/${id}`); }
export function createCharacter(data: CharacterCreateData) { return api.post<{ id: string }>('/characters', data); }
export function updateCharacter(id: string, data: Partial<Character>) { return api.put<{ id: string; updated: boolean }>(`/characters/${id}`, data); }
export function deleteCharacter(id: string) { return api.delete<{ deleted: boolean }>(`/characters/${id}`); }
export function generateCharacters(data: Record<string, unknown>) { return api.post<{ status: string; characters: Character[] }>('/characters/generate', data); }
