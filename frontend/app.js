import { currentEndpoint, data, state } from "./js/data.js?v=20261127-auth-navigation";
import { adminView } from "./js/views/admin.js?v=20261127-workspace-auth";
import { authView } from "./js/views/auth.js?v=20261127-auth-navigation";
import { parcelSvg } from "./js/components.js?v=20261026";
import {
  allocationModal,
  boundaryGuidanceModal,
  parcelCreationModal,
  parcelModal,
  propertyBoundaryCoordinatesModal,
  propertySurveyPlanUploadModal,
} from "./js/views/modals.js?v=20261106-settings";
import { invitationView, userView } from "./js/views/property.js?v=20261106-settings";
import { publicView } from "./js/views/public.js?v=20261106-header-footer";

const app = document.querySelector("#app");
const apiBase = `${window.location.origin}/api`;
const accountApi = `${apiBase}/accounts`;
const recordsApi = `${apiBase}/records`;
let boundaryGuidanceWatchId = null;

function pointInsidePolygon([longitude, latitude], polygon) {
  let inside = false;
  for (let index = 0, previous = polygon.length - 1; index < polygon.length; previous = index++) {
    const [x, y] = polygon[index];
    const [previousX, previousY] = polygon[previous];
    if ((y > latitude) !== (previousY > latitude)
      && longitude < ((previousX - x) * (latitude - y)) / (previousY - y) + x) inside = !inside;
  }
  return inside;
}

function boundaryDistance([longitude, latitude], polygon) {
  const radians = Math.PI / 180;
  const earthRadius = 6371008.8;
  const project = ([x, y]) => [
    (x - longitude) * radians * earthRadius * Math.cos(latitude * radians),
    (y - latitude) * radians * earthRadius,
  ];
  let closest = null;
  for (let index = 0; index < polygon.length; index += 1) {
    const start = project(polygon[index]);
    const end = project(polygon[(index + 1) % polygon.length]);
    const dx = end[0] - start[0];
    const dy = end[1] - start[1];
    const ratio = Math.max(0, Math.min(1, -(start[0] * dx + start[1] * dy) / (dx * dx + dy * dy)));
    const point = [start[0] + ratio * dx, start[1] + ratio * dy];
    const distance = Math.hypot(point[0], point[1]);
    if (!closest || distance < closest.distance) closest = { distance, point };
  }
  const bearing = (Math.atan2(-closest.point[0], -closest.point[1]) * 180 / Math.PI + 360) % 360;
  const direction = ["north", "north-east", "east", "south-east", "south", "south-west", "west", "north-west"][Math.round(bearing / 45) % 8];
  return { ...closest, direction };
}

function describeGuidance(position, polygon) {
  const inside = pointInsidePolygon([position.longitude, position.latitude], polygon);
  const nearest = boundaryDistance([position.longitude, position.latitude], polygon);
  return {
    inside,
    direction: nearest.direction,
    distance: nearest.distance,
    distanceText: `${Math.max(1, Math.round(nearest.distance))} metres`,
    accuracyText: `${Math.max(1, Math.round(position.accuracy))} metres`,
  };
}

function speakGuidance(result) {
  const guidance = state.boundaryGuidance;
  if (!guidance?.audio || !window.speechSynthesis) return;
  const message = result.inside
    ? `You are inside the recorded boundary. The nearest boundary is about ${result.distanceText} away.`
    : `You are approximately ${result.distanceText} outside the recorded ${result.direction} boundary.`;
  const now = Date.now();
  if (guidance.lastSpokenMessage === message && now - (guidance.lastSpokenAt || 0) < 15000) return;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(new SpeechSynthesisUtterance(message));
  guidance.lastSpokenMessage = message;
  guidance.lastSpokenAt = now;
}

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

function clearSensitiveClientState() {
  Object.assign(data, {
    estates: [], parcels: [], allocations: [], companies: [], auditEvents: [],
    platformSummary: null, companySummary: null, estateOverview: null, estateDetail: null,
    settings: {}, companySettings: null, notificationPreferences: {},
  });
  Object.assign(state, {
    user: null, adminRole: null, activeCompanyId: null, propertyAllocations: [],
    propertyAllocation: null, propertyDetail: null, selectedAllocationId: null,
    propertySurveyAllocationId: null, propertyBoundaryAllocationId: null, boundaryGuidance: null,
    selectedParcel: null, selectedEstateId: null, editingEstate: null, modal: null,
    adminAuthorized: false, latestCompanyAdminInvitation: null,
  });
}

