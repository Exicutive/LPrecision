from django.urls import path

from . import views

urlpatterns = [
    path("parcels/", views.parcels, name="parcels"),
    path("companies/<int:company_id>/parcels/", views.company_parcels, name="company-parcels"),
]
