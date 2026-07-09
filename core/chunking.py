"""
core/chunking.py

Splits scraped page content into LLM-sized chunks without cutting mid-sentence.

Previously the extractor took a flat first-N-chars slice of a page and threw
away everything past it — a long page's founding date or funding round could
sit at char 4000 and never reach the model. This splits on paragraph
boundaries first, falls back to sentence boundaries for oversized paragraphs,
and carries a trailing overlap into the next chunk so a fact split across a
boundary isn't lost to either side.
"""

import re

_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+")


def chunk_text(text: str, max_chars: int = 3000, overlap_chars: int = 300) -> list[str]:
    """
    Split text into chunks of at most max_chars, preferring paragraph
    boundaries, falling back to sentence boundaries for oversized paragraphs.
    Each chunk after the first starts with up to overlap_chars carried over
    from the end of the previous chunk.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    current = ""

    def flush_and_carry_overlap() -> None:
        nonlocal current
        if current.strip():
            chunks.append(current.strip())
        current = current[-overlap_chars:] if len(current) > overlap_chars else current

    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if len(paragraph) <= max_chars:
            flush_and_carry_overlap()
            current = f"{current}\n\n{paragraph}" if current else paragraph
            continue

        # Paragraph itself exceeds max_chars — fall back to sentence splitting.
        for sentence in _SENTENCE_BOUNDARY_RE.split(paragraph):
            sentence = sentence.strip()
            if not sentence:
                continue
            candidate = f"{current} {sentence}" if current else sentence
            if len(candidate) <= max_chars:
                current = candidate
            else:
                flush_and_carry_overlap()
                current = f"{current} {sentence}" if current else sentence

    if current.strip():
        chunks.append(current.strip())

    return chunks
