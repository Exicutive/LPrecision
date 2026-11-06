from django.contrib import admin

from .models import Parcel


@admin.register(Parcel)
class ParcelAdmin(admin.ModelAdmin):
    list_display = ("plot_number", "estate", "block", "status", "area_sqm", "updated_at")
    search_fields = ("plot_number", "block", "estate__name")
    list_filter = ("status", "estate")
