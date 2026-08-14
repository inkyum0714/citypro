"""차량 엔티티 및 Phase 1 기초 물리(속도·가속·제동 거리) 업데이트."""

from __future__ import annotations

import math
import random
from typing import Any

from engine.idm import compute_idm_acceleration, net_bumper_gap
from engine.vehicle_physics import (
    apply_mass_to_acceleration,
    mass_for_type,
    sync_velocity_from_speed,
)
from utils.math_helpers import clamp, position_on_road, road_length, travel_angle
from utils.variables import get_variable, load_all_variables


def _default_vehicle_types() -> dict[str, dict[str, Any]]:
    return {
        "car": {
            "length": 14,
            "width": 8,
            "height": 4.5,
            "mass_kg": 1000,
            "space_occupancy": 1.0,
            "speed_range": (45, 70),
            "colors": ["#e74c3c", "#3498db", "#2ecc71", "#f1c40f", "#9b59b6", "#ecf0f1"],
            "weight": 0.62,
        },
        "truck": {
            "length": 22,
            "width": 10,
            "height": 10,
            "mass_kg": 8000,
            "space_occupancy": 2.2,
            "speed_range": (28, 42),
            "colors": ["#d35400", "#7f8c8d", "#2c3e50"],
            "weight": 0.18,
        },
        "bus": {
            "length": 26,
            "width": 11,
            "height": 9.5,
            "mass_kg": 12000,
            "space_occupancy": 2.6,
            "speed_range": (24, 36),
            "colors": ["#f39c12", "#16a085"],
            "weight": 0.12,
        },
        "emergency": {
            "length": 16,
            "width": 9,
            "height": 5.5,
            "mass_kg": 1800,
            "space_occupancy": 1.15,
            "speed_range": (55, 80),
            "colors": ["#ffffff"],
            "weight": 0.08,
        },
    }


def get_vehicle_types() -> dict[str, dict[str, Any]]:
    """all_variable.json의 vehicle_types와 기본값을 병합합니다."""
    defaults = _default_vehicle_types()
    configured = load_all_variables().get("vehicle_types") or {}
    if not isinstance(configured, dict):
        configured = {}
    merged: dict[str, dict[str, Any]] = {}
    for key, base in defaults.items():
        override = configured.get(key) if isinstance(configured.get(key), dict) else {}
        spec = {**base, **override}
        speed = spec.get("speed_range", base["speed_range"])
        if isinstance(speed, list):
            spec["speed_range"] = (float(speed[0]), float(speed[1]))
        length = float(spec["length"])
        width = float(spec["width"])
        height = float(spec.get("height", 4.5))
        spec["height"] = height
        spec["volume"] = float(spec.get("volume", length * width * height))
        spec["space_occupancy"] = float(spec.get("space_occupancy", 1.0))
        spec["mass_kg"] = float(spec.get("mass_kg", base.get("mass_kg", 1000)))
        merged[key] = spec
    return merged


# 하위 호환 alias (모듈 로드 시점 스냅샷; 런타임은 get_vehicle_types() 사용)
VEHICLE_TYPES: dict[str, dict[str, Any]] = get_vehicle_types()


def stopping_distance(speed: float, friction_coeff: float | None = None, decel_scale: float | None = None) -> float:
    """
    운동에너지·마찰 기반 제동 거리: d = v² / (2 μ g_eff).

    Args:
        speed: 현재 속도(단위/초).
        friction_coeff: 마찰계수(고속도로 아스팔트 기본값 사용 가능).
        decel_scale: 유효 중력/감속 스케일(g_eff).

    Returns:
        정지까지 필요한 거리.
    """
    mu = friction_coeff if friction_coeff is not None else float(
        get_variable("physics", "friction_coefficient_asphalt_highway", 0.72)
    )
    g_eff = decel_scale if decel_scale is not None else float(
        get_variable("physics", "gravitational_deceleration_scale", 25.0)
    )
    if mu <= 0 or g_eff <= 0:
        return 0.0
    return (speed * speed) / (2.0 * mu * g_eff)


