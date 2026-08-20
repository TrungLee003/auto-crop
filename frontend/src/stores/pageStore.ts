import { create } from 'zustand';
import { PageModel, PageStatus, PageViewerInfo } from '../types/project';
import * as api from '../api/client';

export type PageFilter = 'ALL' | PageStatus;

interface PageState {
  pages: PageModel[];
  currentPage: PageModel | null;
  viewerInfo: PageViewerInfo | null;
  filter: PageFilter;
  isLoading: boolean;
  error: string | null;

  // Viewport tracking for status bar
  cursorPos: { x: number; y: number } | null;
  zoomLevel: number;

  setPages: (pages: PageModel[]) => void;
  loadPages: (projectId: string, filter?: PageFilter) => Promise<void>;
  selectPage: (pageId: string) => Promise<void>;
  setFilter: (filter: PageFilter) => void;
  navigatePage: (delta: number) => void;
  setCursorPos: (pos: { x: number; y: number } | null) => void;
  setZoomLevel: (zoom: number) => void;
  updateCurrentPageStatus: (status: PageStatus) => Promise<void>;
  deletePage: (pageId: string) => Promise<void>;
  sortPages: (projectId: string) => Promise<void>;
}

export const usePageStore = create<PageState>((set, get) => ({
  pages: [],
  currentPage: null,
  viewerInfo: null,
  filter: 'ALL',
  isLoading: false,
  error: null,
  cursorPos: null,
  zoomLevel: 1.0,

  setPages: (pages) => set({ pages }),

  loadPages: async (projectId: string, filter?: PageFilter) => {
    set({ isLoading: true, error: null });
    const currentFilter = filter || get().filter;
    try {
      const pages = await api.fetchPages(projectId, currentFilter);
      set({ pages, isLoading: false, filter: currentFilter });

      // If current page is no longer in list or none selected, select first
      const current = get().currentPage;
      if (pages.length > 0) {
        if (!current || !pages.some((p) => p.id === current.id)) {
          get().selectPage(pages[0].id);
        }
      } else {
        set({ currentPage: null, viewerInfo: null });
      }
    } catch (err: any) {
      set({ error: err.message || 'Failed to load pages', isLoading: false });
    }
  },

  selectPage: async (pageId: string) => {
    const page = get().pages.find((p) => p.id === pageId);
    if (!page) return;

    set({ currentPage: page, error: null });
    try {
      const viewerInfo = await api.fetchPageViewer(pageId);
      set({ viewerInfo });
    } catch (err: any) {
      console.error('Failed to load page viewer', err);
      set({ error: 'Failed to load high-res image tiles' });
    }
  },

  setFilter: (filter: PageFilter) => {
    set({ filter });
  },

  navigatePage: (delta: number) => {
    const { pages, currentPage } = get();
    if (!currentPage || pages.length === 0) return;

    const currentIndex = pages.findIndex((p) => p.id === currentPage.id);
    if (currentIndex === -1) return;

    const nextIndex = currentIndex + delta;
    if (nextIndex >= 0 && nextIndex < pages.length) {
      get().selectPage(pages[nextIndex].id);
    }
  },

  setCursorPos: (pos) => set({ cursorPos: pos }),
  setZoomLevel: (zoom) => set({ zoomLevel: zoom }),

  updateCurrentPageStatus: async (newStatus: PageStatus) => {
    const current = get().currentPage;
    if (!current) return;
    try {
      const updated = await api.updatePageStatus(current.id, newStatus);
      set({
        currentPage: updated,
        pages: get().pages.map((p) => (p.id === updated.id ? updated : p)),
      });
    } catch (err: any) {
      console.error('Failed to update status', err);
    }
  },

  deletePage: async (pageId: string) => {
    try {
      await api.deletePage(pageId);
      const remaining = get().pages.filter((p) => p.id !== pageId);
      set({ pages: remaining });

      if (get().currentPage?.id === pageId) {
        if (remaining.length > 0) {
          get().selectPage(remaining[0].id);
        } else {
          set({ currentPage: null, viewerInfo: null });
        }
      }
    } catch (err: any) {
      console.error('Failed to delete page', err);
      set({ error: err.message || 'Failed to delete page' });
    }
  },

  sortPages: async (projectId: string) => {
    set({ isLoading: true, error: null });
    try {
      const proj = await api.sortProjectPages(projectId);
      set({ pages: proj.pages, isLoading: false });
      if (proj.pages.length > 0 && !get().currentPage) {
        get().selectPage(proj.pages[0].id);
      }
    } catch (err: any) {
      set({ error: err.message || 'Failed to sort pages', isLoading: false });
    }
  },
}));

