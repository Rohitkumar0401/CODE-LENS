from dotenv import load_dotenv
load_dotenv()

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.services.github_service import clone_repository
from app.services.file_service import get_relevant_files
from app.services.code_parser_service import parse_repository
from app.services.chunk_service import chunk_repository
from app.services.embedding_service import generate_embeddings_batch
from app.services.vector_service import upsert_chunks
from app.services.retrieval_service import search_code
from app.routes.routes_ask import router as ask_router
from app.services.dependency_service import analyze_dependencies

app = FastAPI()
app.include_router(ask_router)


# ---------- Request models ----------

class IngestRequest(BaseModel):
    github_url: str


class ParseRequest(BaseModel):
    repo_path: str


class SearchRequest(BaseModel):
    query: str
    repository: str | None = None
    top_k: int = 5


# ---------- Routes ----------

@app.get("/")
def root():
    return {"message": "CodeLens API is running"}


@app.post("/repository/ingest")
def ingest_repository(request: IngestRequest):
    try:
        repo_path = clone_repository(request.github_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to clone repository: {e}")

    try:
        relevant_files = get_relevant_files(repo_path)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "message": "Repository ingested successfully",
        "repo_path": repo_path,
        "file_count": len(relevant_files),
        "files": relevant_files,
    }


@app.post("/repository/parse")
def parse_repository_structure(request: ParseRequest):
    try:
        relevant_files = get_relevant_files(request.repo_path)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    full_paths = [os.path.join(request.repo_path, f) for f in relevant_files]

    structure = parse_repository(full_paths)

    return {
        "message": "Repository parsed successfully",
        "repo_path": request.repo_path,
        "file_count": len(relevant_files),
        "symbol_count": len(structure),
        "structure": structure,
    }


@app.post("/repository/index")
def index_repository(request: IngestRequest):
    try:
        repo_path = clone_repository(request.github_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to clone repository: {e}")

    try:
        relevant_files = get_relevant_files(repo_path)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    full_paths = [os.path.join(repo_path, f) for f in relevant_files]

    chunks = chunk_repository(full_paths)
    code_snippets = [c.code for c in chunks]
    embeddings = generate_embeddings_batch(code_snippets)

    repo_name = os.path.basename(repo_path)

    try:
        stored_count = upsert_chunks(chunks, embeddings, repository=repo_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to store vectors: {e}")

    return {
        "message": "Repository indexed successfully",
        "repo_path": repo_path,
        "file_count": len(relevant_files),
        "chunk_count": len(chunks),
        "vectors_stored": stored_count,
    }


@app.post("/repository/search")
def search_repository(request: SearchRequest):
    try:
        results = search_code(
            query=request.query,
            repository=request.repository,
            top_k=request.top_k,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

    return {
        "query": request.query,
        "repository": request.repository,
        "result_count": len(results),
        "results": results,
    }

@app.post("/repository/dependencies")
def analyze_repository_dependencies(request: ParseRequest):
    try:
        relevant_files = get_relevant_files(request.repo_path)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    full_paths = [os.path.join(request.repo_path, f) for f in relevant_files]

    graph = analyze_dependencies(full_paths)

    return {
        "message": "Dependency analysis complete",
        "repo_path": request.repo_path,
        "file_count": graph.file_count,
        "edge_count": graph.edge_count,
        "edges": [e.model_dump() for e in graph.edges],
        "cycles": graph.cycles,
    }
