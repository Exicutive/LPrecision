# Land Boundary Engine

This is the first learning milestone: upload a DXF survey plan, list candidate
polylines, and calculate each candidate's planar area, perimeter, and segment
azimuths. It does not claim legal or field-survey verification.

## What you will learn

1. A DXF is a CAD document made of entities such as polylines and text.
2. A parcel boundary is usually a closed polyline.
3. The polygon's vertices determine its area and perimeter.
4. Source files and validation warnings must stay with every calculation.

## Run locally

Create and activate a virtual environment, install dependencies, then start
the local server:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` and upload a DXF file.

If a managed Windows environment prevents virtual-environment creation, install
the packages for your user account instead:

```powershell
py -m pip install --user -r requirements.txt
py -m uvicorn app.main:app --reload
```

## First exercise

Read `app/geometry.py`. The `polygon_area` function uses the shoelace formula.
Change the square in `tests/test_geometry.py` to dimensions from your plan and
run:

```powershell
py -m pytest
```

## Next milestone

Draw the selected DXF boundary in the browser and export its vertices,
segments, and plan metadata as CSV. Only then add a database and user accounts.
