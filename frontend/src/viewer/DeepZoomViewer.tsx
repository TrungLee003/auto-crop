import { useEffect, useRef, useState } from 'react';
import OpenSeadragon from 'openseadragon';
import { usePageStore } from '../stores/pageStore';
import { useAnnotationStore } from '../stores/annotationStore';
import { viewportToMaster } from './coordinateAdapter';
import { AnnotationLayer } from '../annotation/AnnotationLayer';

interface DeepZoomViewerProps {
  dziUrl?: string;
  masterWidth?: number;
  masterHeight?: number;
}

export function DeepZoomViewer({ dziUrl, masterWidth = 0, masterHeight = 0 }: DeepZoomViewerProps) {
  const viewerContainerRef = useRef<HTMLDivElement>(null);
  const [viewerInstance, setViewerInstance] = useState<OpenSeadragon.Viewer | null>(null);

  const currentPage = usePageStore((s) => s.currentPage);
  const setCursorPos = usePageStore((s) => s.setCursorPos);
  const setZoomLevel = usePageStore((s) => s.setZoomLevel);
  const loadRegions = useAnnotationStore((s) => s.loadRegions);

  // Load annotations when page changes
  useEffect(() => {
    if (currentPage) {
      loadRegions(currentPage.id);
    }
  }, [currentPage, loadRegions]);

  useEffect(() => {
    if (!viewerContainerRef.current) return;

    if (!dziUrl) {
      if (viewerInstance) {
        viewerInstance.destroy();
        setViewerInstance(null);
      }
      return;
    }

    // Clean up previous viewer
    if (viewerInstance) {
      viewerInstance.destroy();
      setViewerInstance(null);
    }

    const viewer = OpenSeadragon({
      element: viewerContainerRef.current,
      prefixUrl: '//openseadragon.github.io/openseadragon/images/',
      tileSources: dziUrl,
      showNavigationControl: false,
      showNavigator: true,
      navigatorPosition: 'BOTTOM_RIGHT',
      navigatorSizeRatio: 0.15,
      navigatorAutoFade: true,
      maxZoomPixelRatio: 4,
      animationTime: 0.25,
      blendTime: 0.1,
      minZoomImageRatio: 0.5,
      visibilityRatio: 0.5,
      constrainDuringPan: true,
    });

    setViewerInstance(viewer);

    // Attach custom data
    (viewer as any).__masterWidth = masterWidth;
    (viewer as any).__masterHeight = masterHeight;

    // Event: Track Zoom Level
    const handleAnimation = () => {
      if (viewer && viewer.viewport) {
        setZoomLevel(viewer.viewport.getZoom());
      }
    };
    viewer.addHandler('animation', handleAnimation);
    viewer.addHandler('zoom', handleAnimation);

    // Event: Track Mouse Movement in Master Pixel Coordinates
    const tracker = new OpenSeadragon.MouseTracker({
      element: viewer.element,
      moveHandler: (event) => {
        if (!viewer.viewport || masterWidth === 0) return;
        const webPoint = (event as any).position;
        if (!webPoint) return;
        const vpPoint = viewer.viewport.pointFromPixel(webPoint);
        const masterPt = viewportToMaster(vpPoint, viewer, masterWidth, masterHeight);

        // Clamp to master image bounds
        const x = Math.max(0, Math.min(masterWidth, Math.round(masterPt.x)));
        const y = Math.max(0, Math.min(masterHeight, Math.round(masterPt.y)));
        setCursorPos({ x, y });
      },
      leaveHandler: () => {
        setCursorPos(null);
      },
    });

    return () => {
      tracker.destroy();
      viewer.destroy();
      setViewerInstance(null);
      setCursorPos(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dziUrl, masterWidth, masterHeight]);

  if (!dziUrl) {
    return (
      <div className="w-full h-full bg-gray-950 flex flex-col items-center justify-center text-gray-500 select-none">
        <div className="text-4xl mb-2">📖</div>
        <p className="text-sm font-medium">Select a page from the sidebar to inspect</p>
        <p className="text-xs text-gray-600 mt-1">
          High-resolution DeepZoom tiles will load automatically
        </p>
      </div>
    );
  }

  return (
    <div ref={viewerContainerRef} className="w-full h-full bg-gray-950 relative overflow-hidden">
      <AnnotationLayer
        viewer={viewerInstance}
        masterWidth={masterWidth}
        masterHeight={masterHeight}
      />
    </div>
  );
}
