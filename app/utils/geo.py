"""Geodesic helpers: great-circle distance and search bounding boxes.

The earth is modelled as a sphere, which is accurate to about 0.5 % - more than
enough for an address book. All angles are in decimal degrees.
"""

import math
from dataclasses import dataclass

# Mean earth radius (IUGG), in kilometres.
EARTH_RADIUS_KM = 6371.0088
# Half the earth's circumference: no two points on the surface are further apart.
MAX_SURFACE_DISTANCE_KM = math.pi * EARTH_RADIUS_KM


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in kilometres between two points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    # min() guards against floating-point values marginally above 1.
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """A latitude range plus one or two longitude ranges.

    Two longitude ranges are needed when the box crosses the antimeridian (±180°).
    """

    min_lat: float
    max_lat: float
    lon_ranges: tuple[tuple[float, float], ...]


def bounding_box(lat: float, lon: float, distance_km: float) -> BoundingBox:
    """Return a box that is guaranteed to contain every point within ``distance_km``.

    The box is used as a cheap, index-friendly SQL pre-filter; the exact distance
    is checked afterwards with :func:`haversine_km`. Method after J. P. Matuschek,
    "Finding Points Within a Distance of a Latitude/Longitude Using Bounding
    Coordinates".
    """
    angular_distance = distance_km / EARTH_RADIUS_KM
    delta_lat = math.degrees(angular_distance)
    min_lat, max_lat = lat - delta_lat, lat + delta_lat

    # The circle contains a pole: every longitude is reachable.
    if min_lat <= -90 or max_lat >= 90:
        return BoundingBox(max(min_lat, -90.0), min(max_lat, 90.0), ((-180.0, 180.0),))

    delta_lon = math.degrees(math.asin(math.sin(angular_distance) / math.cos(math.radians(lat))))
    min_lon, max_lon = lon - delta_lon, lon + delta_lon

    if min_lon < -180:  # wraps past the antimeridian on the west side
        ranges = ((min_lon + 360, 180.0), (-180.0, max_lon))
    elif max_lon > 180:  # wraps past the antimeridian on the east side
        ranges = ((min_lon, 180.0), (-180.0, max_lon - 360))
    else:
        ranges = ((min_lon, max_lon),)

    return BoundingBox(min_lat, max_lat, ranges)
