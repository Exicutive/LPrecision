"""Compatibility URL aggregator preserving the existing /api/records/ API."""

from django.urls import include, path

urlpatterns = [
    path("", include("apps.companies.urls")),
    path("", include("apps.platform_admin.urls")),
    path("", include("apps.master_layouts.urls")),
    path("", include("apps.estates.urls")),
    path("", include("apps.parcels.urls")),
    path("", include("apps.allocations.urls")),
    path("", include("apps.survey_plans.urls")),
]
