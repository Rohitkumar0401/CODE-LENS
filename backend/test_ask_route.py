"""
test_ask_route.py

Smoke test for POST /ask. Mocks app.services.retrieval_service.search_code
and app.services.llm_service.generate_answer (as imported into
app.routes.routes_ask) so this runs with no network, no Pinecone
connection, and no Gemini API calls.

Run with:
    python -m test_ask_route
"""

from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.routes_ask import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


FAKE_CHUNKS = [
    {
        "score": 0.91,
        "file_path": "auth.py",
        "function": "login",
        "class": None,
        "language": "Python",
        "start_line": 42,
        "end_line": 68,
        "repository": "abc123",
        "code": "def login():\n    ...",
    },
]


def test_ask_returns_answer_and_sources():
    with patch("app.routes.routes_ask.search_code", return_value=FAKE_CHUNKS) as mock_search, \
         patch("app.routes.routes_ask.generate_answer", return_value="Login is handled in auth.py:42-68.") as mock_llm:

        response = client.post(
            "/ask",
            json={"repository_id": "abc123", "question": "How does login work?"},
        )

    assert response.status_code == 200, response.text
    mock_search.assert_called_once_with(query="How does login work?", repository="abc123", top_k=5)
    mock_llm.assert_called_once()
    data = response.json()
    assert data["answer"] == "Login is handled in auth.py:42-68."
    assert data["sources"][0]["file"] == "auth.py"
    print("PASS: /ask returns answer + sources")


def test_ask_empty_question_rejected():
    response = client.post("/ask", json={"repository_id": "abc123", "question": "  "})
    assert response.status_code == 400
    print("PASS: empty question rejected (400)")


def test_ask_no_chunks_still_calls_llm():
    with patch("app.routes.routes_ask.search_code", return_value=[]), \
         patch("app.routes.routes_ask.generate_answer", return_value="No relevant code was found.") as mock_llm:

        response = client.post(
            "/ask",
            json={"repository_id": "abc123", "question": "Does this repo do payroll?"},
        )

    assert response.status_code == 200
    assert response.json()["sources"] == []
    assert "No relevant code" in response.json()["answer"]
    mock_llm.assert_called_once()
    print("PASS: empty retrieval still produces an honest answer")


def test_ask_llm_failure_returns_500():
    with patch("app.routes.routes_ask.search_code", return_value=FAKE_CHUNKS), \
         patch("app.routes.routes_ask.generate_answer", side_effect=RuntimeError("API down")):

        response = client.post(
            "/ask",
            json={"repository_id": "abc123", "question": "How does login work?"},
        )

    assert response.status_code == 500
    print("PASS: LLM failure surfaces as 500")


if __name__ == "__main__":
    test_ask_returns_answer_and_sources()
    test_ask_empty_question_rejected()
    test_ask_no_chunks_still_calls_llm()
    test_ask_llm_failure_returns_500()
    print("\nAll Day 11 smoke tests passed.")