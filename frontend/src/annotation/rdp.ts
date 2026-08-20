import { Point2D } from '../types/geometry';

/**
 * Calculates perpendicular distance from point p to line segment (p1, p2).
 */
function perpendicularDistance(p: Point2D, p1: Point2D, p2: Point2D): number {
  const [x, y] = p;
  const [x1, y1] = p1;
  const [x2, y2] = p2;

  const dx = x2 - x1;
  const dy = y2 - y1;

  if (dx === 0 && dy === 0) {
    return Math.hypot(x - x1, y - y1);
  }

  const num = Math.abs(dy * x - dx * y + x2 * y1 - y2 * x1);
  const den = Math.hypot(dx, dy);

  return num / den;
}

/**
 * Ramer-Douglas-Peucker (RDP) algorithm to reduce dense point streams into clean polygon vertices.
 * @param points Array of [x, y] points
 * @param epsilon Distance tolerance in pixels (default 2.0)
 */
export function simplifyRDP(points: Point2D[], epsilon: number = 2.0): Point2D[] {
  if (points.length <= 2) {
    return points;
  }

  let maxDist = 0;
  let maxIndex = 0;
  const first = points[0];
  const last = points[points.length - 1];

  for (let i = 1; i < points.length - 1; i++) {
    const dist = perpendicularDistance(points[i], first, last);
    if (dist > maxDist) {
      maxDist = dist;
      maxIndex = i;
    }
  }

  if (maxDist > epsilon) {
    const left = simplifyRDP(points.slice(0, maxIndex + 1), epsilon);
    const right = simplifyRDP(points.slice(maxIndex), epsilon);
    return [...left.slice(0, -1), ...right];
  }

  return [first, last];
}
