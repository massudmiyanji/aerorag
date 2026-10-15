"""Application settings, read from environment variables prefixed with AERORAG_."""

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Every tunable value in one place, so an experiment is a config change."""

    model_config = SettingsConfigDict(env_prefix="AERORAG_", env_file=".env", extra="ignore")

    # Services
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "aerorag_chunks"
    ollama_base_url: str = "http://localhost:11434"

    # Models
    llm_model: str = "qwen3:4b"
    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"

    # Pipeline
    chunk_size_tokens: int = Field(default=512, gt=0)
    chunk_overlap_tokens: int = Field(default=64, ge=0)
    retrieve_top_k: int = Field(default=20, gt=0)
    rerank_top_n: int = Field(default=5, gt=0)
    rerank_score_threshold: float = 0.0

    # Paths and logging
    data_dir: Path = Path("data")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @model_validator(mode="after")
    def _check_consistency(self) -> Self:
        if self.chunk_overlap_tokens >= self.chunk_size_tokens:
            raise ValueError("chunk_overlap_tokens must be smaller than chunk_size_tokens")
        if self.rerank_top_n > self.retrieve_top_k:
            raise ValueError("rerank_top_n cannot exceed retrieve_top_k")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings; call get_settings.cache_clear() to reload."""
    return Settings()
