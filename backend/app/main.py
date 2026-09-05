from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.services.github_service import clone_repository
from app.services.file_service import get_relevant_files

app = FastAPI()


class IngestRequest(BaseModel):
    github_url: str


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