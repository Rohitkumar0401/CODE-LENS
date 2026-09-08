import ast
import re
from typing import List
from app.models.chunk import CodeChunk
from app.services.code_parser_service import detect_language


# ---- Python (AST-based, exact boundaries) ----
def chunk_python_file(file_path: str, source: str) -> List[CodeChunk]:
    chunks = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return chunks

    lines = source.splitlines()

    def extract(node, class_name=None):
        start = node.lineno
        end = getattr(node, "end_lineno", start)
        code = "\n".join(lines[start - 1:end])
        chunks.append(CodeChunk(
            file_path=file_path,
            function_name=node.name,
            class_name=class_name,
            language="Python",
            start_line=start,
            end_line=end,
            code=code,
        ))

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            extract(node)
        elif isinstance(node, ast.ClassDef):
            start = node.lineno
            end = getattr(node, "end_lineno", start)
            code = "\n".join(lines[start - 1:end])
            chunks.append(CodeChunk(
                file_path=file_path,
                function_name=None,
                class_name=node.name,
                language="Python",
                start_line=start,
                end_line=end,
                code=code,
            ))
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    extract(child, class_name=node.name)

    return chunks


# ---- C++ / Java / JavaScript (brace-matching) ----
FUNC_PATTERNS = {
    "C++": re.compile(
        r'^\s*[\w:<>\*&\s]+\s+(\w+)\s*\([^;{]*\)\s*(?:const)?\s*\{', re.MULTILINE
    ),
    "Java": re.compile(
        r'^\s*(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\([^;{]*\)\s*\{', re.MULTILINE
    ),
    "JavaScript": re.compile(
        r'(?:function\s+(\w+)\s*\([^)]*\)\s*\{)'
        r'|(?:(\w+)\s*[:=]\s*(?:async\s*)?\([^)]*\)\s*=>\s*\{)'
        r'|(?:(\w+)\s*\([^)]*\)\s*\{)', re.MULTILINE
    ),
}

def _find_matching_brace(source: str, open_brace_idx: int) -> int:
    depth = 0
    for i in range(open_brace_idx, len(source)):
        if source[i] == '{':
            depth += 1
        elif source[i] == '}':
            depth -= 1
            if depth == 0:
                return i
    return -1

def chunk_brace_language(file_path: str, source: str, language: str) -> List[CodeChunk]:
    chunks = []
    pattern = FUNC_PATTERNS.get(language)
    if not pattern:
        return chunks

    for match in pattern.finditer(source):
        name = next((g for g in match.groups() if g), None)
        if not name:
            continue

        open_brace_idx = match.end() - 1
        close_brace_idx = _find_matching_brace(source, open_brace_idx)
        if close_brace_idx == -1:
            continue

        start_line = source[:match.start()].count("\n") + 1
        end_line = source[:close_brace_idx].count("\n") + 1
        code = source[match.start():close_brace_idx + 1]

        chunks.append(CodeChunk(
            file_path=file_path,
            function_name=name,
            class_name=None,
            language=language,
            start_line=start_line,
            end_line=end_line,
            code=code,
        ))

    return chunks


# ---- Dispatcher ----
def chunk_file(file_path: str, source: str, language: str) -> List[CodeChunk]:
    if language == "Python":
        return chunk_python_file(file_path, source)
    elif language in ("C++", "Java", "JavaScript"):
        return chunk_brace_language(file_path, source, language)
    return []


# ---- Repository-wide entrypoint ----
def chunk_repository(file_paths: List[str]) -> List[CodeChunk]:
    """
    Takes the same file_paths list that Day 3 (file_service) / Day 4
    (code_parser_service.parse_repository) already consume.
    Reads each file itself, detects language, and chunks it.
    """
    all_chunks = []
    for path in file_paths:
        language = detect_language(path)
        if language == "Unknown":
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                source = f.read()
        except OSError:
            continue
        all_chunks.extend(chunk_file(path, source, language))
    return all_chunks