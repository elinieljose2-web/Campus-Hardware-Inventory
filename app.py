from flask import Flask
from functools import wraps

import csv
import io
import json
import logging
import os
import re
import secrets

from datetime import datetime, timedelta, timezone
from math import ceil
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import generate_password_hash

from controllers.auth_controller import AuthController
from controllers.hardware_controller import HardwareController


# ---------------------------------------------------------------------------
# Environment / Application Configuration
# ---------------------------------------------------------------------------

load_dotenv()

app = Flask(__name__)

FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "").strip()

# Use the configured secret when available.
# Otherwise generate a temporary secret for local development.
app.secret_key = FLASK_SECRET_KEY or secrets.token_hex(32)

auth_controller = AuthController()
hw_controller = HardwareController()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Brevo Email Configuration
# ---------------------------------------------------------------------------

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "").strip()
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", "").strip()
BREVO_SENDER_NAME = os.getenv("BREVO_SENDER_NAME", "").strip()


# Safe diagnostic information.
# IMPORTANT: Never print the actual API key.
logger.info(
    "Brevo configuration: key_loaded=%s, key_length=%d, sender_email=%s, sender_name=%s",
    bool(BREVO_API_KEY),
    len(BREVO_API_KEY),
    BREVO_SENDER_EMAIL or "<missing>",
    BREVO_SENDER_NAME or "<missing>",
)


# ---------------------------------------------------------------------------
# OTP Configuration
# ---------------------------------------------------------------------------

OTP_LIFETIME = timedelta(minutes=10)
OTP_RESEND_COOLDOWN = timedelta(seconds=60)
OTP_MAX_ATTEMPTS = 5


def email_service_configured():
    """Return True when all required Brevo configuration is available."""
    return all(
        (
            BREVO_API_KEY,
            BREVO_SENDER_EMAIL,
            BREVO_SENDER_NAME,
        )
    )


def email_verification_configured():
    """
    Email verification only depends on the Brevo email configuration.

    Flask already has a secret key above, including a generated local
    development fallback, so FLASK_SECRET_KEY should not independently
    disable email verification.
    """
    return email_service_configured()


# ---------------------------------------------------------------------------
# Brevo Email Sending
# ---------------------------------------------------------------------------

def send_otp_email(recipient_email, otp, intent="Email verification"):
    """Send a verification or password-reset OTP through Brevo."""

    expiry_notice = (
        "It expires in 10 minutes."
        if intent == "Email verification"
        else "Use this code to continue."
    )

    return send_brevo_email(
        recipient_email,
        f"{intent} code - {BREVO_SENDER_NAME or 'Laboratory System'}",
        (
            f"Your {intent.lower()} code for "
            f"{BREVO_SENDER_NAME or 'Laboratory System'} is {otp}. "
            f"{expiry_notice} "
            "Do not share this code with anyone."
        ),
        (
            f"<p>Your {intent.lower()} code for "
            f"{BREVO_SENDER_NAME or 'Laboratory System'} is:</p>"
            f"<p style=\"font-size:28px;font-weight:bold;"
            f"letter-spacing:6px\">{otp}</p>"
            f"<p>{expiry_notice} Do not share this code with anyone.</p>"
        ),
    )


