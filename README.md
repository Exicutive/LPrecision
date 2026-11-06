# TerraLedger

A Django-backed digital land allocation and boundary verification platform for
estate developments.

## Run it

The frontend CSS is compiled locally with Tailwind CSS. Run the frontend from
the `frontend` folder:

```powershell
cd frontend
npm install
npm start
```

Then open http://127.0.0.1:8080 in a modern browser. `npm start` rebuilds the
stylesheet before serving only the `frontend` folder.

Start the Django account backend in a second terminal:

```powershell
cd backend
.\.lpvenv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

By default, the backend uses SQLite. To use PostgreSQL, install the backend
requirements and set these variables in the same PowerShell terminal before
running migrations and the server:

```powershell
$env:PGDATABASE = "lprecision"
$env:PGUSER = "postgres"
$env:PGPASSWORD = "your-local-password"
$env:PGHOST = "127.0.0.1"
$env:PGPORT = "5432"
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Create the `lprecision` database in PostgreSQL first. Keep real database
passwords in environment variables, not committed settings files.

The sign-in and registration forms use Django session cookies and CSRF
protection. Create an account in the frontend at `/property/`, or sign in with
an account created through Django. The property portal displays only allocations
verified and returned by the backend for the signed-in user.

Use **Forgot password?** on the sign-in page to request a secure reset link.
During local development, Django prints the link in the terminal that runs
`manage.py runserver`. The default `TERRALEDGER_EMAIL_BACKEND` is Django's
console backend; it is for development only. To use SMTP, configure
`TERRALEDGER_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`,
`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`,
`EMAIL_USE_TLS` or `EMAIL_USE_SSL`, and `DEFAULT_FROM_EMAIL` through the
deployment environment or secret store. Do not commit provider credentials.
Set `TERRALEDGER_FRONTEND_URL` to the public frontend origin and optionally
set `TERRALEDGER_ALLOCATION_INVITATION_DAYS` (default: 7). Production email
delivery has not been verified until provider credentials and delivery are
tested in that environment.

During design work, run `npm run dev:css` in a second frontend terminal to
rebuild Tailwind CSS when `styles.css` changes.

## Code structure

- `frontend/app.js` — application router, event binding, and navigation actions
- `frontend/js/data.js` — empty interface state populated by backend responses
- `frontend/js/components.js` — reusable buttons, status badges, branding, and parcel SVG
- `frontend/js/views/` — public, authentication, admin, property, and modal views
- `frontend/styles.css` — editable Tailwind source stylesheet
- `frontend/dist/tailwind.css` — generated stylesheet served by the pages

## Application routes

The browser uses these separate frontend endpoints:

- `/` — public landing page
- `/admin/` — administrator workspace
- `/property/` — property-holder invitation and dashboard journey

## Administrative hierarchy

TerraLedger has two backend-enforced administrative roles:

- **Platform Admin** is an explicit platform-only role. Platform Admins register,
  suspend, and reactivate companies; invite the first Company Admin; manage
  platform settings; and review platform audit events. It does not grant access
  to any company's estate records.
- **Company Admin** is an explicit membership for one company. Every company
  administration endpoint verifies that membership and scopes estates, parcels,
  allocations, survey plans, settings, and property invitations to that company.

The Platform Admin starts the Company Admin invitation flow at
`POST /api/records/platform/companies/<company_id>/invite-first-admin/`.
The invite can be accepted by the already-signed-in invited user, or creates an
account only when no account with that email exists. Public account registration
does not accept or grant administrative roles. Property allocations and property
invitations never create administrative memberships.

### Company setup workflow

1. A Platform Admin registers the company with its name, company email, contact
   person, and phone number. The organisation begins in **Pending setup**;
   creating it grants no user access.
2. The Platform Admin sends the first Company Admin an email-bound invitation.
   The email contains a signed one-time link to the property portal.
3. The invitee signs in to the existing TerraLedger account with that email, or
   creates an account with that email, then accepts. Only then does the backend
   create the Company Admin membership and mark company setup complete.

## Allocation invitations

