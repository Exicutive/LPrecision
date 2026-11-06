import { currentEndpoint, data, state } from "./js/data.js?v=20261106-settings";
import { adminView } from "./js/views/admin.js?v=20261106-settings";
import { authView } from "./js/views/auth.js?v=20261106";
import {
  allocationModal,
  parcelModal,
  surveyPlanDetailsModal,
  surveyPlanUploadModal,
} from "./js/views/modals.js?v=20261106-settings";
import { invitationView, userView } from "./js/views/property.js?v=20261106-settings";
import { publicView } from "./js/views/public.js?v=20261034";

const app = document.querySelector("#app");
const apiBase = `${window.location.protocol}//${window.location.hostname}:8000/api`;
const accountApi = `${apiBase}/accounts`;
const recordsApi = `${apiBase}/records`;

function cookieValue(name) {
  const cookie = document.cookie
    .split("; ")
    .find((entry) => entry.startsWith(`${name}=`));
  return cookie ? decodeURIComponent(cookie.split("=").slice(1).join("=")) : "";
}

async function getCsrfToken() {
  const response = await fetch(`${accountApi}/csrf/`, { credentials: "include" });
  if (!response.ok) throw new Error("Could not initialize secure account access.");
  const token = cookieValue("csrftoken");
  if (!token) throw new Error("Could not read the security token. Refresh and try again.");
  return token;
}

