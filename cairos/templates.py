"""Deterministic task templates for CAIROS.

The template layer is the fast offline brain of CAIROS.  It handles common shell
and project tasks without AI: creating folders, scaffolding Python/C++ projects,
creating header files, checking git state, cleaning generated caches, and more.

When a task is not recognized here, ``planner.py`` may optionally delegate it to
an AI backend.  Adding templates is the best way to make CAIROS faster and more
reliable while reducing AI usage.
"""

from __future__ import annotations

import re
from pathlib import Path

from .models import CommandStep, Plan, VerificationStep
from .rules import load_rules
from .text import candidate_words, has_all, has_concept, tokenize

PROJECT_NAME_RE = r"[a-zA-Z][a-zA-Z0-9_-]*"
CLASS_NAME_RE = r"[A-Z][a-zA-Z0-9_]*"
PATH_RE = r"[a-zA-Z0-9_./-]+"


def _extract_name(text: str, default: str = "demo") -> str:
    """Extract a likely project/folder/file name from free text."""
    patterns = [
        rf"(?:project|projekt|folder|directory|ordner|repo|repository)\s+({PROJECT_NAME_RE})",
        rf"(?:called|named|namens)\s+({PROJECT_NAME_RE})",
        rf"(?:python|cpp|c\+\+|cmake)\s+(?:project|projekt)\s+({PROJECT_NAME_RE})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    candidates = candidate_words(text)
    return candidates[-1] if candidates else default


def _extract_path_after_keywords(text: str, keywords: list[str], default: str) -> str:
    """Extract a path appearing after one of several marker words."""
    for keyword in keywords:
        match = re.search(rf"\b{re.escape(keyword)}\s+({PATH_RE})", text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    candidates = [word for word in candidate_words(text) if "/" in word or "." in word]
    return candidates[-1] if candidates else default


def _extract_class_name(text: str, default: str = "Demo") -> str:
    """Extract a likely C++ class name from a request."""
    explicit_patterns = [
        rf"(?:class|klasse)\s+({CLASS_NAME_RE})",
        rf"(?:header|file|datei)\s+({CLASS_NAME_RE})",
    ]
    for pattern in explicit_patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            name = match.group(1)
            if name.lower() not in {"cpp", "c", "hpp", "header", "file", "datei", "class", "klasse"}:
                return name[:1].upper() + name[1:]
    candidates = candidate_words(text)
    if candidates:
        name = candidates[-1]
        return name[:1].upper() + name[1:]
    return default


def _header_guard(class_name: str, extension: str) -> str:
    raw = f"{class_name}{extension}".upper()
    return re.sub(r"[^A-Z0-9]", "_", raw)


def _cpp_header_content(class_name: str, namespace: str = "", extension: str = ".hpp") -> str:
    """Generate a C++ class header using ifndef guards."""
    guard = _header_guard(class_name, extension)
    open_namespace = f"namespace {namespace} {{\n\n" if namespace else ""
    close_namespace = f"\n}} // namespace {namespace}\n" if namespace else ""
    return f"""#ifndef {guard}
#define {guard}

{open_namespace}class {class_name} {{
public:
    {class_name}();
    {class_name}(const {class_name}& other);
    {class_name}({class_name}&& other) noexcept;
    {class_name}& operator=(const {class_name}& other);
    {class_name}& operator=({class_name}&& other) noexcept;
    ~{class_name}();

private:
}};{close_namespace}
#endif // {guard}
"""


def _python_project_plan(request: str) -> Plan:
    """Create a modern minimal Python package project."""
    name = _extract_name(request)
    package = name.replace("-", "_")
    request_l = request.lower()
    use_pytest = "pytest" in request_l or has_concept(tokenize(request), "test")
    use_typer = "typer" in request_l
    use_rich = "rich" in request_l
    deps = []
    if use_typer:
        deps.append('"typer>=0.12"')
    if use_rich:
        deps.append('"rich>=13"')
    deps_text = "dependencies = [" + ", ".join(deps) + "]\n" if deps else "dependencies = []\n"
    pyproject = f"""[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "{name}"
version = "0.1.0"
requires-python = ">=3.10"
{deps_text}

[tool.setuptools.packages.find]
where = ["."]
include = ["{package}*"]
"""
    steps = [
        CommandStep(kind="mkdir", path=name, description="Create the project root directory.", changes_files=True),
        CommandStep(kind="mkdir", path=f"{name}/{package}", description="Create the Python package directory.", changes_files=True),
        CommandStep(kind="mkdir", path=f"{name}/tests", description="Create the test directory.", changes_files=True),
        CommandStep(kind="write_file", path=f"{name}/{package}/__init__.py", content='__version__ = "0.1.0"\n', description="Create package initializer.", changes_files=True),
        CommandStep(kind="write_file", path=f"{name}/README.md", content=f"# {name}\n\nGenerated with CAIROS.\n", description="Create README.", changes_files=True),
        CommandStep(kind="write_file", path=f"{name}/.gitignore", content=".venv/\nvenv/\n__pycache__/\n*.pyc\n.pytest_cache/\n*.egg-info/\nbuild/\ndist/\n", description="Create Python .gitignore.", changes_files=True),
        CommandStep(kind="write_file", path=f"{name}/pyproject.toml", content=pyproject, description="Create pyproject.toml.", changes_files=True),
    ]
    if use_pytest:
        steps.append(CommandStep(kind="write_file", path=f"{name}/tests/test_basic.py", content="def test_basic():\n    assert True\n", description="Create a basic pytest test.", changes_files=True))
    if has_concept(tokenize(request), "venv"):
        steps.append(CommandStep(kind="command", command=f"cd {name} && python3 -m venv .venv", description="Create a Python virtual environment.", changes_files=True))
    if has_concept(tokenize(request), "git"):
        steps.append(CommandStep(kind="command", command=f"cd {name} && git init", description="Initialize git repository.", changes_files=True))
    return Plan(
        summary=f"Create a Python project named {name}.",
        steps=steps,
        risk="low",
        notes=["Activate the venv with: source .venv/bin/activate" if has_concept(tokenize(request), "venv") else "No venv requested."],
        verification=[VerificationStep(kind="dir_exists", target=name), VerificationStep(kind="file_exists", target=f"{name}/pyproject.toml")],
        source="template:python-project",
    )


def _cpp_project_plan(request: str) -> Plan:
    """Create a minimal CMake-based C++ project."""
    rules = load_rules()["cpp"]
    name = _extract_name(request)
    include_dir = rules.get("include_dir", "include")
    source_dir = rules.get("source_dir", "src")
    test_dir = rules.get("test_dir", "tests")
    standard = rules.get("standard", "17")
    cmake = f"""cmake_minimum_required(VERSION 3.16)
project({name})

set(CMAKE_CXX_STANDARD {standard})
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable({name} {source_dir}/main.cpp)
target_include_directories({name} PRIVATE {include_dir})
"""
    main_cpp = "#include <iostream>\n\nint main() {\n    std::cout << \"Hello from CAIROS!\" << std::endl;\n    return 0;\n}\n"
    return Plan(
        summary=f"Create a C++ project named {name}.",
        steps=[
            CommandStep(kind="mkdir", path=f"{name}/{include_dir}", description="Create include directory.", changes_files=True),
            CommandStep(kind="mkdir", path=f"{name}/{source_dir}", description="Create source directory.", changes_files=True),
            CommandStep(kind="mkdir", path=f"{name}/{test_dir}", description="Create test directory.", changes_files=True),
            CommandStep(kind="write_file", path=f"{name}/CMakeLists.txt", content=cmake, description="Create CMake configuration.", changes_files=True),
            CommandStep(kind="write_file", path=f"{name}/{source_dir}/main.cpp", content=main_cpp, description="Create main.cpp.", changes_files=True),
            CommandStep(kind="write_file", path=f"{name}/README.md", content=f"# {name}\n\nGenerated with CAIROS.\n", description="Create README.", changes_files=True),
        ],
        risk="low",
        verification=[VerificationStep(kind="dir_exists", target=name), VerificationStep(kind="file_exists", target=f"{name}/CMakeLists.txt")],
        source="template:cpp-project",
    )


def _cpp_header_plan(request: str) -> Plan:
    """Create a C++ header file using project rules."""
    rules = load_rules()["cpp"]
    class_name = _extract_class_name(request)
    include_dir = rules.get("include_dir", "include")
    extension = rules.get("header_extension", ".hpp")
    namespace = rules.get("namespace", "")
    path = _extract_path_after_keywords(request, ["at", "in", "into", "nach", "unter"], f"{include_dir}/{class_name}{extension}")
    if not Path(path).suffix:
        path = str(Path(path) / f"{class_name}{extension}")
    return Plan(
        summary=f"Create C++ header for class {class_name}.",
        steps=[
            CommandStep(kind="mkdir", path=str(Path(path).parent), description="Create header parent directory.", changes_files=True),
            CommandStep(kind="write_file", path=path, content=_cpp_header_content(class_name, namespace, extension), description=f"Write ifndef header guard and class {class_name}.", changes_files=True),
        ],
        risk="low",
        notes=["Header style comes from CAIROS rules: cpp.header_style=ifndef."],
        verification=[VerificationStep(kind="file_exists", target=path)],
        source="template:cpp-header",
    )


def _create_folder_plan(request: str) -> Plan:
    name = _extract_name(request, default="new_folder")
    return Plan(
        summary=f"Create folder {name}.",
        steps=[CommandStep(kind="mkdir", path=name, description=f"Create directory {name}.", changes_files=True)],
        risk="low",
        verification=[VerificationStep(kind="dir_exists", target=name)],
        source="template:folder",
    )


def _create_file_plan(request: str) -> Plan:
    path = _extract_path_after_keywords(request, ["file", "datei", "touch"], "new_file.txt")
    return Plan(
        summary=f"Create empty file {path}.",
        steps=[CommandStep(kind="write_file", path=path, content="", description=f"Create empty file {path}.", changes_files=True)],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target=path)],
        source="template:file",
    )


