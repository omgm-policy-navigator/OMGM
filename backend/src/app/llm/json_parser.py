from __future__ import annotations

import json

from pydantic import ValidationError

from app.llm.providers import LLMInvalidJSONError
from app.llm.schemas import AIOutput


def parse_ai_output_json(raw_output: str) -> AIOutput:
    """Extract and validate the first JSON object from model text."""
    text = raw_output.strip()
    if not text:
        raise LLMInvalidJSONError("LLM response did not include JSON text.")

    for candidate in _json_object_candidates(text):
        try:
            decoded = json.loads(candidate)
            return AIOutput.model_validate(decoded)
        except (json.JSONDecodeError, ValidationError):
            continue

    raise LLMInvalidJSONError("LLM response did not match AIOutput JSON contract.")


def _json_object_candidates(text: str) -> list[str]:
    candidates = [text]
    fenced = _extract_fenced_json(text)
    if fenced is not None:
        candidates.append(fenced)
    balanced = _extract_first_balanced_object(text)
    if balanced is not None:
        candidates.append(balanced)
    return candidates


def _extract_fenced_json(text: str) -> str | None:
    marker = "```"
    start = text.find(marker)
    if start == -1:
        return None
    content_start = start + len(marker)
    end = text.find(marker, content_start)
    if end == -1:
        return None
    fenced = text[content_start:end].strip()
    if fenced.lower().startswith("json"):
        fenced = fenced[4:].strip()
    return fenced or None


def _extract_first_balanced_object(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None
