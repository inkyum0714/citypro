"""사용자 JSON 저장소 (login_id, name, password)."""

from __future__ import annotations

import json
import threading
from typing import Any

from werkzeug.security import check_password_hash, generate_password_hash

from utils.variables import data_dir

USERS_PATH = data_dir() / "users.json"
_lock = threading.Lock()


def _load_raw() -> dict[str, Any]:
    if not USERS_PATH.is_file():
        return {"users": {}}
    try:
        with USERS_PATH.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {"users": {}}
    if not isinstance(data, dict):
        return {"users": {}}
    data.setdefault("users", {})
    return data


def _save_raw(data: dict[str, Any]) -> None:
    """원자적 저장: 임시 파일에 쓴 뒤 replace."""
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = USERS_PATH.with_suffix(".json.tmp")
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    with tmp_path.open("w", encoding="utf-8") as handle:
        handle.write(payload)
        handle.flush()
    tmp_path.replace(USERS_PATH)


def list_users_public() -> dict[str, Any]:
    """비밀번호 제외 사용자 요약."""
    data = _load_raw()
    out: dict[str, Any] = {}
    for login_id, user in data.get("users", {}).items():
        out[login_id] = {
            "login_id": user.get("login_id", login_id),
            "name": user.get("name", ""),
            "auth_provider": user.get("auth_provider", "local"),
        }
    return out


def get_user(login_id: str) -> dict[str, Any] | None:
    return _load_raw().get("users", {}).get(login_id)


def get_user_by_google_sub(google_sub: str) -> dict[str, Any] | None:
    if not google_sub:
        return None
    for user in _load_raw().get("users", {}).values():
        if user.get("google_sub") == google_sub:
            return user
    return None


def create_local_user(login_id: str, name: str, password: str) -> tuple[bool, str]:
    """
    로컬 회원가입.

    Returns:
        (성공 여부, 메시지)
    """
    from utils.i18n import t

    login_id = login_id.strip().lower()
    if not login_id or len(login_id) < 3:
        return False, t("auth.id_min")
    if not name.strip():
        return False, t("auth.name_required")
    if len(password) < 8:
        return False, t("auth.password_min")

    with _lock:
        data = _load_raw()
        users = data.setdefault("users", {})
        if login_id in users:
            return False, t("auth.id_taken")
        users[login_id] = {
            "login_id": login_id,
            "name": name.strip(),
            "password": generate_password_hash(password),
            "auth_provider": "local",
        }
        _save_raw(data)
    return True, t("auth.register_ok")


def verify_local_user(login_id: str, password: str) -> dict[str, Any] | None:
    user = get_user(login_id.strip().lower())
    if user is None or user.get("auth_provider", "local") != "local":
        return None
    if not check_password_hash(user.get("password", ""), password):
        return None
    return user


def upsert_google_user(preferred_login_id: str, name: str, google_sub: str) -> dict[str, Any]:
    """Google OAuth 사용자 생성/갱신.

    기존 로컬 계정의 login_id와 충돌하면 google_ 접두 또는 sub 기반 ID를 사용하고,
    이미 google_sub로 연결된 계정이 있으면 그 레코드를 갱신합니다.
    """
    preferred_login_id = preferred_login_id.strip().lower()
    with _lock:
        data = _load_raw()
        users = data.setdefault("users", {})

        existing_by_sub = None
        for uid, user in users.items():
            if user.get("google_sub") == google_sub:
                existing_by_sub = uid
                break

        if existing_by_sub is not None:
            user = users[existing_by_sub]
            user["name"] = name
            user["auth_provider"] = "google"
            user["google_sub"] = google_sub
            _save_raw(data)
            return user

        login_id = preferred_login_id
        conflict = users.get(login_id)
        if conflict is not None and conflict.get("auth_provider", "local") != "google":
            # 로컬 계정 덮어쓰기 방지
            suffix = (google_sub or "user")[-8:]
            login_id = f"g_{preferred_login_id}_{suffix}".lower()
            n = 1
            while login_id in users:
                login_id = f"g_{preferred_login_id}_{suffix}_{n}".lower()
                n += 1

        users[login_id] = {
            "login_id": login_id,
            "name": name,
            "password": "",
            "auth_provider": "google",
            "google_sub": google_sub,
        }
        _save_raw(data)
        return users[login_id]
