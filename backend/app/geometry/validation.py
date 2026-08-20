from typing import List, Optional, Tuple
from shapely.geometry import Polygon as ShapelyPolygon
from shapely.validation import make_valid


def validate_polygon(points: List[List[float]]) -> Tuple[bool, Optional[str]]:
    """
    Validates a list of 2D points forming a polygon.
    Returns (is_valid, error_message).
    """
    if len(points) < 3:
        return False, "Polygon must have at least 3 points"

    try:
        poly = ShapelyPolygon(points)
        if not poly.is_valid:
            return False, "Polygon is self-intersecting or degenerate"
        if poly.area <= 0:
            return False, "Polygon area must be greater than zero"
        return True, None
    except Exception as e:
        return False, f"Invalid polygon geometry: {str(e)}"


def fix_polygon_points(points: List[List[float]]) -> List[List[float]]:
    """
    Uses Shapely make_valid to repair self-intersecting or invalid polygons.
    """
    if len(points) < 3:
        return points

    try:
        poly = ShapelyPolygon(points)
        if poly.is_valid:
            return points

        repaired = make_valid(poly)
        if repaired.geom_type == "Polygon":
            coords = list(repaired.exterior.coords)
            return [[float(x), float(y)] for x, y in coords[:-1]]
        elif repaired.geom_type == "MultiPolygon" and len(repaired.geoms) > 0:
            # take largest component
            largest = max(repaired.geoms, key=lambda g: g.area)
            coords = list(largest.exterior.coords)
            return [[float(x), float(y)] for x, y in coords[:-1]]
    except Exception:
        pass

    return points
