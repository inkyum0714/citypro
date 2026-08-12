"""로그인 시 참여 시스템 연동."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engagement.service import EngagementService

_service: EngagementService | None = None


def bind_engagement(service: EngagementService) -> None:
    global _service
    _service = service


def on_user_login(login_id: str) -> dict[str, Any] | None:
    if _service is None or not login_id:
        return None
    return _service.on_login(login_id)
