from dataclasses import dataclass
from typing import Optional


@dataclass
class CodeChunk:
    file_path: str
    function_name: Optional[str]
    class_name: Optional[str]
    language: str
    start_line: int
    end_line: int
    code: str