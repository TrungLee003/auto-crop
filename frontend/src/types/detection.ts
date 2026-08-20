export interface DetectionConfig {
  preset: 'historical_line_art' | 'dense_woodcut' | 'custom';
  target_long_edge?: number;
  sensitivity?: number;
  min_area_ratio?: number;
  max_area_ratio?: number;
  text_suppression?: boolean;
  merge_distance?: number;
  padding_default?: number;
  min_confidence?: number;
}

export interface TaskStatus {
  task_id: string;
  task_type: string;
  status: 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number; // 0 to 100
  current_item: number;
  total_items: number;
  message: string;
  error?: string | null;
  created_at: string;
  completed_at?: string | null;
}
