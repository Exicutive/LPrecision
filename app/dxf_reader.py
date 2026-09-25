"""DXF parsing kept separate from geometry so both parts are easy to learn and test."""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import ezdxf

from app.geometry import analyse_polygon


def _polyline_points(entity: Any) -> list[tuple[float, float]]:
    if entity.dxftype() == "LWPOLYLINE":
        return [(point[0], point[1]) for point in entity.get_points("xy")]
    return [(vertex.dxf.location.x, vertex.dxf.location.y) for vertex in entity.vertices]


def inspect_document(document: Any) -> dict[str, Any]:
    """Summarise candidate parcel polylines in an opened DXF document."""
    modelspace = document.modelspace()
    layers = sorted(layer.dxf.name for layer in document.layers)
    candidates: list[dict[str, Any]] = []

    for entity in modelspace.query("LWPOLYLINE POLYLINE"):
        points = _polyline_points(entity)
        if len(points) < 3:
            continue
        analysis = analyse_polygon(points)
        candidates.append(
            {
                "entity_handle": entity.dxf.handle,
                "entity_type": entity.dxftype(),
                "layer": entity.dxf.layer,
                "vertex_count": len(points),
                "closed_in_dxf": bool(entity.closed),
                "analysis": analysis,
            }
        )

    text_count = len(list(modelspace.query("TEXT MTEXT")))
    return {
        "layers": layers,
        "candidate_boundaries": candidates,
        "text_entity_count": text_count,
        "message": "Select the parcel boundary with the survey-plan drawing before relying on any result.",
    }


def inspect_dxf(path: Path) -> dict[str, Any]:
    """Read candidate polylines and their calculation summaries from a DXF file."""
    return inspect_document(ezdxf.readfile(path))


def inspect_dxf_bytes(content: bytes) -> dict[str, Any]:
    """Inspect an uploaded text DXF without persisting a temporary copy."""
    stream = io.StringIO(content.decode("utf-8", errors="replace"))
    return inspect_document(ezdxf.read(stream))
