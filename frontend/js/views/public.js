import { brand, button, parcelSvg } from "../components.js";

function publicFooter() {
  return `<footer class="public-footer">
    <div>
      <section>
        <a class="brand" href="#home">${brand()}</a>
        <p>Digital land allocation and boundary verification in Nigerian estates.</p>
      </section>
      <section class="footer-links">
        <h3>Platform</h3>
        <a href="#home">Property access</a>
        <a href="#home">Administrator workspace</a>
        <a href="#home">Survey records</a>
      </section>
      <section class="footer-links">
        <h3>Support</h3>
        <a href="#home">Contact placeholder</a>
        <a href="#home">Help centre</a>
        <a href="#home">Report a record issue</a>
      </section>
      <section class="footer-links">
        <h3>Legal</h3>
        <a href="#home">Privacy</a>
        <a href="#home">Terms of use</a>
        <a href="#home">Record disclaimer</a>
      </section>
    </div>
    <div class="copyright">© 2026 TerraLedger.</div>
  </footer>`;
}

function featureCard([symbol, title, description]) {
  return `<article class="feature">
    <div class="feature-icon">${symbol}</div>
    <h3>${title}</h3>
    <p>${description}</p>
  </article>`;
}

export function publicView() {
  const features = [
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
  ];

  return `<header class="public-header">
    <div>
      <a class="brand" href="#home">${brand()}</a>
      <div class="public-actions">
        <span class="secure-label">Controlled record access</span>
        ${button("User login", "auth", "primary", "small")}
      </div>
    </div>
  </header>
  <main>
    <section class="hero">
      <div>
        <p class="eyebrow">Digital land allocation & boundary verification</p>
        <h1>Know Your Property. Understand Your Boundaries.</h1>
        <p class="lead">A controlled digital workspace for estate teams and allottees to manage approved parcel records, surveyed boundaries and verified allocation access.</p>
        <div class="hero-actions">${button("Access My Property ->", "auth", "primary")}</div>
        <p class="hero-note">Records are released only to authorized account holders.</p>
      </div>
      <div class="parcel-preview">
        <span class="map-label">Surveyed parcel preview</span>
        ${parcelSvg(true)}
        <div class="parcel-info">
          <strong>Marbella Luxury Estate · Plot A-003</strong>
          <span>Boundary visualization — not a legal title or survey validation.</span>
        </div>
      </div>
    </section>
    <section class="public-section">
      <div class="section-heading">
        <p class="eyebrow">Built for clear records</p>
        <h2>A single, trusted view of allocation and survey information.</h2>
      </div>
      <div class="feature-grid">${features.map(featureCard).join("")}</div>
    </section>
    <section class="public-section">
      <div class="section-heading">
        <p class="eyebrow">How it works</p>
        <h2>Designed around a deliberate authorization journey.</h2>
      </div>
      <div class="steps">
        <article class="step">
          <span class="step-number">1</span>
          <div><h3>Administrators prepare parcels</h3><p>Estate teams import approved survey information and manage availability.</p></div>
        </article>
        <article class="step">
          <span class="step-number">2</span>
          <div><h3>Allottees receive invitations</h3><p>Each invitation is associated with a specific property allocation and recipient.</p></div>
        </article>
        <article class="step">
          <span class="step-number">3</span>
          <div><h3>Authorized users view records</h3><p>Users can review only the property and boundary details linked to them.</p></div>
        </article>
      </div>
    </section>
  </main>
  ${publicFooter()}`;
}
