import path_setup  # noqa: F401
import tempfile
import unittest
from pathlib import Path

import backend.auth.user_store as user_store
from backend.engine.analytics import AnalyticsCollector
from backend.engine.traffic_manager import TrafficManager


class UserStoreTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        user_store.USERS_PATH = Path(self._tmpdir.name) / "users.json"
        user_store.USERS_PATH.write_text('{"users": {}}', encoding="utf-8")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_register_and_login(self):
        ok, _ = user_store.create_local_user("testuser", "Tester", "pass1234")
        self.assertTrue(ok)
        user = user_store.verify_local_user("testuser", "pass1234")
        self.assertIsNotNone(user)
        self.assertEqual(user["name"], "Tester")
        raw = user_store._load_raw()
        self.assertIn("testuser", raw["users"])
        self.assertEqual(raw["users"]["testuser"]["login_id"], "testuser")

    def test_google_does_not_overwrite_local(self):
        ok, _ = user_store.create_local_user("alice", "LocalAlice", "pass1234")
        self.assertTrue(ok)
        google_user = user_store.upsert_google_user("alice", "GoogleAlice", "sub-123")
        self.assertNotEqual(google_user["login_id"], "alice")
        local = user_store.get_user("alice")
        self.assertEqual(local["auth_provider"], "local")
        self.assertTrue(user_store.verify_local_user("alice", "pass1234"))


class AnalyticsTests(unittest.TestCase):
    def test_collector_csv(self):
        collector = AnalyticsCollector()
        collector._samples.append(
            {
                "sim_time": 1.0,
                "throughput_per_min": 12.0,
                "avg_wait_seconds": 0.5,
                "active_vehicles": 3,
                "congestion_level": 0.2,
            }
        )
        csv_text = collector.export_csv()
        self.assertIn("throughput_per_min", csv_text)


class TrafficManagerAnalyticsTests(unittest.TestCase):
    def test_state_includes_analytics(self):
        manager = TrafficManager()
        manager.road_network.add_road([0, 0], [200, 0])
        state = manager.get_state()
        self.assertIn("analytics", state)


if __name__ == "__main__":
    unittest.main()