Company Admins allocate only available, approved parcels from their own active
company estates. Allocation, parcel status, and a hashed-token
`AllocationInvitation` are created in one database transaction. Email is
attempted after commit; the current project has no task queue, so delivery is
not yet a background job. A delivery failure is recorded without undoing the
allocation and can be retried from the Company Admin allocation list. Resending
revokes earlier invitation tokens and creates a fresh expiring token.

Recipients claim an allocation through
`GET /api/records/allocation-invitations/status/?token=...` and
`POST /api/records/allocation-invitations/accept/`. The invitation fixes the
email address; new accounts are created only after the invitation validates,
and existing accounts must sign in before claiming. The invitation email
proves ownership of that address and is recorded as a verified email. The
recipient dashboard reads only allocations linked to its authenticated user
through `GET /api/records/my-property/`; an individual property is retrieved
through `GET /api/records/my-property/<allocation_id>/`.

Company Admin management routes remain company-scoped:
`POST /api/records/companies/<company_id>/allocations/`,
`POST /api/records/companies/<company_id>/allocations/<allocation_id>/resend-invitation/`,
and `POST /api/records/companies/<company_id>/allocations/<allocation_id>/revoke/`.
Revocation retains the allocation history and does not delete the parcel.
Allocation records do not independently establish legal title.

## Company and account settings

The Company Admin dashboard's **Company settings** page contains company
information, account settings, notification preferences, and read-only company
details. Company information is loaded and changed only after the backend
confirms the signed-in user's active Company Admin membership. Logo uploads are
limited to PNG or JPEG files of up to 5 MB.

The company settings endpoint is
`GET|POST /api/records/companies/<company_id>/settings/`. It validates
membership for the supplied company ID and rejects changes to protected company
ID, registration date, status, and company code. Company Admins can view but
cannot edit the company contact email; they must contact a Platform Admin to
request a change. Company notification
preferences are stored in the company's settings JSON and control email alerts
to active Company Admin accounts for allocation, survey-plan upload,
survey-plan verification, and master-layout processing events. These alerts
use the configured Django email backend and are attempted after the event's
database transaction commits.

Account name and password updates affect only the authenticated user through
`PATCH /api/accounts/profile/` and `POST /api/accounts/password-change/`.
`POST /api/accounts/email-change/` sends an expiring verification link to the
requested address; the account email is not changed until that link is
confirmed through `POST /api/accounts/email-change/confirm/`. Email-change
tokens are stored only as hashes and are single-use.

## Individual survey plans

Company Admins can upload a PDF and its survey metadata against an allocation
through `POST /api/records/companies/<company_id>/survey-plans/`. Plans can be
listed and reviewed only within that company. The recipient can see a plan only
from their linked property record. Private document endpoints are
`GET /api/records/companies/<company_id>/survey-plans/<survey_plan_id>/download/`
and
`GET /api/records/my-property/<allocation_id>/survey-plans/<survey_plan_id>/download/`.
Append `?inline=1` to view a validated PDF in the browser; without it, the
document is downloaded as an attachment. Both modes require an authenticated
and authorized session.

Survey plan files use private storage configured by
`TERRALEDGER_PRIVATE_MEDIA_ROOT` (default: `backend/private_media`) rather than
public media URLs. The workflow records a SHA-256 checksum, rejects invalid
PDF uploads, and tracks internal verification history. Review status is not
government certification or a legal determination of title; OCR and spatial
boundary verification are not implemented.

## Backend apps

The backend separates domain models, services, admin registrations, URL
definitions, and request handlers into the `companies`, `platform_admin`,
`estates`, `parcels`, `allocations`, `survey_plans`, and `master_layouts`
Django apps. Shared API serialization helpers are in `records.api_helpers`.
The `records` app remains as the URL aggregator for the existing
`/api/records/` prefix and retains its migration history; domain models,
services, views, and email templates live in their owning apps.

The ownership migration preserves the existing `records_*` database tables
and their data; it does not create replacement tables or copy domain records.
It remaps existing Django content-type labels so model permissions and admin
history remain associated with the moved models. Run `python manage.py migrate`
after pulling these changes. Existing Django staff users are migrated once to
explicit Platform Admin roles; new Company Admins are created only through
invitations.

## Integrations still required

Production email delivery, virus/file-type validation for uploads, approved
document storage, and legal/survey review workflows should be configured before
handling real customer records.
