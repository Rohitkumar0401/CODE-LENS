import ast
import os
import re
from typing import Dict, List, Optional, Set

from app.models.dependency import ImportEdge, DependencyGraph
from app.services.code_parser_service import detect_language


# ---------- Raw import extraction (per language) ----------

def _extract_python_imports(source: str) -> List[str]:
    """
    Returns dotted module names imported by this file, e.g.
    'app.services.auth_service', 'os', 'app.models.chunk'.
    Both `import x.y` and `from x.y import z` are captured as 'x.y'.
    """
    imports = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


_JS_IMPORT_PATTERN = re.compile(
    r'''(?:require\(['"](.+?)['"]\))|(?:from\s+['"](.+?)['"])''',
)

_JAVA_IMPORT_PATTERN = re.compile(r'^\s*import\s+(?:static\s+)?([\w.]+)\s*;', re.MULTILINE)

_CPP_INCLUDE_PATTERN = re.compile(r'^\s*#include\s*["<](.+?)[">]', re.MULTILINE)


def _extract_js_imports(source: str) -> List[str]:
    imports = []
    for match in _JS_IMPORT_PATTERN.finditer(source):
        target = match.group(1) or match.group(2)
        if target:
            imports.append(target)
    return imports


def _extract_java_imports(source: str) -> List[str]:
    return _JAVA_IMPORT_PATTERN.findall(source)


def _extract_cpp_includes(source: str) -> List[str]:
    return _CPP_INCLUDE_PATTERN.findall(source)


def extract_raw_imports(source: str, language: str) -> List[str]:
    if language == "Python":
        return _extract_python_imports(source)
    elif language == "JavaScript":
        return _extract_js_imports(source)
    elif language == "Java":
        return _extract_java_imports(source)
    elif language == "C++":
        return _extract_cpp_includes(source)
    return []


# ---------- Resolving raw imports to real files in the repo ----------

def _build_module_index(file_paths: List[str]) -> Dict[str, str]:
    """
    Maps possible lookup keys -> actual file path, so a raw import like
    'app.services.auth_service' or 'auth_service' or './auth_service'
    can be matched against a real file in the repo.
    """
    index: Dict[str, str] = {}
    for path in file_paths:
        norm = path.replace("\\", "/")
        no_ext, _ = os.path.splitext(norm)

        # Full dotted path from repo root, e.g. app.services.auth_service
        dotted = no_ext.replace("/", ".")
        index[dotted] = path

        # Just the filename without extension, e.g. auth_service
        base = os.path.basename(no_ext)
        # Don't overwrite an existing more-specific match
        index.setdefault(base, path)

        # Full relative path without extension, e.g. app/services/auth_service
        index.setdefault(no_ext, path)

    return index


def _resolve_import(raw_import: str, module_index: Dict[str, str]) -> Optional[str]:
    candidate = raw_import.replace("\\", "/")
    candidate = candidate.lstrip("./")
    no_ext, _ = os.path.splitext(candidate)

    for key in (raw_import, candidate, no_ext, os.path.basename(no_ext)):
        if key in module_index:
            return module_index[key]
    return None


# ---------- Cycle detection ----------

def _find_cycles(adjacency: Dict[str, Set[str]]) -> List[List[str]]:
    """
    DFS-based cycle detection over the resolved-file dependency graph.
    Returns each cycle as a list of file paths, e.g.
    ['a.py', 'b.py', 'a.py'].
    """
    cycles: List[List[str]] = []
    visited: Set[str] = set()
    stack: List[str] = []
    on_stack: Set[str] = set()

    def dfs(node: str):
        visited.add(node)
        stack.append(node)
        on_stack.add(node)

        for neighbor in adjacency.get(node, ()):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in on_stack:
                cycle_start = stack.index(neighbor)
                cycles.append(stack[cycle_start:] + [neighbor])

        stack.pop()
        on_stack.discard(node)

    for node in adjacency:
        if node not in visited:
            dfs(node)

    return cycles


# ---------- Repository-wide entrypoint ----------

