from typing import List
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("all-MiniLM-L6-v2")


def generate_embedding(code: str) -> List[float]:
    if not code or not code.strip():
        return []
    embedding = _model.encode(code, convert_to_numpy=True)
    return embedding.tolist()


def generate_embeddings_batch(code_snippets: List[str]) -> List[List[float]]:
    if not code_snippets:
        return []
    embeddings = _model.encode(code_snippets, convert_to_numpy=True)
    return embeddings.tolist()