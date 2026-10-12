export const data = {
  estate: {
    name: "Marbella Luxury Estate",
    location: "Ibeju-Lekki, Lagos",
    state: "Lagos",
    lga: "Ibeju-Lekki",
    parcels: 250,
    allocated: 183,
    available: 67,
  },
  parcels: [
    {
      plot: "A-001",
      block: "A",
      status: "Allocated",
      person: "Chiamaka Okoro",
      area: "612 m²",
      updated: "08 Oct 2026",
    },
    {
      plot: "A-002",
      block: "A",
      status: "Allocated",
      person: "Tunde Adebayo",
      area: "598 m²",
      updated: "07 Oct 2026",
    },
    {
      plot: "A-003",
      block: "A",
      status: "Available",
      person: "—",
      area: "625 m²",
      updated: "07 Oct 2026",
    },
    {
      plot: "A-004",
      block: "A",
      status: "Pending",
      person: "Ngozi Eze",
      area: "604 m²",
      updated: "06 Oct 2026",
    },
    {
      plot: "A-005",
      block: "A",
      status: "Allocated",
      person: "Ifeanyi Umeh",
      area: "620 m²",
      updated: "05 Oct 2026",
    },
    {
      plot: "B-011",
      block: "B",
      status: "Available",
      person: "—",
      area: "640 m²",
      updated: "03 Oct 2026",
    },
  ],
  invitations: [
    {
      recipient: "Ngozi Eze",
      email: "ngozi.eze@example.com",
      parcel: "A-004",
      status: "Pending",
      sent: "06 Oct 2026",
      expiry: "13 Oct 2026",
    },
    {
      recipient: "Chiamaka Okoro",
      email: "chiamaka.okoro@example.com",
      parcel: "A-001",
      status: "Accepted",
      sent: "12 Sep 2026",
      expiry: "19 Sep 2026",
    },
    {
      recipient: "Seyi Adekunle",
      email: "seyi.a@example.com",
      parcel: "B-009",
      status: "Expired",
      sent: "18 Sep 2026",
      expiry: "25 Sep 2026",
    },
  ],
};

export const currentEndpoint = window.location.pathname.includes("/admin/")
  ? "admin"
  : window.location.pathname.includes("/property/")
    ? "property"
    : "public";

export const state = {
  view:
    currentEndpoint === "admin"
      ? "admin"
      : currentEndpoint === "property"
        ? "auth"
        : "public",
  adminPage: "overview",
  userPage: "property",
  propertyTab: "overview",
  authMode: "signin",
  modal: null,
  allocationStep: 1,
  selectedParcel: data.parcels[2],
  toast: "",
};
