"""교통 시뮬레이션 틱·스폰·상태 집계."""

from __future__ import annotations

import random
from typing import Any

from engine.collision_system import CollisionSystem
from engine.analytics import AnalyticsCollector
from engine.content_systems import BusStopSystem, CargoSystem, GoldenHourTracker
from engine.events import EventManager, SimulationEvent
from engine.lane_controller import LaneController
from engine.road_network import RoadNetwork
from engine.road_segment import RoadSegment
from engine.routing_service import RoutingService
from engine.traffic_light import SignalController
from engine.spatial_index import VehicleSpatialIndex
from engine.vehicle_physics import avoidance_constraints
from engine.vehicle import Vehicle
from engine.vehicle_spawner import VehicleSpawner
from utils.variables import get_variable


class TrafficManager:
    """도로 네트워크·차량·이벤트를 한 프레임씩 진행합니다."""

    def __init__(self) -> None:
        self.road_network = RoadNetwork()
        self.event_manager = EventManager()
        self.vehicles: list[Vehicle] = []
        self._segments: dict[int, RoadSegment] = {}
        self._next_vehicle_id = 1
        self.sim_time = 0.0
        self.total_spawned = 0
        self.total_completed = 0
        self.spawn_rate = float(get_variable("traffic_manager", "default_spawn_rate", 0.14))
        self.auto_spawn_enabled = bool(get_variable("traffic_manager", "auto_spawn_enabled", False))
        self.is_paused = False
        self.spawner = VehicleSpawner(self)
        self.lane_controller = LaneController(self)
        self.signals = SignalController()
        self.router = RoutingService(self)
        self.analytics = AnalyticsCollector()
        self._spatial = VehicleSpatialIndex()
        self._segments_dirty = True
        self.collisions = CollisionSystem(self)
        self.bus_stops = BusStopSystem(self)
        self.cargo = CargoSystem(self)
        self.golden_hour = GoldenHourTracker()
        self.accidents_cleared_total = 0
        self.stage_id: str | None = None
        self.stage_progress: dict[str, float] = {}
        self.frame_metrics: dict[str, float] = {}
        self._network_dirty = True
        self._cache_runtime_flags()

    def _cache_runtime_flags(self) -> None:
        self._use_signals = bool(get_variable("phase4", "use_traffic_signals", True))
        self._emergency_ignore_signal = bool(get_variable("phase4", "emergency_ignore_signal", True))
        self._idm_default_lead_length = float(get_variable("phase3", "idm_default_lead_length", 14.0))
        self._edge_end_is_destination = bool(get_variable("phase4", "edge_end_is_destination", True))
        self._use_routing = bool(get_variable("phase4", "use_routing", False))
        self._use_avoidance = bool(get_variable("vehicle", "use_collision_avoidance", True))
        self._use_idm = bool(get_variable("phase3", "use_idm", True))
        self._use_mobil = bool(get_variable("phase3", "use_mobil", True))
        self._adaptive_signals = bool(get_variable("phase6", "adaptive_traffic_lights", True))
        self._congestion_normalizer = float(
            get_variable("traffic_manager", "congestion_vehicles_per_road_normalizer", 8.0)
        )
        self._emergency_spawn_p = float(get_variable("vehicle", "emergency_spawn_probability", 0.08))
        self._default_dt = float(get_variable("traffic_manager", "default_dt", 0.033))

    def _apply_avoidance(
        self,
        vehicle: Vehicle,
        gap: float,
        lead_speed: float | None,
        lead_length: float | None,
    ) -> tuple[float, float | None, float | None]:
        if not self._use_avoidance:
            return gap, lead_speed, lead_length
        active = [v for v in self.vehicles if not v.finished and not getattr(v, "in_accident", False)]
        return avoidance_constraints(vehicle, active, gap, lead_speed, lead_length)

    def _sync_network_systems(self) -> None:
        if not self._network_dirty:
            return
        self.signals.sync_network(self.road_network.nodes, self.road_network.edges)
        self._network_dirty = False

    def _sync_segments(self) -> None:
        """도로 목록과 1D RoadSegment 캐시를 동기화합니다."""
        active_ids = {road["id"] for road in self.road_network.roads}
        for road_id in list(self._segments.keys()):
            if road_id not in active_ids:
                del self._segments[road_id]
        for road in self.road_network.roads:
            road_id = road["id"]
            if road_id not in self._segments:
                self._segments[road_id] = RoadSegment.from_road_dict(road)
            else:
                self._segments[road_id].length = RoadSegment.from_road_dict(road).length
                self._segments[road_id].road = road

    def _rebuild_segment_vehicles(self) -> None:
        """각 RoadSegment의 차량 리스트를 현재 active 차량으로 채웁니다."""
        if not self._segments_dirty:
            return
        for segment in self._segments.values():
            segment.clear_vehicles()
        self._spatial.rebuild(self.vehicles)
        for vehicle in self.vehicles:
            if vehicle.finished:
                continue
            segment = self._segments.get(vehicle.road_id)
            if segment is not None:
                segment.add_vehicle(vehicle)
        self._segments_dirty = False

    def _mark_segments_dirty(self) -> None:
        self._segments_dirty = True

    def _remap_vehicles_after_split(self, remap: dict[str, Any]) -> None:
        """Edge 분할 후 해당 도로 위 차량 progress·소속을 재배치합니다."""
        old_id = int(remap["old_id"])
        t = float(remap["t"])
        edge_a = remap["edge_a"]
        edge_b = remap["edge_b"]
        t = max(1e-6, min(1.0 - 1e-6, t))
        for vehicle in self.vehicles:
            if vehicle.road_id != old_id or vehicle.finished:
                continue
            if vehicle.progress < t:
                vehicle.road = edge_a
                vehicle.road_id = int(edge_a["id"])
                vehicle.progress = vehicle.progress / t
                vehicle.entry_node_id = int(edge_a["start_node_id"])
                vehicle.exit_node_id = int(edge_a["end_node_id"])
            else:
                vehicle.road = edge_b
                vehicle.road_id = int(edge_b["id"])
                vehicle.progress = (vehicle.progress - t) / (1.0 - t)
                vehicle.entry_node_id = int(edge_b["start_node_id"])
                vehicle.exit_node_id = int(edge_b["end_node_id"])
            vehicle.progress = max(0.0, min(0.999, vehicle.progress))
            vehicle.refresh_world_position()
            if self._use_routing:
                self.router.assign_route(vehicle)
        self._mark_segments_dirty()

    def add_road(
        self,
        start: list[float],
        end: list[float],
        road_type: str | None = None,
        *,
        lanes: int | None = None,
        bidirectional: bool = False,
    ) -> dict[str, Any] | None:
        """도로 추가 + 맞닿음/교차 연결 + 차량 remap."""
        edge = self.road_network.add_road(
            start,
            end,
            road_type=road_type,
            lanes=lanes,
            bidirectional=bidirectional,
        )
        for remap in self.road_network.last_remaps:
            self._remap_vehicles_after_split(remap)
        self._mark_segments_dirty()
        self._network_dirty = True
        self._sync_network_systems()
        self.router.reroute_network_changed()
        return edge

    def _approach_counts_for_signals(self) -> dict[int, int]:
        counts: dict[int, int] = {}
        stop_window = float(get_variable("phase4", "stop_line_offset_from_exit", 22.0))
        for vehicle in self.vehicles:
            if vehicle.finished:
                continue
            node_id = int(vehicle.exit_node_id)
            if self.signals.get_light(node_id) is None:
                continue
            dist = self.router.distance_to_stop_line(vehicle)
            if dist <= stop_window * 2.5:
                counts[node_id] = counts.get(node_id, 0) + 1
        return counts

    def create_vehicle_on_edge(
        self,
        edge: dict[str, Any],
        *,
        lane_index: int = 0,
        progress: float = 0.0,
        vehicle_type: str | None = None,
        travel_forward: bool = True,
    ) -> Vehicle:
        """Edge·차선에 차량을 배치하고 Phase 4 경로를 부여합니다."""
        vehicle = Vehicle(
            id=self._next_vehicle_id,
            road=edge,
            vehicle_type=vehicle_type,
            progress=progress,
            lane_index=lane_index,
        )
        vehicle.travel_forward = travel_forward
        if travel_forward:
            vehicle.entry_node_id = int(edge["start_node_id"])
            vehicle.exit_node_id = int(edge["end_node_id"])
        else:
            vehicle.entry_node_id = int(edge["end_node_id"])
            vehicle.exit_node_id = int(edge["start_node_id"])
        self._next_vehicle_id += 1
        self.vehicles.append(vehicle)
        self.total_spawned += 1
        self._mark_segments_dirty()
        self.router.assign_route(vehicle)
        vehicle.refresh_world_position()
        return vehicle

    def spawn_vehicle(self, vehicle_type: str | None = None) -> Vehicle | None:
        """
        Edge 시작점·빈 차선에 차량을 생성합니다 (Phase 2 스폰 규칙).

        Args:
            vehicle_type: 지정 타입 또는 None(랜덤).

        Returns:
            생성된 Vehicle 또는 스폰 불가 시 None.
        """
        return self.spawner.try_spawn(vehicle_type=vehicle_type)

    def spawn_vehicle_user(
        self,
        *,
        road_id: int | None = None,
        lane_index: int | None = None,
        progress: float | None = None,
        world_x: float | None = None,
        world_y: float | None = None,
        vehicle_type: str | None = None,
    ) -> Vehicle | None:
        """유저가 지정한 위치·도로에 차량 생성."""
        if world_x is not None and world_y is not None:
            return self.spawner.try_spawn_at_world(world_x, world_y, vehicle_type=vehicle_type)
        if road_id is not None:
            return self.spawner.try_spawn_on_edge(
                road_id,
                lane_index=lane_index,
                progress=progress,
                vehicle_type=vehicle_type,
            )
        return self.spawner.try_spawn(vehicle_type=vehicle_type)

    def _lead_vehicle_in_lane(self, vehicle: Vehicle) -> Vehicle | None:
        """동일 Edge·차선의 바로 앞 차."""
        segment = self._segments.get(vehicle.road_id)
        if segment is None:
            return None
        ahead = [
            other
            for other in segment.vehicles
            if other.id != vehicle.id
            and not other.finished
            and other.lane_index == vehicle.lane_index
            and other.progress > vehicle.progress
        ]
        if not ahead:
            return None
        return min(ahead, key=lambda o: o.progress)

    def _lead_context(self, vehicle: Vehicle) -> tuple[float, float | None, float | None]:
        """
        IDM용 전방 정보 (차량 + 신호 정지선 + 다차량 회피).

        Returns:
            (lead_gap, lead_speed, lead_length)
        """
        if getattr(vehicle, "in_accident", False):
            return 0.5, 0.0, vehicle.length

        gap = self._lead_gap_in_lane(vehicle)
        lead = self._lead_vehicle_in_lane(vehicle)
        lead_speed: float | None = None
        lead_length: float | None = None
        if lead is not None:
            lead_speed = lead.current_speed
            lead_length = lead.length

        if self._use_signals:
            ignore = vehicle.vehicle_type == "emergency" and self._emergency_ignore_signal
            light = self.signals.get_light(vehicle.exit_node_id)
            if light is not None and not ignore:
                stop_dist = self.router.distance_to_stop_line(vehicle)
                if light.must_stop_before_line() and stop_dist > 0.5 and stop_dist < gap:
                    vehicle.waiting_at_signal = True
                    gap, lead_speed, lead_length = stop_dist, 0.0, self._idm_default_lead_length
                else:
                    vehicle.waiting_at_signal = False
            else:
                vehicle.waiting_at_signal = False
        else:
            vehicle.waiting_at_signal = False

        return self._apply_avoidance(vehicle, gap, lead_speed, lead_length)

    def _lead_gap_in_lane(self, vehicle: Vehicle) -> float:
        """동일 Edge·동일 차선 전방 간격."""
        segment = self._segments.get(vehicle.road_id)
        if segment is None:
            return float(get_variable("vehicle", "lead_gap_no_obstacle", 999.0))
        return segment.lead_gap_for(vehicle)

    def _lead_gap(self, vehicle: Vehicle) -> float:
        """동일 도로·동일 차선 전방 차량까지 간격."""
        return self._lead_gap_in_lane(vehicle)

    def _handle_edge_transitions(self) -> None:
        """progress≥1인 차량의 도착 소멸 또는 다음 Edge 전환."""
        for vehicle in self.vehicles:
            if vehicle.finished or vehicle.progress < 1.0:
                continue
            # 도로 끝=도착 모드이거나 라우팅 사용 시 라우터에 위임
            if self._edge_end_is_destination or self._use_routing:
                self.router.advance_at_end(vehicle)
            else:
                vehicle.finished = True
                vehicle.state = "arrived"

    def step(self, dt: float | None = None) -> None:
        """
        한 시뮬레이션 프레임: 이벤트·스폰·차선 변경·차량 물리·완주 제거.

        Args:
            dt: 시간 간격. None이면 all_variable.json 기본값.
        """
        if self.is_paused:
            return

        if dt is None:
            dt = self._default_dt

        self.sim_time += dt
        self._sync_network_systems()
        approach = self._approach_counts_for_signals()
        self.signals.tick(dt, approach_counts=approach)
        self.event_manager.tick(dt, self.road_network.roads)

        spawn_chance = self.spawn_rate * self.event_manager.get_spawn_multiplier()
        if self.auto_spawn_enabled and random.random() < spawn_chance:
            boosted_type = None
            if random.random() < self._emergency_spawn_p:
                boosted_type = "emergency"
            self.spawn_vehicle(vehicle_type=boosted_type)

        self._sync_segments()
        self._rebuild_segment_vehicles()

        for vehicle in self.vehicles:
            if getattr(vehicle, "in_accident", False):
                continue
            speed_factor = self.event_manager.get_speed_factor(vehicle.road_id, vehicle.progress)
            self.lane_controller.tick(vehicle, dt, speed_factor=speed_factor)

        for vehicle in self.vehicles:
            if getattr(vehicle, "in_accident", False):
                # 사고 차량: 작용-반작용 잔여 속도만 감쇠
                vehicle.update_position(dt, speed_factor=0.0, lead_gap=0.5, lead_speed=0.0)
                continue
            if self.bus_stops.tick_vehicle(vehicle, dt):
                vehicle.refresh_world_position()
                continue
            speed_factor = self.event_manager.get_speed_factor(vehicle.road_id, vehicle.progress)
            lead_gap, lead_speed, lead_length = self._lead_context(vehicle)
            if vehicle.waiting_at_signal:
                self.analytics.on_wait_sample(dt)
            vehicle.update_position(
                dt,
                speed_factor=speed_factor,
                lead_gap=lead_gap,
                lead_speed=lead_speed,
                lead_length=lead_length,
            )
            vehicle.refresh_world_position()

        self._handle_edge_transitions()
        cleared_before = self.accidents_cleared_total
        self.collisions.tick(dt)
        self.collisions.clear_stale_pairs()
        cleared_delta = self.accidents_cleared_total - cleared_before

        golden_delta = self.golden_hour.tick(self.vehicles, dt)

        finished = [vehicle for vehicle in self.vehicles if vehicle.finished]
        self.total_completed += len(finished)
        for _ in finished:
            self.analytics.on_trip_completed()
        self.analytics.tick(self.sim_time, self, completed_this_frame=len(finished))
        self.vehicles = [vehicle for vehicle in self.vehicles if not vehicle.finished]
        if finished:
            self._mark_segments_dirty()

        self.frame_metrics = {
            "trips_completed": float(len(finished)),
            "golden_flow_seconds": float(golden_delta),
            "accidents_cleared": float(cleared_delta),
            "bus_boardings": 0.0,
        }
        if self.stage_id:
            self._bump_stage("trips_completed", len(finished))
            self._bump_stage("golden_flow_seconds", golden_delta)
            self._bump_stage("accidents_cleared", cleared_delta)

    def trigger_event(
        self,
        event_type: str,
        road_id: int | None = None,
        message: str | None = None,
    ) -> SimulationEvent | None:
        """이벤트를 등록합니다. road_id가 없으면 임의 도로."""
        if road_id is None and self.road_network.roads:
            road_id = random.choice(self.road_network.roads)["id"]
        return self.event_manager.add_event(event_type, road_id=road_id, message=message)

    def _bump_stage(self, metric: str, amount: float) -> None:
        if not self.stage_id or amount <= 0:
            return
        self.stage_progress[metric] = float(self.stage_progress.get(metric, 0.0)) + float(amount)

    def add_bus_stop_at(self, x: float, y: float) -> dict[str, Any] | None:
        stop = self.bus_stops.add_at_world(x, y)
        if stop:
            self._bump_stage("bus_stops_built", 1)
        return stop

    def classify_cargo(self, vehicle_id: int, cargo_type: str) -> dict[str, Any]:
        result = self.cargo.classify(vehicle_id, cargo_type)
        if result.get("ok"):
            self._bump_stage("cargo_classified", 1)
            self.frame_metrics["cargo_classified"] = float(self.frame_metrics.get("cargo_classified", 0)) + 1
        return result

    def start_stage(self, stage: dict[str, Any]) -> None:
        """스테이지 시드 맵 로드 및 진행도 초기화."""
        self.reset()
        network = stage.get("network")
        if network:
            self.road_network.load_snapshot(network)
        self.stage_id = str(stage["id"])
        self.stage_progress = {g["metric"]: 0.0 for g in stage.get("goals") or []}
        self.auto_spawn_enabled = True
        self._network_dirty = True
        self._mark_segments_dirty()
        self._sync_network_systems()
        self.router.reroute_network_changed()

    def note_road_built(self) -> None:
        self._bump_stage("roads_built", 1)

    def export_city_snapshot(self) -> dict[str, Any]:
        """플레이어 도시 저장용."""
        return {
            "network": self.road_network.export_snapshot(),
            "spawn_rate": self.spawn_rate,
            "auto_spawn_enabled": self.auto_spawn_enabled,
            "bus_stops": self.bus_stops.export(),
        }

    def load_city_snapshot(self, snapshot: dict[str, Any]) -> None:
        """도시 불러오기 — 차량·이벤트는 초기화."""
        self.reset()
        network = snapshot.get("network")
        if network:
            self.road_network.load_snapshot(network)
        self.spawn_rate = float(snapshot.get("spawn_rate", self.spawn_rate))
        self.auto_spawn_enabled = bool(snapshot.get("auto_spawn_enabled", self.auto_spawn_enabled))
        self.bus_stops.load(snapshot.get("bus_stops"))
        self._network_dirty = True
        self._mark_segments_dirty()
        self.router.reroute_network_changed()

    def reset(self) -> None:
        """도로·차량·통계를 초기 상태로 되돌립니다."""
        self.road_network = RoadNetwork()
        self.event_manager = EventManager()
        self.vehicles = []
        self._segments = {}
        self._next_vehicle_id = 1
        self.sim_time = 0.0
        self.total_spawned = 0
        self.total_completed = 0
        self.is_paused = False
        self.spawn_rate = float(get_variable("traffic_manager", "default_spawn_rate", 0.14))
        self.auto_spawn_enabled = bool(get_variable("traffic_manager", "auto_spawn_enabled", False))
        self.spawner = VehicleSpawner(self)
        self.lane_controller = LaneController(self)
        self.signals = SignalController()
        self.router = RoutingService(self)
        self.analytics = AnalyticsCollector()
        self._spatial = VehicleSpatialIndex()
        self._segments_dirty = True
        self.collisions = CollisionSystem(self)
        self.bus_stops = BusStopSystem(self)
        self.cargo = CargoSystem(self)
        self.golden_hour = GoldenHourTracker()
        self.accidents_cleared_total = 0
        self.stage_id = None
        self.stage_progress = {}
        self.frame_metrics = {}
        self._network_dirty = True
        self._cache_runtime_flags()
        self.analytics.reset()

    def export_analytics_csv(self) -> str:
        return self.analytics.export_csv()

    def _congestion_level(self) -> float:
        """도로당 공간 점유(space_occupancy) 합 기반 혼잡도 0~1."""
        if not self.road_network.roads or not self.vehicles:
            return 0.0

        per_road: dict[int, float] = {}
        for vehicle in self.vehicles:
            occ = float(getattr(vehicle, "space_occupancy", 1.0) or 1.0)
            per_road[vehicle.road_id] = per_road.get(vehicle.road_id, 0.0) + occ

        normalizer = self._congestion_normalizer
        max_density = max(per_road.values())
        return min(1.0, max_density / normalizer)

    def get_state(self, *, full: bool = True) -> dict[str, Any]:
        """WebSocket/API용 상태 스냅샷.

        Args:
            full: True면 카탈로그·분석 시계열 포함. False면 틱 전송용 슬림 페이로드.
        """
        events = self.event_manager.to_dict()
        network = self.road_network.to_dict()
        analytics = self.analytics.to_dict()
        payload: dict[str, Any] = {
            "snapshot": "full" if full else "tick",
            "nodes": network["nodes"],
            "roads": network["roads"],
            "traffic_lights": self.signals.to_dict(),
            "vehicles": [vehicle.to_dict(slim=not full) for vehicle in self.vehicles],
            "bus_stops": self.bus_stops.to_dict(),
            "golden_hour": self.golden_hour.to_dict(),
            "stage": {"id": self.stage_id, "progress": dict(self.stage_progress)},
            "events": events["active"],
            "event_log": events["log"],
            "accidents": self.collisions.to_dict(),
            "weather": events["weather"],
            "time_of_day": events["time_of_day"],
            "analytics": analytics if full else {
                "latest": analytics.get("latest", {}),
                "summary": analytics.get("summary", {}),
            },
            "stats": {
                "sim_time": round(self.sim_time, 1),
                "active_vehicles": len(self.vehicles),
                "total_spawned": self.total_spawned,
                "total_completed": self.total_completed,
                "active_events": len(events["active"]),
                "open_accidents": self.collisions.open_accident_count(),
                "accidents_cleared": self.accidents_cleared_total,
                "bus_stops": len(self.bus_stops.stops),
                "cargo_classified": self.cargo.classified_count,
                "congestion_level": round(self._congestion_level(), 2),
                "road_count": len(self.road_network.roads),
                "node_count": len(self.road_network.nodes),
                "signal_count": len(self.signals.lights),
                "is_paused": self.is_paused,
                "spawn_rate": round(self.spawn_rate, 3),
                "auto_spawn_enabled": self.auto_spawn_enabled,
                "drive_model": "idm+mobil" if self._use_idm and self._use_mobil else "legacy",
                "routing_enabled": self._use_routing,
                "adaptive_signals": self._adaptive_signals,
            },
        }
        if full:
            payload["cargo_catalog"] = self.cargo.catalog()
            payload["event_catalog"] = events["catalog"]
            payload["rescue_catalog"] = events.get("rescue_catalog", [])
        return payload
