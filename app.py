from functools import wraps

import csv
import io

from flask import Flask, Response, flash, jsonify, redirect, render_template, request, session, url_for

from controllers.auth_controller import AuthController
from controllers.hardware_controller import HardwareController

app = Flask(__name__)
app.secret_key = "lab_portal_secret_key"

auth_controller = AuthController()
hw_controller = HardwareController()


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
            flash("Administrator access required.", "danger")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)

    return wrapped


def student_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if session.get("role", "STUDENT").upper() != "STUDENT":
            flash("Student access required.", "danger")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)

    return wrapped


@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()

        if not username or not password:
            flash("Please enter both username and password.", "danger")
            return render_template("login.html")

        ok, result = auth_controller.login_user(username, password)
        if not ok:
            flash(result, "danger")
            return render_template("login.html")

        session.clear()
        session["username"] = result["username"]
        session["role"] = result["role"]

        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""
        recovery_keyword = request.form.get("recovery_keyword") or ""
        role = (request.form.get("role") or "").upper()

        if not username or not email or not password or not recovery_keyword or role not in {"STUDENT", "ADMIN"}:
            flash("Complete all fields and select an account type.", "danger")
            return render_template("register.html")
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html")

        success, message = auth_controller.register_user(
            username, email, password, recovery_keyword, role=role
        )
        flash(message, "success" if success else "danger")
        if success:
            return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip()
        recovery_keyword = request.form.get("recovery_keyword") or ""
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html")

        success, message = auth_controller.reset_password(
            username, email, recovery_keyword, password
        )
        flash(message, "success" if success else "danger")
        if success:
            return redirect(url_for("login"))

    return render_template("reset_password.html")


@app.route("/dashboard")
@login_required
def dashboard():
    if session.get("role", "STUDENT").upper() == "ADMIN":
        return redirect(url_for("admin_dashboard"))
    return redirect(url_for("student_dashboard"))


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    user = {"username": session.get("username", "User"), "role": "ADMIN"}
    metrics = hw_controller.get_dashboard_metrics()
    notification_count = len(hw_controller.get_notifications())
    return render_template(
        "admin.html",
        user=user,
        metrics=metrics,
        notification_count=notification_count,
    )


@app.route("/student/dashboard")
@student_required
def student_dashboard():
    user = {"username": session.get("username", "User"), "role": "STUDENT"}
    return render_template("student.html", user=user)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


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


@app.route("/api/hardware", methods=["GET"])
@login_required
def get_hardware():
    return jsonify(hw_controller.get_all_hardware())


@app.route("/api/hardware/add", methods=["POST"])
@login_required
@admin_required
def add_hardware():
    data = request.get_json(silent=True) or {}
    success = hw_controller.add_hardware(
        item_id=data.get("id", "").strip(),
        name=data.get("name", "").strip(),
        category=data.get("category", "").strip(),
        stock_qty=_parse_int(data.get("stock_qty", 0), 0),
        condition=data.get("condition", "GOOD"),
        admin_username=session["username"],
        unit_price=_parse_float(data.get("unit_price", 0), 0.0),
    )
    return jsonify({"success": success is None or success is True})


@app.route("/api/hardware/update", methods=["POST"])
@login_required
@admin_required
def update_hardware():
    data = request.get_json(silent=True) or {}
    success = hw_controller.update_hardware(
        item_id=data.get("id", "").strip(),
        name=data.get("name", "").strip(),
        category=data.get("category", "").strip(),
        stock_qty=_parse_int(data.get("stock_qty", 0), 0),
        condition=data.get("condition", "GOOD"),
        admin_username=session["username"],
        unit_price=_parse_float(data.get("unit_price", 0), 0.0),
    )
    return jsonify({"success": success})


@app.route("/api/hardware/delete", methods=["POST"])
@login_required
@admin_required
def delete_hardware():
    data = request.get_json(silent=True) or {}
    hw_controller.delete_hardware(
        data.get("id", "").strip(),
        admin_username=session["username"],
    )
    return jsonify({"success": True})


@app.route("/api/reserve", methods=["POST"])
@student_required
def reserve():
    data = request.get_json(silent=True) or {}
    try:
        success = hw_controller.create_reservation(
            username=session["username"],
            hardware_id=data.get("hardware_id", "").strip(),
            borrow_qty=_parse_int(data.get("borrow_qty", 1), 1),
            borrow_date=data.get("borrow_date", ""),
            purpose=data.get("purpose", "Student Reservation"),
            instructor=data.get("instructor", ""),
            return_due_date=data.get("return_due_date"),
            transaction_id=(data.get("transaction_id") or "").strip() or None,
        )
    except Exception:
        success = False
    return jsonify({"success": success})


@app.route("/api/requests", methods=["GET"])
@login_required
def get_requests():
    requests = hw_controller.get_all_requests()
    if session.get("role", "STUDENT").upper() != "ADMIN":
        requests = [
            request_item
            for request_item in requests
            if request_item.get("username") == session["username"]
        ]
    return jsonify(requests)


