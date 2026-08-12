import path_setup  # noqa: F401
import unittest

from backend.engine.idm import compute_idm_acceleration, net_bumper_gap
from backend.engine.lane_controller import LaneController
from backend.engine.mobil import MobilLaneAdvisor
from backend.engine.road_network import RoadNetwork
from backend.engine.road_segment import RoadSegment
from backend.engine.traffic_manager import TrafficManager
from backend.engine.vehicle import Vehicle, stopping_distance


class IdmTests(unittest.TestCase):
    def test_free_flow_accelerates_toward_desired(self):
        a = compute_idm_acceleration(10.0, 50.0)
        self.assertGreater(a, 0.0)

    def test_tight_gap_brakes(self):
        a_free = compute_idm_acceleration(40.0, 50.0)
        a_tight = compute_idm_acceleration(40.0, 50.0, net_gap=8.0, lead_speed=10.0)
        self.assertLess(a_tight, a_free)

    def test_net_bumper_gap(self):
        self.assertAlmostEqual(net_bumper_gap(30.0, 14.0, 14.0), 16.0)


class RoadNetworkTests(unittest.TestCase):
    def test_add_road(self):
        network = RoadNetwork()
        road = network.add_road([10, 20], [30, 40])
        self.assertEqual(road["start"], [10, 20])
        self.assertEqual(road["end"], [30, 40])
        self.assertEqual(road["id"], 1)
        self.assertIn("type", road)
        self.assertIn("start_node_id", road)
        self.assertIn("end_node_id", road)
        self.assertEqual(len(network.nodes), 2)

    def test_merge_nodes_at_intersection(self):
        network = RoadNetwork()
        network.add_road([0, 0], [100, 0])
        network.add_road([100, 0], [100, 80])
        self.assertEqual(len(network.nodes), 3)
        self.assertEqual(len(network.edges), 2)

    def test_t_junction_splits_road(self):
        network = RoadNetwork()
        network.add_road([0, 0], [200, 0])
        network.add_road([100, 0], [100, 100])
        # 수평 도로가 중간에서 분할되어 Edge 3개
        self.assertEqual(len(network.edges), 3)
        self.assertEqual(len(network.nodes), 4)
        degrees = [len(network.edges_from_node(n)) for n in network.nodes]
        self.assertIn(3, degrees)

    def test_crossing_roads_connect(self):
        network = RoadNetwork()
        network.add_road([0, 0], [200, 200])
        network.add_road([0, 200], [200, 0])
        self.assertGreaterEqual(len(network.edges), 4)
        self.assertGreaterEqual(len(network.nodes), 5)


class RoadSegmentTests(unittest.TestCase):
    def test_lead_gap_same_lane_only(self):
        road = {"id": 1, "start": [0, 0], "end": [100, 0], "speed_limit": 50, "lanes": 2}
        segment = RoadSegment.from_road_dict(road)
        lead = Vehicle(id=1, road=road, vehicle_type="car", progress=0.2, speed=10, lane_index=0)
        follower = Vehicle(id=2, road=road, vehicle_type="car", progress=0.1, speed=10, lane_index=0)
        other_lane = Vehicle(id=3, road=road, vehicle_type="car", progress=0.15, speed=10, lane_index=1)
        segment.add_vehicle(lead)
        segment.add_vehicle(follower)
        segment.add_vehicle(other_lane)
        gap = segment.lead_gap_for(follower)
        self.assertAlmostEqual(gap, 10.0)


class VehicleTests(unittest.TestCase):
    def test_update_position_along_road(self):
        road = {
            "id": 1,
            "start": [0, 0],
            "end": [100, 0],
            "speed_limit": 100,
            "lanes": 1,
            "width": 18,
        }
        vehicle = Vehicle(id=1, road=road, vehicle_type="car", speed=10)

        vehicle.update_position(dt=1.0)
        self.assertAlmostEqual(vehicle.x, 10.0, places=1)
        self.assertAlmostEqual(vehicle.y, 0.0)

        vehicle.update_position(dt=1.0)
        self.assertGreater(vehicle.x, 15.0)

    def test_stopping_distance_increases_with_speed(self):
        d_slow = stopping_distance(10.0)
        d_fast = stopping_distance(30.0)
        self.assertGreater(d_fast, d_slow)


class TrafficManagerTests(unittest.TestCase):
    def test_spawn_multiplier_reduces_on_accident(self):
        from backend.engine.events import EventManager

        manager = EventManager()
        self.assertAlmostEqual(manager.get_spawn_multiplier(), 1.0)
        manager.add_event("accident")
        self.assertLess(manager.get_spawn_multiplier(), 1.0)
        manager.add_event("rush_hour")
        # 사고 감소 × 러시아워 증가 → 둘 다 반영된 곱셈
        self.assertNotAlmostEqual(manager.get_spawn_multiplier(), 2.4)

    def test_trigger_event_and_stats(self):
        manager = TrafficManager()
        manager.road_network.add_road([0, 0], [200, 0])
        event = manager.trigger_event("accident")
        self.assertIsNotNone(event)
        state = manager.get_state()
        self.assertEqual(state["stats"]["road_count"], 1)
        self.assertEqual(state["stats"]["node_count"], 2)
        self.assertEqual(state["stats"]["drive_model"], "idm+mobil")
        self.assertGreaterEqual(state["stats"]["active_events"], 1)

    def test_spawn_at_edge_start(self):
        manager = TrafficManager()
        manager.road_network.add_road([0, 0], [300, 0])
        vehicle = manager.create_vehicle_on_edge(manager.road_network.roads[0], lane_index=0)
        self.assertAlmostEqual(vehicle.progress, 0.0)
        self.assertEqual(vehicle.lane_index, 0)

    def test_user_spawn_at_world_click(self):
        manager = TrafficManager()
        manager.road_network.add_road([0, 0], [300, 0])
        vehicle = manager.spawn_vehicle_user(world_x=150.0, world_y=0.0)
        self.assertIsNotNone(vehicle)
        self.assertGreater(vehicle.progress, 0.4)
        self.assertLess(vehicle.progress, 0.6)


