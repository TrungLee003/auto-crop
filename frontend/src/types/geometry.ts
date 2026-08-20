export type Point2D = [number, number];

export interface Point {
  x: number;
  y: number;
}

export interface RectangleGeometry {
  type: 'rectangle';
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface RotatedRectangleGeometry {
  type: 'rotated_rectangle';
  cx: number;
  cy: number;
  width: number;
  height: number;
  angle: number;
}

export interface PolygonGeometry {
  type: 'polygon';
  points: Point2D[];
}

export interface MultiPolygonGeometry {
  type: 'multipolygon';
  polygons: Point2D[][];
}

export type RegionGeometry =
  RectangleGeometry | RotatedRectangleGeometry | PolygonGeometry | MultiPolygonGeometry;

export interface BoundingBox {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
  width: number;
  height: number;
}
