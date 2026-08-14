import path_setup  # noqa: F401
import tempfile
import unittest
from pathlib import Path

import engagement.profile_store as profile_store
from engagement.service import EngagementService


class EngagementTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        profile_store.PROGRESS_PATH = Path(self._tmpdir.name) / "user_progress.json"
        self.svc = EngagementService()

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_login_grants_coins_once_per_day(self):
        p1 = self.svc.on_login("player1")
        coins_first = p1["coins"]
        p2 = self.svc.on_login("player1")
        self.assertEqual(p2["coins"], coins_first)

    def test_record_road_builds_quest(self):
        self.svc.on_login("builder")
        for _ in range(3):
            self.svc.record_action("builder", "add_road")
        profile = self.svc.get_public("builder")
        quest = next(q for q in profile["daily"]["quests"] if q["id"] == "build_roads")
        self.assertTrue(quest["completed"])

    def test_shop_purchase_cosmetic(self):
        self.svc.on_login("shopper")

        profile_store.update_profile("shopper", lambda p: p.update({"coins": 500}))
        ok, _, player = self.svc.purchase_shop("shopper", "cosmetic_neon")
        self.assertTrue(ok)
        self.assertIn("neon", player["owned_items"])
        self.assertEqual(player["active_cosmetic"], "neon")

    def test_pro_demo_activation(self):
        self.svc.on_login("pro_user")
        ok, _, player = self.svc.activate_pro_demo("pro_user")
        self.assertTrue(ok)
        self.assertTrue(player["is_pro"])
        self.assertFalse(player["show_ads"])

    def test_vip_pay_atomic_insufficient(self):
        self.svc.on_login("broke")
        profile_store.update_profile(
            "broke", lambda p: p.update({"coins": 10, "plan": "free", "pro_until": None})
        )
        ok, msg = self.svc.try_pay_premium_event("broke", "vip_convoy")
        self.assertFalse(ok)
        self.assertTrue(msg)
        self.assertEqual(self.svc.get_public("broke")["coins"], 10)

    def test_vip_pay_atomic_deducts(self):
        self.svc.on_login("vipbuyer")
        profile_store.update_profile(
            "vipbuyer", lambda p: p.update({"coins": 100, "plan": "free", "pro_until": None})
        )
        ok, _ = self.svc.try_pay_premium_event("vipbuyer", "vip_convoy")
        self.assertTrue(ok)
        self.assertEqual(self.svc.get_public("vipbuyer")["coins"], 40)


class CouponAndPlanTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        tmp = Path(self._tmpdir.name)
        profile_store.PROGRESS_PATH = tmp / "user_progress.json"
        import engagement.coupon_store as coupon_store
        coupon_store.COUPONS_PATH = tmp / "coupons.json"
        self.coupon_store = coupon_store
        self.svc = EngagementService()
        self.svc.on_login("couponuser")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_plan_prices(self):
        from engagement.catalog import pro_plans
        plans = {p["id"]: p for p in pro_plans()}
        self.assertEqual(plans["pro"]["price_usd"], 1)
        self.assertEqual(plans["pro_plus"]["price_usd"], 2)
        self.assertEqual(plans["ultra"]["price_usd"], 5)
        self.assertEqual(plans["pro"]["price_krw"], 1400)
        self.assertEqual(plans["pro_plus"]["price_krw"], 2800)
        self.assertEqual(plans["ultra"]["price_krw"], 7000)

    def test_coupon_grants_week_of_pro(self):
        ok, _, player = self.svc.redeem_coupon("couponuser", "RDT1WEEK")
        self.assertTrue(ok)
        self.assertTrue(player["is_pro"])
        self.assertEqual(player["plan"], "pro")

    def test_coupon_rejects_second_use(self):
        self.svc.redeem_coupon("couponuser", "rdt1week")
        ok, message, _ = self.svc.redeem_coupon("couponuser", "RDT1WEEK")
        self.assertFalse(ok)
        self.assertIn("이미", message)

    def test_coupon_rejects_bad_format(self):
        ok, message, _ = self.svc.redeem_coupon("couponuser", "NO")
        self.assertFalse(ok)
        self.assertIn("8", message)

    def test_paid_ultra_not_downgraded_by_coupon(self):
        self.svc.grant_plan("couponuser", "ultra", days=30, source="toss")
        ok, _, player = self.svc.redeem_coupon("couponuser", "RDT1WEEK")
        self.assertTrue(ok)
        self.assertEqual(player["plan"], "ultra")

    def test_coupon_stops_at_ten(self):
        for i in range(10):
            uid = f"cuser{i:02d}"
            self.svc.on_login(uid)
            ok, message, _ = self.svc.redeem_coupon(uid, "RDT1WEEK")
            self.assertTrue(ok, message)
        self.svc.on_login("cuser10")
        ok, message, _ = self.svc.redeem_coupon("cuser10", "RDT1WEEK")
        self.assertFalse(ok)
        self.assertIn("한도", message)


if __name__ == "__main__":
    unittest.main()
