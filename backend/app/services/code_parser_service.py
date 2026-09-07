import re
from pathlib import Path
from typing import List, Dict

# ---- Language detection ----
EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".cpp": "C++",
    ".cc": "C++",
    ".cxx": "C++",
    ".hpp": "C++",
    ".h": "C++",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
}

def detect_language(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    return EXTENSION_LANGUAGE_MAP.get(ext, "Unknown")


# ---- Per-language regex patterns ----
PATTERNS = {
    "Python": [
        (r"^\s*def\s+(\w+)\s*\(", "function"),
        (r"^\s*class\s+(\w+)\s*[:\(]", "class"),
    ],
    "JavaScript": [
        (r"function\s+(\w+)\s*\(", "function"),
        (r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>", "function"),
        (r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?function", "function"),
        (r"class\s+(\w+)", "class"),
    ],
    "Java": [
        (r"(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\([^;]*\)\s*\{", "function"),
        (r"(?:public\s+)?(?:abstract\s+)?class\s+(\w+)", "class"),
        (r"interface\s+(\w+)", "interface"),
    ],
    "C++": [
        (r"^[\w:<>\*&\s]+\s+(\w+)\s*\([^;{]*\)\s*\{", "function"),
        (r"class\s+(\w+)", "class"),
        (r"struct\s+(\w+)", "struct"),
    ],
}

# Words that look like functions in regex but aren't (control statements)
CONTROL_KEYWORDS = {"if", "for", "while", "switch", "catch", "return"}


def parse_file(file_path: str) -> List[Dict]:
    """
    Parses a single source file and extracts function/class definitions.
    Returns a list of dicts: {name, type, file, language, line}
    """
    language = detect_language(file_path)
    results = []

    if language == "Unknown":
        return results

    patterns = PATTERNS.get(language, [])
    if not patterns:
        return results

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return results

    for line_number, line in enumerate(lines, start=1):
        for pattern, kind in patterns:
            match = re.search(pattern, line)
            if match:
                name = match.group(1)
                if name in CONTROL_KEYWORDS:
                    continue
                results.append({
                    "name": name,
                    "type": kind,
                    "file": file_path,
                    "language": language,
                    "line": line_number,
                })

    return results


def parse_repository(file_paths: List[str]) -> List[Dict]:
    """
    Runs parse_file across every file discovered by file_service (Day 3).
    """
    structure = []
    for path in file_paths:
        structure.extend(parse_file(path))
    return structure