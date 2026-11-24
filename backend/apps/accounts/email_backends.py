"""Django email backend for Resend's HTTPS API.

Render Free blocks outbound SMTP ports. Resend accepts transactional mail over
HTTPS instead, which lets the application continue to use Django's standard
``send_mail`` and password-reset workflows without storing an SMTP password.
"""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import sanitize_address


class ResendEmailError(OSError):
    """An email was not accepted by Resend's API."""


class ResendEmailBackend(BaseEmailBackend):
    """Deliver Django ``EmailMessage`` instances through Resend over HTTPS."""

    endpoint = "https://api.resend.com/emails"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_key = os.environ.get("RESEND_API_KEY", "").strip()
        self.endpoint = os.environ.get("RESEND_API_URL", self.endpoint).strip()
        self.timeout = float(os.environ.get("RESEND_TIMEOUT_SECONDS", "10"))

    @staticmethod
    def _addresses(addresses):
        return [sanitize_address(address, "utf-8") for address in addresses or ()]

    @staticmethod
    def _html_alternative(message):
        for alternative in getattr(message, "alternatives", ()):
            if hasattr(alternative, "content"):
                content, mimetype = alternative.content, alternative.mimetype
            else:
                content, mimetype = alternative
            if mimetype == "text/html":
                return content
        return None

    def _payload(self, message):
        sender = message.from_email
        recipients = self._addresses(message.to)
        if not sender:
            raise ResendEmailError("A sender address is required for Resend email delivery.")
        if not recipients:
            raise ResendEmailError("At least one recipient is required for Resend email delivery.")
        if message.attachments:
            raise ResendEmailError("Attachments are not supported by the configured Resend email backend.")

        payload = {
            "from": sanitize_address(sender, "utf-8"),
            "to": recipients,
            "subject": message.subject,
            "text": message.body or "",
        }
        if message.cc:
            payload["cc"] = self._addresses(message.cc)
        if message.bcc:
            payload["bcc"] = self._addresses(message.bcc)
        if message.reply_to:
            payload["reply_to"] = self._addresses(message.reply_to)
        if html := self._html_alternative(message):
            payload["html"] = html
        return payload

    def _send(self, message):
        if not self.api_key:
            raise ResendEmailError("RESEND_API_KEY is not configured.")
        request = Request(
            self.endpoint,
            data=json.dumps(self._payload(message)).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "TerraLedger/1.0",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                if not 200 <= response.status < 300:
                    raise ResendEmailError(
                        f"Resend rejected the email with HTTP {response.status}."
                    )
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:500]
            raise ResendEmailError(
                f"Resend rejected the email with HTTP {error.code}: {detail}"
            ) from error
        except (URLError, TimeoutError) as error:
            raise ResendEmailError("Could not reach Resend's email API.") from error

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        sent_count = 0
        for message in email_messages:
            try:
                self._send(message)
            except ResendEmailError:
                if not self.fail_silently:
                    raise
            else:
                sent_count += 1
        return sent_count
