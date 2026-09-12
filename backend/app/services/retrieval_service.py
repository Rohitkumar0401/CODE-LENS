from typing import List, Dict
from app.services.embedding_service import generate_embedding
from app.services.vector_service import get_index


def search_code(query: str, repository: str = None, top_k: int = 5) -> List[Dict]:
    """
    Converts a natural language query into an embedding, then searches
    Pinecone for the most semantically similar code chunks.

    query: e.g. "Where is user authentication implemented?"
    repository: optional filter, e.g. "pallets__flask" — limits search
                to one indexed repo. Omit to search across all.
    top_k: number of results to return.
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty")

    query_embedding = generate_embedding(query)
    if not query_embedding:
        raise ValueError("Failed to generate embedding for query")

    index = get_index()

    filter_dict = {"repository": repository} if repository else None

    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        filter=filter_dict,
    )

    matches = []
    for match in results.get("matches", []):
        metadata = match.get("metadata", {})
        matches.append({
            "score": match.get("score"),
            "file_path": metadata.get("file_path"),
            "function": metadata.get("function") or None,
            "class": metadata.get("class") or None,
            "language": metadata.get("language"),
            "start_line": metadata.get("start_line"),
            "end_line": metadata.get("end_line"),
            "repository": metadata.get("repository"),
        })

    return matches