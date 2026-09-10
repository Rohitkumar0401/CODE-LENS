"""
End-to-end smoke test for the CodeLens ingestion pipeline.
Run: python -m app.test_pipeline <github_url>
"""
import os
import sys
import traceback

from app.services.github_service import clone_repository
from app.services.file_service import get_relevant_files
from app.services.chunk_service import chunk_repository
from app.services.embedding_service import generate_embeddings_batch


def run_pipeline(github_url: str):
    print(f"\n[1/4] Cloning: {github_url}")
    repo_path = clone_repository(github_url)
    print(f"  -> cloned to {repo_path}")

    print("\n[2/4] Discovering files")
    relative_files = get_relevant_files(repo_path)
    full_paths = [os.path.join(repo_path, f) for f in relative_files]
    print(f"  -> found {len(relative_files)} relevant files")
    for f in relative_files[:10]:
        print(f"     {f}")

    print("\n[3/4] Chunking (AST for Python, brace-matching for C++/Java/JS)")
    chunks = chunk_repository(full_paths)
    print(f"  -> generated {len(chunks)} chunks")
    if chunks:
        c = chunks[0]
        print(f"     sample: {c.function_name or c.class_name} "
              f"in {c.file_path} [{c.language}] lines {c.start_line}-{c.end_line}")

    print("\n[4/4] Generating embeddings (batched)")
    code_snippets = [c.code for c in chunks]
    embeddings = generate_embeddings_batch(code_snippets)
    dims = {len(e) for e in embeddings if e}
    print(f"  -> {len(embeddings)} embeddings generated, dimension(s) seen: {dims}")

    print("\n✅ Pipeline completed without fatal errors.")
    print(f"Files: {len(relative_files)} | Chunks: {len(chunks)} | Embeddings: {len(embeddings)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.test_pipeline <github_url>")
        sys.exit(1)
    try:
        run_pipeline(sys.argv[1])
    except Exception:
        print("\n❌ Pipeline failed:")
        traceback.print_exc()
        sys.exit(1)