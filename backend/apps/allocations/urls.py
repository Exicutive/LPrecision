from django.urls import path

from . import views

urlpatterns = [
    path("allocations/", views.allocations, name="allocations"),
    path("my-property/", views.my_property, name="my-property"),
    path("my-property/<int:allocation_id>/", views.my_property_detail, name="my-property-detail"),
    path("allocation-invitations/status/", views.allocation_invitation_status, name="allocation-invitation-status"),
    path("allocation-invitations/accept/", views.accept_allocation_invitation, name="accept-allocation-invitation"),
    path("companies/<int:company_id>/allocations/", views.company_allocations, name="company-allocations"),
    path("companies/<int:company_id>/allocations/<int:allocation_id>/resend-invitation/", views.resend_allocation_invitation, name="resend-allocation-invitation"),
    path("companies/<int:company_id>/allocations/<int:allocation_id>/revoke/", views.revoke_allocation, name="revoke-allocation"),
    path("companies/<int:company_id>/property-invitations/", views.company_property_invitation, name="company-property-invitations"),
]
