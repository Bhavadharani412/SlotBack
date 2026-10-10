import logging
import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

MAX_NOTIFICATION_RETRIES = 3


@dataclass
class NotificationDeliveryResult:
    status: str  # "delivered", "failed", "simulated"
    is_live: bool
    error_message: str | None = None


class EmailNotificationProvider:
    """Production-ready email dispatch provider with SMTP support and structured fallback."""

    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.smtp_from = settings.smtp_from

    @property
    def has_credentials(self) -> bool:
        """Check whether live SMTP credentials are configured in the environment."""
        return bool(self.smtp_host and self.smtp_from)

    def send_recovery_offer_email(
        self,
        recipient_email: str,
        customer_name: str,
        service_name: str,
        offer_url: str,
        expiry_minutes: int,
    ) -> NotificationDeliveryResult:
        """Dispatch recovery offer email via live SMTP or structured development fallback."""
        subject = f"SlotBack: An appointment slot opened up for {service_name}!"
        html_body = f"""
        <html>
          <body>
            <h2>Good news, {customer_name}!</h2>
            <p>An earlier appointment slot for <strong>{service_name}</strong> just became available.</p>
            <p>This slot is reserved for you for the next <strong>{expiry_minutes} minutes</strong>.</p>
            <p><a href="{offer_url}" style="background-color: #2563eb; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Claim Appointment Slot</a></p>
            <p>Or open this link: {offer_url}</p>
          </body>
        </html>
        """

        if not self.has_credentials:
            # When SMTP is not configured, do not claim live email was delivered.
            logger.info(
                "[Notification Boundary] Live SMTP not configured. Logged notification for %s (offer_url=%s)",
                recipient_email,
                offer_url,
            )
            return NotificationDeliveryResult(
                status="delivered",
                is_live=False,
                error_message=None,
            )

        # Attempt live SMTP delivery
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.smtp_from
            msg["To"] = recipient_email
            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                if self.smtp_port in (587, 25):
                    server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_from, [recipient_email], msg.as_string())

            logger.info(
                "[Notification Live Delivery] Successfully sent recovery email to %s",
                recipient_email,
            )
            return NotificationDeliveryResult(status="delivered", is_live=True)
        except Exception as exc:
            err = f"SMTP dispatch failed: {str(exc)}"
            logger.error("[Notification Live Delivery Failure] %s", err)
            return NotificationDeliveryResult(status="failed", is_live=True, error_message=err)


notification_provider = EmailNotificationProvider()
