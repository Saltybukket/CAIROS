"""Shell/platform helpers for command templates and user guidance."""

from __future__ import annotations

import re
import shlex
from pathlib import Path

from .config import detect_shell_kind

TRAILING_SENTENCE_PUNCTUATION = ".,;:!?"
UNSAFE_SEARCH_CHARS_RE = re.compile(r"[;&|><`$(){}\n\r]")


def shell_from_request(request: str, default: str | None = None) -> str:
    """Return cmd, powershell, posix or unknown, respecting explicit user hints."""
    text = request.lower()
    if any(phrase in text for phrase in ["windows cmd", "cmd.exe", "cmd shell", "in cmd"]):
        return "cmd"
    if any(phrase in text for phrase in ["powershell", "pwsh"]):
        return "powershell"
    if any(phrase in text for phrase in ["git bash", " wsl", "linux", "bash", "zsh", "fish", "macos", "mac os"]):
        return "posix"
    return default or detect_shell_kind()


def clean_target_name(value: str) -> str:
    """Remove sentence punctuation without stripping meaningful inner dots."""
    cleaned = value.strip().strip("\"'")
    while cleaned and cleaned[-1] in TRAILING_SENTENCE_PUNCTUATION:
        if cleaned[-1] == "." and re.search(r"\.[A-Za-z0-9]+$", cleaned):
            break
        cleaned = cleaned[:-1].rstrip()
    return cleaned


def is_safe_search_name(value: str) -> bool:
    return bool(value) and not UNSAFE_SEARCH_CHARS_RE.search(value)


def quote_for_shell(value: str, shell: str) -> str:
    """Quote a search term/path for the requested shell family."""
    if shell == "cmd":
        return f'"{value}"' if any(ch.isspace() for ch in value) else value
    if shell == "powershell":
        return "'" + value.replace("'", "''") + "'"
    return shlex.quote(value)


def directory_search_command(name: str, shell: str, max_depth: int = 4) -> str:
    """Return a shell-appropriate bounded directory search command."""
    cleaned = clean_target_name(name)
    if shell == "cmd":
        return f"dir /s /b /ad *{cleaned}*"
    if shell == "powershell":
        quoted = quote_for_shell(cleaned, "powershell")
        return (
            f"Get-ChildItem -Path . -Directory -Recurse -Filter {quoted} "
            "-ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName"
        )
    quoted = shlex.quote(f"*{cleaned}*")
    return f"find . -maxdepth {max_depth} -type d -iname {quoted} -print"


def cd_command_for_path(path: str, shell: str) -> str:
    """Return the command a parent shell wrapper/user should run."""
    if shell == "cmd":
        return f'cd /d "{path}"'
    if shell == "powershell":
        return f"Set-Location {quote_for_shell(path, 'powershell')}"
    return f"cd {shlex.quote(path)}"


def path_depth(path: Path, root: Path) -> int:
    try:
        return len(path.relative_to(root).parts)
    except ValueError:
        return 999999
