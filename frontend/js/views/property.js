import { state } from "../data.js?v=20261106-settings";
import { brand, button, parcelSvg, status, uiIcon } from "../components.js?v=20261026";

const empty = (title, text) => `<section class="panel"><div class="empty"><span class="empty-icon">${uiIcon("records")}</span><h2>${title}</h2><p>${text}</p></div></section>`;
const initials = (name) => name.split(/\s+/).filter(Boolean).map((part) => part[0]).slice(0, 2).join("").toUpperCase();
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({
  "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
})[character]);
const recordsApi = `${window.location.protocol}//${window.location.hostname}:8000/api/records`;

export function invitationView() {
  const allocationInvite = Boolean(state.allocationInvitationToken);
  if (allocationInvite && state.invitationLoading) {
    return `<main class="invite-page"><section class="invite-card"><div class="invite-banner"><a class="brand" href="#home">${brand()}</a><p>Checking your secure allocation invitation.</p></div><div class="invite-body"><p class="eyebrow">Property allocation</p><h1>Verifying invitation…</h1><p class="muted">Please wait while TerraLedger confirms this invitation is ready to use.</p></div></section></main>`;
  }
  if (allocationInvite && state.invitationError) {
    return `<main class="invite-page"><section class="invite-card"><div class="invite-banner"><a class="brand" href="#home">${brand()}</a><p>Secure access to your allocated property.</p></div><div class="invite-body"><p class="eyebrow">Invitation unavailable</p><h1>This invitation can’t be used.</h1><p class="muted">${escapeHtml(state.invitationError)} Contact the company that allocated the property to request a new invitation.</p><div class="form-actions">${button("Return to site", "public", "secondary")}</div></div></section></main>`;
  }
  if (allocationInvite) {
    const invitedEmail = escapeHtml(state.allocationInvitation?.email || "");
    const matchesEmail = state.user
      && state.user.email?.toLowerCase() === state.allocationInvitation?.email?.toLowerCase();
    const actions = state.user
      ? matchesEmail
        ? button("Link allocation to my account", "accept-allocation", "primary")
        : `<p class="auth-error" role="alert">This allocation is tied to a different email address. Sign in with ${invitedEmail} to continue; no property details have been disclosed.</p>${button("Sign out and continue", "allocation-signout", "secondary")}`
      : `${button("I have an account", "invitation-auth:signin", "secondary")}${button("Create my account", "invitation-auth:signup", "primary")}`;
    return `<main class="invite-page"><section class="invite-card"><div class="invite-banner"><a class="brand" href="#home">${brand()}</a><p>Secure access to your allocated property.</p></div><div class="invite-body"><p class="eyebrow">Property allocation</p><h1>Claim your TerraLedger allocation.</h1><p class="muted">This invitation is for <strong>${invitedEmail}</strong>. Register or sign in using this exact email address to securely link the allocation to your account.</p><div class="form-actions">${actions}</div></div></section></main>`;
  }

  const companyAdminInvite = Boolean(state.companyAdminInvitationToken);
  if (state.invitationAccepted) {
    const companyName = state.companyAdminInvitation?.name || "your company";
    return `<main class="invite-page"><section class="invite-card"><div class="invite-banner"><a class="brand" href="#home">${brand()}</a><p>Your Company Admin membership is ready.</p></div><div class="invite-body"><p class="eyebrow">Setup complete</p><h1>Your account is ready.</h1><p class="muted">You now have Company Admin access for <strong>${companyName}</strong>. Your access has been linked to this TerraLedger account.</p><div class="form-actions">${button("Open company workspace", "open-company-workspace", "primary")}</div></div></section></main>`;
  }
  if (companyAdminInvite && state.invitationLoading) {
    return `<main class="invite-page"><section class="invite-card"><div class="invite-banner"><a class="brand" href="#home">${brand()}</a><p>Checking your secure invitation.</p></div><div class="invite-body"><p class="eyebrow">Company Admin invitation</p><h1>Verifying invitation…</h1><p class="muted">Please wait while TerraLedger confirms this invitation is ready to use.</p></div></section></main>`;
  }
  if (companyAdminInvite && state.invitationError) {
    return `<main class="invite-page"><section class="invite-card"><div class="invite-banner"><a class="brand" href="#home">${brand()}</a><p>Company administration access is issued only through a verified Platform Admin invitation.</p></div><div class="invite-body"><p class="eyebrow">Invitation unavailable</p><h1>This invitation can’t be used.</h1><p class="muted">${state.invitationError} Ask your Platform Admin to issue a new Company Admin invitation. No account has been created or changed.</p><div class="form-actions">${button("Return to site", "public", "secondary")}</div></div></section></main>`;
  }
  const companyName = state.companyAdminInvitation?.company?.name || "this company";
  const invitedEmail = state.companyAdminInvitation?.email || "the invited email address";
  return `<main class="invite-page"><section class="invite-card"><div class="invite-banner"><a class="brand" href="#home">${brand()}</a><p>${companyAdminInvite ? "Company administration access is issued only through a verified Platform Admin invitation." : "Property access is issued through a verified administrator invitation."}</p></div><div class="invite-body"><p class="eyebrow">${companyAdminInvite ? "Company Admin invitation" : "Property invitation"}</p><h1>${companyAdminInvite ? `You’re invited to manage ${companyName}.` : "Invitation required"}</h1><p class="muted">${companyAdminInvite ? `This invitation is for ${invitedEmail}. Sign in to that TerraLedger account, or create it now. Your Company Admin membership is granted only when you accept this invitation.` : "Open the secure invitation sent by your estate administrator to connect a property record."}</p><div class="form-actions">${companyAdminInvite ? `${button("I have an account", "invitation-auth:signin", "secondary")}${button("Create my account", "invitation-auth:signup", "primary")}` : button("Sign in", "auth", "primary")}</div></div></section></main>`;
}

