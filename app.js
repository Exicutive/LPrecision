const app = document.querySelector("#app");

const data = {
  estate: {
    name: "Abeni Gardens Estate",
    location: "Ibeju-Lekki, Lagos",
    state: "Lagos",
    lga: "Ibeju-Lekki",
    parcels: 250,
    allocated: 183,
    available: 67,
  },
  parcels: [
    {
      plot: "A-001",
      block: "A",
      status: "Allocated",
      person: "Chiamaka Okoro",
      area: "612 m²",
      updated: "08 Oct 2026",
    },
    {
      plot: "A-002",
      block: "A",
      status: "Allocated",
      person: "Tunde Adebayo",
      area: "598 m²",
      updated: "07 Oct 2026",
    },
    {
      plot: "A-003",
      block: "A",
      status: "Available",
      person: "—",
      area: "625 m²",
      updated: "07 Oct 2026",
    },
    {
      plot: "A-004",
      block: "A",
      status: "Pending",
      person: "Ngozi Eze",
      area: "604 m²",
      updated: "06 Oct 2026",
    },
    {
      plot: "A-005",
      block: "A",
      status: "Allocated",
      person: "Ifeanyi Umeh",
      area: "620 m²",
      updated: "05 Oct 2026",
    },
    {
      plot: "B-011",
      block: "B",
      status: "Available",
      person: "—",
      area: "640 m²",
      updated: "03 Oct 2026",
    },
  ],
  invitations: [
    {
      recipient: "Ngozi Eze",
      email: "ngozi.eze@example.com",
      parcel: "A-004",
      status: "Pending",
      sent: "06 Oct 2026",
      expiry: "13 Oct 2026",
    },
    {
      recipient: "Chiamaka Okoro",
      email: "chiamaka.okoro@example.com",
      parcel: "A-001",
      status: "Accepted",
      sent: "12 Sep 2026",
      expiry: "19 Sep 2026",
    },
    {
      recipient: "Seyi Adekunle",
      email: "seyi.a@example.com",
      parcel: "B-009",
      status: "Expired",
      sent: "18 Sep 2026",
      expiry: "25 Sep 2026",
    },
  ],
};
const currentEndpoint = window.location.pathname.includes("/admin/")
  ? "admin"
  : window.location.pathname.includes("/property/")
    ? "property"
    : "public";

let state = {
  view: currentEndpoint === "admin" ? "admin" : currentEndpoint === "property" ? "invite" : "public",
  adminPage: "overview",
  userPage: "property",
  propertyTab: "overview",
  modal: null,
  allocationStep: 1,
  selectedParcel: data.parcels[2],
  toast: "",
};

const icon =
  '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M4 20V9l8-5 8 5v11M8 20v-7h8v7"/><path d="M17 4v4"/></svg>';
const status = (value) =>
  `<span class="status ${value.toLowerCase()}">${value}</span>`;
const button = (text, action, kind = "secondary", extra = "") =>
  `<button class="button ${kind} ${extra}" data-action="${action}">${text}</button>`;

function endpointUrl(endpoint) {
  if (endpoint === "public") return currentEndpoint === "public" ? "./" : "../";
  if (endpoint === "admin") return currentEndpoint === "public" ? "admin/" : currentEndpoint === "admin" ? "./" : "../admin/";
  return currentEndpoint === "public" ? "property/" : currentEndpoint === "property" ? "./" : "../property/";
}

function navigateTo(endpoint) {
  window.location.assign(endpointUrl(endpoint));
}

function parcelSvg(dark = false) {
  const stroke = dark ? "#d9f8e6" : "#0c725e";
  const fill = dark ? "rgba(185,228,106,.26)" : "rgba(86,187,143,.20)";
  const text = dark ? "#fff" : "#094c3d";
  return `<svg class="boundary-svg" viewBox="0 0 560 330" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Demonstration surveyed parcel boundary"><polygon points="95,53 440,31 490,240 132,287 58,182" fill="${fill}" stroke="${stroke}" stroke-width="4"/><g fill="${stroke}" stroke="#fff" stroke-width="3"><circle cx="95" cy="53" r="8"/><circle cx="440" cy="31" r="8"/><circle cx="490" cy="240" r="8"/><circle cx="132" cy="287" r="8"/><circle cx="58" cy="182" r="8"/></g><g fill="${text}" font-size="13" font-weight="700"><text x="72" y="38">B1</text><text x="446" y="24">B2</text><text x="499" y="253">B3</text><text x="122" y="309">B4</text><text x="33" y="180">B5</text><text x="226" y="158" font-size="25">PLOT A-003</text><text x="237" y="180" font-size="13">625 m²</text></g><g fill="${text}" font-size="11"><text x="245" y="38">42.73 m</text><text x="462" y="146">31.84 m</text><text x="294" y="275">39.17 m</text></g></svg>`;
}

