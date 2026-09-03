from fastapi import FastAPI
from app.api.routes_repository import router as repository_router

app = FastAPI(title="CodeLens API")

app.include_router(repository_router)


@app.get("/")
def read_root():
    return {"message": "CodeLens API is running"}