function recordPanel(allocation) {
  if (!allocation) return empty("No property record is linked", "When your estate team verifies an allocation, its property record will appear here.");
  const { parcel } = allocation;
  return `<section class="property-record"><div class="property-map"><div class="record-tag">${uiIcon("shield")} Verified allocation</div>${parcelSvg(true)}<div class="map-coordinate">Survey boundary layer</div></div><div class="property-summary"><p class="kicker"><span></span> Your verified record</p><h1>Plot ${parcel.plot_number}</h1><p class="property-location">${parcel.estate.name}${parcel.estate.state ? ` · ${parcel.estate.state}` : ""}</p><div class="property-badge">${status(allocation.status)}</div><div class="record-metrics"><div><span>Allocation reference</span><strong>${allocation.reference}</strong></div><div><span>Land area</span><strong>${parcel.area_sqm ? `${parcel.area_sqm} m²` : "Not recorded"}</strong></div><div><span>Survey reference</span><strong>${parcel.survey_reference || "Not recorded"}</strong></div><div><span>Boundary data</span><strong>${parcel.boundary_coordinates.length ? "Recorded" : "Pending"}</strong></div></div></div></section>`;
}

function propertyDetails(allocation) {
  if (!allocation) return empty("No allocation found", "There is no verified property allocation linked to your account.");
  const { parcel } = allocation;
  const features = Array.isArray(parcel.features) ? parcel.features.join(", ") : parcel.features || "Not recorded";
  const surveyPlans = allocation.survey_plans || [];
  const surveySection = surveyPlans.length
    ? surveyPlans.map((plan) => `<article class="survey-plan-card"><div><strong>${escapeHtml(plan.survey_plan_number || plan.name)}</strong><span>${escapeHtml(plan.surveyor_full_name || "Surveyor not recorded")} · ${escapeHtml(plan.stated_area ? `${plan.stated_area} ${plan.area_unit}` : "Area not recorded")}</span><span>${escapeHtml(plan.verification_status.replaceAll("_", " "))}</span></div>${plan.download_path ? `<div class="form-actions"><a class="button secondary small" href="${recordsApi}/${plan.download_path}/?inline=1" target="_blank" rel="noopener">View PDF</a><a class="button secondary small" href="${recordsApi}/${plan.download_path}/" target="_blank" rel="noopener">Download</a></div>` : ""}</article>`).join("")
    : `<p class="muted">No survey plan has been uploaded for this property yet.</p>`;
  return `<section class="panel"><div class="panel-head"><div><p class="eyebrow">Allocation record</p><h2>Property details</h2></div><button class="text-action" data-action="user-page:properties">← My Properties</button></div><div class="detail-list"><div><span>Company</span><strong>${escapeHtml(parcel.estate.company_name)}</strong></div><div><span>Estate</span><strong>${escapeHtml(parcel.estate.name)}</strong></div><div><span>Location</span><strong>${escapeHtml([parcel.estate.local_government_area, parcel.estate.state].filter(Boolean).join(", ") || "Not recorded")}</strong></div><div><span>Plot</span><strong>${escapeHtml(parcel.plot_number)}${parcel.block ? ` · Block ${escapeHtml(parcel.block)}` : ""}</strong></div><div><span>Plot size</span><strong>${parcel.area_sqm ? `${escapeHtml(parcel.area_sqm)} m²` : "Not recorded"}</strong></div><div><span>Property type</span><strong>${escapeHtml(parcel.property_type || "Not recorded")}</strong></div><div><span>Plot features</span><strong>${escapeHtml(features)}</strong></div><div><span>Allocation date</span><strong>${new Date(allocation.allocated_at).toLocaleDateString()}</strong></div><div><span>Allocation status</span>${status(allocation.status)}</div><div><span>Allocation reference</span><strong>${escapeHtml(allocation.reference)}</strong></div></div><p class="muted">An allocation record does not independently establish legal title to property.</p></section><section class="panel"><div class="panel-head"><div><p class="eyebrow">Property document</p><h2>Survey Plan</h2></div></div><div class="survey-plan-list">${surveySection}</div><p class="muted">Verification is an internal company review and does not constitute legal title or independent government certification.</p></section>`;
}