def analyze_dependencies(file_paths: List[str]) -> DependencyGraph:
    """
    Reads every file, extracts its imports, resolves what it can to
    other files in the same repo, and returns the full edge list plus
    any circular-dependency chains found.

    External/third-party imports (e.g. 'os', 'fastapi', '<vector>')
    are still included as edges, but with resolved_file=None and
    is_external=True, so callers can filter them out if they only
    want the internal dependency graph.
    """
    module_index = _build_module_index(file_paths)
    edges: List[ImportEdge] = []
    adjacency: Dict[str, Set[str]] = {}

    for path in file_paths:
        language = detect_language(path)
        if language == "Unknown":
            continue

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                source = f.read()
        except OSError:
            continue

        raw_imports = extract_raw_imports(source, language)
        adjacency.setdefault(path, set())

        for raw in raw_imports:
            resolved = _resolve_import(raw, module_index)
            if resolved == path:
                continue

            edges.append(ImportEdge(
                source_file=path,
                target=raw,
                resolved_file=resolved,
                is_external=resolved is None,
            ))

            if resolved:
                adjacency[path].add(resolved)

    cycles = _find_cycles(adjacency)

    return DependencyGraph(
        file_count=len(file_paths),
        edge_count=len(edges),
        edges=edges,
        cycles=cycles,
    )


def _build_module_index(file_paths: List[str]) -> Dict[str, str]:
    """
    Maps possible lookup keys -> actual file path. Stores every dotted
    AND slash-separated suffix of each path (not just the full path),
    so an import like 'app.services.auth_service' resolves correctly
    regardless of what repo-clone prefix sits in front of it on disk.
    """
    index: Dict[str, str] = {}
    for path in file_paths:
        norm = path.replace("\\", "/")
        no_ext, _ = os.path.splitext(norm)
        segments = [s for s in no_ext.split("/") if s]

        for i in range(len(segments)):
            suffix_dotted = ".".join(segments[i:])
            index.setdefault(suffix_dotted, path)

            suffix_path = "/".join(segments[i:])
            index.setdefault(suffix_path, path)

    return index


def _resolve_import(raw_import: str, module_index: Dict[str, str]) -> Optional[str]:
    candidate = raw_import.replace("\\", "/")
    candidate = candidate.lstrip("./")
    no_ext, _ = os.path.splitext(candidate)

    for key in (raw_import, candidate, no_ext, os.path.basename(no_ext)):
        if key in module_index:
            return module_index[key]
    return None


def _find_cycles(adjacency: Dict[str, Set[str]]) -> List[List[str]]:
    cycles: List[List[str]] = []
    visited: Set[str] = set()
    stack: List[str] = []
    on_stack: Set[str] = set()

    def dfs(node: str):
        visited.add(node)
        stack.append(node)
        on_stack.add(node)

        for neighbor in adjacency.get(node, ()):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in on_stack:
                cycle_start = stack.index(neighbor)
                cycles.append(stack[cycle_start:] + [neighbor])

        stack.pop()
        on_stack.discard(node)

    for node in adjacency:
        if node not in visited:
            dfs(node)

    return cycles


def analyze_dependencies(file_paths: List[str]) -> DependencyGraph:
    module_index = _build_module_index(file_paths)
    edges: List[ImportEdge] = []
    adjacency: Dict[str, Set[str]] = {}

    for path in file_paths:
        language = detect_language(path)
        if language == "Unknown":
            continue

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                source = f.read()
        except OSError:
            continue

        raw_imports = extract_raw_imports(source, language)
        adjacency.setdefault(path, set())

        for raw in raw_imports:
            resolved = _resolve_import(raw, module_index)
            if resolved == path:
                continue

            edges.append(ImportEdge(
                source_file=path,
                target=raw,
                resolved_file=resolved,
                is_external=resolved is None,
            ))

            if resolved:
                adjacency[path].add(resolved)

    cycles = _find_cycles(adjacency)

    return DependencyGraph(
        file_count=len(file_paths),
        edge_count=len(edges),
        edges=edges,
        cycles=cycles,
    )
