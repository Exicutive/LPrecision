from django.contrib import admin

from .models import Allocation, AllocationInvitation, PropertyInvitation


@admin.register(Allocation)
class AllocationAdmin(admin.ModelAdmin):
    list_display = ("reference", "parcel", "allottee", "status", "allocated_at")
    search_fields = ("reference", "parcel__plot_number", "allottee__email")
    list_filter = ("status",)


admin.site.register(AllocationInvitation)
admin.site.register(PropertyInvitation)
