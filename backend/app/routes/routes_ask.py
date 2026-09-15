"""
app/routes/routes_ask.py

Day 11 — /ask endpoint

Full RAG pipeline as a single API call:
    Question -> search_code (Day 9) -> generate_answer (Day 11) -> response

Distinct from /query (Day 10), which returns raw retrieved chunks with
no LLM involved. /ask returns a synthesized natural-language answer
plus the sources it was grounded in, so the caller can verify the
answer against real code locations.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

from app.services.retrieval_service import search_code
from app.services.llm_service import generate_answer

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


class AskResponse(BaseModel):
    answer: str
    sources: List[SourceItem]


@router.post("/ask", response_model=AskResponse)
def ask_repository(payload: AskRequest):
    """
    Retrieves relevant code chunks for the question, then asks the LLM
    to answer grounded strictly in those chunks. Returns both the
    generated answer and the source locations it was based on.
    """
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty.")

    try:
        chunks = search_code(
            query=payload.question,
            repository=payload.repository_id,
            top_k=payload.top_k,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {e}")

    try:
        answer = generate_answer(question=payload.question, chunks=chunks)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {e}")

    sources = [
        SourceItem(
            file=c.get("file_path"),
            start_line=c.get("start_line"),
            end_line=c.get("end_line"),
            function=c.get("function"),
        )
        for c in chunks
    ]

    return AskResponse(answer=answer, sources=sources)