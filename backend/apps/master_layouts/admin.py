from django.contrib import admin

from .models import EstateMasterPlan, ExtractedParcelCandidate, MasterLayoutProcessingJob


admin.site.register(EstateMasterPlan)
admin.site.register(MasterLayoutProcessingJob)
admin.site.register(ExtractedParcelCandidate)
