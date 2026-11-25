"""
Thin abstraction over two zero-cost LLM options:

- "gemini": Google's Gemini API, generous free tier (https://ai.google.dev/)
- "ollama": a fully local, fully free model served by Ollama

Both expose the same .generate(prompt) -> str method so the rest of the
app never needs to know which provider is active. Switch with the
LLM_PROVIDER env var.
"""
from __future__ import annotations

import abc

from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


class LLMClient(abc.ABC):
    @abc.abstractmethod
    def generate(self, prompt: str, *, temperature: float = 0.8) -> str:
        raise NotImplementedError


class GeminiClient(LLMClient):
    def __init__(self):
        if not settings.gemini_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Get a free key at https://ai.google.dev/ "
                "or switch LLM_PROVIDER=ollama to run fully locally."
            )
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)
        self._model = genai.GenerativeModel(settings.gemini_model)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def generate(self, prompt: str, *, temperature: float = 0.8) -> str:
        response = self._model.generate_content(
            prompt,
            generation_config={"temperature": temperature},
        )
        return (response.text or "").strip()


class OllamaClient(LLMClient):
    def __init__(self):
        import ollama

        self._ollama = ollama
        self._host = settings.ollama_host
        self._model = settings.ollama_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    def generate(self, prompt: str, *, temperature: float = 0.8) -> str:
        client = self._ollama.Client(host=self._host)
        response = client.generate(
            model=self._model,
            prompt=prompt,
            options={"temperature": temperature},
        )
        return (response.get("response") or "").strip()


def get_llm_client(provider: str | None = None) -> LLMClient:
    provider = (provider or settings.llm_provider).lower()
    if provider == "gemini":
        return GeminiClient()
    if provider == "ollama":
        return OllamaClient()
    raise ValueError(f"Unknown LLM_PROVIDER '{provider}'. Use 'gemini' or 'ollama'.")
