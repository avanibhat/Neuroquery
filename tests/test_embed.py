import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from retriever import embed

BIOBERT_HIDDEN_SIZE = 768


def test_embed_returns_list():
    vec = embed("Alzheimer's disease biomarkers")
    assert isinstance(vec, list)


def test_embed_dimensionality():
    vec = embed("tau protein neurofibrillary tangles")
    assert len(vec) == BIOBERT_HIDDEN_SIZE, (
        f"Expected {BIOBERT_HIDDEN_SIZE}-dim embedding, got {len(vec)}"
    )


def test_embed_all_floats():
    vec = embed("amyloid beta accumulation")
    assert all(isinstance(x, float) for x in vec)


def test_embed_nonzero():
    vec = embed("APOE4 genetic risk factor")
    assert any(x != 0.0 for x in vec)


def test_embed_different_texts_differ():
    vec1 = embed("amyloid plaques")
    vec2 = embed("clinical drug trial")
    assert vec1 != vec2


def test_embed_same_text_consistent():
    text = "neuroinflammation in Alzheimer's disease"
    assert embed(text) == embed(text)
