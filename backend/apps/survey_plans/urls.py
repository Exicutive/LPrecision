from django.urls import path

from . import views

urlpatterns = [
    path("my-property/<int:allocation_id>/boundary/", views.recipient_boundary_update, name="recipient-boundary-update"),
    path("my-property/<int:allocation_id>/survey-plans/", views.recipient_survey_plan_upload, name="recipient-survey-plan-upload"),
    path("my-property/<int:allocation_id>/survey-plans/<uuid:survey_plan_id>/", views.recipient_survey_plan_detail, name="recipient-survey-plan-detail"),
    path("my-property/<int:allocation_id>/survey-plans/<uuid:survey_plan_id>/download/", views.recipient_survey_plan_download, name="recipient-survey-plan-download"),
]
