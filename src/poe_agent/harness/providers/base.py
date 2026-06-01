# ROLE: harness — LLM and embedding provider interfaces.

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, system: str, user: str) -> tuple[str, dict[str, int]]:
        """Return (text, token_counts)."""


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...
