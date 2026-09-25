"""Small, dependency-free surveying calculations for the first MVP."""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, degrees, hypot
from typing import Iterable


Point = tuple[float, float]


@dataclass(frozen=True)
class Segment:
    sequence: int
    start: Point
    end: Point
    distance: float
    azimuth_degrees: float


def close_ring(points: Iterable[Point]) -> list[Point]:
    """Return a ring with its final point equal to its first point."""
    ring = [(float(x), float(y)) for x, y in points]
    if len(ring) > 1 and ring[0] != ring[-1]:
        ring.append(ring[0])
    return ring


def polygon_area(points: Iterable[Point]) -> float:
    """Calculate planar area in square drawing units with the shoelace formula."""
    ring = close_ring(points)
    if len(ring) < 4:
        return 0.0
    twice_area = sum(
        ring[index][0] * ring[index + 1][1]
        - ring[index + 1][0] * ring[index][1]
        for index in range(len(ring) - 1)
    )
    return abs(twice_area) / 2


def azimuth_from_north(start: Point, end: Point) -> float:
    """Return clockwise azimuth degrees from north for an easting/northing pair."""
    delta_east = end[0] - start[0]
    delta_north = end[1] - start[1]
    return (degrees(atan2(delta_east, delta_north)) + 360) % 360


def segments(points: Iterable[Point]) -> list[Segment]:
    ring = close_ring(points)
    return [
        Segment(
            sequence=index + 1,
            start=ring[index],
            end=ring[index + 1],
            distance=hypot(ring[index + 1][0] - ring[index][0], ring[index + 1][1] - ring[index][1]),
            azimuth_degrees=azimuth_from_north(ring[index], ring[index + 1]),
        )
        for index in range(max(0, len(ring) - 1))
    ]


def perimeter(points: Iterable[Point]) -> float:
    return sum(segment.distance for segment in segments(points))


def orientation(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a: Point, b: Point, c: Point) -> bool:
    return min(a[0], c[0]) <= b[0] <= max(a[0], c[0]) and min(a[1], c[1]) <= b[1] <= max(a[1], c[1])


def _intersects(a: Point, b: Point, c: Point, d: Point) -> bool:
    first = orientation(a, b, c)
    second = orientation(a, b, d)
    third = orientation(c, d, a)
    fourth = orientation(c, d, b)
    if first == 0 and _on_segment(a, c, b):
        return True
    if second == 0 and _on_segment(a, d, b):
        return True
    if third == 0 and _on_segment(c, a, d):
        return True
    if fourth == 0 and _on_segment(c, b, d):
        return True
    return (first > 0) != (second > 0) and (third > 0) != (fourth > 0)


def has_self_intersection(points: Iterable[Point]) -> bool:
    """Detect crossing non-adjacent segments in a closed polygon ring."""
    ring = close_ring(points)
    count = len(ring) - 1
    if count < 4:
        return False
    for first_index in range(count):
        for second_index in range(first_index + 1, count):
            if second_index in {first_index, first_index + 1}:
                continue
            if first_index == 0 and second_index == count - 1:
                continue
            if _intersects(
                ring[first_index], ring[first_index + 1], ring[second_index], ring[second_index + 1]
            ):
                return True
    return False


def analyse_polygon(points: Iterable[Point]) -> dict[str, object]:
    ring = close_ring(points)
    warnings: list[str] = []
    if len(ring) < 4:
        warnings.append("A parcel boundary needs at least three distinct vertices.")
    if has_self_intersection(ring):
        warnings.append("The boundary crosses itself and is not a valid parcel polygon.")
    return {
        "vertices": [{"easting": x, "northing": y} for x, y in ring[:-1]],
        "area_square_units": polygon_area(ring),
        "perimeter_units": perimeter(ring),
        "is_closed": len(ring) > 1 and ring[0] == ring[-1],
        "has_self_intersection": has_self_intersection(ring),
        "segments": [
            {
                "sequence": item.sequence,
                "start": {"easting": item.start[0], "northing": item.start[1]},
                "end": {"easting": item.end[0], "northing": item.end[1]},
                "distance": item.distance,
                "azimuth_degrees": item.azimuth_degrees,
            }
            for item in segments(ring)
        ],
        "warnings": warnings,
    }
