import io

import ezdxf
from fastapi.testclient import TestClient

from app.main import app


def test_dxf_upload_endpoint_returns_candidates() -> None:
    document = ezdxf.new()
    document.modelspace().add_lwpolyline([(0, 0), (5, 0), (5, 5), (0, 5)], close=True)
    stream = io.StringIO()
    document.write(stream)

    response = TestClient(app).post(
        "/api/dxf/inspect",
        files={"file": ("survey-plan.dxf", stream.getvalue().encode("utf-8"), "application/dxf")},
    )

    assert response.status_code == 200
    assert response.json()["candidate_boundaries"][0]["analysis"]["area_square_units"] == 25
