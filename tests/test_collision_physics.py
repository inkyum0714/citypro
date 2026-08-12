import path_setup  # noqa: F401
import math
import unittest

from engine.vehicle import Vehicle
from engine.vehicle_physics import mass_for_type, resolve_collision_impulse
from engine.collision_system import CollisionSystem
from engine.traffic_manager import TrafficManager


class CollisionPhysicsTests(unittest.TestCase):
    def _road(self):
        return {
            "id": 1,
            "start": [0, 0],
            "end": [300, 0],
            "speed_limit": 50,
            "lanes": 1,
            "width": 18,
            "start_node_id": 1,
            "end_node_id": 2,
        }

    def test_type_masses(self):
        self.assertAlmostEqual(mass_for_type("car"), 1000.0)
        self.assertAlmostEqual(mass_for_type("truck"), 8000.0)
        self.assertGreater(mass_for_type("bus"), mass_for_type("car"))

    def test_vehicle_volume_and_occupancy(self):
        road = self._road()
        car = Vehicle(id=1, road=road, vehicle_type="car")
        bus = Vehicle(id=2, road=road, vehicle_type="bus")
        self.assertGreater(car.volume, 0)
        self.assertAlmostEqual(car.volume, car.length * car.width * car.height)
        self.assertGreater(bus.space_occupancy, car.space_occupancy)
        self.assertGreater(bus.mass_kg, car.mass_kg)
        payload = bus.to_dict()
        self.assertIn("volume", payload)
        self.assertIn("space_occupancy", payload)
        self.assertIn("height", payload)

    def test_action_reaction_equal_opposite_impulse(self):
        road = self._road()
        a = Vehicle(id=1, road=road, vehicle_type="car", speed=40, progress=0.4)
        b = Vehicle(id=2, road=road, vehicle_type="car", speed=10, progress=0.45)
        a.x, a.y = 100.0, 0.0
        b.x, b.y = 108.0, 0.0
        a.angle = 0.0
        b.angle = 0.0
        a.vx, a.vy = 40.0, 0.0
        b.vx, b.vy = 10.0, 0.0
        m = a.mass_kg
        result = resolve_collision_impulse(a, b)
        # ?�일 질량: ?�도 교환 경향 + 감쇠
        self.assertGreater(result["impulse"], 0.0)
        self.assertAlmostEqual(result["mass_a"], m)
        self.assertAlmostEqual(result["mass_b"], m)
        # ?�용-반작?? ?�동??변?�의 ????0 (감쇠 ???�리, 감쇠 ?�는 ????줄어??
        self.assertLess(a.current_speed + b.current_speed, 50.0)

    def test_heavy_truck_pushes_light_car(self):
        road = self._road()
        car = Vehicle(id=1, road=road, vehicle_type="car", speed=5, progress=0.4)
        truck = Vehicle(id=2, road=road, vehicle_type="truck", speed=35, progress=0.42)
        car.x, car.y = 120.0, 0.0
        truck.x, truck.y = 112.0, 0.0
        car.angle = truck.angle = 0.0
        car.vx, car.vy = 5.0, 0.0
        truck.vx, truck.vy = 35.0, 0.0
        car_speed_before = car.current_speed
        resolve_collision_impulse(truck, car)
        # ?�럭??밀�?가벼운 차는 ?�도 변?��? ????
        self.assertNotEqual(car.vx, 5.0)

    def test_police_clears_accident(self):
        manager = TrafficManager()
        manager.road_network.add_road([0, 0], [300, 0])
        road = manager.road_network.roads[0]
        a = manager.create_vehicle_on_edge(road, lane_index=0, progress=0.4)
        b = manager.create_vehicle_on_edge(road, lane_index=0, progress=0.45)
        a.in_accident = True
        b.in_accident = True
        a.state = b.state = "accident"
        result = manager.collisions.dispatch_police()
        self.assertTrue(result["ok"])
        manager.collisions._tick_rescue(10.0)
        self.assertEqual(manager.collisions.open_accident_count(), 0)


if __name__ == "__main__":
    unittest.main()
