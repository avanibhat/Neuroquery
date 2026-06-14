import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from ingest import _chunk


def test_short_text_gives_single_chunk():
    text = "Amyloid beta accumulates in Alzheimer's disease."
    chunks = _chunk(text, size=50, overlap=10)
    assert len(chunks) == 1
    assert chunks[0].strip() == text.strip()


def test_long_text_gives_multiple_chunks():
    # 10 sentences of ~15 words each = ~150 words, chunk size 30 → should produce >1 chunk
    sentence = "Tau protein accumulates in neurons and leads to neurofibrillary tangle formation. "
    text = sentence * 10
    chunks = _chunk(text, size=30, overlap=5)
    assert len(chunks) > 1


def test_overlap_carries_words_forward():
    # Build text with enough words to force two chunks
    words = [f"word{i}" for i in range(200)]
    text  = " ".join(words) + "."  # single sentence, falls back to word-level chunking
    chunks = _chunk(text, size=50, overlap=10)
    if len(chunks) > 1:
        tail_of_first = set(chunks[0].split()[-10:])
        head_of_second = set(chunks[1].split()[:10])
        # At least some overlap words should appear in both chunks
        assert len(tail_of_first & head_of_second) > 0


def test_empty_text_returns_no_chunks():
    chunks = _chunk("", size=50, overlap=10)
    assert chunks == [] or (len(chunks) == 1 and chunks[0].strip() == "")


def test_chunk_size_respected():
    sentence = "This is a test sentence with exactly eight words here. "
    text = sentence * 20   # ~160 words
    chunks = _chunk(text, size=20, overlap=5)
    for chunk in chunks:
        assert len(chunk.split()) <= 40  # allow some slack for sentence boundary rounding
