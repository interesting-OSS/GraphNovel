import { create } from 'zustand';
import type {
  Project, Outline, Character, Chapter, Career, Organization,
  CharacterRelationship, Foreshadow, BackgroundTask,
} from '../types';

interface AppState {
  currentProject: Project | null;
  setCurrentProject: (project: Project | null) => void;

  projects: Project[];
  setProjects: (projects: Project[]) => void;

  outlines: Outline[];
  setOutlines: (outlines: Outline[]) => void;

  characters: Character[];
  setCharacters: (characters: Character[]) => void;

  chapters: Chapter[];
  setChapters: (chapters: Chapter[]) => void;

  currentChapter: Chapter | null;
  setCurrentChapter: (chapter: Chapter | null) => void;

  careers: Career[];
  setCareers: (careers: Career[]) => void;

  organizations: Organization[];
  setOrganizations: (orgs: Organization[]) => void;

  relationships: CharacterRelationship[];
  setRelationships: (rels: CharacterRelationship[]) => void;

  foreshadows: Foreshadow[];
  setForeshadows: (fs: Foreshadow[]) => void;

  backgroundTasks: BackgroundTask[];
  setBackgroundTasks: (tasks: BackgroundTask[]) => void;

  loading: boolean;
  setLoading: (loading: boolean) => void;

  lastUpdated: Record<string, number>;
  setLastUpdated: (key: string) => void;
}

export const useStore = create<AppState>((set) => ({
  currentProject: null,
  setCurrentProject: (project) => set({ currentProject: project }),

  projects: [],
  setProjects: (projects) => set({ projects }),

  outlines: [],
  setOutlines: (outlines) => set({ outlines }),

  characters: [],
  setCharacters: (characters) => set({ characters }),

  chapters: [],
  setChapters: (chapters) => set({ chapters }),

  currentChapter: null,
  setCurrentChapter: (chapter) => set({ currentChapter: chapter }),

  careers: [],
  setCareers: (careers) => set({ careers }),

  organizations: [],
  setOrganizations: (organizations) => set({ organizations }),

  relationships: [],
  setRelationships: (relationships) => set({ relationships }),

  foreshadows: [],
  setForeshadows: (foreshadows) => set({ foreshadows }),

  backgroundTasks: [],
  setBackgroundTasks: (backgroundTasks) => set({ backgroundTasks }),

  loading: false,
  setLoading: (loading) => set({ loading }),

  lastUpdated: {},
  setLastUpdated: (key) =>
    set((state) => ({ lastUpdated: { ...state.lastUpdated, [key]: Date.now() } })),
}));
