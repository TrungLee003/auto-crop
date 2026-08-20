import math
from typing import Dict, List, Optional, Tuple, Union
from shapely.geometry import (
    MultiPolygon as ShapelyMultiPolygon,
    Polygon as ShapelyPolygon,
    box as shapely_box,
)
from shapely.ops import unary_union

from app.annotation.models import (
    MultiPolygonGeometry,
    Padding,
    PolygonGeometry,
    RectangleGeometry,
    RegionGeometry,
    RotatedRectangleGeometry,
)


def compute_bounding_box(geom: RegionGeometry) -> Tuple[float, float, float, float]:
    """
    Returns (min_x, min_y, max_x, max_y) in master pixel coordinates.
    """
    if isinstance(geom, RectangleGeometry) or (isinstance(geom, dict) and geom.get("type") == "rectangle"):
        x = geom.x if hasattr(geom, "x") else geom["x"]
        y = geom.y if hasattr(geom, "y") else geom["y"]
        w = geom.width if hasattr(geom, "width") else geom["width"]
        h = geom.height if hasattr(geom, "height") else geom["height"]
        return float(x), float(y), float(x + w), float(y + h)

    elif isinstance(geom, RotatedRectangleGeometry) or (isinstance(geom, dict) and geom.get("type") == "rotated_rectangle"):
        cx = geom.cx if hasattr(geom, "cx") else geom["cx"]
        cy = geom.cy if hasattr(geom, "cy") else geom["cy"]
        w = geom.width if hasattr(geom, "width") else geom["width"]
        h = geom.height if hasattr(geom, "height") else geom["height"]
        angle_rad = math.radians(geom.angle if hasattr(geom, "angle") else geom.get("angle", 0.0))

        # 4 corners before rotation around center
        dx = w / 2.0
        dy = h / 2.0
        corners = [(-dx, -dy), (dx, -dy), (dx, dy), (-dx, dy)]
        rotated = []
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        for rx, ry in corners:
            x_rot = cx + rx * cos_a - ry * sin_a
            y_rot = cy + rx * sin_a + ry * cos_a
            rotated.append((x_rot, y_rot))

        xs = [p[0] for p in rotated]
        ys = [p[1] for p in rotated]
        return min(xs), min(ys), max(xs), max(ys)

    elif isinstance(geom, PolygonGeometry) or (isinstance(geom, dict) and geom.get("type") == "polygon"):
        pts = geom.points if hasattr(geom, "points") else geom["points"]
        if not pts:
            return 0.0, 0.0, 0.0, 0.0
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return min(xs), min(ys), max(xs), max(ys)

    elif isinstance(geom, MultiPolygonGeometry) or (isinstance(geom, dict) and geom.get("type") == "multipolygon"):
        polys = geom.polygons if hasattr(geom, "polygons") else geom["polygons"]
        all_xs = []
        all_ys = []
        for poly in polys:
            for pt in poly:
                all_xs.append(pt[0])
                all_ys.append(pt[1])
        if not all_xs:
            return 0.0, 0.0, 0.0, 0.0
        return min(all_xs), min(all_ys), max(all_xs), max(all_ys)

    return 0.0, 0.0, 0.0, 0.0


def apply_padding(
    bounds: Tuple[float, float, float, float],
    padding: Padding,
    max_w: Optional[int] = None,
    max_h: Optional[int] = None,
) -> Tuple[int, int, int, int]:
    """
    Applies (top, right, bottom, left) padding to (min_x, min_y, max_x, max_y) bounds.
    Returns integer crop rectangle: (crop_x, crop_y, crop_w, crop_h).
    Clamps to [0, max_w] x [0, max_h] if specified.
    """
    min_x, min_y, max_x, max_y = bounds
    x = int(math.floor(min_x - padding.left))
    y = int(math.floor(min_y - padding.top))
    r = int(math.ceil(max_x + padding.right))
    b = int(math.ceil(max_y + padding.bottom))

    if max_w is not None:
        x = max(0, min(max_w - 1, x))
        r = max(x + 1, min(max_w, r))
    if max_h is not None:
        y = max(0, min(max_h - 1, y))
        b = max(y + 1, min(max_h, b))

    w = max(1, r - x)
    h = max(1, b - y)

    return x, y, w, h


