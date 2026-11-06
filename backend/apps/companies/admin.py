from django.contrib import admin

from .models import Company, CompanyAdminInvitation, CompanyMembership


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "status", "created_at")
    search_fields = ("name", "code", "legal_name")
    list_filter = ("status",)


@admin.register(CompanyMembership)
class CompanyMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "role", "is_active", "created_at")
    list_filter = ("role", "is_active", "company")
    search_fields = ("user__email", "company__name")


admin.site.register(CompanyAdminInvitation)