@app.route("/api/requests/update", methods=["POST"])
@login_required
@admin_required
def update_request():
    data = request.get_json(silent=True) or {}
    record_id = _parse_int(data.get("record_id"), -1)
    status = (data.get("status") or "").upper()
    if record_id < 1 or status not in {"APPROVED", "DECLINED"}:
        return jsonify({"success": False, "message": "Invalid request update."})

    success = hw_controller.update_request_status(
        record_id=record_id,
        new_status=status,
        admin_username=session["username"],
    )
    return jsonify({"success": success})


@app.route("/api/requests/return", methods=["POST"])
@student_required
def request_return():
    data = request.get_json(silent=True) or {}
    record_id = _parse_int(data.get("record_id"), -1)
    if record_id < 1:
        return jsonify({"success": False, "message": "Invalid request id."})

    success = hw_controller.request_return(record_id, session["username"])
    return jsonify({"success": success})


@app.route("/api/requests/complete-return", methods=["POST"])
@login_required
@admin_required
def complete_return():
    data = request.get_json(silent=True) or {}
    record_id = _parse_int(data.get("record_id"), -1)
    condition = (data.get("condition") or "GOOD").strip().upper()
    notes = (data.get("notes") or "").strip()
    if record_id < 1 or condition not in {"GOOD", "DAMAGED", "NEEDS_REPAIR"}:
        return jsonify({"success": False, "message": "Invalid return payload."})

    success = hw_controller.return_request(
        record_id,
        condition,
        notes,
        admin_username=session["username"],
    )
    return jsonify({"success": success})


@app.route("/api/notifications", methods=["GET"])
@login_required
def get_notifications():
    username = None if session.get("role", "STUDENT").upper() == "ADMIN" else session["username"]
    notifications = hw_controller.get_all_notifications(username)
    return jsonify(notifications)


@app.route("/api/notifications/read", methods=["POST"])
@login_required
def mark_notification_read():
    data = request.get_json(silent=True) or {}
    notification_id = _parse_int(data.get("notification_id"), -1)
    if notification_id < 1:
        return jsonify({"success": False, "message": "Invalid notification id."})

    username = None if session.get("role", "STUDENT").upper() == "ADMIN" else session["username"]
    success = hw_controller.mark_notification_read(notification_id, username=username)
    return jsonify({"success": success})


@app.route("/api/users", methods=["GET"])
@login_required
@admin_required
def get_users():
    return jsonify(auth_controller.get_users())


@app.route("/api/users/role", methods=["POST"])
@login_required
@admin_required
def set_user_role():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    role = (data.get("role") or "").upper()
    if not username or role not in {"ADMIN", "STUDENT"}:
        return jsonify({"success": False, "message": "Invalid user role payload."})

    success = auth_controller.set_user_role(username, role)
    return jsonify({"success": success})


@app.route("/api/users/password", methods=["POST"])
@login_required
@admin_required
def reset_user_password():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"success": False, "message": "Invalid password reset payload."})

    success = auth_controller.admin_reset_password(username, password)
    return jsonify({"success": success})


@app.route("/api/users/delete", methods=["POST"])
@login_required
@admin_required
def delete_user():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    if not username:
        return jsonify({"success": False, "message": "Invalid username payload."})

    success = auth_controller.delete_user(username)
    return jsonify({"success": success})


@app.route("/api/audit", methods=["GET"])
@login_required
@admin_required
def get_audit_logs():
    return jsonify(hw_controller.get_audit_logs())


@app.route("/api/reports/<report_type>", methods=["GET"])
@login_required
@admin_required
def download_report(report_type):
    if report_type not in {"inventory", "requests", "overdue", "audit"}:
        return jsonify({"success": False, "message": "Unknown report type."}), 404

    report = io.StringIO(newline="")
    fields = {
        "inventory": ("id", "name", "category", "stock_qty", "unit_price", "status", "condition"),
        "requests": ("id", "username", "hardware_id", "borrow_qty", "borrow_date", "return_due_date", "status", "approved_by", "purpose", "instructor"),
        "overdue": ("id", "username", "hardware_id", "borrow_qty", "borrow_date", "return_due_date", "status"),
        "audit": ("id", "action", "details", "performed_by", "timestamp"),
    }[report_type]
    rows = {
        "inventory": hw_controller.get_all_hardware,
        "requests": hw_controller.get_all_requests,
        "overdue": hw_controller.get_overdue_requests,
        "audit": hw_controller.get_audit_logs,
    }[report_type]()
    writer = csv.DictWriter(report, fieldnames=fields)
    writer.writeheader()
    writer.writerows({field: row.get(field, "") for field in fields} for row in rows)
    filename = f"{report_type}_report.csv"
    return Response(
        report.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
