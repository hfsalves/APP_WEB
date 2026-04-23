"""Lightweight detector for untranslated text in critical Jinja templates."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DEFAULT_PATHS = [
    "templates/sz_base.html",
    "templates/login.html",
    "templates/dashboard.html",
    "templates/home.html",
    "templates/dynamic_list.html",
    "templates/dynamic_form.html",
    "templates/profile.html",
]

TEXT_BETWEEN_TAGS_RE = re.compile(r">([^<>{}%][^<>]*[A-Za-zÀ-ÿ][^<>]*)<")
ATTR_RE = re.compile(
    r"\b(?P<attr>aria-label|title|placeholder|alt)\s*=\s*(?P<quote>['\"])(?P<text>.*?[A-Za-zÀ-ÿ].*?)(?P=quote)",
    re.IGNORECASE,
)
SCRIPT_STYLE_RE = re.compile(r"<(script|style)\b.*?</\1>", re.IGNORECASE | re.DOTALL)
JINJA_RE = re.compile(r"({{.*?}}|{%.*?%}|{#.*?#})", re.DOTALL)

IGNORED_TEXTS = {
    "StationZero",
    "Operations Platform",
    "NEW",
    "OK",
}


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _clean(candidate: str) -> str:
    return re.sub(r"\s+", " ", candidate).strip()


def _is_translated_context(candidate: str) -> bool:
    return "_(" in candidate or "i18n_js(" in candidate or "TODO_I18N" in candidate


def scan_file(path: Path) -> list[dict[str, str | int]]:
    source = path.read_text(encoding="utf-8", errors="replace")
    without_scripts = SCRIPT_STYLE_RE.sub("", source)
    findings: list[dict[str, str | int]] = []

    for match in TEXT_BETWEEN_TAGS_RE.finditer(without_scripts):
        raw = match.group(1)
        if _is_translated_context(raw):
            continue
        clean = _clean(JINJA_RE.sub("", raw))
        if not clean or clean in IGNORED_TEXTS:
            continue
        if clean.startswith("&") and clean.endswith(";"):
            continue
        findings.append({
            "file": str(path),
            "line": _line_number(without_scripts, match.start(1)),
            "kind": "text",
            "text": clean,
        })

    for match in ATTR_RE.finditer(without_scripts):
        raw = match.group("text")
        if _is_translated_context(raw):
            continue
        clean = _clean(JINJA_RE.sub("", raw))
        if not clean or clean in IGNORED_TEXTS:
            continue
        if clean.startswith(("/", "#", ".")):
            continue
        findings.append({
            "file": str(path),
            "line": _line_number(without_scripts, match.start("text")),
            "kind": match.group("attr").lower(),
            "text": clean,
        })

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", default=DEFAULT_PATHS)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args()

    root = Path.cwd()
    findings: list[dict[str, str | int]] = []
    for raw_path in args.paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = root / path
        if path.exists() and path.is_file():
            findings.extend(scan_file(path))

    if args.as_json:
        print(json.dumps(findings, ensure_ascii=False, indent=2))
    else:
        for item in findings:
            print(f"{item['file']}:{item['line']}: {item['kind']}: {item['text']}")
        print(f"\n{len(findings)} possible hardcoded text item(s).")

    return 1 if args.fail_on_findings and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
