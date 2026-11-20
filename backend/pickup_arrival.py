"""Location-checked pickup arrival. Device coordinates are used only for comparison."""
import math

from fastapi import HTTPException
from pydantic import BaseModel, Field

from backend.local_marketplace import EARTH_RADIUS_M, sphere


SCHEMA = """
CREATE TABLE IF NOT EXISTS pickup_point_arrivals (
    point_id BIGINT PRIMARY KEY REFERENCES pickup_points(id) ON DELETE CASCADE,
    confirmed_at TEXT NOT NULL
);
"""
MAX_DISTANCE_M = 100
MAX_ACCURACY_M = 100


class ArrivalIn(BaseModel):
    latitude_e6: int = Field(strict=True, ge=-90_000_000, le=90_000_000)
    longitude_e6: int = Field(strict=True, ge=-180_000_000, le=180_000_000)
    accuracy_m: float = Field(strict=True, gt=0, le=MAX_ACCURACY_M)


def verify_location(coordinates, payload):
    if coordinates is None:
        raise HTTPException(409, 'Najpierw ustaw położenie punktu na mapie.')
    point = sphere(coordinates['latitude_e6'], coordinates['longitude_e6'])
    position = sphere(payload.latitude_e6, payload.longitude_e6)
    distance = 2 * EARTH_RADIUS_M * math.asin(min(1, math.dist(point, position) / 2))
    if distance > MAX_DISTANCE_M:
        raise HTTPException(422, 'Podejdź na odległość do 100 m od punktu odbioru.')
