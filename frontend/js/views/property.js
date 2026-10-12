import { state } from "../data.js";
import { brand, button, parcelSvg, status } from "../components.js";

export function invitationView() {
  /* HTML */
  return /* HTML */ `<main class="invite-page">
    <section class="invite-card">
      <div class="invite-banner">
        <a class="brand" href="#home">${brand()}</a>
        <p>
          You have been invited to view a property record in Abeni Gardens
          Estate.
        </p>
      </div>
      <div class="invite-body">
        <p class="eyebrow">Invitation preview · frontend demonstration</p>
        <h1>Review your property invitation</h1>
        <p class="muted">
          This sample invitation is linked to the intended recipient, Chiamaka
          Okoro.
        </p>
        <div class="property-chip">
          <div>
            <strong>Plot A-001 · Block A</strong
            ><span>Abeni Gardens Estate, Ibeju-Lekki, Lagos</span>
          </div>
          ${status("Pending")}
        </div>
        <div class="notice">
          This is a simulated invitation. A production application must validate
          invitation tokens and identity on the backend.
        </div>
        <div class="form-actions">
          ${button("I already have an account", "user", "secondary")}${button("Accept invitation", "user", "primary")}
        </div>
        <p class="muted" style="font-size:11px;margin:17px 0 0">
          Expired, invalid and already accepted states are represented in the
          administrator invitation table.
        </p>
      </div>
    </section>
  </main>`;
}

export function userView() {
  return /* HTML */ `<div class="app-shell">
    <aside class="sidebar">
      <a class="brand" href="#user">${brand()}</a>
      <p class="sidebar-label">My property</p>
      <nav class="side-nav">
        <button
          class="${state.userPage === "property" ? "active" : ""}"
          data-action="user-page:property"
        >
          <span class="nav-icon">⌂</span><span>My property</span></button
        ><button
          class="${state.userPage === "documents" ? "active" : ""}"
          data-action="user-page:documents"
        >
          <span class="nav-icon">▤</span><span>Documents</span></button
        ><button
          class="${state.userPage === "allocation" ? "active" : ""}"
          data-action="user-page:allocation"
        >
          <span class="nav-icon">↗</span><span>Allocation details</span></button
        ><button
          class="${state.userPage === "settings" ? "active" : ""}"
          data-action="user-page:settings"
        >
          <span class="nav-icon">⚙</span><span>Account settings</span>
        </button>
      </nav>
    </aside>
    <section class="main-area">
      <header class="app-header">
        <div class="breadcrumb">
          My property /
          <strong
            >${state.userPage === "property" ? "Abeni Gardens Estate" : "Account"}</strong
          >
        </div>
        <div class="header-tools">
          <span class="demo-badge">Simulated record</span
          >${button("Public site", "public", "ghost", "small")}
          <div class="profile">
            <div class="profile-avatar">CO</div>
            <span>Chiamaka Okoro</span>
          </div>
        </div>
      </header>
      <main class="page">${userPage()}</main>
    </section>
  </div>`;
}

