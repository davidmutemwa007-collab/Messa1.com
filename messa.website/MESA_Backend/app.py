"""MESA Kitchen & Social — self-contained Python/SQLite web application.

Uses only the Python standard library. Run with: python app.py
"""
from __future__ import annotations

import base64
import csv
import hashlib
import hmac
import html
import io
import json
import mimetypes
import os
import re
import secrets
import socket
import sqlite3
import struct
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = Path(os.environ.get("MESA_FRONTEND_DIR", BASE_DIR.parent / "MESA_Frontend")).resolve()
DATABASE = Path(os.environ.get("MESA_DATABASE", BASE_DIR / "data" / "mesa.sqlite3"))
UPLOAD_DIR = Path(os.environ.get("MESA_UPLOAD_DIR", BASE_DIR / "data" / "uploads")).resolve()
MAX_REQUEST_BYTES = 6 * 1024 * 1024

ROLE_LABELS = {
    "super_admin": "Super Administrator",
    "restaurant_admin": "Restaurant Administrator",
    "manager": "Manager",
    "cashier": "Cashier",
    "kitchen_staff": "Kitchen Staff",
    "delivery_staff": "Delivery Staff",
    "customer": "Customer",
}
ROLE_PERMISSIONS = {
    "super_admin": {"*"},
    "restaurant_admin": {"dashboard", "orders.read", "orders.update", "bookings.read", "bookings.update", "customers.read", "customers.access", "menu.read", "menu.write", "payments.read", "payments.review", "payments.configure", "delivery.read", "delivery.write", "delivery.update", "content.read", "content.write", "reports.read", "reports.export", "audit.read"},
    "manager": {"dashboard", "orders.read", "orders.update", "bookings.read", "bookings.update", "customers.read", "menu.read", "menu.write", "payments.read", "delivery.read", "delivery.write", "delivery.update", "reports.read", "reports.export", "audit.read"},
    "cashier": {"dashboard", "orders.read", "orders.update", "payments.read", "payments.review"},
    "kitchen_staff": {"dashboard", "orders.read", "orders.kitchen_update"},
    "delivery_staff": {"dashboard", "delivery.read", "delivery.update"},
    "customer": set(),
}

