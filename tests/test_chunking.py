"""Tests for core/chunking.py — paragraph/sentence-boundary-aware chunking with overlap."""

from core.chunking import chunk_text


def test_short_text_returns_single_chunk():
    text = "A short page about a company."
    assert chunk_text(text, max_chars=3000) == [text]


def test_empty_text_returns_no_chunks():
    assert chunk_text("", max_chars=3000) == []
    assert chunk_text("   ", max_chars=3000) == []


def test_long_text_splits_on_paragraph_boundaries():
    paragraphs = [f"Paragraph {i}. " + ("word " * 50) for i in range(10)]
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text, max_chars=400, overlap_chars=50)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 400 + 50  # allow for one paragraph slightly over due to overlap carry


def test_oversized_single_paragraph_falls_back_to_sentences():
    # One giant paragraph, no \n\n breaks, forces the sentence-split path.
    sentences = [f"This is sentence number {i} in a very long paragraph." for i in range(40)]
    text = " ".join(sentences)
    chunks = chunk_text(text, max_chars=300, overlap_chars=30)
    assert len(chunks) > 1
    # No chunk should have silently swallowed the whole text as one blob.
    assert all(len(c) <= 300 + 30 for c in chunks)


def test_consecutive_chunks_share_overlap():
    paragraphs = [f"Paragraph {i} content here with some words to pad it out." for i in range(8)]
    text = "\n\n".join(paragraphs)
    chunks = chunk_text(text, max_chars=150, overlap_chars=40)
    assert len(chunks) > 1
    # The tail of chunk N should reappear at the head of chunk N+1.
    tail = chunks[0][-20:]
    assert tail in chunks[1]
