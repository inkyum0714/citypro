import random
import uuid

EVENT_CATALOG = {
    "accident": {
        "label": "교통사고",
        "duration": 28.0,
        "speed_factor": 0.0,
        "spawn_factor": 0.35,
        "severity": "critical",
        "icon": "🚨",
    },
    "construction": {
        "label": "공사 구간",
        "duration": 40.0,
        "speed_factor": 0.35,
        "spawn_factor": 0.7,
        "severity": "warning",
        "icon": "🚧",
    },
    "traffic_jam": {
        "label": "정체",
        "duration": 22.0,
        "speed_factor": 0.2,
        "spawn_factor": 0.5,
        "severity": "warning",
        "icon": "🐌",
    },
    "rush_hour": {
        "label": "출퇴근 러시아워",
        "duration": 35.0,
        "speed_factor": 0.55,
        "spawn_factor": 2.4,
        "severity": "info",
        "icon": "🏙️",
    },
    "rain": {
        "label": "폭우",
        "duration": 30.0,
        "speed_factor": 0.65,
        "spawn_factor": 0.85,
        "severity": "info",
        "icon": "🌧️",
    },
    "fog": {
        "label": "안개",
        "duration": 25.0,
        "speed_factor": 0.5,
        "spawn_factor": 0.75,
        "severity": "info",
        "icon": "🌫️",
    },
    "vip_convoy": {
        "label": "VIP 호송",
        "duration": 18.0,
        "speed_factor": 0.4,
        "spawn_factor": 0.3,
        "severity": "premium",
        "icon": "👑",
    },
    "police_response": {
        "label": "경찰 출동",
        "duration": 8.0,
        "speed_factor": 0.7,
        "spawn_factor": 0.6,
        "severity": "info",
        "icon": "🚓",
        "manual_only": True,
    },
    "tow_truck": {
        "label": "견인차 출동",
        "duration": 10.0,
        "speed_factor": 0.65,
        "spawn_factor": 0.5,
        "severity": "info",
        "icon": "🚛",
        "manual_only": True,
    },
    "fire_response": {
        "label": "119 출동",
        "duration": 10.0,
        "speed_factor": 1.0,
        "spawn_factor": 1.0,
        "severity": "info",
        "icon": "🚒",
        "manual_only": True,
    },
    "ambulance": {
        "label": "병원 구급 출동",
        "duration": 10.0,
        "speed_factor": 1.0,
        "spawn_factor": 1.0,
        "severity": "info",
        "icon": "🚑",
        "manual_only": True,
    },
    "clear_accident": {
        "label": "사고 현장 정리",
        "duration": 4.0,
        "speed_factor": 0.85,
        "spawn_factor": 0.9,
        "severity": "info",
        "icon": "✅",
        "manual_only": True,
    },
}


class SimulationEvent:
    def __init__(self, event_type, road_id=None, progress=0.5, duration=None, message=None):
        catalog = EVENT_CATALOG[event_type]
        self.id = str(uuid.uuid4())[:8]
        self.event_type = event_type
        self.label = catalog["label"]
        self.road_id = road_id
        self.progress = progress
        self.duration = duration if duration is not None else catalog["duration"]
        self.remaining = self.duration
        self.message = message or f"{catalog['label']} 발생"
        self.severity = catalog["severity"]
        self.icon = catalog["icon"]
        self.speed_factor = catalog["speed_factor"]
        self.spawn_factor = catalog["spawn_factor"]

    def tick(self, dt):
        self.remaining = max(0.0, self.remaining - dt)
        return self.remaining > 0

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.event_type,
            "label": self.label,
            "road_id": self.road_id,
            "progress": self.progress,
            "remaining": round(self.remaining, 1),
            "duration": self.duration,
            "message": self.message,
            "severity": self.severity,
            "icon": self.icon,
        }


