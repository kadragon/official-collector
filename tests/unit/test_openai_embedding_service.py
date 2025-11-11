"""
Unit tests for OpenAIEmbeddingService batching behaviour.
"""

import sys
import types
import time
from pathlib import Path

import openai
import pytest

# Add src to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from services.openai_embedding_service import (  # pylint: disable=wrong-import-position
    EmbeddingRequest,
    OpenAIEmbeddingService,
)


class DummyEmbeddings:
    """Stub embeddings endpoint that simulates rate limiting."""

    def __init__(self):
        self.calls = 0

    def create(
        self, *, model, input, encoding_format
    ):  # pylint: disable=unused-argument
        self.calls += 1
        if self.calls == 1:
            raise openai.RateLimitError()

        embeddings = [
            types.SimpleNamespace(embedding=[float(index)] * 3)
            for index, _ in enumerate(input, start=1)
        ]
        usage = types.SimpleNamespace(total_tokens=len(input) * 10)
        return types.SimpleNamespace(data=embeddings, usage=usage)


def test_create_embeddings_batch_retries_on_rate_limit(monkeypatch):
    """Ensure batches are retried when a rate limit error occurs."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        openai, "RateLimitError", type("FakeRateLimitError", (Exception,), {})
    )

    dummy_endpoint = DummyEmbeddings()
    dummy_client = types.SimpleNamespace(embeddings=dummy_endpoint)
    monkeypatch.setattr(openai, "OpenAI", lambda api_key: dummy_client)
    monkeypatch.setattr(time, "sleep", lambda _: None)

    service = OpenAIEmbeddingService()
    requests = [
        EmbeddingRequest(text="first text", identifier="doc-1"),
        EmbeddingRequest(text="second text", identifier="doc-2"),
    ]

    responses = service.create_embeddings_batch(requests, batch_size=2)

    assert len(responses) == 2
    assert dummy_endpoint.calls == 2
