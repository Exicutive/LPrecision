from django.http import JsonResponse

from apps.companies.models import CompanyMembership
from apps.platform_admin.models import PlatformAdministrator, PlatformAuditEvent


def is_platform_admin(user):
    return bool(user.is_authenticated and (
        user.is_superuser
        or PlatformAdministrator.objects.filter(user=user, is_active=True).exists()
    ))


def platform_admin_required(request):
    if is_platform_admin(request.user):
        return None
    return JsonResponse({"detail": "Platform administrator access is required."}, status=403)


def company_admin_required(request, company_id):
    membership = CompanyMembership.objects.filter(
        company_id=company_id,
        user=request.user,
        role=CompanyMembership.Role.COMPANY_ADMIN,
        is_active=True,
        company__status="active",
    ).select_related("company").first()
    return membership or None


def log_event(*, actor, action, company=None, details=None):
    return PlatformAuditEvent.objects.create(
        actor=actor, company=company, action=action, details=details or {}
    )
