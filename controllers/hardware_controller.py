import csv
import json
import os
from datetime import date, datetime

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()


class HardwareController:
    LOW_STOCK_LIMIT = 5

    def __init__(self, db_path="hardware_inventory.db"):
        # Kept for compatibility with the existing application.
        # Runtime database is now Supabase PostgreSQL.
        self.db_path = db_path

        self._observers = []
        self._notifications = []
        self._notification_id_counter = 1

        self._init_db()

    def _get_connection(self):
        """Return a connection to Supabase PostgreSQL."""
        database_url = os.getenv("DATABASE_URL")

        if not database_url:
            raise RuntimeError("DATABASE_URL is not configured.")

        return psycopg.connect(database_url, row_factory=dict_row)

    def _init_db(self):
        """
        Supabase tables were already created and migrated.

        We intentionally do not run SQLite CREATE TABLE or ALTER TABLE
        statements here anymore.
        """
        conn = self._get_connection()

        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # BACKUP / RESTORE
    # ------------------------------------------------------------------

    def backup_database(self, output_path):
        """
        Create a logical JSON backup of the PostgreSQL tables used
        by this controller.

        The old SQLite .backup() method cannot be used with PostgreSQL.
        """
        tables = [
            "hardware",
            "borrow_records",
            "condition_history",
            "audit_logs",
        ]

        try:
            backup_data = {
                "created_at": datetime.now().isoformat(),
                "database": "Supabase PostgreSQL",
                "tables": {},
            }

            conn = self._get_connection()

            try:
                for table in tables:
                    rows = conn.execute(
                        f"SELECT * FROM {table} ORDER BY id"
                    ).fetchall()

                    # Convert values into JSON-safe values.
                    clean_rows = []

                    for row in rows:
                        clean_row = {}

                        for key, value in row.items():
                            if isinstance(value, (datetime, date)):
                                clean_row[key] = value.isoformat()
                            else:
                                clean_row[key] = value

                        clean_rows.append(clean_row)

                    backup_data["tables"][table] = clean_rows

            finally:
                conn.close()

            output_path = os.path.abspath(output_path)

            with open(
                output_path,
                "w",
                encoding="utf-8",
            ) as backup_file:
                json.dump(
                    backup_data,
                    backup_file,
                    indent=2,
                    default=str,
                )

            return True

        except Exception as error:
            print("Database Backup Error:", error)
            return False

    def restore_database(self, input_path):
        """
        Restore a logical JSON backup created by backup_database().

        This is intentionally separate from the old SQLite restore logic.
        """
        input_path = os.path.abspath(input_path)

        if not os.path.isfile(input_path):
            return False

        try:
            with open(
                input_path,
                "r",
                encoding="utf-8",
            ) as backup_file:
                backup_data = json.load(backup_file)

            tables = backup_data.get("tables", {})

            conn = self._get_connection()

            try:
                # Restore child/dependent data first.
                # Existing application data is replaced.
                for table in (
                    "condition_history",
                    "audit_logs",
                    "borrow_records",
                    "hardware",
                ):
                    rows = tables.get(table, [])

                    if not rows:
                        continue

                    # Only restore known application columns.
                    if table == "hardware":
                        for row in rows:
                            conn.execute(
                                """
                                INSERT INTO hardware
                                (
                                    id,
                                    name,
                                    category,
                                    stock_qty,
                                    unit_price,
                                    status,
                                    condition_status
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (id)
                                DO UPDATE SET
                                    name = EXCLUDED.name,
                                    category = EXCLUDED.category,
                                    stock_qty = EXCLUDED.stock_qty,
                                    unit_price = EXCLUDED.unit_price,
                                    status = EXCLUDED.status,
                                    condition_status =
                                        EXCLUDED.condition_status
                                """,
                                (
                                    row.get("id"),
                                    row.get("name"),
                                    row.get("category"),
                                    row.get("stock_qty", 0),
                                    row.get("unit_price", 0),
                                    row.get("status", "In Stock"),
                                    row.get("condition_status", "GOOD"),
                                ),
                            )

                    elif table == "borrow_records":
                        for row in rows:
                            conn.execute(
                                """
                                INSERT INTO borrow_records
                                (
                                    id,
                                    username,
                                    hardware_id,
                                    borrow_qty,
                                    borrow_date,
                                    return_due_date,
                                    status,
                                    approved_by,
                                    checked_out_at,
                                    returned_at,
                                    return_condition,
                                    return_notes,
                                    purpose,
                                    instructor,
                                    transaction_id
                                )
                                VALUES
                                (
                                    %s, %s, %s, %s, %s, %s, %s,
                                    %s, %s, %s, %s, %s, %s, %s, %s
                                )
                                ON CONFLICT (id)
                                DO UPDATE SET
                                    username = EXCLUDED.username,
                                    hardware_id = EXCLUDED.hardware_id,
                                    borrow_qty = EXCLUDED.borrow_qty,
                                    borrow_date = EXCLUDED.borrow_date,
                                    return_due_date =
                                        EXCLUDED.return_due_date,
                                    status = EXCLUDED.status,
                                    approved_by = EXCLUDED.approved_by,
                                    checked_out_at =
                                        EXCLUDED.checked_out_at,
                                    returned_at = EXCLUDED.returned_at,
                                    return_condition =
                                        EXCLUDED.return_condition,
                                    return_notes = EXCLUDED.return_notes,
                                    purpose = EXCLUDED.purpose,
                                    instructor = EXCLUDED.instructor,
                                    transaction_id =
                                        EXCLUDED.transaction_id
                                """,
                                (
                                    row.get("id"),
                                    row.get("username"),
                                    row.get("hardware_id"),
                                    row.get("borrow_qty"),
                                    row.get("borrow_date"),
                                    row.get("return_due_date"),
                                    row.get("status", "PENDING"),
                                    row.get("approved_by", "-"),
                                    row.get("checked_out_at"),
                                    row.get("returned_at"),
                                    row.get("return_condition"),
                                    row.get("return_notes"),
                                    row.get("purpose"),
                                    row.get("instructor"),
                                    row.get("transaction_id"),
                                ),
                            )

                    elif table == "condition_history":
                        for row in rows:
                            conn.execute(
                                """
                                INSERT INTO condition_history
                                (
                                    id,
                                    hardware_id,
                                    old_condition,
                                    new_condition,
                                    reason,
                                    changed_by,
                                    changed_at
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (id)
                                DO UPDATE SET
                                    hardware_id =
                                        EXCLUDED.hardware_id,
                                    old_condition =
                                        EXCLUDED.old_condition,
                                    new_condition =
                                        EXCLUDED.new_condition,
                                    reason = EXCLUDED.reason,
                                    changed_by = EXCLUDED.changed_by,
                                    changed_at = EXCLUDED.changed_at
                                """,
                                (
                                    row.get("id"),
                                    row.get("hardware_id"),
                                    row.get("old_condition"),
                                    row.get("new_condition"),
                                    row.get("reason"),
                                    row.get("changed_by"),
                                    row.get("changed_at"),
                                ),
                            )

                    elif table == "audit_logs":
                        for row in rows:
                            conn.execute(
                                """
                                INSERT INTO audit_logs
                                (
                                    id,
                                    action,
                                    details,
                                    performed_by,
                                    timestamp
                                )
                                VALUES (%s, %s, %s, %s, %s)
                                ON CONFLICT (id)
                                DO UPDATE SET
                                    action = EXCLUDED.action,
                                    details = EXCLUDED.details,
                                    performed_by =
                                        EXCLUDED.performed_by,
                                    timestamp = EXCLUDED.timestamp
                                """,
                                (
                                    row.get("id"),
                                    row.get("action"),
                                    row.get("details"),
                                    row.get("performed_by", "System"),
                                    row.get("timestamp"),
                                ),
                            )

                conn.commit()

            except Exception:
                conn.rollback()
                raise

            finally:
                conn.close()

            return True

        except Exception as error:
            print("Database Restore Error:", error)
            return False

    # ------------------------------------------------------------------
    # CONDITION HISTORY
    # ------------------------------------------------------------------

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
            INSERT INTO condition_history
            (
                hardware_id,
                old_condition,
                new_condition,
                reason,
                changed_by,
                changed_at
            )
            VALUES (%s, %s, %s, %s, %s, %s)
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

        try:
            rows = conn.execute(
                """
                SELECT
                    hardware_id,
                    old_condition,
                    new_condition,
                    reason,
                    changed_by,
                    changed_at
                FROM condition_history
                WHERE hardware_id = %s
                ORDER BY id DESC
                """,
                (hardware_id,),
            ).fetchall()

            return [dict(row) for row in rows]

        finally:
            conn.close()

    # ------------------------------------------------------------------
    # OBSERVERS
    # ------------------------------------------------------------------

    def subscribe(self, callback):
        if callback not in self._observers:
            self._observers.append(callback)

    def notify_observers(self):
        for callback in list(self._observers):
            try:
                callback()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # AUDIT LOGS
    # ------------------------------------------------------------------

    def log_audit(self, action, details, performed_by="System"):
        """Insert an audit event into Supabase."""
        try:
            conn = self._get_connection()

            try:
                timestamp = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                conn.execute(
                    """
                    INSERT INTO audit_logs
                    (
                        action,
                        details,
                        performed_by,
                        timestamp
                    )
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        action,
                        details,
                        performed_by,
                        timestamp,
                    ),
                )

                conn.commit()

            finally:
                conn.close()

        except Exception as error:
            print("Audit Logging Error:", error)

    def get_audit_logs(self):
        """Retrieve all audit logs sorted newest first."""
        try:
            conn = self._get_connection()

            try:
                rows = conn.execute(
                    """
                    SELECT
                        id,
                        action,
                        details,
                        performed_by,
                        timestamp
                    FROM audit_logs
                    ORDER BY id DESC
                    """
                ).fetchall()

                return [dict(row) for row in rows]

            finally:
                conn.close()

        except Exception as error:
            print("Get Audit Logs Error:", error)
            return []

    # ------------------------------------------------------------------
    # HARDWARE
    # ------------------------------------------------------------------

    def get_all_hardware(self):
        conn = self._get_connection()

        try:
            rows = conn.execute(
                """
                SELECT
                    id,
                    name,
                    category,
                    stock_qty,
                    unit_price,
                    status,
                    condition_status
                FROM hardware
                ORDER BY id
                """
            ).fetchall()

            result = []

            for row in rows:
                result.append(
                    {
                        "id": row.get("id", ""),
                        "name": row.get("name", ""),
                        "category": row.get("category", ""),
                        "stock_qty": row.get("stock_qty", 0),
                        "quantity": row.get("stock_qty", 0),
                        "unit_price": float(
                            row.get("unit_price", 0) or 0
                        ),
                        "status": self.get_stock_status(
                            row.get("stock_qty", 0)
                        ),
                        "condition": row.get(
                            "condition_status",
                            "GOOD",
                        ),
                    }
                )

            return result

        finally:
            conn.close()

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

        try:
            status = self.get_stock_status(stock_qty)

            previous = conn.execute(
                """
                SELECT condition_status
                FROM hardware
                WHERE id = %s
                """,
                (item_id,),
            ).fetchone()

            conn.execute(
                """
                INSERT INTO hardware
                (
                    id,
                    name,
                    category,
                    stock_qty,
                    unit_price,
                    status,
                    condition_status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    category = EXCLUDED.category,
                    stock_qty = EXCLUDED.stock_qty,
                    unit_price = EXCLUDED.unit_price,
                    status = EXCLUDED.status,
                    condition_status =
                        EXCLUDED.condition_status
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
                    previous.get("condition_status"),
                    condition,
                    "Inventory item updated",
                    admin_username,
                )

            conn.commit()

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

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

            try:
                status = self.get_stock_status(stock_qty)

                previous = conn.execute(
                    """
                    SELECT condition_status
                    FROM hardware
                    WHERE id = %s
                    """,
                    (item_id,),
                ).fetchone()

                if not previous:
                    return False

                cursor = conn.execute(
                    """
                    UPDATE hardware
                    SET
                        name = %s,
                        category = %s,
                        stock_qty = %s,
                        unit_price = %s,
                        status = %s,
                        condition_status = %s
                    WHERE id = %s
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
                    return False

                self._record_condition_change(
                    conn,
                    item_id,
                    previous.get("condition_status"),
                    condition,
                    "Inventory item edited",
                    admin_username,
                )

                conn.commit()

            finally:
                conn.close()

            self.log_audit(
                "EDIT_HARDWARE",
                f"Updated hardware item {item_id} ({name})",
                performed_by=admin_username,
            )

            self.notify_observers()

            return True

        except Exception as error:
            print("Hardware Update Error:", error)
            return False

    def delete_hardware(self, item_id, admin_username="Admin"):
        conn = self._get_connection()

        try:
            conn.execute(
                """
                DELETE FROM hardware
                WHERE id = %s
                """,
                (item_id,),
            )

            conn.commit()

        finally:
            conn.close()

        self.log_audit(
            "DELETE_HARDWARE",
            f"Deleted hardware item {item_id}",
            performed_by=admin_username,
        )

        self.notify_observers()

    # ------------------------------------------------------------------
    # BORROW / RESERVATION
    # ------------------------------------------------------------------

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

            start_date = datetime.strptime(
                borrow_date,
                "%Y-%m-%d",
            ).date()

            due_date = (
                datetime.strptime(
                    return_due_date,
                    "%Y-%m-%d",
                ).date()
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

            try:
                item = conn.execute(
                    """
                    SELECT stock_qty
                    FROM hardware
                    WHERE id = %s
                    """,
                    (hardware_id,),
                ).fetchone()

                if (
                    item is None
                    or item["stock_qty"] < borrow_qty
                ):
                    conn.rollback()
                    return False

                conn.execute(
                    """
                    INSERT INTO borrow_records
                    (
                        username,
                        hardware_id,
                        borrow_qty,
                        borrow_date,
                        return_due_date,
                        status,
                        approved_by,
                        purpose,
                        instructor,
                        transaction_id
                    )
                    VALUES
                    (
                        %s, %s, %s, %s, %s,
                        'PENDING', '-', %s, %s, %s
                    )
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

            finally:
                conn.close()

            self.log_audit(
                "SUBMIT_REQUEST",
                f"Requested {borrow_qty}x {hardware_id}",
                performed_by=username,
            )

            self.notify_observers()

            return True

        except Exception as error:
            print("Database Insert Error:", error)
            return False

    def get_all_requests(self):
        conn = self._get_connection()

        try:
            rows = conn.execute(
                """
                SELECT
                    id,
                    username,
                    hardware_id,
                    borrow_qty,
                    borrow_date,
                    return_due_date,
                    status,
                    approved_by,
                    purpose,
                    instructor,
                    transaction_id
                FROM borrow_records
                ORDER BY id DESC
                """
            ).fetchall()

            return [dict(row) for row in rows]

        finally:
            conn.close()

    def get_requests_by_username(self, username):
        conn = self._get_connection()

        try:
            rows = conn.execute(
                """
                SELECT
                    id,
                    hardware_id,
                    borrow_qty,
                    borrow_date,
                    return_due_date,
                    status,
                    approved_by,
                    checked_out_at,
                    returned_at,
                    return_condition,
                    return_notes,
                    transaction_id
                FROM borrow_records
                WHERE username = %s
                ORDER BY id DESC
                """,
                (username,),
            ).fetchall()

            return [dict(row) for row in rows]

        finally:
            conn.close()

    # ------------------------------------------------------------------
    # SEARCH / STOCK
    # ------------------------------------------------------------------

    def search_hardware(
        self,
        search_query="",
        category="",
        status="",
        condition="",
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
            and (
                not category
                or item["category"] == category
            )
            and (
                not status
                or item["status"] == status
            )
            and (
                not condition
                or item.get("condition", "GOOD") == condition
            )
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

        try:
            rows = conn.execute(
                """
                SELECT *
                FROM borrow_records
                WHERE
                    status = 'APPROVED'
                    AND return_due_date IS NOT NULL
                    AND return_due_date < %s
                """,
                (today,),
            ).fetchall()

            return [dict(row) for row in rows]

        finally:
            conn.close()

    # ------------------------------------------------------------------
    # NOTIFICATIONS
    # ------------------------------------------------------------------

    def _build_notifications(self, username=None):
        if username:
            grouped = {}

            for request in self.get_requests_by_username(
                username
            ):
                group_id = (
                    request.get("transaction_id")
                    or f"request-{request['id']}"
                )

                grouped.setdefault(
                    group_id,
                    [],
                ).append(request)

            notifications = []

            for group_id, requests in grouped.items():
                statuses = {
                    request.get("status")
                    for request in requests
                }

                if statuses == {"APPROVED"}:
                    notifications.append(
                        (
                            group_id,
                            f"Transaction {group_id} was approved.",
                        )
                    )

                elif statuses == {"DECLINED"}:
                    notifications.append(
                        (
                            group_id,
                            f"Transaction {group_id} was declined.",
                        )
                    )

                elif "RETURN_REQUESTED" in statuses:
                    notifications.append(
                        (
                            group_id,
                            f"Return request for transaction "
                            f"{group_id} is awaiting review.",
                        )
                    )

                elif statuses & {"APPROVED", "DECLINED"}:
                    notifications.append(
                        (
                            group_id,
                            f"Transaction {group_id} has been "
                            f"partially processed.",
                        )
                    )

            return notifications

        metrics = self.get_dashboard_metrics()

        notifications = []

        if metrics["pending_requests"]:
            notifications.append(
                f"{metrics['pending_requests']} request(s) "
                f"need approval."
            )

        if metrics["overdue_requests"]:
            notifications.append(
                f"{metrics['overdue_requests']} approved "
                f"item(s) are overdue."
            )

        if metrics["low_stock_items"]:
            notifications.append(
                f"{metrics['low_stock_items']} item(s) are "
                f"low or out of stock."
            )

        return notifications

    def _sync_notifications(self, username=None):
        current_notifications = self._build_notifications(
            username
        )

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

                self._notifications.append(
                    {
                        "id": self._notification_id_counter,
                        "key": key,
                        "message": message,
                        "username": username,
                        "read": False,
                    }
                )

                self._notification_id_counter += 1

            return

        existing = {
            item["message"]: item
            for item in self._notifications
            if item["username"] is None
        }

        for message in current_notifications:
            if message not in existing:
                self._notifications.append(
                    {
                        "id": self._notification_id_counter,
                        "message": message,
                        "username": None,
                        "read": False,
                    }
                )

                self._notification_id_counter += 1

    def get_notifications(self, username=None):
        self._sync_notifications(username)

        if username:
            notifications = [
                item
                for item in self._notifications
                if item["username"] == username
            ]
        else:
            notifications = [
                item
                for item in self._notifications
                if item["username"] is None
            ]

        return [
            item["message"]
            for item in notifications
            if not item["read"]
        ]

    def get_all_notifications(self, username=None):
        self._sync_notifications(username)

        if username:
            return [
                item
                for item in self._notifications
                if item["username"] == username
            ]

        return [
            item
            for item in self._notifications
            if item["username"] is None
        ]

    def mark_notification_read(
        self,
        notification_id,
        username=None,
    ):
        for item in self._notifications:
            if (
                item["id"] == notification_id
                and item["username"] == username
            ):
                item["read"] = True
                return True

        return False

    # ------------------------------------------------------------------
    # REPORTS
    # ------------------------------------------------------------------

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

            fields = (
                "id",
                "action",
                "details",
                "performed_by",
                "timestamp",
            )

        else:
            return False

        with open(
            output_path,
            "w",
            newline="",
            encoding="utf-8",
        ) as report_file:
            writer = csv.DictWriter(
                report_file,
                fieldnames=fields,
            )

            writer.writeheader()

            writer.writerows(
                {
                    field: row.get(field, "")
                    for field in fields
                }
                for row in rows
            )

        return True

    # ------------------------------------------------------------------
    # DASHBOARD
    # ------------------------------------------------------------------

    def get_dashboard_metrics(self):
        conn = self._get_connection()

        try:
            hardware = conn.execute(
                """
                SELECT
                    COUNT(*) AS count,
                    COALESCE(SUM(stock_qty), 0) AS quantity,
                    COALESCE(
                        SUM(stock_qty * unit_price),
                        0
                    ) AS total_value
                FROM hardware
                """
            ).fetchone()

            requests = conn.execute(
                """
                SELECT
                    status,
                    COUNT(*) AS count
                FROM borrow_records
                GROUP BY status
                """
            ).fetchall()

            counts = {
                row["status"]: row["count"]
                for row in requests
            }

            return {
                "equipment_types": hardware["count"],
                "available_units": hardware["quantity"],
                "total_asset_value": float(
                    hardware["total_value"] or 0
                ),
                "pending_requests": counts.get(
                    "PENDING",
                    0,
                ),
                "approved_requests": counts.get(
                    "APPROVED",
                    0,
                ),
                "returned_requests": counts.get(
                    "RETURNED",
                    0,
                ),
                "overdue_requests": len(
                    self.get_overdue_requests()
                ),
                "low_stock_items": len(
                    self.get_low_stock_hardware()
                ),
            }

        finally:
            conn.close()

    # ------------------------------------------------------------------
    # RETURN EQUIPMENT
    # ------------------------------------------------------------------

    def return_request(
        self,
        record_id,
        return_condition,
        return_notes,
        admin_username="Admin",
    ):
        try:
            conn = self._get_connection()

            try:
                record = conn.execute(
                    """
                    SELECT
                        hardware_id,
                        borrow_qty,
                        username,
                        status
                    FROM borrow_records
                    WHERE id = %s
                    """,
                    (record_id,),
                ).fetchone()

                if (
                    not record
                    or record["status"]
                    not in (
                        "APPROVED",
                        "RETURN_REQUESTED",
                    )
                ):
                    conn.rollback()
                    return False

                now = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                condition = return_condition.upper()

                current_item = conn.execute(
                    """
                    SELECT condition_status
                    FROM hardware
                    WHERE id = %s
                    """,
                    (record["hardware_id"],),
                ).fetchone()

                conn.execute(
                    """
                    UPDATE borrow_records
                    SET
                        status = 'RETURNED',
                        returned_at = %s,
                        return_condition = %s,
                        return_notes = %s,
                        approved_by = %s
                    WHERE
                        id = %s
                        AND status IN
                        ('APPROVED', 'RETURN_REQUESTED')
                    """,
                    (
                        now,
                        condition,
                        return_notes,
                        admin_username,
                        record_id,
                    ),
                )

                if condition != "DAMAGED":
                    current_stock = conn.execute(
                        """
                        SELECT stock_qty
                        FROM hardware
                        WHERE id = %s
                        """,
                        (record["hardware_id"],),
                    ).fetchone()["stock_qty"]

                    restored_stock = (
                        current_stock
                        + record["borrow_qty"]
                    )

                    conn.execute(
                        """
                        UPDATE hardware
                        SET
                            stock_qty = %s,
                            status = %s
                        WHERE id = %s
                        """,
                        (
                            restored_stock,
                            self.get_stock_status(
                                restored_stock
                            ),
                            record["hardware_id"],
                        ),
                    )

                conn.execute(
                    """
                    UPDATE hardware
                    SET condition_status = %s
                    WHERE id = %s
                    """,
                    (
                        condition,
                        record["hardware_id"],
                    ),
                )

                self._record_condition_change(
                    conn,
                    record["hardware_id"],
                    (
                        current_item["condition_status"]
                        if current_item
                        else "GOOD"
                    ),
                    condition,
                    return_notes
                    or "Equipment returned",
                    admin_username,
                )

                conn.commit()

            finally:
                conn.close()

            self.log_audit(
                "RETURN_EQUIPMENT",
                f"Returned request #{record_id} "
                f"({condition})",
                performed_by=admin_username,
            )

            self.notify_observers()

            return True

        except Exception as error:
            print(
                "Return Processing Error:",
                error,
            )
            return False

    # ------------------------------------------------------------------
    # REQUEST STATUS
    # ------------------------------------------------------------------

    def update_request_status(
        self,
        record_id,
        new_status,
        admin_username="Admin",
    ):
        try:
            conn = self._get_connection()

            try:
                audit_action = None
                audit_details = None

                if new_status == "APPROVED":
                    record = conn.execute(
                        """
                        SELECT
                            hardware_id,
                            borrow_qty,
                            username
                        FROM borrow_records
                        WHERE
                            id = %s
                            AND status = 'PENDING'
                        """,
                        (record_id,),
                    ).fetchone()

                    if record:
                        hw_id = record["hardware_id"]
                        qty = record["borrow_qty"]
                        student = record["username"]

                        cursor = conn.execute(
                            """
                            UPDATE hardware
                            SET
                                stock_qty =
                                    stock_qty - %s
                            WHERE
                                id = %s
                                AND stock_qty >= %s
                            """,
                            (
                                qty,
                                hw_id,
                                qty,
                            ),
                        )

                        if cursor.rowcount == 0:
                            conn.rollback()
                            return False

                        remaining_stock = conn.execute(
                            """
                            SELECT stock_qty
                            FROM hardware
                            WHERE id = %s
                            """,
                            (hw_id,),
                        ).fetchone()["stock_qty"]

                        conn.execute(
                            """
                            UPDATE hardware
                            SET status = %s
                            WHERE id = %s
                            """,
                            (
                                self.get_stock_status(
                                    remaining_stock
                                ),
                                hw_id,
                            ),
                        )

                        audit_action = (
                            "APPROVE_REQUEST"
                        )

                        audit_details = (
                            f"Approved request "
                            f"#{record_id} for "
                            f"{student} ({qty}x {hw_id})"
                        )

                elif new_status == "DECLINED":
                    record = conn.execute(
                        """
                        SELECT username
                        FROM borrow_records
                        WHERE
                            id = %s
                            AND status = 'PENDING'
                        """,
                        (record_id,),
                    ).fetchone()

                    if record:
                        audit_action = (
                            "DECLINE_REQUEST"
                        )

                        audit_details = (
                            f"Declined request "
                            f"#{record_id} for "
                            f"{record['username']}"
                        )

                if not audit_action:
                    conn.rollback()
                    return False

                checked_out_at = (
                    datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    if new_status == "APPROVED"
                    else None
                )

                conn.execute(
                    """
                    UPDATE borrow_records
                    SET
                        status = %s,
                        approved_by = %s,
                        checked_out_at =
                            COALESCE(
                                %s,
                                checked_out_at
                            )
                    WHERE id = %s
                    """,
                    (
                        new_status,
                        admin_username,
                        checked_out_at,
                        record_id,
                    ),
                )

                conn.commit()

            finally:
                conn.close()

            self.log_audit(
                audit_action,
                audit_details,
                performed_by=admin_username,
            )

            self.notify_observers()

            return True

        except Exception as error:
            print(
                "Error updating request status:",
                error,
            )
            return False

    # ------------------------------------------------------------------
    # REQUEST RETURN
    # ------------------------------------------------------------------

    def request_return(
        self,
        record_id,
        username,
    ):
        try:
            conn = self._get_connection()

            try:
                cursor = conn.execute(
                    """
                    UPDATE borrow_records
                    SET status = 'RETURN_REQUESTED'
                    WHERE
                        id = %s
                        AND username = %s
                        AND status = 'APPROVED'
                    """,
                    (
                        record_id,
                        username,
                    ),
                )

                if cursor.rowcount == 0:
                    conn.rollback()
                    return False

                conn.commit()

            finally:
                conn.close()

            self.log_audit(
                "RETURN_REQUESTED",
                f"Return requested for record #{record_id}",
                performed_by=username,
            )

            self.notify_observers()

            return True

        except Exception as error:
            print(
                "Return Request Error:",
                error,
            )
            return False