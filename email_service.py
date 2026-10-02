import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv


BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


class EmailConfigurationError(RuntimeError):
    pass


class EmailDeliveryError(RuntimeError):
    pass


def send_brevo_email(recipient_email, subject, text_content, html_content):
    load_dotenv()

    api_key = os.getenv("BREVO_API_KEY", "").strip()
    sender_email = os.getenv("BREVO_SENDER_EMAIL", "").strip()
    sender_name = os.getenv("BREVO_SENDER_NAME", "").strip()
    missing_settings = [
        name
        for name, value in (
            ("BREVO_API_KEY", api_key),
            ("BREVO_SENDER_EMAIL", sender_email),
            ("BREVO_SENDER_NAME", sender_name),
        )
        if not value
    ]
    if missing_settings:
        raise EmailConfigurationError(
            "Missing required environment variables: " + ", ".join(missing_settings)
        )

    payload = {
        "sender": {"email": sender_email, "name": sender_name},
        "to": [{"email": recipient_email}],
        "subject": subject,
        "textContent": text_content,
        "htmlContent": html_content,
    }
    api_request = Request(
        BREVO_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "api-key": api_key,
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
