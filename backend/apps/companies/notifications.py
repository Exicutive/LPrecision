import logging
import smtplib

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from apps.companies.models import Company, CompanyMembership
from apps.platform_admin.permissions import log_event


logger = logging.getLogger(__name__)

NOTIFICATION_TYPES = {
    "property_allocation": "Property allocation notifications",
    "survey_plan_upload": "Survey plan upload notifications",
    "survey_plan_verification": "Survey plan verification notifications",
    "master_layout_processing": "Master layout processing notifications",
}


def schedule_company_notification(*, company_id, notification_type, subject, message):
    if notification_type not in NOTIFICATION_TYPES:
        raise ValueError(f"Unknown company notification type: {notification_type}")
    transaction.on_commit(
        lambda: _deliver_company_notification(
            company_id=company_id,
            notification_type=notification_type,
            subject=subject,
            message=message,
        ),
        robust=True,
    )


def _deliver_company_notification(*, company_id, notification_type, subject, message):
    company = Company.objects.filter(pk=company_id).first()
    if not company:
        return
    preferences = company.settings.get("notification_preferences", {})
    if not isinstance(preferences, dict) or preferences.get(notification_type) is not True:
        return
    recipients = list(
        CompanyMembership.objects.filter(
            company=company,
            role=CompanyMembership.Role.COMPANY_ADMIN,
            is_active=True,
            company__status=Company.Status.ACTIVE,
        )
        .exclude(user__email="")
        .values_list("user__email", flat=True)
    )
    if not recipients:
        return
    try:
        delivered = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipients,
            fail_silently=False,
        )
        if delivered != 1:
            raise RuntimeError("The email provider did not accept the notification.")
    except (OSError, smtplib.SMTPException, RuntimeError):
        logger.exception(
            "Company notification delivery failed for company %s (%s).",
            company_id,
            notification_type,
        )
        log_event(
            actor=None,
            action="company_notification.delivery_failed",
            company=company,
            details={"notification_type": notification_type},
        )
