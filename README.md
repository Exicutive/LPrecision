# TerraLedger

A self contained prototype for a digital land allocation and boundary
verification platform for estate developments.

## Run it

The frontend CSS is compiled locally with Tailwind CSS. Run its commands from
the `frontend` folder:

```powershell
cd frontend
npm install
npm start
```

Then open http://localhost:8000 in a modern browser. `npm start` rebuilds the
stylesheet before serving only the `frontend` folder. During design work, run
`npm run dev:css` in a second terminal to rebuild Tailwind CSS when
`styles.css` changes.

To run the Django backend separately, open a second terminal and use its
project command from `backend`, typically:

```powershell
cd backend
python manage.py runserver
```

## Code structure

- `frontend/app.js` — application router, event binding, and navigation actions
- `frontend/js/data.js` — local mock data and interface state
- `frontend/js/components.js` — reusable buttons, status badges, branding, and parcel SVG
- `frontend/js/views/` — public, authentication, admin, property, and modal views
- `frontend/styles.css` — editable Tailwind source stylesheet
- `frontend/dist/tailwind.css` — generated stylesheet served by the pages

## Demonstrated routes

The browser-based navigation demonstrates these separate static endpoints:

- `/` — public landing page
- `/admin/` — administrator workspace
- `/property/` — property-holder invitation and dashboard journey

The administrator workspace demonstrates:

- Administrator workspace: overview, estates, parcels, allocations,
  invitations, survey data, activity logs, and settings
- Parcel detail panel with a surveyed-boundary-style SVG
- Four-step allocation and invitation workflow

The property-holder endpoint demonstrates:

- Invitation acceptance screen
- Property-holder dashboard: property overview, boundary detail, survey
  information, allocation information, documents, and simulated location view

## Local mock data

All estate, parcel, allocation, invitation, survey, document, and location
values are local mock data in `js/data.js`. Interactions demonstrate interface
states only. No invitations, uploads, allocations, accounts, settings, GPS
requests, or records are created outside the browser session.

## Integrations still required

A production implementation still needs authenticated backend APIs, role and
authorization enforcement, invitation-token validation and email delivery,
survey-file processing and validation, an approved document store, mapping and
device-location integrations, audit logs, and legal/survey review workflows.
