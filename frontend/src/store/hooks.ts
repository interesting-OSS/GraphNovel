import { useCallback } from 'react';
import { message } from 'antd';
import { useStore } from './index';
import * as api from '../services/api';

function handleError(error: unknown, fallback: string) {
  // Axios interceptor already shows toast; just log
  console.error(fallback, error);
}

export function useProjectSync() {
  const { setProjects } = useStore();

  const refreshProjects = useCallback(async () => {
    try {
      const data: any = await api.projectApi.list();
      setProjects(data.items || []);
    } catch (error) {
      handleError(error, '获取项目列表失败');
    }
  }, [setProjects]);

  const createProject = useCallback(async (projectData: Parameters<typeof api.projectApi.create>[0]) => {
    try {
      const result = await api.projectApi.create(projectData);
      message.success('项目创建成功');
      await refreshProjects();
      return result;
    } catch (error) {
      handleError(error, '创建项目失败');
      return null;
    }
  }, [refreshProjects]);

  const updateProject = useCallback(async (id: string, data: Record<string, unknown>) => {
    try {
      await api.projectApi.update(id, data);
      message.success('项目已更新');
      await refreshProjects();
    } catch (error) {
      handleError(error, '更新项目失败');
    }
  }, [refreshProjects]);

  const deleteProject = useCallback(async (id: string) => {
    try {
      await api.projectApi.delete(id);
      message.success('项目已删除');
      await refreshProjects();
    } catch (error) {
      handleError(error, '删除项目失败');
    }
  }, [refreshProjects]);

  return { refreshProjects, createProject, updateProject, deleteProject };
}

export function useOutlineSync() {
  const { setOutlines } = useStore();

  const refreshOutlines = useCallback(async (projectId: string) => {
    try {
      const data: any = await api.outlineApi.list(projectId);
      setOutlines(data.items || []);
    } catch (error) {
      handleError(error, '获取大纲失败');
    }
  }, [setOutlines]);

  const createOutline = useCallback(async (data: Record<string, unknown>) => {
    try {
      await api.outlineApi.create(data);
      message.success('大纲已创建');
      if (data.project_id) await refreshOutlines(data.project_id as string);
    } catch (error) {
      handleError(error, '创建大纲失败');
    }
  }, [refreshOutlines]);

  const updateOutline = useCallback(async (id: string, data: Record<string, unknown>) => {
    try {
      await api.outlineApi.update(id, data);
      message.success('大纲已更新');
      if (data.project_id) await refreshOutlines(data.project_id as string);
    } catch (error) {
      handleError(error, '更新大纲失败');
    }
  }, [refreshOutlines]);

  const deleteOutline = useCallback(async (id: string, projectId: string) => {
    try {
      await api.outlineApi.delete(id);
      message.success('大纲已删除');
      await refreshOutlines(projectId);
    } catch (error) {
      handleError(error, '删除大纲失败');
    }
  }, [refreshOutlines]);

  return { refreshOutlines, createOutline, updateOutline, deleteOutline };
}

export function useCharacterSync() {
  const { setCharacters } = useStore();

  const refreshCharacters = useCallback(async (projectId: string) => {
    try {
      const data: any = await api.characterApi.list(projectId);
      setCharacters(data.items || []);
    } catch (error) {
      handleError(error, '获取角色失败');
    }
  }, [setCharacters]);

  const createCharacter = useCallback(async (data: Record<string, unknown>) => {
    try {
      await api.characterApi.create(data);
      message.success('角色已创建');
      if (data.project_id) await refreshCharacters(data.project_id as string);
    } catch (error) {
      handleError(error, '创建角色失败');
    }
  }, [refreshCharacters]);

  const updateCharacter = useCallback(async (id: string, data: Record<string, unknown>) => {
    try {
      await api.characterApi.update(id, data);
      message.success('角色已更新');
      if (data.project_id) await refreshCharacters(data.project_id as string);
    } catch (error) {
      handleError(error, '更新角色失败');
    }
  }, [refreshCharacters]);

  const deleteCharacter = useCallback(async (id: string, projectId: string) => {
    try {
      await api.characterApi.delete(id);
      message.success('角色已删除');
      await refreshCharacters(projectId);
    } catch (error) {
      handleError(error, '删除角色失败');
    }
  }, [refreshCharacters]);

  return { refreshCharacters, createCharacter, updateCharacter, deleteCharacter };
}

export function useChapterSync() {
  const { setChapters } = useStore();

  const refreshChapters = useCallback(async (projectId: string) => {
    try {
      const data: any = await api.chapterApi.list(projectId);
      setChapters(data.items || []);
    } catch (error) {
      handleError(error, '获取章节失败');
    }
  }, [setChapters]);

  const createChapter = useCallback(async (data: Record<string, unknown>) => {
    try {
      await api.chapterApi.create(data);
      message.success('章节已创建');
      if (data.project_id) await refreshChapters(data.project_id as string);
    } catch (error) {
      handleError(error, '创建章节失败');
    }
  }, [refreshChapters]);

  const updateChapter = useCallback(async (id: string, data: Record<string, unknown>) => {
    try {
      await api.chapterApi.update(id, data);
      message.success('章节已更新');
      if (data.project_id) await refreshChapters(data.project_id as string);
    } catch (error) {
      handleError(error, '更新章节失败');
    }
  }, [refreshChapters]);

  const deleteChapter = useCallback(async (id: string, projectId: string) => {
    try {
      await api.chapterApi.delete(id);
      message.success('章节已删除');
      await refreshChapters(projectId);
    } catch (error) {
      handleError(error, '删除章节失败');
    }
  }, [refreshChapters]);

  return { refreshChapters, createChapter, updateChapter, deleteChapter };
}