async function accountRequest(path, { method = "GET", payload } = {}) {
  const headers = { Accept: "application/json" };
  if (payload !== undefined) {
    headers["Content-Type"] = "application/json";
    headers["X-CSRFToken"] = await getCsrfToken();
  }

  const response = await fetch(`${accountApi}/${path}/`, {
    method,
    headers,
    credentials: "include",
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(result.detail || "The account request failed.");
    error.status = response.status;
    throw error;
  }
  return result;
}

async function recordsRequest(path, { method = "GET", payload, formData } = {}) {
  const [route, query] = path.split("?", 2);
  const requestUrl = `${recordsApi}/${route.replace(/\/$/, "")}/${query === undefined ? "" : `?${query}`}`;
  const headers = { Accept: "application/json" };
  if (payload !== undefined || formData !== undefined) {
    if (payload !== undefined) headers["Content-Type"] = "application/json";
    headers["X-CSRFToken"] = await getCsrfToken();
  }
  const response = await fetch(requestUrl, {
    method,
    headers,
    credentials: "include",
    body: formData === undefined ? (payload === undefined ? undefined : JSON.stringify(payload)) : formData,
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(result.detail || "Could not load records.");
    error.status = response.status;
    throw error;
  }
  return result;
}

async function loadRecords() {
  state.recordsLoading = true;
  try {
    const [estates, parcels, allocations, property] = await Promise.all([
      recordsRequest("estates"),
      recordsRequest("parcels"),
      recordsRequest("allocations"),
      recordsRequest("my-property"),
    ]);
    data.estates = estates.estates;
    data.parcels = parcels.parcels;
    data.allocations = allocations.allocations;
    state.propertyAllocations = property.allocations || (property.allocation ? [property.allocation] : []);
    state.propertyAllocation = property.allocation;
  } finally {
    state.recordsLoading = false;
  }
}

async function loadCompanyAdminInvitation() {
  if (!state.companyAdminInvitationToken) return;
  state.invitationLoading = true;
  state.invitationError = "";
  try {
    state.companyAdminInvitation = await recordsRequest(
      `company-admin-invitations/status/?token=${encodeURIComponent(state.companyAdminInvitationToken)}`,
    );
  } catch (error) {
    state.invitationError = error.message;
  } finally {
    state.invitationLoading = false;
  }
}

async function loadAllocationInvitation() {
  if (!state.allocationInvitationToken) return;
  state.invitationLoading = true;
  state.invitationError = "";
  try {
    state.allocationInvitation = await recordsRequest(
      `allocation-invitations/status/?token=${encodeURIComponent(state.allocationInvitationToken)}`,
    );
  } catch (error) {
    state.invitationError = error.message;
  } finally {
    state.invitationLoading = false;
  }
}

async function completeCompanyAdminInvitation(payload) {
  const result = await recordsRequest("company-admin-invitations/accept", {
    method: "POST",
    payload: { token: state.companyAdminInvitationToken, ...payload },
  });
  state.user = (await accountRequest("me")).user;
  state.companyAdminInvitation = result.company;
  state.companyAdminInvitationToken = null;
  state.invitationAccepted = true;
  window.history.replaceState({}, "", window.location.pathname);
  state.view = "invite";
  render();
}

async function completeAllocationInvitation(payload = {}) {
  await recordsRequest("allocation-invitations/accept", {
    method: "POST",
    payload: { token: state.allocationInvitationToken, ...payload },
  });
  state.user = (await accountRequest("me")).user;
  state.allocationInvitationToken = null;
  state.invitationError = "";
  state.propertyDetail = null;
  state.selectedAllocationId = null;
  window.history.replaceState({}, "", window.location.pathname);
  await loadRecords();
  state.userPage = "properties";
  state.view = "user";
  state.toast = "Allocation linked to your account.";
  render();
}

async function loadPropertyDetail(allocationId) {
  state.recordsLoading = true;
  try {
    const result = await recordsRequest(`my-property/${allocationId}`);
    state.selectedAllocationId = Number(allocationId);
    state.propertyDetail = result.allocation;
    state.userPage = "allocation";
    state.view = "user";
  } catch (error) {
    state.toast = error.message;
  } finally {
    state.recordsLoading = false;
    render();
  }
}

async function loadAdminRecords(companyId = state.activeCompanyId) {
  state.recordsLoading = true;
  try {
    if (state.user.is_platform_admin) {
      state.adminRole = "platform";
      const [summary, companies, auditEvents, settings] = await Promise.all([
        recordsRequest("platform/dashboard"),
        recordsRequest("platform/companies"),
        recordsRequest("platform/audit-events"),
        recordsRequest("platform/settings"),
      ]);
      data.platformSummary = summary;
      data.companies = companies.companies;
      data.auditEvents = auditEvents.events;
      data.settings = Object.fromEntries(settings.settings.map((item) => [item.key, item.value]));
      return;
    }

    const companies = state.user.company_admin_companies || [];
    const company = companies.find((item) => item.id === Number(companyId)) || companies[0];
    if (!company) throw new Error("No active Company Admin membership was found.");
    state.adminRole = "company";
    state.activeCompanyId = company.id;
    const prefix = `companies/${company.id}`;
    const [summary, estates, estateOverview, parcels, allocations, surveyPlans, settings] = await Promise.all([
      recordsRequest(`${prefix}/dashboard`),
      recordsRequest(`${prefix}/estates`),
      recordsRequest(`${prefix}/estates/overview`),
      recordsRequest(`${prefix}/parcels`),
      recordsRequest(`${prefix}/allocations`),
      recordsRequest(`${prefix}/survey-plans`),
      recordsRequest(`${prefix}/settings`),
    ]);
    data.companySummary = summary;
    data.estates = estates.estates;
    data.estateOverview = estateOverview;
    data.parcels = parcels.parcels;
    data.allocations = allocations.allocations;
    data.surveyPlans = surveyPlans.survey_plans;
    data.surveyPlanSummary = surveyPlans.summary;
    data.settings = settings.settings;
    data.companySettings = settings.company;
    data.notificationPreferences = settings.notification_preferences || {};
  } finally {
    state.recordsLoading = false;
  }
}

async function loadEstateDetail(estateId) {
  state.recordsLoading = true;
  try {
    const result = await recordsRequest(`companies/${state.activeCompanyId}/estates/${estateId}`);
    state.selectedEstateId = Number(estateId);
    data.estateDetail = result.estate;
    state.adminPage = "estate-detail";
  } catch (error) {
    state.toast = error.message;
  } finally {
    state.recordsLoading = false;
    render();
  }
}

async function loadEstateMasterLayouts(estateId = state.selectedEstateId) {
  if (!estateId) return;
  state.recordsLoading = true;
  try {
    const result = await recordsRequest(`companies/${state.activeCompanyId}/estates/${estateId}/master-layouts`);
    data.masterLayouts = result.master_layouts;
  } catch (error) {
    state.toast = error.message;
  } finally {
    state.recordsLoading = false;
    render();
  }
}

async function loadMasterLayoutReview(layoutId) {
  state.recordsLoading = true;
  try {
    const [detail, candidates] = await Promise.all([
      recordsRequest(`companies/${state.activeCompanyId}/master-layouts/${layoutId}`),
      recordsRequest(`companies/${state.activeCompanyId}/master-layouts/${layoutId}/candidates`),
    ]);
    data.masterLayoutDetail = detail.master_layout;
    data.extractionCandidates = candidates.candidates;
    state.selectedCandidateIds = [];
    state.modal = "master-layout-review";
  } catch (error) {
    state.toast = error.message;
  } finally {
    state.recordsLoading = false;
    render();
  }
}

async function submitMasterLayout(form) {
  const errorMessage = form.querySelector(".form-error");
  const submitButton = form.querySelector('[type="submit"]');
  const formData = new FormData(form);
  if (!formData.get("document")?.size) {
    errorMessage.textContent = "Choose a GeoJSON, DXF, or Shapefile ZIP layout first.";
    errorMessage.hidden = false;
    return;
  }
  errorMessage.hidden = true;
  submitButton.disabled = true;
  try {
    const result = await recordsRequest(
      `companies/${state.activeCompanyId}/estates/${state.selectedEstateId}/master-layouts`,
      { method: "POST", formData },
    );
    state.modal = null;
    state.masterLayoutFileName = "";
    state.toast = result.job?.stage || "Master layout uploaded and queued.";
    await loadEstateMasterLayouts();
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
    if (submitButton.isConnected) submitButton.disabled = false;
  }
}

async function processMasterLayout(layoutId) {
  try {
    const result = await recordsRequest(`companies/${state.activeCompanyId}/master-layouts/${layoutId}/process`, {
      method: "POST", payload: {},
    });
    state.toast = result.job?.stage || "Master layout processing updated.";
    await loadEstateMasterLayouts();
  } catch (error) {
    state.toast = error.message;
    render();
  }
}

async function reviewMasterLayoutCandidates(layoutId, decision) {
  if (decision === "reject" && !state.selectedCandidateIds.length) {
    state.toast = "Select one or more extraction candidates to reject.";
    render();
    return;
  }
  try {
    const candidateIds = decision === "approve"
      ? state.selectedCandidateIds.filter((id) => data.extractionCandidates.some((candidate) => candidate.id === id && candidate.status === "validated"))
      : state.selectedCandidateIds;
    const result = await recordsRequest(`companies/${state.activeCompanyId}/master-layouts/${layoutId}/${decision}-candidates`, {
      method: "POST", payload: candidateIds.length ? { candidate_ids: candidateIds } : {},
    });
    state.toast = decision === "approve"
      ? `${result.published_count} validated parcel${result.published_count === 1 ? "" : "s"} approved.`
      : `${result.rejected_count} candidate${result.rejected_count === 1 ? "" : "s"} rejected.`;
    await loadMasterLayoutReview(layoutId);
    await loadEstateMasterLayouts();
    await loadAdminRecords();
  } catch (error) {
    state.toast = error.message;
    render();
  }
}

async function submitEstate(form) {
  const errorMessage = form.querySelector(".form-error");
  const submitButton = form.querySelector('[type="submit"]');
  const formData = new FormData(form);
  const image = formData.get("image");
  errorMessage.hidden = true;
  submitButton.disabled = true;
  try {
    const estateId = state.editingEstate?.id;
    const result = await recordsRequest(
      estateId ? `companies/${state.activeCompanyId}/estates/${estateId}` : `companies/${state.activeCompanyId}/estates`,
      image?.size
        ? { method: "POST", formData }
        : {
            method: estateId ? "PATCH" : "POST",
            payload: Object.fromEntries([...formData.entries()].filter(([key]) => key !== "image")),
          },
    );
    state.modal = null;
    state.editingEstate = null;
    state.toast = estateId ? "Estate updated." : "Estate created.";
    await loadAdminRecords();
    if (estateId) {
      data.estateDetail = result.estate;
      state.adminPage = "estate-detail";
    }
    render();
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  } finally {
    if (submitButton.isConnected) submitButton.disabled = false;
  }
}

async function submitAllocation(form) {
  const errorMessage = form.querySelector(".form-error");
  const submitButton = form.querySelector('[type="submit"]');
  errorMessage.hidden = true;
  submitButton.disabled = true;
  try {
    const result = await recordsRequest(`companies/${state.activeCompanyId}/allocations`, {
      method: "POST",
      payload: Object.fromEntries(new FormData(form)),
    });
    state.modal = null;
    await loadAdminRecords();
    state.adminPage = "allocations";
    state.toast = result.allocation.invitation?.status === "failed"
      ? "Allocation completed, but the notification failed. Use Resend invitation to retry."
      : "Allocation completed. The invitation was accepted by the configured email backend.";
    render();
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  } finally {
    if (submitButton.isConnected) submitButton.disabled = false;
  }
}

async function uploadSurveyPlan(form) {
  const errorMessage = form.querySelector(".form-error");
  const submitButton = form.querySelector('[type="submit"]');
  const progress = form.querySelector(".survey-upload-progress");
  const progressLabel = form.querySelector(".survey-upload-progress-label");
  errorMessage.hidden = true;
  submitButton.disabled = true;
  progress.hidden = false;
  progress.value = 0;
  progressLabel.hidden = false;
  progressLabel.textContent = "Preparing upload…";

  try {
    const formData = new FormData(form);
    const csrfToken = await getCsrfToken();
    const result = await new Promise((resolve, reject) => {
      const request = new XMLHttpRequest();
      request.open("POST", `${recordsApi}/companies/${state.activeCompanyId}/survey-plans/`);
      request.withCredentials = true;
      request.setRequestHeader("Accept", "application/json");
      request.setRequestHeader("X-CSRFToken", csrfToken);
      request.upload.addEventListener("progress", (event) => {
        if (!event.lengthComputable) return;
        const percentage = Math.round((event.loaded / event.total) * 100);
        progress.value = percentage;
        progressLabel.textContent = `Uploading survey plan… ${percentage}%`;
      });
      request.addEventListener("load", () => {
        let payload = {};
        try {
          payload = JSON.parse(request.responseText);
        } catch {
          reject(new Error("The server returned an invalid upload response."));
          return;
        }
        if (request.status < 200 || request.status >= 300) {
          reject(new Error(payload.detail || "The survey plan could not be uploaded."));
          return;
        }
        resolve(payload);
      });
      request.addEventListener("error", () => reject(new Error("The survey plan upload failed. Check your connection and try again.")));
      request.addEventListener("abort", () => reject(new Error("The survey plan upload was cancelled.")));
      request.send(formData);
    });
    await loadAdminRecords();
    state.modal = null;
    state.surveyPlanAllocationId = null;
    state.adminPage = "survey";
    state.toast = result.duplicate
      ? "This survey plan was already uploaded for the allocation."
      : "Survey plan uploaded and queued for company verification.";
    render();
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
    progressLabel.textContent = "Upload did not complete.";
  } finally {
    if (submitButton.isConnected) submitButton.disabled = false;
  }
}

async function loadSurveyPlanDetail(surveyPlanId) {
  try {
    const result = await recordsRequest(
      `companies/${state.activeCompanyId}/survey-plans/${surveyPlanId}`,
    );
    const index = data.surveyPlans.findIndex((plan) => plan.id === surveyPlanId);
    if (index >= 0) data.surveyPlans[index] = result.survey_plan;
    else data.surveyPlans.unshift(result.survey_plan);
    state.selectedSurveyPlanId = surveyPlanId;
    state.modal = "survey-plan-details";
    render();
  } catch (error) {
    state.toast = error.message;
    render();
  }
}

async function saveSurveyPlanMetadata(form, surveyPlanId) {
  const errorMessage = form.querySelector(".form-error");
  errorMessage.hidden = true;
  const submitButton = form.querySelector(`[data-action="save-survey:${surveyPlanId}"]`);
  if (submitButton) submitButton.disabled = true;
  try {
    const result = await recordsRequest(
      `companies/${state.activeCompanyId}/survey-plans/${surveyPlanId}`,
      { method: "PATCH", payload: Object.fromEntries(new FormData(form)) },
    );
    const index = data.surveyPlans.findIndex((plan) => plan.id === surveyPlanId);
    if (index >= 0) data.surveyPlans[index] = result.survey_plan;
    state.toast = "Survey plan metadata updated.";
    render();
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  } finally {
    if (submitButton?.isConnected) submitButton.disabled = false;
  }
}

async function saveCompanyInformation(form) {
  const errorMessage = form.querySelector(".form-error");
  const submitButton = form.querySelector('[type="submit"]');
  errorMessage.hidden = true;
  submitButton.disabled = true;
  try {
    const result = await recordsRequest(
      `companies/${state.activeCompanyId}/settings`,
      { method: "POST", payload: Object.fromEntries(new FormData(form)) },
    );
    data.companySettings = result.company;
    await loadAdminRecords();
    state.toast = "Company information saved.";
    render();
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  } finally {
    if (submitButton.isConnected) submitButton.disabled = false;
  }
}

async function saveAccountProfile(form) {
  const errorMessage = form.querySelector(".form-error");
  const submitButton = form.querySelector('[type="submit"]');
  errorMessage.hidden = true;
  submitButton.disabled = true;
  try {
    const result = await accountRequest("profile", {
      method: "PATCH",
      payload: { full_name: new FormData(form).get("full_name") },
    });
    state.user = result.user;
    state.toast = "Account name saved.";
    render();
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  } finally {
    if (submitButton.isConnected) submitButton.disabled = false;
  }
}

async function requestAccountEmailChange(form) {
  const errorMessage = form.querySelector(".form-error");
  const submitButton = form.querySelector('[type="submit"]');
  errorMessage.hidden = true;
  submitButton.disabled = true;
  try {
    const result = await accountRequest("email-change", {
      method: "POST",
      payload: { email: new FormData(form).get("email") },
    });
    state.toast = result.detail;
    form.reset();
    render();
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  } finally {
    if (submitButton.isConnected) submitButton.disabled = false;
  }
}

async function submitPasswordChange(form) {
  const errorMessage = form.querySelector(".form-error");
  const submitButton = form.querySelector('[type="submit"]');
  const values = new FormData(form);
  errorMessage.hidden = true;
  if (values.get("new_password") !== values.get("confirm_password")) {
    errorMessage.textContent = "The new passwords do not match.";
    errorMessage.hidden = false;
    return;
  }
  submitButton.disabled = true;
  try {
    const result = await accountRequest("password-change", {
      method: "POST",
      payload: {
        current_password: values.get("current_password"),
        new_password: values.get("new_password"),
      },
    });
    form.reset();
    state.toast = result.detail;
    render();
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  } finally {
    if (submitButton.isConnected) submitButton.disabled = false;
  }
}

async function saveNotificationPreferences(form) {
  const errorMessage = form.querySelector(".form-error");
  const submitButton = form.querySelector('[type="submit"]');
  const values = new FormData(form);
  const preferenceKeys = [
    "property_allocation",
    "survey_plan_upload",
    "survey_plan_verification",
    "master_layout_processing",
  ];
  const notificationPreferences = Object.fromEntries(
    preferenceKeys.map((key) => [key, values.get(key) === "on"]),
  );
  errorMessage.hidden = true;
  submitButton.disabled = true;
  try {
    const result = await recordsRequest(
      `companies/${state.activeCompanyId}/settings`,
      { method: "POST", payload: { notification_preferences: notificationPreferences } },
    );
    data.notificationPreferences = notificationPreferences;
    data.settings = result.settings;
    state.toast = "Notification preferences saved.";
    render();
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  } finally {
    if (submitButton.isConnected) submitButton.disabled = false;
  }
}

async function verifySurveyPlan(surveyPlanId, status) {
  const notes = app.querySelector("#survey-verification-notes")?.value || "";
  try {
    const result = await recordsRequest(
      `companies/${state.activeCompanyId}/survey-plans/${surveyPlanId}/verify`,
      { method: "POST", payload: { status, notes } },
    );
    const index = data.surveyPlans.findIndex((plan) => plan.id === surveyPlanId);
    if (index >= 0) data.surveyPlans[index] = result.survey_plan;
    state.toast = `Survey plan marked ${status.replaceAll("_", " ")}.`;
    render();
  } catch (error) {
    state.toast = error.message;
    render();
  }
}

function downloadSurveyPlan(surveyPlanId, allocationId = null, inline = false) {
  const plan = data.surveyPlans.find((item) => item.id === surveyPlanId);
  if (!plan?.download_path) {
    state.toast = "Survey plan document is unavailable.";
    render();
    return;
  }
  const downloadPath = allocationId
    ? `my-property/${allocationId}/survey-plans/${surveyPlanId}/download`
    : plan.download_path;
  window.open(`${recordsApi}/${downloadPath}/${inline ? "?inline=1" : ""}`, "_blank", "noopener");
}

async function resendAllocationInvitation(allocationId) {
  try {
    const result = await recordsRequest(
      `companies/${state.activeCompanyId}/allocations/${allocationId}/resend-invitation`,
      { method: "POST", payload: {} },
    );
    await loadAdminRecords();
    state.adminPage = "allocations";
    state.toast = result.allocation.invitation?.status === "failed"
      ? "Allocation remains complete, but the notification retry failed."
      : "A new invitation was accepted by the configured email backend. Previous invitation links are invalid.";
    render();
  } catch (error) {
    state.toast = error.message;
    render();
  }
}

async function revokeAllocation(allocationId) {
  if (!window.confirm("Revoke this allocation? Its historical record will be retained and the parcel will remain allocated.")) return;
  try {
    await recordsRequest(
      `companies/${state.activeCompanyId}/allocations/${allocationId}/revoke`,
      { method: "POST", payload: {} },
    );
    await loadAdminRecords();
    state.adminPage = "allocations";
    state.toast = "Allocation revoked. Its historical record was retained.";
    render();
  } catch (error) {
    state.toast = error.message;
    render();
  }
}

async function changeEstateStatus(estateId, status) {
  try {
    await recordsRequest(`companies/${state.activeCompanyId}/estates/${estateId}/${status}`, { method: "POST", payload: {} });
    state.toast = `Estate ${status}.`;
    await loadAdminRecords();
    if (data.estateDetail?.id === Number(estateId)) {
      data.estateDetail = data.estates.find((estate) => estate.id === Number(estateId)) || null;
    }
    render();
  } catch (error) {
    state.toast = error.message;
    render();
  }
}

async function submitAuthentication(form) {
  const errorMessage = form.querySelector("#auth-error");
  const submitButton = form.querySelector('[type="submit"]');
  const values = new FormData(form);
  const isSignUp = state.authMode === "signup";
  const payload = {
    email: values.get("email"),
    password: values.get("password"),
  };
  if (isSignUp) payload.full_name = values.get("full_name");

  errorMessage.hidden = true;
  submitButton.disabled = true;
  try {
    if (state.allocationInvitationToken && isSignUp) {
      await completeAllocationInvitation({
        full_name: payload.full_name,
        password: payload.password,
      });
      return;
    }
    if (state.companyAdminInvitationToken && isSignUp) {
      await completeCompanyAdminInvitation({
        full_name: payload.full_name,
        password: payload.password,
      });
      return;
    }
    const result = await accountRequest(isSignUp ? "register" : "login", {
      method: "POST",
      payload,
    });
    state.user = result.user;
    if (state.allocationInvitationToken) {
      await completeAllocationInvitation({});
      return;
    }
    if (state.companyAdminInvitationToken) {
      await completeCompanyAdminInvitation({});
      return;
    }
    if (currentEndpoint === "admin") {
      if (!result.user.is_platform_admin && !result.user.company_admin_companies?.length) {
        await accountRequest("logout", { method: "POST", payload: {} });
        throw new Error("This account does not have administrator access.");
      }
      state.adminAuthorized = true;
      await loadAdminRecords();
      state.view = "admin";
      render();
      return;
    }
    await loadRecords();
    state.view = "user";
    render();
  } catch (error) {
    state.recordsLoading = false;
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  } finally {
    if (submitButton.isConnected) submitButton.disabled = false;
  }
}

async function submitCompanyRegistration(form) {
  const errorMessage = form.querySelector(".form-error");
  const submitButton = form.querySelector('[type="submit"]');
  const values = new FormData(form);
  errorMessage.hidden = true;
  submitButton.disabled = true;
  try {
    await recordsRequest("platform/companies/register", {
      method: "POST",
      payload: Object.fromEntries(values),
    });
    state.modal = null;
    await loadAdminRecords();
    state.adminPage = "companies";
    state.toast = "Company created. Invite its administrator when you are ready.";
    render();
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  } finally {
    if (submitButton.isConnected) submitButton.disabled = false;
  }
}

async function submitCompanyAdminInvitation(form) {
  const errorMessage = form.querySelector(".form-error");
  const submitButton = form.querySelector('[type="submit"]');
  const email = new FormData(form).get("email");
  errorMessage.hidden = true;
  submitButton.disabled = true;
  try {
    const result = await recordsRequest(`platform/companies/${state.invitationCompanyId}/invite-first-admin`, {
      method: "POST",
      payload: { email },
    });
    state.latestCompanyAdminInvitation = result.invitation_url
      ? { ...result.invitation, url: result.invitation_url }
      : null;
    state.modal = state.latestCompanyAdminInvitation ? "company-admin-invitation-sent" : null;
    state.invitationCompanyId = null;
    await loadAdminRecords();
    state.adminPage = "companies";
    state.toast = state.latestCompanyAdminInvitation
      ? "Invitation issued. Use the link shown in the confirmation."
      : "Company Admin invitation sent.";
    render();
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  } finally {
    if (submitButton.isConnected) submitButton.disabled = false;
  }
}

async function submitPasswordReset(form) {
  const errorMessage = form.querySelector("#auth-error");
  const submitButton = form.querySelector('[type="submit"]');
  const values = new FormData(form);

  errorMessage.hidden = true;
  submitButton.disabled = true;
  try {
    const result = await accountRequest("password-reset", {
      method: "POST",
      payload: { email: values.get("email") },
    });
    state.passwordResetNotice = result.detail;
    render();
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  } finally {
    if (submitButton.isConnected) submitButton.disabled = false;
  }
}

function endpointUrl(endpoint) {
  if (endpoint === "public") return currentEndpoint === "public" ? "./" : "../";
  if (endpoint === "admin")
    return currentEndpoint === "public"
      ? "admin/"
      : currentEndpoint === "admin"
        ? "./"
        : "../admin/";
  return currentEndpoint === "public"
    ? "property/"
    : currentEndpoint === "property"
      ? "./"
      : "../property/";
}

function navigateTo(endpoint) {
  window.location.assign(endpointUrl(endpoint));
}

function render() {
  let markup =
    state.view === "public"
      ? publicView()
      : state.view === "admin"
        ? adminView()
        : state.view === "auth"
          ? authView()
          : state.view === "invite"
            ? invitationView()
            : userView();

  if (state.modal === "allocation") markup += allocationModal();
  if (state.modal === "parcel") markup += parcelModal();
  if (state.modal === "survey-upload") markup += surveyPlanUploadModal();
  if (state.modal === "survey-plan-details") markup += surveyPlanDetailsModal();
  if (state.toast) markup += `<div class="toast">${state.toast}</div>`;
  app.innerHTML = markup;
  bind();
}

function bind() {
  app.querySelectorAll("[data-action]").forEach((element) => {
    element.addEventListener("click", () => handle(element.dataset.action));
  });
  const authForm = app.querySelector("#auth-form");
  if (authForm) {
    authForm.addEventListener("submit", (event) => {
      event.preventDefault();
      submitAuthentication(authForm);
    });
  }
  const passwordResetForm = app.querySelector("#password-reset-form");
  if (passwordResetForm) {
    passwordResetForm.addEventListener("submit", (event) => {
      event.preventDefault();
      submitPasswordReset(passwordResetForm);
    });
  }
  const companyForm = app.querySelector("#company-registration-form");
  if (companyForm) companyForm.addEventListener("submit", (event) => { event.preventDefault(); submitCompanyRegistration(companyForm); });
  const invitationForm = app.querySelector("#company-admin-invitation-form");
  if (invitationForm) invitationForm.addEventListener("submit", (event) => { event.preventDefault(); submitCompanyAdminInvitation(invitationForm); });
  const estateForm = app.querySelector("#estate-form");
  if (estateForm) estateForm.addEventListener("submit", (event) => { event.preventDefault(); submitEstate(estateForm); });
  const allocationForm = app.querySelector("#allocation-form");
  if (allocationForm) allocationForm.addEventListener("submit", (event) => { event.preventDefault(); submitAllocation(allocationForm); });
  const surveyPlanUploadForm = app.querySelector("#survey-plan-upload-form");
  if (surveyPlanUploadForm) surveyPlanUploadForm.addEventListener("submit", (event) => {
    event.preventDefault();
    uploadSurveyPlan(surveyPlanUploadForm);
  });
  const surveyPlanEditForm = app.querySelector("#survey-plan-edit-form");
  if (surveyPlanEditForm) surveyPlanEditForm.addEventListener("submit", (event) => {
    event.preventDefault();
    saveSurveyPlanMetadata(surveyPlanEditForm, state.selectedSurveyPlanId);
  });
  const companyInfoForm = app.querySelector("#company-info-form");
  if (companyInfoForm) companyInfoForm.addEventListener("submit", (event) => {
    event.preventDefault();
    saveCompanyInformation(companyInfoForm);
  });
  const accountProfileForm = app.querySelector("#account-profile-form");
  if (accountProfileForm) accountProfileForm.addEventListener("submit", (event) => {
    event.preventDefault();
    saveAccountProfile(accountProfileForm);
  });
  const emailChangeForm = app.querySelector("#email-change-form");
  if (emailChangeForm) emailChangeForm.addEventListener("submit", (event) => {
    event.preventDefault();
    requestAccountEmailChange(emailChangeForm);
  });
  const passwordChangeForm = app.querySelector("#password-change-form");
  if (passwordChangeForm) passwordChangeForm.addEventListener("submit", (event) => {
    event.preventDefault();
    submitPasswordChange(passwordChangeForm);
  });
  const notificationSettingsForm = app.querySelector("#notification-settings-form");
  if (notificationSettingsForm) notificationSettingsForm.addEventListener("submit", (event) => {
    event.preventDefault();
    saveNotificationPreferences(notificationSettingsForm);
  });
  const masterLayoutForm = app.querySelector("#master-layout-form");
  if (masterLayoutForm) masterLayoutForm.addEventListener("submit", (event) => { event.preventDefault(); submitMasterLayout(masterLayoutForm); });
  const masterLayoutFile = app.querySelector("#master-layout-file");
  if (masterLayoutFile) masterLayoutFile.addEventListener("change", () => {
    state.masterLayoutFileName = masterLayoutFile.files?.[0] ? `${masterLayoutFile.files[0].name} · ${(masterLayoutFile.files[0].size / 1024 / 1024).toFixed(2)} MB` : "";
    const selectedFile = app.querySelector("#master-layout-selected-file");
    if (selectedFile) {
      selectedFile.textContent = state.masterLayoutFileName ? `Selected: ${state.masterLayoutFileName}` : "";
      selectedFile.hidden = !state.masterLayoutFileName;
    }
  });
  const candidateSearch = app.querySelector("#candidate-search");
  if (candidateSearch) candidateSearch.addEventListener("input", () => { state.candidateSearch = candidateSearch.value; render(); });
  const candidateStatus = app.querySelector("#candidate-status");
  if (candidateStatus) candidateStatus.addEventListener("change", () => { state.candidateStatusFilter = candidateStatus.value; render(); });
  app.querySelectorAll("[data-candidate-id]").forEach((checkbox) => checkbox.addEventListener("change", () => {
    const candidateId = checkbox.dataset.candidateId;
    state.selectedCandidateIds = checkbox.checked
      ? [...new Set([...state.selectedCandidateIds, candidateId])]
      : state.selectedCandidateIds.filter((id) => id !== candidateId);
    render();
  }));
  const estateSearch = app.querySelector("#estate-search");
  if (estateSearch) estateSearch.addEventListener("input", () => { state.estateSearch = estateSearch.value; render(); });
  const estateStatus = app.querySelector("#estate-status");
  if (estateStatus) estateStatus.addEventListener("change", () => { state.estateStatusFilter = estateStatus.value; render(); });
  const surveyPlanSearch = app.querySelector("#survey-plan-search");
  if (surveyPlanSearch) surveyPlanSearch.addEventListener("input", () => {
    state.surveyPlanSearch = surveyPlanSearch.value;
    render();
  });
  const surveyPlanStatus = app.querySelector("#survey-plan-status");
  if (surveyPlanStatus) surveyPlanStatus.addEventListener("change", () => {
    state.surveyPlanStatusFilter = surveyPlanStatus.value;
    render();
  });
  const surveyPlanEstate = app.querySelector("#survey-plan-estate");
  if (surveyPlanEstate) surveyPlanEstate.addEventListener("change", () => {
    state.surveyPlanEstateFilter = surveyPlanEstate.value;
    render();
  });
  const surveyPlanBlock = app.querySelector("#survey-plan-block");
  if (surveyPlanBlock) surveyPlanBlock.addEventListener("input", () => {
    state.surveyPlanBlockFilter = surveyPlanBlock.value;
    render();
  });
  const surveyPlanDate = app.querySelector("#survey-plan-date");
  if (surveyPlanDate) surveyPlanDate.addEventListener("change", () => {
    state.surveyPlanDateFilter = surveyPlanDate.value;
    render();
  });
  const search = document.querySelector("#parcel-search");
  if (search) search.addEventListener("input", filterParcels);
  const filter = document.querySelector("#parcel-status");
  if (filter) filter.addEventListener("change", filterParcels);
  const companySwitch = app.querySelector("#company-switch");
  if (companySwitch) {
    companySwitch.addEventListener("change", async () => {
      try {
        await loadAdminRecords(companySwitch.value);
        render();
      } catch (error) {
        state.toast = error.message;
        render();
      }
    });
  }
}

function handle(action) {
  const [kind, value] = action.split(":");
  if (action === "public") {
    navigateTo("public");
    return;
  } else if (action === "admin") {
    navigateTo("admin");
    return;
  } else if (action === "auth") {
    navigateTo("property");
    return;
  } else if (action === "invite-preview") {
    state.view = "invite";
  } else if (action === "user") {
    state.view = "user";
    state.userPage = "properties";
  } else if (action === "create-allocation") {
    state.adminPage = "allocations";
    state.modal = "allocation";
  } else if (action === "upload-survey") {
    state.surveyPlanAllocationId = null;
    state.modal = "survey-upload";
  } else if (action.startsWith("upload-survey:")) {
    state.surveyPlanAllocationId = Number(action.split(":")[1]);
    state.modal = "survey-upload";
  } else if (action.startsWith("view-survey:")) {
    loadSurveyPlanDetail(action.split(":")[1]);
    return;
  } else if (action.startsWith("download-survey:")) {
    downloadSurveyPlan(action.split(":")[1]);
    return;
  } else if (action.startsWith("view-survey-document:")) {
    downloadSurveyPlan(action.split(":")[1], null, true);
    return;
  } else if (action.startsWith("save-survey:")) {
    const surveyPlanId = action.split(":")[1];
    const form = app.querySelector("#survey-plan-edit-form");
    if (form) saveSurveyPlanMetadata(form, surveyPlanId);
    return;
  } else if (action.startsWith("verify-survey:")) {
    const [, surveyPlanId, status] = action.split(":");
    verifySurveyPlan(surveyPlanId, status);
    return;
  } else if (action.startsWith("resend-allocation:")) {
    resendAllocationInvitation(action.split(":")[1]);
    return;
  } else if (action.startsWith("revoke-allocation:")) {
    revokeAllocation(action.split(":")[1]);
    return;
  } else if (action.startsWith("property-detail:")) {
    loadPropertyDetail(action.split(":")[1]);
    return;
  } else if (action === "accept-allocation") {
    completeAllocationInvitation().catch((error) => {
      state.toast = error.message;
      render();
    });
    return;
  } else if (action === "allocation-signout") {
    accountRequest("logout", { method: "POST", payload: {} })
      .then(() => {
        state.user = null;
        state.view = "invite";
        state.authMode = "signin";
        render();
      })
      .catch((error) => {
        state.toast = error.message;
        render();
      });
    return;
  } else if (action === "register-company") {
    state.modal = "register-company";
  } else if (action === "create-estate") {
    state.editingEstate = null;
    state.modal = "estate-form";
  } else if (action.startsWith("view-estate:")) {
    loadEstateDetail(action.split(":")[1]);
    return;
  } else if (action.startsWith("edit-estate:")) {
    const estateId = Number(action.split(":")[1]);
    state.editingEstate = data.estateDetail?.id === estateId
      ? data.estateDetail
      : data.estates.find((estate) => estate.id === estateId);
    state.modal = "estate-form";
  } else if (action.startsWith("estate-status:")) {
    const [, estateId, estateStatus] = action.split(":");
    if (estateStatus === "archived" && !window.confirm("Archive this estate? Its existing parcels, plans, and allocations will be retained.")) return;
    changeEstateStatus(estateId, estateStatus);
    return;
  } else if (action === "back-to-estates") {
    state.adminPage = "estates";
    data.estateDetail = null;
  } else if (action.startsWith("estate-tab:")) {
    state.estateDetailTab = action.split(":")[1];
    if (state.estateDetailTab === "master-layout") {
      loadEstateMasterLayouts();
      return;
    }
  } else if (action === "upload-master-layout") {
    state.masterLayoutFileName = "";
    state.modal = "master-layout-upload";
  } else if (action.startsWith("process-master-layout:")) {
    processMasterLayout(action.split(":")[1]);
    return;
  } else if (action.startsWith("review-master-layout:")) {
    state.candidateSearch = "";
    state.candidateStatusFilter = "all";
    loadMasterLayoutReview(action.split(":")[1]);
    return;
  } else if (action.startsWith("approve-master-layout:")) {
    reviewMasterLayoutCandidates(action.split(":")[1], "approve");
    return;
  } else if (action.startsWith("reject-master-layout:")) {
    if (!window.confirm("Reject the selected extraction candidates? This does not delete the uploaded source file.")) return;
    reviewMasterLayoutCandidates(action.split(":")[1], "reject");
    return;
  } else if (kind === "invite-company-admin") {
    state.invitationCompanyId = Number(value);
    state.modal = "invite-company-admin";
  } else if (kind === "invitation-auth") {
    state.authMode = value;
    state.view = "auth";
  } else if (action === "open-company-workspace") {
    navigateTo("admin");
    return;
  } else if (action === "copy-company-admin-invitation") {
    const url = state.latestCompanyAdminInvitation?.url;
    if (!url) return;
    navigator.clipboard.writeText(url)
      .then(() => {
        state.toast = "Current invitation link copied.";
        render();
      })
      .catch(() => {
        state.toast = "Copy the invitation link from the confirmation field.";
        render();
      });
    return;
  } else if (action === "logout") {
    accountRequest("logout", { method: "POST", payload: {} })
      .then(() => {
        state.user = null;
        state.view = state.allocationInvitationToken || state.companyAdminInvitationToken ? "invite" : "auth";
        state.authMode = "signin";
        render();
      })
      .catch(() => {
        state.toast = "Could not sign out. Check that the backend is running.";
        render();
      });
    return;
  } else if (kind === "auth-mode") {
    state.authMode = value;
    state.passwordResetNotice = "";
  } else if (kind === "admin-page") {
    state.adminPage = value;
    state.view = "admin";
  } else if (kind === "settings-section") {
    state.settingsSection = value;
  } else if (kind === "user-page") {
    state.userPage = value;
    if (value !== "allocation") state.propertyDetail = null;
    state.view = "user";
  } else if (kind === "property-tab") {
    state.propertyTab = value;
  } else if (kind === "parcel") {
    state.selectedParcel = data.parcels.find((parcel) => parcel.plot === value);
    state.modal = "parcel";
  } else if (kind === "select-parcel") {
    state.selectedParcel = data.parcels.find((parcel) => parcel.plot === value);
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
    state.toast = "Allocation creation requires backend authorization.";
  } else if (kind === "toast") {
    state.toast = value;
  }
  render();
  if (state.toast) {
    setTimeout(() => {
      state.toast = "";
      render();
    }, 2800);
  }
}

function filterParcels() {
  const query = document.querySelector("#parcel-search").value.toLowerCase();
  const status = document.querySelector("#parcel-status").value;
  document.querySelectorAll("[data-selectable]").forEach((row) => {
    const text = row.textContent.toLowerCase();
    const matches =
      text.includes(query) &&
      (status === "All" || text.includes(status.toLowerCase()));
    row.style.display = matches ? "" : "none";
  });
}

render();

if (currentEndpoint === "property") {
  accountRequest("me")
    .then(async ({ user }) => {
      state.user = user;
      if (state.companyAdminInvitationToken) {
        await loadCompanyAdminInvitation();
        state.view = "invite";
        render();
        return;
      }
      if (state.allocationInvitationToken) {
        await loadAllocationInvitation();
        state.view = "invite";
        render();
        return;
      }
      await loadRecords();
      state.view = "user";
      render();
    })
    .catch((error) => {
      if (state.companyAdminInvitationToken) {
        loadCompanyAdminInvitation().then(render);
      } else if (state.allocationInvitationToken) {
        loadAllocationInvitation().then(() => {
          state.view = "invite";
          render();
        });
      } else if (error.status !== 401) {
        state.toast = "Could not connect to the account backend.";
        render();
      }
    });
}

if (currentEndpoint === "admin") {
  const emailChangeToken = new URLSearchParams(window.location.search).get("email_change");
  if (emailChangeToken) {
    accountRequest("email-change/confirm", {
      method: "POST",
      payload: { token: emailChangeToken },
    })
      .then((result) => {
        window.history.replaceState({}, "", window.location.pathname);
        if (result.user) state.user = result.user;
        state.toast = result.detail;
        render();
      })
      .catch((error) => {
        window.history.replaceState({}, "", window.location.pathname);
        state.toast = error.message;
        render();
      });
  }
  accountRequest("me")
    .then(async ({ user }) => {
      state.user = user;
      state.adminAuthorized = user.is_platform_admin || user.company_admin_companies?.length;
      if (!state.adminAuthorized) {
        state.view = "auth";
        state.toast = "Administrator access is required for this workspace.";
        render();
        return;
      }
      await loadAdminRecords();
      state.view = "admin";
      render();
    })
    .catch(() => {
      render();
    });
}