def _readme_plan(request: str) -> Plan:
    name = _extract_name(request, default=Path.cwd().name)
    return Plan(
        summary="Create or replace README.md.",
        steps=[CommandStep(kind="write_file", path="README.md", content=f"# {name}\n\nGenerated with CAIROS.\n", description="Write a simple README.md.", changes_files=True)],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target="README.md")],
        source="template:readme",
    )


def _gitignore_plan(_: str) -> Plan:
    return Plan(
        summary="Create a useful Python/C++ .gitignore.",
        steps=[CommandStep(kind="write_file", path=".gitignore", content=".venv/\nvenv/\n__pycache__/\n*.pyc\n.pytest_cache/\n*.egg-info/\nbuild/\ndist/\ncmake-build-*/\n.vscode/\n.idea/\n", description="Write .gitignore.", changes_files=True)],
        risk="low",
        verification=[VerificationStep(kind="file_exists", target=".gitignore")],
        source="template:gitignore",
    )


def _git_finish_plan(_: str) -> Plan:
    rules = load_rules()["git"]
    remote = rules.get("remote", "origin")
    main_branch = rules.get("main_branch", "main")
    return Plan(
        summary="Safely inspect current branch before merging or pushing.",
        steps=[
            CommandStep(kind="command", command="git status --short", description="Inspect uncommitted local changes."),
            CommandStep(kind="command", command="git branch --show-current", description="Print the current branch."),
            CommandStep(kind="command", command=f"git fetch {remote}", description="Fetch latest remote refs without merging."),
            CommandStep(kind="command", command=f"git log --oneline --decorate --graph --max-count=12 --all", description="Show recent local and remote commit graph."),
            CommandStep(kind="command", command=f"git log --oneline --left-right --cherry-pick HEAD...{remote}/{main_branch}", description="Compare current HEAD with remote main."),
        ],
        risk="medium",
        notes=[
            "This workflow intentionally does not merge or push automatically.",
            f"Review the comparison with {remote}/{main_branch}. Then explicitly ask CAIROS for merge/rebase/push next step.",
        ],
        source="template:git-safe-workflow",
        requires_confirmation=False,
    )


