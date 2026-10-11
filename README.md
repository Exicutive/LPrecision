# TerraLedger 

A self contained prototype for a digital land allocation and boundary
verification platform for estate developments.

## Run it

There is no backend, database, API, authentication service, or file processor.
The CSS is compiled locally with Tailwind CSS. Install dependencies and start
the local web server:

```powershell
npm install
npm start
```

Then open http://localhost:8000 in a modern browser. `npm start` rebuilds the
stylesheet before serving the app. During design work, run `npm run dev:css`
in a second terminal to rebuild Tailwind CSS when `styles.css`, `index.html`, or
`app.js` changes.

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
values are local mock data in `app.js`. Interactions demonstrate interface
states only. No invitations, uploads, allocations, accounts, settings, GPS
requests, or records are created outside the browser session.

## Integrations still required

A production implementation still needs authenticated backend APIs, role and
authorization enforcement, invitation-token validation and email delivery,
survey-file processing and validation, an approved document store, mapping and
device-location integrations, audit logs, and legal/survey review workflows.