def send_brevo_email(recipient_email, subject, text_content, html_content):
    """Send a transactional email through Brevo's API."""

    if not email_service_configured():
        logger.error(
            "Brevo email is not configured. "
            "Check BREVO_API_KEY, BREVO_SENDER_EMAIL, and BREVO_SENDER_NAME."
        )
        return False

    payload = {
        "sender": {
            "email": BREVO_SENDER_EMAIL,
            "name": BREVO_SENDER_NAME,
        },
        "to": [
            {
                "email": recipient_email,
            }
        ],
        "subject": subject,
        "textContent": text_content,
        "htmlContent": html_content,
    }

    api_request = Request(
        BREVO_API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(api_request, timeout=30) as response:
            response_body = response.read().decode(
                "utf-8",
                errors="replace",
            )

            if 200 <= response.status < 300:
                logger.info(
                    "Brevo email sent successfully. HTTP %s.",
                    response.status,
                )
                return True

            logger.warning(
                "Brevo email API returned HTTP %s: %s",
                response.status,
                response_body,
            )

    except HTTPError as error:
        # Brevo's response body is extremely important when diagnosing
        # authentication, sender, payload, or account errors.
        response_body = error.read().decode(
            "utf-8",
            errors="replace",
        )

        logger.error(
            "Brevo email API returned HTTP %s: %s",
            error.code,
            response_body,
        )

    except URLError as error:
        logger.error(
            "Could not connect to Brevo email API: %s",
            error.reason,
        )

    except TimeoutError:
        logger.error(
            "Brevo email API request timed out."
        )

    except OSError as error:
        logger.error(
            "Brevo email API request failed: %s",
            error,
        )

    return False


# ---------------------------------------------------------------------------
# OTP Helpers
# ---------------------------------------------------------------------------

def _hash_otp(otp):
    return generate_password_hash(otp)


def _utc_now():
    return datetime.now(timezone.utc)


def _verification_page(username):
    status = auth_controller.get_email_verification_status(username)

    if not status:
        session.pop("email_verification_username", None)
        flash(
            "That account could not be found. Please register again.",
            "warning",
        )
        return redirect(url_for("register"))

    if status["email_verified"]:
        session.pop("email_verification_username", None)
        flash(
            "This email address is already verified. Please log in.",
            "info",
        )
        return redirect(url_for("login"))

    now = _utc_now()

    expires_at = (
        datetime.fromisoformat(status["otp_expires_at"])
        if status["otp_expires_at"]
        else None
    )

    sent_at = (
        datetime.fromisoformat(status["otp_last_sent_at"])
        if status["otp_last_sent_at"]
        else None
    )

    expires_in = (
        max(0, ceil((expires_at - now).total_seconds()))
        if expires_at
        else 0
    )

    resend_wait = (
        max(
            0,
            ceil(
                (
                    sent_at
                    + OTP_RESEND_COOLDOWN
                    - now
                ).total_seconds()
            ),
        )
        if sent_at
        else 0
    )

    return render_template(
        "otp_verify.html",
        action_url=url_for("verify_email"),
        resend_url=url_for("resend_verification_otp"),
        email_verification=True,
        expires_in_seconds=expires_in,
        resend_wait_seconds=resend_wait,
        attempts_remaining=max(
            0,
            OTP_MAX_ATTEMPTS - status["otp_attempts"],
        ),
    )


def _handle_auth_storage_error(action):
    logger.exception(
        "User data storage failed while %s.",
        action,
    )

    flash(
        "We could not access your account data. Please try again later.",
        "danger",
    )

    return redirect(url_for("login"))


def _send_registration_otp(username, recipient_email, otp, now):
    expires_at = (now + OTP_LIFETIME).isoformat()

    if not auth_controller.set_email_otp(
        username,
        _hash_otp(otp),
        expires_at,
        now.isoformat(),
    ):
        return False

    if send_otp_email(recipient_email, otp):
        return True

    auth_controller.clear_email_otp_cooldown(username)
    return False


# ---------------------------------------------------------------------------
# Authentication Decorators
# ---------------------------------------------------------------------------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "username" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("role", "STUDENT").upper() != "ADMIN":
            flash(
                "Administrator access required.",
                "danger",
            )
            return redirect(url_for("dashboard"))

        return view(*args, **kwargs)

    return wrapped


def student_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if session.get("role", "STUDENT").upper() != "STUDENT":
            flash(
                "Student access required.",
                "danger",
            )
            return redirect(url_for("dashboard"))

        return view(*args, **kwargs)

    return wrapped


# ---------------------------------------------------------------------------
# Authentication Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (
            request.form.get("username") or ""
        ).strip()

        password = (
            request.form.get("password") or ""
        ).strip()

        if not username or not password:
            flash(
                "Please enter both username and password.",
                "danger",
            )
            return render_template("login.html")

        ok, result = auth_controller.login_user(
            username,
            password,
        )

        if not ok:
            if result == (
                "Please verify your email address before logging in."
            ):
                session["email_verification_username"] = username

                flash(
                    "Please verify your email address to finish registration.",
                    "warning",
                )

                return redirect(url_for("verify_email"))

            flash(result, "danger")
            return render_template("login.html")

        session.clear()

        session["username"] = result["username"]
        session["role"] = result["role"]

        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    confirm_password = (
        request.form.get("confirm_password", "").strip()
    )
    recovery_keyword = (
        request.form.get("recovery_keyword", "").strip()
    )
    role = request.form.get("role", "").strip()

    if not all(
        (
            username,
            email,
            password,
            confirm_password,
            recovery_keyword,
        )
    ):
        flash(
            "All registration fields are required.",
            "danger",
        )
        return redirect(url_for("register"))

    if password != confirm_password:
        flash(
            "Passwords do not match.",
            "danger",
        )
        return redirect(url_for("register"))

    if not re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+",
        email,
    ):
        flash(
            "Please enter a valid email address.",
            "danger",
        )
        return redirect(url_for("register"))

    if not email_verification_configured():
        flash(
            "Email verification is not configured yet. "
            "Please try again later.",
            "danger",
        )
        return redirect(url_for("register"))

    now = _utc_now()

    otp = f"{secrets.randbelow(1_000_000):06d}"

    try:
        ok, message = auth_controller.register_pending_user(
            username,
            email,
            password,
            recovery_keyword,
            _hash_otp(otp),
            (now + OTP_LIFETIME).isoformat(),
            now.isoformat(),
            role=role,
        )

    except (OSError, json.JSONDecodeError):
        return _handle_auth_storage_error(
            "creating a pending account"
        )

    if not ok:
        flash(message, "danger")
        return redirect(url_for("register"))

    session["email_verification_username"] = username

    if send_otp_email(email, otp):
        flash(
            "We sent a 6-digit code to your email. "
            "It expires in 10 minutes.",
            "info",
        )
    else:
        try:
            auth_controller.clear_email_otp_cooldown(
                username
            )
        except (OSError, json.JSONDecodeError):
            return _handle_auth_storage_error(
                "preparing an OTP resend"
            )

        flash(
            "We couldn't send the verification email. "
            "Please try resending shortly.",
            "danger",
        )

    return redirect(url_for("verify_email"))


