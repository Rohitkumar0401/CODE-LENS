"""
test_rag_service.py

Unit tests for app.services.rag_service.answer_question — the Day 12
end-to-end pipeline function. Tested directly, with no FastAPI/HTTP
layer involved, since this function should be usable standalone (CLI,
batch job, etc.), not just from the /ask route.

Mocks search_code and generate_answer (as imported into rag_service)
so this runs with no network, no Pinecone, no Gemini API calls.

Run with:
    python -m test_rag_service
"""

from unittest.mock import patch
from app.services.rag_service import answer_question

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
    {
        "score": 0.77,
        "file_path": "auth.py",
        "function": "generate_token",
        "class": None,
        "language": "Python",
        "start_line": 70,
        "end_line": 85,
        "repository": "abc123",
        "code": "def generate_token():\n    ...",
    },
]


def test_full_pipeline_happy_path():
    with patch("app.services.rag_service.search_code", return_value=FAKE_CHUNKS) as mock_search, \
         patch("app.services.rag_service.generate_answer",
               return_value="Authentication is handled in auth.py. The login flow starts at line 42...") as mock_llm:

        result = answer_question(
            question="How does authentication work?",
            repository_id="abc123",
            top_k=5,
        )

    mock_search.assert_called_once_with(query="How does authentication work?", repository="abc123", top_k=5)
    mock_llm.assert_called_once_with(question="How does authentication work?", chunks=FAKE_CHUNKS)

    assert result["chunks_used"] == 2
    assert len(result["references"]) == 2
    assert result["references"][0]["file"] == "auth.py"
    assert result["references"][0]["start_line"] == 42
    assert "auth.py" in result["answer"]
    print("PASS: full pipeline returns answer + sources + chunk count")


def test_empty_question_raises_value_error():
    try:
        answer_question(question="   ", repository_id="abc123")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "Question" in str(e)
        print("PASS: empty question raises ValueError")


def test_empty_repository_id_raises_value_error():
    try:
        answer_question(question="How does login work?", repository_id="")
        assert False, "expected ValueError"
    except ValueError as e:
        assert "repository_id" in str(e)
        print("PASS: empty repository_id raises ValueError")


def test_no_chunks_still_returns_honest_answer():
    with patch("app.services.rag_service.search_code", return_value=[]), \
         patch("app.services.rag_service.generate_answer", return_value="No relevant code was found.") as mock_llm:

        result = answer_question(question="Does this repo do payroll?", repository_id="abc123")

    mock_llm.assert_called_once_with(question="Does this repo do payroll?", chunks=[])
    assert result["chunks_used"] == 0
    assert result["references"] == []
    assert "No relevant code" in result["answer"]
    print("PASS: zero-chunk retrieval still produces an honest, non-hallucinated answer")


def test_retrieval_error_propagates():
    with patch("app.services.rag_service.search_code", side_effect=RuntimeError("Pinecone down")):
        try:
            answer_question(question="How does login work?", repository_id="abc123")
            assert False, "expected RuntimeError to propagate"
        except RuntimeError:
            print("PASS: retrieval errors propagate to the caller unmodified")


if __name__ == "__main__":
    test_full_pipeline_happy_path()
    test_empty_question_raises_value_error()
    test_empty_repository_id_raises_value_error()
    test_no_chunks_still_returns_honest_answer()
    test_retrieval_error_propagates()
    print("\nAll Day 12 rag_service tests passed.")