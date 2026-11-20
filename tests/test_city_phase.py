import path_setup  # noqa: F401
import unittest

from engine.city_systems import BUILDING_CATALOG
from engine.traffic_light import TrafficLight
from engine.traffic_manager import TrafficManager


class CityPhaseTests(unittest.TestCase):
    def setUp(self):
        self.mgr = TrafficManager()
        self.mgr.add_road([0, 0], [320, 0])

    def test_three_house_types_and_civic_market(self):
        detached = self.mgr.add_building_at(40, 18, "house_detached")
        town = self.mgr.add_building_at(90, 18, "house_town")
        apt = self.mgr.add_building_at(150, 18, "house_apt")
        hall = self.mgr.add_building_at(210, 18, "city_hall")
        market = self.mgr.add_building_at(270, 18, "market")
        self.assertIsNotNone(detached)
        self.assertIsNotNone(town)
        self.assertIsNotNone(apt)
        self.assertIsNotNone(hall)
        self.assertIsNotNone(market)
        self.assertEqual(self.mgr.buildings.count(), 5)
        self.assertGreater(self.mgr.buildings.trip_demand(), 8)
        again = self.mgr.add_building_at(220, 18, "city_hall")
        self.assertIsNone(again)
        for key in (
            "house_detached", "house_town", "house_apt", "villa", "officetel",
            "city_hall", "police", "fire", "school", "hospital", "library", "park",
            "market", "convenience", "pharmacy", "restaurant", "office", "hotel",
            "gas_station", "factory",
        ):
            self.assertIn(key, BUILDING_CATALOG)

    def test_per_approach_phases_split_axes(self):
        mgr = TrafficManager()
        mgr.add_road([0, 200], [400, 200])
        mgr.add_road([200, 0], [200, 400])
        lights = list(mgr.signals.lights.values())
        self.assertGreaterEqual(len(lights), 1)
        junction = max(lights, key=lambda light: len(light.approaches))
        self.assertGreaterEqual(len(junction.approaches), 3)
        self.assertEqual({ap["axis"] for ap in junction.approaches}, {0, 1})
        junction.phase = "a_green"
        by_axis = {ap["axis"]: junction.state_for(ap["edge_id"]) for ap in junction.approaches}
        self.assertEqual(by_axis[0], "green")
        self.assertEqual(by_axis[1], "red")
        junction.phase = "b_green"
        by_axis = {ap["axis"]: junction.state_for(ap["edge_id"]) for ap in junction.approaches}
        self.assertEqual(by_axis[0], "red")
        self.assertEqual(by_axis[1], "green")

    def test_crash_dispatches_hospital_119_112(self):
        mgr = TrafficManager()
        mgr.add_road([0, 0], [400, 0])
        self.assertIsNotNone(mgr.add_building_at(40, 18, "police"))
        self.assertIsNotNone(mgr.add_building_at(140, 18, "fire"))
        self.assertIsNotNone(mgr.add_building_at(240, 18, "hospital"))
        road = mgr.road_network.roads[0]
        a = mgr.create_vehicle_on_edge(road, lane_index=0, progress=0.4)
        b = mgr.create_vehicle_on_edge(road, lane_index=0, progress=0.45)
        a.x, a.y = 160.0, 0.0
        b.x, b.y = 168.0, 0.0
        applied = mgr.collisions.apply_client_reports([{"id_a": a.id, "id_b": b.id, "impulse": 40.0}])
        self.assertEqual(applied, 1)
        roles = {v.response_role for v in mgr.vehicles if getattr(v, "response_role", None)}
        self.assertEqual(roles, {"112", "119", "hospital"})
        for _ in range(30):
            mgr.collisions.tick(0.5)
        self.assertEqual(mgr.collisions.open_accident_count(), 0)

    def test_crosswalk_yields_when_pedestrian(self):
        walk = self.mgr.add_crosswalk_at(160, 0)
        self.assertIsNotNone(walk)
        walk["pedestrian"] = True
        car = self.mgr.spawn_vehicle(vehicle_type="car")
        self.assertIsNotNone(car)
        car.progress = 0.2
        car.refresh_world_position()
        dist = self.mgr.crosswalks.yield_distance(car)
        self.assertIsNotNone(dist)
        self.assertGreater(dist, 0)

    def test_yellow_stop_only_if_can_stop(self):
        light = TrafficLight(1, 0, 0)
        light.state = "yellow"
        self.assertTrue(light.should_stop(40.0, 8.0))
        self.assertFalse(light.should_stop(2.0, 28.0))
        light.state = "walk"
        self.assertTrue(light.must_stop_before_line())
        self.assertTrue(light.should_stop(12.0, 10.0))

    def test_snapshot_roundtrip_city(self):
        self.mgr.add_building_at(80, 16, "house_detached")
        self.mgr.add_crosswalk_at(120, 0)
        snap = self.mgr.export_city_snapshot()
        other = TrafficManager()
        other.load_city_snapshot(snap)
        self.assertEqual(other.buildings.count(), 1)
        self.assertEqual(len(other.crosswalks.crosswalks), 1)
        state = other.get_state(full=True)
        self.assertTrue(state["physics"]["client_physics"])
        self.assertGreaterEqual(state["physics"]["max_pairs_per_frame"], 80)
        self.assertTrue(any(b["id"] == "house_apt" for b in state["building_catalog"]))

    def test_plan_building_slots(self):
        from engagement.catalog import pro_plans

        plans = {p["id"]: p for p in pro_plans()}
        self.assertEqual(plans["pro"]["building_slots"], 80)
        self.assertEqual(plans["pro_plus"]["building_slots"], 160)
        self.assertEqual(plans["ultra"]["building_slots"], -1)


if __name__ == "__main__":
    unittest.main()