@app.route("/verify-email", methods=["GET", "POST"])
def verify_email():
    username = session.get(
        "email_verification_username"
    )

    if not username:
        flash(
            "Start registration or log in to continue email verification.",
            "warning",
        )
        return redirect(url_for("login"))

    if request.method == "POST":
        entered_otp = request.form.get(
            "otp_code",
            "",
        )

        try:
            result = auth_controller.verify_email_otp(
                username,
                (
                    entered_otp
                    if re.fullmatch(
                        r"[0-9]{6}",
                        entered_otp,
                    )
                    else ""
                ),
                _utc_now().isoformat(),
            )

        except (
            OSError,
            json.JSONDecodeError,
            ValueError,
        ):
            return _handle_auth_storage_error(
                "verifying an email address"
            )

        if result == "verified":
            session.pop(
                "email_verification_username",
                None,
            )

            flash(
                "Email verified. You can now log in.",
                "success",
            )

            return redirect(url_for("login"))

        if result == "already_verified":
            session.pop(
                "email_verification_username",
                None,
            )

            flash(
                "This email address is already verified. "
                "Please log in.",
                "info",
            )

            return redirect(url_for("login"))

        if result == "not_found":
            session.pop(
                "email_verification_username",
                None,
            )

            flash(
                "That account could not be found. "
                "Please register again.",
                "warning",
            )

            return redirect(url_for("register"))

        if result == "expired":
            flash(
                "That code has expired. "
                "Request a new verification code.",
                "danger",
            )

        elif result == "max_attempts":
            flash(
                "Too many incorrect attempts. "
                "Request a new code to continue.",
                "danger",
            )

        elif result == "no_code":
            flash(
                "There is no active code. "
                "Request a new verification code.",
                "danger",
            )

        else:
            flash(
                "That code is incorrect. "
                "Please check it and try again.",
                "danger",
            )

    try:
        return _verification_page(username)

    except (
        OSError,
        json.JSONDecodeError,
        ValueError,
    ):
        return _handle_auth_storage_error(
            "loading email verification"
        )


