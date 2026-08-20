import { create } from 'zustand';
import { ProjectSchema } from '../types/project';
import * as api from '../api/client';

interface ProjectState {
  currentProject: ProjectSchema | null;
  recentPaths: string[];
  isLoading: boolean;
  error: string | null;

  setProject: (project: ProjectSchema | null) => void;
  createProject: (name: string, path?: string) => Promise<ProjectSchema>;
  openProject: (path: string) => Promise<ProjectSchema>;
  closeProject: () => void;
  deleteProject: (projectId: string, deleteFiles?: boolean) => Promise<void>;
  removeRecentPath: (path: string) => void;
  refreshProject: () => Promise<void>;
  clearError: () => void;
}

const RECENT_KEY = 'illustration_extractor_recent_projects';

function getRecentPaths(): string[] {
  try {
    const raw = localStorage.getItem(RECENT_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveRecentPath(path: string) {
  try {
    const recents = getRecentPaths().filter((p) => p !== path);
    recents.unshift(path);
    localStorage.setItem(RECENT_KEY, JSON.stringify(recents.slice(0, 10)));
  } catch {
    // ignore storage errors
  }
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  currentProject: null,
  recentPaths: getRecentPaths(),
  isLoading: false,
  error: null,

  setProject: (project) => set({ currentProject: project }),

  createProject: async (name: string, path?: string) => {
    set({ isLoading: true, error: null });
    try {
      const project = await api.createProject(name, path);
      saveRecentPath(project.root_path);
      set({
        currentProject: project,
        recentPaths: getRecentPaths(),
        isLoading: false,
      });
      return project;
    } catch (err: any) {
      set({ error: err.message || 'Failed to create project', isLoading: false });
      throw err;
    }
  },

  openProject: async (path: string) => {
    set({ isLoading: true, error: null });
    try {
      const project = await api.openProject(path);
      saveRecentPath(project.root_path);
      set({
        currentProject: project,
        recentPaths: getRecentPaths(),
        isLoading: false,
      });
      return project;
    } catch (err: any) {
      set({ error: err.message || 'Failed to open project', isLoading: false });
      throw err;
    }
  },

  closeProject: () => {
    set({ currentProject: null });
  },

  deleteProject: async (projectId: string, deleteFiles: boolean = false) => {
    set({ isLoading: true, error: null });
    try {
      await api.deleteProject(projectId, deleteFiles);
      const current = get().currentProject;
      if (current && current.project_id === projectId) {
        get().removeRecentPath(current.root_path);
        set({ currentProject: null });
      }
      set({ isLoading: false });
    } catch (err: any) {
      set({ error: err.message || 'Failed to delete project', isLoading: false });
      throw err;
    }
  },

  removeRecentPath: (path: string) => {
    try {
      const recents = getRecentPaths().filter((p) => p !== path);
      localStorage.setItem(RECENT_KEY, JSON.stringify(recents));
      set({ recentPaths: recents });
    } catch {
      // ignore
    }
  },

  refreshProject: async () => {
    const current = get().currentProject;
    if (!current) return;
    try {
      const project = await api.fetchProject(current.project_id);
      set({ currentProject: project });
    } catch (err: any) {
      console.error('Failed to refresh project', err);
    }
  },

  clearError: () => set({ error: null }),
}));
