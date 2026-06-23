import axios from 'axios';
import { message } from 'antd';

const client = axios.create({
  baseURL: '/api',
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
});

// Interceptor unwraps response.data so callers get the body directly.
// Using explicit `any` because axios type system cannot express this unwrap.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const _unwrap = (response: any) => response.data;
client.interceptors.response.use(_unwrap,
  (error) => {
    const detail = error.response?.data?.detail || error.message || '未知错误';
    if (error.response?.status === 500) {
      message.error(`服务器错误: ${detail}`);
    } else if (!error.response) {
      message.error('网络错误，请检查网络连接');
    } else {
      message.error(detail);
    }
    return Promise.reject(error);
  },
);

/* ===== Project API ===== */
export const projectApi = {
  list: () => client.get('/projects'),
  create: (data: Record<string, unknown>) => client.post('/projects', data),
  get: (id: string) => client.get(`/projects/${id}`),
  update: (id: string, data: Record<string, unknown>) => client.put(`/projects/${id}`, data),
  delete: (id: string) => client.delete(`/projects/${id}`),
  export: (id: string) => client.post(`/projects/${id}/export`),
  import: (data: Record<string, unknown>) => client.post('/projects/import', data),
  generateCover: (id: string, data: Record<string, unknown>) => client.post(`/projects/${id}/generate-cover`, data),
};

/* ===== Outline API ===== */
export const outlineApi = {
  list: (projectId: string) => client.get(`/outlines/project/${projectId}`),
  create: (data: Record<string, unknown>) => client.post('/outlines', data),
  update: (id: string, data: Record<string, unknown>) => client.put(`/outlines/${id}`, data),
  delete: (id: string) => client.delete(`/outlines/${id}`),
  reorder: (data: Record<string, unknown>) => client.post('/outlines/reorder', data),
  generate: (data: Record<string, unknown>) => client.post('/outlines/generate', data),
};

/* ===== Character API ===== */
export const characterApi = {
  list: (projectId: string) => client.get(`/characters/project/${projectId}`),
  create: (data: Record<string, unknown>) => client.post('/characters', data),
  get: (id: string) => client.get(`/characters/${id}`),
  update: (id: string, data: Record<string, unknown>) => client.put(`/characters/${id}`, data),
  delete: (id: string) => client.delete(`/characters/${id}`),
  generate: (data: Record<string, unknown>) => client.post('/characters/generate', data),
};

/* ===== Chapter API ===== */
export const chapterApi = {
  list: (projectId: string) => client.get(`/chapters/project/${projectId}`),
  create: (data: Record<string, unknown>) => client.post('/chapters', data),
  get: (id: string) => client.get(`/chapters/${id}`),
  update: (id: string, data: Record<string, unknown>) => client.put(`/chapters/${id}`, data),
  delete: (id: string) => client.delete(`/chapters/${id}`),
  batchGenerate: (projectId: string, data: Record<string, unknown>) =>
    client.post(`/chapters/project/${projectId}/batch-generate`, data),
  getGenerationHistory: (chapterId: string) => client.get(`/chapters/${chapterId}/generation-history`),
};

/* ===== Settings API ===== */
export const settingsApi = {
  get: () => client.get('/settings'),
  save: (data: Record<string, unknown>) => client.put('/settings', data),
  getModels: (provider: string) => client.get(`/settings/available-models?provider=${provider}`),
  testConnection: (data: Record<string, unknown>) => client.post('/settings/test-connection', data),
  listPresets: () => client.get('/settings/presets'),
};

/* ===== Foreshadow API ===== */
export const foreshadowApi = {
  list: (projectId: string) => client.get(`/foreshadows/project/${projectId}`),
  create: (data: Record<string, unknown>) => client.post('/foreshadows', data),
  update: (id: string, data: Record<string, unknown>) => client.put(`/foreshadows/${id}`, data),
  delete: (id: string) => client.delete(`/foreshadows/${id}`),
};

/* ===== Task API ===== */
export const taskApi = {
  list: (projectId?: string) => client.get(`/tasks${projectId ? `?project_id=${projectId}` : ''}`),
  get: (taskId: string) => client.get(`/tasks/${taskId}`),
  cancel: (taskId: string) => client.post(`/tasks/${taskId}/cancel`),
  delete: (taskId: string) => client.delete(`/tasks/${taskId}`),
};

/* ===== Graph Status API ===== */
export const graphStatusApi = {
  getState: (projectId: string) => client.get(`/graph-status/state/${projectId}`),
  getVisualization: (projectId: string) => client.get(`/graph-status/visualization/${projectId}`),
  getMetrics: (projectId: string) => client.get(`/graph-status/metrics/${projectId}`),
  getHistory: (projectId: string) => client.get(`/graph-status/history/${projectId}`),
};

/* ===== Career API ===== */
export const careerApi = {
  list: (projectId: string) => client.get(`/careers/project/${projectId}`),
  create: (data: Record<string, unknown>) => client.post('/careers', data),
  update: (id: string, data: Record<string, unknown>) => client.put(`/careers/${id}`, data),
  delete: (id: string) => client.delete(`/careers/${id}`),
  generate: (data: Record<string, unknown>) => client.post('/careers/generate', data),
};

/* ===== Organization API ===== */
export const organizationApi = {
  list: (projectId: string) => client.get(`/organizations/project/${projectId}`),
  create: (data: Record<string, unknown>) => client.post('/organizations', data),
  update: (id: string, data: Record<string, unknown>) => client.put(`/organizations/${id}`, data),
  delete: (id: string) => client.delete(`/organizations/${id}`),
  generate: (data: Record<string, unknown>) => client.post('/organizations/generate', data),
};

