"""퀘스트 진행, 보상, 상점, PRO, 도시 저장."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from engagement.catalog import (
    achievements_catalog,
    daily_quest_templates,
    pro_plan_catalog,
    shop_items,
    xp_for_level,
)
from engagement import profile_store
from engagement.stages import get_stage, stage_catalog, stage_public
from utils.variables import get_variable


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


class EngagementService:
    """로그인 사용자별 재방문·수익화 로직."""

    def __init__(self) -> None:
        self._active_users: dict[str, float] = {}
        self._last_play_tick: dict[str, float] = {}
        self._play_buffer: dict[str, float] = {}
        self._play_flush_at: dict[str, float] = {}
        self._metric_buffer: dict[str, dict[str, float]] = {}
        self._metric_flush_at: dict[str, float] = {}

    def touch(self, login_id: str) -> None:
        import time

        self._active_users[login_id.strip().lower()] = time.time()

    def active_user_ids(self) -> set[str]:
        import time

        now = time.time()
        active_window = float(get_variable("engagement", "active_player_seconds", 90.0))
        return {uid for uid, ts in self._active_users.items() if now - ts <= active_window}

    def is_pro(self, profile: dict[str, Any]) -> bool:
        if profile.get("plan") == "pro":
            until = profile.get("pro_until")
            if until is None:
                return True
            try:
                end = datetime.fromisoformat(str(until).replace("Z", "+00:00"))
                return end > datetime.now(timezone.utc)
            except ValueError:
                return True
        return False

    def max_save_slots(self, profile: dict[str, Any]) -> int:
        base = int(get_variable("engagement", "free_save_slots", 1))
        pro_slots = int(get_variable("engagement", "pro_save_slots", 5))
        extra = int(profile.get("extra_save_slots", 0))
        cap = pro_slots if self.is_pro(profile) else base
        return cap + extra

    def xp_multiplier(self, profile: dict[str, Any]) -> float:
        mult = 1.0
        if self.is_pro(profile):
            mult *= float(get_variable("engagement", "pro_xp_bonus_multiplier", 1.25))
        boosters = profile.get("boosters") or {}
        xp_booster = boosters.get("xp_multiplier")
        if xp_booster:
            try:
                expires = datetime.fromisoformat(str(xp_booster["expires_at"]).replace("Z", "+00:00"))
                if expires > datetime.now(timezone.utc):
                    mult *= float(xp_booster.get("value", 1.0))
            except (KeyError, ValueError, TypeError):
                pass
        return mult

    def on_login(self, login_id: str) -> dict[str, Any]:
        login_id = login_id.strip().lower()
        today = profile_store._today_str()

        def mutate(p: dict[str, Any]) -> None:
            self._ensure_daily(p)
            last = _parse_date(p.get("last_login_date", ""))
            streak = int(p.get("streak_days", 0))
            first_login_today = last != date.today()
            if last is None:
                streak = 1
            elif last == date.today():
                pass
            elif last == date.today() - timedelta(days=1):
                streak += 1
            else:
                streak = 1
            p["streak_days"] = streak
            if first_login_today:
                p["last_login_date"] = today
                bonus = int(get_variable("engagement", "daily_login_coins", 15))
                if self.is_pro(p):
                    bonus *= int(get_variable("engagement", "pro_daily_coin_multiplier", 2))
                p["coins"] = int(p.get("coins", 0)) + bonus
                streak_xp = min(streak, 14) * 5
                self._add_xp(p, streak_xp, apply_multipliers=False)
            self._check_achievements(p)

        profile = profile_store.update_profile(login_id, mutate)
        self.touch(login_id)
        return self.to_public(profile)

    def _ensure_daily(self, profile: dict[str, Any]) -> None:
        daily = profile.setdefault("daily", {})
        today = profile_store._today_str()
        if daily.get("date") == today and daily.get("quests"):
            return
        quests = []
        for tpl in daily_quest_templates():
            quests.append(
                {
                    **tpl,
                    "progress": 0,
                    "completed": False,
                    "claimed": False,
                }
            )
        profile["daily"] = {
            "date": today,
            "quests": quests,
            "all_complete_bonus_claimed": False,
        }

    def _roll_week(self, profile: dict[str, Any]) -> None:
        wid = profile_store._week_id()
        if profile.get("week_id") != wid:
            profile["week_id"] = wid
            profile["weekly_xp"] = 0

    def _add_xp(self, profile: dict[str, Any], amount: int, *, apply_multipliers: bool = True) -> None:
        if amount <= 0:
            return
        # 주간 롤을 먼저 수행해야 가산분이 새 주에 0으로 날아가지 않음
        self._roll_week(profile)
        if apply_multipliers:
            amount = int(amount * self.xp_multiplier(profile))
        profile["xp"] = int(profile.get("xp", 0)) + amount
        profile["weekly_xp"] = int(profile.get("weekly_xp", 0)) + amount
        while profile["xp"] >= xp_for_level(profile["level"]):
            profile["xp"] -= xp_for_level(profile["level"])
            profile["level"] = int(profile.get("level", 1)) + 1
            profile["coins"] = int(profile.get("coins", 0)) + int(
                get_variable("engagement", "level_up_coins", 25)
            )
        profile["leaderboard_score"] = int(profile.get("leaderboard_score", 0)) + amount

    def _quest_progress(self, profile: dict[str, Any], metric: str, delta: float) -> None:
        self._ensure_daily(profile)
        lifetime = profile.setdefault("lifetime", {})
        # 새 메트릭도 lifetime에 자동 누적
        lifetime[metric] = float(lifetime.get(metric, 0) or 0) + delta
        for quest in profile["daily"]["quests"]:
            if quest.get("metric") != metric or quest.get("completed"):
                continue
            quest["progress"] = min(float(quest["target"]), float(quest.get("progress", 0)) + delta)
            if quest["progress"] >= float(quest["target"]):
                quest["completed"] = True

    def record_action(self, login_id: str, action: str, *, amount: float = 1.0) -> dict[str, Any]:
        login_id = login_id.strip().lower()
        metric_map = {
            "add_road": "roads_built",
            "spawn_vehicle": "vehicles_spawned",
            "trigger_event": "events_triggered",
            "add_bus_stop": "bus_stops_built",
            "classify_cargo": "cargo_classified",
            "clear_accident": "accidents_cleared",
        }
        metric = metric_map.get(action)
        if not metric:
            self.touch(login_id)
            return self.get_public(login_id)

        def mutate(p: dict[str, Any]) -> None:
            self._ensure_daily(p)
            self._roll_week(p)
            self._quest_progress(p, metric, amount)
            self._check_achievements(p)

        profile = profile_store.update_profile(login_id, mutate)
        self.touch(login_id)
        return self.to_public(profile)

    def apply_sim_metrics(self, login_id: str, metrics: dict[str, float]) -> dict[str, Any] | None:
        """시뮬 프레임 메트릭을 버퍼에 모았다가 주기적으로 반영합니다."""
        if not login_id or not metrics:
            return None
        import time

        login_id = login_id.strip().lower()
        interesting = {
            k: float(v)
            for k, v in metrics.items()
            if float(v or 0) > 0
            and k
            in (
                "trips_completed",
                "golden_flow_seconds",
                "accidents_cleared",
                "bus_boardings",
                "cargo_classified",
            )
        }
        if not interesting:
            return None

        buf = self._metric_buffer.setdefault(login_id, {})
        for metric, amount in interesting.items():
            buf[metric] = float(buf.get(metric, 0.0)) + amount

        now = time.time()
        # 사고 정리·완주는 즉시, 골든 흐름은 2초 배치
        urgent = any(k in interesting for k in ("trips_completed", "accidents_cleared", "cargo_classified"))
        if not urgent and now < self._metric_flush_at.get(login_id, 0.0):
            return None
        self._metric_flush_at[login_id] = now + 2.0
        to_apply = self._metric_buffer.pop(login_id, {})
        if not to_apply:
            return None

        def mutate(p: dict[str, Any]) -> None:
            self._ensure_daily(p)
            for metric, amount in to_apply.items():
                self._quest_progress(p, metric, amount)
            self._check_achievements(p)

        return self.to_public(profile_store.update_profile(login_id, mutate))

    def list_stages(self, login_id: str) -> list[dict[str, Any]]:
        profile = profile_store.get_profile(login_id)
        done = set(profile.get("stages_completed") or [])
        active = profile.get("active_stage_id")
        out = []
        for stage in stage_catalog():
            pub = stage_public(stage, completed=stage["id"] in done)
            pub["active"] = stage["id"] == active
            out.append(pub)
        return out

    def start_stage(self, login_id: str, stage_id: str) -> tuple[bool, str, dict[str, Any]]:
        stage = get_stage(stage_id)
        if stage is None:
            return False, "스테이지를 찾을 수 없습니다.", self.get_public(login_id)

        def mutate(p: dict[str, Any]) -> None:
            p["active_stage_id"] = stage_id

        profile = profile_store.update_profile(login_id, mutate)
        return True, f"{stage['name']} 시작!", self.to_public(profile)

    def sync_stage_progress(
        self, login_id: str, stage_id: str | None, progress: dict[str, float]
    ) -> dict[str, Any]:
        """현재 스테이지 목표 달성 여부 확인용 공개 정보."""
        if not stage_id:
            return {"active": False}
        stage = get_stage(stage_id)
        if stage is None:
            return {"active": False}
        profile = profile_store.get_profile(login_id)
        done = stage_id in set(profile.get("stages_completed") or [])
        return stage_public(stage, completed=done, progress=progress)

    def claim_stage(self, login_id: str, stage_id: str, progress: dict[str, float]) -> tuple[bool, str, dict[str, Any]]:
        stage = get_stage(stage_id)
        if stage is None:
            return False, "스테이지를 찾을 수 없습니다.", self.get_public(login_id)
        pub = stage_public(stage, progress=progress)
        if not pub.get("all_goals_met"):
            return False, "아직 목표를 모두 달성하지 않았습니다.", self.get_public(login_id)

        def mutate(p: dict[str, Any]) -> None:
            completed = set(p.get("stages_completed") or [])
            if stage_id in completed:
                raise ValueError("already_claimed")
            completed.add(stage_id)
            p["stages_completed"] = list(completed)
            p["active_stage_id"] = None
            p["coins"] = int(p.get("coins", 0)) + int(stage.get("reward_coins", 0))
            self._add_xp(p, int(stage.get("reward_xp", 0)))
            self._quest_progress(p, "stages_cleared", 1)
            self._check_achievements(p)

        try:
            profile = profile_store.update_profile(login_id, mutate)
        except ValueError:
            return False, "이미 클리어한 스테이지입니다.", self.get_public(login_id)
        return True, f"{stage['name']} 클리어! 보상 지급", self.to_public(profile)

    def on_trips_completed(self, count: int, sim_time: float = 0.0) -> None:
        """하위 호환: 활성 유저에게 균등 분배(레거시 공유 시뮬용)."""
        if count <= 0:
            return
        active = list(self.active_user_ids())
        if not active:
            return
        share = count / len(active)
        for login_id in active:
            self.on_trips_completed_for_user(login_id, share)

    def on_trips_completed_for_user(self, login_id: str, count: float) -> None:
        if count <= 0:
            return
        login_id = login_id.strip().lower()

        def mutate(p: dict[str, Any], _count=float(count)) -> None:
            self._ensure_daily(p)
            self._quest_progress(p, "trips_completed", _count)
            self._check_achievements(p)

        profile_store.update_profile(login_id, mutate)

    def tick_playtime(self, sim_dt: float) -> None:
        """플레이타임을 버퍼에 모았다가 주기적으로 디스크에 반영합니다."""
        import time

        now = time.time()
        active_window = float(get_variable("engagement", "active_player_seconds", 90.0))
        flush_interval = 5.0
        for login_id, ts in list(self._active_users.items()):
            if now - ts > active_window:
                continue
            last = self._last_play_tick.get(login_id, 0.0)
            if last <= 0:
                self._last_play_tick[login_id] = now
                self._play_flush_at[login_id] = now + flush_interval
                continue
            elapsed = min(sim_dt, now - last)
            self._last_play_tick[login_id] = now
            self._play_buffer[login_id] = self._play_buffer.get(login_id, 0.0) + elapsed
            if now < self._play_flush_at.get(login_id, 0.0):
                continue
            buffered = self._play_buffer.pop(login_id, 0.0)
            self._play_flush_at[login_id] = now + flush_interval
            if buffered <= 0:
                continue

            def mutate(p: dict[str, Any], _elapsed=buffered) -> None:
                self._ensure_daily(p)
                self._quest_progress(p, "play_seconds", _elapsed)

            profile_store.update_profile(login_id, mutate)

    def _check_achievements(self, profile: dict[str, Any]) -> None:
        unlocked = set(profile.get("achievements") or [])
        for ach in achievements_catalog():
            if ach["id"] in unlocked:
                continue
            metric = ach["metric"]
            if metric == "streak_days":
                val = profile.get("streak_days", 0)
            else:
                val = profile.get("lifetime", {}).get(metric, 0)
            if float(val) >= float(ach["target"]):
                unlocked.add(ach["id"])
                profile["achievements"] = list(unlocked)
                profile["coins"] = int(profile.get("coins", 0)) + int(ach.get("reward_coins", 0))

    def claim_quest(self, login_id: str, quest_id: str) -> tuple[bool, str, dict[str, Any]]:
        login_id = login_id.strip().lower()

        def mutate(p: dict[str, Any]) -> None:
            self._ensure_daily(p)
            quest = next((q for q in p["daily"]["quests"] if q["id"] == quest_id), None)
            if quest is None:
                raise ValueError("unknown_quest")
            if not quest.get("completed"):
                raise ValueError("not_complete")
            if quest.get("claimed"):
                raise ValueError("already_claimed")
            quest["claimed"] = True
            p["coins"] = int(p.get("coins", 0)) + int(quest.get("reward_coins", 0))
            self._add_xp(p, int(quest.get("reward_xp", 0)))

        try:
            profile = profile_store.update_profile(login_id, mutate)
        except ValueError as exc:
            code = str(exc)
            messages = {
                "unknown_quest": "퀘스트를 찾을 수 없습니다.",
                "not_complete": "아직 완료되지 않았습니다.",
                "already_claimed": "이미 보상을 받았습니다.",
            }
            return False, messages.get(code, "실패"), self.get_public(login_id)
        return True, "보상을 받았습니다!", self.to_public(profile)

    def claim_daily_bonus(self, login_id: str) -> tuple[bool, str, dict[str, Any]]:
        login_id = login_id.strip().lower()

        def mutate(p: dict[str, Any]) -> None:
            self._ensure_daily(p)
            quests = p["daily"]["quests"]
            if not quests or not all(q.get("completed") for q in quests):
                raise ValueError("not_all_complete")
            if p["daily"].get("all_complete_bonus_claimed"):
                raise ValueError("already_claimed")
            p["daily"]["all_complete_bonus_claimed"] = True
            bonus = int(get_variable("engagement", "daily_all_complete_coins", 100))
            if self.is_pro(p):
                bonus *= int(get_variable("engagement", "pro_daily_coin_multiplier", 2))
            p["coins"] = int(p.get("coins", 0)) + bonus
            self._add_xp(p, int(get_variable("engagement", "daily_all_complete_xp", 50)))

        try:
            profile = profile_store.update_profile(login_id, mutate)
        except ValueError as exc:
            code = str(exc)
            messages = {
                "not_all_complete": "모든 일일 퀘스트를 완료하세요.",
                "already_claimed": "오늘 보너스는 이미 받았습니다.",
            }
            return False, messages.get(code, "실패"), self.get_public(login_id)
        return True, "일일 완료 보너스!", self.to_public(profile)

    def purchase_shop(self, login_id: str, item_id: str) -> tuple[bool, str, dict[str, Any]]:
        login_id = login_id.strip().lower()
        item = next((i for i in shop_items() if i["id"] == item_id), None)
        if item is None:
            return False, "상품을 찾을 수 없습니다.", self.get_public(login_id)

        def mutate(p: dict[str, Any]) -> None:
            owned = set(p.get("owned_items") or [])
            price = int(item["price_coins"])
            if item["type"] == "cosmetic" and item["cosmetic_id"] in owned:
                raise ValueError("already_owned")
            if p.get("coins", 0) < price:
                raise ValueError("insufficient_coins")
            p["coins"] = int(p["coins"]) - price
            if item["type"] == "booster":
                hours = float(item.get("duration_hours", 1))
                expires = datetime.now(timezone.utc) + timedelta(hours=hours)
                boosters = p.setdefault("boosters", {})
                boosters[item["booster_key"]] = {
                    "value": item["booster_value"],
                    "expires_at": expires.isoformat(),
                }
            elif item["type"] == "cosmetic":
                owned.add(item["cosmetic_id"])
                p["owned_items"] = list(owned)
                p["active_cosmetic"] = item["cosmetic_id"]
            elif item["type"] == "save_slot":
                p["extra_save_slots"] = int(p.get("extra_save_slots", 0)) + int(item.get("slots_added", 1))
            p.setdefault("owned_items", [])
            if item["id"] not in p["owned_items"]:
                p["owned_items"].append(item["id"])

        try:
            profile = profile_store.update_profile(login_id, mutate)
        except ValueError as exc:
            code = str(exc)
            messages = {
                "already_owned": "이미 보유한 스킨입니다.",
                "insufficient_coins": "코인이 부족합니다.",
            }
            return False, messages.get(code, "구매 실패"), self.get_public(login_id)
        return True, f"{item['name']} 구매 완료!", self.to_public(profile)

    def activate_pro_demo(self, login_id: str) -> tuple[bool, str, dict[str, Any]]:
        """데모/베타용 PRO 체험 (실결제 연동 전)."""
        if not bool(get_variable("engagement", "allow_demo_pro_activation", True)):
            return False, "PRO 체험을 사용할 수 없습니다.", self.get_public(login_id)
        days = int(get_variable("engagement", "demo_pro_days", 7))
        login_id = login_id.strip().lower()

        def mutate(p: dict[str, Any]) -> None:
            p["plan"] = "pro"
            p["pro_until"] = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()

        profile = profile_store.update_profile(login_id, mutate)
        return True, f"PRO {days}일 체험이 시작되었습니다.", self.to_public(profile)

    def set_cosmetic(self, login_id: str, cosmetic_id: str) -> dict[str, Any]:
        login_id = login_id.strip().lower()

        def mutate(p: dict[str, Any]) -> None:
            owned = set(p.get("owned_items") or [])
            if cosmetic_id != "default" and cosmetic_id not in owned:
                raise ValueError("not_owned")
            p["active_cosmetic"] = cosmetic_id

        try:
            profile = profile_store.update_profile(login_id, mutate)
        except ValueError:
            return self.get_public(login_id)
        return self.to_public(profile)

    def can_trigger_premium_event(self, profile: dict[str, Any], event_type: str) -> tuple[bool, str]:
        if event_type != "vip_convoy":
            return True, ""
        if self.is_pro(profile):
            return True, ""
        cost = int(get_variable("engagement", "vip_event_coin_cost", 60))
        if int(profile.get("coins", 0)) >= cost:
            return True, "coins"
        return False, "PRO 전용 이벤트입니다. PRO 가입 또는 코인 60 필요."

    def spend_for_vip_event(self, login_id: str) -> None:
        """하위 호환 — try_pay_premium_event 사용 권장."""
        self.try_pay_premium_event(login_id, "vip_convoy")

    def try_pay_premium_event(self, login_id: str, event_type: str) -> tuple[bool, str]:
        """권한 확인과 코인 차감을 한 번의 프로필 갱신으로 원자 처리합니다."""
        if event_type != "vip_convoy":
            return True, ""
        login_id = login_id.strip().lower()
        cost = int(get_variable("engagement", "vip_event_coin_cost", 60))
        result: dict[str, Any] = {"ok": False, "message": ""}

        def mutate(p: dict[str, Any]) -> None:
            if self.is_pro(p):
                result["ok"] = True
                return
            coins = int(p.get("coins", 0))
            if coins < cost:
                result["ok"] = False
                result["message"] = "VIP 호송은 PRO 가입 또는 코인 60으로 이용할 수 있습니다."
                return
            p["coins"] = coins - cost
            result["ok"] = True

        profile_store.update_profile(login_id, mutate)
        return bool(result["ok"]), str(result.get("message") or "")

    def save_city(self, login_id: str, slot: int, name: str, snapshot: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
        login_id = login_id.strip().lower()
        slot = int(slot)

        def mutate(p: dict[str, Any]) -> None:
            saves = p.setdefault("city_saves", {})
            max_slots = self.max_save_slots(p)
            if slot < 0 or slot >= max_slots:
                raise ValueError("invalid_slot")
            saves[str(slot)] = {
                "name": name.strip() or f"도시 {slot + 1}",
                "saved_at": profile_store.iso_now(),
                "snapshot": snapshot,
            }

        try:
            profile = profile_store.update_profile(login_id, mutate)
        except ValueError:
            return False, "저장 슬롯이 없습니다.", self.get_public(login_id)
        return True, "도시가 저장되었습니다.", self.to_public(profile)

    def list_saves(self, login_id: str) -> dict[str, Any]:
        profile = profile_store.get_profile(login_id)
        saves = profile.get("city_saves") or {}
        meta = {
            sid: {"name": s.get("name"), "saved_at": s.get("saved_at")}
            for sid, s in saves.items()
        }
        return {"slots": self.max_save_slots(profile), "saves": meta}

    def get_save_snapshot(self, login_id: str, slot: int) -> dict[str, Any] | None:
        profile = profile_store.get_profile(login_id)
        entry = (profile.get("city_saves") or {}).get(str(int(slot)))
        if not entry:
            return None
        return entry.get("snapshot")

    def get_public(self, login_id: str) -> dict[str, Any]:
        return self.to_public(profile_store.get_profile(login_id))

    def to_public(self, profile: dict[str, Any]) -> dict[str, Any]:
        self._ensure_daily(profile)
        pro = self.is_pro(profile)
        return {
            "login_id": profile.get("login_id"),
            "xp": profile.get("xp", 0),
            "level": profile.get("level", 1),
            "xp_to_next": xp_for_level(int(profile.get("level", 1))),
            "coins": profile.get("coins", 0),
            "streak_days": profile.get("streak_days", 0),
            "plan": "pro" if pro else "free",
            "pro_until": profile.get("pro_until"),
            "is_pro": pro,
            "active_cosmetic": profile.get("active_cosmetic", "default"),
            "owned_items": profile.get("owned_items", []),
            "boosters": profile.get("boosters", {}),
            "daily": profile.get("daily", {}),
            "achievements": profile.get("achievements", []),
            "lifetime": profile.get("lifetime", {}),
            "weekly_xp": profile.get("weekly_xp", 0),
            "save_slots": self.max_save_slots(profile),
            "shop": shop_items(),
            "pro_plan": pro_plan_catalog(),
            "achievement_catalog": achievements_catalog(),
            "show_ads": not pro,
            "stages_completed": profile.get("stages_completed") or [],
            "active_stage_id": profile.get("active_stage_id"),
        }

    def leaderboard(self) -> list[dict[str, Any]]:
        return profile_store.list_leaderboard(
            int(get_variable("engagement", "leaderboard_size", 10))
        )
