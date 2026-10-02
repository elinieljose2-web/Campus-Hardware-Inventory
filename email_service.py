import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv


load_dotenv()

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
BREVO_API_KEY = os.getenv("BREVO_API_KEY", "").strip()
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "").strip()
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "").strip()


class EmailConfigurationError(RuntimeError):
    pass


class EmailDeliveryError(RuntimeError):
    pass


def refresh_brevo_config():
    """Load the current Brevo settings from the environment."""
    global BREVO_API_KEY, BREVO_SENDER_EMAIL, BREVO_SENDER_NAME

    load_dotenv()

    BREVO_API_KEY = os.getenv("BREVO_API_KEY", "").strip()
    BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "").strip()
    BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "").strip()


def email_service_configured():
    refresh_brevo_config()
    return all((BREVO_API_KEY, BREVO_SENDER_EMAIL, BREVO_SENDER_NAME))


def send_brevo_email(recipient_email, subject, text_content, html_content):
    refresh_brevo_config()

    missing_settings = [
        name
        for name, value in (
            ("BREVO_API_KEY", BREVO_API_KEY),
            ("BREVO_SENDER_EMAIL", BREVO_SENDER_EMAIL),
            ("BREVO_SENDER_NAME", BREVO_SENDER_NAME),
        )
        if not value
    ]
    if missing_settings:
        raise EmailConfigurationError(
            "Missing required environment variables: " + ", ".join(missing_settings)
        )

    payload = {
        "sender": {"email": BREVO_SENDER_EMAIL, "name": BREVO_SENDER_NAME},
        "to": [{"email": recipient_email}],
        "subject": subject,
        "textContent": text_content,
        "htmlContent": html_content,
    }
    api_request = Request(
        BREVO_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "api-key": BREVO_API_KEY,
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(api_request, timeout=10) as response:
            if 200 <= response.status < 300:
                return
            raise EmailDeliveryError(
                f"Brevo rejected the email request (HTTP {response.status})."
            )
    except HTTPError as error:
        raise EmailDeliveryError(
            f"Brevo rejected the email request (HTTP {error.code})."
        ) from None
    except (URLError, TimeoutError, OSError):
        raise EmailDeliveryError("Could not connect to Brevo to send the email.") from None