@app.route(
    "/resend-verification-otp",
    methods=["POST"],
)
def resend_verification_otp():
    username = session.get(
        "email_verification_username"
    )

    if not username:
        flash(
            "Start registration or log in to request a verification code.",
            "warning",
        )
        return redirect(url_for("login"))

    if not email_verification_configured():
        flash(
            "Email verification is not configured yet. "
            "Please try again later.",
            "danger",
        )
        return redirect(url_for("verify_email"))

    now = _utc_now()

    try:
        status = auth_controller.get_email_verification_status(
            username
        )

        if not status:
            session.pop(
                "email_verification_username",
                None,
            )

            flash(
                "That account could not be found. "
                "Please register again.",
                "warning",
            )

            return redirect(url_for("register"))

        if status["email_verified"]:
            session.pop(
                "email_verification_username",
                None,
            )

            flash(
                "This email address is already verified. "
                "Please log in.",
                "info",
            )

            return redirect(url_for("login"))

        sent_at = (
            datetime.fromisoformat(
                status["otp_last_sent_at"]
            )
            if status["otp_last_sent_at"]
            else None
        )

        if sent_at and now < (
            sent_at + OTP_RESEND_COOLDOWN
        ):
            wait_seconds = ceil(
                (
                    sent_at
                    + OTP_RESEND_COOLDOWN
                    - now
                ).total_seconds()
            )

            flash(
                f"Please wait {wait_seconds} seconds "
                "before requesting another code.",
                "warning",
            )

            return redirect(url_for("verify_email"))

        otp = f"{secrets.randbelow(1_000_000):06d}"

        if not _send_registration_otp(
            username,
            status["email"],
            otp,
            now,
        ):
            flash(
                "We couldn't send the verification email. "
                "Please try again shortly.",
                "danger",
            )

            return redirect(url_for("verify_email"))

    except (
        OSError,
        json.JSONDecodeError,
        ValueError,
    ):
        return _handle_auth_storage_error(
            "resending an email verification code"
        )

    flash(
        "A new verification code has been sent. "
        "It expires in 10 minutes.",
        "info",
    )

    return redirect(url_for("verify_email"))


# ---------------------------------------------------------------------------
# Password Reset
# ---------------------------------------------------------------------------

@app.route("/reset-request", methods=["GET", "POST"])
def reset_request():
    if request.method == "GET":
        return render_template("reset.html")

    username = request.form.get(
        "username",
        "",
    ).strip()

    email = request.form.get(
        "email",
        "",
    ).strip()

    recovery_keyword = request.form.get(
        "recovery_keyword",
        "",
    ).strip()

    new_password = request.form.get(
        "new_password",
        "",
    ).strip()

    confirm_password = request.form.get(
        "confirm_password",
        "",
    ).strip()

    if not all(
        (
            username,
            email,
            recovery_keyword,
            new_password,
            confirm_password,
        )
    ):
        flash(
            "All reset fields are required.",
            "danger",
        )
        return redirect(url_for("reset_request"))

    if new_password != confirm_password:
        flash(
            "New passwords do not match.",
            "danger",
        )
        return redirect(url_for("reset_request"))

    otp = f"{secrets.randbelow(1_000_000):06d}"

    session["pending_reset"] = {
        "username": username,
        "email": email,
        "recovery_keyword": recovery_keyword,
        "new_password": new_password,
        "otp": otp,
    }

    if send_otp_email(
        email,
        otp,
        intent="Password Reset",
    ):
        flash(
            "We sent a 6-digit code to your email. "
            "Please verify.",
            "info",
        )

        return redirect(
            url_for(
                "verify_otp",
                action="reset",
            )
        )

    flash(
        "Failed to send OTP email. Please try again.",
        "danger",
    )

    return redirect(url_for("reset_request"))


