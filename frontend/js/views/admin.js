import { data, state } from "../data.js";
import { brand, button, parcelSvg, status } from "../components.js";

const navItems = [
  ["overview", "▦", "Overview"],
  ["estates", "⌂", "Estates"],
  ["parcels", "⌗", "Parcels"],
  ["allocations", "↗", "Allocations"],
  ["invitations", "✉", "Invitations"],
  ["survey", "◫", "Survey data"],
  ["activity", "◷", "Activity logs"],
  ["settings", "⚙", "Settings"],
];

function navButton([key, icon, label]) {
  return /* HTML */ `<button
    class="${state.adminPage === key ? "active" : ""}"
    data-action="admin-page:${key}"
  >
    <span class="nav-icon">${icon}</span>
    <span>${label}</span>
  </button>`;
}

function adminLayout(content, title) {
  return /* HTML */ `<div class="app-shell">
    <aside class="sidebar">
      <a class="brand" href="#admin">${brand()}</a>
      <p class="sidebar-label">Estate workspace</p>
      <nav class="side-nav">${navItems.map(navButton).join("")}</nav>
      <div class="sidebar-bottom">
        <strong>Demo workspace</strong><span>Uses local mock data only</span>
      </div>
    </aside>
    <section class="main-area">
      <header class="app-header">
        <div class="breadcrumb">
          Estate workspace / <strong>${title}</strong>
        </div>
        <div class="header-tools">
          <span class="demo-badge">Frontend demonstration</span
          >${button("View public site", "public", "ghost", "small")}
          <div class="profile">
            <div class="profile-avatar">AO</div>
            <span>Amara Okeke</span>
          </div>
        </div>
      </header>
      <main class="page">${content}</main>
    </section>
  </div>`;
}

const stat = (label, value, note) =>
  `<article class="stat-card"><span>${label}</span><strong>${value}</strong><small>${note}</small></article>`;
const activityRows = (entries) =>
  entries
    .map(
      ([title, detail, time]) =>
        `<div class="activity-row"><i class="activity-dot"></i><div><strong>${title}</strong><span>${detail}</span></div><time>${time}</time></div>`,
    )
    .join("");
const allocationBars = () =>
  /* HTML */ `<div class="chart-wrap">
    <div class="bar-chart">
      <div class="bar-row">
        <span>Allocated</span>
        <div class="bar-track"><i style="width:73%"></i></div>
        <b>183</b>
      </div>
      <div class="bar-row">
        <span>Available</span>
        <div class="bar-track"><i style="width:27%"></i></div>
        <b>67</b>
      </div>
      <div class="bar-row">
        <span>Pending</span>
        <div class="bar-track"><i style="width:4%"></i></div>
        <b>4</b>
      </div>
    </div>
  </div>`;

function parcelRow(parcel) {
  return /* HTML */ `<tr data-selectable data-action="parcel:${parcel.plot}">
    <td>
      <span class="table-title">${parcel.plot}</span
      ><span class="subcell">Block ${parcel.block}</span>
    </td>
    <td>Abeni Gardens</td>
    <td>${parcel.area}</td>
    <td>${status(parcel.status)}</td>
    <td>${parcel.person}</td>
    <td>${parcel.updated}</td>
  </tr>`;
}

function invitationRow(invitation) {
  const resendButton =
    invitation.status === "Pending"
      ? button(
          "Resend demo",
          "toast:Demo invitation queued locally.",
          "secondary",
          "small",
        )
      : "";

  return /* HTML */ `<tr>
    <td>
      <span class="table-title">${invitation.recipient}</span
      ><span class="subcell">${invitation.email}</span>
    </td>
    <td>Abeni Gardens · ${invitation.parcel}</td>
    <td>${invitation.sent}</td>
    <td>${invitation.expiry}</td>
    <td>${status(invitation.status)}</td>
    <td>${resendButton}</td>
  </tr>`;
}

function parcelTable(parcels) {
  return /* HTML */ `<div class="table-wrap">
    <table class="data-table">
      <thead>
        <tr>
          <th>Plot</th>
          <th>Estate</th>
          <th>Area</th>
          <th>Status</th>
          <th>Assigned to</th>
          <th>Updated</th>
        </tr>
      </thead>
      <tbody>
        ${parcels.map(parcelRow).join("")}
      </tbody>
    </table>
  </div>`;
}