function propertyList(allocations) {
  if (!allocations.length) return empty("No properties linked yet", "Properties allocated to this email will appear here after you accept their secure invitation.");
  const cards = allocations.map((allocation) => {
    const parcel = allocation.parcel;
    const features = Array.isArray(parcel.features) ? parcel.features.join(", ") : parcel.features || "Not recorded";
    const surveyPlans = allocation.survey_plans || [];
    const surveySection = surveyPlans.length
      ? surveyPlans.map((plan) => `<div class="survey-plan-card"><div><strong>${escapeHtml(plan.survey_plan_number || plan.name)}</strong><span>${escapeHtml(plan.verification_status.replaceAll("_", " "))}</span></div>${plan.download_path ? `<div class="form-actions"><a class="button secondary small" href="${recordsApi}/${plan.download_path}/?inline=1" target="_blank" rel="noopener">View</a><a class="button secondary small" href="${recordsApi}/${plan.download_path}/" target="_blank" rel="noopener">Download</a></div>` : ""}</div>`).join("")
      : `<p class="muted">No survey plan has been uploaded for this property yet.</p>`;
    return `<article class="panel property-card"><div class="panel-head"><div><p class="eyebrow">${escapeHtml(parcel.estate.company_name)}</p><h2>${escapeHtml(parcel.estate.name)}</h2></div>${status(allocation.status)}</div><div class="detail-list"><div><span>Plot</span><strong>${escapeHtml(parcel.plot_number)}${parcel.block ? ` · Block ${escapeHtml(parcel.block)}` : ""}</strong></div><div><span>Plot size</span><strong>${parcel.area_sqm ? `${escapeHtml(parcel.area_sqm)} m²` : "Not recorded"}</strong></div><div><span>Property type</span><strong>${escapeHtml(parcel.property_type || "Not recorded")}</strong></div><div><span>Plot features</span><strong>${escapeHtml(features)}</strong></div><div><span>Allocation date</span><strong>${new Date(allocation.allocated_at).toLocaleDateString()}</strong></div></div><div class="survey-plan-list"><h3>Survey Plan</h3>${surveySection}</div><div class="form-actions">${button("View property details", `property-detail:${allocation.id}`, "secondary")}</div></article>`;
  }).join("");
  return `<section><div class="page-head"><div><p class="eyebrow">Your account</p><h1>My Properties</h1><p>Allocations securely linked to your TerraLedger account.</p></div></div><div class="cards">${cards}</div></section>`;
}

function content(allocation) {
  if (state.userPage === "documents") return empty("No approved documents", "Approved survey plans and property documents will appear here when shared by your estate administrator.");
  if (state.userPage === "allocation") return propertyDetails(allocation);
  if (state.userPage === "settings") return `<section class="panel"><div class="panel-head"><div><p class="eyebrow">Account</p><h2>Your access profile</h2></div></div><div class="detail-list"><div><span>Name</span><strong>${state.user.full_name}</strong></div><div><span>Email</span><strong>${state.user.email}</strong></div><div><span>Access</span><strong>Property-holder record view</strong></div></div></section>`;
  return propertyList(state.propertyAllocations || []);
}

export function userView() {
  const name = state.user?.full_name || "Account";
  const allocation = state.propertyDetail || state.propertyAllocations?.find((item) => item.id === state.selectedAllocationId) || null;
  const nav = [["properties", "estate", "My Properties"], ["documents", "document", "Documents"], ["settings", "settings", "Account"]];
  const heading = state.userPage === "allocation" && allocation
    ? `${escapeHtml(allocation.parcel.estate.name)} · Plot ${escapeHtml(allocation.parcel.plot_number)}`
    : "My Properties";
  return `<div class="app-shell property-shell"><aside class="sidebar"><a class="brand" href="#user">${brand()}</a><p class="sidebar-label">Property holder</p><nav class="side-nav" aria-label="Property navigation">${nav.map(([key, icon, label]) => `<button aria-label="${label}" class="${state.userPage === key || (key === "properties" && state.userPage === "allocation") ? "active" : ""}" data-action="user-page:${key}"><span class="nav-icon">${uiIcon(icon)}</span><span>${label}</span></button>`).join("")}</nav></aside><section class="main-area"><header class="app-header"><div class="breadcrumb">My Properties / <strong>${heading}</strong></div><div class="header-tools"><span class="workspace-status">${uiIcon("shield")} Property access</span><div class="profile"><div class="profile-avatar">${initials(name)}</div><span>${escapeHtml(name)}</span></div>${button("Sign out", "logout", "secondary")}</div></header><main class="page property-page">${content(allocation)}</main></section></div>`;
}
