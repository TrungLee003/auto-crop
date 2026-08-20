import { create } from 'zustand';
import { Job } from '../types/job';

interface JobState {
  activeJobs: Job[];
  completedJobs: Job[];

  addJob: (job: Job) => void;
  updateJobProgress: (id: string, progress: number, status?: Job['status']) => void;
  removeJob: (id: string) => void;
}

export const useJobStore = create<JobState>((set) => ({
  activeJobs: [],
  completedJobs: [],

  addJob: (job) => set((state) => ({ activeJobs: [...state.activeJobs, job] })),

  updateJobProgress: (id, progress, status) =>
    set((state) => {
      const updatedJobs = state.activeJobs.map((j) =>
        j.id === id ? { ...j, progress, status: status || j.status } : j
      );

      // Move to completed if finished or failed
      const finishedJob = updatedJobs.find(
        (j) => j.id === id && (j.status === 'completed' || j.status === 'failed')
      );
      if (finishedJob) {
        return {
          activeJobs: updatedJobs.filter((j) => j.id !== id),
          completedJobs: [...state.completedJobs, finishedJob],
        };
      }

      return { activeJobs: updatedJobs };
    }),

  removeJob: (id) =>
    set((state) => ({
      activeJobs: state.activeJobs.filter((j) => j.id !== id),
      completedJobs: state.completedJobs.filter((j) => j.id !== id),
    })),
}));