function overviewPage() {
  const estate = data.estate;
  const activity = [
    [
      "A-001 allocation accepted",
      "Chiamaka Okoro can now view her property record",
      "Today, 10:24",
    ],
    [
      "Invitation created for Plot A-004",
      "Awaiting Ngozi Eze’s response",
      "Yesterday, 16:42",
    ],
    [
      "Survey plan import reviewed",
      "24 parcel geometries are ready for use",
      "06 Oct 2026",
    ],
    [
      "Plot B-011 marked available",
      "Allocation record updated by Amara Okeke",
      "05 Oct 2026",
    ],
  ];
  return adminLayout(
    /* HTML */ `<div class="page-head">
        <div>
          <p class="eyebrow">Portfolio overview</p>
          <h1>Good morning, Amara</h1>
          <p>Here is what is happening across your estate records.</p>
        </div>
        ${button("Allocate property", "open-allocation", "primary")}
      </div>
      <section class="cards">
        ${stat("Total estates", "1", "Abeni Gardens Estate")}
        ${stat("Total parcels", estate.parcels, "Surveyed parcel records")}
        ${stat("Allocated parcels", estate.allocated, "73% of portfolio")}
        ${stat("Available parcels", estate.available, "Ready for allocation")}
        ${stat("Pending invitations", "4", "Require recipient action")}
      </section>
      <section class="content-grid">
        <article class="panel">
          <div class="panel-head">
            <div>
              <h2>Recent allocation activity</h2>
              <p>Latest changes in Abeni Gardens Estate</p>
            </div>
            <button
              class="button ghost small"
              data-action="admin-page:activity"
            >
              View all
            </button>
          </div>
          <div class="activity">${activityRows(activity)}</div>
        </article>
        <aside class="panel">
          <div class="panel-head">
            <div>
              <h2>Parcel allocation status</h2>
              <p>250 surveyed parcels</p>
            </div>
          </div>
          ${allocationBars()}
        </aside>
      </section>
      <section class="panel" style="margin-top:17px">
        <div class="panel-head">
          <div>
            <h2>Recently updated parcels</h2>
            <p>Parcel records changed in the last seven days</p>
          </div>
          ${button("Manage parcels", "admin-page:parcels", "secondary", "small")}
        </div>
        ${parcelTable(data.parcels.slice(0, 5))}
      </section>`,
    "Overview",
  );
}

function estatesPage() {
  const estate = data.estate;
  return adminLayout(
    /* HTML */ `<div class="page-head">
        <div>
          <p class="eyebrow">Estate directory</p>
          <h1>Estates</h1>
          <p>Manage estate-level parcel and allocation records.</p>
        </div>
        ${button("Add estate", "toast:Estate creation is a demonstration-only action.", "primary")}
      </div>
      <div class="filters">
        <input
          aria-label="Search estates"
          placeholder="Search estates or locations"
        /><select aria-label="Filter estate status">
          <option>All statuses</option>
          <option>Active</option>
          <option>Inactive</option>
        </select>
      </div>
      <section class="panel">
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Estate</th>
                <th>Location</th>
                <th>Parcels</th>
                <th>Allocated</th>
                <th>Available</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr data-selectable data-action="admin-page:parcels">
                <td>
                  <span class="table-title">${estate.name}</span
                  ><span class="subcell">Estate record EG-001</span>
                </td>
                <td>
                  ${estate.location}<span class="subcell"
                    >${estate.lga}, ${estate.state}</span
                  >
                </td>
                <td>${estate.parcels}</td>
                <td>${estate.allocated}</td>
                <td>${estate.available}</td>
                <td>${status("Active")}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
      <section class="content-grid">
        <article class="panel">
          <div class="panel-head">
            <div>
              <h2>Estate overview</h2>
              <p>Allocation and parcel readiness</p>
            </div>
          </div>
          ${allocationBars()}
        </article>
        <article class="boundary-panel">
          ${parcelSvg()}
          <div class="boundary-top">
            <span>Estate parcel map · demonstration</span><span>N ↑</span>
          </div>
          <div class="boundary-legend">
            <span>Selected parcel: A-003</span
            ><span>Open map integration required</span>
          </div>
        </article>
      </section>`,
    "Estates",
  );
}

