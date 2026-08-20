import { create } from 'zustand';
import { Padding, RegionExportSettings, RegionModel, RegionStatus } from '../types/region';
import { RegionGeometry } from '../types/geometry';
import * as api from '../api/client';
import { usePageStore } from './pageStore';

export type ToolType = 'select' | 'rectangle' | 'rotated_rect' | 'polygon' | 'lasso';
export type SaveStatus = 'saved' | 'saving' | 'error';

function generateRegionId(): string {
  try {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID().slice(0, 8);
    }
  } catch {
    // fallback
  }
  return Math.random().toString(36).substring(2, 10);
}

function syncPageRegionCount(pageId: string | null, count: number) {
  if (!pageId) return;
  const pageState = usePageStore.getState();
  const current = pageState.currentPage;
  const updatedPages = pageState.pages.map((p) => {
    if (p.id === pageId) {
      const newStatus = p.status === 'NEW' && count > 0 ? ('IN_REVIEW' as const) : p.status;
      return { ...p, region_count: count, status: newStatus };
    }
    return p;
  });

  const updatedCurrent =
    current && current.id === pageId
      ? {
          ...current,
          region_count: count,
          status: current.status === 'NEW' && count > 0 ? ('IN_REVIEW' as const) : current.status,
        }
      : current;

  usePageStore.setState({ pages: updatedPages, currentPage: updatedCurrent });
}

interface AnnotationState {
  currentPageId: string | null;
  regions: RegionModel[];
  selectedRegionId: string | null;
  selectedRegionIds: string[]; // For multi-select / merge
  activeTool: ToolType;

  // History
  undoStack: RegionModel[][];
  redoStack: RegionModel[][];

  // Persistence status
  saveStatus: SaveStatus;
  isDirty: boolean;
  isLoading: boolean;
  isFitting: boolean;
  isDetecting: boolean;
  error: string | null;

  // Actions
  loadRegions: (pageId: string) => Promise<void>;
  setSelectedRegionId: (id: string | null) => void;
  toggleRegionSelection: (id: string) => void;
  clearSelection: () => void;
  setActiveTool: (tool: ToolType) => void;

  addRegion: (geometry: RegionGeometry, status?: RegionStatus) => void;
  setRegionGeometryLive: (id: string, geometry: RegionGeometry) => void;
  updateRegionGeometry: (id: string, geometry: RegionGeometry) => void;
  updateRegionAngle: (id: string, angle: number) => void;
  updateRegionPadding: (id: string, padding: Partial<Padding>) => void;
  updateRegionExport: (id: string, exportSettings: Partial<RegionExportSettings>) => void;
  updateRegionStatus: (id: string, status: RegionStatus) => void;
  deleteRegion: (id: string) => void;
  duplicateRegion: (id: string) => void;
  nudgeRegion: (id: string, dx: number, dy: number) => void;

  // Custom Tools Actions
  fitSelectedRegion: () => Promise<void>;
  mergeSelectedRegions: () => Promise<void>;

  // Auto-detection Actions
  detectCurrentPage: (config?: any) => Promise<void>;
  approveAllPageRegions: () => Promise<void>;

  // History actions
  undo: () => void;
  redo: () => void;

  // Manual & debounced saving
  saveNow: () => Promise<void>;
}

const MAX_HISTORY = 100;
let autosaveTimeout: NodeJS.Timeout | null = null;

