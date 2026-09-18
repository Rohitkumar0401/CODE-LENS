from pydantic import BaseModel
from typing import List, Optional


class ImportEdge(BaseModel):
    """
    One import relationship: `source_file` imports `target`.
    `resolved_file` is set only if `target` matched an actual file
    in the repository (vs. an external/third-party library).
    """
    source_file: str
    target: str
    resolved_file: Optional[str] = None
    is_external: bool = False


class DependencyGraph(BaseModel):
    file_count: int
    edge_count: int
    edges: List[ImportEdge]
    cycles: List[List[str]]
