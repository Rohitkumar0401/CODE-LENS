"""
test_ask_route.py

Smoke test for POST /ask. Mocks app.services.rag_service.answer_question
(as imported into app.routes.routes_ask) so this runs with no network,
no Pinecone connection, and no Gemini API calls. rag_service's own logic
is tested separately in test_rag_service.py.

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


FAKE_RESULT = {
    "answer": "Login is handled in auth.py:42-68.",
    "sources": [
        {"file": "auth.py", "start_line": 42, "end_line": 68, "function": "login", "class": None, "score": 0.91},
    ],
    "chunks_used": 1,
}


def test_ask_returns_answer_and_sources():
    with patch("app.routes.routes_ask.answer_question", return_value=FAKE_RESULT) as mock_pipeline:
        response = client.post(
            "/ask",
            json={"repository_id": "abc123", "question": "How does login work?"},
        )

    assert response.status_code == 200, response.text
    mock_pipeline.assert_called_once_with(question="How does login work?", repository_id="abc123", top_k=5)
    data = response.json()
    assert data["answer"] == "Login is handled in auth.py:42-68."
    assert data["chunks_used"] == 1
    assert data["sources"][0]["file"] == "auth.py"
    print("PASS: /ask returns answer + sources + chunks_used")


def test_ask_empty_question_becomes_400():
    with patch("app.routes.routes_ask.answer_question", side_effect=ValueError("Question cannot be empty")):
        response = client.post("/ask", json={"repository_id": "abc123", "question": "  "})

    assert response.status_code == 400
    print("PASS: ValueError from pipeline surfaces as 400")


def test_ask_pipeline_failure_returns_500():
    with patch("app.routes.routes_ask.answer_question", side_effect=RuntimeError("Gemini API down")):
        response = client.post(
            "/ask",
            json={"repository_id": "abc123", "question": "How does login work?"},
        )

    assert response.status_code == 500
    print("PASS: unexpected pipeline failure surfaces as 500")


def test_custom_top_k_passed_through():
    with patch("app.routes.routes_ask.answer_question", return_value=FAKE_RESULT) as mock_pipeline:
        client.post(
            "/ask",
            json={"repository_id": "abc123", "question": "auth flow", "top_k": 3},
        )
    mock_pipeline.assert_called_once_with(question="auth flow", repository_id="abc123", top_k=3)
    print("PASS: top_k passed through to the pipeline")


if __name__ == "__main__":
    test_ask_returns_answer_and_sources()
    test_ask_empty_question_becomes_400()
    test_ask_pipeline_failure_returns_500()
    test_custom_top_k_passed_through()
    print("\nAll Day 11/12 route tests passed.")