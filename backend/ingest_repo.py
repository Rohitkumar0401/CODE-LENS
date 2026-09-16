"""
ingest_repo.py

Chains together everything built on Days 2–8:

    GitHub URL
        |
        v
    clone_repository        (github_service.py)
        |
        v
    get_relevant_files       (file_service.py)
        |
        v
    chunk_repository         (chunk_service.py, uses code_parser_service.py internally)
        |
        v
    generate_embeddings_batch (embedding_service.py)
        |
        v
    upsert_chunks            (vector_service.py -> Pinecone)

Run:
    python ingest_repo.py https://github.com/owner/repo

This is a one-time (or re-run-when-updated) indexing step. Once it
finishes, /query and /ask can search that repository by its
repository_id, which is printed at the end of the run.
"""

import os
import sys
import argparse

from dotenv import load_dotenv
load_dotenv()

from app.services.github_service import clone_repository
from app.services.file_service import get_relevant_files
from app.services.chunk_service import chunk_repository
from app.services.embedding_service import generate_embeddings_batch
from app.services.vector_service import upsert_chunks


def _repository_id_from_url(github_url: str) -> str:
    """
    Matches the same owner__repo naming convention that
    github_service.clone_repository already uses for the folder name,
    so the repository_id you pass to /query and /ask is predictable.
    """
    repo_name = github_url.rstrip("/").split("/")[-1]
    owner = github_url.rstrip("/").split("/")[-2]
    return f"{owner}__{repo_name}"


def ingest_repository(github_url: str) -> None:
    repository_id = _repository_id_from_url(github_url)

    print(f"[1/5] Cloning {github_url} ...")
    repo_path = clone_repository(github_url)
    print(f"      -> cloned to {repo_path}")

    print("[2/5] Discovering relevant source files ...")
    relative_files = get_relevant_files(repo_path)
    print(f"      -> found {len(relative_files)} relevant files")

    if not relative_files:
        print("No relevant files found. Nothing to ingest.")
        return

    # chunk_repository reads each file itself, so it needs real paths on
    # disk (get_relevant_files returns paths relative to the repo root).
    absolute_files = [os.path.join(repo_path, f) for f in relative_files]

    print("[3/5] Parsing and chunking code (functions/classes) ...")
    chunks = chunk_repository(absolute_files)
    print(f"      -> extracted {len(chunks)} code chunks")

    if not chunks:
        print("No chunks were extracted (unsupported languages only?). Stopping.")
        return

    # Store clean, repo-relative paths instead of absolute disk paths,
    # so results returned by /query and /ask look like "auth.py" instead
    # of "C:\Users\...\data\repos\owner__repo\auth.py".
    for chunk in chunks:
        chunk.file_path = os.path.relpath(chunk.file_path, repo_path).replace(os.sep, "/")

    print(f"[4/5] Generating embeddings for {len(chunks)} chunks ...")
    code_snippets = [c.code for c in chunks]
    embeddings = generate_embeddings_batch(code_snippets)
    print(f"      -> generated {len(embeddings)} embeddings")

    print(f"[5/5] Upserting into Pinecone under repository_id='{repository_id}' ...")
    upserted_count = upsert_chunks(chunks, embeddings, repository=repository_id)
    print(f"      -> upserted {upserted_count} vectors")

    print()
    print("Done. Use this repository_id when calling /query or /ask:")
    print(f"    {repository_id}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest a GitHub repository into CodeLens.")
    parser.add_argument("github_url", help="e.g. https://github.com/pallets/flask")
    args = parser.parse_args()

    try:
        ingest_repository(args.github_url)
    except Exception as e:
        print(f"\nIngestion failed: {e}", file=sys.stderr)
        sys.exit(1)