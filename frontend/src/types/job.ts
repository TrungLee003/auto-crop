export type JobType = 'detection' | 'export' | 'processing';
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface Job {
  id: string;
  type: JobType;
  status: JobStatus;
  progress: number; // 0 to 100
  message?: string;
  createdAt: string;
  updatedAt: string;
}
