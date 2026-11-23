"""Smoke tests for MESA's standard-library API. Run: python -m unittest -v"""
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import MesaApplication, password_hash


class MesaApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = MesaApplication(Path(self.temp_dir.name) / "test.sqlite3", "unit-test-secret")
        self.cookie = ""

    def tearDown(self):
        self.temp_dir.cleanup()

    def request(self, method, path, payload=None, cookie=None, origin=None):
        headers = {"Host": "127.0.0.1:5000"}
        if cookie:
            headers["Cookie"] = cookie
        if origin:
            headers["Origin"] = origin
        body = json.dumps(payload).encode("utf-8") if payload is not None else b""
        status, raw_body, response_headers = self.app.handle(method, path, headers, body)
        parsed = json.loads(raw_body.decode("utf-8")) if response_headers.get("Content-Type", "").startswith("application/json") else raw_body
        return status, parsed, response_headers

    def test_home_and_menu(self):
        status, page, headers = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"MESA", page)
        self.assertIn("text/html", headers["Content-Type"])
        status, data, _ = self.request("GET", "/api/menu")
        self.assertEqual(status, 200)
        self.assertEqual(len(data["items"]), 8)

    def test_register_login_logout_and_session(self):
        status, data, headers = self.request("POST", "/api/register", {"name": "Test Guest", "email": "guest@example.com", "password": "correct-horse-1"})
        self.assertEqual(status, 201, data)
        self.cookie = headers["Set-Cookie"].split(";", 1)[0]
        status, me, _ = self.request("GET", "/api/me", cookie=self.cookie)
        self.assertEqual(me["user"]["email"], "guest@example.com")
        status, data, _ = self.request("POST", "/api/logout", {})
        self.assertEqual(status, 200)
        status, data, headers = self.request("POST", "/api/login", {"email": "guest@example.com", "password": "correct-horse-1"})
        self.assertEqual(status, 200, data)
        self.assertIn("Set-Cookie", headers)
        self.assertEqual(data["user"]["name"], "Test Guest")

    def test_duplicate_registration_rejected(self):
        payload = {"name": "Test Guest", "email": "guest@example.com", "password": "correct-horse-1"}
        self.assertEqual(self.request("POST", "/api/register", payload)[0], 201)
        self.assertEqual(self.request("POST", "/api/register", payload)[0], 409)

    def test_registration_validates_email_and_password_length(self):
        self.assertEqual(self.request("POST", "/api/register", {
            "name": "Test Guest", "email": "invalid-email", "password": "correct-horse-1"
        })[0], 400)
        self.assertEqual(self.request("POST", "/api/register", {
            "name": "Test Guest", "email": "guest@example.com", "password": "short"
        })[0], 400)
        self.assertEqual(self.request("POST", "/api/register", {
            "name": "Test Guest", "email": "guest@example.com", "password": "x" * 129
        })[0], 400)

    def test_existing_account_survives_additive_session_migration(self):
        path = Path(self.temp_dir.name) / "legacy.sqlite3"
        db = sqlite3.connect(path)
        try:
            db.execute("""CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL, created_at TEXT NOT NULL
            )""")
            db.execute("INSERT INTO users(name,email,password_hash,created_at) VALUES(?,?,?,?)", (
                "Existing Guest", "existing@example.com", password_hash("ExistingPass123"), "2024-01-01T00:00:00+00:00"
            ))
            db.commit()
        finally:
            db.close()
        migrated = MesaApplication(path, "unit-test-migration-secret")
        with migrated._db() as db:
            row = db.execute("SELECT id,name,email,role,is_active FROM users WHERE email=?", ("existing@example.com",)).fetchone()
            self.assertEqual(tuple(row), (1, "Existing Guest", "existing@example.com", "customer", 1))
            self.assertTrue(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sessions'").fetchone())
        backups = list(Path(self.temp_dir.name).glob("legacy.sqlite3.backup-pre-schema-*"))
        self.assertEqual(len(backups), 1)
        backup = sqlite3.connect(backups[0])
        try:
            self.assertEqual(backup.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(backup.execute("SELECT email FROM users").fetchone()[0], "existing@example.com")
        finally:
            backup.close()
        status, _, headers = migrated.handle("POST", "/api/login", {"Host": "localhost"}, json.dumps({
            "email": "existing@example.com", "password": "ExistingPass123"
        }).encode())
        self.assertEqual(status, 200)
        self.assertIn("HttpOnly", headers["Set-Cookie"])

    def test_logout_clears_and_invalidates_the_session_cookie(self):
        status, _, headers = self.request("POST", "/api/register", {
            "name": "Test Guest", "email": "guest@example.com", "password": "correct-horse-1"
        })
        self.assertEqual(status, 201)
        cookie = headers["Set-Cookie"].split(";", 1)[0]
        self.assertEqual(self.request("GET", "/api/me", cookie=cookie)[1]["user"]["email"], "guest@example.com")
        status, _, headers = self.request("POST", "/api/logout", {}, cookie=cookie)
        self.assertEqual(status, 200)
        self.assertIn("Max-Age=0", headers["Set-Cookie"])
        self.assertIsNone(self.request("GET", "/api/me", cookie=cookie)[1]["user"])

    def test_production_session_cookie_is_secure(self):
        with patch.dict(os.environ, {"MESA_ENV": "production", "MESA_COOKIE_SECURE": "0"}):
            status, _, headers = self.request("POST", "/api/register", {
                "name": "Secure Guest", "email": "secure@example.com", "password": "correct-horse-1"
            })
        self.assertEqual(status, 201)
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        self.assertIn("SameSite=Lax", headers["Set-Cookie"])
        self.assertIn("Secure", headers["Set-Cookie"])

    def test_disabled_account_session_is_not_authenticated(self):
        _, _, headers = self.request("POST", "/api/register", {
            "name": "Test Guest", "email": "guest@example.com", "password": "correct-horse-1"
        })
        cookie = headers["Set-Cookie"].split(";", 1)[0]
        with self.app._db() as db:
            db.execute("UPDATE users SET is_active=0 WHERE email=?", ("guest@example.com",))
        self.assertIsNone(self.request("GET", "/api/me", cookie=cookie)[1]["user"])

    def test_booking_submission(self):
        status, data, _ = self.request("POST", "/api/bookings", {
            "name": "Table Guest", "email": "table@example.com", "phone": "+260971234567",
            "date": "2099-06-20", "time": "18:00", "guests": 4, "notes": "Window seat, please"
        })
        self.assertEqual(status, 201, data)
        self.assertTrue(data["reference"].startswith("MESA-"))

    def test_order_total_is_calculated_server_side(self):
        with self.app._db() as db:
            db.execute("UPDATE delivery_zones SET active=1,fee=12 WHERE id='kabulonga'")
        status, data, _ = self.request("POST", "/api/orders", {
            "name": "Order Guest", "email": "order@example.com", "phone": "+260971234567",
            "fulfilment": "delivery", "delivery_zone_id": "kabulonga", "address": "House 12, Kabulonga, Lusaka",
            "payment": "cash-on-delivery", "items": [{"id": "mesa-smash", "quantity": 2}]
        })
        self.assertEqual(status, 201, data)
        self.assertEqual(data["total"], 188)
        self.assertTrue(data["reference"].startswith("ORD-"))

    def test_order_rejects_unknown_menu_item(self):
        status, data, _ = self.request("POST", "/api/orders", {
            "name": "Order Guest", "email": "order@example.com", "phone": "+260971234567",
            "fulfilment": "pickup", "payment": "pay-at-counter", "items": [{"id": "not-a-real-item", "quantity": 1}]
        })
        self.assertEqual(status, 400)

    def test_cross_origin_post_rejected(self):
        status, data, _ = self.request("POST", "/api/logout", {}, origin="https://example.invalid")
        self.assertEqual(status, 403)
        self.assertEqual(self.request("POST", "/api/logout", {}, origin="https://[::1")[0], 403)

    def test_numeric_fields_reject_fractional_values(self):
        booking = {
            "name": "Table Guest", "email": "table@example.com", "phone": "+260971234567",
            "date": "2099-06-20", "time": "18:00", "guests": 2.5
        }
        self.assertEqual(self.request("POST", "/api/bookings", booking)[0], 400)
        order = {
            "name": "Order Guest", "email": "order@example.com", "phone": "+260971234567",
            "fulfilment": "pickup", "payment": "pay-at-counter",
            "items": [{"id": "mesa-smash", "quantity": 1.5}]
        }
        self.assertEqual(self.request("POST", "/api/orders", order)[0], 400)

    def test_password_change_revokes_old_session_and_persists_new_password(self):
        _, _, headers = self.request("POST", "/api/register", {
            "name": "Test Guest", "email": "guest@example.com", "password": "correct-horse-1"
        })
        cookie = headers["Set-Cookie"].split(";", 1)[0]
        status, result, new_headers = self.request("POST", "/api/password/change", {
            "current_password": "correct-horse-1", "new_password": "a-new-strong-password"
        }, cookie)
        self.assertEqual(status, 200, result)
        self.assertIn("Set-Cookie", new_headers)
        self.assertIsNone(self.request("GET", "/api/me", cookie=cookie)[1]["user"])
        self.assertEqual(self.request("POST", "/api/login", {
            "email": "guest@example.com", "password": "a-new-strong-password"
        })[0], 200)

    def test_static_file(self):
        status, body, headers = self.request("GET", "/static/css/app.css")
        self.assertEqual(status, 200)
        self.assertIn(b".hero", body)
        self.assertIn("text/css", headers["Content-Type"])

    def test_supplied_video_and_soundtrack_are_served(self):
        for path, content_type in (
            ("/static/media/mesa-kitchen-burger.mp4", "video/mp4"),
            ("/static/media/mesa-background-score.mp3", "audio/mpeg"),
        ):
            status, body, headers = self.request("GET", path)
            self.assertEqual(status, 200)
            self.assertGreater(len(body), 100_000)
            self.assertEqual(headers["Content-Type"], content_type)

    def test_seo_routes_and_canonical_configuration(self):
        with patch.dict(os.environ, {"MESA_PUBLIC_URL": ""}):
            status, html, _ = self.request("GET", "/")
            self.assertEqual(status, 200)
            self.assertIn(b"og:title", html)
            self.assertNotIn(b"<!-- MESA_CANONICAL -->", html)
            status, robots, _ = self.request("GET", "/robots.txt")
            self.assertEqual(status, 200)
            self.assertIn(b"Disallow: /api/", robots)
            self.assertEqual(self.request("GET", "/sitemap.xml")[0], 503)
        with patch.dict(os.environ, {"MESA_PUBLIC_URL": "https://mesa.example", "MESA_ENV": "production"}):
            status, html, _ = self.request("GET", "/")
            self.assertIn(b'rel="canonical" href="https://mesa.example/"', html)
            self.assertIn(b'"@type": "Restaurant"', html)
            self.assertEqual(self.request("GET", "/sitemap.xml")[0], 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
