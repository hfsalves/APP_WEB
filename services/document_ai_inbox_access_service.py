from __future__ import annotations

import json
import os
from typing import Any, Mapping


INBOX_VIEW_DEFINITIONS = (
    {"value": "home", "label": "Receção"},
    {"value": "management", "label": "Controlo de Gestão"},
    {"value": "accounting", "label": "Contabilidade"},
)

DEFAULT_INBOX_VIEW_ACCESS = {
    "ldias": ("home",),
    "msilva": ("management",),
    "arocha": ("management",),
}


def _normalized_login(value: Any) -> str:
    return str(value or "").strip().lower()


def _configured_access(config: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
    raw = (config or {}).get("DOC_AI_INBOX_VIEW_ACCESS") or os.environ.get("DOC_AI_INBOX_VIEW_ACCESS")
    if raw in (None, ""):
        return DEFAULT_INBOX_VIEW_ACCESS
    if isinstance(raw, Mapping):
        return raw
    try:
        parsed = json.loads(str(raw))
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, Mapping) else {}


def allowed_inbox_views(login: Any, config: Mapping[str, Any] | None = None) -> list[dict[str, str]]:
    """Return explicitly authorized Inbox views; unknown users fail closed."""
    normalized_login = _normalized_login(login)
    if not normalized_login:
        return []

    access = _configured_access(config)
    configured_views = access.get(normalized_login, ())
    if isinstance(configured_views, str):
        configured_views = [configured_views]
    allowed_values = {
        str(value or "").strip().lower()
        for value in (configured_views or ())
    }
    return [dict(view) for view in INBOX_VIEW_DEFINITIONS if view["value"] in allowed_values]


def is_inbox_view_allowed(login: Any, view: Any, config: Mapping[str, Any] | None = None) -> bool:
    requested = str(view or "").strip().lower()
    return any(item["value"] == requested for item in allowed_inbox_views(login, config))
