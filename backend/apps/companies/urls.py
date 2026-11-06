from django.urls import path

from . import views

urlpatterns = [
    path("company-admin-invitations/status/", views.company_admin_invitation_status, name="company-admin-invitation-status"),
    path("company-admin-invitations/accept/", views.accept_company_admin_invitation, name="accept-company-admin-invitation"),
    path("companies/<int:company_id>/dashboard/", views.company_dashboard, name="company-dashboard"),
    path("companies/<int:company_id>/settings/", views.company_settings, name="company-settings"),
]
