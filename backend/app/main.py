from fastapi import FastAPI

app = FastAPI(title="CodeLens API")

@app.get("/")
def read_root():
    return {"message": "CodeLens API is running"}