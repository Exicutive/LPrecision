import { currentEndpoint, data, state } from "./js/data.js";
import { adminView } from "./js/views/admin.js";
import { authView } from "./js/views/auth.js";
import { allocationModal, parcelModal } from "./js/views/modals.js";
import { invitationView, userView } from "./js/views/property.js";
import { publicView } from "./js/views/public.js";

const app = document.querySelector("#app");

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
  if (state.toast) markup += `<div class="toast">${state.toast}</div>`;
  app.innerHTML = markup;
  bind();
}

function bind() {
  app.querySelectorAll("[data-action]").forEach((element) => {
    element.addEventListener("click", () => handle(element.dataset.action));
  });
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
  } else if (action === "auth") {
    navigateTo("property");
    return;
  } else if (action === "invite-preview") {
    state.view = "invite";
  } else if (action === "user") {
    state.view = "user";
    state.userPage = "property";
  } else if (action === "authenticate") {
    state.toast =
      "Authentication is simulated in this frontend demonstration. Connect an identity service to enable sign-in.";
  } else if (kind === "auth-mode") {
    state.authMode = value;
  } else if (kind === "admin-page") {
    state.adminPage = value;
    state.view = "admin";
  } else if (kind === "user-page") {
    state.userPage = value;
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
    state.toast =
      "Demonstration allocation confirmed locally. No email was sent.";
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
