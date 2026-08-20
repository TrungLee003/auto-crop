from app.geometry.validation import validate_polygon
from app.geometry.transforms import compute_bounding_box
from app.annotation.models import RectangleGeometry

def test_rectangle():
    rect = RectangleGeometry(x=50.0, y=80.0, width=200.0, height=150.0)
    bounds = compute_bounding_box(rect)
    assert bounds == (50.0, 80.0, 250.0, 230.0)

def test_polygon_validation():
    # valid square
    ok, err = validate_polygon([[0, 0], [0, 1], [1, 1], [1, 0]])
    assert ok is True
    assert err is None
    # invalid
    ok, err = validate_polygon([[0, 0], [1, 1]])
    assert ok is False
    assert err is not None