def simplify_polygon_rdp(points: List[List[float]], tolerance: float = 2.0) -> List[List[float]]:
    """
    Ramer-Douglas-Peucker simplification using Shapely.
    Preserves topology while reducing dense vertices.
    """
    if len(points) <= 3:
        return points

    try:
        poly = ShapelyPolygon(points)
        simplified = poly.simplify(tolerance, preserve_topology=True)
        if simplified.geom_type == "Polygon" and not simplified.is_empty:
            coords = list(simplified.exterior.coords)
            return [[float(x), float(y)] for x, y in coords[:-1]]
    except Exception:
        pass

    return points


def geometry_to_shapely(geom: RegionGeometry):
    """Convert any canonical RegionGeometry to a Shapely Geometry."""
    if isinstance(geom, RectangleGeometry) or (isinstance(geom, dict) and geom.get("type") == "rectangle"):
        x = geom.x if hasattr(geom, "x") else geom["x"]
        y = geom.y if hasattr(geom, "y") else geom["y"]
        w = geom.width if hasattr(geom, "width") else geom["width"]
        h = geom.height if hasattr(geom, "height") else geom["height"]
        return shapely_box(x, y, x + w, y + h)

    elif isinstance(geom, RotatedRectangleGeometry) or (isinstance(geom, dict) and geom.get("type") == "rotated_rectangle"):
        cx = geom.cx if hasattr(geom, "cx") else geom["cx"]
        cy = geom.cy if hasattr(geom, "cy") else geom["cy"]
        w = geom.width if hasattr(geom, "width") else geom["width"]
        h = geom.height if hasattr(geom, "height") else geom["height"]
        angle_rad = math.radians(geom.angle if hasattr(geom, "angle") else geom.get("angle", 0.0))

        dx = w / 2.0
        dy = h / 2.0
        corners = [(-dx, -dy), (dx, -dy), (dx, dy), (-dx, dy)]
        rotated = []
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        for rx, ry in corners:
            x_rot = cx + rx * cos_a - ry * sin_a
            y_rot = cy + rx * sin_a + ry * cos_a
            rotated.append([x_rot, y_rot])
        return ShapelyPolygon(rotated)

    elif isinstance(geom, PolygonGeometry) or (isinstance(geom, dict) and geom.get("type") == "polygon"):
        pts = geom.points if hasattr(geom, "points") else geom["points"]
        return ShapelyPolygon(pts)

    elif isinstance(geom, MultiPolygonGeometry) or (isinstance(geom, dict) and geom.get("type") == "multipolygon"):
        polys = geom.polygons if hasattr(geom, "polygons") else geom["polygons"]
        return ShapelyMultiPolygon([ShapelyPolygon(p) for p in polys])

    return None


def merge_geometries(geometries: List[RegionGeometry]) -> RegionGeometry:
    """
    Computes boolean union of multiple geometries using Shapely.
    Returns either PolygonGeometry or MultiPolygonGeometry.
    """
    shapely_geoms = [geometry_to_shapely(g) for g in geometries if g]
    valid_geoms = [g for g in shapely_geoms if g is not None and g.is_valid]

    if not valid_geoms:
        raise ValueError("No valid geometries to merge")

    union_geom = unary_union(valid_geoms)

    if union_geom.geom_type == "Polygon":
        coords = list(union_geom.exterior.coords)
        return PolygonGeometry(points=[[float(x), float(y)] for x, y in coords[:-1]])
    elif union_geom.geom_type == "MultiPolygon":
        all_polys = []
        for poly in union_geom.geoms:
            coords = list(poly.exterior.coords)
            all_polys.append([[float(x), float(y)] for x, y in coords[:-1]])
        return MultiPolygonGeometry(polygons=all_polys)
    else:
        # Fallback to bounding box
        minx, miny, maxx, maxy = union_geom.bounds
        return RectangleGeometry(x=minx, y=miny, width=maxx - minx, height=maxy - miny)


def nudge_geometry(geom: RegionGeometry, dx: float, dy: float) -> RegionGeometry:
    """Nudges geometry coordinates by (dx, dy)."""
    if isinstance(geom, RectangleGeometry):
        return RectangleGeometry(x=geom.x + dx, y=geom.y + dy, width=geom.width, height=geom.height)
    elif isinstance(geom, RotatedRectangleGeometry):
        return RotatedRectangleGeometry(cx=geom.cx + dx, cy=geom.cy + dy, width=geom.width, height=geom.height, angle=geom.angle)
    elif isinstance(geom, PolygonGeometry):
        return PolygonGeometry(points=[[p[0] + dx, p[1] + dy] for p in geom.points])
    elif isinstance(geom, MultiPolygonGeometry):
        return MultiPolygonGeometry(polygons=[[[p[0] + dx, p[1] + dy] for p in poly] for poly in geom.polygons])
    return geom
