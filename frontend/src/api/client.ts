import {
  ImportMode,
  ImportResult,
  PageModel,
  PageViewerInfo,
  ProjectResponse,
  ProjectSchema,
} from '../types/project';
import { RegionModel } from '../types/region';
import { DetectionConfig, TaskStatus } from '../types/detection';
import { ExportJobSummary, ExportRequest } from '../types/export';
import { VectorPreviewResult, VTracerPreset } from '../types/vector';

const API_BASE = '/api/v2';

export async function fetchProjects(): Promise<ProjectResponse[]> {
  const res = await fetch(`${API_BASE}/projects`);
  if (!res.ok) throw new Error('Failed to fetch projects list');
  return res.json();
}

export async function createProject(name: string, path?: string): Promise<ProjectSchema> {
  const res = await fetch(`${API_BASE}/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, path: path || null }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create project');
  }
  return res.json();
}

export async function openProject(path: string): Promise<ProjectSchema> {
  const res = await fetch(`${API_BASE}/projects/open`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to open project');
  }
  return res.json();
}

export async function deleteProject(
  projectId: string,
  deleteFiles: boolean = false
): Promise<void> {
  const res = await fetch(`${API_BASE}/projects/${projectId}?delete_files=${deleteFiles}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to delete project');
  }
}

export async function fetchProject(projectId: string): Promise<ProjectSchema> {
  const res = await fetch(`${API_BASE}/projects/${projectId}`);
  if (!res.ok) throw new Error('Failed to fetch project');
  return res.json();
}

export async function sortProjectPages(projectId: string): Promise<ProjectSchema> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/sort-pages`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to sort pages');
  }
  return res.json();
}

export async function importScans(
  projectId: string,
  filePaths: string[],
  folderPath?: string,
  mode: ImportMode = 'COPY',
  recursive: boolean = false
): Promise<ImportResult> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/imports`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      file_paths: filePaths,
      folder_path: folderPath || null,
      mode,
      recursive,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Import failed');
  }
  return res.json();
}

export async function fetchPages(projectId: string, statusFilter?: string): Promise<PageModel[]> {
  const url = new URL(`${window.location.origin}${API_BASE}/projects/${projectId}/pages`);
  if (statusFilter && statusFilter !== 'ALL') {
    url.searchParams.append('status', statusFilter);
  }
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error('Failed to fetch pages');
  return res.json();
}

export async function fetchPageViewer(pageId: string): Promise<PageViewerInfo> {
  const res = await fetch(`${API_BASE}/pages/${pageId}/viewer`);
  if (!res.ok) throw new Error('Failed to fetch page viewer metadata');
  return res.json();
}

export async function updatePageStatus(pageId: string, status: string): Promise<PageModel> {
  const res = await fetch(`${API_BASE}/pages/${pageId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
  if (!res.ok) throw new Error('Failed to update page status');
  return res.json();
}

export async function deletePage(pageId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/pages/${pageId}`, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to delete page');
  }
}

// Annotation / Regions API
export async function fetchRegions(pageId: string): Promise<RegionModel[]> {
  const res = await fetch(`${API_BASE}/pages/${pageId}/regions`);
  if (!res.ok) throw new Error('Failed to fetch regions');
  return res.json();
}

export async function saveRegions(pageId: string, regions: RegionModel[]): Promise<RegionModel[]> {
  const res = await fetch(`${API_BASE}/pages/${pageId}/regions`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(regions),
  });
  if (!res.ok) throw new Error('Failed to save regions');
  return res.json();
}

export async function addRegion(
  pageId: string,
  region: Partial<RegionModel>
): Promise<RegionModel> {
  const res = await fetch(`${API_BASE}/pages/${pageId}/regions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(region),
  });
  if (!res.ok) throw new Error('Failed to add region');
  return res.json();
}

export async function deleteRegion(pageId: string, regionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/pages/${pageId}/regions/${regionId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete region');
}

export async function fitRegion(pageId: string, regionId: string): Promise<RegionModel> {
  const res = await fetch(`${API_BASE}/pages/${pageId}/regions/${regionId}/fit`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to fit region');
  return res.json();
}

export async function mergeRegions(pageId: string, regionIds: string[]): Promise<RegionModel> {
  const res = await fetch(`${API_BASE}/pages/${pageId}/regions/merge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ region_ids: regionIds }),
  });
  if (!res.ok) throw new Error('Failed to merge regions');
  return res.json();
}

// Detection API
export async function detectPage(pageId: string, config?: DetectionConfig): Promise<RegionModel[]> {
  const res = await fetch(`${API_BASE}/pages/${pageId}/detect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config || null),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Auto-detection failed');
  }
  return res.json();
}

export async function approveAllRegions(pageId: string): Promise<RegionModel[]> {
  const res = await fetch(`${API_BASE}/pages/${pageId}/approve-all`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to approve all regions');
  return res.json();
}

export async function startBatchDetect(
  projectId: string,
  filterStatus: string = 'NEW',
  config?: DetectionConfig
): Promise<{ status: string; task_id: string }> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/batch-detect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      filter_status: filterStatus,
      config: config || null,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to start batch detection');
  }
  return res.json();
}

export async function fetchTaskStatus(taskId: string): Promise<TaskStatus> {
  const res = await fetch(`${API_BASE}/tasks/${taskId}`);
  if (!res.ok) throw new Error('Failed to fetch task status');
  return res.json();
}

export async function cancelTask(taskId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/tasks/${taskId}/cancel`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to cancel task');
}

// Export API
export async function startExport(
  projectId: string,
  req: ExportRequest
): Promise<{ status: string; task_id: string; export_dir: string; total_regions: number }> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Export failed');
  }
  return res.json();
}

export async function fetchProjectExports(projectId: string): Promise<ExportJobSummary[]> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/exports`);
  if (!res.ok) throw new Error('Failed to fetch export history');
  return res.json();
}

// Vector API (Phase 7)
export async function fetchVectorPresets(): Promise<VTracerPreset[]> {
  const res = await fetch(`${API_BASE}/vector/presets`);
  if (!res.ok) throw new Error('Failed to fetch vector presets');
  return res.json();
}

export async function previewVectorRegion(
  pageId: string,
  regionId: string,
  req?: { preset_id: string; custom_params?: any }
): Promise<VectorPreviewResult> {
  const res = await fetch(`${API_BASE}/pages/${pageId}/regions/${regionId}/vector-preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req || {}),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Vector preview failed');
  }
  return res.json();
}
