import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.services.github_service import clone_repository
from app.services.file_service import get_relevant_files
from app.services.code_parser_service import parse_repository

app = FastAPI()


class IngestRequest(BaseModel):
    github_url: str


class ParseRequest(BaseModel):
    repo_path: str


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