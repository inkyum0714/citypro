"""랭킹전 점수·티어 계산. 자유 모드에서는 점수를 올리지 않습니다."""

from __future__ import annotations

from typing import Any

from utils.variables import load_all_variables

PLAY_MODE_RANKED = "ranked"
PLAY_MODE_SANDBOX = "sandbox"
PLAY_MODES = (PLAY_MODE_SANDBOX, PLAY_MODE_RANKED)

DEFAULT_POINTS: dict[str, int] = {
    "trips_completed": 12,
    "accidents_cleared": 20,
    "cargo_classified": 8,
    "bus_boardings": 4,
    "golden_flow_seconds": 1,
    "roads_built": 6,
    "bus_stops_built": 10,
    "buildings_built": 8,
    "crosswalks_built": 7,
    "vehicles_spawned": 1,
    "events_triggered": 2,
    "stages_cleared": 50,
}

DEFAULT_TIERS: list[dict[str, Any]] = [
    {"id": "bronze", "min": 0},
    {"id": "silver", "min": 120},
    {"id": "gold", "min": 350},
    {"id": "platinum", "min": 700},
    {"id": "diamond", "min": 1400},
    {"id": "master", "min": 2800},
]


def ranked_config() -> dict[str, Any]:
    raw = load_all_variables().get("ranked") or {}
    points_raw = raw.get("points") if isinstance(raw.get("points"), dict) else {}
    points = {**DEFAULT_POINTS, **{k: int(v) for k, v in points_raw.items()}}
    tiers = raw.get("tiers") if isinstance(raw.get("tiers"), list) and raw["tiers"] else DEFAULT_TIERS
    return {
        "mode": PLAY_MODE_RANKED,
        "leaderboard_size": int(raw.get("leaderboard_size") or 10),
        "points": points,
        "tiers": list(tiers),
    }


def points_for(metric: str, amount: float) -> int:
    if amount <= 0:
        return 0
    unit = int(ranked_config()["points"].get(metric, 0) or 0)
    if unit <= 0:
        return 0
    return int(float(amount) * unit)


def tier_for(score: int) -> dict[str, Any]:
    tiers = sorted(ranked_config()["tiers"], key=lambda item: int(item.get("min", 0)))
    chosen: dict[str, Any] = tiers[0] if tiers else {"id": "bronze", "min": 0}
    for tier in tiers:
        if int(score) >= int(tier.get("min", 0)):
            chosen = tier
    return {"id": str(chosen.get("id") or "bronze"), "min": int(chosen.get("min", 0))}


def normalize_play_mode(value: Any) -> str:
    mode = str(value or PLAY_MODE_RANKED).strip().lower()
    return mode if mode in PLAY_MODES else PLAY_MODE_RANKED