@app.route(
    "/verify-otp/<action>",
    methods=["GET", "POST"],
)
def verify_otp(action):
    if action == "register":
        return redirect(url_for("verify_email"))

    if action != "reset":
        return "Unknown verification action.", 404

    session_key = "pending_reset"

    if session_key not in session:
        flash(
            "Session expired. Please try again.",
            "warning",
        )
        return redirect(url_for("login"))

    if request.method == "POST":
        user_otp = request.form.get(
            "otp_code",
            "",
        ).strip()

        data = session[session_key]

        if user_otp == data["otp"]:
            ok, msg = auth_controller.reset_password(
                data["username"],
                data["email"],
                data["recovery_keyword"],
                data["new_password"],
            )

            session.pop(
                session_key,
                None,
            )

            flash(
                msg,
                "success" if ok else "danger",
            )

            return redirect(url_for("login"))

        flash(
            "Invalid OTP code. Try again.",
            "danger",
        )

    return render_template(
        "otp_verify.html",
        action_url=url_for(
            "verify_otp",
            action=action,
        ),
        email_verification=False,
    )


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    if session.get(
        "role",
        "STUDENT",
    ).upper() == "ADMIN":
        return redirect(
            url_for("admin_dashboard")
        )

    return redirect(
        url_for("student_dashboard")
    )


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    user = {
        "username": session.get(
            "username",
            "User",
        ),
        "role": "ADMIN",
    }

    metrics = hw_controller.get_dashboard_metrics()

    notification_count = len(
        hw_controller.get_notifications()
    )

    return render_template(
        "admin.html",
        user=user,
        metrics=metrics,
        notification_count=notification_count,
    )


@app.route("/student/dashboard")
@student_required
def student_dashboard():
    user = {
        "username": session.get(
            "username",
            "User",
        ),
        "role": "STUDENT",
    }

    return render_template(
        "student.html",
        user=user,
    )


@app.route("/logout")
def logout():
    session.clear()

    flash(
        "You have been logged out.",
        "success",
    )

    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Utility Parsers
# ---------------------------------------------------------------------------

def _parse_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Hardware API
# ---------------------------------------------------------------------------

@app.route("/api/hardware", methods=["GET"])
@login_required
def get_hardware():
    return jsonify(
        hw_controller.get_all_hardware()
    )


@app.route("/api/hardware/add", methods=["POST"])
@login_required
@admin_required
def add_hardware():
    data = request.get_json(
        silent=True
    ) or {}

    success = hw_controller.add_hardware(
        item_id=data.get(
            "id",
            "",
        ).strip(),

        name=data.get(
            "name",
            "",
        ).strip(),

        category=data.get(
            "category",
            "",
        ).strip(),

        stock_qty=_parse_int(
            data.get(
                "stock_qty",
                0,
            ),
            0,
        ),

        condition=data.get(
            "condition",
            "GOOD",
        ),

        admin_username=session["username"],

        unit_price=_parse_float(
            data.get(
                "unit_price",
                0,
            ),
            0.0,
        ),
    )

    return jsonify(
        {
            "success": (
                success is None
                or success is True
            )
        }
    )


@app.route("/api/hardware/update", methods=["POST"])
@login_required
@admin_required
def update_hardware():
    data = request.get_json(
        silent=True
    ) or {}

    success = hw_controller.update_hardware(
        item_id=data.get(
            "id",
            "",
        ).strip(),

        name=data.get(
            "name",
            "",
        ).strip(),

        category=data.get(
            "category",
            "",
        ).strip(),

        stock_qty=_parse_int(
            data.get(
                "stock_qty",
                0,
            ),
            0,
        ),

        condition=data.get(
            "condition",
            "GOOD",
        ),

        admin_username=session["username"],

        unit_price=_parse_float(
            data.get(
                "unit_price",
                0,
            ),
            0.0,
        ),
    )

    return jsonify(
        {
            "success": success
        }
    )


@app.route("/api/hardware/delete", methods=["POST"])
@login_required
@admin_required
def delete_hardware():
    data = request.get_json(
        silent=True
    ) or {}

    hw_controller.delete_hardware(
        data.get(
            "id",
            "",
        ).strip(),
        admin_username=session["username"],
    )

    return jsonify(
        {
            "success": True
        }
    )


# ---------------------------------------------------------------------------
# Reservation API
# ---------------------------------------------------------------------------

