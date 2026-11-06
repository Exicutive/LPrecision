from django.urls import path

from . import views

urlpatterns = [
    path("estates/", views.estates, name="estates"),
    path("companies/<int:company_id>/estates/overview/", views.company_estates_overview, name="company-estates-overview"),
    path("companies/<int:company_id>/estates/", views.company_estates, name="company-estates"),
    path("companies/<int:company_id>/estates/<int:estate_id>/", views.company_estate_detail, name="company-estate-detail"),
    path("companies/<int:company_id>/estates/<int:estate_id>/<str:status>/", views.company_estate_status, name="company-estate-status"),
]