class Vehicle:
    """도로 위 차량: 위치(progress), 속도, 가속도, 최대 속도."""

    def __init__(
        self,
        id: int,
        road: dict[str, Any],
        vehicle_type: str | None = None,
        progress: float = 0.0,
        lane_index: int = 0,
        color: str | None = None,
        speed: float | None = None,
    ) -> None:
        """
        Args:
            id: 차량 ID.
            road: 소속 도로 dict(start/end, speed_limit 등).
            vehicle_type: car/truck/bus/emergency. None이면 가중치 랜덤.
            progress: 도로 진행률 0~1.
            lane_index: 차선 번호(0=우측·느린 차선).
            color: 렌더 색상 hex.
            speed: 초기 속도. None이면 타입별 범위에서 샘플.
        """
        self.id = id
        self.road = road
        self.road_id = road["id"]
        self.vehicle_type = vehicle_type or self._pick_type()
        spec = get_vehicle_types().get(self.vehicle_type) or get_vehicle_types()["car"]

        self.progress = progress
        lanes = max(1, int(road.get("lanes", 1)))
        self.lane_index = int(clamp(float(lane_index), 0.0, float(lanes - 1)))
        self.turn_signal: str | None = None
        self.signal_elapsed = 0.0
        self.lane_change_active = False
        self.lane_change_target_lane: int | None = None
        self.lane_change_from_lane: int | None = None
        self.lane_change_progress = 0.0
        self.lane_change_elapsed = 0.0
        self.length = float(spec["length"])
        self.width = float(spec["width"])
        self.height = float(spec.get("height", 4.5))
        self.volume = float(spec.get("volume", self.length * self.width * self.height))
        self.space_occupancy = float(spec.get("space_occupancy", 1.0))
        self.mass_kg = float(spec.get("mass_kg", mass_for_type(self.vehicle_type)))
        self.in_accident = False
        self.accident_timer = 0.0
        self.collision_partner_id: int | None = None
        self.last_impulse = 0.0
        self.rescue_state: str | None = None  # police | towing | cleared
        self.color = color or random.choice(list(spec["colors"]))
        speed_range = spec["speed_range"]
        if isinstance(speed_range, list):
            speed_range = (float(speed_range[0]), float(speed_range[1]))
        self.base_speed = float(speed if speed is not None else random.uniform(*speed_range))
        self.max_speed = self.base_speed
        self.current_speed = self.base_speed
        self.acceleration = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.travel_forward = True
        self.entry_node_id = int(road.get("start_node_id", 0))
        self.exit_node_id = int(road.get("end_node_id", 0))
        self.destination_node_id: int | None = None
        self.route_steps: list[Any] = []
        self.route_step_index = 0
        self.waiting_at_signal = False
        self.angle = travel_angle(road, True)
        self.x = 0.0
        self.y = 0.0
        self.refresh_world_position()
        sync_velocity_from_speed(self)
        self.finished = False
        self.state = "moving"
        self.wait_timer = 0.0
        self.emergency_flash = self.vehicle_type == "emergency"
        self.cargo_type: str | None = None
        self.cargo_classified = True
        self.bus_dwell_remaining = 0.0
        self.served_stops: set[int] = set()
        if self.vehicle_type == "truck":
            from engine.content_systems import CargoSystem

            CargoSystem.assign_spawn_cargo(self)

    @staticmethod
    def _pick_type() -> str:
        """VEHICLE_TYPES 가중치에 따라 타입을 선택합니다."""
        types_map = get_vehicle_types()
        types = list(types_map.keys())
        weights = [float(types_map[t].get("weight", 1.0)) for t in types]
        return random.choices(types, weights=weights, k=1)[0]

    def refresh_world_position(self) -> None:
        """차선·차선 변경 보간을 반영해 x, y를 갱신합니다."""
        blend = self.lane_change_progress if self.lane_change_active else 1.0
        from_lane = self.lane_index
        target_lane = self.lane_change_target_lane if self.lane_change_active else self.lane_index
        if self.lane_change_active and self.lane_change_from_lane is not None:
            from_lane = self.lane_change_from_lane
        if self.lane_change_active and target_lane is not None:
            self.x, self.y = position_on_road(
                self.road,
                self.progress,
                target_lane,
                lane_blend=blend,
                from_lane_index=from_lane,
                travel_forward=self.travel_forward,
            )
        else:
            self.x, self.y = position_on_road(
                self.road,
                self.progress,
                self.lane_index,
                travel_forward=self.travel_forward,
            )
        self.angle = travel_angle(self.road, self.travel_forward)

    def _max_braking_decel(self) -> float:
        """아스팔트 마찰 한도에서의 최대 제동 감속도."""
        mu = float(get_variable("physics", "friction_coefficient_asphalt_highway", 0.72))
        g_eff = float(get_variable("physics", "gravitational_deceleration_scale", 25.0))
        return mu * g_eff

    def _compute_target_acceleration(
        self,
        dt: float,
        target_speed: float,
        lead_gap: float,
        lead_speed: float | None = None,
        lead_length: float | None = None,
    ) -> float:
        """
        Phase 3: IDM 가속도. 전방차 없으면 자유 IDM.
        """
        use_idm = bool(get_variable("phase3", "use_idm", True))
        if not use_idm:
            return self._compute_legacy_acceleration(dt, target_speed, lead_gap)

        no_lead = lead_gap >= float(get_variable("vehicle", "lead_gap_no_obstacle", 999.0)) - 1.0
        if no_lead or lead_speed is None:
            accel = compute_idm_acceleration(self.current_speed, target_speed)
        else:
            lead_len = lead_length if lead_length is not None else float(
                get_variable("phase3", "idm_default_lead_length", 14.0)
            )
            net_s = net_bumper_gap(lead_gap, self.length, lead_len)
            accel = compute_idm_acceleration(
                self.current_speed,
                target_speed,
                net_gap=net_s,
                lead_speed=lead_speed,
            )

        if accel < -0.5:
            self.state = "braking"
        elif self.waiting_at_signal:
            self.state = "waiting_signal"
        else:
            self.state = "moving"
        return apply_mass_to_acceleration(accel, self.mass_kg)

    def _compute_legacy_acceleration(
        self,
        dt: float,
        target_speed: float,
        lead_gap: float,
    ) -> float:
        """Phase 1 제동 거리 기반 가속 (IDM 비활성 시)."""
        max_accel = float(get_variable("physics", "max_acceleration", 12.0))
        min_gap = float(get_variable("physics", "min_follow_gap", 8.0))
        reaction_factor = float(get_variable("physics", "reaction_time_buffer_factor", 0.15))

        v = self.current_speed
        stop_dist = stopping_distance(v)
        required_clearance = stop_dist + min_gap + self.length * 0.5
        buffer = v * reaction_factor * dt

        if lead_gap < required_clearance + buffer:
            self.state = "braking"
            if lead_gap <= min_gap:
                return apply_mass_to_acceleration(-self._max_braking_decel(), self.mass_kg)
            safe_speed = math.sqrt(
                max(0.0, 2.0 * self._max_braking_decel() * max(0.0, lead_gap - min_gap))
            )
            if v > safe_speed + 0.5:
                return apply_mass_to_acceleration(-self._max_braking_decel(), self.mass_kg)
            raw = clamp((safe_speed - v) / max(dt, 1e-6), -self._max_braking_decel(), max_accel)
            return apply_mass_to_acceleration(raw, self.mass_kg)

        self.state = "moving"
        speed_error = target_speed - v
        raw = clamp(speed_error * 4.0, -self._max_braking_decel(), max_accel)
        return apply_mass_to_acceleration(raw, self.mass_kg)

    def physics_step(
        self,
        dt: float,
        target_speed: float,
        lead_gap: float,
        lead_speed: float | None = None,
        lead_length: float | None = None,
    ) -> None:
        """
        v = v + a·dt 로 속도 갱신 후 progress를 이동합니다.

        Args:
            dt: 시간 간격(초).
            target_speed: 도로 한도·이벤트 반영 목표 속도.
            lead_gap: 전방 차량까지 거리(길이 단위).
            lead_speed: 전방차 속도(IDM).
            lead_length: 전방차 길이(IDM 범퍼 간격).
        """
        if getattr(self, "in_accident", False):
            # 충돌 직후 잔여 속도 감쇠(작용-반작용 후 미끄러짐)
            self.accident_timer += dt
            self.vx = getattr(self, "vx", 0.0) * 0.85
            self.vy = getattr(self, "vy", 0.0) * 0.85
            if math.hypot(self.vx, self.vy) < 0.8 or self.accident_timer > 1.2:
                self.vx = 0.0
                self.vy = 0.0
                self.current_speed = 0.0
            else:
                self.current_speed = math.hypot(self.vx, self.vy)
                self.x += self.vx * dt
                self.y += self.vy * dt
            self.acceleration = 0.0
            self.state = "accident"
            return

        self.acceleration = self._compute_target_acceleration(
            dt,
            target_speed,
            lead_gap,
            lead_speed=lead_speed,
            lead_length=lead_length,
        )
        self.current_speed = clamp(
            self.current_speed + self.acceleration * dt,
            0.0,
            self.max_speed,
        )
        sync_velocity_from_speed(self)

        length = road_length(self.road)
        if length == 0:
            self.finished = True
            return

        progress_delta = (self.current_speed * dt) / length
        self.progress += progress_delta

        if self.progress >= 1.0:
            self.progress = 1.0
            # 도로 끝 도착 모드(기본) 또는 라우팅 비활성 시 즉시 완주 표시
            # (실제 소멸·상태 확정은 TrafficManager._handle_edge_transitions)
            edge_end = bool(get_variable("phase4", "edge_end_is_destination", True))
            use_routing = bool(get_variable("phase4", "use_routing", False))
            if edge_end or not use_routing:
                self.finished = True
                self.state = "arrived"

        self.refresh_world_position()
        sync_velocity_from_speed(self)

    def update_position(
        self,
        dt: float,
        speed_factor: float = 1.0,
        lead_gap: float = 999.0,
        lead_speed: float | None = None,
        lead_length: float | None = None,
    ) -> None:
        """
        시뮬레이션 틱당 위치·속도 업데이트(외부 API).

        Args:
            dt: 시간 간격.
            speed_factor: 이벤트/날씨 등 속도 배율.
            lead_gap: 전방 간격(동일 진행 방향 충돌 회피용).
            lead_speed: IDM 전방차 속도.
            lead_length: IDM 전방차 길이.
        """
        road_limit = float(self.road.get("speed_limit", 50))
        self.max_speed = min(self.base_speed, road_limit)
        target_speed = self.max_speed * speed_factor
        self.physics_step(
            dt,
            target_speed=target_speed,
            lead_gap=lead_gap,
            lead_speed=lead_speed,
            lead_length=lead_length,
        )

    def to_dict(self, *, slim: bool = False) -> dict[str, Any]:
        """프론트엔드/WebSocket 직렬화 dict."""
        payload: dict[str, Any] = {
            "id": self.id,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "speed": round(self.current_speed, 1),
            "color": self.color,
            "type": self.vehicle_type,
            "length": self.length,
            "width": self.width,
            "angle": round(self.angle, 4),
            "road_id": self.road_id,
            "lane_index": self.lane_index,
            "turn_signal": self.turn_signal,
            "state": self.state,
            "mass_kg": round(self.mass_kg, 0),
            "cargo_type": getattr(self, "cargo_type", None),
            "cargo_classified": bool(getattr(self, "cargo_classified", True)),
            "bus_dwell_remaining": round(float(getattr(self, "bus_dwell_remaining", 0.0) or 0.0), 2),
            "in_accident": self.in_accident,
            "rescue_state": self.rescue_state,
            "emergency_flash": self.emergency_flash,
        }
        if slim:
            return payload
        payload.update(
            {
                "progress": round(self.progress, 3),
                "acceleration": round(self.acceleration, 2),
                "base_speed": round(self.base_speed, 1),
                "max_speed": round(self.max_speed, 1),
                "height": round(getattr(self, "height", 0.0), 1),
                "volume": round(getattr(self, "volume", 0.0), 0),
                "space_occupancy": round(getattr(self, "space_occupancy", 1.0), 2),
                "destination_node_id": self.destination_node_id,
                "exit_node_id": self.exit_node_id,
                "travel_forward": self.travel_forward,
                "vx": round(getattr(self, "vx", 0.0), 2),
                "vy": round(getattr(self, "vy", 0.0), 2),
                "collision_partner_id": self.collision_partner_id,
                "last_impulse": round(getattr(self, "last_impulse", 0.0), 1),
                "drive_model": "idm" if get_variable("phase3", "use_idm", True) else "legacy",
            }
        )
        return payload
