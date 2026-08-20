from pydantic import BaseModel
from typing import List

class Rectangle(BaseModel):
    x: float
    y: float
    width: float
    height: float

class RotatedRectangle(BaseModel):
    cx: float
    cy: float
    width: float
    height: float
    angle: float

class Polygon(BaseModel):
    points: List[List[float]]

class MultiPolygon(BaseModel):
    polygons: List[List[List[float]]]
