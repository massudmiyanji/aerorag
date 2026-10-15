from collections.abc import Iterator

import pytest
from pydantic import ValidationError

from aerorag.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _fresh_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    # Isolate tests from a developer's shell or .env file.
    monkeypatch.chdir("/")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_defaults_load() -> None:
    settings = get_settings()
    assert settings.llm_model == "qwen3:4b"
    assert settings.retrieve_top_k == 20


def test_env_var_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AERORAG_LLM_MODEL", "qwen3:8b")
    assert get_settings().llm_model == "qwen3:8b"


def test_overlap_must_be_smaller_than_chunk_size() -> None:
    with pytest.raises(ValidationError):
        Settings(chunk_size_tokens=100, chunk_overlap_tokens=100)


def test_rerank_top_n_cannot_exceed_retrieve_top_k() -> None:
    with pytest.raises(ValidationError):
        Settings(retrieve_top_k=5, rerank_top_n=10)
