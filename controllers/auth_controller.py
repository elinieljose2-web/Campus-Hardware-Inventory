import json
import os
from datetime import datetime, timedelta
from supplementary_auth import is_password_strong, hash_password

class AuthController:
    def __init__(self, db_path="database/users.json"):
        self.db_path = db_path
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """Creates the directory and JSON file if they don't exist."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        if not os.path.exists(self.db_path):
            # Seed with a default admin account
            default_data = {
                "admin": {
                    "email": "admin@lab.edu",
                    "password_hash": self._hash_password("Admin123!"),
                    "role": "ADMIN",
                    "failed_attempts": 0,
                    "locked_until": None
                }
            }
            self._save_users(default_data)

    def _load_users(self):
        """Loads users from the JSON file."""
        try:
            with open(self.db_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_users(self, users):
        """Saves users to the JSON file."""
        with open(self.db_path, "w") as f:
            json.dump(users, f, indent=4)

    def _hash_password(self, password):
        """Hashes passwords using the shared project helper."""
        return hash_password(password)

    def _hash_recovery_keyword(self, keyword):
        return hash_password(keyword.strip().casefold())

    def _password_error(self, password):
        ok, message = is_password_strong(password)
        return None if ok else message

    def register_user(self, username, email, password, recovery_keyword, role="STUDENT"):
        users = self._load_users()

        password_error = self._password_error(password)
        if password_error:
            return False, password_error
        if not recovery_keyword or len(recovery_keyword.strip()) < 3:
            return False, "Recovery keyword must be at least 3 characters long."
        role = role.upper()
        if role not in {"STUDENT", "ADMIN"}:
            return False, "Please select a valid account type."

        # Check if username already exists
        if username.lower() in [u.lower() for u in users.keys()]:
            return False, "Username already exists."

        # Store new user
        users[username] = {
            "email": email,
            "password_hash": self._hash_password(password),
            "recovery_keyword_hash": self._hash_recovery_keyword(recovery_keyword),
            "role": role,
            "failed_attempts": 0,
            "locked_until": None
        }

        # Save to disk
        self._save_users(users)
        return True, "Registration successful! You can now log in."

    def login_user(self, username, password):
        users = self._load_users()
        user = users.get(username)

        if not user:
            return False, "User not found."

        locked_until = user.get("locked_until")
        if locked_until:
            try:
                if datetime.now() < datetime.fromisoformat(locked_until):
                    return False, "Account temporarily locked after failed attempts. Try again later."
            except ValueError:
                user["locked_until"] = None

        if user["password_hash"] != self._hash_password(password):
            user["failed_attempts"] = user.get("failed_attempts", 0) + 1
            if user["failed_attempts"] >= 5:
                user["locked_until"] = (datetime.now() + timedelta(minutes=5)).isoformat(timespec="seconds")
                message = "Account locked for 5 minutes after too many failed attempts."
            else:
                message = "Incorrect password."
            users[username] = user
            self._save_users(users)
            return False, message

        user["failed_attempts"] = 0
        user["locked_until"] = None
        users[username] = user
        self._save_users(users)

        return True, {
            "username": username,
            "email": user["email"],
            "role": user["role"]
        }

    def reset_password(self, username, email, recovery_keyword, new_password):
        users = self._load_users()
        user = users.get(username)

        if not user or user["email"].lower() != email.lower():
            return False, "Invalid username or email match."
        stored_keyword = user.get("recovery_keyword_hash")
        if not stored_keyword:
            return False, "This account has no recovery keyword configured. Contact an administrator."
        if stored_keyword != self._hash_recovery_keyword(recovery_keyword):
            return False, "Invalid recovery keyword."

        password_error = self._password_error(new_password)
        if password_error:
            return False, password_error

        users[username]["password_hash"] = self._hash_password(new_password)
        users[username]["failed_attempts"] = 0
        users[username]["locked_until"] = None
        self._save_users(users)
        return True, "Password reset successfully!"

    def get_users(self):
        return [
            {"username": username, "email": details.get("email", ""), "role": details.get("role", "STUDENT")}
            for username, details in self._load_users().items()
        ]

    def set_user_role(self, username, role):
        users = self._load_users()
        if username not in users or role.upper() not in ("ADMIN", "STUDENT"):
            return False
        users[username]["role"] = role.upper()
        self._save_users(users)
        return True

    def delete_user(self, username):
        users = self._load_users()
        if username not in users or username.lower() == "admin":
            return False
        del users[username]
        self._save_users(users)
        return True

    def admin_reset_password(self, username, new_password):
        users = self._load_users()
        if username not in users or self._password_error(new_password):
            return False
        users[username]["password_hash"] = self._hash_password(new_password)
        users[username]["failed_attempts"] = 0
        users[username]["locked_until"] = None
        self._save_users(users)
        return True