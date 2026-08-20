import { useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Theme } from '@radix-ui/themes';
import { Layout } from './components/Layout';
import { Toolbar } from './components/Toolbar';
import { StatusBar } from './components/StatusBar';
import { PageSidebar } from './pages/PageSidebar';
import { RegionPanel } from './review/RegionPanel';
import { DeepZoomViewer } from './viewer/DeepZoomViewer';
import { usePageStore } from './stores/pageStore';
import { useProjectStore } from './stores/projectStore';
import { useAnnotationStore } from './stores/annotationStore';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function MainApp() {
  const currentProject = useProjectStore((s) => s.currentProject);
  const { viewerInfo, loadPages, navigatePage } = usePageStore();
  const {
    activeTool,
    setActiveTool,
    selectedRegionId,
    setSelectedRegionId,
    updateRegionStatus,
    deleteRegion,
    duplicateRegion,
    fitSelectedRegion,
    nudgeRegion,
    approveAllPageRegions,
    undo,
    redo,
  } = useAnnotationStore();

  // Load pages when project changes
  useEffect(() => {
    if (currentProject) {
      loadPages(currentProject.project_id);
    }
  }, [currentProject, loadPages]);

  // Global Keyboard Shortcuts (Spec §57 & Phase 3)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Avoid intercepting input fields
      if (['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) {
        return;
      }

      // Tool selection shortcuts
      if (!e.ctrlKey && !e.metaKey && !e.altKey) {
        if (e.key.toLowerCase() === 'v') {
          e.preventDefault();
          setActiveTool('select');
        } else if (e.key.toLowerCase() === 'r') {
          e.preventDefault();
          setActiveTool('rectangle');
        } else if (e.key.toLowerCase() === 'o') {
          e.preventDefault();
          setActiveTool('rotated_rect');
        } else if (e.key.toLowerCase() === 'p') {
          e.preventDefault();
          setActiveTool('polygon');
        } else if (e.key.toLowerCase() === 'l') {
          e.preventDefault();
          setActiveTool('lasso');
        } else if (e.key.toLowerCase() === 'f' && selectedRegionId) {
          e.preventDefault();
          fitSelectedRegion();
        } else if (e.key === 'Escape') {
          e.preventDefault();
          setSelectedRegionId(null);
        } else if (e.key === 'Enter') {
          e.preventDefault();
          if (e.shiftKey) {
            approveAllPageRegions();
          } else if (selectedRegionId) {
            updateRegionStatus(selectedRegionId, 'APPROVED');
          }
        } else if ((e.key === 'Delete' || e.key === 'Backspace') && selectedRegionId) {
          e.preventDefault();
          deleteRegion(selectedRegionId);
        }

        // Nudge with arrow keys
        if (selectedRegionId) {
          const step = e.shiftKey ? 10 : 1;
          if (e.key === 'ArrowUp') {
            e.preventDefault();
            nudgeRegion(selectedRegionId, 0, -step);
          } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            nudgeRegion(selectedRegionId, 0, step);
          } else if (e.key === 'ArrowLeft') {
            e.preventDefault();
            nudgeRegion(selectedRegionId, -step, 0);
          } else if (e.key === 'ArrowRight') {
            e.preventDefault();
            nudgeRegion(selectedRegionId, step, 0);
          }
        }
      }

      // Duplicate: Ctrl+D
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'd' && selectedRegionId) {
        e.preventDefault();
        duplicateRegion(selectedRegionId);
      }

      // Undo / Redo
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        if (e.shiftKey) {
          redo();
        } else {
          undo();
        }
      } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') {
        e.preventDefault();
        redo();
      }

      // Page Navigation
      if (e.key === 'PageUp' || (e.altKey && e.key === 'ArrowLeft')) {
        e.preventDefault();
        navigatePage(-1);
      } else if (e.key === 'PageDown' || (e.altKey && e.key === 'ArrowRight')) {
        e.preventDefault();
        navigatePage(1);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    activeTool,
    setActiveTool,
    selectedRegionId,
    setSelectedRegionId,
    updateRegionStatus,
    deleteRegion,
    duplicateRegion,
    fitSelectedRegion,
    nudgeRegion,
    approveAllPageRegions,
    undo,
    redo,
    navigatePage,
  ]);

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-gray-950 text-gray-100">
      <Toolbar />

      <Layout
        sidebar={<PageSidebar />}
        viewer={
          <DeepZoomViewer
            dziUrl={viewerInfo?.dzi_url}
            masterWidth={viewerInfo?.master_width}
            masterHeight={viewerInfo?.master_height}
          />
        }
        panel={<RegionPanel />}
      />

      <StatusBar />
    </div>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Theme appearance="dark" accentColor="blue" radius="small">
        <MainApp />
      </Theme>
    </QueryClientProvider>
  );
}

export default App;
