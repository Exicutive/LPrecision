# Land Boundary Guidance System Guidelines

These rules apply to every user interface, API endpoint, data model, notification, and future integration in the system.

## 1. Product purpose

The system helps a property holder understand their recorded plot boundary from a submitted survey plan or coordinate set. It may provide live, optional location guidance such as whether the holder is inside or outside the recorded boundary and their approximate distance from it.

It is not a government land registry, a substitute for a licensed surveyor, a title-verification service, or a legal determination of ownership.

## 2. Source of boundary information

- A property holder may upload a survey-plan PDF for an active property allocation.
- A property holder may submit boundary coordinates for that same allocation.
- A survey-plan PDF is supporting evidence; coordinates are the data used to construct the boundary polygon.
- Do not claim that a PDF was automatically interpreted unless the system has actually extracted and validated its coordinates.
- Do not change a parcel boundary from an image or PDF alone without an explicit coordinate set or a user-confirmed digitisation result.

## 3. Coordinate integrity

- Store the original submitted coordinates exactly as supplied, with their declared coordinate reference system (CRS), datum, units, and source.
- Convert a validated working copy to WGS84 longitude/latitude for phone-location comparisons and web maps.
- Require the contributor to select the CRS when it cannot be determined reliably. Relevant Nigerian options include Minna Datum NTM belts, Minna Datum UTM zones, and WGS84.
- Never silently assume that projected coordinates are WGS84 GPS coordinates.
- Reject malformed coordinates, non-finite values, polygons with fewer than three vertices, and self-intersecting or otherwise invalid polygons.
- Record who supplied the coordinates, when, the source document, and any transformation applied.
- Preserve prior boundary versions; never overwrite them without an audit record and a clear reason.

## 4. Accuracy and guidance language

- Clearly distinguish `recorded boundary`, `approximate phone location`, and `survey-grade RTK location` in the interface.
- Treat ordinary phone GPS as approximate. Do not use it to make centimetre-level, legal, or beacon-placement claims.
- Display the current location accuracy reported by the device when available.
- If accuracy is too poor for useful guidance, say so and avoid a definitive inside/outside statement.
- Use measured language: “approximately 8 metres outside the recorded north boundary,” not “you are trespassing” or “this is your legal boundary.”
- Use geodesic distance calculations for WGS84 coordinates; do not calculate metres by directly subtracting longitude and latitude values.
- Support RTK/GNSS device data as a future higher-accuracy input, while still recording its datum, fix type, and reported accuracy.

## 5. Live-location and audio consent
Godfather of harlem. Make your music to move with you
- Live location is strictly opt-in and starts only after the holder selects **Start boundary guidance**.
- Explain why location is requested before the browser or mobile operating system permission prompt appears.
- Give the holder a prominent **Stop guidance** control at all times.
- Do not retain location history by default. Store it only when the holder explicitly starts a named tracking or evidence session and understands the retention period.
- Audio guidance is optional, off by default, and must have an easy mute control.
- Audio messages must be short, factual, rate-limited, and non-alarming. Provide the same information visually and through vibration where supported.
- Guidance must continue to be useful without sound, location permission, or network access where cached boundary data is available.

## 6. User experience

- Place boundary actions in the property-holder portal, not the Company Admin workspace.
- For every active property, show an obvious **Upload survey plan**, **Enter coordinates**, and, when a valid polygon exists, **Start boundary guidance** action.
- Explain what format is accepted and show a copyable coordinate example.
- Preview a proposed polygon before saving it and identify invalid vertices in plain language.
- After saving, state what changed: document stored, boundary recorded, coordinate system used, and whether location guidance is ready.
- Make every boundary workflow usable on a mobile phone with touch-sized controls, clear status messages, and low-bandwidth fallbacks.

## 7. Roles and permissions

- Only the authenticated holder of an active allocation can upload a survey plan or submit coordinates for that allocation.
- Company Admins manage estates, parcels, and allocations; they do not review, verify, alter, or download holders’ individual survey-plan submissions.
- Platform Admins may access only what is required for platform governance and support, and access must be audited.
- Every document and boundary endpoint must enforce object-level authorization, not just role-level authorization.

## 8. Documents and file handling

- Accept only the documented formats and enforce type, signature, size, filename, and malware-scanning controls as appropriate.
- Store uploaded survey documents privately. Use authenticated, short-lived or protected delivery routes rather than public file URLs.
- Allow holders to replace or remove an optional supporting document where policy permits, while retaining the corresponding audit event.
- Images and documents must use durable object storage in production. Do not rely on a free Render service’s local filesystem for persistent uploads.

## 9. Security and auditability

- Require HTTPS for all application, API, file, and geolocation traffic.
- Use CSRF protection, secure HTTP-only sessions, rate limits, input validation, and private cache controls for authenticated data.
- Audit boundary submission, replacement, deletion, coordinate transformation, guidance-session start/stop, and privileged access.
- Audit records must identify actor, time, property, action, before/after values where applicable, and source.
- Never expose another holder’s allocation, document, coordinates, or location through search, predictable URLs, logs, or error messages.

## 10. External data and legal status

- Government cadastral or acquisition overlays may be added only through authorized, documented data sources.
- Clearly label the data provider, retrieval date, coverage limits, and whether an overlay is informational or authoritative.
- Do not present a third-party or government data match as title confirmation unless the responsible authority explicitly provides that determination.
- Keep legal and safety disclaimers close to boundary guidance, not hidden only in terms of service.

## 11. Reliability and failure handling

- Validate a full boundary before making it live; failed uploads or invalid transformations must leave the previous live boundary unchanged.
- Design operations to be idempotent so a retry does not create duplicate documents or boundary versions.
- Show actionable errors: missing CRS, invalid coordinate pair, poor GPS accuracy, location permission denied, file too large, or offline state.
- Test coordinate conversion, point-in-polygon decisions, distance calculations, authorization boundaries, and file uploads/removal before release.

## 12. Release checklist

Before releasing a boundary-related change, confirm that:

1. The feature uses an explicitly declared CRS and datum.
2. It does not overstate GPS accuracy or legal certainty.
3. It works for a property holder on mobile and without audio.
4. Location and audio require explicit, reversible consent.
5. All related APIs enforce object-level authorization.
6. Submitted documents and files are private and stored durably in production.
7. Audit events and clear failure messages are present.
8. Automated tests cover valid, invalid, unauthorized, and retry scenarios.

## Current implementation boundary

The current release accepts WGS84 longitude/latitude coordinates (`EPSG:4326`) for live browser guidance. It rejects Minna Datum, NTM, and UTM submissions rather than guessing a conversion. Datum conversion, government-cadastral overlays, RTK receiver ingestion, and durable object storage remain planned integrations that require approved external services or survey-grade equipment.
