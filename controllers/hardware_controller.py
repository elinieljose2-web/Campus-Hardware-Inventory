import csv
from datetime import date, datetime
import os
import sqlite3


class HardwareController:
    LOW_STOCK_LIMIT = 5

    def __init__(self, db_path="hardware_inventory.db"):
        self.db_path = db_path
        self._observers = []
        self._notifications = []
        self._notification_id_counter = 1
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()

        # Hardware Inventory Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hardware (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                stock_qty INTEGER NOT NULL,
                unit_price REAL DEFAULT 0.0,
                status TEXT DEFAULT 'In Stock',
                condition_status TEXT DEFAULT 'GOOD'
            );
        """)

        # Borrow Records Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS borrow_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                hardware_id TEXT NOT NULL,
                borrow_qty INTEGER NOT NULL,
                borrow_date TEXT NOT NULL,
                return_due_date TEXT,
                status TEXT DEFAULT 'PENDING',
                approved_by TEXT DEFAULT '-',
                checked_out_at TEXT,
                returned_at TEXT,
                return_condition TEXT,
                return_notes TEXT,
                purpose TEXT,
                instructor TEXT,
                transaction_id TEXT
            );
        """)

        # System Audit Log Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                details TEXT NOT NULL,
                performed_by TEXT DEFAULT 'System',
                timestamp TEXT NOT NULL
            );
        """)

        # Condition History Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS condition_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hardware_id TEXT NOT NULL,
                old_condition TEXT NOT NULL,
                new_condition TEXT NOT NULL,
                reason TEXT NOT NULL,
                changed_by TEXT NOT NULL,
                changed_at TEXT NOT NULL
            );
        """)

        # Database Schema Migrations for existing DB files
        try:
            cursor.execute(
                "ALTER TABLE borrow_records ADD COLUMN approved_by TEXT DEFAULT"
                " '-'"
            )
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute(
                "ALTER TABLE borrow_records ADD COLUMN transaction_id TEXT"
            )
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute(
                "ALTER TABLE audit_logs ADD COLUMN performed_by TEXT DEFAULT"
                " 'System'"
            )
        except sqlite3.OperationalError:
            pass

        for column, definition in (
            ("condition_status", "TEXT DEFAULT 'GOOD'"),
            ("unit_price", "REAL DEFAULT 0.0"),
            ("checked_out_at", "TEXT"),
            ("returned_at", "TEXT"),
            ("return_condition", "TEXT"),
            ("return_notes", "TEXT"),
            ("purpose", "TEXT"),
            ("instructor", "TEXT"),
        ):
            try:
                table = (
                    "hardware"
                    if column in ("condition_status", "unit_price")
                    else "borrow_records"
                )
                cursor.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
                )
            except sqlite3.OperationalError:
                pass

        conn.commit()
        conn.close()

    def backup_database(self, output_path):
        output_path = os.path.abspath(output_path)
        if output_path == os.path.abspath(self.db_path):
            return False
        source = self._get_connection()
        destination = sqlite3.connect(output_path)
        try:
            source.backup(destination)
            self._init_db()
            return True
        except sqlite3.Error:
            return False
        finally:
            destination.close()
            source.close()

    def restore_database(self, input_path):
        input_path = os.path.abspath(input_path)
        if not os.path.isfile(input_path) or input_path == os.path.abspath(
            self.db_path
        ):
            return False
        source = sqlite3.connect(input_path)
        destination = self._get_connection()
        try:
            source.backup(destination)
            return True
        except sqlite3.Error:
            return False
        finally:
            destination.close()
            source.close()

    def _record_condition_change(
        self,
        conn,
        hardware_id,
        old_condition,
        new_condition,
        reason,
        changed_by,
    ):
        old_condition = (old_condition or "GOOD").upper()
        new_condition = (new_condition or "GOOD").upper()
        if old_condition == new_condition:
            return
        conn.execute(
            """
            INSERT INTO condition_history (hardware_id, old_condition, new_condition, reason, changed_by, changed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                hardware_id,
                old_condition,
                new_condition,
                reason,
                changed_by,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

    def get_condition_history(self, hardware_id):
        conn = self._get_connection()
        rows = conn.execute(
            """
            SELECT hardware_id, old_condition, new_condition, reason, changed_by, changed_at
            FROM condition_history
            WHERE hardware_id = ?
            ORDER BY id DESC
            """,
            (hardware_id,),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def subscribe(self, callback):
        if callback not in self._observers:
            self._observers.append(callback)

    def notify_observers(self):
        for callback in list(self._observers):
            try:
                callback()
            except Exception:
                pass

    def log_audit(self, action, details, performed_by="System"):
        """Inserts an audit event into the database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                """
                INSERT INTO audit_logs (action, details, performed_by, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (action, details, performed_by, timestamp),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print("Audit Logging Error:", e)

    def get_audit_logs(self):
        """Retrieves all log entries sorted by latest first."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, action, details, performed_by, timestamp
                FROM audit_logs
                ORDER BY id DESC
                """
            )
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            print("Get Audit Logs Error:", e)
            return []

    def get_all_hardware(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, category, stock_qty, unit_price, status,"
            " condition_status FROM hardware"
        )
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": dict(r).get("id", ""),
                "name": dict(r).get("name", ""),
                "category": dict(r).get("category", ""),
                "stock_qty": dict(r).get("stock_qty", 0),
                "quantity": dict(r).get("stock_qty", 0),
                "unit_price": float(dict(r).get("unit_price", 0) or 0),
                "status": self.get_stock_status(dict(r).get("stock_qty", 0)),
                "condition": dict(r).get("condition_status", "GOOD"),
            }
            for r in rows
        ]

    @classmethod
    def get_stock_status(cls, stock_qty):
        if stock_qty <= 0:
            return "OUT OF STOCK"
        if stock_qty <= cls.LOW_STOCK_LIMIT:
            return "LOW STOCK"
        return "IN STOCK"

    def add_hardware(
        self,
        item_id,
        name,
        category,
        stock_qty,
        status="In Stock",
        condition="GOOD",
        admin_username="Admin",
        unit_price=0.0,
    ):
        conn = self._get_connection()
        cursor = conn.cursor()
        status = self.get_stock_status(stock_qty)
        previous = cursor.execute(
            "SELECT condition_status FROM hardware WHERE id = ?", (item_id,)
        ).fetchone()
        cursor.execute(
            """
            INSERT OR REPLACE INTO hardware (id, name, category, stock_qty, unit_price, status, condition_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_id,
                name,
                category,
                stock_qty,
                float(unit_price or 0),
                status,
                condition.upper(),
            ),
        )
        if previous:
            self._record_condition_change(
                conn,
                item_id,
                previous["condition_status"],
                condition,
                "Inventory item updated",
                admin_username,
            )
        conn.commit()
        conn.close()

        # Audit Log Trigger
        self.log_audit(
            "ADD_HARDWARE",
            f"Added hardware item {item_id} ({name})",
            performed_by=admin_username,
        )
        self.notify_observers()

    def update_hardware(
        self,
        item_id,
        name,
        category,
        stock_qty,
        condition="GOOD",
        admin_username="Admin",
        unit_price=0.0,
    ):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            status = self.get_stock_status(stock_qty)
            previous = cursor.execute(
                "SELECT condition_status FROM hardware WHERE id = ?", (item_id,)
            ).fetchone()
            cursor.execute(
                """
                UPDATE hardware
                SET name = ?, category = ?, stock_qty = ?, unit_price = ?, status = ?, condition_status = ?
                WHERE id = ?
                """,
                (
                    name,
                    category,
                    stock_qty,
                    float(unit_price or 0),
                    status,
                    condition.upper(),
                    item_id,
                ),
            )
            if cursor.rowcount == 0:
                conn.rollback()
                conn.close()
                return False
            self._record_condition_change(
                conn,
                item_id,
                previous["condition_status"],
                condition,
                "Inventory item edited",
                admin_username,
            )
            conn.commit()
            conn.close()
            self.log_audit(
                "EDIT_HARDWARE",
                f"Updated hardware item {item_id} ({name})",
                performed_by=admin_username,
            )
            self.notify_observers()
            return True
        except Exception as e:
            print("Hardware Update Error:", e)
            return False

    def delete_hardware(self, item_id, admin_username="Admin"):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM hardware WHERE id = ?", (item_id,))
        conn.commit()
        conn.close()

        # Audit Log Trigger
        self.log_audit(
            "DELETE_HARDWARE",
            f"Deleted hardware item {item_id}",
            performed_by=admin_username,
        )
        self.notify_observers()

    def create_reservation(
        self,
        username,
        hardware_id,
        borrow_qty,
        borrow_date,
        purpose,
        instructor,
        return_due_date=None,
        transaction_id=None,
    ):
        try:
            borrow_qty = int(borrow_qty)
            start_date = datetime.strptime(borrow_date, "%Y-%m-%d").date()
            due_date = (
                datetime.strptime(return_due_date, "%Y-%m-%d").date()
                if return_due_date
                else None
            )
            if (
                borrow_qty <= 0
                or start_date < date.today()
                or (due_date and due_date < start_date)
            ):
                return False
            conn = self._get_connection()
            cursor = conn.cursor()
            item = cursor.execute(
                "SELECT stock_qty FROM hardware WHERE id = ?", (hardware_id,)
            ).fetchone()
            if item is None or item["stock_qty"] < borrow_qty:
                conn.close()
                return False
            cursor.execute(
                """
                INSERT INTO borrow_records (username, hardware_id, borrow_qty, borrow_date, return_due_date, status, approved_by, purpose, instructor, transaction_id)
                VALUES (?, ?, ?, ?, ?, 'PENDING', '-', ?, ?, ?)
                """,
                (
                    username,
                    hardware_id,
                    borrow_qty,
                    borrow_date,
                    return_due_date,
                    purpose,
                    instructor,
                    transaction_id,
                ),
            )
            conn.commit()
            conn.close()

            # Audit Log Trigger
            self.log_audit(
                "SUBMIT_REQUEST",
                f"Requested {borrow_qty}x {hardware_id}",
                performed_by=username,
            )
            self.notify_observers()
            return True
        except Exception as e:
            print("Database Insert Error:", e)
            return False

    def get_all_requests(self):
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, username, hardware_id, borrow_qty, borrow_date, return_due_date, status, approved_by, purpose, instructor, transaction_id
            FROM borrow_records
            ORDER BY id DESC
            """
        )
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def get_requests_by_username(self, username):
        conn = self._get_connection()
        rows = conn.execute(
            """
            SELECT id, hardware_id, borrow_qty, borrow_date, return_due_date, status, approved_by, checked_out_at, returned_at, return_condition, return_notes, transaction_id
            FROM borrow_records
            WHERE username = ?
            ORDER BY id DESC
            """,
            (username,),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def search_hardware(
        self, search_query="", category="", status="", condition=""
    ):
        hardware = self.get_all_hardware()
        query = search_query.strip().lower()
        return [
            item
            for item in hardware
            if (
                not query
                or query in str(item["id"]).lower()
                or query in item["name"].lower()
            )
            and (not category or item["category"] == category)
            and (not status or item["status"] == status)
            and (not condition or item.get("condition", "GOOD") == condition)
        ]

    def get_low_stock_hardware(self):
        return [
            item
            for item in self.get_all_hardware()
            if item["stock_qty"] <= self.LOW_STOCK_LIMIT
        ]

    def get_overdue_requests(self):
        today = date.today().isoformat()
        conn = self._get_connection()
        rows = conn.execute(
            """
            SELECT *
            FROM borrow_records
            WHERE status = 'APPROVED' AND return_due_date IS NOT NULL AND return_due_date < ?
            """,
            (today,),
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def _build_notifications(self, username=None):
        if username:
            grouped = {}
            for request in self.get_requests_by_username(username):
                group_id = request.get("transaction_id") or f"request-{request['id']}"
                grouped.setdefault(group_id, []).append(request)

            notifications = []
            for group_id, requests in grouped.items():
                statuses = {request.get("status") for request in requests}
                if statuses == {"APPROVED"}:
                    notifications.append((group_id, f"Transaction {group_id} was approved."))
                elif statuses == {"DECLINED"}:
                    notifications.append((group_id, f"Transaction {group_id} was declined."))
                elif "RETURN_REQUESTED" in statuses:
                    notifications.append((group_id, f"Return request for transaction {group_id} is awaiting review."))
                elif statuses & {"APPROVED", "DECLINED"}:
                    notifications.append((group_id, f"Transaction {group_id} has been partially processed."))
            return notifications

        metrics = self.get_dashboard_metrics()
        notifications = []
        if metrics["pending_requests"]:
            notifications.append(
                f"{metrics['pending_requests']} request(s) need approval."
            )
        if metrics["overdue_requests"]:
            notifications.append(
                f"{metrics['overdue_requests']} approved item(s) are overdue."
            )
        if metrics["low_stock_items"]:
            notifications.append(
                f"{metrics['low_stock_items']} item(s) are low or out of stock."
            )
        return notifications

    def _sync_notifications(self, username=None):
        current_notifications = self._build_notifications(username)
        if username:
            existing = {
                item.get("key"): item
                for item in self._notifications
                if item["username"] == username
            }
            for key, message in current_notifications:
                if key in existing:
                    if existing[key]["message"] != message:
                        existing[key]["message"] = message
                        existing[key]["read"] = False
                    continue
                self._notifications.append({
                    "id": self._notification_id_counter,
                    "key": key,
                    "message": message,
                    "username": username,
                    "read": False,
                })
                self._notification_id_counter += 1
            return

        existing = {
            item["message"]: item
            for item in self._notifications
            if item["username"] == username
        }

        for message in current_notifications:
            if message not in existing:
                self._notifications.append({
                    "id": self._notification_id_counter,
                    "message": message,
                    "username": username,
                    "read": False,
                })
                self._notification_id_counter += 1

    def get_notifications(self, username=None):
        self._sync_notifications(username)
        notifications = (
            [
                item
                for item in self._notifications
                if item["username"] == username
            ]
            if username
            else [
                item for item in self._notifications if item["username"] is None
            ]
        )
        return [item["message"] for item in notifications if not item["read"]]

    def get_all_notifications(self, username=None):
        self._sync_notifications(username)
        if username:
            return [
                item
                for item in self._notifications
                if item["username"] == username
            ]
        return [
            item for item in self._notifications if item["username"] is None
        ]

    def mark_notification_read(self, notification_id, username=None):
        for item in self._notifications:
            if item["id"] == notification_id and item["username"] == username:
                item["read"] = True
                return True
        return False

    def export_report(self, report_type, output_path):
        if report_type == "inventory":
            rows = self.get_all_hardware()
            fields = (
                "id",
                "name",
                "category",
                "stock_qty",
                "unit_price",
                "status",
                "condition",
            )
        elif report_type == "requests":
            rows = self.get_all_requests()
            fields = (
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
            )
        elif report_type == "overdue":
            rows = self.get_overdue_requests()
            fields = (
                "id",
                "username",
                "hardware_id",
                "borrow_qty",
                "borrow_date",
                "return_due_date",
                "status",
            )
        elif report_type == "audit":
            rows = self.get_audit_logs()
            fields = ("id", "action", "details", "performed_by", "timestamp")
        else:
            return False
        with open(output_path, "w", newline="", encoding="utf-8") as report_file:
            writer = csv.DictWriter(report_file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(
                {field: row.get(field, "") for field in fields} for row in rows
            )
        return True

    def get_dashboard_metrics(self):
        conn = self._get_connection()
        hardware = conn.execute(
            """
            SELECT COUNT(*) AS count,
                   COALESCE(SUM(stock_qty), 0) AS quantity,
                   COALESCE(SUM(stock_qty * unit_price), 0) AS total_value
            FROM hardware
            """
        ).fetchone()
        requests = conn.execute(
            "SELECT status, COUNT(*) AS count FROM borrow_records GROUP BY"
            " status"
        ).fetchall()
        conn.close()
        counts = {row["status"]: row["count"] for row in requests}
        return {
            "equipment_types": hardware["count"],
            "available_units": hardware["quantity"],
            "total_asset_value": float(hardware["total_value"] or 0),
            "pending_requests": counts.get("PENDING", 0),
            "approved_requests": counts.get("APPROVED", 0),
            "returned_requests": counts.get("RETURNED", 0),
            "overdue_requests": len(self.get_overdue_requests()),
            "low_stock_items": len(self.get_low_stock_hardware()),
        }

    def return_request(
        self, record_id, return_condition, return_notes, admin_username="Admin"
    ):
        try:
            conn = self._get_connection()
            record = conn.execute(
                "SELECT hardware_id, borrow_qty, username, status FROM"
                " borrow_records WHERE id = ?",
                (record_id,),
            ).fetchone()
            if not record or record["status"] not in (
                "APPROVED",
                "RETURN_REQUESTED",
            ):
                conn.close()
                return False

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            condition = return_condition.upper()
            current_item = conn.execute(
                "SELECT condition_status FROM hardware WHERE id = ?",
                (record["hardware_id"],),
            ).fetchone()
            conn.execute(
                """
                UPDATE borrow_records
                SET status = 'RETURNED', returned_at = ?, return_condition = ?, return_notes = ?, approved_by = ?
                WHERE id = ? AND status IN ('APPROVED', 'RETURN_REQUESTED')
                """,
                (now, condition, return_notes, admin_username, record_id),
            )
            if condition != "DAMAGED":
                current_stock = conn.execute(
                    "SELECT stock_qty FROM hardware WHERE id = ?",
                    (record["hardware_id"],),
                ).fetchone()["stock_qty"]
                restored_stock = current_stock + record["borrow_qty"]
                conn.execute(
                    """
                    UPDATE hardware
                    SET stock_qty = ?, status = ?
                    WHERE id = ?
                    """,
                    (
                        restored_stock,
                        self.get_stock_status(restored_stock),
                        record["hardware_id"],
                    ),
                )
            conn.execute(
                "UPDATE hardware SET condition_status = ? WHERE id = ?",
                (condition, record["hardware_id"]),
            )
            self._record_condition_change(
                conn,
                record["hardware_id"],
                current_item["condition_status"] if current_item else "GOOD",
                condition,
                return_notes or "Equipment returned",
                admin_username,
            )
            conn.commit()
            conn.close()
            self.log_audit(
                "RETURN_EQUIPMENT",
                f"Returned request #{record_id} ({condition})",
                performed_by=admin_username,
            )
            self.notify_observers()
            return True
        except Exception as error:
            print("Return Processing Error:", error)
            return False

    def update_request_status(
        self, record_id, new_status, admin_username="Admin"
    ):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            audit_action = None
            audit_details = None

            if new_status == "APPROVED":
                cursor.execute(
                    """
                    SELECT hardware_id, borrow_qty, username
                    FROM borrow_records
                    WHERE id = ? AND status = 'PENDING'
                    """,
                    (record_id,),
                )
                record = cursor.fetchone()
                if record:
                    hw_id, qty, student = (
                        record["hardware_id"],
                        record["borrow_qty"],
                        record["username"],
                    )
                    cursor.execute(
                        """
                        UPDATE hardware
                        SET stock_qty = stock_qty - ?
                        WHERE id = ? AND stock_qty >= ?
                        """,
                        (qty, hw_id, qty),
                    )
                    if cursor.rowcount == 0:
                        conn.rollback()
                        conn.close()
                        return False
                    cursor.execute(
                        "SELECT stock_qty FROM hardware WHERE id = ?",
                        (hw_id,),
                    )
                    remaining_stock = cursor.fetchone()["stock_qty"]
                    cursor.execute(
                        "UPDATE hardware SET status = ? WHERE id = ?",
                        (self.get_stock_status(remaining_stock), hw_id),
                    )
                    audit_action = "APPROVE_REQUEST"
                    audit_details = (
                        f"Approved request #{record_id} for {student} ({qty}x"
                        f" {hw_id})"
                    )

            elif new_status == "DECLINED":
                cursor.execute(
                    """
                    SELECT username
                    FROM borrow_records
                    WHERE id = ? AND status = 'PENDING'
                    """,
                    (record_id,),
                )
                record = cursor.fetchone()
                if record:
                    audit_action = "DECLINE_REQUEST"
                    audit_details = (
                        f"Declined request #{record_id} for"
                        f" {record['username']}"
                    )

            if not audit_action:
                conn.rollback()
                conn.close()
                return False
            checked_out_at = (
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if new_status == "APPROVED"
                else None
            )
            cursor.execute(
                """
                UPDATE borrow_records
                SET status = ?, approved_by = ?, checked_out_at = COALESCE(?, checked_out_at)
                WHERE id = ?
                """,
                (new_status, admin_username, checked_out_at, record_id),
            )
            conn.commit()
            conn.close()
            if audit_action:
                self.log_audit(
                    audit_action, audit_details, performed_by=admin_username
                )
            self.notify_observers()
            return True
        except Exception as e:
            print("Error updating request status:", e)
            return False

    def request_return(self, record_id, username):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE borrow_records
                SET status = 'RETURN_REQUESTED'
                WHERE id = ? AND username = ? AND status = 'APPROVED'
                """,
                (record_id, username),
            )
            if cursor.rowcount == 0:
                conn.close()
                return False
            conn.commit()
            conn.close()
            self.log_audit(
                "RETURN_REQUESTED",
                f"Return requested for record #{record_id}",
                performed_by=username,
            )
            self.notify_observers()
            return True
        except Exception as error:
            print("Return Request Error:", error)
            return False