class EventManager:
    """자동 사건: 1분마다 시도, 설정 확률로 랜덤 도로에 발생."""

    RANDOM_TYPES = ["construction", "fog", "rain", "traffic_jam", "rush_hour"]

    def __init__(self):
        self.events = []
        self.weather = "clear"
        self.time_of_day = "day"
        self._event_timer = 0.0
        self.recent_log = []

    def add_event(self, event_type, road_id=None, progress=None, message=None):
        if event_type not in EVENT_CATALOG:
            return None

        if progress is None:
            progress = random.uniform(0.25, 0.75)

        event = SimulationEvent(event_type, road_id=road_id, progress=progress, message=message)
        self.events.append(event)
        self._apply_global_effects()
        self._push_log(event)
        return event

    def tick(self, dt, roads):
        from utils.variables import get_variable

        interval = float(get_variable("events", "auto_interval_seconds", 60.0))
        chance = float(get_variable("events", "auto_spawn_chance", 0.05))
        self._event_timer += dt
        if self._event_timer >= interval:
            self._event_timer = 0.0
            if roads and random.random() < chance:
                event_type = random.choice(self.RANDOM_TYPES)
                road = random.choice(roads)
                self.add_event(event_type, road_id=road["id"])

        self.events = [event for event in self.events if event.tick(dt)]
        self._apply_global_effects()

    def _apply_global_effects(self):
        active_types = {event.event_type for event in self.events}
        if "rain" in active_types or "fog" in active_types:
            self.weather = "rain" if "rain" in active_types else "fog"
        else:
            self.weather = "clear"

        if "rush_hour" in active_types:
            self.time_of_day = "rush_hour"
        else:
            self.time_of_day = "day"

    def _push_log(self, event):
        entry = {
            "id": event.id,
            "message": event.message,
            "severity": event.severity,
            "icon": event.icon,
        }
        self.recent_log.insert(0, entry)
        self.recent_log = self.recent_log[:8]

    def push_message(self, message: str, *, severity: str = "info", icon: str = "ℹ️") -> None:
        """구조 완료 등 로그 전용 메시지."""
        self.recent_log.insert(
            0,
            {"id": "msg", "message": message, "severity": severity, "icon": icon},
        )
        self.recent_log = self.recent_log[:8]

    def get_speed_factor(self, road_id, progress):
        factor = 1.0
        for event in self.events:
            if event.road_id is None:
                factor = min(factor, event.speed_factor)
                continue
            if event.road_id != road_id:
                continue
            if abs(event.progress - progress) <= 0.18:
                factor = min(factor, event.speed_factor)
        return factor

    def get_spawn_multiplier(self):
        """활성 이벤트의 spawn_factor를 곱해 스폰 배율을 계산합니다.

        사고(0.35)·정체(0.5)처럼 1 미만은 감소, 러시아워(2.4)는 증가.
        max()만 쓰면 감소 이벤트가 무시되므로 곱셈을 사용합니다.
        """
        multiplier = 1.0
        for event in self.events:
            multiplier *= float(event.spawn_factor)
        return max(0.05, multiplier)

    def clear(self):
        self.events.clear()
        self.weather = "clear"
        self.time_of_day = "day"

    def to_dict(self):
        return {
            "active": [event.to_dict() for event in self.events],
            "weather": self.weather,
            "time_of_day": self.time_of_day,
            "log": self.recent_log,
            "catalog": [
                {
                    "type": key,
                    **{k: value for k, value in spec.items() if k not in ("duration", "manual_only")},
                    "manual_only": bool(spec.get("manual_only", False)),
                }
                for key, spec in EVENT_CATALOG.items()
                if not spec.get("manual_only")
            ],
            "rescue_catalog": [
                {
                    "type": key,
                    **{k: value for k, value in spec.items() if k not in ("duration", "manual_only")},
                }
                for key, spec in EVENT_CATALOG.items()
                if spec.get("manual_only")
            ],
        }
