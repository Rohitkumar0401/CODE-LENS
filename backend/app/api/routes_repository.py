from fastapi import APIRouter, HTTPException

from app.models.repository import RepositoryRequest
from app.services.github_service import clone_repository


router = APIRouter(
    prefix="/repository",
    tags=["Repository"]
)


@router.post("/ingest")
def ingest_repository(request: RepositoryRequest):

    try:

        result = clone_repository(request.github_url)

        return result

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except RuntimeError as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )