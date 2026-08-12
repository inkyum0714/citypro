"""unittest discover? ?? ?????."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_BACKEND = _ROOT / "backend"
for _path in (_ROOT, _BACKEND):
    _s = str(_path)
    if _s not in sys.path:
        sys.path.insert(0, _s)
