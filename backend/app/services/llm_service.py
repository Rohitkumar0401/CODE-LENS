"""
app/services/llm_service.py

Day 11 — LLM Response Generation (Google Gemini, free tier)

Pipeline this module completes:
    User Question -> Embedding -> Vector Search -> Relevant Code
                                                        |
                                                        v
                                                     Prompt -> LLM -> Answer

Core rule: the LLM must answer ONLY from the retrieved code chunks it's
given. It should never pretend to know the rest of the repository, and
must say so explicitly when the retrieved context doesn't answer the
question.

Uses Google's Gemini API free tier (no billing required). Get a key at
https://aistudio.google.com/apikey and set it as GEMINI_API_KEY.
"""

import os
from typing import List, Dict

from google import genai
from google.genai import types

_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# gemini-2.5-flash is on Google's free tier (no billing needed) as of
# this writing. Swap to a newer Flash model (e.g. gemini-3.8-flash) if
# you want the latest — the rest of this file doesn't need to change.
DEFAULT_MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = (
    "You are CodeLens, a code assistant that answers questions about a "
    "specific software repository.\n\n"
    "You will be given a set of retrieved code snippets from that repository, "
    "each labeled with its file path and line range. These snippets are the "
    "ONLY information you have about the repository — you have no other "
    "knowledge of this codebase.\n\n"
    "Rules:\n"
    "1. Answer using ONLY the provided code snippets. Do not assume the "
    "existence of any function, class, file, or behavior that is not shown.\n"
    "2. If the snippets don't contain enough information to answer the "
    "question, say so plainly instead of guessing.\n"
    "3. When you reference code, cite the file path and line numbers it "
    "came from.\n"
    "4. Do not fabricate code, APIs, or explanations not grounded in the "
    "given snippets."
)


def _format_chunk(chunk: Dict, index: int) -> str:
    """
    Formats one retrieved chunk (the dict shape returned by
    retrieval_service.search_code) into a labeled block for the prompt.
    """
    file_path = chunk.get("file_path", "unknown")
    start = chunk.get("start_line", "?")
    end = chunk.get("end_line", "?")
    language = chunk.get("language", "")
    function = chunk.get("function")
    class_name = chunk.get("class")
    code = chunk.get("code", "")

    label_bits = [f"[{index}] {file_path}:{start}-{end}"]
    if class_name:
        label_bits.append(f"class {class_name}")
    if function:
        label_bits.append(f"function {function}")
    label = " | ".join(label_bits)

    return f"{label}\n```{language.lower() if language else ''}\n{code}\n```"


def build_prompt(question: str, chunks: List[Dict]) -> str:
    """
    Assembles the user-turn prompt: the retrieved snippets followed by
    the question, so the model answers grounded in exactly what's given.
    """
    if not chunks:
        return (
            f"No relevant code snippets were found in the repository for "
            f"this question.\n\nQuestion: {question}\n\n"
            f"Explain that nothing relevant was found and do not guess "
            f"at an answer."
        )

    snippet_blocks = "\n\n".join(
        _format_chunk(chunk, i + 1) for i, chunk in enumerate(chunks)
    )

    return (
        f"Retrieved code snippets:\n\n{snippet_blocks}\n\n"
        f"Question: {question}\n\n"
        f"Answer the question using only the snippets above, citing "
        f"file paths and line numbers where relevant."
    )


def generate_answer(
    question: str,
    chunks: List[Dict],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
) -> str:
    """
    Full Day 11 pipeline step: retrieved chunks + question -> LLM answer.

    chunks: the list of dicts returned by retrieval_service.search_code().
    Kept deliberately low temperature (0.2) since this is meant to be a
    grounded, factual answer about real code, not creative writing.
    """
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")

    prompt = build_prompt(question, chunks)

    response = _client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=temperature,
        ),
    )

    return response.text