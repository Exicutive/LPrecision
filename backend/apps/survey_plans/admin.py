from django.contrib import admin

from .models import SurveyPlan, SurveyPlanVerificationEvent


admin.site.register(SurveyPlan)
admin.site.register(SurveyPlanVerificationEvent)
