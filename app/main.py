"""First API for inspecting an uploaded DXF survey plan."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.dxf_reader import inspect_dxf_bytes


app = FastAPI(title="Land Boundary Engine", version="0.1.0")
WEB_DIR = Path(__file__).parent / "web"


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/dxf/inspect")
async def inspect_uploaded_dxf(file: UploadFile = File(...)) -> dict:
    if not file.filename or not file.filename.lower().endswith(".dxf"):
        raise HTTPException(status_code=400, detail="Upload a .dxf survey plan.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    try:
        return inspect_dxf_bytes(content)
    except Exception as error:
        raise HTTPException(status_code=422, detail=f"Could not read this DXF: {error}") from error
