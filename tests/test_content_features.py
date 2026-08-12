import path_setup  # noqa: F401
import tempfile
import unittest
from pathlib import Path

import engagement.profile_store as profile_store
from engagement.service import EngagementService
from engagement.stages import get_stage, stage_catalog
from engine.content_systems import CargoSystem, CARGO_IDS
from engine.traffic_manager import TrafficManager


class ContentFeatureTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        profile_store.PROGRESS_PATH = Path(self._tmpdir.name) / "user_progress.json"
        self.svc = EngagementService()
        self.mgr = TrafficManager()

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_bus_stop_and_golden_metrics(self):
        self.mgr.add_road([0, 0], [300, 0])
        stop = self.mgr.add_bus_stop_at(150, 0)
        self.assertIsNotNone(stop)
        self.assertEqual(len(self.mgr.bus_stops.stops), 1)
        # 차량 여러 대 배치 후 골든 흐름 가능
        for _ in range(3):
            self.mgr.spawn_vehicle(vehicle_type="car")
        gained = 0.0
        for _ in range(30):
            self.mgr.step(0.1)
            gained += self.mgr.frame_metrics.get("golden_flow_seconds", 0)
        self.assertGreaterEqual(gained, 0.0)

    def test_cargo_classify(self):
        self.mgr.add_road([0, 0], [300, 0])
        truck = self.mgr.spawn_vehicle(vehicle_type="truck")
        self.assertIsNotNone(truck)
        self.assertEqual(truck.cargo_type, "unclassified")
        result = self.mgr.classify_cargo(truck.id, "food")
        self.assertTrue(result["ok"])
        self.assertEqual(truck.cargo_type, "food")
        self.assertIn("food", CARGO_IDS)

    def test_stage_start_and_claim(self):
        self.svc.on_login("stager")
        stage = stage_catalog()[0]
        ok, _, player = self.svc.start_stage("stager", stage["id"])
        self.assertTrue(ok)
        self.assertEqual(player["active_stage_id"], stage["id"])
        self.mgr.start_stage(stage)
        self.assertEqual(self.mgr.stage_id, stage["id"])
        # 목표 충족 시뮬레이션
        progress = {g["metric"]: float(g["target"]) for g in stage["goals"]}
        ok, msg, player = self.svc.claim_stage("stager", stage["id"], progress)
        self.assertTrue(ok, msg)
        self.assertIn(stage["id"], player["stages_completed"])

    def test_daily_quests_include_new_content(self):
        self.svc.on_login("quester")
        player = self.svc.get_public("quester")
        ids = {q["id"] for q in player["daily"]["quests"]}
        self.assertIn("golden_hour", ids)
        self.assertIn("accident_cleanup", ids)
        self.assertIn("bus_stops", ids)
        self.assertIn("cargo_sort", ids)


if __name__ == "__main__":
    unittest.main()
