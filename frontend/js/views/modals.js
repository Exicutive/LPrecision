import { data, state } from "../data.js";
import { button, parcelSvg, status } from "../components.js";

export function allocationModal() {
  const parcel = state.selectedParcel;
  const progress = ["Parcel", "Recipient", "Review", "Confirm"]
    .map(
      (label, index) =>
        /* HTML */ `<div
          data-step="${index + 1}"
          class="${state.allocationStep === index + 1 ? "active" : ""}"
        >
          ${label}
        </div>`,
    )
    .join("");
  const previousAction =
    state.allocationStep > 1
      ? button("Back", "allocation-back", "secondary")
      : button("Cancel", "close-modal", "secondary");
  const nextAction =
    state.allocationStep < 4
      ? button("Continue", "allocation-next", "primary")
      : button("Confirm demonstration", "allocation-confirm", "primary");
  let body = "";
  if (state.allocationStep === 1)
    body = /* HTML */ `<p>Select an available parcel for this allocation.</p>
      <div class="form-grid">
        ${data.parcels
          .filter((item) => item.status === "Available")
          .map(
            (item) =>
              `<button class="button ${parcel.plot === item.plot ? "primary" : "secondary"}" data-action="select-parcel:${item.plot}">${item.plot} · ${item.area}</button>`,
          )
          .join("")}
      </div>`;
  if (state.allocationStep === 2)
    body = /* HTML */ `<p>
        Enter the intended allottee details. These values stay in the browser
        and are not sent anywhere.
      </p>
      <div class="form-grid">
        <div class="field">
          <label>Full name</label
          ><input id="allottee-name" placeholder="e.g. Adewale Bello" />
        </div>
        <div class="field">
          <label>Email address</label
          ><input
            id="allottee-email"
            type="email"
            placeholder="name@example.com"
          />
        </div>
        <div class="field full">
          <label>Phone number (optional)</label><input placeholder="+234 …" />
        </div>
      </div>`;
  if (state.allocationStep === 3)
    body = /* HTML */ `<p>
        Review the property and recipient information before creating a
        demonstration invitation.
      </p>
      <div class="review-card">
        <strong
          >${parcel.plot} · Block ${parcel.block} · Abeni Gardens Estate</strong
        ><span>${parcel.area} · Currently available</span>
      </div>
      <div class="review-card">
        <strong>Recipient details</strong
        ><span
          >Captured only in this browser for a frontend demonstration.</span
        >
      </div>`;
  if (state.allocationStep === 4)
    body = /* HTML */ `<div class="review-card">
        <strong>Ready to demonstrate allocation</strong
        ><span
          >A local status change will be shown. No allocation is written to a
          database and no email is sent.</span
        >
      </div>
      <div class="notice">
        In production, this final step requires authorized backend validation,
        persistence and a secure invitation delivery service.
      </div>`;
  return /* HTML */ `<div class="modal-backdrop">
    <section
      class="modal"
      role="dialog"
      aria-modal="true"
      aria-labelledby="allocation-title"
    >
      <header class="modal-header">
        <div>
          <p class="eyebrow">Allocation workflow</p>
          <h2 id="allocation-title">Allocate a property</h2>
        </div>
        <button
          class="close"
          aria-label="Close allocation workflow"
          data-action="close-modal"
        >
          ×
        </button>
      </header>
      <div class="progress">${progress}</div>
      ${body}
      <div class="form-actions">${previousAction}${nextAction}</div>
    </section>
  </div>`;
}

export function parcelModal() {
  const parcel = state.selectedParcel;
  return /* HTML */ `<div class="modal-backdrop">
    <section class="modal" role="dialog" aria-modal="true">
      <header class="modal-header">
        <div>
          <p class="eyebrow">Parcel detail</p>
          <h2>Plot ${parcel.plot}, Block ${parcel.block}</h2>
          <p>Abeni Gardens Estate · ${parcel.area}</p>
        </div>
        <button
          class="close"
          aria-label="Close parcel details"
          data-action="close-modal"
        >
          ×
        </button>
      </header>
      <section class="boundary-panel" style="min-height:270px">
        ${parcelSvg()}
        <div class="boundary-top">
          <span>Example surveyed boundary</span><span>N ↑</span>
        </div>
      </section>
      <section class="two-column" style="margin-top:17px">
        <article class="panel">
          <div class="detail-list">
            <div><span>Status</span>${status(parcel.status)}</div>
            <div>
              <span>Assigned person</span><strong>${parcel.person}</strong>
            </div>
            <div><span>Survey plan</span><strong>SP/AG/2026/014</strong></div>
          </div>
        </article>
        <article class="panel">
          <div class="detail-list">
            <div><span>Area</span><strong>${parcel.area}</strong></div>
            <div><span>Perimeter</span><strong>103.74 m</strong></div>
            <div><span>Geometry</span><strong>Validated sample</strong></div>
          </div>
        </article>
      </section>
      <div class="form-actions">
        ${parcel.status === "Available" ? button("Allocate property", "open-allocation", "primary") : button("Close", "close-modal", "secondary")}
      </div>
    </section>
  </div>`;
}
