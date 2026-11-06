from django.urls import path

from . import views

urlpatterns = [
    path("companies/<int:company_id>/estates/<int:estate_id>/master-layouts/", views.company_estate_master_layouts, name="company-estate-master-layouts"),
    path("companies/<int:company_id>/master-layouts/<uuid:layout_id>/", views.company_master_layout_detail, name="company-master-layout-detail"),
    path("companies/<int:company_id>/master-layouts/<uuid:layout_id>/process/", views.company_master_layout_process, name="company-master-layout-process"),
    path("companies/<int:company_id>/master-layouts/<uuid:layout_id>/status/", views.company_master_layout_status, name="company-master-layout-status"),
    path("companies/<int:company_id>/master-layouts/<uuid:layout_id>/download/", views.company_master_layout_download, name="company-master-layout-download"),
    path("companies/<int:company_id>/master-layouts/<uuid:layout_id>/candidates/", views.company_master_layout_candidates, name="company-master-layout-candidates"),
    path("companies/<int:company_id>/master-layouts/<uuid:layout_id>/approve-candidates/", views.company_master_layout_approve_candidates, name="company-master-layout-approve-candidates"),
    path("companies/<int:company_id>/master-layouts/<uuid:layout_id>/reject-candidates/", views.company_master_layout_reject_candidates, name="company-master-layout-reject-candidates"),
]