@app.route("/api/reserve", methods=["POST"])
@student_required
def reserve():
    data = request.get_json(
        silent=True
    ) or {}

    try:
        success = hw_controller.create_reservation(
            username=session["username"],

            hardware_id=data.get(
                "hardware_id",
                "",
            ).strip(),

            borrow_qty=_parse_int(
                data.get(
                    "borrow_qty",
                    1,
                ),
                1,
            ),

            borrow_date=data.get(
                "borrow_date",
                "",
            ),

            purpose=data.get(
                "purpose",
                "Student Reservation",
            ),

            instructor=data.get(
                "instructor",
                "",
            ),

            return_due_date=data.get(
                "return_due_date"
            ),

            transaction_id=(
                data.get(
                    "transaction_id"
                ) or ""
            ).strip() or None,
        )

    except Exception:
        logger.exception(
            "Failed to create reservation."
        )
        success = False

    return jsonify(
        {
            "success": success
        }
    )


# ---------------------------------------------------------------------------
# Requests API
# ---------------------------------------------------------------------------

@app.route("/api/requests", methods=["GET"])
@login_required
def get_requests():
    requests = hw_controller.get_all_requests()

    if session.get(
        "role",
        "STUDENT",
    ).upper() != "ADMIN":

        requests = [
            request_item
            for request_item in requests
            if request_item.get("username")
            == session["username"]
        ]

    return jsonify(requests)


@app.route(
    "/api/requests/update",
    methods=["POST"],
)
@login_required
@admin_required
def update_request():
    data = request.get_json(
        silent=True
    ) or {}

    record_id = _parse_int(
        data.get("record_id"),
        -1,
    )

    status = (
        data.get("status") or ""
    ).upper()

    if (
        record_id < 1
        or status not in {
            "APPROVED",
            "DECLINED",
        }
    ):
        return jsonify(
            {
                "success": False,
                "message": "Invalid request update.",
            }
        )

    success = hw_controller.update_request_status(
        record_id=record_id,
        new_status=status,
        admin_username=session["username"],
    )

    return jsonify(
        {
            "success": success
        }
    )


@app.route(
    "/api/requests/return",
    methods=["POST"],
)
@student_required
def request_return():
    data = request.get_json(
        silent=True
    ) or {}

    record_id = _parse_int(
        data.get("record_id"),
        -1,
    )

    if record_id < 1:
        return jsonify(
            {
                "success": False,
                "message": "Invalid request id.",
            }
        )

    success = hw_controller.request_return(
        record_id,
        session["username"],
    )

    return jsonify(
        {
            "success": success
        }
    )


@app.route(
    "/api/requests/complete-return",
    methods=["POST"],
)
@login_required
@admin_required
def complete_return():
    data = request.get_json(
        silent=True
    ) or {}

    record_id = _parse_int(
        data.get("record_id"),
        -1,
    )

    condition = (
        data.get("condition")
        or "GOOD"
    ).strip().upper()

    notes = (
        data.get("notes")
        or ""
    ).strip()

    if (
        record_id < 1
        or condition not in {
            "GOOD",
            "DAMAGED",
            "NEEDS_REPAIR",
        }
    ):
        return jsonify(
            {
                "success": False,
                "message": "Invalid return payload.",
            }
        )

    success = hw_controller.return_request(
        record_id,
        condition,
        notes,
        admin_username=session["username"],
    )

    return jsonify(
        {
            "success": success
        }
    )


# ---------------------------------------------------------------------------
# Notifications API
# ---------------------------------------------------------------------------

@app.route(
    "/api/notifications",
    methods=["GET"],
)
@login_required
def get_notifications():
    username = (
        None
        if session.get(
            "role",
            "STUDENT",
        ).upper() == "ADMIN"
        else session["username"]
    )

    notifications = (
        hw_controller.get_all_notifications(
            username
        )
    )

    return jsonify(notifications)


@app.route(
    "/api/notifications/read",
    methods=["POST"],
)
@login_required
def mark_notification_read():
    data = request.get_json(
        silent=True
    ) or {}

    notification_id = _parse_int(
        data.get("notification_id"),
        -1,
    )

    if notification_id < 1:
        return jsonify(
            {
                "success": False,
                "message": "Invalid notification id.",
            }
        )

    username = (
        None
        if session.get(
            "role",
            "STUDENT",
        ).upper() == "ADMIN"
        else session["username"]
    )

    success = hw_controller.mark_notification_read(
        notification_id,
        username=username,
    )

    return jsonify(
        {
            "success": success
        }
    )