/* ===== Relationship API ===== */
export const relationshipApi = {
  list: (projectId: string) => client.get(`/relationships/project/${projectId}`),
  create: (data: Record<string, unknown>) => client.post('/relationships', data),
  update: (id: string, data: Record<string, unknown>) => client.put(`/relationships/${id}`, data),
  delete: (id: string) => client.delete(`/relationships/${id}`),
};

/* ===== Memory API ===== */
export const memoryApi = {
  list: (projectId: string) => client.get(`/memories/project/${projectId}`),
  search: (projectId: string, params: Record<string, unknown>) =>
    client.get(`/memories/project/${projectId}/search`, { params }),
  getAnalysis: (projectId: string, chapterId: string) =>
    client.get(`/memories/project/${projectId}/analysis/${chapterId}`),
};

/* ===== Skill API ===== */
export const skillApi = {
  list: () => client.get('/skills/list'),
  chat: (data: Record<string, unknown>) => client.post('/skills/chat', data),
  get: (name: string) => client.get(`/skills/${name}`),
  create: (data: Record<string, unknown>) => client.post('/skills', data),
  delete: (name: string) => client.delete(`/skills/${name}`),
};

/* ===== Book Import API ===== */
export const bookImportApi = {
  upload: (formData: FormData) =>
    client.post('/book-import/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } }),
  preview: (taskId: string) => client.get(`/book-import/preview/${taskId}`),
  apply: (data: Record<string, unknown>) => client.post('/book-import/apply', data),
};

/* ===== Writing Style API ===== */
export const writingStyleApi = {
  list: () => client.get('/writing-styles'),
  presets: () => client.get('/writing-styles/presets'),
  create: (data: Record<string, unknown>) => client.post('/writing-styles', data),
  update: (id: string, data: Record<string, unknown>) => client.put(`/writing-styles/${id}`, data),
  delete: (id: string) => client.delete(`/writing-styles/${id}`),
};

/* ===== Prompt Template API ===== */
export const promptTemplateApi = {
  list: () => client.get('/prompt-templates'),
  categories: () => client.get('/prompt-templates/categories'),
  create: (data: Record<string, unknown>) => client.post('/prompt-templates', data),
  update: (id: string, data: Record<string, unknown>) => client.put(`/prompt-templates/${id}`, data),
  delete: (id: string) => client.delete(`/prompt-templates/${id}`),
};

/* ===== MCP Plugin API ===== */
export const mcpApi = {
  list: () => client.get('/mcp/plugins'),
  create: (data: Record<string, unknown>) => client.post('/mcp/plugins', data),
  update: (id: string, data: Record<string, unknown>) => client.put(`/mcp/plugins/${id}`, data),
  delete: (id: string) => client.delete(`/mcp/plugins/${id}`),
  toggle: (id: string) => client.post(`/mcp/plugins/${id}/toggle`),
  test: (id: string) => client.post(`/mcp/plugins/${id}/test`),
  getTools: (id: string) => client.get(`/mcp/plugins/${id}/tools`),
  callTool: (id: string, data: Record<string, unknown>) => client.post(`/mcp/plugins/${id}/tools/call`, data),
};

/* ===== Inspiration API ===== */
export const inspirationApi = {
  generate: (data: Record<string, unknown>) => client.post('/inspiration/generate', data),
  quickGenerate: (data: Record<string, unknown>) => client.post('/inspiration/quick-generate', data),
  save: (data: Record<string, unknown>) => client.post('/inspiration/save', data),
  saved: () => client.get('/inspiration/saved'),
  convertToProject: (id: string, data: Record<string, unknown>) =>
    client.post(`/inspiration/${id}/convert-to-project`, data),
};

/* ===== Wizard Stream API ===== */
export const wizardStreamApi = {
  worldBuilding: (data: Record<string, unknown>) => client.post('/wizard-stream/world-building', data),
  characters: (data: Record<string, unknown>) => client.post('/wizard-stream/characters', data),
  careers: (data: Record<string, unknown>) => client.post('/wizard-stream/careers', data),
  outline: (data: Record<string, unknown>) => client.post('/wizard-stream/outline', data),
};

/* ===== Project Covers API ===== */
export const coverApi = {
  generate: (projectId: string, data: Record<string, unknown>) =>
    client.post(`/projects/${projectId}/generate-cover`, data),
  download: (projectId: string) => client.get(`/projects/${projectId}/download-cover`),
  styles: () => client.get('/projects/cover-styles'),
};

/* ===== Polish API ===== */
export const polishApi = {
  text: (data: Record<string, unknown>) => client.post('/polish/text', data),
  batch: (data: Record<string, unknown>) => client.post('/polish/batch', data),
};

/* ===== Chapter extended API (non-CRUD) ===== */
export const chapterExtendedApi = {
  generateStream: (chapterId: string, data: Record<string, unknown>) =>
    client.post(`/chapters/${chapterId}/generate-stream`, data),
  analyze: (chapterId: string) => client.post(`/chapters/${chapterId}/analyze`),
  polish: (chapterId: string, data: Record<string, unknown>) => client.post(`/chapters/${chapterId}/polish`, data),
  rewrite: (chapterId: string, data: Record<string, unknown>) => client.post(`/chapters/${chapterId}/rewrite`, data),
  partialRegenerate: (chapterId: string, data: Record<string, unknown>) =>
    client.post(`/chapters/${chapterId}/partial-regenerate-stream`, data),
  getDiff: (chapterId: string, params: Record<string, unknown>) =>
    client.get(`/chapters/${chapterId}/diff`, { params }),
  review: (chapterId: string) => client.post(`/chapters/${chapterId}/review`),
};