export const useAnnotationStore = create<AnnotationState>((set, get) => {
  const scheduleAutosave = () => {
    const pageId = get().currentPageId;
    if (!pageId) return;

    set({ isDirty: true });

    if (autosaveTimeout) {
      clearTimeout(autosaveTimeout);
    }

    autosaveTimeout = setTimeout(async () => {
      const currentRegions = get().regions;
      const currentPage = get().currentPageId;
      if (!currentPage) return;

      set({ saveStatus: 'saving' });
      try {
        await api.saveRegions(currentPage, currentRegions);
        set({ saveStatus: 'saved', isDirty: false });
      } catch (err) {
        console.error('Autosave failed', err);
        set({ saveStatus: 'error' });
      }
    }, 600);
  };

  const pushSnapshot = () => {
    const current = get().regions.map((r) => JSON.parse(JSON.stringify(r)));
    const history = get().undoStack;
    set({
      undoStack: [...history.slice(-(MAX_HISTORY - 1)), current],
      redoStack: [], // clear redo
    });
  };

  return {
    currentPageId: null,
    regions: [],
    selectedRegionId: null,
    selectedRegionIds: [],
    activeTool: 'select',
    undoStack: [],
    redoStack: [],
    saveStatus: 'saved',
    isDirty: false,
    isLoading: false,
    isFitting: false,
    isDetecting: false,
    error: null,

    loadRegions: async (pageId: string) => {
      set({
        currentPageId: pageId,
        isLoading: true,
        error: null,
        selectedRegionId: null,
        selectedRegionIds: [],
        undoStack: [],
        redoStack: [],
        saveStatus: 'saved',
        isDirty: false,
      });

      try {
        const regions = await api.fetchRegions(pageId);
        set({ regions, isLoading: false });
        syncPageRegionCount(pageId, regions.length);
      } catch (err: any) {
        set({ error: err.message || 'Failed to load regions', isLoading: false });
      }
    },

    setSelectedRegionId: (id) =>
      set({
        selectedRegionId: id,
        selectedRegionIds: id ? [id] : [],
      }),

    toggleRegionSelection: (id) => {
      const current = get().selectedRegionIds;
      const next = current.includes(id) ? current.filter((x) => x !== id) : [...current, id];
      set({
        selectedRegionIds: next,
        selectedRegionId: next.length > 0 ? next[next.length - 1] : null,
      });
    },

    clearSelection: () => set({ selectedRegionId: null, selectedRegionIds: [] }),
    setActiveTool: (tool) => set({ activeTool: tool }),

    addRegion: (geometry, status = 'EDITED') => {
      pushSnapshot();
      const current = get().regions;
      const newRegion: RegionModel = {
        id: generateRegionId(),
        sequence: current.length + 1,
        geometry,
        source: 'manual',
        status,
        tags: [],
        padding: { top: 40, right: 40, bottom: 40, left: 40 },
        export: { archive: true, clean: true, vector: false },
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      const nextRegions = [...current, newRegion];
      set({
        regions: nextRegions,
        selectedRegionId: newRegion.id,
        selectedRegionIds: [newRegion.id],
      });
      syncPageRegionCount(get().currentPageId, nextRegions.length);
      scheduleAutosave();
    },

    setRegionGeometryLive: (id, geometry) => {
      set({
        regions: get().regions.map((r) =>
          r.id === id
            ? {
                ...r,
                geometry,
                status: r.status === 'AUTO' ? 'EDITED' : r.status,
              }
            : r
        ),
      });
    },

    updateRegionGeometry: (id, geometry) => {
      pushSnapshot();
      set({
        regions: get().regions.map((r) =>
          r.id === id
            ? {
                ...r,
                geometry,
                status: r.status === 'AUTO' ? 'EDITED' : r.status,
                updated_at: new Date().toISOString(),
              }
            : r
        ),
      });
      scheduleAutosave();
    },

    updateRegionAngle: (id, angle) => {
      pushSnapshot();
      set({
        regions: get().regions.map((r) => {
          if (r.id !== id) return r;
          if (r.geometry.type === 'rotated_rectangle') {
            return {
              ...r,
              geometry: { ...r.geometry, angle },
              status: r.status === 'AUTO' ? 'EDITED' : r.status,
              updated_at: new Date().toISOString(),
            };
          } else if (r.geometry.type === 'rectangle') {
            // Convert to rotated rectangle
            return {
              ...r,
              geometry: {
                type: 'rotated_rectangle',
                cx: r.geometry.x + r.geometry.width / 2,
                cy: r.geometry.y + r.geometry.height / 2,
                width: r.geometry.width,
                height: r.geometry.height,
                angle,
              },
              status: r.status === 'AUTO' ? 'EDITED' : r.status,
              updated_at: new Date().toISOString(),
            };
          }
          return r;
        }),
      });
      scheduleAutosave();
    },

    updateRegionPadding: (id, paddingPartial) => {
      pushSnapshot();
      set({
        regions: get().regions.map((r) =>
          r.id === id
            ? {
                ...r,
                padding: { ...r.padding, ...paddingPartial },
                updated_at: new Date().toISOString(),
              }
            : r
        ),
      });
      scheduleAutosave();
    },

    updateRegionExport: (id, exportPartial) => {
      pushSnapshot();
      set({
        regions: get().regions.map((r) =>
          r.id === id
            ? {
                ...r,
                export: { ...r.export, ...exportPartial },
                updated_at: new Date().toISOString(),
              }
            : r
        ),
      });
      scheduleAutosave();
    },

    updateRegionStatus: (id, status) => {
      pushSnapshot();
      set({
        regions: get().regions.map((r) =>
          r.id === id
            ? {
                ...r,
                status,
                updated_at: new Date().toISOString(),
              }
            : r
        ),
      });
      scheduleAutosave();
    },

    deleteRegion: (id) => {
      pushSnapshot();
      const filtered = get().regions.filter((r) => r.id !== id);
      const resequenced = filtered.map((r, idx) => ({ ...r, sequence: idx + 1 }));
      set({
        regions: resequenced,
        selectedRegionId: get().selectedRegionId === id ? null : get().selectedRegionId,
        selectedRegionIds: get().selectedRegionIds.filter((x) => x !== id),
      });
      syncPageRegionCount(get().currentPageId, resequenced.length);
      scheduleAutosave();
    },

    duplicateRegion: (id) => {
      const target = get().regions.find((r) => r.id === id);
      if (!target) return;

      pushSnapshot();
      const current = get().regions;
      let newGeom = { ...target.geometry };

      // Offset by +30px
      if (newGeom.type === 'rectangle') {
        newGeom = { ...newGeom, x: newGeom.x + 30, y: newGeom.y + 30 };
      } else if (newGeom.type === 'rotated_rectangle') {
        newGeom = { ...newGeom, cx: newGeom.cx + 30, cy: newGeom.cy + 30 };
      } else if (newGeom.type === 'polygon') {
        newGeom = {
          ...newGeom,
          points: newGeom.points.map(([px, py]) => [px + 30, py + 30]),
        };
      }

      const duplicated: RegionModel = {
        id: generateRegionId(),
        sequence: current.length + 1,
        geometry: newGeom,
        source: 'manual',
        status: 'EDITED',
        tags: [...target.tags],
        padding: { ...target.padding },
        export: { ...target.export },
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      const next = [...current, duplicated];
      set({
        regions: next,
        selectedRegionId: duplicated.id,
        selectedRegionIds: [duplicated.id],
      });
      syncPageRegionCount(get().currentPageId, next.length);
      scheduleAutosave();
    },

    nudgeRegion: (id, dx, dy) => {
      pushSnapshot();
      set({
        regions: get().regions.map((r) => {
          if (r.id !== id) return r;
          const geom = r.geometry;
          let nudged = { ...geom };

          if (geom.type === 'rectangle') {
            nudged = { ...geom, x: geom.x + dx, y: geom.y + dy };
          } else if (geom.type === 'rotated_rectangle') {
            nudged = { ...geom, cx: geom.cx + dx, cy: geom.cy + dy };
          } else if (geom.type === 'polygon') {
            nudged = {
              ...geom,
              points: geom.points.map(([px, py]) => [px + dx, py + dy]),
            };
          }

          return {
            ...r,
            geometry: nudged as RegionGeometry,
            updated_at: new Date().toISOString(),
          };
        }),
      });
      scheduleAutosave();
    },

    fitSelectedRegion: async () => {
      const { selectedRegionId, currentPageId, regions } = get();
      if (!selectedRegionId || !currentPageId) return;

      pushSnapshot();
      set({ isFitting: true });

      try {
        const fitted = await api.fitRegion(currentPageId, selectedRegionId);
        set({
          regions: regions.map((r) => (r.id === selectedRegionId ? fitted : r)),
          isFitting: false,
        });
      } catch (err) {
        console.error('Fit region failed', err);
        set({ isFitting: false });
      }
    },

    mergeSelectedRegions: async () => {
      const { selectedRegionIds, currentPageId } = get();
      if (!currentPageId || selectedRegionIds.length < 2) return;

      pushSnapshot();
      try {
        const merged = await api.mergeRegions(currentPageId, selectedRegionIds);
        const current = get().regions.filter((r) => !selectedRegionIds.includes(r.id));
        const updated = [...current, merged].map((r, idx) => ({
          ...r,
          sequence: idx + 1,
        }));
        set({
          regions: updated,
          selectedRegionId: merged.id,
          selectedRegionIds: [merged.id],
        });
        syncPageRegionCount(currentPageId, updated.length);
      } catch (err) {
        console.error('Merge failed', err);
      }
    },

    detectCurrentPage: async (config) => {
      const pageId = get().currentPageId;
      if (!pageId) return;

      pushSnapshot();
      set({ isDetecting: true });

      try {
        const detected = await api.detectPage(pageId, config);
        set({
          regions: detected,
          isDetecting: false,
          selectedRegionId: detected.length > 0 ? detected[0].id : null,
          selectedRegionIds: detected.length > 0 ? [detected[0].id] : [],
        });
        syncPageRegionCount(pageId, detected.length);
      } catch (err) {
        console.error('Detection failed', err);
        set({ isDetecting: false });
      }
    },

    approveAllPageRegions: async () => {
      const pageId = get().currentPageId;
      if (!pageId) return;

      pushSnapshot();
      try {
        const approved = await api.approveAllRegions(pageId);
        set({ regions: approved });
        syncPageRegionCount(pageId, approved.length);
      } catch (err) {
        console.error('Approve all failed', err);
      }
    },

    undo: () => {
      const { undoStack, regions, redoStack, currentPageId } = get();
      if (undoStack.length === 0) return;

      const previous = undoStack[undoStack.length - 1];
      const newUndo = undoStack.slice(0, -1);
      const current = regions.map((r) => JSON.parse(JSON.stringify(r)));

      set({
        regions: previous,
        undoStack: newUndo,
        redoStack: [...redoStack, current],
      });
      syncPageRegionCount(currentPageId, previous.length);
      scheduleAutosave();
    },

    redo: () => {
      const { redoStack, regions, undoStack, currentPageId } = get();
      if (redoStack.length === 0) return;

      const next = redoStack[redoStack.length - 1];
      const newRedo = redoStack.slice(0, -1);
      const current = regions.map((r) => JSON.parse(JSON.stringify(r)));

      set({
        regions: next,
        redoStack: newRedo,
        undoStack: [...undoStack, current],
      });
      syncPageRegionCount(currentPageId, next.length);
      scheduleAutosave();
    },

    saveNow: async () => {
      const pageId = get().currentPageId;
      if (!pageId) return;

      set({ saveStatus: 'saving' });
      try {
        await api.saveRegions(pageId, get().regions);
        set({ saveStatus: 'saved', isDirty: false });
      } catch (err) {
        console.error('Manual save failed', err);
        set({ saveStatus: 'error' });
      }
    },
  };
});
