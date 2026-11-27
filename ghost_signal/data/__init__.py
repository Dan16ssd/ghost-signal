"""Translations written once at build time and saved as JSON, so the app needs no AI for them.

Layout:
  call_scripts.json     {"ru": {"intro": ..., "press": ..., "thanks": ..., "retry": ..., "_review": ...}}
  messages/<lang>.json  {"_review": ..., "help": ..., ...}

Keys starting with "_" are notes and are skipped. A missing or broken file is logged and
skipped, so the app still starts. Callers merge the result without overwriting hand-written
entries (see `merge_missing`).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent
SCRIPT_KEYS = {"intro", "press", "thanks", "retry"}


def _clean(entries: object, where: str) -> dict[str, str] | None:
    """Drop `_` notes; None when the entry is not a flat object of strings."""
    if not isinstance(entries, dict):
        log.error("offline language data: %s is not an object, skipped", where)
        return None
    clean = {}
    for key, value in entries.items():
        if key.startswith("_"):
            continue
        if not isinstance(value, str):
            log.error("offline language data: %s key %r is not text, skipped", where, key)
            return None
        clean[key] = value
    return clean


def _read(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as e:
        log.error("offline language data: cannot read %s: %s", path.name, e)
        return None


def load_call_scripts() -> dict[str, dict[str, str]]:
    """{language: {intro, press, thanks, retry}} from call_scripts.json."""
    raw = _read(DATA_DIR / "call_scripts.json")
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        log.error("offline language data: call_scripts.json is not an object, skipped")
        return {}
    scripts = {}
    for lang, entries in raw.items():
        clean = _clean(entries, f"call_scripts.json[{lang}]")
        if clean is None:
            continue
        missing = SCRIPT_KEYS - clean.keys()
        if missing:
            log.error("offline language data: call_scripts.json[%s] misses %s, skipped", lang, sorted(missing))
            continue
        scripts[lang] = clean
    return scripts


def load_messages() -> dict[str, dict[str, str]]:
    """{language: {key: text}} from messages/<language>.json."""
    folder = DATA_DIR / "messages"
    if not folder.is_dir():
        return {}
    messages = {}
    for path in sorted(folder.glob("*.json")):
        clean = _clean(_read(path), f"messages/{path.name}")
        if clean is not None:
            messages[path.stem] = clean
    return messages


def merge_missing(target: dict[str, dict[str, str]], loaded: dict[str, dict[str, str]]) -> None:
    """Add loaded languages and keys to `target` without overwriting anything already there."""
    for lang, entries in loaded.items():
        have = target.setdefault(lang, {})
        for key, text in entries.items():
            have.setdefault(key, text)
