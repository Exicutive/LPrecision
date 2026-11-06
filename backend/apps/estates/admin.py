from django.contrib import admin

from .models import Estate


@admin.register(Estate)
class EstateAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "code", "state", "status", "is_active", "updated_at")
    search_fields = ("name", "company__name", "code", "state")
    list_filter = ("company", "status", "is_active", "state")
