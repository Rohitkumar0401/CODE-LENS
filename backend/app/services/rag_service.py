"""
app/services/rag_service.py

Day 12 — Proper RAG Pipeline
Day 13 — File + Line References

Combines everything built on Days 9–11 into a single orchestrated flow:

    Question
       |
       v
    Query Embedding        (embedding_service.generate_embedding,
       |                     called internally by search_code)
       v
    Vector Search           (retrieval_service.search_code)
       |
       v
    Top K Chunks
       |
       v
    Context Construction    (llm_service.build_prompt)
       |
       v
    Prompt
       |
       v
    LLM                     (llm_service.generate_answer)
       |
       v
    Answer + References

This is the single entrypoint the API layer (routes_ask.py) should call.
Routes stay thin; all pipeline logic and error handling for "what does
answering a question actually involve" lives here, in one place, so it
can be reused (CLI tool, background job, tests) without going through
FastAPI at all.
"""

from typing import Dict, List

from app.services.retrieval_service import search_code
from app.services.llm_service import generate_answer


def _shape_references(chunks: List[Dict]) -> List[Dict]:
    """
    Turns raw retrieved chunk dicts into citation objects for the API
    response, e.g.:

        {
            "file": "backend/services/auth.py",
            "start_line": 24,
            "end_line": 48,
            "function": "login",
            "class": None,
            "score": 0.83
        }

    Deduplicated by (file, start_line, end_line) in case the same
    chunk is retrieved more than once for a single question.
    """
    seen = set()
    references = []

    for c in chunks:
        key = (c.get("file_path"), c.get("start_line"), c.get("end_line"))
        if key in seen:
            continue
        seen.add(key)

        references.append({
            "file": c.get("file_path"),
            "start_line": c.get("start_line"),
            "end_line": c.get("end_line"),
            "function": c.get("function"),
            "class": c.get("class"),
            "score": c.get("score"),
        })

    return references


def answer_question(question: str, repository_id: str, top_k: int = 5) -> Dict:
    """
    Runs the full RAG pipeline for a single question against a single
    ingested repository:

        question -> embedding -> vector search -> top_k chunks
                 -> context construction -> prompt -> LLM -> answer

    Returns:
        {
            "answer": str,
            "references": [
                {file, start_line, end_line, function, class, score}, ...
            ],
            "chunks_used": int
        }

    Raises:
        ValueError if question is empty (surfaced by the route as a 400).
        Any other exception from retrieval or the LLM call propagates up
        for the route to translate into a 500 — this function does not
        swallow errors, since a caller (e.g. a batch job) may want to
        handle them differently than an HTTP route would.
    """
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")

    if not repository_id or not repository_id.strip():
        raise ValueError("repository_id cannot be empty")

    # Embedding + vector search (Day 6, 8, 9)
    chunks = search_code(query=question, repository=repository_id, top_k=top_k)

    # Context construction + prompt + LLM (Day 11)
    # generate_answer internally builds the grounded prompt from chunks
    # and calls the LLM — if chunks is empty, it still returns an honest
    # "nothing relevant found" answer rather than hallucinating.
    answer = generate_answer(question=question, chunks=chunks)

    return {
        "answer": answer,
        "references": _shape_references(chunks),
        "chunks_used": len(chunks),
    }