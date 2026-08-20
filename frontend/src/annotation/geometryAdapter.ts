import OpenSeadragon from 'openseadragon';
import { BoundingBox, Point2D, RegionGeometry } from '../types/geometry';
import { Padding } from '../types/region';
import { masterToViewport } from '../viewer/coordinateAdapter';

export function computeBoundingBox(geom: RegionGeometry): BoundingBox {
  switch (geom.type) {
    case 'rectangle':
      return {
        minX: geom.x,
        minY: geom.y,
        maxX: geom.x + geom.width,
        maxY: geom.y + geom.height,
        width: geom.width,
        height: geom.height,
      };

    case 'rotated_rectangle': {
      const rad = (geom.angle * Math.PI) / 180.0;
      const cos = Math.cos(rad);
      const sin = Math.sin(rad);
      const dx = geom.width / 2.0;
      const dy = geom.height / 2.0;
      const corners = [
        [-dx, -dy],
        [dx, -dy],
        [dx, dy],
        [-dx, dy],
      ];
      const xs = corners.map(([rx, ry]) => geom.cx + rx * cos - ry * sin);
      const ys = corners.map(([rx, ry]) => geom.cy + rx * sin + ry * cos);
      const minX = Math.min(...xs);
      const minY = Math.min(...ys);
      const maxX = Math.max(...xs);
      const maxY = Math.max(...ys);
      return {
        minX,
        minY,
        maxX,
        maxY,
        width: maxX - minX,
        height: maxY - minY,
      };
    }

    case 'polygon': {
      if (!geom.points || geom.points.length === 0) {
        return { minX: 0, minY: 0, maxX: 0, maxY: 0, width: 0, height: 0 };
      }
      const xs = geom.points.map((p) => p[0]);
      const ys = geom.points.map((p) => p[1]);
      const minX = Math.min(...xs);
      const minY = Math.min(...ys);
      const maxX = Math.max(...xs);
      const maxY = Math.max(...ys);
      return {
        minX,
        minY,
        maxX,
        maxY,
        width: maxX - minX,
        height: maxY - minY,
      };
    }

    case 'multipolygon': {
      const allPts = geom.polygons.flat();
      if (allPts.length === 0) {
        return { minX: 0, minY: 0, maxX: 0, maxY: 0, width: 0, height: 0 };
      }
      const xs = allPts.map((p) => p[0]);
      const ys = allPts.map((p) => p[1]);
      const minX = Math.min(...xs);
      const minY = Math.min(...ys);
      const maxX = Math.max(...xs);
      const maxY = Math.max(...ys);
      return {
        minX,
        minY,
        maxX,
        maxY,
        width: maxX - minX,
        height: maxY - minY,
      };
    }
  }
}

export function applyPaddingToBounds(
  bounds: BoundingBox,
  padding: Padding,
  masterWidth?: number,
  masterHeight?: number
): BoundingBox {
  let minX = bounds.minX - padding.left;
  let minY = bounds.minY - padding.top;
  let maxX = bounds.maxX + padding.right;
  let maxY = bounds.maxY + padding.bottom;

  if (masterWidth !== undefined) {
    minX = Math.max(0, Math.min(masterWidth, minX));
    maxX = Math.max(minX + 1, Math.min(masterWidth, maxX));
  }
  if (masterHeight !== undefined) {
    minY = Math.max(0, Math.min(masterHeight, minY));
    maxY = Math.max(minY + 1, Math.min(masterHeight, maxY));
  }

  return {
    minX,
    minY,
    maxX,
    maxY,
    width: maxX - minX,
    height: maxY - minY,
  };
}

export function masterPointsToScreenPoints(
  points: Point2D[],
  viewer: OpenSeadragon.Viewer,
  masterW: number,
  masterH: number
): Point2D[] {
  return points.map(([mx, my]) => {
    const vp = masterToViewport({ x: mx, y: my }, viewer, masterW, masterH);
    const pixel = viewer.viewport.pixelFromPoint(new OpenSeadragon.Point(vp.x, vp.y), true);
    return [pixel.x, pixel.y];
  });
}
