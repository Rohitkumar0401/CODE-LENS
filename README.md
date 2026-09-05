# CodeLens

**CodeLens** is an AI-powered codebase understanding tool. Give it a GitHub repository URL, and it lets you *ask questions about the code* in plain English — from simple lookups like "what does this function do?" to deeper reasoning like "what happens if I change this?"

Under the hood, it combines **Retrieval-Augmented Generation (RAG)** with static code analysis, so answers are grounded in the actual structure and content of the repository — not just an LLM guessing.

---

## Why this exists

Understanding an unfamiliar codebase is one of the most time-consuming parts of working with software — whether you're onboarding onto a new project, reviewing a pull request, or trying to safely make a change without breaking something you don't fully understand. CodeLens aims to shorten that gap by letting you *ask* the codebase directly, instead of manually tracing through files.

---

## What it does

- **Ingests a GitHub repository** — clones it and identifies the relevant source files, filtering out noise like `.git`, `node_modules`, build artifacts, and binaries.
- **Answers questions about the code** using retrieval over the codebase's content (RAG) — e.g. "where is user authentication handled?"
- **Answers impact questions** — e.g. "what happens if I change this function?" — by combining semantic retrieval with structural analysis of the codebase (such as which files/functions depend on the one being changed), rather than relying on the language model to guess.
- **Runs anywhere via Docker** — packaged for easy setup and deployment, not tied to a specific machine's environment.

---

## How it works (architecture)

```
GitHub URL
    │
    ▼
Repository Ingestion   → clones the repo locally
    │
    ▼
File Discovery         → walks the repo, filters out irrelevant/binary/oversized files
    │
    ▼
Indexing                → chunks relevant files and embeds them for semantic search
    │
    ▼
Query Engine            → given a user question, retrieves relevant code context
    │                      (and, for "what if" questions, relevant dependency/call info)
    ▼
LLM Response            → generates a grounded answer using the retrieved context
```

*(Architecture diagram: see `docs/architecture.png`)*

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python) |
| Repository handling | GitPython |
| Data validation | Pydantic |
| Retrieval / embeddings | *(in progress)* |
| Vector storage | *(in progress)* |
| LLM integration | *(in progress)* |
| Deployment | Docker |

---

## Project status

This project is being built incrementally, day by day, as part of a structured build log. Current progress:

- [x] Project scaffolding (FastAPI app, repo structure, licensing)
- [x] GitHub repository ingestion (clone by URL)
- [x] File discovery — relevant source file detection with filtering for VCS folders, dependency folders, binaries, and oversized files
- [ ] Code chunking + embedding pipeline
- [ ] Vector search / retrieval
- [ ] LLM-based question answering (RAG)
- [ ] Structural/dependency analysis for "what if I change this" queries
- [ ] Dockerization
- [ ] Frontend interface

---

## Getting started

### Prerequisites
- Python 3.10+
- Git installed and available on your system PATH

### Setup

```bash
# Clone this repository
git clone https://github.com/<your-username>/CODE-LENS.git
cd CODE-LENS/backend

# Create and activate a virtual environment
python -m venv venv
source venv/Scripts/activate     # Windows (Git Bash)
# source venv/bin/activate       # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the API server
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`, with interactive docs at `http://127.0.0.1:8000/docs`.

### Example usage

```bash
curl -X POST http://127.0.0.1:8000/repository/ingest \
  -H "Content-Type: application/json" \
  -d '{"github_url": "https://github.com/octocat/Hello-World"}'
```

Response:
```json
{
  "message": "Repository ingested successfully",
  "repo_path": "data/repos/octocat__Hello-World",
  "file_count": 1,
  "files": ["README"]
}
```

---

## Project structure

```
CODE-LENS/
├── backend/
│   └── app/
│       ├── api/
│       ├── models/
│       ├── services/
│       │   ├── github_service.py   # Repository cloning
│       │   └── file_service.py     # File discovery & filtering
│       ├── utils/
│       └── main.py                 # FastAPI entrypoint
├── frontend/                       # (planned)
├── docs/                           # Architecture diagrams, design notes
├── tests/
├── requirements.txt
└── README.md
```

---

## Roadmap

1. Chunk discovered source files (by function/class boundaries where possible, not naive fixed-size splits)
2. Generate embeddings and store them in a vector database
3. Build the retrieval + LLM answer pipeline
4. Add structural/call-graph analysis to support accurate "what happens if I change this" answers
5. Containerize the full application with Docker
6. Build a simple frontend for interacting with a repository conversationally

---

## License

See [LICENSE](./LICENSE) for details.