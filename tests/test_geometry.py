from app.geometry import analyse_polygon, azimuth_from_north, polygon_area


def test_square_area_and_perimeter() -> None:
    result = analyse_polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    assert polygon_area([(0, 0), (10, 0), (10, 10), (0, 10)]) == 100
    assert result["perimeter_units"] == 40
    assert result["has_self_intersection"] is False


def test_azimuth_is_clockwise_from_north() -> None:
    assert azimuth_from_north((0, 0), (10, 0)) == 90
    assert azimuth_from_north((0, 0), (0, 10)) == 0


def test_crossing_boundary_is_flagged() -> None:
    result = analyse_polygon([(0, 0), (10, 10), (0, 10), (10, 0)])
    assert result["has_self_intersection"] is True
