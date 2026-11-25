import { data, state } from "../data.js?v=20261106-settings";
import { brand, button, status, uiIcon } from "../components.js?v=20261026";

const platformNavigation = [["overview", "dashboard", "Platform overview"], ["companies", "estate", "Companies"], ["audit", "records", "Audit events"], ["settings", "settings", "Platform settings"]];
const companyNavigation = [["overview", "dashboard", "Company overview"], ["estates", "estate", "Estates"], ["parcels", "parcel", "Parcels"], ["allocations", "allocation", "Allocations"], ["settings", "settings", "Company settings"]];
const empty = (title, text) => `<section class="panel"><div class="empty"><span class="empty-icon">${uiIcon("records")}</span><h2>${title}</h2><p>${text}</p></div></section>`;
const table = (headings, rows, message) => rows.length ? `<div class="table-wrap"><table class="data-table"><thead><tr>${headings.map((heading) => `<th>${heading}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>` : `<div class="empty">${message}</div>`;
const statCard = (icon, label, value, note) => `<article class="stat-card"><span>${uiIcon(icon)} ${label}</span><strong>${value ?? 0}</strong><small>${note}</small></article>`;
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[character]);

function accessRequired() {
  return `<main class="access-page"><section class="access-card"><a class="brand" href="../">${brand()}</a><p class="eyebrow">Administrator workspace</p><h1>Administrator access required</h1><p>Sign in with an assigned Platform Admin or Company Admin account.</p>${button("Go to sign in", "auth", "primary")}</section></main>`;
}

function layout(content, title) {
  const platform = state.adminRole === "platform";
  const navigation = platform ? platformNavigation : companyNavigation;
  const workspace = platform ? "Platform Admin" : data.companySummary?.company?.name || "Company Admin";
  const name = state.user?.full_name || "Administrator";
  const companySwitch = !platform && state.user.company_admin_companies.length > 1 ? `<label class="company-switch" for="company-switch">Company<select id="company-switch">${state.user.company_admin_companies.map((company) => `<option value="${company.id}" ${company.id === state.activeCompanyId ? "selected" : ""}>${company.name}</option>`).join("")}</select></label>` : "";
  return `<div class="app-shell"><aside class="sidebar"><a class="brand" href="#admin">${brand()}</a><p class="sidebar-label">${workspace}</p><nav class="side-nav" aria-label="${workspace} navigation">${navigation.map(([key, icon, label]) => `<button aria-label="${label}" class="${state.adminPage === key ? "active" : ""}" data-action="admin-page:${key}"><span class="nav-icon">${uiIcon(icon)}</span><span>${label}</span></button>`).join("")}</nav></aside><section class="main-area"><header class="app-header"><div class="breadcrumb">${workspace} / <strong>${title}</strong></div><div class="header-tools">${companySwitch}<span class="workspace-status">${uiIcon("shield")} ${platform ? "Platform access" : "Company-scoped access"}</span><div class="profile"><div class="profile-avatar">${name.slice(0, 2).toUpperCase()}</div><span>${name}</span></div>${button("Sign out", "logout", "secondary")}</div></header><main class="page">${content}</main></section></div>`;
}

function platformOverview() {
  const summary = data.platformSummary || {};
  return layout(`<div class="dashboard-hero platform-hero"><div><p class="kicker"><span></span> Platform command centre</p><h1>TerraLedger, in view.</h1><p>Monitor the organisations that use your land-record platform without inheriting access to their private workspaces.</p></div><div class="dashboard-seal"><span>${uiIcon("shield")}</span><strong>Platform<br />governance</strong><small>Access separated by design</small></div></div><section class="cards">${statCard("estate", "Companies", summary.companies, "Registered companies")}${statCard("records", "Company admins", summary.company_admins, "Active memberships")}${statCard("parcel", "Parcels", summary.parcels, "Across all companies")}</section><section class="dashboard-note"><span>${uiIcon("shield")}</span><div><strong>Platform role boundary</strong><p>Platform Admin access is for company governance, audit review and global configuration. It does not grant estate or property access.</p></div></section>`, "Platform overview");
}

function companies() {
  const rows = data.companies.map((company) => {
    const administrator = company.administrator_email || company.pending_admin_email || "Not invited";
    const setup = company.setup_status === "complete" ? "Ready" : "Pending setup";
    const action = company.administrator_email ? "—" : button("Invite administrator", `invite-company-admin:${company.id}`, "secondary", "small");
    return `<tr><td><span class="table-title">${company.name}</span><span class="subcell">${company.email}</span></td><td>${administrator}</td><td>${status(setup)}</td><td>${status(company.status)}</td><td>${action}</td></tr>`;
  });
  const dialog = state.modal === "register-company" ? companyRegistrationDialog() : state.modal === "invite-company-admin" ? companyAdminInvitationDialog() : state.modal === "company-admin-invitation-sent" ? companyAdminInvitationSentDialog() : "";
  return layout(`<div class="page-head"><div><p class="eyebrow">Platform administration</p><h1>Companies</h1><p>Create a company record first, then send its first Company Admin a secure, company-specific invitation.</p></div>${button("+ Register company", "register-company", "primary")}</div><section class="workflow-banner"><span>01</span><div><strong>Register company</strong><p>Create the organisation record and contact profile.</p></div><span>02</span><div><strong>Invite Company Admin</strong><p>Assign access only when the recipient accepts.</p></div><span>03</span><div><strong>Setup complete</strong><p>The membership is linked to their existing or new account.</p></div></section><section class="panel">${table(["Company", "Administrator", "Setup", "Status", "Action"], rows, "No companies have been registered.")}</section>${dialog}`, "Companies");
}

function companyRegistrationDialog() {
  return `<div class="modal-backdrop"><section class="modal workflow-modal" role="dialog" aria-modal="true"><header class="modal-header"><div><p class="eyebrow">Step 1 of 2</p><h2>Register company</h2><p>Create the organisation record. This does not grant anyone admin access yet.</p></div><button class="close" aria-label="Close" data-action="close-modal">×</button></header><form id="company-registration-form" class="workflow-form"><label>Company name<input name="name" autocomplete="organization" required placeholder="ABC Properties Ltd." /></label><label>Company email<input name="email" type="email" autocomplete="email" required placeholder="admin@abcproperties.com" /></label><label>Contact person<input name="contact_person" autocomplete="name" required placeholder="John Adebayo" /></label><label>Company phone<input name="phone" type="tel" autocomplete="tel" required placeholder="+234 801 234 5678" /></label><label>Legal name <span class="field-optional">Optional</span><input name="legal_name" autocomplete="organization" placeholder="ABC Properties Limited" /></label><p class="form-error" hidden role="alert"></p><div class="form-actions">${button("Cancel", "close-modal", "secondary")}<button class="button primary" type="submit">Create company</button></div></form></section></div>`;
}

function companyAdminInvitationDialog() {
  const company = data.companies.find((item) => item.id === state.invitationCompanyId);
  if (!company) return "";
  return `<div class="modal-backdrop"><section class="modal workflow-modal" role="dialog" aria-modal="true"><header class="modal-header"><div><p class="eyebrow">Step 2 of 2</p><h2>Invite Company Administrator</h2><p>Send a role-specific invitation for <strong>${company.name}</strong>. The invitee can sign in to an existing account or create one.</p></div><button class="close" aria-label="Close" data-action="close-modal">×</button></header><form id="company-admin-invitation-form" class="workflow-form"><label>Administrator email<input name="email" type="email" autocomplete="email" required value="${company.email || ""}" placeholder="admin@abcproperties.com" /></label><div class="invitation-note">${uiIcon("shield")} This link grants Company Admin membership only after the recipient accepts it. It never creates Platform Admin access.</div><p class="form-error" hidden role="alert"></p><div class="form-actions">${button("Cancel", "close-modal", "secondary")}<button class="button primary" type="submit">Send invitation</button></div></form></section></div>`;
}

function companyAdminInvitationSentDialog() {
  const invitation = state.latestCompanyAdminInvitation;
  if (!invitation?.url) return "";
  const deliveryNote = invitation.emailDeliveryWarning
    ? `<div class="invitation-note">${uiIcon("shield")} ${invitation.emailDeliveryWarning}</div>`
    : `<div class="invitation-note">${uiIcon("shield")} Email delivery was accepted. Keep this link private and do not issue another invitation before it is used.</div>`;
  return `<div class="modal-backdrop"><section class="modal workflow-modal" role="dialog" aria-modal="true"><header class="modal-header"><div><p class="eyebrow">Invitation issued</p><h2>Use this current invitation link</h2><p>Send this link to <strong>${invitation.email}</strong>. Issuing another invitation for this company will immediately invalidate this one.</p></div><button class="close" aria-label="Close" data-action="close-modal">×</button></header><div class="workflow-form"><label>Company Admin invitation link<input value="${invitation.url}" readonly aria-label="Current Company Admin invitation link" /></label>${deliveryNote}<div class="form-actions">${button("Copy link", "copy-company-admin-invitation", "secondary")}${button("Done", "close-modal", "primary")}</div></div></section></div>`;
}

function audit() {
  const rows = data.auditEvents.map((event) => `<tr><td>${event.action}</td><td>${event.actor || "System"}</td><td>${event.company_id || "Platform"}</td><td>${new Date(event.created_at).toLocaleString()}</td></tr>`);
  return layout(`<div class="page-head"><div><p class="eyebrow">Platform administration</p><h1>Audit events</h1><p>Relevant company and platform administrative events.</p></div></div><section class="panel">${table(["Action", "Actor", "Company", "When"], rows, "No administrative events have been recorded.")}</section>`, "Audit events");
}

function platformSettings() {
  const rows = Object.entries(data.settings).map(([key, value]) => `<tr><td>${key}</td><td>${JSON.stringify(value)}</td></tr>`);
  return layout(`<div class="page-head"><div><p class="eyebrow">Platform administration</p><h1>Platform settings</h1><p>These settings affect TerraLedger globally, never a single company.</p></div></div><section class="panel">${table(["Setting", "Value"], rows, "No platform settings have been configured.")}</section>`, "Platform settings");
}

function companyOverview() {
  const summary = data.companySummary || {};
  const company = summary.company || {};
  return layout(`<div class="dashboard-hero company-hero"><div><p class="kicker"><span></span> Company workspace</p><h1>${company.name || "Company workspace"}</h1><p>Your operational view of estates, parcels and allocation activity. Everything here is contained within your organisation.</p></div><div class="mini-parcel"><div class="mini-grid"></div><span>Company record boundary</span></div></div><section class="cards">${statCard("estate", "Estates", summary.estates, `${summary.active_estates ?? 0} active`) }${statCard("parcel", "Parcels", summary.parcels, `${summary.available_parcels ?? 0} available`) }${statCard("allocation", "Allocated", summary.allocated_parcels, "Company parcel allocations")}</section><section class="dashboard-note"><span>${uiIcon("shield")}</span><div><strong>Company-scoped access</strong><p>Only estates, parcels, allocations and settings owned by ${company.name || "this company"} are available in this workspace.</p></div></section>`, "Company overview");
}

function estateFormDialog() {
  const estate = state.editingEstate || {};
  const creating = !estate.id;
  const imageControl = !creating && estate.image
    ? `<div class="estate-image-control"><img src="${escapeHtml(estate.image)}" alt="Current image for ${escapeHtml(estate.name)}" style="width:72px;height:54px;object-fit:cover;border-radius:6px" /><label><input name="remove_image" type="checkbox" value="true" /> Remove this picture</label></div>`
    : "";
  return `<div class="modal-backdrop"><section class="modal workflow-modal" role="dialog" aria-modal="true"><header class="modal-header"><div><p class="eyebrow">Estate management</p><h2>${creating ? "Create estate" : "Edit estate"}</h2><p>${creating ? "Add a new estate to your company. Its ownership is assigned securely by TerraLedger." : "Update this estate’s operational information. It cannot be moved to another company."}</p></div><button class="close" aria-label="Close" data-action="close-modal">×</button></header><form id="estate-form" class="workflow-form"><label>Estate name<input name="name" required maxlength="200" value="${estate.name || ""}" placeholder="Meridian Gardens" /></label><label>Estate address / location<textarea name="address" required rows="2" placeholder="12 Meridian Drive, Lekki">${estate.address || ""}</textarea></label><div class="form-grid"><label>State<input name="state" required maxlength="100" value="${estate.state || ""}" placeholder="Lagos" /></label><label>Local Government Area<input name="local_government_area" required maxlength="100" value="${estate.local_government_area || ""}" placeholder="Eti-Osa" /></label></div><label>Description <span class="field-optional">Optional</span><textarea name="description" rows="3" placeholder="A short description of this development.">${estate.description || ""}</textarea></label><label>Estate image <span class="field-optional">Optional, up to 5 MB</span><input name="image" type="file" accept="image/*" /></label>${imageControl}<p class="form-error" hidden role="alert"></p><div class="form-actions">${button("Cancel", "close-modal", "secondary")}<button class="button primary" type="submit">${creating ? "Create estate" : "Save changes"}</button></div></form></section></div>`;
}

function estates() {
  const overview = data.estateOverview || {};
  const query = state.estateSearch.trim().toLowerCase();
  const records = data.estates.filter((item) => {
    const matchesQuery = !query || [item.name, item.address, item.state, item.local_government_area].join(" ").toLowerCase().includes(query);
    return matchesQuery && (state.estateStatusFilter === "all" || item.status === state.estateStatusFilter);
  });
  const rows = records.map((item) => `<tr><td><button class="table-link" data-action="view-estate:${item.id}"><span class="table-title">${item.name}</span><span class="subcell">${item.address || item.code}</span></button></td><td>${item.local_government_area}, ${item.state}</td><td>${item.parcel_count}<span class="subcell">${item.allocated_parcel_count} allocated</span></td><td>${status(item.status)}</td><td><div class="table-actions">${button("View", `view-estate:${item.id}`, "secondary", "small")}${button("Edit", `edit-estate:${item.id}`, "secondary", "small")}${item.status !== "archived" ? button("Archive", `estate-status:${item.id}:archived`, "secondary", "small") : button("Activate", `estate-status:${item.id}:active`, "secondary", "small")}</div></td></tr>`);
  const emptyMessage = data.estates.length ? "No estates match this search or status filter." : "No company estates have been created.";
  const dialog = state.modal === "estate-form" ? estateFormDialog() : "";
  return layout(`<div class="page-head"><div><p class="eyebrow">Company administration</p><h1>Estates</h1><p>Manage the estates belonging to your company.</p></div>${button("+ Create estate", "create-estate", "primary")}</div><section class="cards estate-stats">${statCard("estate", "Total estates", overview.total_estates, "All company estates")}${statCard("estate", "Active estates", overview.active_estates, "Ready for management")}${statCard("parcel", "Total parcels", overview.total_parcels, "Across all estates")}${statCard("allocation", "Allocated parcels", overview.allocated_parcels, "Assigned plots")}</section><section class="panel"><div class="table-toolbar"><label class="search-field"><span class="sr-only">Search estates</span><input id="estate-search" type="search" value="${state.estateSearch}" placeholder="Search estates" /></label><label class="filter-field">Status<select id="estate-status"><option value="all">All statuses</option>${["active", "inactive", "archived"].map((value) => `<option value="${value}" ${state.estateStatusFilter === value ? "selected" : ""}>${value[0].toUpperCase() + value.slice(1)}</option>`).join("")}</select></label></div>${table(["Estate", "Location", "Parcels", "Status", "Actions"], rows, emptyMessage)}</section>${dialog}`, "Estates");
}

function estateDetail() {
  const estate = data.estateDetail || data.estates.find((item) => item.id === state.selectedEstateId);
  if (!estate) return layout(empty("Estate unavailable", "This estate could not be retrieved from your company records."), "Estate");
  const tab = state.estateDetailTab;
  const estateParcels = data.parcels.filter((parcel) => parcel.estate.id === estate.id);
  const estateAllocations = data.allocations.filter((allocation) => allocation.parcel.estate.id === estate.id);
  const sections = {
    overview: `<section class="detail-list"><div><span>Location</span><strong>${estate.address}</strong></div><div><span>State / LGA</span><strong>${estate.state} · ${estate.local_government_area}</strong></div><div><span>Status</span>${status(estate.status)}</div><div><span>Created</span><strong>${new Date(estate.created_at).toLocaleDateString()}</strong></div><div><span>Last updated</span><strong>${new Date(estate.updated_at).toLocaleDateString()}</strong></div><div><span>Created by</span><strong>${estate.created_by || "Not recorded"}</strong></div><div class="detail-wide"><span>Description</span><strong>${estate.description || "No description recorded."}</strong></div></section>`,
    parcels: table(["Parcel", "Plot", "Type", "Status"], estateParcels.map((parcel) => `<tr><td><strong>${escapeHtml(parcel.name || parcel.plot_number)}</strong>${parcel.plot_details ? `<span class="subcell">${escapeHtml(parcel.plot_details)}</span>` : ""}</td><td>${escapeHtml(parcel.plot_number)}<span class="subcell">${escapeHtml(parcel.block || "No block")}</span></td><td>${escapeHtml(parcel.property_type || "—")}</td><td>${status(parcel.status)}</td></tr>`), "No parcels have been created for this estate."),
    allocations: table(["Reference", "Plot", "Recipient", "Status"], estateAllocations.map((item) => `<tr><td>${escapeHtml(item.reference)}</td><td>${escapeHtml(item.parcel.plot_number)}${item.parcel.block ? `<span class="subcell">Block ${escapeHtml(item.parcel.block)}</span>` : ""}</td><td>${escapeHtml(item.allottee?.full_name || item.recipient_name)}<span class="subcell">${escapeHtml(item.recipient_email)}</span></td><td>${status(item.status)}</td></tr>`), "No parcel allocations have been recorded for this estate."),
  };
  const dialog = state.modal === "estate-form" ? estateFormDialog() : "";
  return layout(`<div class="page-head"><div><button class="text-action" data-action="back-to-estates">← All estates</button><p class="eyebrow">Estate record</p><h1>${estate.name}</h1><p>${estate.address}</p></div><div class="form-actions">${button("Edit estate", `edit-estate:${estate.id}`, "secondary")}${estate.status === "active" ? button("Deactivate", `estate-status:${estate.id}:inactive`, "secondary") : button("Activate", `estate-status:${estate.id}:active`, "secondary")}${estate.status !== "archived" ? button("Archive", `estate-status:${estate.id}:archived`, "primary") : ""}</div></div><section class="cards estate-stats">${statCard("parcel", "Total parcels", estate.parcel_count, "Approved estate parcels")}${statCard("allocation", "Allocated", estate.allocated_parcel_count, "Allocated parcels")}${statCard("parcel", "Available", estate.available_parcel_count, "Available parcels")}</section><section class="panel"><nav class="record-tabs" aria-label="Estate record sections">${[["overview", "Overview"], ["parcels", "Parcels"], ["allocations", "Allocations"]].map(([key, label]) => `<button class="${tab === key ? "active" : ""}" data-action="estate-tab:${key}">${label}</button>`).join("")}</nav><div class="estate-detail-section">${sections[tab]}</div></section>${dialog}`, estate.name);
}

function parcels() {
  const rows = data.parcels.map((item) => `<tr><td>${escapeHtml(item.estate.name)}</td><td><span class="table-title">${escapeHtml(item.name || item.plot_number)}</span><span class="subcell">Plot ${escapeHtml(item.plot_number)}${item.block ? ` · Block ${escapeHtml(item.block)}` : ""}</span></td><td>${escapeHtml(item.property_type || "—")}</td><td>${item.area_sqm ? `${item.area_sqm} m²` : "—"}</td><td>${status(item.status)}</td></tr>`);
  return layout(`<div class="page-head"><div><p class="eyebrow">Company administration</p><h1>Parcels</h1><p>Create the plots you want to allocate. Survey coordinates are added later by the property holder.</p></div>${button("+ Create parcel", "create-parcel", "primary")}</div><section class="panel">${table(["Estate", "Parcel", "Type", "Area", "Status"], rows, "No company parcels have been created.")}</section>`, "Parcels");
}

function allocations() {
  const rows = data.allocations.map((item) => {
    const recipient = escapeHtml(item.allottee?.full_name || item.recipient_name);
    const reference = escapeHtml(item.reference);
    const propertyName = escapeHtml(`${item.parcel.estate.name} · ${item.parcel.plot_number}${item.parcel.block ? ` · Block ${item.parcel.block}` : ""}`);
    const recipientEmail = escapeHtml(item.recipient_email);
    const invitation = item.invitation;
    const delivery = invitation ? status(invitation.status) : "No invitation";
    const resend = item.status !== "revoked"
      ? button("Resend invitation", `resend-allocation:${item.id}`, "secondary", "small")
      : "";
    const revoke = item.status !== "revoked"
      ? button("Revoke", `revoke-allocation:${item.id}`, "danger", "small")
      : "";
    const failure = invitation?.failure_reason
      ? `<span class="subcell">${escapeHtml(invitation.failure_reason)}</span>`
      : "";
    return `<tr><td><span class="table-title">${reference}</span><span class="subcell">${new Date(item.allocated_at).toLocaleDateString()}</span></td><td>${propertyName}</td><td>${recipient}<span class="subcell">${recipientEmail}</span></td><td>${status(item.status)}</td><td>${delivery}${failure}</td><td><div class="form-actions">${resend}${revoke}</div></td></tr>`;
  });
  return layout(`<div class="page-head"><div><p class="eyebrow">Company administration</p><h1>Allocation history</h1><p>Allocations for parcels owned by this company.</p></div><div class="form-actions">${button("Allocate parcel", "create-allocation", "primary")}</div></div><section class="panel">${table(["Reference", "Property", "Recipient", "Allocation", "Invitation delivery", "Actions"], rows, "No company allocations have been created.")}</section>`, "Allocations");
}

function companySettings() {
  const company = data.companySettings;
  if (!company) return layout(empty("Settings unavailable", "Company settings could not be loaded. Refresh and try again."), "Company settings");
  const sections = [
    ["company-information", "Company Information"],
    ["account-settings", "Account Settings"],
    ["notifications", "Notifications"],
    ["company-details", "Company Details"],
  ];
  const navigation = `<nav class="settings-tabs" aria-label="Company settings sections">${sections.map(([key, label]) => `<button type="button" class="${state.settingsSection === key ? "active" : ""}" aria-pressed="${state.settingsSection === key}" data-action="settings-section:${key}">${label}</button>`).join("")}</nav>`;
  let content = "";

  if (state.settingsSection === "company-information") {
    content = `<section class="panel settings-panel"><div class="panel-head"><div><p class="eyebrow">Organisation profile</p><h2>Company Information</h2><p>Update the contact details for this company.</p></div></div><form id="company-info-form" class="workflow-form"><div class="form-grid"><label>Company name<input name="name" required maxlength="200" value="${escapeHtml(company.name)}" /></label><label>Company email<input type="email" value="${escapeHtml(company.email)}" readonly /></label><label>Company phone number<input name="phone" type="tel" maxlength="40" value="${escapeHtml(company.phone)}" /></label><label>RC number<input name="registration_number" maxlength="100" value="${escapeHtml(company.registration_number)}" /></label></div><p class="form-error" hidden role="alert"></p><div class="form-actions"><button class="button primary" type="submit">Save Changes</button></div></form></section>`;
  } else if (state.settingsSection === "account-settings") {
    content = `<section class="panel settings-panel"><div class="panel-head"><div><p class="eyebrow">Your TerraLedger login</p><h2>Account Settings</h2><p>These details apply only to your authenticated account.</p></div></div><form id="account-profile-form" class="workflow-form"><label>Full name<input name="full_name" required maxlength="200" value="${escapeHtml(state.user?.full_name || "")}" autocomplete="name" /></label><p class="form-error" hidden role="alert"></p><div class="form-actions"><button class="button primary" type="submit">Save Name</button></div></form><hr class="settings-divider" /><form id="password-change-form" class="workflow-form"><h3>Change password</h3><div class="form-grid"><label>Current password<input name="current_password" type="password" required autocomplete="current-password" /></label><label>New password<input name="new_password" type="password" required autocomplete="new-password" /></label><label>Confirm new password<input name="confirm_password" type="password" required autocomplete="new-password" /></label></div><p class="form-error" hidden role="alert"></p><div class="form-actions"><button class="button primary" type="submit">Save Password</button></div></form></section>`;
  } else if (state.settingsSection === "notifications") {
    const preferences = data.notificationPreferences || {};
    const notificationOptions = [
      ["property_allocation", "Property allocation notifications", "Get an email when a property is allocated."],
    ];
    content = `<section class="panel settings-panel"><div class="panel-head"><div><p class="eyebrow">Email alerts</p><h2>Notifications</h2><p>Selected alerts are sent to active Company Admin accounts for this company.</p></div></div><form id="notification-settings-form" class="workflow-form">${notificationOptions.map(([key, title, description]) => `<label class="notification-option"><span><strong>${title}</strong><small>${description}</small></span><input type="checkbox" name="${key}" ${preferences[key] ? "checked" : ""} aria-label="${title}" /></label>`).join("")}<p class="muted">Allocation invitations to property recipients are required for claiming an allocation and are not disabled by these admin notification preferences.</p><p class="form-error" hidden role="alert"></p><div class="form-actions"><button class="button primary" type="submit">Save Changes</button></div></form></section>`;
  } else {
    const created = company.created_at ? new Date(company.created_at).toLocaleDateString() : "Not available";
    content = `<section class="panel settings-panel"><div class="panel-head"><div><p class="eyebrow">Read-only record</p><h2>Company Details</h2><p>These values are managed by TerraLedger and cannot be changed here.</p></div></div><div class="detail-list"><div><span>Company ID</span><strong>${escapeHtml(company.id)}</strong></div><div><span>Registration date on TerraLedger</span><strong>${escapeHtml(created)}</strong></div><div><span>Company account status</span>${status(company.status)}</div></div></section>`;
  }
  return layout(`<div class="page-head"><div><p class="eyebrow">Company administration</p><h1>Company settings</h1><p>Manage your organisation profile, your account, and email alerts.</p></div></div>${navigation}${content}`, "Company settings");
}

export function adminView() {
  if (!state.adminAuthorized) return accessRequired();
  if (state.recordsLoading) return layout(empty("Loading dashboard", "Retrieving only the records you are authorized to access."), "Loading");
  const views = state.adminRole === "platform" ? { overview: platformOverview, companies, audit, settings: platformSettings } : { overview: companyOverview, estates, "estate-detail": estateDetail, parcels, allocations, settings: companySettings };
  return (views[state.adminPage] || views.overview)();
}
