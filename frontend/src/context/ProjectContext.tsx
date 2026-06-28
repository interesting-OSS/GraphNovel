import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import { getProject as fetchProject, updateProject as updateProjectApi, deleteProject as deleteProjectApi } from '../api/projects';
import type { Project } from '../types/project';

interface ProjectContextValue {
  project: Project | null;
  loading: boolean;
  error: string | null;
  loadProject: (id: string) => Promise<void>;
  updateProject: (data: Partial<Project>) => Promise<void>;
  deleteProject: () => Promise<void>;
  clearProject: () => void;
}

const ProjectContext = createContext<ProjectContextValue | null>(null);

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadProject = useCallback(async (id: string) => {
    setLoading(true); setError(null);
    try { setProject(await fetchProject(id)); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setLoading(false); }
  }, []);

  const updateProject = useCallback(async (data: Partial<Project>) => {
    if (!project) return;
    await updateProjectApi(project.id, data);
    setProject(prev => prev ? { ...prev, ...data } : null);
  }, [project]);

  const deleteProject = useCallback(async () => {
    if (!project) return;
    await deleteProjectApi(project.id);
    setProject(null);
  }, [project]);

  const clearProject = useCallback(() => setProject(null), []);

  return (
    <ProjectContext.Provider value={{ project, loading, error, loadProject, updateProject, deleteProject, clearProject }}>
      {children}
    </ProjectContext.Provider>
  );
}

export function useProject() {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error('useProject must be used within ProjectProvider');
  return ctx;
}
