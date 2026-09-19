import ast
import re
import textwrap
from typing import Dict, List

from app.models.call_graph import CallEdge, CallGraph
from app.services.chunk_service import chunk_repository


def _extract_python_calls(code: str) -> List[str]:
    """
    Parses a single function/method's source (as pulled out by
    chunk_service) and returns the names of everything it calls.
    Handles both bare calls (validate_user()) and attribute calls
    (self.query_database(), db.query_database()) by taking just the
    final attribute name in the second case.
    """
    calls = []
    try:
        source = textwrap.dedent(code)
        tree = ast.parse(source)
    except SyntaxError:
        return calls

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                calls.append(func.id)
            elif isinstance(func, ast.Attribute):
                calls.append(func.attr)
    return calls


_CALL_PATTERN = re.compile(r'\b([A-Za-z_]\w*)\s*\(')

_NOT_A_CALL = {
    "if", "for", "while", "switch", "catch", "return", "new", "sizeof",
    "typedef", "function", "else", "do", "throw", "delete",
}


def _extract_generic_calls(code: str) -> List[str]:
    calls = []
    for match in _CALL_PATTERN.finditer(code):
        name = match.group(1)
        if name in _NOT_A_CALL:
            continue
        calls.append(name)
    return calls


def extract_calls(code: str, language: str) -> List[str]:
    if language == "Python":
        return _extract_python_calls(code)
    elif language in ("C++", "Java", "JavaScript"):
        return _extract_generic_calls(code)
    return []


def _build_function_index(chunks) -> Dict[str, list]:
    """
    Maps a bare function/method name -> every chunk in the repo defined
    with that name (there can be more than one: overloads, methods on
    different classes, functions with the same name in different files).
    """
    index: Dict[str, list] = {}
    for chunk in chunks:
        if chunk.function_name:
            index.setdefault(chunk.function_name, []).append(chunk)
    return index


def build_call_graph(file_paths: List[str]) -> CallGraph:
    """
    Runs chunk_repository to get every function/method in the repo
    with its source code, then for each one extracts what it calls
    and resolves those calls against every other function defined in
    the repo. Calls to things not defined in the repo (print(), len(),
    a third-party library call) are silently skipped -- this builds
    the internal call graph, not a list of every builtin touched.
    """
    chunks = chunk_repository(file_paths)
    function_chunks = [c for c in chunks if c.function_name]
    function_index = _build_function_index(function_chunks)

    edges: List[CallEdge] = []
    seen = set()

    for caller in function_chunks:
        call_names = extract_calls(caller.code, caller.language)

        for name in call_names:
            if name not in function_index:
                continue

            for callee in function_index[name]:
                key = (
                    caller.file_path, caller.function_name, caller.start_line,
                    callee.file_path, callee.function_name, callee.start_line,
                )
                if key in seen:
                    continue
                seen.add(key)

                is_recursive = (
                    caller.file_path == callee.file_path
                    and caller.function_name == callee.function_name
                    and caller.start_line == callee.start_line
                )

                edges.append(CallEdge(
                    caller_function=caller.function_name,
                    caller_file=caller.file_path,
                    caller_class=caller.class_name,
                    caller_start_line=caller.start_line,
                    callee_function=callee.function_name,
                    callee_file=callee.file_path,
                    callee_class=callee.class_name,
                    callee_start_line=callee.start_line,
                    is_recursive=is_recursive,
                ))

    return CallGraph(
        function_count=len(function_chunks),
        edge_count=len(edges),
        edges=edges,
    )
