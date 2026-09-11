import os
from typing import List
from pinecone import Pinecone, ServerlessSpec

from app.models.chunk import CodeChunk

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "codelens")
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 output size — must match embedding_service.py

pc = Pinecone(api_key=PINECONE_API_KEY)
_index = None


def _ensure_index():
    existing = [i["name"] for i in pc.list_indexes()]
    if INDEX_NAME not in existing:
        pc.create_index(
            name=INDEX_NAME,
            dimension=EMBEDDING_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    return pc.Index(INDEX_NAME)


def get_index():
    global _index
    if _index is None:
        _index = _ensure_index()
    return _index


def _chunk_id(chunk: CodeChunk, repository: str) -> str:
    return f"{repository}:{chunk.file_path}:{chunk.start_line}"


def _chunk_metadata(chunk: CodeChunk, repository: str) -> dict:
    return {
        "file_path": chunk.file_path,
        "function": chunk.function_name or "",
        "class": chunk.class_name or "",
        "language": chunk.language,
        "start_line": chunk.start_line,
        "end_line": chunk.end_line,
        "repository": repository,
    }


def upsert_chunks(chunks: List[CodeChunk], embeddings: List[List[float]],
                   repository: str, batch_size: int = 100) -> int:
    """
    chunks and embeddings must be the same length and same order
    (i.e. embeddings[i] corresponds to chunks[i]).
    """
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) length mismatch"
        )

    index = get_index()
    vectors = [
        {
            "id": _chunk_id(chunk, repository),
            "values": embedding,
            "metadata": _chunk_metadata(chunk, repository),
        }
        for chunk, embedding in zip(chunks, embeddings)
        if embedding  # skip empty embeddings (e.g. blank code)
    ]

    for i in range(0, len(vectors), batch_size):
        index.upsert(vectors=vectors[i:i + batch_size])

    return len(vectors)