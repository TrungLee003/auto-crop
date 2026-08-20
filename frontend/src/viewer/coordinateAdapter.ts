import OpenSeadragon from 'openseadragon';
import { Point } from '../types/geometry';

export type MasterCoord = Point;
export type ViewportCoord = Point;

/**
 * Convert OpenSeadragon viewport coordinates to master pixel coordinates.
 *
 * OpenSeadragon uses a normalized coordinate system where the image width = 1.0
 * at the viewport level. This function maps those coordinates back to actual
 * pixel positions on the master image.
 *
 * masterWidth and masterHeight are kept as parameters for future validation
 * and clamping (ensuring coordinates stay within image bounds).
 */
export function viewportToMaster(
  point: ViewportCoord,
  viewer: OpenSeadragon.Viewer,
  _masterWidth: number,
  _masterHeight: number
): MasterCoord {
  const viewportPoint = new OpenSeadragon.Point(point.x, point.y);
  const imagePoint = viewer.viewport.viewportToImageCoordinates(viewportPoint);

  // TODO: Clamp to [0, masterWidth] x [0, masterHeight]
  return {
    x: imagePoint.x,
    y: imagePoint.y,
  };
}

/**
 * Convert master pixel coordinates to OpenSeadragon viewport coordinates.
 *
 * Used to project canonical annotation geometry onto the viewer canvas.
 */
export function masterToViewport(
  point: MasterCoord,
  viewer: OpenSeadragon.Viewer,
  _masterWidth: number,
  _masterHeight: number
): ViewportCoord {
  const imagePoint = new OpenSeadragon.Point(point.x, point.y);
  const viewportPoint = viewer.viewport.imageToViewportCoordinates(imagePoint);

  return {
    x: viewportPoint.x,
    y: viewportPoint.y,
  };
}