function parcelsPage() {
  return adminLayout(
    /* HTML */ `<div class="page-head">
        <div>
          <p class="eyebrow">Parcel management</p>
          <h1>Parcels</h1>
          <p>
            Review parcel details, survey boundaries and allocation readiness.
          </p>
        </div>
        ${button("Allocate property", "open-allocation", "primary")}
      </div>
      <div class="filters">
        <input
          id="parcel-search"
          aria-label="Search parcels"
          placeholder="Search plot, block or assigned person"
        /><select id="parcel-status" aria-label="Filter parcel status">
          <option value="All">All statuses</option>
          <option>Available</option>
          <option>Allocated</option>
          <option>Pending</option>
        </select>
      </div>
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2>Parcel records</h2>
            <p>Click a record to inspect its boundary detail.</p>
          </div>
          <span class="muted"
            >${data.parcels.length} demonstration records</span
          >
        </div>
        ${parcelTable(data.parcels)}
      </section>`,
    "Parcels",
  );
}

function allocationsPage() {
  return adminLayout(
    /* HTML */ `<div class="page-head">
        <div>
          <p class="eyebrow">Allocation management</p>
          <h1>Allocations</h1>
          <p>
            Track approved parcel assignments and their invitation progress.
          </p>
        </div>
        ${button("Start allocation", "open-allocation", "primary")}
      </div>
      <section class="panel">
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Reference</th>
                <th>Property</th>
                <th>Allottee</th>
                <th>Email</th>
                <th>Allocation date</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><span class="table-title">ALC-AG-2026-0183</span></td>
                <td>Abeni Gardens · A-001</td>
                <td>Chiamaka Okoro</td>
                <td>chiamaka.okoro@example.com</td>
                <td>12 Sep 2026</td>
                <td>${status("Accepted")}</td>
              </tr>
              <tr>
                <td><span class="table-title">ALC-AG-2026-0184</span></td>
                <td>Abeni Gardens · A-002</td>
                <td>Tunde Adebayo</td>
                <td>tunde.adebayo@example.com</td>
                <td>20 Sep 2026</td>
                <td>${status("Accepted")}</td>
              </tr>
              <tr>
                <td><span class="table-title">ALC-AG-2026-0185</span></td>
                <td>Abeni Gardens · A-004</td>
                <td>Ngozi Eze</td>
                <td>ngozi.eze@example.com</td>
                <td>06 Oct 2026</td>
                <td>${status("Pending")}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>`,
    "Allocations",
  );
}

function invitationsPage() {
  return adminLayout(
    /* HTML */ `<div class="page-head">
        <div>
          <p class="eyebrow">Invitation management</p>
          <h1>Invitations</h1>
          <p>
            Invitation status is simulated locally in this frontend
            demonstration.
          </p>
        </div>
        ${button("Send invitation", "open-allocation", "primary")}
      </div>
      <section class="panel">
        <div class="panel-head">
          <div>
            <h2>Allocation invitations</h2>
            <p>Linked to a specific recipient and allocated property.</p>
          </div>
          <span class="demo-badge">No email service connected</span>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Recipient</th>
                <th>Property</th>
                <th>Sent</th>
                <th>Expires</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              ${data.invitations.map(invitationRow).join("")}
            </tbody>
          </table>
        </div>
      </section>`,
    "Invitations",
  );
}

