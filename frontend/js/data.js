export const data = {
  estates: [],
  parcels: [],
  allocations: [],
  companies: [],
  auditEvents: [],
  platformSummary: null,
  companySummary: null,
  estateOverview: null,
  estateDetail: null,
  masterLayouts: [],
  masterLayoutDetail: null,
  extractionCandidates: [],
  surveyPlans: [],
  surveyPlanSummary: { total: 0, pending: 0, verified: 0, disputed: 0 },
  settings: {},
  companySettings: null,
  notificationPreferences: {},
};

export const currentEndpoint = window.location.pathname.includes("/admin/")
  ? "admin"
  : window.location.pathname.includes("/property/")
    ? "property"
    : "public";

export const state = {
  view:
    currentEndpoint === "admin"
      ? "auth"
      : currentEndpoint === "property"
      ? (new URLSearchParams(window.location.search).has("company_admin_invitation")
        || new URLSearchParams(window.location.search).has("allocation_invitation")) ? "invite" : "auth"
      : "public",
  adminPage: "overview",
  settingsSection: "company-information",
  adminRole: null,
  activeCompanyId: null,
  userPage: "properties",
  user: null,
  propertyAllocations: [],
  propertyDetail: null,
  selectedAllocationId: null,
  propertyTab: "overview",
  authMode: "signin",
  passwordResetNotice: "",
  modal: null,
  invitationCompanyId: null,
  latestCompanyAdminInvitation: null,
  companyAdminInvitationToken: new URLSearchParams(window.location.search).get("company_admin_invitation"),
  allocationInvitationToken: new URLSearchParams(window.location.search).get("allocation_invitation"),
  allocationInvitation: null,
  companyAdminInvitation: null,
  invitationLoading: new URLSearchParams(window.location.search).has("company_admin_invitation")
    || new URLSearchParams(window.location.search).has("allocation_invitation"),
  invitationError: "",
  invitationAccepted: false,
  allocationStep: 1,
  selectedParcel: null,
  selectedEstateId: null,
  editingEstate: null,
  estateSearch: "",
  estateStatusFilter: "all",
  estateDetailTab: "overview",
  masterLayoutFileName: "",
  candidateSearch: "",
  candidateStatusFilter: "all",
  selectedCandidateIds: [],
  surveyPlanSearch: "",
  surveyPlanStatusFilter: "all",
  surveyPlanEstateFilter: "all",
  surveyPlanBlockFilter: "",
  surveyPlanDateFilter: "",
  selectedSurveyPlanId: null,
  surveyPlanAllocationId: null,
  propertyAllocation: null,
  recordsLoading: false,
  adminAuthorized: false,
  toast: "",
};