MENU: list[dict[str, Any]] = [
    {"id": "mesa-smash", "name": "MESA Smash Burger", "description": "Double-seared beef, cheddar, crisp lettuce, house sauce, toasted brioche.", "price": 88, "category": "Burgers", "tag": "Bestseller", "art": "burger", "vegetarian": False},
    {"id": "garden-stack", "name": "Garden Stack", "description": "Grilled halloumi, avocado, tomato, greens and basil mayo.", "price": 76, "category": "Burgers", "tag": "Fresh pick", "art": "burgerVeg", "vegetarian": True},
    {"id": "fire-pizza", "name": "The Firehouse Pizza", "description": "Stone-baked crust, mozzarella, pepperoni, basil and a little heat.", "price": 148, "category": "Pizza", "tag": "Fan favourite", "art": "pizza", "vegetarian": False},
    {"id": "market-pizza", "name": "Market Garden Pizza", "description": "Roasted peppers, mushrooms, olives, mozzarella and garden herbs.", "price": 132, "category": "Pizza", "tag": "Vegetarian", "art": "pizzaVeg", "vegetarian": True},
    {"id": "golden-fries", "name": "Golden Parmesan Fries", "description": "Hand-cut fries, parmesan snow, parsley and smoky house dip.", "price": 38, "category": "Sides", "tag": "Perfect side", "art": "fries", "vegetarian": True},
    {"id": "cloud-sundae", "name": "Cloud Nine Sundae", "description": "Vanilla bean scoops, chocolate ribbon, wafer and toasted nuts.", "price": 48, "category": "Desserts", "tag": "Sweet finish", "art": "icecream", "vegetarian": True},
    {"id": "pink-lemonade", "name": "Pink Citrus Fizz", "description": "Fresh lemon, berry, mint and sparkling soda over ice.", "price": 32, "category": "Drinks", "tag": "House-made", "art": "drink", "vegetarian": True},
    {"id": "mango-shake", "name": "Mango Dream Shake", "description": "Real mango, creamy vanilla and a cloud of whipped cream.", "price": 46, "category": "Drinks", "tag": "Cool favourite", "art": "shake", "vegetarian": True},
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'customer',
    is_active INTEGER NOT NULL DEFAULT 1,
    must_change_password INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference TEXT NOT NULL UNIQUE,
    user_id INTEGER,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    booking_date TEXT NOT NULL,
    booking_time TEXT NOT NULL,
    guests INTEGER NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Received',
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reference TEXT NOT NULL UNIQUE,
    user_id INTEGER,
    customer_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    fulfilment TEXT NOT NULL,
    address TEXT NOT NULL DEFAULT '',
    payment_method TEXT NOT NULL,
    items_json TEXT NOT NULL,
    subtotal INTEGER NOT NULL,
    service_fee INTEGER NOT NULL,
    total INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'Received',
    created_at TEXT NOT NULL,
    delivery_zone_id TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS admin_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT, admin_user_id INTEGER NOT NULL, action TEXT NOT NULL,
    target_type TEXT NOT NULL, target_id TEXT NOT NULL DEFAULT '', details TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
    FOREIGN KEY(admin_user_id) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS sessions (
    session_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires_at INTEGER NOT NULL, created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS sessions_expiry_idx ON sessions(expires_at);
CREATE INDEX IF NOT EXISTS orders_created_idx ON orders(created_at);
CREATE INDEX IF NOT EXISTS bookings_date_idx ON bookings(booking_date);
CREATE TABLE IF NOT EXISTS roles (
    name TEXT PRIMARY KEY, label TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS role_permissions (
    role TEXT NOT NULL, permission TEXT NOT NULL, PRIMARY KEY(role,permission),
    FOREIGN KEY(role) REFERENCES roles(name) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS menu_overrides (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL, price INTEGER NOT NULL,
    category TEXT NOT NULL, tag TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1,
    vegetarian INTEGER NOT NULL DEFAULT 0, prep_minutes INTEGER NOT NULL DEFAULT 0,
    is_popular INTEGER NOT NULL DEFAULT 0, image_url TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS delivery_zones (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, region TEXT NOT NULL, fee INTEGER NOT NULL DEFAULT 0,
    estimated_minutes INTEGER NOT NULL DEFAULT 60, minimum_order INTEGER NOT NULL DEFAULT 0,
    free_threshold INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 0,
    instructions TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS payment_methods (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, business_number TEXT NOT NULL DEFAULT '',
    registered_name TEXT NOT NULL DEFAULT '', merchant_info TEXT NOT NULL DEFAULT '',
    instructions TEXT NOT NULL DEFAULT '', qr_image_url TEXT NOT NULL DEFAULT '',
    enabled INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER NOT NULL, transaction_reference TEXT NOT NULL UNIQUE,
    method_id TEXT NOT NULL, amount INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'Payment Submitted',
    customer_note TEXT NOT NULL DEFAULT '', submitted_at TEXT NOT NULL, reviewed_at TEXT NOT NULL DEFAULT '',
    reviewed_by INTEGER, FOREIGN KEY(order_id) REFERENCES orders(id),
    FOREIGN KEY(reviewed_by) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS site_content (
    key TEXT PRIMARY KEY, value TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL, updated_by INTEGER,
    FOREIGN KEY(updated_by) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS delivery_assignments (
    order_id INTEGER PRIMARY KEY, staff_user_id INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'Assigned',
    assigned_at TEXT NOT NULL, FOREIGN KEY(order_id) REFERENCES orders(id),
    FOREIGN KEY(staff_user_id) REFERENCES users(id)
);
"""


def clean_text(value: Any, limit: int = 160) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()[:limit]


def whole_number(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and len(value) <= 12 and re.fullmatch(r"[+-]?\d+", value):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value))

def csv_safe(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    normalized = value.lstrip()
    if normalized.startswith(("=", "+", "-", "@")) or normalized.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


def make_reference(prefix: str) -> str:
    return f"{prefix}-{secrets.token_hex(3).upper()}"


def password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    iterations = 310_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(
        iterations,
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
        expected = base64.urlsafe_b64decode(digest_text.encode("ascii"))
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations_text))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


class MesaApplication:
    """Small request router used by the standard-library HTTP server and tests."""

    def __init__(self, database_path: Path | str = DATABASE, secret_key: str | bytes | None = None):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.secret_key = secret_key.encode("utf-8") if isinstance(secret_key, str) else secret_key
        if not self.secret_key:
            self.secret_key = self._load_or_create_secret()
        self._backup_before_schema_change()
        self._init_db()

    def _backup_before_schema_change(self) -> None:
        if not self.database_path.is_file() or self.database_path.stat().st_size == 0:
            return
        required = {
            "users": {"id", "name", "email", "password_hash", "created_at", "role", "is_active", "must_change_password"},
            "orders": {"delivery_zone_id"},
            "sessions": {"session_hash", "user_id", "expires_at"},
            "roles": {"name", "label"},
            "role_permissions": {"role", "permission"},
            "menu_overrides": {"vegetarian", "prep_minutes", "is_popular", "image_url"},
            "delivery_zones": {"id", "name", "fee", "active"},
            "payment_methods": {"id", "name", "enabled"},
            "payments": {"id", "order_id", "status"},
            "site_content": {"key", "value"},
            "delivery_assignments": {"order_id", "staff_user_id", "status"},
        }
        source = sqlite3.connect(self.database_path, timeout=15)
        try:
            tables = {
                row[0] for row in source.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if "users" not in tables:
                return
            missing = any(
                table not in tables
                or not columns.issubset({row[1] for row in source.execute(f"PRAGMA table_info({table})")})
                for table, columns in required.items()
            )
            if not missing:
                return
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            backup = self.database_path.with_name(
                f"{self.database_path.name}.backup-pre-schema-{stamp}"
            )
            destination = sqlite3.connect(backup)
            try:
                source.backup(destination)
            finally:
                destination.close()
            print(f"MESA database schema backup created: {backup}", file=sys.stderr)
        except sqlite3.Error as exc:
            raise RuntimeError(f"Cannot safely back up the database before schema changes: {exc}") from exc
        finally:
            source.close()

    def _load_or_create_secret(self) -> bytes:
        env_secret = os.environ.get("MESA_SECRET_KEY")
        if env_secret:
            if len(env_secret.encode("utf-8")) < 32:
                raise RuntimeError("MESA_SECRET_KEY must contain at least 32 bytes.")
            return env_secret.encode("utf-8")
        secret_path = BASE_DIR / "data" / "secret.key"
        secret_path.parent.mkdir(parents=True, exist_ok=True)
        if secret_path.exists():
            secret = secret_path.read_bytes()
            if len(secret) < 32:
                raise RuntimeError(f"Session key at {secret_path} is too short; replace it securely before starting.")
            return secret
        secret = secrets.token_bytes(48)
        try:
            secret_path.write_bytes(secret)
        except OSError as exc:
            raise RuntimeError(f"Cannot persist the session key at {secret_path}: {exc}") from exc
        return secret

    @contextmanager
    def _db(self):
        conn = sqlite3.connect(self.database_path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._db() as db:
            db.executescript(SCHEMA)
            migrations = {
                "users": {
                    "role": "TEXT NOT NULL DEFAULT 'customer'",
                    "is_active": "INTEGER NOT NULL DEFAULT 1",
                    "must_change_password": "INTEGER NOT NULL DEFAULT 0",
                },
                "orders": {"delivery_zone_id": "TEXT NOT NULL DEFAULT ''"},
                "menu_overrides": {
                    "vegetarian": "INTEGER NOT NULL DEFAULT 0",
                    "prep_minutes": "INTEGER NOT NULL DEFAULT 0",
                    "is_popular": "INTEGER NOT NULL DEFAULT 0",
                    "image_url": "TEXT NOT NULL DEFAULT ''",
                },
            }
            for table, columns in migrations.items():
                existing = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
                for column, definition in columns.items():
                    if column not in existing:
                        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            db.execute("UPDATE users SET role='super_admin' WHERE role='admin'")
            db.execute("CREATE INDEX IF NOT EXISTS payments_order_idx ON payments(order_id)")
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            for role, label in ROLE_LABELS.items():
                db.execute("INSERT OR IGNORE INTO roles(name,label) VALUES(?,?)", (role, label))
                for permission in ROLE_PERMISSIONS.get(role, set()):
                    db.execute("INSERT OR IGNORE INTO role_permissions(role,permission) VALUES(?,?)", (role, permission))
            for method_id, name in (
                ("mtn-mobile-money", "MTN Mobile Money"),
                ("airtel-money", "Airtel Money"),
                ("zamtel-kwacha", "Zamtel Kwacha"),
            ):
                db.execute(
                    "INSERT OR IGNORE INTO payment_methods(id,name,updated_at) VALUES(?,?,?)",
                    (method_id, name, now),
                )
            zones = (
                ("lusaka-central", "Lusaka Central", "Lusaka"),
                ("kabulonga", "Kabulonga", "Lusaka"),
                ("woodlands", "Woodlands", "Lusaka"),
                ("chelstone", "Chelstone", "Lusaka"),
                ("chilenje", "Chilenje", "Lusaka"),
                ("matero", "Matero", "Lusaka"),
                ("kanyama", "Kanyama", "Lusaka"),
                ("chongwe", "Chongwe", "Lusaka"),
            )
            for zone_id, name, region in zones:
                db.execute(
                    """INSERT OR IGNORE INTO delivery_zones
                       (id,name,region,created_at,updated_at) VALUES(?,?,?,?,?)""",
                    (zone_id, name, region, now, now),
                )
            for key, value in {
                "announcement": "GOOD FOOD. GREAT COMPANY. THAT'S THE MESA WAY.",
                "hero_lede": "Good ingredients. Generous plates. The kind of food that turns an ordinary day into a reason to gather.",
                "restaurant_description": "Thoughtful food, generous hospitality and a seat saved just for you.",
                "opening_hours": "",
                "phone": "",
                "address": "",
                "social_links": "",
                "hero_image": "",
            }.items():
                db.execute(
                    "INSERT OR IGNORE INTO site_content(key,value,updated_at) VALUES(?,?,?)",
                    (key, value, now),
                )

    def _session_cookie(self, user_id: int) -> str:
        expiry = int(time.time()) + 7 * 24 * 60 * 60
        session_id = secrets.token_urlsafe(32)
        payload = f"{int(user_id)}.{expiry}.{session_id}"
        signature = hmac.new(self.secret_key, payload.encode("ascii"), hashlib.sha256).hexdigest()
        session_hash = hashlib.sha256(session_id.encode("ascii")).hexdigest()
        with self._db() as db:
            db.execute("DELETE FROM sessions WHERE expires_at < ?", (int(time.time()),))
            db.execute(
                "INSERT INTO sessions (session_hash,user_id,expires_at,created_at) VALUES (?,?,?,?)",
                (session_hash, user_id, expiry, datetime.now(timezone.utc).isoformat(timespec="seconds")),
            )
        token = f"{payload}.{signature}"
        secure = os.environ.get("MESA_COOKIE_SECURE", "").lower() in {"1", "true", "yes"} or os.environ.get("MESA_ENV", "").lower() == "production"
        secure_attribute = "; Secure" if secure else ""
        return f"mesa_session={token}; Path=/; Max-Age=604800; HttpOnly; SameSite=Lax{secure_attribute}"

    def _clear_cookie(self) -> str:
        secure = os.environ.get("MESA_COOKIE_SECURE", "").lower() in {"1", "true", "yes"} or os.environ.get("MESA_ENV", "").lower() == "production"
        secure_attribute = "; Secure" if secure else ""
        return f"mesa_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax{secure_attribute}"

    def _public_url(self) -> str:
        value = os.environ.get("MESA_PUBLIC_URL", "").strip().rstrip("/")
        try:
            parsed = urlsplit(value)
            if (parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password
                    or parsed.path or parsed.query or parsed.fragment
                    or (os.environ.get("MESA_ENV", "").lower() == "production" and parsed.scheme != "https")):
                return ""
            parsed.port
        except ValueError:
            return ""
        return value

    def _menu_catalog(self) -> list[dict[str, Any]]:
        items = {item["id"]: {**item, "image": "", "popular": False, "prep_minutes": 0, "active": True} for item in MENU}
        with self._db() as db:
            exists = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='menu_overrides'"
            ).fetchone()
            if exists:
                for row in db.execute(
                    """SELECT id,name,description,price,category,tag,active,vegetarian,
                              prep_minutes,is_popular,image_url FROM menu_overrides"""
                ):
                    base = items.get(row["id"], {"id": row["id"], "art": "food", "vegetarian": False})
                    items[row["id"]] = {
                        **base,
                        "name": row["name"],
                        "description": row["description"],
                        "price": row["price"],
                        "category": row["category"],
                        "tag": row["tag"],
                        "active": bool(row["active"]),
                        "vegetarian": bool(row["vegetarian"]),
                        "prep_minutes": row["prep_minutes"],
                        "popular": bool(row["is_popular"]),
                        "image": row["image_url"],
                    }
        return list(items.values())

    def _store_image(self, value: Any) -> str:
        if not isinstance(value, str) or not value.startswith("data:") or ";base64," not in value:
            raise ValueError("Choose a JPEG, PNG, or WebP image.")
        _, encoded = value.split(";base64,", 1)
        try:
            content = base64.b64decode(encoded, validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise ValueError("The image upload is not valid base64 data.") from exc
        if not content or len(content) > 4 * 1024 * 1024:
            raise ValueError("Images must be smaller than 4 MB.")
        if content.startswith(b"\xff\xd8\xff"):
            extension = "jpg"
        elif content.startswith(b"\x89PNG\r\n\x1a\n"):
            extension = "png"
        elif len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
            extension = "webp"
        else:
            raise ValueError("Only JPEG, PNG, and WebP image files are supported.")
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.{extension}"
        try:
            (UPLOAD_DIR / filename).write_bytes(content)
        except OSError as exc:
            print(f"MESA image upload failed: {type(exc).__name__}", file=sys.stderr)
            raise RuntimeError("The image could not be stored. Check persistent upload storage.") from exc
        return f"/uploads/{filename}"

    def _admin_analytics(self):
        today = date.today()
        start = today - timedelta(days=6)
        month_start = today.replace(day=1)
        today_start = today.isoformat() + "T00:00:00"
        tomorrow_start = (today + timedelta(days=1)).isoformat() + "T00:00:00"
        with self._db() as db:
            weekly = db.execute(
                "SELECT COALESCE(SUM(total),0),COUNT(*) FROM orders WHERE created_at>=? AND created_at<? AND status NOT IN ('Cancelled','Rejected')",
                (start.isoformat() + "T00:00:00", tomorrow_start),
            ).fetchone()
            monthly = db.execute(
                "SELECT COALESCE(SUM(total),0),COUNT(*) FROM orders WHERE created_at>=? AND created_at<? AND status NOT IN ('Cancelled','Rejected')",
                (month_start.isoformat() + "T00:00:00", tomorrow_start),
            ).fetchone()
            revenue_today = db.execute(
                "SELECT COALESCE(SUM(total),0) FROM orders WHERE created_at>=? AND created_at<? AND status NOT IN ('Cancelled','Rejected')",
                (today_start, tomorrow_start),
            ).fetchone()[0]
            overall = db.execute(
                """SELECT COALESCE(SUM(CASE WHEN status NOT IN ('Cancelled','Rejected') THEN total ELSE 0 END),0),
                          COUNT(*),SUM(CASE WHEN status='Completed' THEN 1 ELSE 0 END),
                          SUM(CASE WHEN status IN ('Cancelled','Rejected') THEN 1 ELSE 0 END)
                   FROM orders"""
            ).fetchone()
            completed = db.execute(
                "SELECT COALESCE(AVG(total),0) FROM orders WHERE status='Completed'"
            ).fetchone()[0]
            new_customers = db.execute(
                "SELECT COUNT(*) FROM users WHERE created_at>=?",
                ((today - timedelta(days=6)).isoformat() + "T00:00:00",),
            ).fetchone()[0]
            daily_rows = db.execute(
                """SELECT substr(created_at,1,10) AS day,COALESCE(SUM(total),0) AS revenue
                   FROM orders WHERE created_at>=? AND created_at<? AND status NOT IN ('Cancelled','Rejected')
                   GROUP BY substr(created_at,1,10)""",
                (start.isoformat() + "T00:00:00", tomorrow_start),
            ).fetchall()
            item_rows = db.execute("SELECT items_json FROM orders WHERE status NOT IN ('Cancelled','Rejected')").fetchall()
        daily = {row["day"]: row["revenue"] for row in daily_rows}
        popular: dict[str, int] = {}
        for row in item_rows:
            try:
                for item in json.loads(row["items_json"]):
                    name = clean_text(item.get("name"), 100)
                    quantity = whole_number(item.get("quantity"))
                    if name and quantity is not None:
                        popular[name] = popular.get(name, 0) + quantity
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        return {
            "revenue_today": revenue_today,
            "revenue_week": weekly[0],
            "revenue_month": monthly[0],
            "total_revenue": overall[0],
            "total_orders": overall[1],
            "completed_orders": overall[2] or 0,
            "cancelled_orders": overall[3] or 0,
            "new_customers": new_customers,
            "average_order_value": completed,
            "daily_sales": [{"date": (start + timedelta(days=i)).isoformat(), "revenue": daily.get((start + timedelta(days=i)).isoformat(), 0)} for i in range(7)],
            "popular_items": [{"name": name, "quantity": quantity} for name, quantity in sorted(popular.items(), key=lambda entry: entry[1], reverse=True)[:10]],
        }

    def _user_id(self, headers: dict[str, str]) -> int | None:
        cookie_header = headers.get("Cookie", "")
        match = re.search(r"(?:^|;\s*)mesa_session=([^;]+)", cookie_header)
        if not match:
            return None
        try:
            user_text, expiry_text, session_id, supplied_sig = match.group(1).split(".", 3)
            payload = f"{user_text}.{expiry_text}.{session_id}"
            expected_sig = hmac.new(self.secret_key, payload.encode("ascii"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(supplied_sig, expected_sig) or int(expiry_text) < int(time.time()):
                return None
            user_id = int(user_text)
            session_hash = hashlib.sha256(session_id.encode("ascii")).hexdigest()
            with self._db() as db:
                exists = db.execute(
                    """SELECT 1 FROM sessions s JOIN users u ON u.id=s.user_id
                       WHERE s.session_hash=? AND s.user_id=? AND s.expires_at=? AND s.expires_at>=? AND u.is_active=1""",
                    (session_hash, user_id, int(expiry_text), int(time.time())),
                ).fetchone()
            return user_id if exists else None
        except (ValueError, TypeError):
            return None

    def _revoke_session(self, headers: dict[str, str]) -> None:
        cookie_header = headers.get("Cookie", "")
        match = re.search(r"(?:^|;\s*)mesa_session=([^;]+)", cookie_header)
        if not match:
            return
        try:
            user_text, expiry_text, session_id, supplied_sig = match.group(1).split(".", 3)
            payload = f"{user_text}.{expiry_text}.{session_id}"
            expected_sig = hmac.new(self.secret_key, payload.encode("ascii"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(supplied_sig, expected_sig):
                return
            user_id = int(user_text)
            session_hash = hashlib.sha256(session_id.encode("ascii")).hexdigest()
            with self._db() as db:
                db.execute("DELETE FROM sessions WHERE session_hash=? AND user_id=?", (session_hash, user_id))
        except (ValueError, TypeError):
            return

    @staticmethod
    def _json(status: int, data: dict[str, Any], extra_headers: dict[str, str] | None = None):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"}
        if extra_headers:
            headers.update(extra_headers)
        return status, body, headers

    def _error(self, message: str, status: int = 400):
        return self._json(status, {"ok": False, "message": message})

    def _read_json(self, body: bytes) -> dict[str, Any]:
        try:
            parsed = json.loads(body.decode("utf-8")) if body else {}
            return parsed if isinstance(parsed, dict) else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}

    def _same_origin(self, headers: dict[str, str]) -> bool:
        origin = headers.get("Origin")
        if not origin:
            return True
        host = headers.get("Host", "")
        try:
            parsed = urlsplit(origin)
            return parsed.scheme in {"http", "https"} and parsed.netloc.lower() == host.lower()
        except ValueError:
            return False

    def handle(self, method: str, raw_path: str, headers: dict[str, str] | None = None, body: bytes = b""):
        headers = headers or {}
        method = method.upper()
        if method == "HEAD":
            method = "GET"
        parsed_url = urlsplit(raw_path)
        path = parsed_url.path or "/"
        if len(body) > MAX_REQUEST_BYTES:
            return self._json(413, {"ok": False, "message": "That request is too large."})
        if method == "GET" and path == "/":
            page_path = FRONTEND_DIR / "index.html"
            if not page_path.is_file():
                page_path = FRONTEND_DIR / "templates" / "index.html"
            if not page_path.is_file():
                return self._json(503, {"ok": False, "message": "MESA frontend index.html was not found."})
            page = page_path.read_text(encoding="utf-8")
            public_url = self._public_url()
            canonical = f'<link rel="canonical" href="{html.escape(public_url, quote=True)}/">' if public_url else ""
            page = page.replace("<!-- MESA_CANONICAL -->", canonical)
            page = page.replace("<!-- MESA_OG_URL -->", f'<meta property="og:url" content="{html.escape(public_url, quote=True)}/">' if public_url else "")
            page = page.replace("<!-- MESA_OG_IMAGE -->", f'<meta property="og:image" content="{html.escape(public_url, quote=True)}/static/media/mesa-food-spread.jpg">' if public_url else "")
            schema = {
                "@context": "https://schema.org",
                "@type": "Restaurant",
                "name": "MESA Kitchen & Social",
                "description": "Good ingredients, generous plates and a table made for gathering.",
                "url": f"{public_url}/",
                "image": f"{public_url}/static/media/mesa-food-spread.jpg",
            } if public_url else None
            structured_data = ""
            if schema:
                schema_json = json.dumps(schema, ensure_ascii=False).replace("<", "\\u003c")
                structured_data = f'<script type="application/ld+json">{schema_json}</script>'
            page = page.replace("<!-- MESA_JSON_LD -->", structured_data)
            page = page.encode("utf-8")
            return 200, page, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache"}
        if method == "GET" and path == "/robots.txt":
            content = "User-agent: *\nDisallow: /api/\nDisallow: /admin\n"
            public_url = self._public_url()
            if public_url:
                content += f"Sitemap: {public_url}/sitemap.xml\n"
            return 200, content.encode("utf-8"), {"Content-Type": "text/plain; charset=utf-8", "Cache-Control": "public, max-age=3600"}
        if method == "GET" and path == "/sitemap.xml":
            public_url = self._public_url()
            if not public_url:
                return self._json(503, {"ok": False, "message": "Set MESA_PUBLIC_URL to publish the canonical sitemap."})
            sitemap = (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                f"<url><loc>{html.escape(public_url, quote=False)}/</loc></url></urlset>"
            )
            return 200, sitemap.encode("utf-8"), {"Content-Type": "application/xml; charset=utf-8", "Cache-Control": "public, max-age=3600"}
        if method == "GET" and path.startswith("/static/"):
            return self._static(path[len("/static/"):])
        if method == "GET" and path.startswith("/uploads/"):
            return self._uploaded_file(path[len("/uploads/"):])
        if path.startswith("/api/") and method == "POST" and not self._same_origin(headers):
            return self._error("Cross-origin requests are not allowed.", 403)
        if method == "GET" and path == "/api/health":
            try:
                with self._db() as db:
                    db.execute("SELECT 1").fetchone()
            except sqlite3.Error as exc:
                print(f"MESA health check database failure: {type(exc).__name__}", file=sys.stderr)
                return self._json(503, {"ok": False, "message": "Database is unavailable."})
            return self._json(200, {"ok": True, "service": "MESA Backend", "database": "connected"})
        if method == "GET" and path == "/api/menu":
            items = [{key: value for key, value in item.items() if key != "active"} for item in self._menu_catalog() if item["active"]]
            return self._json(200, {"ok": True, "items": items, "currency": "ZMW"})
        if method == "GET" and path == "/api/delivery-zones":
            with self._db() as db:
                rows = db.execute(
                    """SELECT id,name,region,fee,estimated_minutes,minimum_order,free_threshold,instructions
                       FROM delivery_zones WHERE active=1 ORDER BY name"""
                ).fetchall()
            return self._json(200, {"ok": True, "zones": [dict(row) for row in rows]})
        if method == "GET" and path == "/api/payment-methods":
            with self._db() as db:
                rows = db.execute(
                    """SELECT id,name,business_number,registered_name,merchant_info,instructions,qr_image_url
                       FROM payment_methods WHERE enabled=1 ORDER BY name"""
                ).fetchall()
            return self._json(200, {"ok": True, "methods": [dict(row) for row in rows]})
        if method == "GET" and path == "/api/content":
            with self._db() as db:
                rows = db.execute("SELECT key,value FROM site_content").fetchall()
            return self._json(200, {"ok": True, "content": {row["key"]: row["value"] for row in rows}})
        if method == "GET" and path == "/api/me":
            user = self._current_user(headers)
            if user:
                user.pop("is_active", None)
            return self._json(200, {"ok": True, "user": user})
        if path.startswith("/api/admin/"):
            return self._admin_route(method, path, headers, self._read_json(body))
        if method != "POST":
            return self._json(404, {"ok": False, "message": "That page was not found."})
        data = self._read_json(body)
        if path == "/api/register":
            return self._register(data)
        if path == "/api/login":
            return self._login(data)
        if path == "/api/password/change":
            return self._change_password(data, headers)
        if path == "/api/logout":
            self._revoke_session(headers)
            return self._json(200, {"ok": True, "message": "You are signed out."}, {"Set-Cookie": self._clear_cookie()})
        if path == "/api/bookings":
            return self._booking(data, headers)
        if path == "/api/orders":
            return self._order(data, headers)
        if path == "/api/payments/submit":
            return self._submit_payment(data, headers)
        return self._json(404, {"ok": False, "message": "That API endpoint was not found."})

    def _current_user(self, headers: dict[str, str]):
        user_id = self._user_id(headers)
        if not user_id:
            return None
        with self._db() as db:
            row = db.execute(
                "SELECT id, name, email, role, is_active, must_change_password FROM users WHERE id=?",
                (user_id,),
            ).fetchone()
        return dict(row) if row and row["is_active"] else None

    def _admin_required(self, headers: dict[str, str], permission: str = "dashboard"):
        user = self._current_user(headers)
        if not user:
            return None, self._error("Please sign in to continue.", 401)
        if user["must_change_password"]:
            return None, self._error("Change your temporary password before continuing.", 403)
        with self._db() as db:
            accepted = (permission, "orders.kitchen_update") if permission == "orders.update" else (permission, permission)
            allowed = db.execute(
                "SELECT 1 FROM role_permissions WHERE role=? AND permission IN ('*',?,?) LIMIT 1",
                (user["role"], *accepted),
            ).fetchone()
        if not allowed:
            return None, self._error("You do not have permission to perform this action.", 403)
        return user, None

    def _audit(self, db, admin_id: int, action: str, target_type: str, target_id: str = "", details: str = ""):
        db.execute("INSERT INTO admin_audit (admin_user_id, action, target_type, target_id, details, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                   (admin_id, action, target_type, str(target_id), clean_text(details, 300), datetime.now(timezone.utc).isoformat(timespec="seconds")))

    def _admin_route(self, method: str, path: str, headers: dict[str, str], data: dict[str, Any]):
        permission = "dashboard"
        if path == "/api/admin/orders" or path.endswith("/orders"):
            permission = "orders.read"
        elif path == "/api/admin/bookings":
            permission = "bookings.read"
        elif path == "/api/admin/users":
            permission = "customers.read"
        elif path == "/api/admin/users/role":
            permission = "roles.manage"
        elif path.startswith("/api/admin/menu"):
            permission = "menu.read" if method == "GET" else "menu.write"
        elif path.startswith("/api/admin/payments"):
            permission = "payments.read" if method == "GET" else "payments.review"
        elif path.startswith("/api/admin/payment-methods"):
            permission = "payments.configure"
        elif path.startswith("/api/admin/delivery/"):
            permission = "delivery.read" if method == "GET" else "delivery.write"
        elif path.startswith("/api/admin/deliveries"):
            permission = "delivery.read" if method == "GET" else "delivery.update"
        elif path.startswith("/api/admin/content"):
            permission = "content.read" if method == "GET" else "content.write"
        elif path.startswith("/api/admin/reports"):
            permission = "reports.read" if method == "GET" else "reports.export"
        elif path == "/api/admin/audit":
            permission = "audit.read"
        elif path.startswith("/api/admin/roles"):
            permission = "roles.manage"
        elif path == "/api/admin/users/access":
            permission = "customers.access"
        elif path == "/api/admin/orders/status":
            permission = "orders.update"
        elif path == "/api/admin/bookings/status":
            permission = "bookings.update"
        elif path == "/api/admin/uploads/image":
            permission = "menu.write"
        elif path == "/api/admin/analytics":
            permission = "reports.read"
        elif path == "/api/admin/summary":
            permission = "reports.read"
        elif path == "/api/admin/delivery/staff":
            permission = "delivery.read"
        admin, denied = self._admin_required(headers, permission)
        if denied:
            return denied
        if method == "GET" and path == "/api/admin/me":
            return self._json(200, {"ok": True, "user": {"id": admin["id"], "name": admin["name"], "email": admin["email"], "role": admin["role"], "must_change_password": bool(admin["must_change_password"])}})
        if method == "GET" and path == "/api/admin/analytics":
            return self._json(200, {"ok": True, "analytics": self._admin_analytics()})
        if method == "GET" and path == "/api/admin/reports/orders.csv":
            with self._db() as db:
                rows = db.execute(
                    """SELECT reference,customer_name,email,phone,fulfilment,address,payment_method,
                              items_json,subtotal,service_fee,total,status,created_at
                       FROM orders ORDER BY id DESC"""
                ).fetchall()
            output = io.StringIO(newline="")
            writer = csv.writer(output)
            writer.writerow(("Reference", "Customer", "Email", "Phone", "Fulfilment", "Address", "Payment", "Items", "Subtotal ZMW", "Fee ZMW", "Total ZMW", "Status", "Created"))
            for row in rows:
                writer.writerow(tuple(csv_safe(row[key]) for key in (
                    "reference", "customer_name", "email", "phone", "fulfilment", "address",
                    "payment_method", "items_json", "subtotal", "service_fee", "total",
                    "status", "created_at",
                )))
            return 200, output.getvalue().encode("utf-8-sig"), {"Content-Type": "text/csv; charset=utf-8", "Content-Disposition": 'attachment; filename="mesa-orders.csv"', "Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"}
        if method == "GET" and path == "/api/admin/roles":
            with self._db() as db:
                roles = db.execute("SELECT name,label FROM roles ORDER BY name").fetchall()
                permissions = db.execute("SELECT role,permission FROM role_permissions ORDER BY role,permission").fetchall()
            mapping = {role["name"]: [] for role in roles}
            for item in permissions:
                mapping[item["role"]].append(item["permission"])
            return self._json(200, {"ok": True, "roles": [{"name": role["name"], "label": role["label"], "permissions": mapping[role["name"]]} for role in roles]})
        if method == "GET" and path == "/api/admin/payment-methods":
            with self._db() as db:
                rows = db.execute("SELECT * FROM payment_methods ORDER BY name").fetchall()
            return self._json(200, {"ok": True, "methods": [dict(row) for row in rows]})
        if method == "POST" and path == "/api/admin/payment-methods/save":
            return self._save_payment_method(admin, data)
        if method == "GET" and path == "/api/admin/payments":
            with self._db() as db:
                rows = db.execute(
                    """SELECT p.id,p.transaction_reference,p.method_id,p.amount,p.status,p.customer_note,
                              p.submitted_at,p.reviewed_at,o.reference AS order_reference,
                              o.customer_name,o.email,p.reviewed_by
                       FROM payments p JOIN orders o ON o.id=p.order_id ORDER BY p.id DESC LIMIT 500"""
                ).fetchall()
            return self._json(200, {"ok": True, "payments": [dict(row) for row in rows]})
        if method == "POST" and path == "/api/admin/payments/status":
            return self._review_payment(admin, data)
        if method == "GET" and path == "/api/admin/delivery/zones":
            with self._db() as db:
                rows = db.execute("SELECT * FROM delivery_zones ORDER BY name").fetchall()
            return self._json(200, {"ok": True, "zones": [dict(row) for row in rows]})
        if method == "GET" and path == "/api/admin/delivery/staff":
            with self._db() as db:
                rows = db.execute(
                    "SELECT id,name,email FROM users WHERE role='delivery_staff' AND is_active=1 ORDER BY name"
                ).fetchall()
            return self._json(200, {"ok": True, "staff": [dict(row) for row in rows]})
        if method == "POST" and path == "/api/admin/delivery/zones/save":
            return self._save_delivery_zone(admin, data)
        if method == "POST" and path == "/api/admin/delivery/zones/delete":
            zone_id = clean_text(data.get("id"), 60)
            with self._db() as db:
                changed = db.execute("UPDATE delivery_zones SET active=0,updated_at=? WHERE id=?", (datetime.now(timezone.utc).isoformat(timespec="seconds"), zone_id))
                if not changed.rowcount:
                    return self._error("Delivery zone not found.", 404)
                self._audit(db, admin["id"], "delivery_zone_disabled", "delivery_zone", zone_id)
            return self._json(200, {"ok": True, "message": "Delivery zone disabled."})
        if method == "GET" and path == "/api/admin/deliveries":
            with self._db() as db:
                if admin["role"] == "delivery_staff":
                    rows = db.execute(
                        """SELECT o.id,o.reference,o.customer_name,o.phone,o.address,o.total,
                                  a.status AS delivery_status,a.staff_user_id,a.assigned_at
                           FROM delivery_assignments a JOIN orders o ON o.id=a.order_id
                           WHERE a.staff_user_id=? AND o.fulfilment='delivery' ORDER BY a.assigned_at DESC""",
                        (admin["id"],),
                    ).fetchall()
                else:
                    rows = db.execute(
                        """SELECT o.id,o.reference,o.customer_name,o.phone,o.address,o.total,
                                  a.status AS delivery_status,a.staff_user_id,a.assigned_at
                           FROM orders o LEFT JOIN delivery_assignments a ON a.order_id=o.id
                           WHERE o.fulfilment='delivery' ORDER BY o.id DESC LIMIT 300"""
                    ).fetchall()
            return self._json(200, {"ok": True, "deliveries": [dict(row) for row in rows]})
        if method == "POST" and path == "/api/admin/delivery/assign":
            return self._assign_delivery(admin, data)
        if method == "POST" and path == "/api/admin/deliveries/status":
            return self._update_delivery_status(admin, data)
        if method == "GET" and path == "/api/admin/content":
            with self._db() as db:
                rows = db.execute("SELECT key,value FROM site_content ORDER BY key").fetchall()
            return self._json(200, {"ok": True, "content": {row["key"]: row["value"] for row in rows}})
        if method == "POST" and path == "/api/admin/content/save":
            return self._save_content(admin, data)
        if method == "POST" and path == "/api/admin/uploads/image":
            try:
                image_url = self._store_image(data.get("data"))
            except ValueError as exc:
                return self._error(str(exc), 400)
            except RuntimeError as exc:
                return self._error(str(exc), 500)
            self._audit_upload(admin, image_url)
            return self._json(201, {"ok": True, "url": image_url})
        if method == "POST" and path == "/api/admin/users/role":
            return self._assign_role(admin, data)
        if method == "GET" and path == "/api/admin/summary":
            today = date.today()
            start_of_day = today.isoformat() + "T00:00:00"
            start_of_tomorrow = (today + timedelta(days=1)).isoformat() + "T00:00:00"
            with self._db() as db:
                orders_today = db.execute("SELECT COUNT(*) FROM orders WHERE created_at>=? AND created_at<?", (start_of_day, start_of_tomorrow)).fetchone()[0]
                bookings_today = db.execute("SELECT COUNT(*) FROM bookings WHERE booking_date=?", (today.isoformat(),)).fetchone()[0]
                sales_today = db.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE created_at>=? AND created_at<? AND status NOT IN ('Cancelled','Rejected')", (start_of_day, start_of_tomorrow)).fetchone()[0]
                summary = {
                    "customers": db.execute("SELECT COUNT(*) FROM users WHERE role='customer'").fetchone()[0],
                    "orders": db.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
                    "bookings": db.execute("SELECT COUNT(*) FROM bookings").fetchone()[0],
                    "revenue": db.execute("SELECT COALESCE(SUM(total),0) FROM orders WHERE status NOT IN ('Cancelled','Rejected')").fetchone()[0],
                    "pending_orders": db.execute("SELECT COUNT(*) FROM orders WHERE status IN ('Received','Preparing')").fetchone()[0],
                    "pending_bookings": db.execute("SELECT COUNT(*) FROM bookings WHERE status='Received'").fetchone()[0],
                    "orders_today": orders_today, "bookings_today": bookings_today, "sales_today": sales_today
                }
            return self._json(200, {"ok": True, "summary": summary, **summary})
        if method == "GET" and path in {"/api/admin/orders", "/api/admin/bookings", "/api/admin/users", "/api/admin/menu", "/api/admin/audit"}:
            if path.endswith("/menu"):
                return self._json(200, {"ok": True, "items": self._menu_catalog(), "currency": "ZMW"})
            with self._db() as db:
                if path.endswith("/orders"):
                    rows = db.execute("SELECT id, reference, customer_name, email, phone, fulfilment, address, payment_method, items_json, subtotal, service_fee, total, status, created_at FROM orders ORDER BY id DESC LIMIT 300").fetchall()
                    result = [dict(r) | {"items": json.loads(r["items_json"])} for r in rows]
                    return self._json(200, {"ok": True, "orders": result})
                if path.endswith("/bookings"):
                    rows = db.execute("SELECT id, reference, name, email, phone, booking_date, booking_time, guests, notes, status, created_at FROM bookings ORDER BY id DESC LIMIT 300").fetchall()
                    return self._json(200, {"ok": True, "bookings": [dict(r) for r in rows]})
                if path.endswith("/users"):
                    rows = db.execute("SELECT id, name, email, role, is_active, created_at FROM users ORDER BY id DESC LIMIT 500").fetchall()
                    return self._json(200, {"ok": True, "users": [dict(r) for r in rows]})
                rows = db.execute("SELECT id, admin_user_id, action, target_type, target_id, details, created_at FROM admin_audit ORDER BY id DESC LIMIT 200").fetchall()
                return self._json(200, {"ok": True, "audit": [dict(r) for r in rows]})
        if method == "POST" and path == "/api/admin/orders/status":
            allowed = {"Preparing", "Ready"} if admin["role"] == "kitchen_staff" else {
                "Received", "Preparing", "Ready", "Out for Delivery", "Completed", "Cancelled"
            }
            return self._admin_update_status(admin, "orders", data, allowed)
        if method == "POST" and path == "/api/admin/bookings/status":
            return self._admin_update_status(admin, "bookings", data, {"Received", "Confirmed", "Seated", "Completed", "Cancelled"})
        if method == "POST" and path == "/api/admin/users/access":
            target_id = whole_number(data.get("user_id"))
            if target_id is None: return self._error("Invalid customer account.")
            active = data.get("active")
            if not isinstance(active, bool): return self._error("Choose whether the account should be active.")
            if target_id == admin["id"]: return self._error("You cannot disable your own administrator account.", 400)
            with self._db() as db:
                row = db.execute("SELECT id FROM users WHERE id=? AND role='customer'", (target_id,)).fetchone()
                if not row: return self._error("Customer account not found.", 404)
                db.execute("UPDATE users SET is_active=? WHERE id=?", (1 if active else 0, target_id))
                self._audit(db, admin["id"], "account_access_changed", "user", target_id, f"active={active}")
            return self._json(200, {"ok": True, "message": "Customer account updated."})
        if method == "POST" and path == "/api/admin/menu/save":
            item_id = clean_text(data.get("id"), 60)
            name = clean_text(data.get("name"), 100)
            description = clean_text(data.get("description"), 300)
            category = clean_text(data.get("category"), 40)
            tag = clean_text(data.get("tag"), 40)
            price = whole_number(data.get("price"))
            prep_minutes = whole_number(data.get("prep_minutes", 0))
            vegetarian = data.get("vegetarian", False)
            popular = data.get("popular", False)
            image_url = clean_text(data.get("image_url"), 180)
            if price is None: return self._error("Enter a valid whole-number price in ZMW.")
            if prep_minutes is None or not 0 <= prep_minutes <= 1440:
                return self._error("Enter a valid preparation time in minutes.")
            if not isinstance(vegetarian, bool) or not isinstance(popular, bool):
                return self._error("Choose valid vegetarian and popularity values.")
            if image_url and not re.fullmatch(r"/uploads/[a-f0-9]{32}\.(?:jpg|png|webp)", image_url):
                return self._error("Choose an image uploaded through the protected media endpoint.")
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,59}", item_id) or not name or not category or not 1 <= price <= 1000000: return self._error("Complete the menu item details and enter a valid price.")
            # Persist managed menu records separately; public menu endpoint merges these with built-ins.
            with self._db() as db:
                db.execute(
                    """INSERT INTO menu_overrides
                       (id,name,description,price,category,tag,active,vegetarian,prep_minutes,is_popular,image_url)
                       VALUES (?,?,?,?,?,?,1,?,?,?,?)
                       ON CONFLICT(id) DO UPDATE SET name=excluded.name,description=excluded.description,
                       price=excluded.price,category=excluded.category,tag=excluded.tag,active=1,
                       vegetarian=excluded.vegetarian,prep_minutes=excluded.prep_minutes,
                       is_popular=excluded.is_popular,image_url=excluded.image_url""",
                    (item_id, name, description, price, category, tag, int(vegetarian), prep_minutes, int(popular), image_url),
                )
                self._audit(db, admin["id"], "menu_item_saved", "menu", item_id, name)
            return self._json(200, {"ok": True, "message": "Menu item saved."})
        if method == "POST" and path == "/api/admin/menu/delete":
            item_id = clean_text(data.get("id"), 60)
            if not item_id:
                return self._error("Choose a menu item to archive.")
            with self._db() as db:
                db.execute("CREATE TABLE IF NOT EXISTS menu_overrides (id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL, price INTEGER NOT NULL, category TEXT NOT NULL, tag TEXT NOT NULL DEFAULT '', active INTEGER NOT NULL DEFAULT 1)")
                item = next((entry for entry in MENU if entry["id"] == item_id), None)
                if item:
                    db.execute(
                        """INSERT INTO menu_overrides (id,name,description,price,category,tag,active)
                           VALUES (?,?,?,?,?,?,0)
                           ON CONFLICT(id) DO UPDATE SET active=0""",
                        (item["id"], item["name"], item["description"], item["price"], item["category"], item["tag"]),
                    )
                else:
                    updated = db.execute("UPDATE menu_overrides SET active=0 WHERE id=?", (item_id,))
                    if not updated.rowcount:
                        return self._error("Menu item not found.", 404)
                self._audit(db, admin["id"], "menu_item_archived", "menu", item_id)
            return self._json(200, {"ok": True, "message": "Menu item archived."})
        if method == "POST" and path == "/api/admin/menu/restore":
            item_id = clean_text(data.get("id"), 60)
            if not item_id:
                return self._error("Choose a menu item to restore.")
            with self._db() as db:
                updated = db.execute("UPDATE menu_overrides SET active=1 WHERE id=?", (item_id,))
                if not updated.rowcount:
                    return self._error("Archived menu item not found.", 404)
                self._audit(db, admin["id"], "menu_item_restored", "menu", item_id)
            return self._json(200, {"ok": True, "message": "Menu item restored."})
        return self._json(404, {"ok": False, "message": "Administrator endpoint not found."})

    def _save_payment_method(self, admin, data: dict[str, Any]):
        method_id = clean_text(data.get("id"), 60)
        name = clean_text(data.get("name"), 80)
        business_number = clean_text(data.get("business_number"), 40)
        registered_name = clean_text(data.get("registered_name"), 100)
        merchant_info = clean_text(data.get("merchant_info"), 200)
        instructions = clean_text(data.get("instructions"), 500)
        qr_image_url = clean_text(data.get("qr_image_url"), 180)
        enabled = data.get("enabled")
        if method_id not in {"mtn-mobile-money", "airtel-money", "zamtel-kwacha"}:
            return self._error("Choose a supported mobile-money provider.")
        if not name or not isinstance(enabled, bool):
            return self._error("Enter a provider name and choose whether it is enabled.")
        if enabled and (not business_number or not registered_name):
            return self._error("Enter the actual registered account name and payment number before enabling this provider.")
        if qr_image_url and not re.fullmatch(r"/uploads/[a-f0-9]{32}\.(?:jpg|png|webp)", qr_image_url):
            return self._error("Choose a QR image uploaded through the protected media endpoint.")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._db() as db:
            db.execute(
                """UPDATE payment_methods SET name=?,business_number=?,registered_name=?,merchant_info=?,
                   instructions=?,qr_image_url=?,enabled=?,updated_at=? WHERE id=?""",
                (name, business_number, registered_name, merchant_info, instructions, qr_image_url, int(enabled), now, method_id),
            )
            self._audit(db, admin["id"], "payment_method_updated", "payment_method", method_id, f"enabled={enabled}")
        return self._json(200, {"ok": True, "message": "Payment method settings saved."})

    def _review_payment(self, admin, data: dict[str, Any]):
        payment_id = whole_number(data.get("id"))
        status = clean_text(data.get("status"), 30)
        if payment_id is None or status not in {"Verified", "Rejected", "Refunded"}:
            return self._error("Choose a valid payment and review status.")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._db() as db:
            row = db.execute("SELECT id,status FROM payments WHERE id=?", (payment_id,)).fetchone()
            if not row:
                return self._error("Payment not found.", 404)
            if row["status"] not in {"Payment Submitted", "Verified"}:
                return self._error("This payment has already been rejected or refunded.", 409)
            if status == "Refunded" and row["status"] != "Verified":
                return self._error("Only a verified payment can be marked as refunded.", 409)
            db.execute(
                "UPDATE payments SET status=?,reviewed_at=?,reviewed_by=? WHERE id=?",
                (status, now, admin["id"], payment_id),
            )
            self._audit(db, admin["id"], "payment_reviewed", "payment", payment_id, status)
        return self._json(200, {"ok": True, "message": f"Payment marked {status.lower()}."})

    def _save_delivery_zone(self, admin, data: dict[str, Any]):
        zone_id = clean_text(data.get("id"), 60)
        name = clean_text(data.get("name"), 80)
        region = clean_text(data.get("region"), 80)
        fee = whole_number(data.get("fee"))
        estimated = whole_number(data.get("estimated_minutes"))
        minimum = whole_number(data.get("minimum_order", 0))
        free_threshold = whole_number(data.get("free_threshold", 0))
        active = data.get("active")
        instructions = clean_text(data.get("instructions"), 250)
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,59}", zone_id) or not name or not region:
            return self._error("Enter a valid zone ID, name and region.")
        if any(value is None for value in (fee, estimated, minimum, free_threshold)):
            return self._error("Enter whole-number delivery amounts and times.")
        if not 0 <= fee <= 1000000 or not 5 <= estimated <= 2880 or not 0 <= minimum <= 1000000 or not 0 <= free_threshold <= 1000000:
            return self._error("Delivery fee, minimum, free-delivery threshold or estimate is outside the allowed range.")
        if not isinstance(active, bool):
            return self._error("Choose whether the delivery zone is active.")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._db() as db:
            db.execute(
                """INSERT INTO delivery_zones
                   (id,name,region,fee,estimated_minutes,minimum_order,free_threshold,active,instructions,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO UPDATE SET name=excluded.name,region=excluded.region,fee=excluded.fee,
                   estimated_minutes=excluded.estimated_minutes,minimum_order=excluded.minimum_order,
                   free_threshold=excluded.free_threshold,active=excluded.active,instructions=excluded.instructions,
                   updated_at=excluded.updated_at""",
                (zone_id, name, region, fee, estimated, minimum, free_threshold, int(active), instructions, now, now),
            )
            self._audit(db, admin["id"], "delivery_zone_saved", "delivery_zone", zone_id, f"active={active}")
        return self._json(200, {"ok": True, "message": "Delivery zone saved."})

    def _assign_delivery(self, admin, data: dict[str, Any]):
        order_id = whole_number(data.get("order_id"))
        staff_id = whole_number(data.get("staff_user_id"))
        if order_id is None or staff_id is None:
            return self._error("Choose an order and an active delivery staff member.")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._db() as db:
            order = db.execute("SELECT fulfilment FROM orders WHERE id=?", (order_id,)).fetchone()
            staff = db.execute(
                "SELECT id FROM users WHERE id=? AND role='delivery_staff' AND is_active=1",
                (staff_id,),
            ).fetchone()
            if not order or order["fulfilment"] != "delivery":
                return self._error("Only an existing delivery order can be assigned.", 404)
            if not staff:
                return self._error("Active delivery staff account not found.", 404)
            db.execute(
                """INSERT INTO delivery_assignments(order_id,staff_user_id,status,assigned_at)
                   VALUES(?,?,'Assigned',?)
                   ON CONFLICT(order_id) DO UPDATE SET staff_user_id=excluded.staff_user_id,
                   status='Assigned',assigned_at=excluded.assigned_at""",
                (order_id, staff_id, now),
            )
            self._audit(db, admin["id"], "delivery_assigned", "order", order_id, f"staff_user_id={staff_id}")
        return self._json(200, {"ok": True, "message": "Delivery assigned."})

    def _update_delivery_status(self, admin, data: dict[str, Any]):
        order_id = whole_number(data.get("order_id"))
        status = clean_text(data.get("status"), 30)
        if order_id is None or status not in {"Picked up", "Out for Delivery", "Delivered"}:
            return self._error("Choose a valid delivery and status.")
        if admin["role"] == "delivery_staff" and status not in {"Picked up", "Delivered"}:
            return self._error("Delivery staff can mark a delivery picked up or delivered.")
        with self._db() as db:
            assignment = db.execute(
                "SELECT staff_user_id FROM delivery_assignments WHERE order_id=?",
                (order_id,),
            ).fetchone()
            if not assignment:
                return self._error("Delivery assignment not found.", 404)
            if admin["role"] == "delivery_staff" and assignment["staff_user_id"] != admin["id"]:
                return self._error("This delivery is not assigned to your account.", 403)
            db.execute("UPDATE delivery_assignments SET status=? WHERE order_id=?", (status, order_id))
            if status in {"Out for Delivery", "Delivered"}:
                order_status = "Completed" if status == "Delivered" else "Out for Delivery"
                db.execute("UPDATE orders SET status=? WHERE id=?", (order_status, order_id))
            self._audit(db, admin["id"], "delivery_status_changed", "order", order_id, status)
        return self._json(200, {"ok": True, "message": "Delivery status updated."})

    def _save_content(self, admin, data: dict[str, Any]):
        editable = {
            "announcement": 160,
            "hero_lede": 240,
            "restaurant_description": 300,
            "opening_hours": 300,
            "phone": 40,
            "address": 180,
            "social_links": 500,
            "hero_image": 180,
        }
        content = data.get("content")
        if not isinstance(content, dict) or not content:
            return self._error("Provide at least one editable content value.")
        unknown = set(content) - set(editable)
        if unknown:
            return self._error("One or more content fields are not editable.")
        cleaned = {}
        for key, limit in editable.items():
            if key not in content:
                continue
            value = content[key]
            if not isinstance(value, str) or len(value) > limit:
                return self._error(f"Enter valid text for {key.replace('_', ' ')}.")
            if key == "hero_image" and value and not re.fullmatch(r"/uploads/[a-f0-9]{32}\.(?:jpg|png|webp)", value):
                return self._error("Choose a hero image uploaded through the protected media endpoint.")
            cleaned[key] = value.strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._db() as db:
            db.executemany(
                """INSERT INTO site_content(key,value,updated_at,updated_by) VALUES(?,?,?,?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at,
                   updated_by=excluded.updated_by""",
                [(key, value, now, admin["id"]) for key, value in cleaned.items()],
            )
            self._audit(db, admin["id"], "site_content_updated", "site_content", ",".join(cleaned))
        return self._json(200, {"ok": True, "message": "Website content saved."})

    def _audit_upload(self, admin, image_url: str):
        with self._db() as db:
            self._audit(db, admin["id"], "image_uploaded", "media", image_url)

    def _assign_role(self, admin, data: dict[str, Any]):
        user_id = whole_number(data.get("user_id"))
        role = clean_text(data.get("role"), 40)
        if user_id is None or role not in ROLE_LABELS or role == "customer":
            return self._error("Choose an existing staff role and account.")
        if admin["role"] != "super_admin":
            return self._error("Only a super administrator can assign staff roles.", 403)
        with self._db() as db:
            target = db.execute("SELECT id,role FROM users WHERE id=?", (user_id,)).fetchone()
            if not target:
                return self._error("Account not found.", 404)
            if target["id"] == admin["id"] and role != "super_admin":
                return self._error("You cannot remove your own super administrator access.", 400)
            if target["role"] == "super_admin" and role != "super_admin":
                remaining = db.execute(
                    "SELECT COUNT(*) FROM users WHERE role='super_admin' AND is_active=1 AND id<>?",
                    (user_id,),
                ).fetchone()[0]
                if remaining == 0:
                    return self._error("At least one active super administrator must remain.", 409)
            db.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
            self._audit(db, admin["id"], "staff_role_assigned", "user", user_id, role)
        return self._json(200, {"ok": True, "message": f"Account role set to {ROLE_LABELS[role]}."})

    def _submit_payment(self, data: dict[str, Any], headers: dict[str, str]):
        user = self._current_user(headers)
        if not user:
            return self._error("Sign in to submit a payment reference.", 401)
        order_reference = clean_text(data.get("order_reference"), 40)
        transaction_reference = clean_text(data.get("transaction_reference"), 80)
        note = clean_text(data.get("note"), 200)
        if not order_reference or not transaction_reference:
            return self._error("Enter your order reference and mobile-money transaction reference.")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            with self._db() as db:
                row = db.execute(
                    """SELECT o.id,o.total,o.payment_method,p.id AS payment_id,p.status
                       FROM orders o LEFT JOIN payments p ON p.order_id=o.id
                       WHERE o.reference=? AND o.user_id=?""",
                    (order_reference, user["id"]),
                ).fetchone()
                if not row:
                    return self._error("Order not found for your account.", 404)
                if row["payment_method"] not in {"mtn-mobile-money", "airtel-money", "zamtel-kwacha"}:
                    return self._error("This order is not awaiting mobile-money payment.", 409)
                enabled = db.execute(
                    "SELECT 1 FROM payment_methods WHERE id=? AND enabled=1",
                    (row["payment_method"],),
                ).fetchone()
                if not enabled:
                    return self._error("This payment method is no longer available. Contact the restaurant.", 409)
                if row["status"] not in {None, "Awaiting Payment"}:
                    return self._error("A payment reference has already been submitted for this order.", 409)
                if row["payment_id"]:
                    db.execute(
                        """UPDATE payments SET transaction_reference=?,status='Payment Submitted',
                           customer_note=?,submitted_at=? WHERE id=?""",
                        (transaction_reference, note, now, row["payment_id"]),
                    )
                else:
                    db.execute(
                        """INSERT INTO payments(order_id,transaction_reference,method_id,amount,status,customer_note,submitted_at)
                           VALUES(?,?,?,?, 'Payment Submitted',?,?)""",
                        (row["id"], transaction_reference, row["payment_method"], row["total"], note, now),
                    )
        except sqlite3.IntegrityError:
            return self._error("That transaction reference has already been submitted.", 409)
        return self._json(201, {
            "ok": True,
            "message": "Payment reference received for manual review. This does not confirm payment.",
        })

    def _admin_update_status(self, admin, table: str, data: dict[str, Any], allowed: set[str]):
        target_id = whole_number(data.get("id"))
        if target_id is None: return self._error("Invalid record.")
        status = clean_text(data.get("status"), 30)
        if status not in allowed: return self._error("That status is not allowed.")
        column = "status"
        with self._db() as db:
            row = db.execute(f"SELECT id FROM {table} WHERE id=?", (target_id,)).fetchone()
            if not row: return self._error("Record not found.", 404)
            db.execute(f"UPDATE {table} SET {column}=? WHERE id=?", (status, target_id))
            self._audit(db, admin["id"], "status_changed", table[:-1], target_id, status)
        return self._json(200, {"ok": True, "message": "Status updated."})

    def _static(self, relative_path: str):
        relative_path = unquote(relative_path)
        target = (FRONTEND_DIR / "static" / relative_path).resolve()
        static_root = (FRONTEND_DIR / "static").resolve()
        if not str(target).startswith(str(static_root) + os.sep) or not target.is_file():
            return self._json(404, {"ok": False, "message": "File not found."})
        content_type, _ = mimetypes.guess_type(str(target))
        return 200, target.read_bytes(), {"Content-Type": f"{content_type or 'application/octet-stream'}; charset=utf-8" if content_type and content_type.startswith(("text/", "image/svg")) else (content_type or "application/octet-stream"), "Cache-Control": "public, max-age=3600"}

    def _uploaded_file(self, relative_path: str):
        if not re.fullmatch(r"[a-f0-9]{32}\.(?:jpg|png|webp)", relative_path):
            return self._error("File not found.", 404)
        target = (UPLOAD_DIR / relative_path).resolve()
        if not target.is_file() or target.parent != UPLOAD_DIR:
            return self._error("File not found.", 404)
        content_type = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[target.suffix[1:]]
        return 200, target.read_bytes(), {"Content-Type": content_type, "Cache-Control": "public, max-age=31536000, immutable", "X-Content-Type-Options": "nosniff"}

    def _register(self, data: dict[str, Any]):
        name = clean_text(data.get("name"), 80)
        email = clean_text(data.get("email"), 160).lower()
        password = data.get("password") if isinstance(data.get("password"), str) else ""
        if len(name) < 2:
            return self._error("Please enter your name.")
        if not valid_email(email):
            return self._error("Enter a valid email address.")
        if not 8 <= len(password) <= 128:
            return self._error("Use a password between 8 and 128 characters.")
        try:
            with self._db() as db:
                cursor = db.execute(
                    "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                    (name, email, password_hash(password), datetime.now(timezone.utc).isoformat(timespec="seconds")),
                )
                user_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            return self._error("An account with that email already exists.", 409)
        user = {"id": user_id, "name": name, "email": email, "role": "customer"}
        return self._json(201, {"ok": True, "message": "Your MESA account is ready.", "user": user}, {"Set-Cookie": self._session_cookie(user_id)})

    def _login(self, data: dict[str, Any]):
        email = clean_text(data.get("email"), 160).lower()
        password = data.get("password") if isinstance(data.get("password"), str) else ""
        with self._db() as db:
            row = db.execute(
                "SELECT id, name, email, password_hash, role, is_active, must_change_password FROM users WHERE email = ?",
                (email,),
            ).fetchone()
        if row is None or len(password) > 128 or not verify_password(password, row["password_hash"]):
            return self._error("That email and password combination was not recognised.", 401)
        if not row["is_active"]:
            return self._error("This account has been disabled. Please contact the restaurant.", 403)
        user = {
            "id": row["id"], "name": row["name"], "email": row["email"],
            "role": row["role"], "must_change_password": bool(row["must_change_password"]),
        }
        message = f"Welcome back, {row['name'].split()[0]}."
        return self._json(200, {"ok": True, "message": message, "user": user}, {"Set-Cookie": self._session_cookie(row["id"])})

    def _change_password(self, data: dict[str, Any], headers: dict[str, str]):
        user = self._current_user(headers)
        if not user:
            return self._error("Please sign in again to change your password.", 401)
        current_password = data.get("current_password") if isinstance(data.get("current_password"), str) else ""
        new_password = data.get("new_password") if isinstance(data.get("new_password"), str) else ""
        if len(current_password) > 128:
            return self._error("Your current password was not recognised.", 401)
        if not 12 <= len(new_password) <= 128:
            return self._error("Use a new password between 12 and 128 characters.")
        with self._db() as db:
            row = db.execute("SELECT password_hash FROM users WHERE id=?", (user["id"],)).fetchone()
            if not row or not verify_password(current_password, row["password_hash"]):
                return self._error("Your current password was not recognised.", 401)
            if current_password == new_password:
                return self._error("Choose a password different from your current password.")
            db.execute(
                "UPDATE users SET password_hash=?,must_change_password=0 WHERE id=?",
                (password_hash(new_password), user["id"]),
            )
            db.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))
        clean_user = {key: user[key] for key in ("id", "name", "email", "role")}
        clean_user["must_change_password"] = False
        return self._json(
            200,
            {"ok": True, "message": "Your password has been changed.", "user": clean_user},
            {"Set-Cookie": self._session_cookie(user["id"])},
        )

    def _booking(self, data: dict[str, Any], headers: dict[str, str]):
        name = clean_text(data.get("name"), 80)
        email = clean_text(data.get("email"), 160).lower()
        phone = clean_text(data.get("phone"), 30)
        booking_date = clean_text(data.get("date"), 10)
        booking_time = clean_text(data.get("time"), 5)
        notes = clean_text(data.get("notes"), 500)
        try:
            guests = whole_number(data.get("guests", 0))
            parsed_date = date.fromisoformat(booking_date)
            datetime.strptime(booking_time, "%H:%M")
        except (TypeError, ValueError):
            return self._error("Please check the date, time and number of guests.")
        if guests is None:
            return self._error("Please check the date, time and number of guests.")
        if len(name) < 2 or not valid_email(email) or len(phone) < 7:
            return self._error("Please enter your name, a valid email and phone number.")
        if parsed_date < date.today():
            return self._error("Please choose today or a future date.")
        if not 1 <= guests <= 12:
            return self._error("Online bookings are for 1–12 guests. Please contact us for a larger table.")
        if not ("11:00" <= booking_time <= "22:00"):
            return self._error("Choose a time between 11:00 and 22:00.")
        reference = make_reference("MESA")
        with self._db() as db:
            db.execute(
                """INSERT INTO bookings (reference, user_id, name, email, phone, booking_date, booking_time, guests, notes, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (reference, self._user_id(headers), name, email, phone, booking_date, booking_time, guests, notes, datetime.now(timezone.utc).isoformat(timespec="seconds")),
            )
        return self._json(201, {"ok": True, "message": "Your table request has been received.", "reference": reference})

    def _order(self, data: dict[str, Any], headers: dict[str, str]):
        name = clean_text(data.get("name"), 80)
        email = clean_text(data.get("email"), 160).lower()
        phone = clean_text(data.get("phone"), 30)
        fulfilment = clean_text(data.get("fulfilment"), 20)
        address = clean_text(data.get("address"), 250)
        payment = clean_text(data.get("payment"), 30)
        zone_id = clean_text(data.get("delivery_zone_id"), 60)
        items = data.get("items")
        if len(name) < 2 or not valid_email(email) or len(phone) < 7:
            return self._error("Please complete your name, email and phone number.")
        if fulfilment not in {"pickup", "delivery", "dine-in"}:
            return self._error("Choose how you would like to receive your order.")
        if fulfilment == "delivery" and len(address) < 8:
            return self._error("Please add a delivery address.")
        if payment not in {"pay-at-counter", "cash-on-delivery", "mtn-mobile-money", "airtel-money", "zamtel-kwacha"}:
            return self._error("Choose a payment method.")
        if payment == "cash-on-delivery" and fulfilment != "delivery":
            return self._error("Cash on delivery is available for delivery orders only.")
        if not isinstance(items, list) or not items or len(items) > 30:
            return self._error("Your cart is empty. Add something delicious first.")
        menu_items = [item for item in self._menu_catalog() if item["active"]]
        delivery_zone = None
        with self._db() as db:
            if fulfilment == "delivery":
                delivery_zone = db.execute(
                    """SELECT id,fee,minimum_order,free_threshold FROM delivery_zones
                       WHERE id=? AND active=1""",
                    (zone_id,),
                ).fetchone()
                if not delivery_zone:
                    return self._error("Choose an available delivery zone.")
                if not address:
                    return self._error("Please add a delivery address.")
            if payment in {"mtn-mobile-money", "airtel-money", "zamtel-kwacha"}:
                available = db.execute(
                    "SELECT 1 FROM payment_methods WHERE id=? AND enabled=1",
                    (payment,),
                ).fetchone()
                if not available:
                    return self._error("That mobile-money provider is not currently enabled.")
                if not self._user_id(headers):
                    return self._error("Sign in before choosing mobile-money payment.", 401)
        menu_by_id = {item["id"]: item for item in menu_items}
        clean_items = []
        subtotal = 0
        for entry in items:
            if not isinstance(entry, dict):
                return self._error("One of the cart items is invalid.")
            item_id = clean_text(entry.get("id"), 60)
            quantity = whole_number(entry.get("quantity", 0))
            if quantity is None:
                return self._error("One of the item quantities is invalid.")
            product = menu_by_id.get(item_id)
            if product is None or not 1 <= quantity <= 20:
                return self._error("One of the cart items or quantities is not available.")
            line_total = product["price"] * quantity
            subtotal += line_total
            clean_items.append({"id": item_id, "name": product["name"], "quantity": quantity, "unit_price": product["price"], "line_total": line_total})
        if delivery_zone and subtotal < delivery_zone["minimum_order"]:
            return self._error("Your order does not meet the minimum for that delivery zone.")
        service_fee = 0
        if delivery_zone:
            service_fee = 0 if delivery_zone["free_threshold"] and subtotal >= delivery_zone["free_threshold"] else delivery_zone["fee"]
        total = subtotal + service_fee
        reference = make_reference("ORD")
        user_id = self._user_id(headers)
        with self._db() as db:
            db.execute(
                """INSERT INTO orders (reference, user_id, customer_name, email, phone, fulfilment, address, payment_method,
                   items_json, subtotal, service_fee, total, created_at, delivery_zone_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (reference, user_id, name, email, phone, fulfilment, address, payment, json.dumps(clean_items), subtotal, service_fee, total, datetime.now(timezone.utc).isoformat(timespec="seconds"), zone_id if delivery_zone else ""),
            )
            if payment in {"mtn-mobile-money", "airtel-money", "zamtel-kwacha"}:
                db.execute(
                    """INSERT INTO payments(order_id,transaction_reference,method_id,amount,status,submitted_at)
                       SELECT id,?,?,?,'Awaiting Payment',? FROM orders WHERE reference=?""",
                    (f"PENDING-{reference}", payment, total, datetime.now(timezone.utc).isoformat(timespec="seconds"), reference),
                )
        return self._json(201, {"ok": True, "message": "Your order is in the kitchen queue.", "reference": reference, "total": total})


class MesaRequestHandler(BaseHTTPRequestHandler):
    server_version = "MESA/1.0"
    sys_version = ""

    def _dispatch(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length > MAX_REQUEST_BYTES:
            status, body, headers = self.server.mesa_app._json(413, {"ok": False, "message": "That request is too large."})
        else:
            body_in = self.rfile.read(length) if length else b""
            request_headers = {"Host": self.headers.get("Host", ""), "Origin": self.headers.get("Origin", ""), "Cookie": self.headers.get("Cookie", "")}
            status, body, headers = self.server.mesa_app.handle(self.command, self.path, request_headers, body_in)
        self.send_response(status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data:; media-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self): self._dispatch()
    def do_POST(self): self._dispatch()
    def do_HEAD(self): self._dispatch()

    def log_message(self, format_string, *args):
        # Keep the local console readable; errors still appear in normal output.
        print(f"[{self.log_date_time_string()}] {format_string % args}")


def run_server():
    if not (FRONTEND_DIR / "index.html").is_file() and not (FRONTEND_DIR / "templates" / "index.html").is_file():
        raise SystemExit("MESA Frontend was not found. Extract MESA_Frontend beside MESA_Backend, then run this launcher again.")
    app = MesaApplication()
    host = os.environ.get("MESA_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "5000"))
    server = ThreadingHTTPServer((host, port), MesaRequestHandler)
    server.mesa_app = app
    print("\n  MESA Kitchen & Social is ready")
    print(f"  On this PC: http://127.0.0.1:{port}")
    print(f"  Network listening address: {host}:{port}")
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.connect(("192.0.2.1", 80))
        lan_ip = probe.getsockname()[0]
        probe.close()
        print(f"  Open on phone (same Wi-Fi): http://{lan_ip}:{port}")
    except OSError:
        print(f"  On your phone, open http://<your-PC-IPv4>:{port}")
    print("  Keep this window open. Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMESA server stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
