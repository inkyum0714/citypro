"""Gunicorn 진입점 — Render / 프로덕션 WSGI."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_BACKEND = _ROOT / "backend"
_backend_s = str(_BACKEND)
if _backend_s not in sys.path:
    sys.path.insert(0, _backend_s)

from main import create_app, _start_simulation_thread  # noqa: E402

app = create_app()
_start_simulation_thread()
