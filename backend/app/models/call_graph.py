from pydantic import BaseModel
from typing import List, Optional


class CallEdge(BaseModel):
    caller_function: str
    caller_file: str
    caller_class: Optional[str] = None
    caller_start_line: int

    callee_function: str
    callee_file: str
    callee_class: Optional[str] = None
    callee_start_line: int

    is_recursive: bool = False


class CallGraph(BaseModel):
    function_count: int
    edge_count: int
    edges: List[CallEdge]