function publicView() {
  return `<header class="public-header"><div><a class="brand" href="#home">${brand()}</a><div class="public-actions"><span class="secure-label">Controlled record access</span>${button("User login", "invite", "primary", "small")}</div></div></header>
  <main><section class="hero"><div><p class="eyebrow">Digital land allocation & boundary verification</p><h1>Know Your Property. Understand Your Boundaries.</h1><p class="lead">A controlled digital workspace for estate teams and allottees to manage approved parcel records, surveyed boundaries and verified allocation access.</p><div class="hero-actions">${button("Access My Property →", "invite", "primary")}</div><p class="hero-note">Records are released only to authorized account holders.</p></div><div class="parcel-preview"><span class="map-label">Surveyed parcel preview</span>${parcelSvg(true)}<div class="parcel-info"><strong>Abeni Gardens Estate · Plot A-003</strong><span>Example boundary visualization — not a legal title or survey validation.</span></div></div></section>
  <section class="public-section"><div class="section-heading"><p class="eyebrow">Built for clear records</p><h2>A single, trusted view of allocation and survey information.</h2></div><div class="feature-grid">${[
    [
      "▦",
      "Digital property records",
      "Keep estate, allocation and approved parcel information together.",
    ],
    [
      "⌗",
      "Survey boundaries",
      "Visualize surveyed beacon points and parcel segments.",
    ],
    [
      "↗",
      "Controlled allocation",
      "Link a property only through an administrator-managed process.",
    ],
    ["◉", "Secure access", "Allottees see only records allocated to them."],
    [
      "⌖",
      "Boundary verification",
      "Prepare a clear path to future location-based checks.",
    ],
  ]
    .map(
      (x) =>
        `<article class="feature"><div class="feature-icon">${x[0]}</div><h3>${x[1]}</h3><p>${x[2]}</p></article>`,
    )
    .join("")}</div></section>
  <section class="public-section"><div class="section-heading"><p class="eyebrow">How it works</p><h2>Designed around a deliberate authorization journey.</h2></div><div class="steps"><article class="step"><span class="step-number">1</span><div><h3>Administrators prepare parcels</h3><p>Estate teams import approved survey information and manage availability.</p></div></article><article class="step"><span class="step-number">2</span><div><h3>Allottees receive invitations</h3><p>Each invitation is associated with a specific property allocation and recipient.</p></div></article><article class="step"><span class="step-number">3</span><div><h3>Authorized users view records</h3><p>Users can review only the property and boundary details linked to them.</p></div></article></div></section></main>${publicFooter()}`;
}
function brand() {
  return `<span class="brand-mark">${icon}</span><span class="brand-copy"><small>Land records portal</small><strong>TerraLedger</strong></span>`;
}
function publicFooter() {
  return `<footer class="public-footer"><div><section><a class="brand" href="#home">${brand()}</a><p>Digital land allocation and boundary verification in Nigerian estates.</p></section><section class="footer-links"><h3>Platform</h3><a href="#home">Property access</a><a href="#home">Administrator workspace</a><a href="#home">Survey records</a></section><section class="footer-links"><h3>Support</h3><a href="#home">Contact placeholder</a><a href="#home">Help centre</a><a href="#home">Report a record issue</a></section><section class="footer-links"><h3>Legal</h3><a href="#home">Privacy</a><a href="#home">Terms of use</a><a href="#home">Record disclaimer</a></section></div><div class="copyright">© 2026 TerraLedger.</div></footer>`;
}

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
function adminLayout(content, title) {
  return `<div class="app-shell"><aside class="sidebar"><a class="brand" href="#admin">${brand()}</a><p class="sidebar-label">Estate workspace</p><nav class="side-nav">${navItems.map(([key, ic, label]) => `<button class="${state.adminPage === key ? "active" : ""}" data-action="admin-page:${key}"><span class="nav-icon">${ic}</span><span>${label}</span></button>`).join("")}</nav><div class="sidebar-bottom"><strong>Demo workspace</strong><span>Uses local mock data only</span></div></aside><section class="main-area"><header class="app-header"><div class="breadcrumb">Estate workspace / <strong>${title}</strong></div><div class="header-tools"><span class="demo-badge">Frontend demonstration</span>${button("View public site", "public", "ghost", "small")}<div class="profile"><div class="profile-avatar">AO</div><span>Amara Okeke</span></div></div></header><main class="page">${content}</main></section></div>`;
}
function stat(label, value, note) {
  return `<article class="stat-card"><span>${label}</span><strong>${value}</strong><small>${note}</small></article>`;
}
function adminOverview() {
  const e = data.estate;
  return adminLayout(
    `<div class="page-head"><div><p class="eyebrow">Portfolio overview</p><h1>Good morning, Amara</h1><p>Here is what is happening across your estate records.</p></div>${button("Allocate property", "open-allocation", "primary")}</div><section class="cards">${stat("Total estates", "1", "Abeni Gardens Estate")}${stat("Total parcels", e.parcels, "Surveyed parcel records")}${stat("Allocated parcels", e.allocated, "73% of portfolio")}${stat("Available parcels", e.available, "Ready for allocation")}${stat("Pending invitations", "4", "Require recipient action")}</section><section class="content-grid"><article class="panel"><div class="panel-head"><div><h2>Recent allocation activity</h2><p>Latest changes in Abeni Gardens Estate</p></div><button class="button ghost small" data-action="admin-page:activity">View all</button></div><div class="activity">${[
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
    ]
      .map(
        (x) =>
          `<div class="activity-row"><i class="activity-dot"></i><div><strong>${x[0]}</strong><span>${x[1]}</span></div><time>${x[2]}</time></div>`,
      )
      .join(
        "",
      )}</div></article><aside class="panel"><div class="panel-head"><div><h2>Parcel allocation status</h2><p>250 surveyed parcels</p></div></div><div class="chart-wrap"><div class="bar-chart"><div class="bar-row"><span>Allocated</span><div class="bar-track"><i style="width:73%"></i></div><b>183</b></div><div class="bar-row"><span>Available</span><div class="bar-track"><i style="width:27%"></i></div><b>67</b></div><div class="bar-row"><span>Pending</span><div class="bar-track"><i style="width:4%"></i></div><b>4</b></div></div></div></aside></section><section class="panel" style="margin-top:17px"><div class="panel-head"><div><h2>Recently updated parcels</h2><p>Parcel records changed in the last seven days</p></div>${button("Manage parcels", "admin-page:parcels", "secondary", "small")}</div>${parcelTable(data.parcels.slice(0, 5))}</section>`,
    "Overview",
  );
}
function parcelTable(parcels) {
  return `<div class="table-wrap"><table class="data-table"><thead><tr><th>Plot</th><th>Estate</th><th>Area</th><th>Status</th><th>Assigned to</th><th>Updated</th></tr></thead><tbody>${parcels.map((p) => `<tr data-selectable data-action="parcel:${p.plot}"><td><span class="table-title">${p.plot}</span><span class="subcell">Block ${p.block}</span></td><td>Abeni Gardens</td><td>${p.area}</td><td>${status(p.status)}</td><td>${p.person}</td><td>${p.updated}</td></tr>`).join("")}</tbody></table></div>`;
}
function estatesPage() {
  const e = data.estate;
  return adminLayout(
    `<div class="page-head"><div><p class="eyebrow">Estate directory</p><h1>Estates</h1><p>Manage estate-level parcel and allocation records.</p></div>${button("Add estate", "toast:Estate creation is a demonstration-only action.", "primary")}</div><div class="filters"><input aria-label="Search estates" placeholder="Search estates or locations"><select aria-label="Filter estate status"><option>All statuses</option><option>Active</option><option>Inactive</option></select></div><section class="panel">${`<div class="table-wrap"><table class="data-table"><thead><tr><th>Estate</th><th>Location</th><th>Parcels</th><th>Allocated</th><th>Available</th><th>Status</th></tr></thead><tbody><tr data-selectable data-action="admin-page:parcels"><td><span class="table-title">${e.name}</span><span class="subcell">Estate record EG-001</span></td><td>${e.location}<span class="subcell">${e.lga}, ${e.state}</span></td><td>${e.parcels}</td><td>${e.allocated}</td><td>${e.available}</td><td>${status("Active")}</td></tr></tbody></table></div>`}</section><section class="content-grid"><article class="panel"><div class="panel-head"><div><h2>Estate overview</h2><p>Allocation and parcel readiness</p></div></div><div class="chart-wrap"><div class="bar-chart"><div class="bar-row"><span>Allocated</span><div class="bar-track"><i style="width:73%"></i></div><b>183</b></div><div class="bar-row"><span>Available</span><div class="bar-track"><i style="width:27%"></i></div><b>67</b></div></div></div></article><article class="boundary-panel">${parcelSvg()}<div class="boundary-top"><span>Estate parcel map · demonstration</span><span>N ↑</span></div><div class="boundary-legend"><span>Selected parcel: A-003</span><span>Open map integration required</span></div></article></section>`,
    "Estates",
  );
}
function parcelsPage() {
  return adminLayout(
    `<div class="page-head"><div><p class="eyebrow">Parcel management</p><h1>Parcels</h1><p>Review parcel details, survey boundaries and allocation readiness.</p></div>${button("Allocate property", "open-allocation", "primary")}</div><div class="filters"><input id="parcel-search" aria-label="Search parcels" placeholder="Search plot, block or assigned person"><select id="parcel-status" aria-label="Filter parcel status"><option value="All">All statuses</option><option>Available</option><option>Allocated</option><option>Pending</option></select></div><section class="panel"><div class="panel-head"><div><h2>Parcel records</h2><p>Click a record to inspect its boundary detail.</p></div><span class="muted">${data.parcels.length} demonstration records</span></div>${parcelTable(data.parcels)}</section>`,
    "Parcels",
  );
}
function allocationsPage() {
  return adminLayout(
    `<div class="page-head"><div><p class="eyebrow">Allocation management</p><h1>Allocations</h1><p>Track approved parcel assignments and their invitation progress.</p></div>${button("Start allocation", "open-allocation", "primary")}</div><section class="panel"><div class="table-wrap"><table class="data-table"><thead><tr><th>Reference</th><th>Property</th><th>Allottee</th><th>Email</th><th>Allocation date</th><th>Status</th></tr></thead><tbody><tr><td><span class="table-title">ALC-AG-2026-0183</span></td><td>Abeni Gardens · A-001</td><td>Chiamaka Okoro</td><td>chiamaka.okoro@example.com</td><td>12 Sep 2026</td><td>${status("Accepted")}</td></tr><tr><td><span class="table-title">ALC-AG-2026-0184</span></td><td>Abeni Gardens · A-002</td><td>Tunde Adebayo</td><td>tunde.adebayo@example.com</td><td>20 Sep 2026</td><td>${status("Accepted")}</td></tr><tr><td><span class="table-title">ALC-AG-2026-0185</span></td><td>Abeni Gardens · A-004</td><td>Ngozi Eze</td><td>ngozi.eze@example.com</td><td>06 Oct 2026</td><td>${status("Pending")}</td></tr></tbody></table></div></section>`,
    "Allocations",
  );
}
function invitationsPage() {
  return adminLayout(
    `<div class="page-head"><div><p class="eyebrow">Invitation management</p><h1>Invitations</h1><p>Invitation status is simulated locally in this frontend demonstration.</p></div>${button("Send invitation", "open-allocation", "primary")}</div><section class="panel"><div class="panel-head"><div><h2>Allocation invitations</h2><p>Linked to a specific recipient and allocated property.</p></div><span class="demo-badge">No email service connected</span></div><div class="table-wrap"><table class="data-table"><thead><tr><th>Recipient</th><th>Property</th><th>Sent</th><th>Expires</th><th>Status</th><th></th></tr></thead><tbody>${data.invitations.map((i) => `<tr><td><span class="table-title">${i.recipient}</span><span class="subcell">${i.email}</span></td><td>Abeni Gardens · ${i.parcel}</td><td>${i.sent}</td><td>${i.expiry}</td><td>${status(i.status)}</td><td>${i.status === "Pending" ? button("Resend demo", "toast:Demo invitation queued locally.", "secondary", "small") : ""}</td></tr>`).join("")}</tbody></table></div></section>`,
    "Invitations",
  );
}
function surveyPage() {
  return adminLayout(
    `<div class="page-head"><div><p class="eyebrow">Survey data</p><h1>Survey imports</h1><p>Review demonstration import states before releasing parcel records.</p></div>${button("Import survey data", "toast:File processing needs a backend integration.", "primary")}</div><section class="two-column"><article class="form-card"><h2>Import survey file</h2><p>Frontend capability preview only. No file will be uploaded or processed.</p><div class="upload-box"><div><strong>Drop a survey file here</strong><span>Intended formats: PDF, DXF, CSV and GeoJSON</span><div style="margin-top:14px">${button("Choose a file", "toast:File import is unavailable in this frontend demonstration.", "secondary", "small")}</div></div></div></article><article class="form-card"><h2>Last reviewed import</h2><p>A clearly labeled demonstration dataset.</p><div class="survey-stats"><div><span>Parcels found</span><strong>24</strong></div><div><span>Geometry valid</span><strong>23</strong></div><div><span>Warnings</span><strong>1</strong></div></div><div class="notice">Warning: Parcel C-014 has an unclosed geometry and needs survey review before it can be allocated.</div></article></section><section class="panel" style="margin-top:17px"><div class="panel-head"><div><h2>Import history</h2><p>Illustrative only — no survey files have been processed.</p></div></div><div class="table-wrap"><table class="data-table"><thead><tr><th>File</th><th>Estate</th><th>Imported</th><th>Records</th><th>Status</th></tr></thead><tbody><tr><td><span class="table-title">abeni-gardens-block-a.dxf</span><span class="subcell">Demonstration data</span></td><td>Abeni Gardens</td><td>06 Oct 2026</td><td>24</td><td>${status("Processing")}</td></tr><tr><td><span class="table-title">abeni-gardens-overview.csv</span><span class="subcell">Demonstration data</span></td><td>Abeni Gardens</td><td>21 Sep 2026</td><td>250</td><td>${status("Active")}</td></tr></tbody></table></div></section>`,
    "Survey data",
  );
}
function activityPage() {
  return adminLayout(
    `<div class="page-head"><div><p class="eyebrow">Audit view</p><h1>Activity logs</h1><p>Sample audit events for the frontend experience.</p></div></div><section class="panel"><div class="activity">${[
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
    ]
      .map(
        (x) =>
          `<div class="activity-row"><i class="activity-dot"></i><div><strong>${x[0]}</strong><span>${x[1]}</span></div><time>${x[2]}</time></div>`,
      )
      .join("")}</div></section>`,
    "Activity logs",
  );
}
function settingsPage() {
  return adminLayout(
    `<div class="page-head"><div><p class="eyebrow">Workspace preferences</p><h1>Settings</h1><p>These controls are visual only and are not persisted.</p></div></div><section class="two-column"><article class="form-card"><h2>Organization profile</h2><div class="form-grid"><div class="field"><label>Organization name</label><input value="Abeni Estate Development Ltd."></div><div class="field"><label>Support email</label><input value="records@abeni.example"></div><div class="field full"><label>Estate address</label><input value="Ibeju-Lekki, Lagos State"></div></div><div class="form-actions">${button("Save changes", "toast:Settings are not saved in this frontend demonstration.", "primary")}</div></article><article class="form-card"><h2>Access policy</h2><p>Backend authorization must enforce access policy on every protected request.</p><div class="notice">This interface can demonstrate navigation only. Authentication, roles and invitations need secure server-side implementation.</div></article></section>`,
    "Settings",
  );
}