# ---------------------------------------------------------------------------
# User Administration API
# ---------------------------------------------------------------------------

@app.route(
    "/api/users",
    methods=["GET"],
)
@login_required
@admin_required
def get_users():
    return jsonify(
        auth_controller.get_users()
    )


@app.route(
    "/api/users/role",
    methods=["POST"],
)
@login_required
@admin_required
def set_user_role():
    data = request.get_json(
        silent=True
    ) or {}

    username = (
        data.get("username")
        or ""
    ).strip()

    role = (
        data.get("role")
        or ""
    ).upper()

    if (
        not username
        or role not in {
            "ADMIN",
            "STUDENT",
        }
    ):
        return jsonify(
            {
                "success": False,
                "message": "Invalid user role payload.",
            }
        )

    success = auth_controller.set_user_role(
        username,
        role,
    )

    return jsonify(
        {
            "success": success
        }
    )


@app.route(
    "/api/users/password",
    methods=["POST"],
)
@login_required
@admin_required
def reset_user_password():
    data = request.get_json(
        silent=True
    ) or {}

    username = (
        data.get("username")
        or ""
    ).strip()

    password = data.get(
        "password",
        "",
    )

    if not username or not password:
        return jsonify(
            {
                "success": False,
                "message": "Invalid password reset payload.",
            }
        )

    success = auth_controller.admin_reset_password(
        username,
        password,
    )

    return jsonify(
        {
            "success": success
        }
    )


@app.route(
    "/api/users/delete",
    methods=["POST"],
)
@login_required
@admin_required
def delete_user():
    data = request.get_json(
        silent=True
    ) or {}

    username = (
        data.get("username")
        or ""
    ).strip()

    if not username:
        return jsonify(
            {
                "success": False,
                "message": "Invalid username payload.",
            }
        )

    success = auth_controller.delete_user(
        username
    )

    return jsonify(
        {
            "success": success
        }
    )


# ---------------------------------------------------------------------------
# Audit API
# ---------------------------------------------------------------------------

@app.route(
    "/api/audit",
    methods=["GET"],
)
@login_required
@admin_required
def get_audit_logs():
    return jsonify(
        hw_controller.get_audit_logs()
    )


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

@app.route(
    "/api/reports/<report_type>",
    methods=["GET"],
)
@login_required
@admin_required
def download_report(report_type):
    if report_type not in {
        "inventory",
        "requests",
        "overdue",
        "audit",
    }:
        return jsonify(
            {
                "success": False,
                "message": "Unknown report type.",
            }
        ), 404

    report = io.StringIO(
        newline=""
    )

    fields = {
        "inventory": (
            "id",
            "name",
            "category",
            "stock_qty",
            "unit_price",
            "status",
            "condition",
        ),

        "requests": (
            "id",
            "username",
            "hardware_id",
            "borrow_qty",
            "borrow_date",
            "return_due_date",
            "status",
            "approved_by",
            "purpose",
            "instructor",
        ),

        "overdue": (
            "id",
            "username",
            "hardware_id",
            "borrow_qty",
            "borrow_date",
            "return_due_date",
            "status",
        ),

        "audit": (
            "id",
            "action",
            "details",
            "performed_by",
            "timestamp",
        ),
    }[report_type]

    rows = {
        "inventory": hw_controller.get_all_hardware,
        "requests": hw_controller.get_all_requests,
        "overdue": hw_controller.get_overdue_requests,
        "audit": hw_controller.get_audit_logs,
    }[report_type]()

    writer = csv.DictWriter(
        report,
        fieldnames=fields,
    )

    writer.writeheader()

    writer.writerows(
        {
            field: row.get(
                field,
                "",
            )
            for field in fields
        }
        for row in rows
    )

    filename = f"{report_type}_report.csv"

    return Response(
        report.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
                f"attachment; filename={filename}"
        },
    )


# ---------------------------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(
        debug=True,
        port=5000,
    )