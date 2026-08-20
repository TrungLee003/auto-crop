export type ExportScope = 'APPROVED_ONLY' | 'ALL_EXCEPT_REJECTED' | 'ALL';

export interface ExportFormatOptions {
  archive: boolean;
  clean: boolean;
  vector: boolean;
}

export interface ExportRequest {
  scope: ExportScope;
  formats: ExportFormatOptions;
  archive_format: 'PNG' | 'TIFF';
  custom_output_dir?: string | null;
}

export interface ExportJobSummary {
  export_id: string;
  export_dir: string;
  total_regions: number;
  archive_count: number;
  clean_count: number;
  vector_count: number;
  exported_at: string;
}
