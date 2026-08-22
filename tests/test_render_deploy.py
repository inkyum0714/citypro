import path_setup  # noqa: F401
import unittest

from engine.traffic_manager import TrafficManager
from main import create_app


class RenderDeployTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_health_unauthenticated(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["service"], "cityflow")

    def test_root_redirects_without_login(self):
        response = self.client.get("/")
        self.assertIn(response.status_code, (302, 303))


class StateSnapshotTests(unittest.TestCase):
    def test_full_state_includes_catalogs(self):
        manager = TrafficManager()
        manager.road_network.add_road([0, 0], [200, 0])
        state = manager.get_state(full=True)
        self.assertEqual(state["snapshot"], "full")
        self.assertIn("event_catalog", state)
        self.assertIn("cargo_catalog", state)
        self.assertIn("series", state["analytics"])

    def test_tick_state_omits_static_catalogs(self):
        manager = TrafficManager()
        manager.road_network.add_road([0, 0], [200, 0])
        state = manager.get_state(full=False)
        self.assertEqual(state["snapshot"], "tick")
        self.assertNotIn("event_catalog", state)
        self.assertNotIn("cargo_catalog", state)
        self.assertNotIn("series", state["analytics"])
        self.assertIn("latest", state["analytics"])
        self.assertIn("vehicles", state)
        self.assertIn("stats", state)
        self.assertIn("roads", state)
        self.assertTrue(state["stats"]["client_physics"])

    def test_subsequent_tick_omits_unchanged_network(self):
        manager = TrafficManager()
        manager.road_network.add_road([0, 0], [200, 0])
        manager._mark_network_changed()
        first = manager.get_state(full=False)
        self.assertIn("roads", first)
        second = manager.get_state(full=False)
        self.assertNotIn("roads", second)
        self.assertNotIn("nodes", second)
        self.assertEqual(second["network_rev"], first["network_rev"])

    def test_full_state_includes_physics_config(self):
        manager = TrafficManager()
        state = manager.get_state(full=True)
        self.assertIn("physics", state)
        self.assertTrue(state["physics"]["client_physics"])
        self.assertIn("collision_radius_scale", state["physics"])


if __name__ == "__main__":
    unittest.main()
