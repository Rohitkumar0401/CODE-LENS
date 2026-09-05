"""
file_service.py

Discovers relevant source files inside a cloned repository.
Filters out VCS folders, dependency folders, caches, binaries,
and oversized generated files.
"""

import os
from pathlib import Path
from typing import List

# Directories we never want to walk into
IGNORED_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    "venv",
    ".venv",
    "env",
    ".env",
    "dist",
    "build",
    ".next",
    ".idea",
    ".vscode",
    "target",       # java/rust build output
    "bin",
    "obj",
    ".pytest_cache",
    ".mypy_cache",
    "coverage",
    ".terraform",
}

# File extensions we consider "source" / relevant to analysis.
# Extend this list as your ingestion pipeline supports more languages.
RELEVANT_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".java", ".kt", ".go", ".rb", ".php",
    ".c", ".cpp", ".h", ".hpp", ".cs",
    ".rs", ".swift", ".scala",
    ".md", ".txt",
    ".json", ".yaml", ".yml", ".toml",
    ".sql",
    ".html", ".css", ".scss",
}

# Known binary / non-text extensions to explicitly exclude,
# even if somehow not caught above.
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar",
    ".exe", ".dll", ".so", ".dylib",
    ".pyc", ".class", ".jar",
    ".woff", ".woff2", ".ttf", ".eot",
    ".mp4", ".mp3", ".wav", ".avi",
    ".db", ".sqlite", ".sqlite3",
}

# Skip files larger than this (likely generated/lockfiles/data dumps)
MAX_FILE_SIZE_BYTES = 500 * 1024  # 500 KB

# Filenames to always skip regardless of extension
IGNORED_FILENAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
}

# Extensionless filenames that should always be treated as relevant
# (common convention: no file extension, but clearly source/docs)
RELEVANT_FILENAMES_NO_EXT = {
    "README",
    "LICENSE",
    "LICENCE",
    "Dockerfile",
    "Makefile",
    "CHANGELOG",
    "CONTRIBUTING",
    "AUTHORS",
    "NOTICE",
    ".gitignore",
    ".dockerignore",
    ".env.example",
}


def _is_binary_file(file_path: Path, sample_size: int = 1024) -> bool:
    """
    Heuristic binary check: reads a small chunk and looks for null bytes,
    which almost never appear in text files.
    """
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(sample_size)
        return b"\x00" in chunk
    except OSError:
        # Unreadable file — treat as unsafe to include
        return True


def _should_skip_dir(dir_name: str) -> bool:
    return dir_name in IGNORED_DIRS or dir_name.startswith(".")


def _should_skip_file(file_path: Path) -> bool:
    name = file_path.name
    ext = file_path.suffix.lower()

    if name in IGNORED_FILENAMES:
        return True

    if ext in BINARY_EXTENSIONS:
        return True

    # Allow known extensionless files (README, LICENSE, Dockerfile, etc.)
    is_known_no_ext_file = name in RELEVANT_FILENAMES_NO_EXT

    if not is_known_no_ext_file and ext not in RELEVANT_EXTENSIONS:
        return True

    try:
        if file_path.stat().st_size > MAX_FILE_SIZE_BYTES:
            return True
    except OSError:
        return True

    if _is_binary_file(file_path):
        return True

    return False


def get_relevant_files(repo_path: str) -> List[str]:
    """
    Walks the repository at repo_path and returns a list of relevant
    source file paths, relative to the repo root.

    Example:
        get_relevant_files("/tmp/codelens/some-repo")
        -> [
            "src/main.py",
            "src/auth.py",
            "src/models/user.py",
            "README.md",
            "requirements.txt",
        ]
    """
    repo_root = Path(repo_path).resolve()
    if not repo_root.exists() or not repo_root.is_dir():
        raise ValueError(f"Repository path does not exist: {repo_path}")

    relevant_files: List[str] = []

    for current_dir, dir_names, file_names in os.walk(repo_root):
        # Prune ignored directories in-place so os.walk skips them entirely
        dir_names[:] = [d for d in dir_names if not _should_skip_dir(d)]

        for file_name in file_names:
            file_path = Path(current_dir) / file_name

            if _should_skip_file(file_path):
                continue

            relative_path = file_path.relative_to(repo_root)
            relevant_files.append(str(relative_path).replace(os.sep, "/"))

    return sorted(relevant_files)