function surveyPage() {
  return adminLayout(
    /* HTML */ `<div class="page-head">
        <div>
          <p class="eyebrow">Survey data</p>
          <h1>Survey imports</h1>
          <p>
            Review demonstration import states before releasing parcel records.
          </p>
        </div>
        ${button("Import survey data", "toast:File processing needs a backend integration.", "primary")}
      </div>
      <section class="two-column">
        <article class="form-card">
          <h2>Import survey file</h2>
          <p>
            Frontend capability preview only. No file will be uploaded or
            processed.
          </p>
          <div class="upload-box">
            <div>
              <strong>Drop a survey file here</strong
              ><span>Intended formats: PDF, DXF, CSV and GeoJSON</span>
              <div style="margin-top:14px">
                ${button("Choose a file", "toast:File import is unavailable in this frontend demonstration.", "secondary", "small")}
              </div>
            </div>
          </div>
        </article>
        <article class="form-card">
          <h2>Last reviewed import</h2>
          <p>A clearly labeled demonstration dataset.</p>
          <div class="survey-stats">
            <div><span>Parcels found</span><strong>24</strong></div>
            <div><span>Geometry valid</span><strong>23</strong></div>
            <div><span>Warnings</span><strong>1</strong></div>
          </div>
          <div class="notice">
            Warning: Parcel C-014 has an unclosed geometry and needs survey
            review before it can be allocated.
          </div>
        </article>
      </section>
      <section class="panel" style="margin-top:17px">
        <div class="panel-head">
          <div>
            <h2>Import history</h2>
            <p>Illustrative only — no survey files have been processed.</p>
          </div>
        </div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>File</th>
                <th>Estate</th>
                <th>Imported</th>
                <th>Records</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>
                  <span class="table-title">abeni-gardens-block-a.dxf</span
                  ><span class="subcell">Demonstration data</span>
                </td>
                <td>Abeni Gardens</td>
                <td>06 Oct 2026</td>
                <td>24</td>
                <td>${status("Processing")}</td>
              </tr>
              <tr>
                <td>
                  <span class="table-title">abeni-gardens-overview.csv</span
                  ><span class="subcell">Demonstration data</span>
                </td>
                <td>Abeni Gardens</td>
                <td>21 Sep 2026</td>
                <td>250</td>
                <td>${status("Active")}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>`,
    "Survey data",
  );
}

function activityPage() {
  const activity = [
    [
      "Allocation accepted",
      "Chiamaka Okoro accepted access to Plot A-001",
      "Today, 10:24",
    ],
    [
      "Invitation created",
      "Invitation prepared for Ngozi Eze and Plot A-004",
      "Yesterday, 16:42",
    ],
    [
      "Survey import reviewed",
      "Block A import passed 23 of 24 geometry checks",
      "06 Oct 2026",
    ],
    ["Parcel updated", "A-003 marked ready for allocation", "05 Oct 2026"],
    [
      "Estate profile updated",
      "Abeni Gardens record updated by Amara Okeke",
      "02 Oct 2026",
    ],
  ];
  return adminLayout(
    /* HTML */ `<div class="page-head">
        <div>
          <p class="eyebrow">Audit view</p>
          <h1>Activity logs</h1>
          <p>Sample audit events for the frontend experience.</p>
        </div>
      </div>
      <section class="panel">
        <div class="activity">${activityRows(activity)}</div>
      </section>`,
    "Activity logs",
  );
}

function settingsPage() {
  return adminLayout(
    /* HTML */ `<div class="page-head">
        <div>
          <p class="eyebrow">Workspace preferences</p>
          <h1>Settings</h1>
          <p>These controls are visual only and are not persisted.</p>
        </div>
      </div>
      <section class="two-column">
        <article class="form-card">
          <h2>Organization profile</h2>
          <div class="form-grid">
            <div class="field">
              <label>Organization name</label
              ><input value="Abeni Estate Development Ltd." />
            </div>
            <div class="field">
              <label>Support email</label
              ><input value="records@abeni.example" />
            </div>
            <div class="field full">
              <label>Estate address</label
              ><input value="Ibeju-Lekki, Lagos State" />
            </div>
          </div>
          <div class="form-actions">
            ${button("Save changes", "toast:Settings are not saved in this frontend demonstration.", "primary")}
          </div>
        </article>
        <article class="form-card">
          <h2>Access policy</h2>
          <p>
            Backend authorization must enforce access policy on every protected
            request.
          </p>
          <div class="notice">
            This interface can demonstrate navigation only. Authentication,
            roles and invitations need secure server-side implementation.
          </div>
        </article>
      </section>`,
    "Settings",
  );
}

export function adminView() {
  return {
    overview: overviewPage,
    estates: estatesPage,
    parcels: parcelsPage,
    allocations: allocationsPage,
    invitations: invitationsPage,
    survey: surveyPage,
    activity: activityPage,
    settings: settingsPage,
  }[state.adminPage]();
}