def _run_tests_plan(_: str) -> Plan:
    if Path("Makefile").exists():
        command = "make test"
    elif Path("pyproject.toml").exists():
        command = "python -m pytest"
    elif Path("CMakeLists.txt").exists():
        command = "cmake --build build && ctest --test-dir build"
    else:
        command = "python -m pytest"
    return Plan(
        summary="Run the detected project test command.",
        steps=[CommandStep(kind="command", command=command, description="Run tests for the current project.")],
        risk="low",
        requires_confirmation=False,
        source="template:test-runner",
    )


def plan_from_template(request: str) -> Plan | None:
    """Return a deterministic plan for a known request, or ``None``."""
    tokens = tokenize(request)
    text = request.lower()

    if has_concept(tokens, "python") and has_concept(tokens, "project") and has_concept(tokens, "make"):
        return _python_project_plan(request)

    if has_concept(tokens, "cpp") and has_concept(tokens, "project") and has_concept(tokens, "make"):
        return _cpp_project_plan(request)

    if has_concept(tokens, "header") and (has_concept(tokens, "cpp") or has_concept(tokens, "class") or "hpp" in text):
        return _cpp_header_plan(request)

    if has_concept(tokens, "venv") and has_concept(tokens, "make"):
        return Plan(
            summary="Create a Python virtual environment in the current directory.",
            steps=[CommandStep(kind="command", command="python3 -m venv .venv", description="Create .venv.", changes_files=True)],
            risk="low",
            notes=["Activate it with: source .venv/bin/activate"],
            verification=[VerificationStep(kind="dir_exists", target=".venv")],
            source="template:venv",
        )

    if has_all(request, "git", "make") and ("init" in tokens or "initialize" in tokens or "initialisiere" in text):
        return Plan(
            summary="Initialize a git repository in the current directory.",
            steps=[CommandStep(kind="command", command="git init", description="Initialize git.", changes_files=True)],
            risk="low",
            source="template:git-init",
        )

    if has_concept(tokens, "folder") and has_concept(tokens, "make"):
        return _create_folder_plan(request)

    if has_concept(tokens, "file") and has_concept(tokens, "make"):
        return _create_file_plan(request)

    if has_concept(tokens, "readme") and has_concept(tokens, "make"):
        return _readme_plan(request)

    if has_concept(tokens, "gitignore") and has_concept(tokens, "make"):
        return _gitignore_plan(request)

    if has_concept(tokens, "large") and "file" in text:
        return Plan(
            summary="Find large files below the current directory.",
            steps=[CommandStep(kind="command", command="find . -type f -size +100M -print", description="List files larger than 100 MB.")],
            risk="low",
            requires_confirmation=False,
            source="template:find-large-files",
        )

    if has_concept(tokens, "clean") and has_concept(tokens, "pycache"):
        return Plan(
            summary="Remove Python bytecode cache folders.",
            steps=[CommandStep(kind="command", command="find . -type d -name __pycache__ -prune -exec rm -rf {} +", description="Delete generated __pycache__ folders only.", changes_files=True, risk="medium")],
            risk="medium",
            notes=["This removes generated Python cache folders only."],
            source="template:clean-pycache",
        )

    if has_concept(tokens, "status") and has_concept(tokens, "git"):
        return Plan(
            summary="Show compact git status.",
            steps=[CommandStep(kind="command", command="git status --short --branch", description="Show branch and working tree status.")],
            risk="low",
            requires_confirmation=False,
            source="template:git-status",
        )

    if has_concept(tokens, "fetch") and has_concept(tokens, "git"):
        return Plan(
            summary="Fetch latest git remote refs.",
            steps=[CommandStep(kind="command", command="git fetch --all --prune", description="Fetch all remotes and prune deleted branches.")],
            risk="low",
            requires_confirmation=False,
            source="template:git-fetch",
        )

    if has_concept(tokens, "test") and ("run" in tokens or "starte" in text or "mach" in text or "mache" in text or "macke" in text):
        return _run_tests_plan(request)

    if (has_concept(tokens, "branch") and has_concept(tokens, "push")) or "origin main" in text or "fertig" in text:
        return _git_finish_plan(request)

    return None