function userPage() {
  if (state.userPage === "documents")
    return /* HTML */ `<div class="page-head">
        <div>
          <p class="eyebrow">Approved documents</p>
          <h1>Property documents</h1>
          <p>Sample document references only — no files are connected.</p>
        </div>
      </div>
      <section class="panel">
        <div class="document-list" style="padding:17px">
          <article class="document">
            <div>
              <strong>Survey plan · SP/AG/2026/014</strong
              ><span>Sample approved document reference</span>
            </div>
            ${status("Active")}
          </article>
          <article class="document">
            <div>
              <strong>Allocation letter · ALC-AG-2026-0183</strong
              ><span>Sample document reference</span>
            </div>
            ${status("Active")}
          </article>
          <div class="empty">
            No other approved documents are available in this demonstration.
          </div>
        </div>
      </section>`;
  if (state.userPage === "allocation")
    return /* HTML */ `<div class="page-head">
        <div>
          <p class="eyebrow">Allocation information</p>
          <h1>Allocation details</h1>
          <p>Details issued by Abeni Estate Development Ltd.</p>
        </div>
      </div>
      <section class="two-column">
        <article class="panel">
          <div class="panel-head"><h2>Allocation record</h2></div>
          <div class="detail-list">
            <div>
              <span>Allocation reference</span><strong>ALC-AG-2026-0183</strong>
            </div>
            <div><span>Estate</span><strong>Abeni Gardens Estate</strong></div>
            <div><span>Plot & block</span><strong>A-001 · Block A</strong></div>
            <div><span>Allocation date</span><strong>12 Sep 2026</strong></div>
            <div><span>Status</span>${status("Allocated")}</div>
          </div>
        </article>
        <article class="panel">
          <div class="panel-head"><h2>Responsible organization</h2></div>
          <div class="detail-list">
            <div>
              <span>Organization</span
              ><strong>Abeni Estate Development Ltd.</strong>
            </div>
            <div>
              <span>Record state</span><strong>Approved sample record</strong>
            </div>
            <div><span>Location</span><strong>Ibeju-Lekki, Lagos</strong></div>
          </div>
        </article>
      </section>`;
  if (state.userPage === "settings")
    return /* HTML */ `<div class="page-head">
        <div>
          <p class="eyebrow">Account</p>
          <h1>Account settings</h1>
          <p>Visual-only profile controls.</p>
        </div>
      </div>
      <article class="form-card">
        <div class="form-grid">
          <div class="field">
            <label>Full name</label><input value="Chiamaka Okoro" />
          </div>
          <div class="field">
            <label>Email</label><input value="chiamaka.okoro@example.com" />
          </div>
        </div>
        <div class="form-actions">
          ${button("Save demonstration", "toast:Account settings are not persisted.", "primary")}
        </div>
      </article>`;
  return propertyPage();
}

function propertyPage() {
  const content =
    state.userPage === "locate" ? locatePage() : propertyDetails();

  return /* HTML */ `<div class="property-hero">
      <div>
        <p class="eyebrow" style="color:#b9e46a">
          Abeni Gardens Estate · Ibeju-Lekki
        </p>
        <h1>Plot A-001, Block A</h1>
        <p>Approved allocation and survey record</p>
      </div>
      ${button("Locate My Land", "user-page:locate", "secondary")}
    </div>
    ${content}`;
}

function propertyDetails() {
  const tabs = [
    ["overview", "Overview"],
    ["boundary", "Boundary details"],
    ["survey", "Survey information"],
    ["allocation", "Allocation information"],
  ];
  const tabButtons = tabs
    .map(
      ([key, label]) =>
        /* HTML */ `<button
          class="${state.propertyTab === key ? "active" : ""}"
          data-action="property-tab:${key}"
        >
          ${label}
        </button>`,
    )
    .join("");

  return /* HTML */ `<div class="property-metrics">
      <div>
        <span>Allocation reference</span><strong>ALC-AG-2026-0183</strong>
      </div>
      <div><span>Land area</span><strong>612 m²</strong></div>
      <div><span>Perimeter</span><strong>103.74 m</strong></div>
      <div><span>Allocation status</span>${status("Allocated")}</div>
    </div>
    <div class="tabs" style="margin-top:18px">${tabButtons}</div>
    <div class="tab-content">${propertyTab()}</div>`;
}

