import path_setup  # noqa: F401
import math
import unittest

from backend.engine.vehicle import Vehicle
from backend.engine.vehicle_physics import (
    avoidance_constraints,
    detect_collision_pair,
)


class VehiclePhysicsTests(unittest.TestCase):
    def test_default_mass_one_ton(self):
        road = {
            "id": 1,
            "start": [0, 0],
            "end": [100, 0],
            "speed_limit": 50,
            "lanes": 1,
            "width": 18,
            "start_node_id": 1,
            "end_node_id": 2,
        }
        v = Vehicle(id=1, road=road, vehicle_type="car", speed=10)
        self.assertAlmostEqual(v.mass_kg, 1000.0)

    def test_collision_detected_when_overlapping(self):
        road = {
            "id": 1,
            "start": [0, 0],
            "end": [100, 0],
            "speed_limit": 50,
            "lanes": 1,
            "width": 18,
            "start_node_id": 1,
            "end_node_id": 2,
        }
        a = Vehicle(id=1, road=road, vehicle_type="car", speed=20, progress=0.5)
        b = Vehicle(id=2, road=road, vehicle_type="car", speed=15, progress=0.51)
        a.x, a.y = 50, 0
        b.x, b.y = 51, 0
        a.angle = 0
        b.angle = math.pi
        self.assertTrue(detect_collision_pair(a, b))

    def test_avoidance_tightens_gap(self):
        road = {
            "id": 1,
            "start": [0, 0],
            "end": [200, 0],
            "speed_limit": 50,
            "lanes": 2,
            "width": 18,
            "start_node_id": 1,
            "end_node_id": 2,
        }
        ego = Vehicle(id=1, road=road, vehicle_type="car", speed=30, progress=0.4, lane_index=0)
        other = Vehicle(id=2, road=road, vehicle_type="car", speed=5, progress=0.45, lane_index=1)
        ego.x, ego.y = 80, 0
        other.x, other.y = 88, 2
        ego.angle = 0
        other.angle = math.pi
        gap, speed, _ = avoidance_constraints(ego, [other], 999.0, None, None)
        self.assertLess(gap, 999.0)
        self.assertIsNotNone(speed)


if __name__ == "__main__":
    unittest.main()
