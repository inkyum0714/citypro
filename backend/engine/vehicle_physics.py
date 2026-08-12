"""차량 질량·위치 기반 충돌(작용-반작용)·회피 물리."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from utils.math_helpers import clamp
from utils.variables import get_variable

if TYPE_CHECKING:
    from engine.vehicle import Vehicle

# 차종별 기본 질량(kg) — vehicle_types 설정이 없을 때 폴백
TYPE_MASS_KG: dict[str, float] = {
    "car": 1000.0,
    "truck": 8000.0,
    "bus": 12000.0,
    "emergency": 1800.0,
}


def mass_for_type(vehicle_type: str) -> float:
    try:
        from engine.vehicle import get_vehicle_types

        spec = get_vehicle_types().get(vehicle_type)
        if spec and spec.get("mass_kg") is not None:
            return float(spec["mass_kg"])
    except Exception:
        pass
    return float(TYPE_MASS_KG.get(vehicle_type, get_variable("vehicle", "mass_kg", 1000.0)))


def vehicle_mass_kg(vehicle: Vehicle | None = None) -> float:
    """차량 질량(kg). 차종별 기본값, 없으면 설정 기본(1톤)."""
    if vehicle is not None:
        if getattr(vehicle, "mass_kg", None):
            return float(vehicle.mass_kg)
        vtype = getattr(vehicle, "vehicle_type", "car")
        return mass_for_type(vtype)
    return float(get_variable("vehicle", "mass_kg", 1000.0))


def vehicle_collision_radius(vehicle: Vehicle) -> float:
    """충돌 판정용 등가 반경 (크기·공간 차지 반영)."""
    scale = float(get_variable("vehicle", "collision_radius_scale", 0.55))
    occupancy = float(getattr(vehicle, "space_occupancy", 1.0) or 1.0)
    base = math.hypot(vehicle.length, vehicle.width) * scale
    return max(4.0, base * math.sqrt(max(0.5, occupancy)))


def max_longitudinal_accel(mass_kg: float) -> float:
    """F=ma → 질량에 따른 최대 가속."""
    base = float(get_variable("physics", "max_acceleration", 12.0))
    ref = float(get_variable("vehicle", "mass_reference_kg", 1000.0))
    return base * (ref / max(mass_kg, 1.0))


def max_longitudinal_brake(mass_kg: float) -> float:
    """마찰 제동 한도."""
    mu = float(get_variable("physics", "friction_coefficient_asphalt_highway", 0.72))
    g_eff = float(get_variable("physics", "gravitational_deceleration_scale", 25.0))
    ref = float(get_variable("vehicle", "mass_reference_kg", 1000.0))
    return mu * g_eff * (ref / max(mass_kg, 1.0))


def apply_mass_to_acceleration(raw_accel: float, mass_kg: float) -> float:
    """IDM 등 가속도를 질량 한도로 클램프."""
    brake = max_longitudinal_brake(mass_kg)
    accel = max_longitudinal_accel(mass_kg)
    return clamp(raw_accel, -brake, accel)


def velocity_components(vehicle: Vehicle) -> tuple[float, float]:
    """위치 진행 방향 속도 벡터 (vx, vy)."""
    vx = getattr(vehicle, "vx", None)
    vy = getattr(vehicle, "vy", None)
    if vx is not None and vy is not None:
        return float(vx), float(vy)
    speed = float(vehicle.current_speed)
    return speed * math.cos(vehicle.angle), speed * math.sin(vehicle.angle)


def sync_speed_from_velocity(vehicle: Vehicle) -> None:
    """vx,vy → current_speed·angle 동기화."""
    vx = float(getattr(vehicle, "vx", 0.0))
    vy = float(getattr(vehicle, "vy", 0.0))
    speed = math.hypot(vx, vy)
    vehicle.current_speed = speed
    if speed > 0.05:
        vehicle.angle = math.atan2(vy, vx)


def sync_velocity_from_speed(vehicle: Vehicle) -> None:
    """current_speed·angle → vx,vy."""
    vehicle.vx = vehicle.current_speed * math.cos(vehicle.angle)
    vehicle.vy = vehicle.current_speed * math.sin(vehicle.angle)


def _closing_speed(ego: Vehicle, other: Vehicle) -> float:
    """other 쪽으로 ego가 접근하는 상대 속도 성분."""
    dx = other.x - ego.x
    dy = other.y - ego.y
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        return max(ego.current_speed, other.current_speed)
    nx, ny = dx / dist, dy / dist
    v1x, v1y = velocity_components(ego)
    v2x, v2y = velocity_components(other)
    return (v1x - v2x) * nx + (v1y - v2y) * ny


def detect_collision_pair(a: Vehicle, b: Vehicle) -> bool:
    """두 차량 충돌 여부."""
    if a.id == b.id or a.finished or b.finished:
        return False
    if getattr(a, "in_accident", False) or getattr(b, "in_accident", False):
        return False
    dist = math.hypot(a.x - b.x, a.y - b.y)
    min_sep = vehicle_collision_radius(a) + vehicle_collision_radius(b)
    if dist >= min_sep:
        return False
    min_rel = float(get_variable("vehicle", "collision_min_closing_speed", 2.0))
    return _closing_speed(a, b) > min_rel or dist < min_sep * 0.65


def resolve_collision_impulse(a: Vehicle, b: Vehicle) -> dict[str, Any]:
    """
    2D 작용-반작용 충돌.

    접촉 법선 방향으로 충격량 J, -J를 질량에 나눠 적용 (Newton 3법칙).
    겹침은 역질량 비율로 분리.

    Returns:
        충격량·속도 변화 요약.
    """
    m1 = max(1.0, vehicle_mass_kg(a))
    m2 = max(1.0, vehicle_mass_kg(b))
    dx = b.x - a.x
    dy = b.y - a.y
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        nx, ny = math.cos(a.angle), math.sin(a.angle)
        dist = 1e-6
    else:
        nx, ny = dx / dist, dy / dist

    v1x, v1y = velocity_components(a)
    v2x, v2y = velocity_components(b)
    # 상대 속도: b 기준 a에 대한 속도 (법선 a→b)
    rvx = v2x - v1x
    rvy = v2y - v1y
    vel_along_n = rvx * nx + rvy * ny

    e = float(get_variable("vehicle", "collision_restitution", 0.25))
    # 이미 멀어지는 중이면 충격 없음 (vel_along_n > 0 = 분리)
    if vel_along_n > 0:
        return {
            "impulse": 0.0,
            "normal": [nx, ny],
            "mass_a": m1,
            "mass_b": m2,
            "velocity_a": [v1x, v1y],
            "velocity_b": [v2x, v2y],
        }

    inv_m1 = 1.0 / m1
    inv_m2 = 1.0 / m2
    # j = -(1+e)(v_rel·n) / (1/m1 + 1/m2)
    denom = inv_m1 + inv_m2
    j = -(1.0 + e) * vel_along_n / denom if denom > 0 else 0.0
    impulse = abs(j)

    # 작용-반작용: a에 -j·n, b에 +j·n (같은 크기 반대 방향)
    a.vx = v1x - j * inv_m1 * nx
    a.vy = v1y - j * inv_m1 * ny
    b.vx = v2x + j * inv_m2 * nx
    b.vy = v2y + j * inv_m2 * ny

    damp = float(get_variable("vehicle", "collision_velocity_damp", 0.35))
    a.vx *= damp
    a.vy *= damp
    b.vx *= damp
    b.vy *= damp
    sync_speed_from_velocity(a)
    sync_speed_from_velocity(b)

    # 위치 분리 (겹침 해소) — 역질량 비례
    r1 = vehicle_collision_radius(a)
    r2 = vehicle_collision_radius(b)
    overlap = (r1 + r2) - dist
    if overlap > 0:
        total_inv = inv_m1 + inv_m2
        sep = overlap / total_inv
        a.x -= nx * sep * inv_m1
        a.y -= ny * sep * inv_m1
        b.x += nx * sep * inv_m2
        b.y += ny * sep * inv_m2

    a.last_impulse = abs(impulse)
    b.last_impulse = abs(impulse)
    a.collision_partner_id = b.id
    b.collision_partner_id = a.id

    return {
        "impulse": abs(impulse),
        "normal": [nx, ny],
        "mass_a": m1,
        "mass_b": m2,
        "velocity_a": [a.vx, a.vy],
        "velocity_b": [b.vx, b.vy],
    }


def avoidance_threats(ego: Vehicle, others: list[Vehicle]) -> list[Vehicle]:
    """회피 대상 후보."""
    radius = float(get_variable("vehicle", "avoidance_scan_radius", 55.0))
    threats: list[Vehicle] = []
    for other in others:
        if other.id == ego.id or other.finished:
            continue
        if getattr(other, "in_accident", False):
            # 사고 차량은 정지 장애물로 회피
            dist = math.hypot(other.x - ego.x, other.y - ego.y)
            if dist <= radius:
                threats.append(other)
            continue
        dist = math.hypot(other.x - ego.x, other.y - ego.y)
        if dist > radius:
            continue
        if _closing_speed(ego, other) <= 0.5:
            continue
        threats.append(other)
    return threats


def avoidance_constraints(
    ego: Vehicle,
    others: list[Vehicle],
    base_gap: float,
    base_lead_speed: float | None,
    base_lead_length: float | None,
) -> tuple[float, float | None, float | None]:
    """다차량 회피: TTC 기반 IDM gap/speed 제한."""
    threats = avoidance_threats(ego, others)
    if not threats:
        return base_gap, base_lead_speed, base_lead_length

    gap = base_gap
    lead_speed = base_lead_speed
    lead_length = base_lead_length
    ttc_limit = float(get_variable("vehicle", "avoidance_ttc_seconds", 2.2))

    for other in threats:
        dist = max(0.5, math.hypot(other.x - ego.x, other.y - ego.y))
        if getattr(other, "in_accident", False):
            closing = max(0.1, ego.current_speed)
        else:
            closing = max(0.1, _closing_speed(ego, other))
        ttc = dist / closing
        desired_gap = closing * ttc_limit + ego.length * 0.5
        if ttc < ttc_limit and desired_gap < gap:
            gap = desired_gap
            lead_speed = 0.0 if getattr(other, "in_accident", False) else other.current_speed * 0.85
            lead_length = other.length
            ego.state = "avoiding"

    return gap, lead_speed, lead_length
