from django.urls import path

from . import views

urlpatterns = [
    path("companies/<int:company_id>/survey-plans/", views.company_survey_plans, name="company-survey-plans"),
    path("companies/<int:company_id>/survey-plans/<uuid:survey_plan_id>/", views.company_survey_plan_detail, name="company-survey-plan-detail"),
    path("companies/<int:company_id>/survey-plans/<uuid:survey_plan_id>/verify/", views.company_survey_plan_verify, name="company-survey-plan-verify"),
    path("companies/<int:company_id>/survey-plans/<uuid:survey_plan_id>/download/", views.company_survey_plan_download, name="company-survey-plan-download"),
    path("my-property/<int:allocation_id>/survey-plans/<uuid:survey_plan_id>/", views.recipient_survey_plan_detail, name="recipient-survey-plan-detail"),
    path("my-property/<int:allocation_id>/survey-plans/<uuid:survey_plan_id>/download/", views.recipient_survey_plan_download, name="recipient-survey-plan-download"),
]
