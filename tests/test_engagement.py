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


if __name__ == "__main__":
    unittest.main()
