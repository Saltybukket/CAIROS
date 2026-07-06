"""Global and project-local rule handling for CAIROS.

Rules let users teach CAIROS how a project should look without requiring an AI
call.  Global rules live in ``~/.config/cairos/rules.json``.  Project rules live
in ``.cairos/rules.json`` and override global defaults.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_RULES: dict[str, Any] = {
    "project": {"type": "auto", "name": ""},
    "python": {
        "layout": "package",
        "use_pyproject": True,
        "test_dir": "tests",
        "default_dependencies": [],
    },
    "cpp": {
        "include_dir": "include",
        "source_dir": "src",
        "test_dir": "tests",
        "header_extension": ".hpp",
        "source_extension": ".cpp",
        "header_style": "ifndef",
        "namespace": "",
        "class_constructors": True,
        "standard": "17",
    },
    "git": {
        "remote": "origin",
        "main_branch": "main",
        "force_push_allowed": False,
        "prefer_rebase": False,
    },
    "ai": {
        "allow_file_content_context": False,
    },
}


def global_rules_path() -> Path:
    """Return the global rules file path."""
    return Path.home() / ".config" / "cairos" / "rules.json"


def local_rules_path() -> Path:
    """Return the project-local rules file path for the current directory."""
    return Path.cwd() / ".cairos" / "rules.json"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(base))
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def load_rules() -> dict[str, Any]:
    """Load merged default, global and project-local rules."""
    rules = _deep_merge(DEFAULT_RULES, _read_json(global_rules_path()))
    return _deep_merge(rules, _read_json(local_rules_path()))


def init_local_rules() -> Path:
    """Create ``.cairos/rules.json`` in the current project if missing."""
    path = local_rules_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(DEFAULT_RULES, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def init_global_rules() -> Path:
    """Create the global rules file if missing."""
    path = global_rules_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(json.dumps(DEFAULT_RULES, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def rules_json() -> str:
    """Return active merged rules as pretty JSON."""
    return json.dumps(load_rules(), indent=2, sort_keys=True)


def _parse_value(raw_value: str) -> Any:
    lowered = raw_value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(raw_value)
    except ValueError:
        return raw_value


def set_rule(key_path: str, raw_value: str, local: bool = True) -> Path:
    """Set a dotted rule in the local or global rules file."""
    path = local_rules_path() if local else global_rules_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _read_json(path)
    keys = key_path.split(".")
    current = data
    for key in keys[:-1]:
        current = current.setdefault(key, {})
    current[keys[-1]] = _parse_value(raw_value)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
