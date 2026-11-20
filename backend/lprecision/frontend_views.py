"""Safe same-origin delivery for the browser application and user images."""

from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse
from django.views.decorators.http import require_GET

from apps.allocations.models import Allocation
from apps.companies.models import Company, CompanyMembership
from apps.estates.models import Estate
from apps.platform_admin.permissions import is_platform_admin


FRONTEND_ROOT = settings.BASE_DIR.parent / "frontend"
FRONTEND_PAGES = {
    "public": FRONTEND_ROOT / "index.html",
    "property": FRONTEND_ROOT / "property" / "index.html",
    "workspace": FRONTEND_ROOT / "admin" / "index.html",
}


@require_GET
def healthz(request):
    """Lightweight process-health response for Render's HTTP health check."""
    return JsonResponse({"status": "ok"})


@require_GET
def frontend_page(request, page):
    try:
        page_path = FRONTEND_PAGES[page]
    except KeyError as error:
        raise Http404 from error
    response = FileResponse(page_path.open("rb"), content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "no-store"
    return response


def _can_access_company(request, company_id):
    return request.user.is_authenticated and (
        is_platform_admin(request.user)
        or CompanyMembership.objects.filter(
            company_id=company_id, user=request.user, is_active=True
        ).exists()
    )


def _can_access_estate(request, estate):
    return _can_access_company(request, estate.company_id) or (
        request.user.is_authenticated
        and Allocation.objects.filter(
            allottee=request.user,
            parcel__estate=estate,
            status=Allocation.Status.ACTIVE,
        ).exists()
    )


def _private_file_response(field_file):
    response = FileResponse(field_file.open("rb"), as_attachment=False)
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@require_GET
def company_logo(request, filename):
    company = Company.objects.filter(logo=f"company-logos/{filename}").first()
    if not company or not _can_access_company(request, company.pk):
        raise Http404
    return _private_file_response(company.logo)


@require_GET
def estate_image(request, filename):
    estate = Estate.objects.select_related("company").filter(
        image=f"estate-images/{filename}"
    ).first()
    if not estate or not _can_access_estate(request, estate):
        raise Http404
    return _private_file_response(estate.image)