function adminView() {
  const pages = {
    overview: adminOverview,
    estates: estatesPage,
    parcels: parcelsPage,
    allocations: allocationsPage,
    invitations: invitationsPage,
    survey: surveyPage,
    activity: activityPage,
    settings: settingsPage,
  };
  return pages[state.adminPage]();
}
function invitationView() {
  return `<main class="invite-page"><section class="invite-card"><div class="invite-banner"><a class="brand" href="#home">${brand()}</a><p>You have been invited to view a property record in Abeni Gardens Estate.</p></div><div class="invite-body"><p class="eyebrow">Invitation preview · frontend demonstration</p><h1>Review your property invitation</h1><p class="muted">This sample invitation is linked to the intended recipient, Chiamaka Okoro.</p><div class="property-chip"><div><strong>Plot A-001 · Block A</strong><span>Abeni Gardens Estate, Ibeju-Lekki, Lagos</span></div>${status("Pending")}</div><div class="notice">This is a simulated invitation. A production application must validate invitation tokens and identity on the backend.</div><div class="form-actions">${button("I already have an account", "user", "secondary")}${button("Accept invitation", "user", "primary")}</div><p class="muted" style="font-size:11px;margin:17px 0 0">Expired, invalid and already accepted states are represented in the administrator invitation table.</p></div></section></main>`;
}
function userView() {
  return `<div class="app-shell"><aside class="sidebar"><a class="brand" href="#user">${brand()}</a><p class="sidebar-label">My property</p><nav class="side-nav"><button class="${state.userPage === "property" ? "active" : ""}" data-action="user-page:property"><span class="nav-icon">⌂</span><span>My property</span></button><button class="${state.userPage === "documents" ? "active" : ""}" data-action="user-page:documents"><span class="nav-icon">▤</span><span>Documents</span></button><button class="${state.userPage === "allocation" ? "active" : ""}" data-action="user-page:allocation"><span class="nav-icon">↗</span><span>Allocation details</span></button><button class="${state.userPage === "settings" ? "active" : ""}" data-action="user-page:settings"><span class="nav-icon">⚙</span><span>Account settings</span></button></nav></aside><section class="main-area"><header class="app-header"><div class="breadcrumb">My property / <strong>${state.userPage === "property" ? "Abeni Gardens Estate" : "Account"}</strong></div><div class="header-tools"><span class="demo-badge">Simulated record</span>${button("Public site", "public", "ghost", "small")}<div class="profile"><div class="profile-avatar">CO</div><span>Chiamaka Okoro</span></div></div></header><main class="page">${userPage()}</main></section></div>`;
}
function userPage() {
  if (state.userPage === "documents")
    return `<div class="page-head"><div><p class="eyebrow">Approved documents</p><h1>Property documents</h1><p>Sample document references only — no files are connected.</p></div></div><section class="panel"><div class="document-list" style="padding:17px"><article class="document"><div><strong>Survey plan · SP/AG/2026/014</strong><span>Sample approved document reference</span></div>${status("Active")}</article><article class="document"><div><strong>Allocation letter · ALC-AG-2026-0183</strong><span>Sample document reference</span></div>${status("Active")}</article><div class="empty">No other approved documents are available in this demonstration.</div></div></section>`;
  if (state.userPage === "allocation")
    return `<div class="page-head"><div><p class="eyebrow">Allocation information</p><h1>Allocation details</h1><p>Details issued by Abeni Estate Development Ltd.</p></div></div><section class="two-column"><article class="panel"><div class="panel-head"><h2>Allocation record</h2></div><div class="detail-list"><div><span>Allocation reference</span><strong>ALC-AG-2026-0183</strong></div><div><span>Estate</span><strong>Abeni Gardens Estate</strong></div><div><span>Plot & block</span><strong>A-001 · Block A</strong></div><div><span>Allocation date</span><strong>12 Sep 2026</strong></div><div><span>Status</span>${status("Allocated")}</div></div></article><article class="panel"><div class="panel-head"><h2>Responsible organization</h2></div><div class="detail-list"><div><span>Organization</span><strong>Abeni Estate Development Ltd.</strong></div><div><span>Record state</span><strong>Approved sample record</strong></div><div><span>Location</span><strong>Ibeju-Lekki, Lagos</strong></div></div></article></section>`;
  if (state.userPage === "settings")
    return `<div class="page-head"><div><p class="eyebrow">Account</p><h1>Account settings</h1><p>Visual-only profile controls.</p></div></div><article class="form-card"><div class="form-grid"><div class="field"><label>Full name</label><input value="Chiamaka Okoro"></div><div class="field"><label>Email</label><input value="chiamaka.okoro@example.com"></div></div><div class="form-actions">${button("Save demonstration", "toast:Account settings are not persisted.", "primary")}</div></article>`;
  return propertyPage();
}
function propertyPage() {
  return `<div class="property-hero"><div><p class="eyebrow" style="color:#b9e46a">Abeni Gardens Estate · Ibeju-Lekki</p><h1>Plot A-001, Block A</h1><p>Approved allocation and survey record</p></div>${button("Locate My Land", "user-page:locate", "secondary")}</div>${state.userPage === "locate" ? locatePage() : `<div class="property-metrics"><div><span>Allocation reference</span><strong>ALC-AG-2026-0183</strong></div><div><span>Land area</span><strong>612 m²</strong></div><div><span>Perimeter</span><strong>103.74 m</strong></div><div><span>Allocation status</span>${status("Allocated")}</div></div><div class="tabs" style="margin-top:18px">${["overview", "boundary", "survey", "allocation"].map((x) => `<button class="${state.propertyTab === x ? "active" : ""}" data-action="property-tab:${x}">${x === "overview" ? "Overview" : x === "boundary" ? "Boundary details" : x === "survey" ? "Survey information" : "Allocation information"}</button>`).join("")}</div><div class="tab-content">${propertyTab()}</div>`}`;
}
function propertyTab() {
  if (state.propertyTab === "boundary")
    return `<section class="parcel-layout"><article class="boundary-panel">${parcelSvg()}<div class="boundary-top"><span>Approved parcel boundary · sample</span><span>N ↑</span></div><div class="boundary-legend"><span>B1–B5 recorded beacons</span><span>Boundary source: survey plan</span></div></article><aside class="panel"><div class="panel-head"><h2>Boundary summary</h2></div><div class="detail-list"><div><span>Area</span><strong>612 m²</strong></div><div><span>Perimeter</span><strong>103.74 m</strong></div><div><span>Beacons</span><strong>5 points</strong></div><div><span>Adjoining plot</span><strong>Plot A-002</strong></div></div></aside></section><section class="panel" style="margin-top:17px"><div class="panel-head"><h2>Beacon coordinates</h2></div><div class="table-wrap"><table class="data-table"><thead><tr><th>Beacon</th><th>Easting</th><th>Northing</th><th>Next segment</th></tr></thead><tbody>${[
      ["B1", "587948.068", "715353.886", "42.73 m"],
      ["B2", "587997.214", "715360.421", "31.84 m"],
      ["B3", "588001.842", "715318.170", "39.17 m"],
      ["B4", "587951.320", "715312.540", "30.25 m"],
      ["B5", "587935.842", "715332.170", "—"],
    ]
      .map(
        (x) =>
          `<tr><td>${x[0]}</td><td>${x[1]}</td><td>${x[2]}</td><td>${x[3]}</td></tr>`,
      )
      .join("")}</tbody></table></div></section>`;
  if (state.propertyTab === "survey")
    return `<section class="two-column"><article class="panel"><div class="panel-head"><h2>Survey record</h2></div><div class="detail-list"><div><span>Survey plan</span><strong>SP/AG/2026/014</strong></div><div><span>Survey date</span><strong>18 Aug 2026</strong></div><div><span>Surveyor</span><strong>O. B. Adetayo (SURV. 4217)</strong></div><div><span>Datum</span><strong>Minna datum</strong></div></div></article><article class="panel"><div class="panel-head"><h2>Coordinate system</h2></div><div class="detail-list"><div><span>CRS</span><strong>UTM Zone 31N</strong></div><div><span>Projection</span><strong>Transverse Mercator</strong></div><div><span>Units</span><strong>Metres</strong></div><div><span>Validation</span>${status("Active")}</div></div></article></section>`;
  if (state.propertyTab === "allocation")
    return `<section class="panel"><div class="panel-head"><h2>Allocation record</h2></div><div class="detail-list"><div><span>Allocation reference</span><strong>ALC-AG-2026-0183</strong></div><div><span>Allocated to</span><strong>Chiamaka Okoro</strong></div><div><span>Estate</span><strong>Abeni Gardens Estate</strong></div><div><span>Allocation status</span>${status("Allocated")}</div></div></section>`;
  return `<section class="parcel-layout"><article class="boundary-panel">${parcelSvg()}<div class="boundary-top"><span>Approved surveyed boundary · sample record</span><span>N ↑</span></div><div class="boundary-legend"><span>Plot A-001</span><span>5 recorded beacons</span></div></article><aside class="panel"><div class="panel-head"><h2>Property record</h2></div><div class="detail-list"><div><span>Estate</span><strong>Abeni Gardens Estate</strong></div><div><span>Location</span><strong>Ibeju-Lekki, Lagos</strong></div><div><span>Survey plan</span><strong>SP/AG/2026/014</strong></div><div><span>Record status</span>${status("Active")}</div></div></aside></section>`;
}
function locatePage() {
  return `<div class="page-head"><div><p class="eyebrow">Location verification</p><h1>Locate My Land</h1><p>This is a simulated positioning experience. No device location or mapping service is connected.</p></div>${button("Back to property", "user-page:property", "secondary")}</div><div class="locate-status"><article class="boundary-panel">${parcelSvg()}<div class="boundary-top"><span>Simulated parcel boundary</span><span>N ↑</span></div><div class="boundary-legend"><span>Sample position shown near B3</span><span>Mapping integration required</span></div></article><aside class="form-card"><h2>Simulated position result</h2><p>For design demonstration only — this is not a live GPS result.</p><div class="detail-list"><div><span>Boundary result</span><strong style="color:#08705a">Inside parcel</strong></div><div><span>Nearest segment</span><strong>B2 → B3</strong></div><div><span>Distance to boundary</span><strong>14.6 m</strong></div><div><span>Nearest beacon</span><strong>B3</strong></div><div><span>Position uncertainty</span><strong>Not available</strong></div></div><p class="simulated">A backend, mapping provider, device permission flow and validated positioning service are required before displaying a real location result.</p>${button("Simulate permission prompt", "toast:Location permission is not requested in this frontend demonstration.", "secondary")}</aside></div>`;
}
function allocationModal() {
  const p = state.selectedParcel;
  let body = "";
  if (state.allocationStep === 1)
    body = `<p>Select an available parcel for this allocation.</p><div class="form-grid">${data.parcels
      .filter((x) => x.status === "Available")
      .map(
        (x) =>
          `<button class="button ${p.plot === x.plot ? "primary" : "secondary"}" data-action="select-parcel:${x.plot}">${x.plot} · ${x.area}</button>`,
      )
      .join("")}</div>`;
  if (state.allocationStep === 2)
    body = `<p>Enter the intended allottee details. These values stay in the browser and are not sent anywhere.</p><div class="form-grid"><div class="field"><label>Full name</label><input id="allottee-name" placeholder="e.g. Adewale Bello"></div><div class="field"><label>Email address</label><input id="allottee-email" type="email" placeholder="name@example.com"></div><div class="field full"><label>Phone number (optional)</label><input placeholder="+234 …"></div></div>`;
  if (state.allocationStep === 3)
    body = `<p>Review the property and recipient information before creating a demonstration invitation.</p><div class="review-card"><strong>${p.plot} · Block ${p.block} · Abeni Gardens Estate</strong><span>${p.area} · Currently available</span></div><div class="review-card"><strong>Recipient details</strong><span>Captured only in this browser for a frontend demonstration.</span></div>`;
  if (state.allocationStep === 4)
    body = `<div class="review-card"><strong>Ready to demonstrate allocation</strong><span>A local status change will be shown. No allocation is written to a database and no email is sent.</span></div><div class="notice">In production, this final step requires authorized backend validation, persistence and a secure invitation delivery service.</div>`;
  return `<div class="modal-backdrop"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="allocation-title"><header class="modal-header"><div><p class="eyebrow">Allocation workflow</p><h2 id="allocation-title">Allocate a property</h2></div><button class="close" aria-label="Close allocation workflow" data-action="close-modal">×</button></header><div class="progress">${["Parcel", "Recipient", "Review", "Confirm"].map((x, i) => `<div data-step="${i + 1}" class="${state.allocationStep === i + 1 ? "active" : ""}">${x}</div>`).join("")}</div>${body}<div class="form-actions">${state.allocationStep > 1 ? button("Back", "allocation-back", "secondary") : button("Cancel", "close-modal", "secondary")}${state.allocationStep < 4 ? button("Continue", "allocation-next", "primary") : button("Confirm demonstration", "allocation-confirm", "primary")}</div></section></div>`;
}
function parcelModal() {
  const p = state.selectedParcel;
  return `<div class="modal-backdrop"><section class="modal" role="dialog" aria-modal="true"><header class="modal-header"><div><p class="eyebrow">Parcel detail</p><h2>Plot ${p.plot}, Block ${p.block}</h2><p>Abeni Gardens Estate · ${p.area}</p></div><button class="close" aria-label="Close parcel details" data-action="close-modal">×</button></header><section class="boundary-panel" style="min-height:270px">${parcelSvg()}<div class="boundary-top"><span>Example surveyed boundary</span><span>N ↑</span></div></section><section class="two-column" style="margin-top:17px"><article class="panel"><div class="detail-list"><div><span>Status</span>${status(p.status)}</div><div><span>Assigned person</span><strong>${p.person}</strong></div><div><span>Survey plan</span><strong>SP/AG/2026/014</strong></div></div></article><article class="panel"><div class="detail-list"><div><span>Area</span><strong>${p.area}</strong></div><div><span>Perimeter</span><strong>103.74 m</strong></div><div><span>Geometry</span><strong>Validated sample</strong></div></div></article></section><div class="form-actions">${p.status === "Available" ? button("Allocate property", "open-allocation", "primary") : button("Close", "close-modal", "secondary")}</div></section></div>`;
}
function render() {
  let markup =
    state.view === "public"
      ? publicView()
      : state.view === "admin"
        ? adminView()
        : state.view === "invite"
          ? invitationView()
          : userView();
  if (state.modal === "allocation") markup += allocationModal();
  if (state.modal === "parcel") markup += parcelModal();
  if (state.toast) markup += `<div class="toast">${state.toast}</div>`;
  app.innerHTML = markup;
  bind();
}
function bind() {
  app
    .querySelectorAll("[data-action]")
    .forEach((el) =>
      el.addEventListener("click", () => handle(el.dataset.action)),
    );
  const search = document.querySelector("#parcel-search");
  if (search) search.addEventListener("input", filterParcels);
  const filter = document.querySelector("#parcel-status");
  if (filter) filter.addEventListener("change", filterParcels);
}
function handle(action) {
  const [kind, value] = action.split(":");
  if (action === "public") {
    navigateTo("public");
    return;
  } else if (action === "admin") {
    navigateTo("admin");
    return;
  } else if (action === "invite") {
    navigateTo("property");
    return;
  } else if (action === "user") {
    state.view = "user";
    state.userPage = "property";
  } else if (kind === "admin-page") {
    state.adminPage = value;
    state.view = "admin";
  } else if (kind === "user-page") {
    state.userPage = value;
    state.view = "user";
  } else if (kind === "property-tab") {
    state.propertyTab = value;
  } else if (kind === "parcel") {
    state.selectedParcel = data.parcels.find((p) => p.plot === value);
    state.modal = "parcel";
  } else if (kind === "select-parcel") {
    state.selectedParcel = data.parcels.find((p) => p.plot === value);
  } else if (action === "open-allocation") {
    state.modal = "allocation";
    state.allocationStep = 1;
  } else if (action === "close-modal") {
    state.modal = null;
  } else if (action === "allocation-next") {
    state.allocationStep = Math.min(4, state.allocationStep + 1);
  } else if (action === "allocation-back") {
    state.allocationStep = Math.max(1, state.allocationStep - 1);
  } else if (action === "allocation-confirm") {
    state.modal = null;
    state.toast =
      "Demonstration allocation confirmed locally. No email was sent.";
  } else if (kind === "toast") {
    state.toast = value;
  }
  render();
  if (state.toast)
    setTimeout(() => {
      state.toast = "";
      render();
    }, 2800);
}
function filterParcels() {
  const q = document.querySelector("#parcel-search").value.toLowerCase(),
    s = document.querySelector("#parcel-status").value;
  document.querySelectorAll("[data-selectable]").forEach((row) => {
    const txt = row.textContent.toLowerCase();
    const match =
      txt.includes(q) && (s === "All" || txt.includes(s.toLowerCase()));
    row.style.display = match ? "" : "none";
  });
}
render();
