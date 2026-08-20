export interface VTracerParams {
  colormode: 'bw' | 'color' | 'binary';
  mode: 'spline' | 'polygon' | 'none';
  filter_speckle: number;
  color_precision: number;
  layer_difference: number;
  corner_threshold: number;
  length_threshold: number;
  max_iterations: number;
  splice_threshold: number;
  path_precision: number;
}

export interface VTracerPreset {
  id: string;
  name: string;
  description: string;
  params: VTracerParams;
}

export interface VectorPreviewResult {
  svg_content: string;
  path_count: number;
  width: number;
  height: number;
  file_size_bytes: number;
  elapsed_ms: number;
  preset_id: string;
  params: VTracerParams;
}
