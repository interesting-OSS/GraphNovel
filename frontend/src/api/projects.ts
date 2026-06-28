import { api } from './client';
import type { Project, ProjectSummary, CreateProjectData } from '../types/project';

export function listProjects() { return api.get<{ items: ProjectSummary[]; total: number }>('/projects'); }
export function getProject(id: string) { return api.get<Project>(`/projects/${id}`); }
export function createProject(data: CreateProjectData) { return api.post<{ id: string; title: string; message?: string }>('/projects', data); }
export function updateProject(id: string, data: Partial<Project>) { return api.put<{ id: string; updated: boolean }>(`/projects/${id}`, data); }
export function deleteProject(id: string) { return api.delete<{ deleted: boolean }>(`/projects/${id}`); }
