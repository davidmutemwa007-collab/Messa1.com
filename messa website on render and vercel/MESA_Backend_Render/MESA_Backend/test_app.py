"""Smoke tests for MESA's standard-library API. Run: python -m unittest -v"""
import json
import tempfile
import unittest
from pathlib import Path

from app import MesaApplication


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
        self.assertIn(b"MESA Kitchen", page)
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

    def test_booking_submission(self):
        status, data, _ = self.request("POST", "/api/bookings", {
            "name": "Table Guest", "email": "table@example.com", "phone": "+260971234567",
            "date": "2099-06-20", "time": "18:00", "guests": 4, "notes": "Window seat, please"
        })
        self.assertEqual(status, 201, data)
        self.assertTrue(data["reference"].startswith("MESA-"))

    def test_order_total_is_calculated_server_side(self):
        status, data, _ = self.request("POST", "/api/orders", {
            "name": "Order Guest", "email": "order@example.com", "phone": "+260971234567",
            "fulfilment": "delivery", "address": "House 12, Kabulonga, Lusaka",
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

    def test_static_file(self):
        status, body, headers = self.request("GET", "/static/css/app.css")
        self.assertEqual(status, 200)
        self.assertIn(b"hero-section", body)
        self.assertIn("text/css", headers["Content-Type"])

    def test_allowed_cross_origin_preflight_and_credentials(self):
        import os
        previous = os.environ.get("MESA_ALLOWED_ORIGINS")
        os.environ["MESA_ALLOWED_ORIGINS"] = "https://mesa-example.vercel.app"
        try:
            status, body, headers = self.request("OPTIONS", "/api/login", origin="https://mesa-example.vercel.app")
            self.assertEqual(status, 204)
            self.assertEqual(headers.get("Access-Control-Allow-Origin"), "https://mesa-example.vercel.app")
            self.assertEqual(headers.get("Access-Control-Allow-Credentials"), "true")
            status, data, headers = self.request("GET", "/api/menu", origin="https://mesa-example.vercel.app")
            self.assertEqual(status, 200)
            self.assertEqual(headers.get("Access-Control-Allow-Origin"), "https://mesa-example.vercel.app")
        finally:
            if previous is None:
                os.environ.pop("MESA_ALLOWED_ORIGINS", None)
            else:
                os.environ["MESA_ALLOWED_ORIGINS"] = previous


if __name__ == "__main__":
    unittest.main(verbosity=2)
