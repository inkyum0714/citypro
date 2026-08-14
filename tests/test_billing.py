import path_setup  # noqa: F401
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import engagement.profile_store as profile_store
from billing import orders as order_store
from engagement.service import EngagementService
from main import create_app


class BillingOrderTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        tmp = Path(self._tmpdir.name)
        profile_store.PROGRESS_PATH = tmp / "user_progress.json"
        order_store.ORDERS_PATH = tmp / "orders.json"
        self.svc = EngagementService()
        self.svc.on_login("payer")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_create_pro_order_amount(self):
        ok, _, order = order_store.create_order("payer", "pro")
        self.assertTrue(ok)
        self.assertEqual(order["amount"], 1400)
        self.assertEqual(order["price_usd"], 1)
        self.assertEqual(order["plan_id"], "pro")

    def test_create_ultra_order_amount(self):
        ok, _, order = order_store.create_order("payer", "ultra")
        self.assertTrue(ok)
        self.assertEqual(order["amount"], 7000)
        self.assertEqual(order["price_usd"], 5)

    def test_confirm_grants_plan(self):
        ok, _, order = order_store.create_order("payer", "pro_plus")
        self.assertTrue(ok)
        paid = order_store.mark_paid(order["order_id"], "pay_test", {"method": "카드"})
        self.assertEqual(paid["status"], "paid")
        granted, _, player = self.svc.grant_plan("payer", "pro_plus", days=30, source="toss")
        self.assertTrue(granted)
        self.assertEqual(player["plan"], "pro_plus")
        self.assertTrue(player["is_pro"])


class CheckoutPageTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_checkout_requires_login(self):
        res = self.client.get("/pro/checkout?plan=pro")
        self.assertIn(res.status_code, (302, 303))

    def test_checkout_without_keys_shows_error(self):
        with self.client.session_transaction() as sess:
            sess["login_id"] = "payer"
            sess["name"] = "Payer"
        with patch("billing.routes.toss_configured", return_value=False):
            res = self.client.get("/pro/checkout?plan=pro")
        self.assertEqual(res.status_code, 200)
        self.assertIn("TOSS".encode(), res.data)


if __name__ == "__main__":
    unittest.main()
