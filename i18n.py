"""Small JSON-backed i18n helpers for the main Flask application."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable

from flask import current_app, g, has_app_context


BASE_LANGUAGE = "pt_PT"
BASE_LANGUAGE_TAG = "pt-PT"
SESSION_LANGUAGE_KEY = "APP_LANG"
SUPPORTED_LANGUAGES = ("pt_PT", "en", "fr", "es", "de")

TRANSLATION_FILENAMES = {
    "pt_PT": "pt_PT.json",
    "en": "en.json",
    "fr": "fr.json",
    "es": "es.json",
    "de": "de.json",
}

LANGUAGE_LABELS = {
    "pt_PT": "Português",
    "en": "English",
    "fr": "Français",
    "es": "Español",
    "de": "Deutsch",
}

LANGUAGE_TAGS = {
    "pt_PT": BASE_LANGUAGE_TAG,
    "en": "en",
    "fr": "fr",
    "es": "es",
    "de": "de",
}

_LANGUAGE_ALIASES = {
    "pt": "pt_PT",
    "pt-pt": "pt_PT",
    "pt-pt.utf-8": "pt_PT",
    "pt_pt": "pt_PT",
    "pt_PT": "pt_PT",
    "pt_PT.UTF-8": "pt_PT",
    "en-us": "en",
    "en-gb": "en",
    "fr-fr": "fr",
    "es-es": "es",
    "de-de": "de",
}

_TRANSLATIONS: dict[str, dict[str, Any]] = {}
_TRANSLATIONS_PATH = Path(__file__).resolve().parent / "translations"


def coerce_bool_flag(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return int(value) == 1
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y", "sim", "s", "on"}


def _param_lookup(params: dict[str, Any], key: str) -> tuple[bool, Any]:
    target = str(key or "").strip().upper()
    if not target:
        return False, None
    for param_key, value in (params or {}).items():
        if str(param_key or "").strip().upper() == target:
            return True, value
    return False, None


def normalize_language(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    text = text.split(",", 1)[0].strip()
    if not text:
        return ""
    if text in SUPPORTED_LANGUAGES:
        return text
    lower = text.replace("_", "-").lower()
    if lower in _LANGUAGE_ALIASES:
        return _LANGUAGE_ALIASES[lower]
    short = lower.split("-", 1)[0]
    if short in _LANGUAGE_ALIASES:
        return _LANGUAGE_ALIASES[short]
    return short if short in SUPPORTED_LANGUAGES else ""


def language_tag(language: Any) -> str:
    return LANGUAGE_TAGS.get(normalize_language(language) or BASE_LANGUAGE, BASE_LANGUAGE_TAG)


def load_translations(translations_path: str | os.PathLike[str] | None = None) -> dict[str, dict[str, Any]]:
    """Load all configured JSON catalogs into the process cache."""

    global _TRANSLATIONS_PATH
    if translations_path is not None:
        _TRANSLATIONS_PATH = Path(translations_path)

    loaded: dict[str, dict[str, Any]] = {}
    for language, filename in TRANSLATION_FILENAMES.items():
        path = _TRANSLATIONS_PATH / filename
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            loaded[language] = payload if isinstance(payload, dict) else {}
        except Exception:
            loaded[language] = {}

    _TRANSLATIONS.clear()
    _TRANSLATIONS.update(loaded)
    return _TRANSLATIONS


def reload_translations() -> dict[str, dict[str, Any]]:
    return load_translations(_TRANSLATIONS_PATH)


def configure_i18n(app, translations_path: str | os.PathLike[str] | None = None) -> None:
    env_flag = os.environ.get("USA_MULTILINGUA")
    if "USA_MULTILINGUA" not in app.config:
        app.config["USA_MULTILINGUA"] = 1 if coerce_bool_flag(env_flag) else 0
    app.config.setdefault("DEFAULT_LANGUAGE", normalize_language(os.environ.get("APP_LANGUAGE")) or BASE_LANGUAGE)
    app.config.setdefault("I18N_SESSION_KEY", SESSION_LANGUAGE_KEY)
    load_translations(translations_path or Path(app.root_path) / "translations")


def sync_i18n_config_from_params(app, params: dict[str, Any] | None) -> None:
    params = params or {}
    has_multilingual, multilingual_value = _param_lookup(params, "USA_MULTILINGUA")
    if has_multilingual:
        app.config["USA_MULTILINGUA"] = 1 if coerce_bool_flag(multilingual_value) else 0

    for key in ("APP_LANGUAGE", "APP_DEFAULT_LANGUAGE", "IDIOMA_APP", "LANGUAGE"):
        has_language, language_value = _param_lookup(params, key)
        if not has_language:
            continue
        language = normalize_language(language_value)
        if language:
            app.config["DEFAULT_LANGUAGE"] = language
            break


def i18n_enabled(app=None) -> bool:
    if app is None and has_app_context():
        app = current_app
    if app is None:
        return False
    return coerce_bool_flag(app.config.get("USA_MULTILINGUA", 0))


def extract_user_language(user: Any) -> str:
    for attr in ("LANGUAGE", "PREFERRED_LANGUAGE", "IDIOMA", "LANG", "LOCALE", "PREFERRED_LOCALE"):
        language = normalize_language(getattr(user, attr, None))
        if language:
            return language
    return ""


def resolve_language(
    user_preference: Any = None,
    session_language: Any = None,
    config_language: Any = None,
    *,
    enabled: bool | None = None,
) -> str:
    if enabled is None:
        enabled = i18n_enabled()
    if not enabled:
        return BASE_LANGUAGE

    for candidate in (user_preference, session_language, config_language):
        language = normalize_language(candidate)
        if language:
            return language
    return BASE_LANGUAGE


def _catalog_value(catalog: dict[str, Any], key: str) -> Any:
    if key in catalog:
        return catalog[key]

    value: Any = catalog
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _format_value(value: Any, kwargs: dict[str, Any]) -> str:
    text = value if isinstance(value, str) else str(value)
    if not kwargs:
        return text
    try:
        return text.format(**kwargs)
    except Exception:
        return text


def translate(key: Any, language: Any = None, **kwargs: Any) -> str:
    text_key = str(key or "")
    if not text_key:
        return ""

    if not _TRANSLATIONS:
        load_translations()

    active_language = BASE_LANGUAGE
    if i18n_enabled():
        active_language = normalize_language(language or getattr(g, "language", None)) or BASE_LANGUAGE

    value = _catalog_value(_TRANSLATIONS.get(active_language, {}), text_key)
    if value is None and active_language != BASE_LANGUAGE:
        value = _catalog_value(_TRANSLATIONS.get(BASE_LANGUAGE, {}), text_key)
    if value is None:
        return text_key
    return _format_value(value, kwargs)


def js_translations(keys: Iterable[Any] | None, language: Any = None) -> dict[str, str]:
    result: dict[str, str] = {}
    seen: set[str] = set()
    for raw_key in keys or ():
        key = str(raw_key or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        result[key] = translate(key, language=language)
    return result


def available_languages() -> list[dict[str, str]]:
    return [
        {
            "code": code,
            "tag": language_tag(code),
            "label": LANGUAGE_LABELS.get(code, code),
        }
        for code in SUPPORTED_LANGUAGES
    ]


_ = translate
