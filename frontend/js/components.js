const icon = `<svg
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  stroke-width="1.8"
  aria-hidden="true"
>
  <path d="M4 20V9l8-5 8 5v11M8 20v-7h8v7" />
  <path d="M17 4v4" />
</svg>`;

const icons = {
  arrow: `<path d="M5 12h14M13 6l6 6-6 6" />`,
  dashboard: `<rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><rect x="14" y="14" width="6" height="6" rx="1"/>`,
  estate: `<path d="m3 10 9-7 9 7v10H3zM9 20v-6h6v6"/>`,
  parcel: `<path d="m4 6 5-3 6 3 5-2v14l-5 3-6-3-5 2zM9 3v14m6-11v14"/>`,
  allocation: `<path d="M7 17 17 7M9 7h8v8"/><path d="M5 4h5M4 4v5M19 20h-5m5 0v-5"/>`,
  survey: `<path d="m4 7 8-4 8 4-8 4zM4 12l8 4 8-4M4 17l8 4 8-4"/>`,
  settings: `<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.8 1.8 0 0 0 .36 2l.06.06-2.13 2.13-.06-.06a1.8 1.8 0 0 0-2-.36 1.8 1.8 0 0 0-1.1 1.65v.08h-3.02v-.08a1.8 1.8 0 0 0-1.1-1.65 1.8 1.8 0 0 0-2 .36l-.06.06-2.13-2.13.06-.06a1.8 1.8 0 0 0 .36-2 1.8 1.8 0 0 0-1.65-1.1H5v-3.02h.08a1.8 1.8 0 0 0 1.65-1.1 1.8 1.8 0 0 0-.36-2l-.06-.06 2.13-2.13.06.06a1.8 1.8 0 0 0 2 .36 1.8 1.8 0 0 0 1.1-1.65V3.5h3.02v.08a1.8 1.8 0 0 0 1.1 1.65 1.8 1.8 0 0 0 2-.36l.06-.06 2.13 2.13-.06.06a1.8 1.8 0 0 0-.36 2 1.8 1.8 0 0 0 1.65 1.1H19v3.02h-.08A1.8 1.8 0 0 0 17.27 15Z"/>`,
  document: `<path d="M6 3h8l4 4v14H6zM14 3v5h5M9 13h6M9 17h6"/>`,
  shield: `<path d="M12 3 19 6v5c0 4.6-3 8-7 10-4-2-7-5.4-7-10V6z"/><path d="m9 12 2 2 4-4"/>`,
  check: `<path d="m5 12 4 4L19 6"/>`,
  records: `<path d="M5 4h14v16H5zM8 8h8M8 12h8M8 16h5"/>`,
};

export function uiIcon(name, extra = "") {
  const paths = icons[name] || icons.records;
  return `<svg class="ui-icon ${extra}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;
}

export function status(value) {
  return `<span class="status ${value.toLowerCase().replace(/\s+/g, "-")}">${value}</span>`;
}

export function button(text, action, kind = "secondary", extra = "") {
  return `<button type="button" class="button ${kind} ${extra}" data-action="${action}">${text}</button>`;
}

export function brand() {
  return /* HTML */ `<span class="brand-mark">${icon}</span>
    <span class="brand-copy">
      <small>Land records portal</small>
      <strong>TerraLedger</strong>
    </span>`;
}

export function parcelSvg(dark = false) {
  const stroke = dark ? "#d9f8e6" : "#0c725e";
  const fill = dark ? "rgba(185,228,106,.26)" : "rgba(86,187,143,.20)";
  const text = dark ? "#fff" : "#094c3d";

  return /* HTML */ `<svg
    class="boundary-svg"
    viewBox="0 0 560 330"
    preserveAspectRatio="xMidYMid meet"
    role="img"
    aria-label="Boundary data placeholder"
  >
    <polygon
      points="100,65 440,65 475,240 135,275 65,190"
      fill="${fill}"
      stroke="${stroke}"
      stroke-width="4"
    />
    <g fill="${stroke}" stroke="#fff" stroke-width="3">
      <circle cx="100" cy="65" r="8" />
      <circle cx="440" cy="65" r="8" />
      <circle cx="490" cy="240" r="8" />
      <circle cx="132" cy="287" r="8" />
      <circle cx="58" cy="182" r="8" />
    </g>
    <text x="160" y="165" fill="${text}" font-size="18" font-weight="700">Boundary data loads from an approved record</text>
  </svg>`;
}
