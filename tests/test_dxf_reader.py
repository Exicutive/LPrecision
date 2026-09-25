import io

import ezdxf

from app.dxf_reader import inspect_dxf_bytes


def test_extracts_a_closed_polyline_from_dxf() -> None:
    document = ezdxf.new()
    document.modelspace().add_lwpolyline(
        [(0, 0), (10, 0), (10, 10), (0, 10)],
        close=True,
        dxfattribs={"layer": "PARCEL_BOUNDARY"},
    )
    stream = io.StringIO()
    document.write(stream)

    result = inspect_dxf_bytes(stream.getvalue().encode("utf-8"))

    candidate = result["candidate_boundaries"][0]
    assert candidate["layer"] == "PARCEL_BOUNDARY"
    assert candidate["closed_in_dxf"] is True
    assert candidate["analysis"]["area_square_units"] == 100
