export type PageStatus =
  'NEW' | 'PROCESSING' | 'DETECTED' | 'IN_REVIEW' | 'REVIEWED' | 'EXPORTED' | 'FAILED';

export type ImportMode = 'COPY' | 'REFERENCE';

export interface PageModel {
  id: string;
  project_id: string;
  sequence: number;
  filename: string;
  source_path: string;
  master_path: string;
  status: PageStatus;
  width: number;
  height: number;
  dpi: number;
  bit_depth: number;
  bands: number;
  file_size_bytes: number;
  file_hash: string;
  thumbnail_path?: string;
  dzi_path?: string;
  annotation_path?: string;
  region_count: number;
  warnings: string[];
  created_at: string;
  updated_at: string;
}

export interface DetectionSettings {
  provider: string;
  profile: string;
  sensitivity: number;
  min_area_ratio: number;
  working_long_edge: number;
}

export interface EditorSettings {
  default_padding_top: number;
  default_padding_right: number;
  default_padding_bottom: number;
  default_padding_left: number;
  autosave_delay_ms: number;
  polygon_simplification_tolerance: number;
}

export interface ExportSettings {
  default_preset: string;
  archive_format: string;
  transparent_png: boolean;
  scale: number;
}

export interface VectorSettings {
  vectorizer: string;
  preset: string;
  colormode: string;
  filter_speckle: number;
}

export interface ProjectSettings {
  detection: DetectionSettings;
  editor: EditorSettings;
  export: ExportSettings;
  vector: VectorSettings;
}

export interface ProjectSchema {
  schema_version: number;
  project_id: string;
  name: string;
  root_path: string;
  created_at: string;
  updated_at: string;
  settings: ProjectSettings;
  pages: PageModel[];
}

export interface ProjectResponse {
  project_id: string;
  name: string;
  root_path: string;
  page_count: number;
  created_at: string;
  updated_at: string;
  settings: ProjectSettings;
}

export interface PageViewerInfo {
  page_id: string;
  project_id: string;
  filename: string;
  master_width: number;
  master_height: number;
  dpi: number;
  dzi_url: string;
  thumbnail_url: string;
}

export interface ImportResult {
  imported_count: number;
  skipped_duplicates: number;
  failed_count: number;
  pages: PageModel[];
  errors: string[];
}
