"""
app/routes/routes_query.py

Day 10 — Repository Query API

Exposes:
    POST /query

Request body:
    {
        "repository_id": "abc123",
        "question": "How does authentication work?",
        "top_k": 5                # optional, defaults to 5
    }

Response body:
    {
        "results": [
            {
                "file": "auth.py",
                "function": "login",
                "class": null,
                "language": "Python",
                "start_line": 42,
                "end_line": 68,
                "score": 0.8734
            },
            ...
        ]
    }

Wraps app.services.retrieval_service.search_code, which already does
question -> embedding -> Pinecone query -> shaped matches, all in one
call. This route is intentionally thin: validate input, call the
service, map its output onto the API response shape, handle errors.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

from app.services.retrieval_service import search_code

router = APIRouter()


# ---- Request / Response schemas ----

class QueryRequest(BaseModel):
    repository_id: str = Field(..., min_length=1, description="Repository identifier, e.g. 'owner__repo'")
    question: str = Field(..., min_length=1, description="Natural language question about the codebase")
    top_k: Optional[int] = Field(5, ge=1, le=50, description="Number of chunks to return")


class QueryResultItem(BaseModel):
    file: Optional[str] = None
    function: Optional[str] = None
    class_name: Optional[str] = Field(default=None, alias="class")
    language: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    score: Optional[float] = None

    class Config:
        populate_by_name = True


class QueryResponse(BaseModel):
    results: List[QueryResultItem]


# ---- Route ----

@router.post("/query", response_model=QueryResponse)
def query_repository(payload: QueryRequest):
    """
    Runs a natural language question against a single ingested repository
    and returns the top-k most semantically relevant code chunks.
    """
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    try:
        matches = search_code(
            query=payload.question,
            repository=payload.repository_id,
            top_k=payload.top_k,
        )
    except ValueError as e:
        # search_code raises ValueError for empty query / failed embedding
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

    results = [
        QueryResultItem(
            file=m.get("file_path"),
            function=m.get("function"),
            **{"class": m.get("class")},
            language=m.get("language"),
            start_line=m.get("start_line"),
            end_line=m.get("end_line"),
            score=m.get("score"),
        )
        for m in matches
    ]

    return QueryResponse(results=results)