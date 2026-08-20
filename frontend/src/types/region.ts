import { RegionGeometry } from './geometry';

export type RegionStatus = 'AUTO' | 'EDITED' | 'APPROVED' | 'REJECTED';

export interface Padding {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

export interface RegionExportSettings {
  archive: boolean;
  clean: boolean;
  vector: boolean;
}

export interface RegionModel {
  id: string;
  sequence: number;
  geometry: RegionGeometry;
  source: 'auto' | 'manual';
  status: RegionStatus;
  name?: string | null;
  tags: string[];
  padding: Padding;
  export: RegionExportSettings;
  confidence?: number | null;
  created_at?: string;
  updated_at?: string;
}