function propertyTab() {
  if (state.propertyTab === "boundary")
    return /* HTML */ `<section class="parcel-layout">
        <article class="boundary-panel">
          ${parcelSvg()}
          <div class="boundary-top">
            <span>Approved parcel boundary · sample</span><span>N ↑</span>
          </div>
          <div class="boundary-legend">
            <span>B1–B5 recorded beacons</span
            ><span>Boundary source: survey plan</span>
          </div>
        </article>
        <aside class="panel">
          <div class="panel-head"><h2>Boundary summary</h2></div>
          <div class="detail-list">
            <div><span>Area</span><strong>612 m²</strong></div>
            <div><span>Perimeter</span><strong>103.74 m</strong></div>
            <div><span>Beacons</span><strong>5 points</strong></div>
            <div><span>Adjoining plot</span><strong>Plot A-002</strong></div>
          </div>
        </aside>
      </section>
      <section class="panel" style="margin-top:17px">
        <div class="panel-head"><h2>Beacon coordinates</h2></div>
        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Beacon</th>
                <th>Easting</th>
                <th>Northing</th>
                <th>Next segment</th>
              </tr>
            </thead>
            <tbody>
              ${[
                ["B1", "587948.068", "715353.886", "42.73 m"],
                ["B2", "587997.214", "715360.421", "31.84 m"],
                ["B3", "588001.842", "715318.170", "39.17 m"],
                ["B4", "587951.320", "715312.540", "30.25 m"],
                ["B5", "587935.842", "715332.170", "—"],
              ]
                .map(
                  (row) =>
                    `<tr><td>${row[0]}</td><td>${row[1]}</td><td>${row[2]}</td><td>${row[3]}</td></tr>`,
                )
                .join("")}
            </tbody>
          </table>
        </div>
      </section>`;
  if (state.propertyTab === "survey")
    return /* HTML */ `<section class="two-column">
      <article class="panel">
        <div class="panel-head"><h2>Survey record</h2></div>
        <div class="detail-list">
          <div><span>Survey plan</span><strong>SP/AG/2026/014</strong></div>
          <div><span>Survey date</span><strong>18 Aug 2026</strong></div>
          <div>
            <span>Surveyor</span><strong>O. B. Adetayo (SURV. 4217)</strong>
          </div>
          <div><span>Datum</span><strong>Minna datum</strong></div>
        </div>
      </article>
      <article class="panel">
        <div class="panel-head"><h2>Coordinate system</h2></div>
        <div class="detail-list">
          <div><span>CRS</span><strong>UTM Zone 31N</strong></div>
          <div><span>Projection</span><strong>Transverse Mercator</strong></div>
          <div><span>Units</span><strong>Metres</strong></div>
          <div><span>Validation</span>${status("Active")}</div>
        </div>
      </article>
    </section>`;
  if (state.propertyTab === "allocation")
    return /* HTML */ `<section class="panel">
      <div class="panel-head"><h2>Allocation record</h2></div>
      <div class="detail-list">
        <div>
          <span>Allocation reference</span><strong>ALC-AG-2026-0183</strong>
        </div>
        <div><span>Allocated to</span><strong>Chiamaka Okoro</strong></div>
        <div><span>Estate</span><strong>Abeni Gardens Estate</strong></div>
        <div><span>Allocation status</span>${status("Allocated")}</div>
      </div>
    </section>`;
  return /* HTML */ `<section class="parcel-layout">
    <article class="boundary-panel">
      ${parcelSvg()}
      <div class="boundary-top">
        <span>Approved surveyed boundary · sample record</span><span>N ↑</span>
      </div>
      <div class="boundary-legend">
        <span>Plot A-001</span><span>5 recorded beacons</span>
      </div>
    </article>
    <aside class="panel">
      <div class="panel-head"><h2>Property record</h2></div>
      <div class="detail-list">
        <div><span>Estate</span><strong>Abeni Gardens Estate</strong></div>
        <div><span>Location</span><strong>Ibeju-Lekki, Lagos</strong></div>
        <div><span>Survey plan</span><strong>SP/AG/2026/014</strong></div>
        <div><span>Record status</span>${status("Active")}</div>
      </div>
    </aside>
  </section>`;
}

function locatePage() {
  return /* HTML */ `<div class="page-head">
      <div>
        <p class="eyebrow">Location verification</p>
        <h1>Locate My Land</h1>
        <p>
          This is a simulated positioning experience. No device location or
          mapping service is connected.
        </p>
      </div>
      ${button("Back to property", "user-page:property", "secondary")}
    </div>
    <div class="locate-status">
      <article class="boundary-panel">
        ${parcelSvg()}
        <div class="boundary-top">
          <span>Simulated parcel boundary</span><span>N ↑</span>
        </div>
        <div class="boundary-legend">
          <span>Sample position shown near B3</span
          ><span>Mapping integration required</span>
        </div>
      </article>
      <aside class="form-card">
        <h2>Simulated position result</h2>
        <p>For design demonstration only — this is not a live GPS result.</p>
        <div class="detail-list">
          <div>
            <span>Boundary result</span
            ><strong style="color:#08705a">Inside parcel</strong>
          </div>
          <div><span>Nearest segment</span><strong>B2 → B3</strong></div>
          <div><span>Distance to boundary</span><strong>14.6 m</strong></div>
          <div><span>Nearest beacon</span><strong>B3</strong></div>
          <div>
            <span>Position uncertainty</span><strong>Not available</strong>
          </div>
        </div>
        <p class="simulated">
          A backend, mapping provider, device permission flow and validated
          positioning service are required before displaying a real location
          result.
        </p>
        ${button("Simulate permission prompt", "toast:Location permission is not requested in this frontend demonstration.", "secondary")}
      </aside>
    </div>`;
}
