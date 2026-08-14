"""사용자별 진행도·재화 JSON 저장."""

from __future__ import annotations

import json
import threading
import time
from copy import deepcopy
from datetime import date, datetime, timezone
from typing import Any

from utils.variables import data_dir

_lock = threading.Lock()
PROGRESS_PATH = data_dir() / "user_progress.json"


def _today_str() -> str:
    return date.today().isoformat()


def _week_id() -> str:
    today = date.today()
    return f"{today.isocalendar().year}-W{today.isocalendar().week:02d}"


def default_profile(login_id: str) -> dict[str, Any]:
    starter_coins = 120
    return {
        "login_id": login_id,
        "xp": 0,
        "level": 1,
        "coins": starter_coins,
        "streak_days": 0,
        "last_login_date": "",
        "plan": "free",
        "pro_until": None,
        "owned_items": [],
        "active_cosmetic": "default",
        "boosters": {},
        "daily": {
            "date": "",
            "quests": [],
            "all_complete_bonus_claimed": False,
        },
        "lifetime": {
            "roads_built": 0,
            "vehicles_spawned": 0,
            "trips_completed": 0,
            "events_triggered": 0,
            "play_seconds": 0.0,
            "golden_flow_seconds": 0.0,
            "accidents_cleared": 0,
            "bus_stops_built": 0,
            "cargo_classified": 0,
            "stages_cleared": 0,
        },
        "stages_completed": [],
        "active_stage_id": None,
        "weekly_xp": 0,
        "week_id": _week_id(),
        "achievements": [],
        "city_saves": {},
        "leaderboard_score": 0,
    }


def _backup_corrupt(raw: str) -> None:
    stamp = int(time.time())
    backup = PROGRESS_PATH.with_name(f"user_progress.corrupt.{stamp}.json")
    try:
        backup.write_text(raw, encoding="utf-8")
    except OSError:
        pass


def _load_all() -> dict[str, Any]:
    if not PROGRESS_PATH.is_file():
        return {"profiles": {}}
    try:
        raw = PROGRESS_PATH.read_text(encoding="utf-8")
    except OSError:
        return {"profiles": {}}
    if not raw.strip():
        return {"profiles": {}}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        _backup_corrupt(raw)
        # 부분 복구 시도: 완전한 프로필 블록만 남기기
        recovered = _try_recover_profiles(raw)
        _save_all(recovered)
        return recovered
    if not isinstance(data, dict):
        return {"profiles": {}}
    data.setdefault("profiles", {})
    return data


def _try_recover_profiles(raw: str) -> dict[str, Any]:
    """잘린 JSON에서 닫힌 프로필 객체만 추출 시도."""
    import re

    profiles: dict[str, Any] = {}
    # "login_id": "..." 를 포함한 객체 블록을 탐욕적으로 스캔
    for match in re.finditer(
        r'\{\s*"login_id"\s*:\s*"([^"]+)"[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',
        raw,
        flags=re.DOTALL,
    ):
        blob = match.group(0)
        try:
            obj = json.loads(blob)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and obj.get("login_id"):
            lid = str(obj["login_id"]).strip().lower()
            if "lifetime" in obj or "coins" in obj:
                profiles[lid] = obj
    return {"profiles": profiles}


def _save_all(data: dict[str, Any]) -> None:
    """원자적 저장: 임시 파일에 쓴 뒤 replace."""
    PROGRESS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = PROGRESS_PATH.with_suffix(".json.tmp")
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    with tmp_path.open("w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
    tmp_path.replace(PROGRESS_PATH)


def get_profile(login_id: str, *, create: bool = True) -> dict[str, Any]:
    login_id = login_id.strip().lower()
    with _lock:
        data = _load_all()
        profiles = data.setdefault("profiles", {})
        if login_id not in profiles:
            if not create:
                return default_profile(login_id)
            profiles[login_id] = default_profile(login_id)
            _save_all(data)
        return deepcopy(profiles[login_id])


def update_profile(login_id: str, mutator) -> dict[str, Any]:
    """mutator(profile) -> None, 저장 후 복사본 반환."""
    login_id = login_id.strip().lower()
    with _lock:
        data = _load_all()
        profiles = data.setdefault("profiles", {})
        profile = profiles.get(login_id)
        if profile is None:
            profile = default_profile(login_id)
            profiles[login_id] = profile
        mutator(profile)
        _save_all(data)
        return deepcopy(profile)


def list_leaderboard(limit: int = 10) -> list[dict[str, Any]]:
    with _lock:
        data = _load_all()
        rows: list[dict[str, Any]] = []
        for login_id, profile in data.get("profiles", {}).items():
            rows.append(
                {
                    "login_id": login_id,
                    "level": profile.get("level", 1),
                    "weekly_xp": profile.get("weekly_xp", 0),
                    "leaderboard_score": profile.get("leaderboard_score", 0),
                    "plan": profile.get("plan", "free"),
                }
            )
        rows.sort(key=lambda r: (r["weekly_xp"], r["leaderboard_score"]), reverse=True)
        return rows[:limit]


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()
