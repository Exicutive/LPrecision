from django.urls import path

from . import views

urlpatterns = [
    path("platform/dashboard/", views.platform_dashboard, name="platform-dashboard"),
    path("platform/companies/", views.platform_companies, name="platform-companies"),
    path("platform/companies/register/", views.platform_register_company, name="platform-register-company"),
    path("platform/companies/<int:company_id>/", views.platform_company_detail, name="platform-company-detail"),
    path("platform/companies/<int:company_id>/invite-first-admin/", views.platform_invite_first_company_admin, name="platform-invite-first-company-admin"),
    path("platform/companies/<int:company_id>/<str:status>/", views.platform_company_status, name="platform-company-status"),
    path("platform/settings/", views.platform_settings, name="platform-settings"),
    path("platform/audit-events/", views.platform_audit_events, name="platform-audit-events"),
]
