from django.contrib import admin

from .models import PlatformAdministrator, PlatformAuditEvent, PlatformSetting


@admin.register(PlatformAdministrator)
class PlatformAdministratorAdmin(admin.ModelAdmin):
    list_display = ("user", "is_active", "created_at")
    search_fields = ("user__email", "user__username")


admin.site.register(PlatformSetting)
admin.site.register(PlatformAuditEvent)
