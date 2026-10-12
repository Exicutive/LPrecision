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

export function status(value) {
  return `<span class="status ${value.toLowerCase()}">${value}</span>`;
}

export function button(text, action, kind = "secondary", extra = "") {
  return `<button class="button ${kind} ${extra}" data-action="${action}">${text}</button>`;
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
    aria-label="Demonstration surveyed parcel boundary"
  >
    <polygon
      points="95,53 440,31 490,240 132,287 58,182"
      fill="${fill}"
      stroke="${stroke}"
      stroke-width="4"
    />
    <g fill="${stroke}" stroke="#fff" stroke-width="3">
      <circle cx="95" cy="53" r="8" />
      <circle cx="440" cy="31" r="8" />
      <circle cx="490" cy="240" r="8" />
      <circle cx="132" cy="287" r="8" />
      <circle cx="58" cy="182" r="8" />
    </g>
    <g fill="${text}" font-size="13" font-weight="700">
      <text x="72" y="38">B1</text>
      <text x="446" y="24">B2</text>
      <text x="499" y="253">B3</text>
      <text x="122" y="309">B4</text>
      <text x="33" y="180">B5</text>
      <text x="226" y="158" font-size="25">PLOT A-003</text>
      <text x="237" y="180" font-size="13">625 m²</text>
    </g>
    <g fill="${text}" font-size="11">
      <text x="245" y="38">42.73 m</text>
      <text x="462" y="146">31.84 m</text>
      <text x="294" y="275">39.17 m</text>
    </g>
  </svg>`;
}
