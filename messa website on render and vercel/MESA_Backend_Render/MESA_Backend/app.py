"""MESA Kitchen & Social — self-contained Python/SQLite web application.

Uses only the Python standard library. Run with: python app.py
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import mimetypes
import os
import re
import secrets
import socket
import sqlite3
import sys
import time
from contextlib import contextmanager
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = Path(os.environ.get("MESA_FRONTEND_DIR", BASE_DIR.parent / "MESA_Frontend")).resolve()
DATABASE = Path(os.environ.get("MESA_DATABASE", BASE_DIR / "data" / "mesa.sqlite3"))

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
    created_at TEXT NOT NULL
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
    FOREIGN KEY(user_id) REFERENCES users(id)
);
"""


def clean_text(value: Any, limit: int = 160) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()[:limit]


def valid_email(value: str) -> bool:
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value))


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
        self._init_db()

    def _load_or_create_secret(self) -> bytes:
        env_secret = os.environ.get("MESA_SECRET_KEY")
        if env_secret:
            return env_secret.encode("utf-8")
        secret_path = BASE_DIR / "data" / "secret.key"
        secret_path.parent.mkdir(parents=True, exist_ok=True)
        if secret_path.exists():
            return secret_path.read_bytes()
        secret = secrets.token_bytes(48)
        try:
            secret_path.write_bytes(secret)
        except OSError:
            pass
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

    def _cookie_attributes(self) -> str:
        # Cross-site frontend (Vercel) + API (Render) requires SameSite=None and Secure.
        cross_site = bool(os.environ.get("MESA_ALLOWED_ORIGINS", "").strip())
        same_site = os.environ.get("MESA_COOKIE_SAMESITE", "None" if cross_site else "Lax")
        secure = os.environ.get("MESA_COOKIE_SECURE", "true" if cross_site else "false").lower() in {"1", "true", "yes"}
        return f"SameSite={same_site}" + ("; Secure" if secure else "")

    def _session_cookie(self, user_id: int) -> str:
        expiry = int(time.time()) + 7 * 24 * 60 * 60
        payload = f"{int(user_id)}.{expiry}"
        signature = hmac.new(self.secret_key, payload.encode("ascii"), hashlib.sha256).hexdigest()
        token = f"{payload}.{signature}"
        return f"mesa_session={token}; Path=/; Max-Age=604800; HttpOnly; {self._cookie_attributes()}"

    def _clear_cookie(self) -> str:
        return f"mesa_session=; Path=/; Max-Age=0; HttpOnly; {self._cookie_attributes()}"

    @staticmethod
    def _allowed_origins() -> set[str]:
        return {item.strip().rstrip("/") for item in os.environ.get("MESA_ALLOWED_ORIGINS", "").split(",") if item.strip()}

    def _cors_headers(self, headers: dict[str, str]) -> dict[str, str]:
        origin = headers.get("Origin", "").rstrip("/")
        allowed = self._allowed_origins()
        if origin and origin in allowed:
            return {
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Accept",
                "Vary": "Origin",
            }
        return {}

    def _user_id(self, headers: dict[str, str]) -> int | None:
        cookie_header = headers.get("Cookie", "")
        match = re.search(r"(?:^|;\s*)mesa_session=([^;]+)", cookie_header)
        if not match:
            return None
        try:
            user_text, expiry_text, supplied_sig = match.group(1).split(".", 2)
            payload = f"{user_text}.{expiry_text}"
            expected_sig = hmac.new(self.secret_key, payload.encode("ascii"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(supplied_sig, expected_sig) or int(expiry_text) < int(time.time()):
                return None
            user_id = int(user_text)
            with self._db() as db:
                exists = db.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone()
            return user_id if exists else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _json(status: int, data: dict[str, Any], extra_headers: dict[str, str] | None = None):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store"}
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
        allowed = self._allowed_origins()
        if allowed:
            return origin.rstrip("/") in allowed
        host = headers.get("Host", "")
        parsed = urlsplit(origin)
        return parsed.scheme in {"http", "https"} and parsed.netloc.lower() == host.lower()

    def handle(self, method: str, raw_path: str, headers: dict[str, str] | None = None, body: bytes = b""):
        headers = headers or {}
        method = method.upper()
        def with_cors(result):
            status, response_body, response_headers = result
            if urlsplit(raw_path).path.startswith("/api/"):
                response_headers = {**response_headers, **self._cors_headers(headers)}
            return status, response_body, response_headers
        if method == "HEAD":
            method = "GET"
        parsed_url = urlsplit(raw_path)
        path = parsed_url.path or "/"
        cors_headers = self._cors_headers(headers)
        if method == "OPTIONS" and path.startswith("/api/"):
            if headers.get("Origin") and not cors_headers:
                return with_cors(self._json(403, {"ok": False, "message": "This website is not allowed to access the MESA API."}))
            return 204, b"", {**cors_headers, "Cache-Control": "no-store"}
        if len(body) > 1_048_576:
            return with_cors(self._json(413, {"ok": False, "message": "That request is too large."}))
        if method == "GET" and path == "/":
            page = (FRONTEND_DIR / "index.html").read_bytes()
            return 200, page, {"Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-cache"}
        if method == "GET" and path.startswith("/static/"):
            return self._static(path[len("/static/"):])
        if path.startswith("/api/") and method == "POST" and not self._same_origin(headers):
            return with_cors(self._error("Cross-origin requests are not allowed.", 403))
        if method == "GET" and path == "/api/health":
            return with_cors(self._json(200, {"ok": True, "service": "MESA Backend", "database": "connected"}))
        if method == "GET" and path == "/api/menu":
            return with_cors(self._json(200, {"ok": True, "items": MENU, "currency": "ZMW"}))
        if method == "GET" and path == "/api/me":
            user_id = self._user_id(headers)
            if not user_id:
                return with_cors(self._json(200, {"ok": True, "user": None}))
            with self._db() as db:
                row = db.execute("SELECT id, name, email FROM users WHERE id = ?", (user_id,)).fetchone()
            return with_cors(self._json(200, {"ok": True, "user": dict(row) if row else None}))
        if method != "POST":
            return with_cors(self._json(404, {"ok": False, "message": "That page was not found."}))
        data = self._read_json(body)
        if path == "/api/register":
            return with_cors(self._register(data))
        if path == "/api/login":
            return with_cors(self._login(data))
        if path == "/api/logout":
            return with_cors(self._json(200, {"ok": True, "message": "You are signed out."}, {"Set-Cookie": self._clear_cookie()}))
        if path == "/api/bookings":
            return with_cors(self._booking(data, headers))
        if path == "/api/orders":
            return with_cors(self._order(data, headers))
        return with_cors(self._json(404, {"ok": False, "message": "That API endpoint was not found."}))
    def _static(self, relative_path: str):
        relative_path = unquote(relative_path)
        target = (FRONTEND_DIR / "static" / relative_path).resolve()
        static_root = (FRONTEND_DIR / "static").resolve()
        if not str(target).startswith(str(static_root) + os.sep) or not target.is_file():
            return self._json(404, {"ok": False, "message": "File not found."})
        content_type, _ = mimetypes.guess_type(str(target))
        return 200, target.read_bytes(), {"Content-Type": f"{content_type or 'application/octet-stream'}; charset=utf-8" if content_type and content_type.startswith(("text/", "image/svg")) else (content_type or "application/octet-stream"), "Cache-Control": "public, max-age=3600"}

    def _register(self, data: dict[str, Any]):
        name = clean_text(data.get("name"), 80)
        email = clean_text(data.get("email"), 160).lower()
        password = data.get("password") if isinstance(data.get("password"), str) else ""
        if len(name) < 2:
            return self._error("Please enter your name.")
        if not valid_email(email):
            return self._error("Enter a valid email address.")
        if len(password) < 8:
            return self._error("Use a password with at least 8 characters.")
        try:
            with self._db() as db:
                cursor = db.execute(
                    "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                    (name, email, password_hash(password), datetime.now(timezone.utc).isoformat(timespec="seconds")),
                )
                user_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            return self._error("An account with that email already exists.", 409)
        user = {"id": user_id, "name": name, "email": email}
        return self._json(201, {"ok": True, "message": "Your MESA account is ready.", "user": user}, {"Set-Cookie": self._session_cookie(user_id)})

    def _login(self, data: dict[str, Any]):
        email = clean_text(data.get("email"), 160).lower()
        password = data.get("password") if isinstance(data.get("password"), str) else ""
        with self._db() as db:
            row = db.execute("SELECT id, name, email, password_hash FROM users WHERE email = ?", (email,)).fetchone()
        if row is None or not verify_password(password, row["password_hash"]):
            return self._error("That email and password combination was not recognised.", 401)
        user = {"id": row["id"], "name": row["name"], "email": row["email"]}
        message = f"Welcome back, {row['name'].split()[0]}."
        return self._json(200, {"ok": True, "message": message, "user": user}, {"Set-Cookie": self._session_cookie(row["id"])})

    def _booking(self, data: dict[str, Any], headers: dict[str, str]):
        name = clean_text(data.get("name"), 80)
        email = clean_text(data.get("email"), 160).lower()
        phone = clean_text(data.get("phone"), 30)
        booking_date = clean_text(data.get("date"), 10)
        booking_time = clean_text(data.get("time"), 5)
        notes = clean_text(data.get("notes"), 500)
        try:
            guests = int(data.get("guests", 0))
            parsed_date = date.fromisoformat(booking_date)
            datetime.strptime(booking_time, "%H:%M")
        except (TypeError, ValueError):
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
        items = data.get("items")
        if len(name) < 2 or not valid_email(email) or len(phone) < 7:
            return self._error("Please complete your name, email and phone number.")
        if fulfilment not in {"pickup", "delivery", "dine-in"}:
            return self._error("Choose how you would like to receive your order.")
        if fulfilment == "delivery" and len(address) < 8:
            return self._error("Please add a delivery address.")
        if payment not in {"pay-at-counter", "mobile-money", "cash-on-delivery"}:
            return self._error("Choose a payment method.")
        if not isinstance(items, list) or not items or len(items) > 30:
            return self._error("Your cart is empty. Add something delicious first.")
        menu_by_id = {item["id"]: item for item in MENU}
        clean_items = []
        subtotal = 0
        for entry in items:
            if not isinstance(entry, dict):
                return self._error("One of the cart items is invalid.")
            item_id = clean_text(entry.get("id"), 60)
            try:
                quantity = int(entry.get("quantity", 0))
            except (TypeError, ValueError):
                return self._error("One of the item quantities is invalid.")
            product = menu_by_id.get(item_id)
            if product is None or not 1 <= quantity <= 20:
                return self._error("One of the cart items or quantities is not available.")
            line_total = product["price"] * quantity
            subtotal += line_total
            clean_items.append({"id": item_id, "name": product["name"], "quantity": quantity, "unit_price": product["price"], "line_total": line_total})
        service_fee = 12 if fulfilment == "delivery" else 0
        total = subtotal + service_fee
        reference = make_reference("ORD")
        with self._db() as db:
            db.execute(
                """INSERT INTO orders (reference, user_id, customer_name, email, phone, fulfilment, address, payment_method,
                   items_json, subtotal, service_fee, total, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (reference, self._user_id(headers), name, email, phone, fulfilment, address, payment, json.dumps(clean_items), subtotal, service_fee, total, datetime.now(timezone.utc).isoformat(timespec="seconds")),
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
        if length > 1_048_576:
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
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'")
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
