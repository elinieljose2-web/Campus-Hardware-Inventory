import os
from datetime import datetime, timedelta

import psycopg
from dotenv import load_dotenv
from supplementary_auth import is_password_strong, hash_password
from werkzeug.security import check_password_hash


class AuthController:
    def __init__(self):
        load_dotenv(override=True)

        self.database_url = os.getenv("DATABASE_URL")

        if not self.database_url:
            raise RuntimeError("DATABASE_URL is not configured.")

    def _get_connection(self):
        return psycopg.connect(self.database_url)

    def _hash_password(self, password):
        """Hashes passwords using the shared project helper."""
        return hash_password(password)

    def _hash_recovery_keyword(self, keyword):
        return hash_password(keyword.strip().casefold())

    def _password_error(self, password):
        ok, message = is_password_strong(password)
        return None if ok else message

    def _get_user(self, username):
        conn = self._get_connection()

        try:
            cur = conn.cursor()

            cur.execute(
                """
                SELECT
                    id,
                    username,
                    email,
                    password_hash,
                    role,
                    failed_attempts,
                    is_locked,
                    recovery_keyword_hash,
                    locked_until,
                    email_verified,
                    otp_hash,
                    otp_expires_at,
                    otp_attempts,
                    otp_last_sent_at
                FROM public.users
                WHERE username = %s
                """,
                (username,),
            )

            row = cur.fetchone()

            if not row:
                return None

            columns = [
                "id",
                "username",
                "email",
                "password_hash",
                "role",
                "failed_attempts",
                "is_locked",
                "recovery_keyword_hash",
                "locked_until",
                "email_verified",
                "otp_hash",
                "otp_expires_at",
                "otp_attempts",
                "otp_last_sent_at",
            ]

            return dict(zip(columns, row))

        finally:
            conn.close()

    def register_user(
        self,
        username,
        email,
        password,
        recovery_keyword,
        role="STUDENT",
    ):
        error = self._registration_error(
            username,
            email,
            password,
            recovery_keyword,
            role,
        )

        if error:
            return False, error

        conn = self._get_connection()

        try:
            cur = conn.cursor()

            cur.execute(
                """
                SELECT 1
                FROM public.users
                WHERE LOWER(username) = LOWER(%s)
                """,
                (username,),
            )

            if cur.fetchone():
                return False, "Username already exists."

            cur.execute(
                """
                INSERT INTO public.users (
                    username,
                    email,
                    password_hash,
                    role,
                    failed_attempts,
                    is_locked,
                    recovery_keyword_hash,
                    locked_until,
                    email_verified,
                    otp_hash,
                    otp_expires_at,
                    otp_attempts,
                    otp_last_sent_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                """,
                (
                    username,
                    email,
                    self._hash_password(password),
                    role.upper(),
                    0,
                    0,
                    self._hash_recovery_keyword(recovery_keyword),
                    None,
                    True,
                    None,
                    None,
                    0,
                    None,
                ),
            )

            conn.commit()

            return True, "Registration successful! You can now log in."

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

    def _registration_error(
        self,
        username,
        email,
        password,
        recovery_keyword,
        role,
    ):
        password_error = self._password_error(password)

        if password_error:
            return password_error

        if not recovery_keyword or len(recovery_keyword.strip()) < 3:
            return "Recovery keyword must be at least 3 characters long."

        if not username or not email or "@" not in email:
            return "Please enter a valid username and email address."

        if role.upper() not in {"STUDENT", "ADMIN"}:
            return "Please select a valid account type."

        return None

    def register_pending_user(
        self,
        username,
        email,
        password,
        recovery_keyword,
        otp_hash,
        otp_expires_at,
        otp_sent_at,
        role="STUDENT",
    ):
        error = self._registration_error(
            username,
            email,
            password,
            recovery_keyword,
            role,
        )

        if error:
            return False, error

        conn = self._get_connection()

        try:
            cur = conn.cursor()

            cur.execute(
                """
                SELECT 1
                FROM public.users
                WHERE LOWER(username) = LOWER(%s)
                """,
                (username,),
            )

            if cur.fetchone():
                return False, "Username already exists."

            cur.execute(
                """
                SELECT 1
                FROM public.users
                WHERE LOWER(email) = LOWER(%s)
                  AND email_verified = FALSE
                """,
                (email,),
            )

            if cur.fetchone():
                return (
                    False,
                    "An unverified account already uses this email. "
                    "Log in to resend its code.",
                )

            cur.execute(
                """
                INSERT INTO public.users (
                    username,
                    email,
                    password_hash,
                    role,
                    failed_attempts,
                    is_locked,
                    recovery_keyword_hash,
                    locked_until,
                    email_verified,
                    otp_hash,
                    otp_expires_at,
                    otp_attempts,
                    otp_last_sent_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                """,
                (
                    username,
                    email,
                    self._hash_password(password),
                    role.upper(),
                    0,
                    0,
                    self._hash_recovery_keyword(recovery_keyword),
                    None,
                    False,
                    otp_hash,
                    otp_expires_at,
                    0,
                    otp_sent_at,
                ),
            )

            conn.commit()

            return True, "Verification code sent."

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

    def get_email_verification_status(self, username):
        user = self._get_user(username)

        if not user:
            return None

        return {
            "email": user.get("email", ""),
            "email_verified": user.get("email_verified", True),
            "otp_expires_at": user.get("otp_expires_at"),
            "otp_attempts": user.get("otp_attempts", 0),
            "otp_last_sent_at": user.get("otp_last_sent_at"),
        }

    def set_email_otp(
        self,
        username,
        otp_hash,
        otp_expires_at,
        otp_sent_at,
    ):
        conn = self._get_connection()

        try:
            cur = conn.cursor()

            cur.execute(
                """
                UPDATE public.users
                SET
                    otp_hash = %s,
                    otp_expires_at = %s,
                    otp_attempts = 0,
                    otp_last_sent_at = %s
                WHERE username = %s
                  AND email_verified = FALSE
                """,
                (
                    otp_hash,
                    otp_expires_at,
                    otp_sent_at,
                    username,
                ),
            )

            updated = cur.rowcount > 0
            conn.commit()

            return updated

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

    def clear_email_otp_cooldown(self, username):
        conn = self._get_connection()

        try:
            cur = conn.cursor()

            cur.execute(
                """
                UPDATE public.users
                SET otp_last_sent_at = NULL
                WHERE username = %s
                  AND email_verified = FALSE
                """,
                (username,),
            )

            updated = cur.rowcount > 0
            conn.commit()

            return updated

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

    def verify_email_otp(self, username, submitted_otp, now):
        user = self._get_user(username)

        if not user:
            return "not_found"

        if user.get("email_verified", True):
            return "already_verified"

        if not user.get("otp_hash") or not user.get("otp_expires_at"):
            return "no_code"

        if user.get("otp_attempts", 0) >= 5:
            return "max_attempts"

        expires_at = datetime.fromisoformat(user["otp_expires_at"])

        if expires_at <= datetime.fromisoformat(now):
            return "expired"

        if not check_password_hash(user["otp_hash"], submitted_otp):
            conn = self._get_connection()

            try:
                cur = conn.cursor()

                new_attempts = user.get("otp_attempts", 0) + 1

                cur.execute(
                    """
                    UPDATE public.users
                    SET otp_attempts = %s
                    WHERE username = %s
                    """,
                    (
                        new_attempts,
                        username,
                    ),
                )

                conn.commit()

            finally:
                conn.close()

            return "max_attempts" if new_attempts >= 5 else "invalid"

        conn = self._get_connection()

        try:
            cur = conn.cursor()

            cur.execute(
                """
                UPDATE public.users
                SET
                    email_verified = TRUE,
                    otp_hash = NULL,
                    otp_expires_at = NULL,
                    otp_attempts = 0,
                    otp_last_sent_at = NULL
                WHERE username = %s
                """,
                (username,),
            )

            conn.commit()

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

        return "verified"

    def login_user(self, username, password):
        user = self._get_user(username)

        if not user:
            return False, "User not found."

        locked_until = user.get("locked_until")

        if locked_until:
            try:
                if datetime.now() < datetime.fromisoformat(locked_until):
                    return (
                        False,
                        "Account temporarily locked after failed attempts. "
                        "Try again later.",
                    )
            except (ValueError, TypeError):
                locked_until = None

        if user["password_hash"] != self._hash_password(password):
            failed_attempts = user.get("failed_attempts", 0) + 1

            if failed_attempts >= 5:
                new_locked_until = (
                    datetime.now() + timedelta(minutes=5)
                ).isoformat(timespec="seconds")

                message = (
                    "Account locked for 5 minutes after too many "
                    "failed attempts."
                )
            else:
                new_locked_until = None
                message = "Incorrect password."

            conn = self._get_connection()

            try:
                cur = conn.cursor()

                cur.execute(
                    """
                    UPDATE public.users
                    SET
                        failed_attempts = %s,
                        locked_until = %s,
                        is_locked = %s
                    WHERE username = %s
                    """,
                    (
                        failed_attempts,
                        new_locked_until,
                        1 if failed_attempts >= 5 else 0,
                        username,
                    ),
                )

                conn.commit()

            except Exception:
                conn.rollback()
                raise

            finally:
                conn.close()

            return False, message

        if user.get("email_verified", True) is False:
            return (
                False,
                "Please verify your email address before logging in.",
            )

        conn = self._get_connection()

        try:
            cur = conn.cursor()

            cur.execute(
                """
                UPDATE public.users
                SET
                    failed_attempts = 0,
                    locked_until = NULL,
                    is_locked = 0
                WHERE username = %s
                """,
                (username,),
            )

            conn.commit()

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

        return True, {
            "username": username,
            "email": user["email"],
            "role": user["role"],
        }

    def reset_password(
        self,
        username,
        email,
        recovery_keyword,
        new_password,
    ):
        user = self._get_user(username)

        if not user or user["email"].lower() != email.lower():
            return False, "Invalid username or email match."

        stored_keyword = user.get("recovery_keyword_hash")

        if not stored_keyword:
            return (
                False,
                "This account has no recovery keyword configured. "
                "Contact an administrator.",
            )

        if stored_keyword != self._hash_recovery_keyword(recovery_keyword):
            return False, "Invalid recovery keyword."

        password_error = self._password_error(new_password)

        if password_error:
            return False, password_error

        conn = self._get_connection()

        try:
            cur = conn.cursor()

            cur.execute(
                """
                UPDATE public.users
                SET
                    password_hash = %s,
                    failed_attempts = 0,
                    locked_until = NULL,
                    is_locked = 0
                WHERE username = %s
                """,
                (
                    self._hash_password(new_password),
                    username,
                ),
            )

            conn.commit()

            return True, "Password reset successfully!"

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

    def get_users(self):
        conn = self._get_connection()

        try:
            cur = conn.cursor()

            cur.execute(
                """
                SELECT username, email, role
                FROM public.users
                ORDER BY id
                """
            )

            return [
                {
                    "username": row[0],
                    "email": row[1],
                    "role": row[2],
                }
                for row in cur.fetchall()
            ]

        finally:
            conn.close()

    def set_user_role(self, username, role):
        if role.upper() not in ("ADMIN", "STUDENT"):
            return False

        conn = self._get_connection()

        try:
            cur = conn.cursor()

            cur.execute(
                """
                UPDATE public.users
                SET role = %s
                WHERE username = %s
                """,
                (
                    role.upper(),
                    username,
                ),
            )

            updated = cur.rowcount > 0
            conn.commit()

            return updated

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

    def delete_user(self, username):
        if username.lower() == "admin":
            return False

        conn = self._get_connection()

        try:
            cur = conn.cursor()

            cur.execute(
                """
                DELETE FROM public.users
                WHERE username = %s
                """,
                (username,),
            )

            deleted = cur.rowcount > 0
            conn.commit()

            return deleted

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()

    def admin_reset_password(self, username, new_password):
        password_error = self._password_error(new_password)

        if password_error:
            return False

        conn = self._get_connection()

        try:
            cur = conn.cursor()

            cur.execute(
                """
                UPDATE public.users
                SET
                    password_hash = %s,
                    failed_attempts = 0,
                    locked_until = NULL,
                    is_locked = 0
                WHERE username = %s
                """,
                (
                    self._hash_password(new_password),
                    username,
                ),
            )

            updated = cur.rowcount > 0
            conn.commit()

            return updated

        except Exception:
            conn.rollback()
            raise

        finally:
            conn.close()