async function signOut({ invitationMode } = {}) {
  await accountRequest("logout", { method: "POST", payload: {} });
  clearSensitiveClientState();
  const hasInvitation = state.allocationInvitationToken || state.companyAdminInvitationToken;
  state.view = hasInvitation && !invitationMode ? "invite" : "auth";
  state.authMode = invitationMode || "signin";
  window.history.replaceState({}, "", window.location.pathname + window.location.search);
  render();
}

async function signOutForAllocationAccount() {
  state.invitationActionError = "";
  state.invitationActionLoading = true;
  render();
  try {
    await signOut({ invitationMode: "signup" });
  } catch (error) {
    state.invitationActionLoading = false;
    state.invitationActionError = error.message || "Could not sign out. Refresh the page and try again.";
    state.view = "invite";
    render();
  }
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
    const [summary, estates, estateOverview, parcels, allocations, settings] = await Promise.all([
      recordsRequest(`${prefix}/dashboard`),
      recordsRequest(`${prefix}/estates`),
      recordsRequest(`${prefix}/estates/overview`),
      recordsRequest(`${prefix}/parcels`),
      recordsRequest(`${prefix}/allocations`),
      recordsRequest(`${prefix}/settings`),
    ]);
    data.companySummary = summary;
    data.estates = estates.estates;
    data.estateOverview = estateOverview;
    data.parcels = parcels.parcels;
    data.allocations = allocations.allocations;
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

async function submitEstate(form) {
  const errorMessage = form.querySelector(".form-error");
  const submitButton = form.querySelector('[type="submit"]');
  const formData = new FormData(form);
  const image = formData.get("image");
  const removeImage = formData.get("remove_image") === "true";
  errorMessage.hidden = true;
  submitButton.disabled = true;
  try {
    const estateId = state.editingEstate?.id;
    const result = await recordsRequest(
      estateId ? `companies/${state.activeCompanyId}/estates/${estateId}` : `companies/${state.activeCompanyId}/estates`,
      image?.size || removeImage
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
    errorMessage.textContent = error.message || "The estate could not be saved. Try a smaller image or continue without one.";
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

async function submitParcel(form) {
  const errorMessage = form.querySelector(".form-error");
  const submitButton = form.querySelector('[type="submit"]');
  errorMessage.hidden = true;
  submitButton.disabled = true;
  try {
    const result = await recordsRequest(`companies/${state.activeCompanyId}/parcels`, {
      method: "POST",
      payload: Object.fromEntries(new FormData(form)),
    });
    state.modal = null;
    state.adminPage = "parcels";
    state.toast = `${result.parcel.name} is now available for allocation.`;
    await loadAdminRecords();
    render();
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  } finally {
    if (submitButton.isConnected) submitButton.disabled = false;
  }
}

async function uploadPropertySurveyPlan(form) {
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
    const csrfToken = await getCsrfToken();
    const formData = new FormData(form);
    const allocationId = state.propertySurveyAllocationId;
    const result = await new Promise((resolve, reject) => {
      const request = new XMLHttpRequest();
      request.open("POST", `${recordsApi}/my-property/${allocationId}/survey-plans/`);
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
        try { payload = JSON.parse(request.responseText); } catch { reject(new Error("The server returned an invalid upload response.")); return; }
        if (request.status < 200 || request.status >= 300) { reject(new Error(payload.detail || "The survey plan could not be uploaded.")); return; }
        resolve(payload);
      });
      request.addEventListener("error", () => reject(new Error("The survey plan upload failed. Check your connection and try again.")));
      request.addEventListener("abort", () => reject(new Error("The survey plan upload was cancelled.")));
      request.send(formData);
    });
    await loadRecords();
    state.propertyDetail = state.propertyAllocations.find(
      (allocation) => allocation.id === Number(allocationId),
    ) || null;
    state.modal = null;
    state.propertySurveyAllocationId = null;
    state.toast = result.duplicate ? "This survey plan is already saved for this property." : "Survey plan and boundary saved.";
    render();
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
    progressLabel.textContent = "Upload did not complete.";
  } finally {
    if (submitButton.isConnected) submitButton.disabled = false;
  }
}

async function savePropertyBoundaryCoordinates(form) {
  const errorMessage = form.querySelector(".form-error");
  const submitButton = form.querySelector('[type="submit"]');
  errorMessage.hidden = true;
  submitButton.disabled = true;
  try {
    const allocationId = state.propertyBoundaryAllocationId;
    const values = Object.fromEntries(new FormData(form));
    const result = await recordsRequest(`my-property/${allocationId}/boundary`, {
      method: "POST",
      payload: values,
    });
    await loadRecords();
    state.propertyDetail = state.propertyAllocations.find(
      (allocation) => allocation.id === Number(allocationId),
    ) || null;
    state.modal = null;
    state.propertyBoundaryAllocationId = null;
    state.toast = `Recorded boundary saved with ${result.parcel.boundary_coordinates.length} vertices.`;
    render();
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  } finally {
    if (submitButton.isConnected) submitButton.disabled = false;
  }
}

function beginBoundaryGuidance() {
  const guidance = state.boundaryGuidance;
  const allocation = state.propertyAllocations.find(
    (item) => item.id === Number(guidance?.allocationId),
  );
  if (!allocation || allocation.parcel.boundary_coordinate_reference_system !== "EPSG:4326") {
    state.boundaryGuidance = { ...guidance, error: "This property needs a WGS84 recorded boundary before guidance can start." };
    render();
    return;
  }
  if (!navigator.geolocation) {
    state.boundaryGuidance = { ...guidance, error: "This browser does not support live location." };
    render();
    return;
  }
  state.boundaryGuidance = { ...guidance, active: true, error: "Requesting your location…" };
  render();
  boundaryGuidanceWatchId = navigator.geolocation.watchPosition(
    (position) => {
      const currentPosition = {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy,
      };
      if (currentPosition.accuracy > 50) {
        state.boundaryGuidance = {
          ...state.boundaryGuidance,
          position: currentPosition,
          result: null,
          error: `Location accuracy is about ${Math.round(currentPosition.accuracy)} metres. Move to an open area and wait for a more accurate reading.`,
        };
      } else {
        const result = describeGuidance(currentPosition, allocation.parcel.boundary_coordinates);
        state.boundaryGuidance = { ...state.boundaryGuidance, position: currentPosition, result, error: "" };
        speakGuidance(result);
      }
      render();
    },
    (error) => {
      const message = error.code === error.PERMISSION_DENIED
        ? "Location permission was not granted. You can enable it in your browser settings and try again."
        : "Your location could not be read. Check GPS, network, and browser permissions, then try again.";
      state.boundaryGuidance = { ...state.boundaryGuidance, active: false, error: message };
      render();
    },
    { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 },
  );
}

function stopBoundaryGuidance() {
  if (boundaryGuidanceWatchId !== null) navigator.geolocation?.clearWatch(boundaryGuidanceWatchId);
  boundaryGuidanceWatchId = null;
  if (window.speechSynthesis) window.speechSynthesis.cancel();
  state.boundaryGuidance = null;
  state.modal = null;
  render();
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
  if (!window.confirm("Revoke this allocation? Its historical record will be retained and the parcel will become available for a new allocation.")) return;
  try {
    await recordsRequest(
      `companies/${state.activeCompanyId}/allocations/${allocationId}/revoke`,
      { method: "POST", payload: {} },
    );
    await loadAdminRecords();
    state.adminPage = "allocations";
    state.toast = "Allocation revoked. The parcel is now available to allocate again.";
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
        await signOut();
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
      ? {
          ...result.invitation,
          url: result.invitation_url,
          emailDeliveryWarning: result.email_delivery_warning || "",
        }
      : null;
    state.modal = state.latestCompanyAdminInvitation ? "company-admin-invitation-sent" : null;
    state.invitationCompanyId = null;
    await loadAdminRecords();
    state.adminPage = "companies";
    state.toast = state.latestCompanyAdminInvitation
      ? result.email_delivery_warning || "Invitation issued. Use the link shown in the confirmation."
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
      ? "workspace/"
      : currentEndpoint === "admin"
        ? "./"
        : "../workspace/";
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
  if (state.modal === "parcel-creation") markup += parcelCreationModal();
  if (state.modal === "parcel") markup += parcelModal();
  if (state.modal === "property-survey-upload") markup += propertySurveyPlanUploadModal();
  if (state.modal === "property-boundary-coordinates") markup += propertyBoundaryCoordinatesModal();
  if (state.modal === "boundary-guidance") markup += boundaryGuidanceModal();
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
  const parcelCreationForm = app.querySelector("#parcel-creation-form");
  if (parcelCreationForm) parcelCreationForm.addEventListener("submit", (event) => { event.preventDefault(); submitParcel(parcelCreationForm); });
  const propertySurveyPlanUploadForm = app.querySelector("#property-survey-plan-upload-form");
  if (propertySurveyPlanUploadForm) propertySurveyPlanUploadForm.addEventListener("submit", (event) => {
    event.preventDefault();
    uploadPropertySurveyPlan(propertySurveyPlanUploadForm);
  });
  const propertyBoundaryCoordinatesForm = app.querySelector("#property-boundary-coordinates-form");
  if (propertyBoundaryCoordinatesForm) propertyBoundaryCoordinatesForm.addEventListener("submit", (event) => {
    event.preventDefault();
    savePropertyBoundaryCoordinates(propertyBoundaryCoordinatesForm);
  });
  const boundaryCoordinates = app.querySelector("#submitted-boundary-coordinates");
  if (boundaryCoordinates) boundaryCoordinates.addEventListener("input", () => {
    const preview = app.querySelector("#submitted-boundary-preview");
    if (!preview) return;
    try {
      const coordinates = JSON.parse(boundaryCoordinates.value || "[]");
      preview.innerHTML = parcelSvg(false, coordinates);
    } catch {
      preview.innerHTML = "<p class=\"muted\" style=\"padding:20px\">Enter valid JSON coordinate pairs to preview the boundary.</p>";
    }
  });
  const directBoundaryCoordinates = app.querySelector("#direct-boundary-coordinates");
  if (directBoundaryCoordinates) directBoundaryCoordinates.addEventListener("input", () => {
    const preview = app.querySelector("#direct-boundary-preview");
    if (!preview) return;
    try {
      preview.innerHTML = parcelSvg(false, JSON.parse(directBoundaryCoordinates.value || "[]"));
    } catch {
      preview.innerHTML = "<p class=\"muted\" style=\"padding:20px\">Enter valid JSON coordinate pairs to preview the boundary.</p>";
    }
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
  const estateSearch = app.querySelector("#estate-search");
  if (estateSearch) estateSearch.addEventListener("input", () => { state.estateSearch = estateSearch.value; render(); });
  const estateStatus = app.querySelector("#estate-status");
  if (estateStatus) estateStatus.addEventListener("change", () => { state.estateStatusFilter = estateStatus.value; render(); });
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
  } else if (action === "workspace-auth") {
    signOut().catch(() => {
      clearSensitiveClientState();
      state.view = "auth";
      state.authMode = "signin";
      state.toast = "Your session could not be closed automatically. Please sign in with the account that has workspace access.";
      render();
    });
    return;
  } else if (action === "invite-preview") {
    state.view = "invite";
  } else if (action === "user") {
    state.view = "user";
    state.userPage = "properties";
  } else if (action === "create-allocation") {
    state.adminPage = "allocations";
    state.modal = "allocation";
  } else if (action === "create-parcel") {
    state.adminPage = "parcels";
    state.modal = "parcel-creation";
  } else if (action.startsWith("upload-property-survey:")) {
    state.propertySurveyAllocationId = Number(action.split(":")[1]);
    state.modal = "property-survey-upload";
  } else if (action.startsWith("edit-boundary-coordinates:")) {
    state.propertyBoundaryAllocationId = Number(action.split(":")[1]);
    state.modal = "property-boundary-coordinates";
  } else if (action.startsWith("start-boundary-guidance:")) {
    state.boundaryGuidance = {
      allocationId: Number(action.split(":")[1]), active: false, audio: false, error: "", position: null, result: null,
    };
    state.modal = "boundary-guidance";
  } else if (action === "start-boundary-guidance") {
    beginBoundaryGuidance();
    return;
  } else if (action === "stop-boundary-guidance") {
    stopBoundaryGuidance();
    return;
  } else if (action === "toggle-boundary-audio") {
    state.boundaryGuidance = { ...state.boundaryGuidance, audio: !state.boundaryGuidance?.audio };
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
    signOutForAllocationAccount();
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
    signOut()
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
        loadCompanyAdminInvitation().then(() => {
          if (!state.invitationError) {
            state.authMode = "signup";
            state.view = "auth";
          } else {
            state.view = "invite";
          }
          render();
        });
      } else if (state.allocationInvitationToken) {
        loadAllocationInvitation().then(() => {
          // A property invite is most often for a recipient who does not have an
          // account yet. Take that recipient straight to the account form instead
          // of leaving the sign-in mode selected by default. Existing recipients
          // can still choose the Sign in tab on the form.
          if (!state.invitationError) {
            state.authMode = "signup";
            state.view = "auth";
          } else {
            state.view = "invite";
          }
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