class LaneControllerTests(unittest.TestCase):
    def test_turn_signal_before_lane_change(self):
        manager = TrafficManager()
        road = manager.road_network.add_road([0, 0], [400, 0])
        road["lanes"] = 2
        slow = manager.create_vehicle_on_edge(road, lane_index=0, progress=0.35)
        slow.current_speed = 5.0
        slow.base_speed = 5.0
        chaser = manager.create_vehicle_on_edge(road, lane_index=0, progress=0.2)
        chaser.base_speed = 60.0
        chaser.max_speed = 60.0
        chaser.current_speed = 30.0
        manager._sync_segments()
        manager._rebuild_segment_vehicles()
        controller = LaneController(manager)
        controller.tick(chaser, 0.5, speed_factor=1.0)
        self.assertIn(chaser.turn_signal, ("left", None))

    def test_mobil_prefers_free_lane(self):
        manager = TrafficManager()
        road = manager.road_network.add_road([0, 0], [500, 0])
        road["lanes"] = 2
        slow = manager.create_vehicle_on_edge(road, lane_index=0, progress=0.4)
        slow.current_speed = 6.0
        ego = manager.create_vehicle_on_edge(road, lane_index=0, progress=0.25)
        ego.current_speed = 35.0
        ego.base_speed = 55.0
        manager._sync_segments()
        manager._rebuild_segment_vehicles()
        advisor = MobilLaneAdvisor(manager)
        lane = advisor.best_adjacent_lane(ego, desired_speed=55.0)
        self.assertEqual(lane, 1)


class Phase4Tests(unittest.TestCase):
    def test_dijkstra_on_l_shape(self):
        network = RoadNetwork()
        network.add_road([0, 0], [200, 0])
        network.add_road([200, 0], [200, 150])
        from backend.engine.pathfinding import dijkstra_route

        steps = dijkstra_route(network.edges, 1, 3)
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0].to_node_id, 2)
        self.assertEqual(steps[1].to_node_id, 3)

    def test_vehicle_routes_through_intersection(self):
        """도로 끝=도착 모드: 첫 도로 끝에 도착하면 소멸(교차로 경유 없음)."""
        manager = TrafficManager()
        manager.road_network.add_road([0, 0], [300, 0])
        manager.road_network.add_road([300, 0], [300, 200])
        manager._sync_network_systems()
        v = manager.create_vehicle_on_edge(
            manager.road_network.roads[0], lane_index=0, vehicle_type="car"
        )
        self.assertEqual(v.destination_node_id, v.exit_node_id)
        self.assertEqual(len(v.route_steps), 1)
        for _ in range(900):
            manager.step(0.033)
        self.assertGreater(manager.total_completed, 0)
        self.assertEqual(len(manager.vehicles), 0)

    def test_bidirectional_and_lanes(self):
        network = RoadNetwork()
        edge = network.add_road([0, 0], [200, 0], lanes=3, bidirectional=True)
        self.assertIsNotNone(edge)
        self.assertEqual(edge["lanes"], 3)
        self.assertTrue(edge["bidirectional"])
        self.assertEqual(len(network.edges), 2)
        reverse = network.get_road(int(edge["pair_id"]))
        self.assertIsNotNone(reverse)
        self.assertEqual(reverse["start_node_id"], edge["end_node_id"])
        self.assertEqual(reverse["end_node_id"], edge["start_node_id"])
        self.assertEqual(reverse["lanes"], 3)

    def test_auto_event_spawns_once_per_interval(self):
        from unittest.mock import patch

        from backend.engine.events import EventManager

        em = EventManager()
        roads = [{"id": 1}, {"id": 2}]
        with patch("backend.engine.events.random.random", return_value=0.01), patch(
            "backend.engine.events.random.choice", side_effect=lambda seq: seq[0]
        ), patch(
            "utils.variables.get_variable",
            side_effect=lambda section, key, default=None: {
                ("events", "auto_interval_seconds"): 60.0,
                ("events", "auto_spawn_chance"): 0.05,
            }.get((section, key), default),
        ):
            em.tick(30.0, roads)
            self.assertEqual(len(em.events), 0)
            em.tick(30.0, roads)
            self.assertEqual(len(em.events), 1)
            self.assertEqual(em.events[0].event_type, "construction")
            self.assertEqual(em.events[0].road_id, 1)

    def test_auto_event_skips_when_chance_misses(self):
        from unittest.mock import patch

        from backend.engine.events import EventManager

        em = EventManager()
        roads = [{"id": 1}]
        with patch("backend.engine.events.random.random", return_value=0.99), patch(
            "utils.variables.get_variable",
            side_effect=lambda section, key, default=None: {
                ("events", "auto_interval_seconds"): 60.0,
                ("events", "auto_spawn_chance"): 0.05,
            }.get((section, key), default),
        ):
            em.tick(60.0, roads)
            self.assertEqual(len(em.events), 0)

    def test_traffic_light_at_junction(self):
        manager = TrafficManager()
        manager.road_network.add_road([0, 0], [200, 0])
        manager.road_network.add_road([200, 0], [200, 100])
        manager._sync_network_systems()
        self.assertGreaterEqual(len(manager.signals.lights), 1)


if __name__ == "__main__":
    unittest.main()
