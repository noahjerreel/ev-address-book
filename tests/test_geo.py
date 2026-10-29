"""Unit tests for the geodesic helpers."""

import pytest

from app.utils.geo import bounding_box, haversine_km


def test_haversine_zero_distance() -> None:
    assert haversine_km(52.5, 13.4, 52.5, 13.4) == 0


def test_haversine_berlin_to_paris() -> None:
    # Berlin (Brandenburg Gate) -> Paris (Eiffel Tower) is roughly 878 km.
    distance = haversine_km(52.516275, 13.377704, 48.858370, 2.294481)
    assert distance == pytest.approx(878, abs=3)


def test_haversine_is_symmetric() -> None:
    assert haversine_km(10, 20, -30, 140) == pytest.approx(haversine_km(-30, 140, 10, 20))


def test_bounding_box_simple_case() -> None:
    box = bounding_box(52.5, 13.4, 10)
    assert box.min_lat < 52.5 < box.max_lat
    assert len(box.lon_ranges) == 1
    lo, hi = box.lon_ranges[0]
    assert lo < 13.4 < hi


def test_bounding_box_crosses_antimeridian() -> None:
    box = bounding_box(0, 179.95, 50)
    assert len(box.lon_ranges) == 2
    assert (-180.0, pytest.approx(-179.60, abs=0.05)) == box.lon_ranges[1]


def test_bounding_box_containing_pole_covers_all_longitudes() -> None:
    box = bounding_box(89.9, 0, 50)
    assert box.max_lat == 90
    assert box.lon_ranges == ((-180.0, 180.0),)
