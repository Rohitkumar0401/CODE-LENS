from pydantic import BaseModel, Field


class RepositoryRequest(BaseModel):
    github_url: str = Field(..., example="https://github.com/user/repository")
