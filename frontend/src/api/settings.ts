import { api } from './client';
import type { GlobalSettings, WritingStyle } from '../types/settings';

export function getSettings() { return api.get<GlobalSettings>('/settings'); }
export function updateSettings(data: Partial<GlobalSettings>) { return api.put<{ saved: boolean }>('/settings', data); }
export function testConnection(data: Record<string, unknown>) { return api.post<{ success: boolean; preview: string; error?: string }>('/settings/test-connection', data); }
export function getWritingStyles() { return api.get<{ items: WritingStyle[]; total: number }>('/writing-styles'); }
export function getPresetWritingStyles() { return api.get<{ items: WritingStyle[] }>('/writing-styles/presets'); }
