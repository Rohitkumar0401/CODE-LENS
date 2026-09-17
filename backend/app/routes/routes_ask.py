"""
app/routes/routes_ask.py

Day 11/12 — /ask endpoint

Thin HTTP wrapper around app.services.rag_service.answer_question, which
owns the actual end-to-end RAG pipeline (Day 12). This route's only job
is: validate the request shape, call the pipeline, translate errors into
HTTP status codes, shape the response.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

from app.services.rag_service import answer_question

router = APIRouter()


class AskRequest(BaseModel):
    repository_id: str = Field(..., min_length=1, description="Repository identifier, e.g. 'owner__repo'")
    question: str = Field(..., min_length=1, description="Natural language question about the codebase")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Number of chunks to retrieve as context")


class SourceItem(BaseModel):
    file: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    function: Optional[str] = None
    class_name: Optional[str] = Field(default=None, alias="class")
    score: Optional[float] = None

    class Config:
        populate_by_name = True


class AskResponse(BaseModel):
    answer: str
    sources: List[SourceItem]
    chunks_used: int


@router.post("/ask", response_model=AskResponse)
def ask_repository(payload: AskRequest):
    """
    Runs the full RAG pipeline (Day 12) for a question against a single
    ingested repository and returns the generated answer plus the
    source locations it was grounded in.
    """
    try:
        result = answer_question(
            question=payload.question,
            repository_id=payload.repository_id,
            top_k=payload.top_k,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG pipeline failed: {e}")

    return AskResponse(
        answer=result["answer"],
        sources=[SourceItem(**s) for s in result["references"]],
        chunks_used=result["chunks_used"],
    )