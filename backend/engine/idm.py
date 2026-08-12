"""Phase 3: Intelligent Driver Model (IDM) 가속도."""

from __future__ import annotations

import math
from typing import Any

from utils.math_helpers import clamp
from utils.variables import get_variable


def _idm_params() -> dict[str, float]:
    """all_variable.json phase3.idm 파라미터."""
    return {
        "a_max": float(get_variable("phase3", "idm_a_max", 12.0)),
        "b_comfort": float(get_variable("phase3", "idm_b_comfort", 16.0)),
        "delta": float(get_variable("phase3", "idm_delta", 4.0)),
        "time_headway": float(get_variable("phase3", "idm_time_headway", 1.6)),
        "min_gap": float(get_variable("phase3", "idm_min_gap", 10.0)),
    }


def compute_idm_acceleration(
    speed: float,
    desired_speed: float,
    *,
    net_gap: float | None = None,
    lead_speed: float | None = None,
    params: dict[str, float] | None = None,
) -> float:
    """
    IDM 가속도 (Treiber et al.).

    자유류: a = a_max * (1 - (v/v0)^δ)
    추종:   a = a_max * (1 - (v/v0)^δ - (s*/s)²)
    s* = s0 + max(0, v·T + v·Δv / (2√(a_max·b)))

    Args:
        speed: 자차 속도 v.
        desired_speed: 목표 속도 v0.
        net_gap: 앞 범퍼 간격 s. None이면 자유 주행.
        lead_speed: 전방차 속도. net_gap과 쌍으로 사용.
        params: IDM 상수 override.

    Returns:
        가속도 [m/s² 게임 단위].
    """
    cfg = _idm_params()
    if params:
        cfg.update(params)

    a_max = cfg["a_max"]
    b_comfort = max(cfg["b_comfort"], 1e-3)
    delta = cfg["delta"]
    time_headway = cfg["time_headway"]
    s0 = cfg["min_gap"]
    v0 = max(desired_speed, 1.0)
    v = max(speed, 0.0)

    free_term = 1.0 - (v / v0) ** delta

    if net_gap is None or lead_speed is None or net_gap >= 900.0:
        return clamp(a_max * free_term, -b_comfort, a_max)

    s = max(net_gap, 0.5)
    delta_v = v - lead_speed
    s_star = s0 + max(0.0, v * time_headway + (v * delta_v) / (2.0 * math.sqrt(a_max * b_comfort)))
    interaction = (s_star / s) ** 2
    acceleration = a_max * (free_term - interaction)
    return clamp(acceleration, -b_comfort, a_max)


def net_bumper_gap(gap_center_to_center: float, ego_length: float, lead_length: float) -> float:
    """중심/진행 거리 기반 간격을 범퍼 간격으로 변환."""
    return max(0.5, gap_center_to_center - 0.5 * ego_length - 0.5 * lead_length)
