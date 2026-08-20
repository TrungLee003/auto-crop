import React, { useCallback, useEffect, useRef, useState } from 'react';
import OpenSeadragon from 'openseadragon';
import { useAnnotationStore } from '../stores/annotationStore';
import { applyPaddingToBounds, computeBoundingBox } from './geometryAdapter';
import { masterToViewport, viewportToMaster } from '../viewer/coordinateAdapter';
import { Point2D, RegionGeometry } from '../types/geometry';
import { simplifyRDP } from './rdp';

interface AnnotationLayerProps {
  viewer: OpenSeadragon.Viewer | null;
  masterWidth: number;
  masterHeight: number;
}

type DragHandle = 'move' | 'nw' | 'ne' | 'se' | 'sw';

const DRAG_THRESHOLD = 3; // px dead zone to distinguish click vs drag

export function AnnotationLayer({ viewer, masterWidth, masterHeight }: AnnotationLayerProps) {
  const storeRef = useRef(useAnnotationStore.getState());
  // Keep storeRef always up-to-date
  useEffect(() => {
    return useAnnotationStore.subscribe((state) => {
      storeRef.current = state;
    });
  }, []);

  const {
    regions,
    selectedRegionIds,
    selectedRegionId,
    activeTool,
    setSelectedRegionId,
    addRegion,
    updateRegionAngle,
  } = useAnnotationStore();

  const [, setRenderTick] = useState(0);

  // Drawing & Rotating state
  const [drawingStart, setDrawingStart] = useState<{ x: number; y: number } | null>(null);
  const [currentDrawPoint, setCurrentDrawPoint] = useState<{ x: number; y: number } | null>(null);
  const [polyVertices, setPolyVertices] = useState<Point2D[]>([]);
  const [lassoPoints, setLassoPoints] = useState<Point2D[]>([]);
  const [isRotating, setIsRotating] = useState(false);

  // Live dragging state (local-only for smooth rendering)
  const [liveDragGeometry, setLiveDragGeometry] = useState<{
    regionId: string;
    geometry: RegionGeometry;
  } | null>(null);

  const svgRef = useRef<SVGSVGElement>(null);
  const viewerRef = useRef(viewer);
  viewerRef.current = viewer;
  const masterWRef = useRef(masterWidth);
  masterWRef.current = masterWidth;
  const masterHRef = useRef(masterHeight);
  masterHRef.current = masterHeight;

  // ---------- OpenSeadragon sync ----------
  useEffect(() => {
    if (!viewer) return;
    const onUpdate = () => setRenderTick((t) => t + 1);
    viewer.addHandler('animation', onUpdate);
    viewer.addHandler('zoom', onUpdate);
    viewer.addHandler('pan', onUpdate);
    viewer.addHandler('resize', onUpdate);
    viewer.addHandler('open', onUpdate);
    viewer.addHandler('update-viewport', onUpdate);
    return () => {
      viewer.removeHandler('animation', onUpdate);
      viewer.removeHandler('zoom', onUpdate);
      viewer.removeHandler('pan', onUpdate);
      viewer.removeHandler('resize', onUpdate);
      viewer.removeHandler('open', onUpdate);
      viewer.removeHandler('update-viewport', onUpdate);
    };
  }, [viewer]);

  // ---------- Coordinate helpers (use refs, no closures!) ----------
  const toScreen = useCallback(
    (mx: number, my: number): [number, number] => {
      const v = viewerRef.current;
      const mw = masterWRef.current;
      const mh = masterHRef.current;
      if (!v || !v.viewport || mw === 0) return [0, 0];
      const vp = masterToViewport({ x: mx, y: my }, v, mw, mh);
      const pixel = v.viewport.pixelFromPoint(new OpenSeadragon.Point(vp.x, vp.y), true);
      return [pixel.x, pixel.y];
    },
    [] // stable — reads from refs
  );

  /** Convert screen clientX/clientY → master image coordinates (always reads from refs) */
  const screenToMasterRef = useCallback(
    (clientX: number, clientY: number): { x: number; y: number } => {
      const v = viewerRef.current;
      const mw = masterWRef.current;
      const mh = masterHRef.current;
      const svg = svgRef.current;
      if (!v || !v.viewport || !svg || mw === 0) return { x: 0, y: 0 };
      const rect = svg.getBoundingClientRect();
      const vpPoint = v.viewport.pointFromPixel(
        new OpenSeadragon.Point(clientX - rect.left, clientY - rect.top)
      );
      const masterPt = viewportToMaster(vpPoint, v, mw, mh);
      return {
        x: Math.max(0, Math.min(mw, Math.round(masterPt.x))),
        y: Math.max(0, Math.min(mh, Math.round(masterPt.y))),
      };
    },
    [] // stable — reads from refs
  );

  // ---------- Geometry computation during drag ----------
  const computeDragGeom = useCallback(
    (initial: RegionGeometry, mode: DragHandle, dx: number, dy: number): RegionGeometry => {
      const mw = masterWRef.current;
      const mh = masterHRef.current;
      if (initial.type === 'rectangle') {
        let { x, y, width, height } = initial;
        if (mode === 'move') {
          x = Math.max(0, Math.min(mw - width, Math.round(x + dx)));
          y = Math.max(0, Math.min(mh - height, Math.round(y + dy)));
        } else if (mode === 'se') {
          width = Math.max(20, Math.min(mw - x, Math.round(width + dx)));
          height = Math.max(20, Math.min(mh - y, Math.round(height + dy)));
        } else if (mode === 'nw') {
          const nx = Math.max(0, Math.min(x + width - 20, Math.round(x + dx)));
          const ny = Math.max(0, Math.min(y + height - 20, Math.round(y + dy)));
          width = width + (x - nx); height = height + (y - ny); x = nx; y = ny;
        } else if (mode === 'ne') {
          const ny = Math.max(0, Math.min(y + height - 20, Math.round(y + dy)));
          width = Math.max(20, Math.min(mw - x, Math.round(width + dx)));
          height = height + (y - ny); y = ny;
        } else if (mode === 'sw') {
          const nx = Math.max(0, Math.min(x + width - 20, Math.round(x + dx)));
          width = width + (x - nx);
          height = Math.max(20, Math.min(mh - y, Math.round(height + dy))); x = nx;
        }
        return { type: 'rectangle', x, y, width, height };
      } else if (initial.type === 'rotated_rectangle') {
        let { cx, cy, width, height, angle } = initial;
        if (mode === 'move') {
          cx = Math.max(0, Math.min(mw, Math.round(cx + dx)));
          cy = Math.max(0, Math.min(mh, Math.round(cy + dy)));
        } else if (mode === 'se') {
          width = Math.max(20, Math.round(width + dx));
          height = Math.max(20, Math.round(height + dy));
        } else if (mode === 'nw') {
          width = Math.max(20, Math.round(width - dx));
          height = Math.max(20, Math.round(height - dy));
        }
        return { type: 'rotated_rectangle', cx, cy, width, height, angle };
      } else if (initial.type === 'polygon' && mode === 'move') {
        const points = initial.points.map(([px, py]) => [
          Math.max(0, Math.min(mw, Math.round(px + dx))),
          Math.max(0, Math.min(mh, Math.round(py + dy))),
        ]) as Point2D[];
        return { type: 'polygon', points };
      }
      return initial;
    },
    [] // stable — reads from refs
  );

  // ---------- Region interaction: mousedown on region body or handle ----------
  const handleRegionPointerDown = useCallback(
    (e: React.MouseEvent, regionId: string, handle: DragHandle) => {
      if (storeRef.current.activeTool !== 'select') return;
      e.stopPropagation();
      e.preventDefault();

      const v = viewerRef.current;
      if (v) v.setMouseNavEnabled(false);

      const region = storeRef.current.regions.find((r) => r.id === regionId);
      if (!region) return;

      const pt = screenToMasterRef(e.clientX, e.clientY);
      const initial = JSON.parse(JSON.stringify(region.geometry)) as RegionGeometry;
      const startScreenX = e.clientX;
      const startScreenY = e.clientY;
      const shiftKey = e.shiftKey;

      let isDragging = false;
      let currentGeometry = initial;

      const onMove = (moveEvent: MouseEvent) => {
        const dsx = moveEvent.clientX - startScreenX;
        const dsy = moveEvent.clientY - startScreenY;
        const dist = Math.sqrt(dsx * dsx + dsy * dsy);

        if (!isDragging) {
          if (dist < DRAG_THRESHOLD) return;
          isDragging = true;
          storeRef.current.setSelectedRegionId(regionId);
        }

        const curPt = screenToMasterRef(moveEvent.clientX, moveEvent.clientY);
        const dx = curPt.x - pt.x;
        const dy = curPt.y - pt.y;
        const newGeom = computeDragGeom(initial, handle, dx, dy);
        currentGeometry = newGeom;
        setLiveDragGeometry({ regionId, geometry: newGeom });
      };

      const onUp = () => {
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('mouseup', onUp);

        if (isDragging) {
          // Commit geometry to store FIRST, then clear live state, then re-enable OSD
          storeRef.current.updateRegionGeometry(regionId, currentGeometry);
          setLiveDragGeometry(null);
        } else {
          // Was a click — select
          setLiveDragGeometry(null);
          if (shiftKey) {
            storeRef.current.toggleRegionSelection(regionId);
          } else {
            storeRef.current.setSelectedRegionId(regionId);
          }
        }

        // Re-enable OSD panning AFTER store is committed
        const v2 = viewerRef.current;
        if (v2) v2.setMouseNavEnabled(true);
      };

      window.addEventListener('mousemove', onMove);
      window.addEventListener('mouseup', onUp);
    },
    [screenToMasterRef, computeDragGeom]
  );

  // ---------- SVG-level mouse handlers (drawing tools only) ----------
  const handleMouseDown = (e: React.MouseEvent<SVGSVGElement>) => {
    if (isRotating) return;

    if (activeTool === 'select') {
      // Click on empty canvas — deselect
      setSelectedRegionId(null);
      return;
    }

    const pt = screenToMasterRef(e.clientX, e.clientY);
    if (activeTool === 'rectangle' || activeTool === 'rotated_rect') {
      setDrawingStart(pt);
      setCurrentDrawPoint(pt);
    } else if (activeTool === 'polygon') {
      setPolyVertices((prev) => [...prev, [pt.x, pt.y]]);
    } else if (activeTool === 'lasso') {
      setLassoPoints([[pt.x, pt.y]]);
    }
  };

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const pt = screenToMasterRef(e.clientX, e.clientY);

    if (isRotating && selectedRegionId) {
      const selected = regions.find((r) => r.id === selectedRegionId);
      if (selected) {
        const bounds = computeBoundingBox(selected.geometry);
        const cx = (bounds.minX + bounds.maxX) / 2;
        const cy = (bounds.minY + bounds.maxY) / 2;
        const angleRad = Math.atan2(pt.y - cy, pt.x - cx);
        let angleDeg = Math.round((angleRad * 180) / Math.PI) + 90;
        if (angleDeg > 180) angleDeg -= 360;
        if (angleDeg < -180) angleDeg += 360;
        updateRegionAngle(selectedRegionId, angleDeg);
      }
      return;
    }

    if (activeTool === 'lasso' && lassoPoints.length > 0) {
      setLassoPoints((prev) => [...prev, [pt.x, pt.y]]);
      return;
    }

    if (drawingStart || polyVertices.length > 0) {
      setCurrentDrawPoint(pt);
    }
  };

  const handleMouseUp = (e: React.MouseEvent<SVGSVGElement>) => {
    if (isRotating) {
      setIsRotating(false);
      return;
    }

    if ((activeTool === 'rectangle' || activeTool === 'rotated_rect') && drawingStart) {
      const pt = screenToMasterRef(e.clientX, e.clientY);
      const minX = Math.min(drawingStart.x, pt.x);
      const minY = Math.min(drawingStart.y, pt.y);
      const w = Math.abs(drawingStart.x - pt.x);
      const h = Math.abs(drawingStart.y - pt.y);

      if (w > 20 && h > 20) {
        if (activeTool === 'rotated_rect') {
          addRegion({ type: 'rotated_rectangle', cx: minX + w / 2, cy: minY + h / 2, width: w, height: h, angle: 0.0 });
        } else {
          addRegion({ type: 'rectangle', x: minX, y: minY, width: w, height: h });
        }
      }
      setDrawingStart(null);
      setCurrentDrawPoint(null);
    } else if (activeTool === 'lasso' && lassoPoints.length > 5) {
      const simplified = simplifyRDP(lassoPoints, 2.5);
      if (simplified.length >= 3) {
        addRegion({ type: 'polygon', points: simplified });
      }
      setLassoPoints([]);
    }
  };

  const handleDoubleClick = () => {
    if (activeTool === 'polygon' && polyVertices.length >= 3) {
      addRegion({ type: 'polygon', points: polyVertices });
      setPolyVertices([]);
      setCurrentDrawPoint(null);
    }
  };

  if (!viewer || masterWidth === 0) return null;

  return (
    <svg
      ref={svgRef}
      className={`absolute inset-0 w-full h-full pointer-events-auto ${
        activeTool !== 'select' ? 'cursor-crosshair' : 'cursor-default'
      }`}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onDoubleClick={handleDoubleClick}
      style={{ zIndex: 20 }}
    >
      {regions.map((region) => {
        const isSelected = selectedRegionIds.includes(region.id);
        const geom =
          liveDragGeometry && liveDragGeometry.regionId === region.id
            ? liveDragGeometry.geometry
            : region.geometry;
        const bounds = computeBoundingBox(geom);
        const [tlX, tlY] = toScreen(bounds.minX, bounds.minY);
        const [brX, brY] = toScreen(bounds.maxX, bounds.maxY);
        const w = brX - tlX;
        const h = brY - tlY;

        let strokeColor = '#3b82f6';
        if (region.status === 'APPROVED') strokeColor = '#10b981';
        if (region.status === 'REJECTED') strokeColor = '#ef4444';
        if (isSelected) strokeColor = '#f59e0b';

        const paddedBounds = applyPaddingToBounds(bounds, region.padding, masterWidth, masterHeight);
        const [padTlX, padTlY] = toScreen(paddedBounds.minX, paddedBounds.minY);
        const [padBrX, padBrY] = toScreen(paddedBounds.maxX, paddedBounds.maxY);

        const [cx, cy] = toScreen((bounds.minX + bounds.maxX) / 2, (bounds.minY + bounds.maxY) / 2);
        const angle = geom.type === 'rotated_rectangle' ? geom.angle : 0;
        const rotHandleDist = Math.max(25, h / 2 + 20);

        return (
          <g key={region.id} className="select-none">
            {isSelected && (
              <rect
                x={padTlX} y={padTlY}
                width={padBrX - padTlX} height={padBrY - padTlY}
                fill="none" stroke="#60a5fa" strokeWidth="1.5"
                strokeDasharray="4 4" opacity="0.6"
              />
            )}

            {/* Region Body — click to select, drag to move */}
            {geom.type === 'rectangle' ? (
              <rect
                x={tlX} y={tlY} width={w} height={h}
                fill={isSelected ? 'rgba(245, 158, 11, 0.15)' : 'rgba(59, 130, 246, 0.1)'}
                stroke={strokeColor} strokeWidth={isSelected ? 2.5 : 2}
                className={activeTool === 'select' ? 'cursor-pointer' : ''}
                onMouseDown={(e) => handleRegionPointerDown(e, region.id, 'move')}
              />
            ) : geom.type === 'rotated_rectangle' ? (
              <g transform={`rotate(${geom.angle}, ${cx}, ${cy})`}>
                <rect
                  x={tlX} y={tlY} width={w} height={h}
                  fill={isSelected ? 'rgba(245, 158, 11, 0.15)' : 'rgba(59, 130, 246, 0.1)'}
                  stroke={strokeColor} strokeWidth={isSelected ? 2.5 : 2}
                  className={activeTool === 'select' ? 'cursor-pointer' : ''}
                  onMouseDown={(e) => handleRegionPointerDown(e, region.id, 'move')}
                />
              </g>
            ) : geom.type === 'polygon' ? (
              <polygon
                points={geom.points.map(([px, py]) => toScreen(px, py).join(',')).join(' ')}
                fill={isSelected ? 'rgba(245, 158, 11, 0.15)' : 'rgba(59, 130, 246, 0.1)'}
                stroke={strokeColor} strokeWidth={isSelected ? 2.5 : 2}
                className={activeTool === 'select' ? 'cursor-pointer' : ''}
                onMouseDown={(e) => handleRegionPointerDown(e, region.id, 'move')}
              />
            ) : (
              <rect
                x={tlX} y={tlY} width={w} height={h}
                fill="rgba(59, 130, 246, 0.1)"
                stroke={strokeColor} strokeWidth={2}
                className={activeTool === 'select' ? 'cursor-pointer' : ''}
                onMouseDown={(e) => handleRegionPointerDown(e, region.id, 'move')}
              />
            )}

            {/* Corner Resize Handles */}
            {isSelected && activeTool === 'select' && (
              <g>
                {([
                  { hx: tlX, hy: tlY, handle: 'nw' as DragHandle, cursor: 'cursor-nwse-resize' },
                  { hx: brX, hy: tlY, handle: 'ne' as DragHandle, cursor: 'cursor-nesw-resize' },
                  { hx: brX, hy: brY, handle: 'se' as DragHandle, cursor: 'cursor-nwse-resize' },
                  { hx: tlX, hy: brY, handle: 'sw' as DragHandle, cursor: 'cursor-nesw-resize' },
                ]).map(({ hx, hy, handle, cursor }) => (
                  <circle
                    key={handle} cx={hx} cy={hy} r="6"
                    fill="#ffffff" stroke="#f59e0b" strokeWidth="2.5"
                    className={`${cursor} hover:scale-125 transition-transform`}
                    onMouseDown={(e) => handleRegionPointerDown(e, region.id, handle)}
                  />
                ))}
              </g>
            )}

            {/* Sequence Badge */}
            <g transform={`translate(${tlX}, ${tlY - 18})`}>
              <rect x="0" y="0" width="34" height="16" rx="3"
                fill={isSelected ? '#f59e0b' : '#1e293b'} stroke={strokeColor} strokeWidth="1" />
              <text x="17" y="11" fill="#ffffff" fontSize="10"
                fontWeight="bold" textAnchor="middle" fontFamily="monospace">
                #{region.sequence}
              </text>
            </g>

            {/* Rotation Knob */}
            {isSelected && (
              <g transform={`rotate(${angle}, ${cx}, ${cy})`}>
                <line x1={cx} y1={cy - h / 2} x2={cx} y2={cy - rotHandleDist}
                  stroke="#f59e0b" strokeWidth="1.5" strokeDasharray="2 2" />
                <circle cx={cx} cy={cy - rotHandleDist} r="6"
                  fill="#f59e0b" stroke="#ffffff" strokeWidth="2"
                  className="cursor-grab active:cursor-grabbing hover:scale-125 transition-transform"
                  onMouseDown={(e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    const v = viewerRef.current;
                    if (v) v.setMouseNavEnabled(false);
                    setIsRotating(true);
                    setSelectedRegionId(region.id);
                    const onRotUp = () => {
                      window.removeEventListener('mouseup', onRotUp);
                      setIsRotating(false);
                      const v2 = viewerRef.current;
                      if (v2) v2.setMouseNavEnabled(true);
                    };
                    window.addEventListener('mouseup', onRotUp);
                  }}
                />
              </g>
            )}
          </g>
        );
      })}

      {/* Drawing Previews */}
      {drawingStart && currentDrawPoint &&
        (activeTool === 'rectangle' || activeTool === 'rotated_rect') &&
        (() => {
          const [x1, y1] = toScreen(
            Math.min(drawingStart.x, currentDrawPoint.x),
            Math.min(drawingStart.y, currentDrawPoint.y)
          );
          const [x2, y2] = toScreen(
            Math.max(drawingStart.x, currentDrawPoint.x),
            Math.max(drawingStart.y, currentDrawPoint.y)
          );
          return (
            <rect x={x1} y={y1}
              width={Math.abs(x2 - x1)} height={Math.abs(y2 - y1)}
              fill="rgba(59, 130, 246, 0.2)"
              stroke="#3b82f6" strokeWidth="2" strokeDasharray="4 2"
            />
          );
        })()}

      {polyVertices.length > 0 && activeTool === 'polygon' && (
        <g>
          <polyline
            points={[
              ...polyVertices.map(([px, py]) => toScreen(px, py).join(',')),
              ...(currentDrawPoint ? [toScreen(currentDrawPoint.x, currentDrawPoint.y).join(',')] : []),
            ].join(' ')}
            fill="rgba(59, 130, 246, 0.15)" stroke="#60a5fa" strokeWidth="2" strokeDasharray="4 2"
          />
          {polyVertices.map(([px, py], i) => {
            const [sx, sy] = toScreen(px, py);
            return <circle key={i} cx={sx} cy={sy} r="4" fill="#3b82f6" stroke="#ffffff" strokeWidth="1.5" />;
          })}
        </g>
      )}

      {lassoPoints.length > 0 && activeTool === 'lasso' && (
        <polyline
          points={lassoPoints.map(([px, py]) => toScreen(px, py).join(',')).join(' ')}
          fill="rgba(59, 130, 246, 0.1)" stroke="#60a5fa" strokeWidth="2"
        />
      )}
    </svg>
  );
}
