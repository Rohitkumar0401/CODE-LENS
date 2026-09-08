from pydantic import BaseModel
from typing import Optional

class CodeChunk(BaseModel):
    file_path: str
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    language: str
    start_line: int
    end_line: int
    code: str