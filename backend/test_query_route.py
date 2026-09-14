"""
test_query_route.py

Smoke test for POST /query. Mocks app.services.retrieval_service.search_code
(as imported into app.routes.routes_query) so this runs with no network,
no Pinecone connection, and no embedding model download.

Run with:
    pip install fastapi httpx --break-system-packages
    cd codelens
    python -m test_query_route
"""

from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.routes_query import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


FAKE_MATCHES = [
    {
        "score": 0.91,
        "file_path": "auth.py",
        "function": "login",
        "class": None,
        "language": "Python",
        "start_line": 42,
        "end_line": 68,
        "repository": "abc123",
    },
    {
        "score": 0.77,
        "file_path": "middleware/auth.py",
        "function": "verify_token",
        "class": None,
        "language": "Python",
        "start_line": 10,
        "end_line": 30,
        "repository": "abc123",
    },
]


def test_query_returns_expected_shape():
    with patch("app.routes.routes_query.search_code", return_value=FAKE_MATCHES) as mock_search:
        response = client.post(
            "/query",
            json={"repository_id": "abc123", "question": "How does authentication work?"},
        )

    assert response.status_code == 200, response.text
    mock_search.assert_called_once_with(
        query="How does authentication work?", repository="abc123", top_k=5
    )
    data = response.json()
    assert len(data["results"]) == 2
    assert data["results"][0]["file"] == "auth.py"
    assert data["results"][0]["start_line"] == 42
    assert data["results"][0]["end_line"] == 68
    print("PASS: /query returns correctly shaped results")


def test_empty_question_rejected():
    response = client.post("/query", json={"repository_id": "abc123", "question": "   "})
    assert response.status_code == 400
    print("PASS: empty question correctly rejected (400)")


def test_no_matches_returns_empty_list():
    with patch("app.routes.routes_query.search_code", return_value=[]):
        response = client.post(
            "/query",
            json={"repository_id": "abc123", "question": "Something not in the repo"},
        )
    assert response.status_code == 200
    assert response.json() == {"results": []}
    print("PASS: no-match query returns empty results list")


def test_search_code_value_error_becomes_400():
    with patch("app.routes.routes_query.search_code", side_effect=ValueError("Query cannot be empty")):
        response = client.post(
            "/query",
            json={"repository_id": "abc123", "question": "x"},
        )
    assert response.status_code == 400
    print("PASS: ValueError from search_code surfaces as 400")


def test_custom_top_k_is_passed_through():
    with patch("app.routes.routes_query.search_code", return_value=[]) as mock_search:
        client.post(
            "/query",
            json={"repository_id": "abc123", "question": "auth flow", "top_k": 3},
        )
    mock_search.assert_called_once_with(query="auth flow", repository="abc123", top_k=3)
    print("PASS: top_k passed through to search_code")


if __name__ == "__main__":
    test_query_returns_expected_shape()
    test_empty_question_rejected()
    test_no_matches_returns_empty_list()
    test_search_code_value_error_becomes_400()
    test_custom_top_k_is_passed_through()
    print("\nAll Day 10 smoke tests passed.")