"""
core/llm_json.py

Shared JSON parsing for LLM output. Every agent asks the model for JSON-only
output, but models still occasionally wrap it in markdown fences, prepend a
sentence of prose, or return a Qwen3 <think> block. This centralizes the
cleanup and adds a bracket-slice recovery pass so one malformed response
doesn't need its own bespoke parser in every agent file.
"""

import json
import re

_THINK_BLOCK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*")


def clean_llm_output(raw: str) -> str:
    """Strip <think> blocks and markdown code fences from raw LLM output."""
    cleaned = _THINK_BLOCK_RE.sub("", raw).strip()
    cleaned = _CODE_FENCE_RE.sub("", cleaned).strip().rstrip("```").strip()
    return cleaned


def parse_llm_json(raw: str) -> dict | list:
    """
    Parse JSON from LLM output, tolerating the ways models fail to follow
    "JSON only" instructions.

    Order of attempts:
    1. Direct json.loads() on the cleaned string.
    2. Bracket-slice recovery — find the first '{'/'[' and matching last
       '}'/']' and try parsing that slice. Recovers JSON the model wrapped
       in leading/trailing prose despite instructions not to.

    Raises ValueError if neither attempt produces valid JSON.
    """
    cleaned = clean_llm_output(raw)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    for start_char, end_char in (("{", "}"), ("[", "]")):
        start = cleaned.find(start_char)
        end = cleaned.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                continue

    raise ValueError(f"Could not parse JSON from LLM output (first 300 chars): {raw[:300]}")
