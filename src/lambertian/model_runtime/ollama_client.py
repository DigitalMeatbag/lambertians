"""Ollama HTTP client for inference and embeddings. IS-6.3 step 9, IS-7.3."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from lambertian.configuration.universe_config import Config
from lambertian.contracts.tool_records import ToolIntent

_log = logging.getLogger(__name__)


class OllamaInferenceError(Exception):
    """Model inference failed — timeout or connection error."""


class OllamaClient:
    """Ollama HTTP client for inference and embeddings."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = httpx.Client(
            timeout=float(config.model.request_timeout_seconds)
        )

    def chat(
        self,
        messages: list[dict[str, object]],  # object: heterogeneous message fields
        tools: list[dict[str, object]],  # object: Ollama function calling schema
    ) -> tuple[str, list[ToolIntent]]:
        """Submit chat request. Returns (response_text, tool_intents).

        Raises OllamaInferenceError on timeout or connection failure.
        HTTP errors are returned as (error text, []) not raised.
        """
        url = f"{self._config.model.endpoint_url}/api/chat"
        payload: dict[str, object] = {
            "model": self._config.model.name,
            "messages": messages,
            "tools": tools,
            "stream": False,
        }
        try:
            response = self._client.post(url, json=payload)
        except httpx.TimeoutException as exc:
            raise OllamaInferenceError(f"Inference timeout: {exc}") from exc
        except httpx.ConnectError as exc:
            raise OllamaInferenceError(f"Connection error: {exc}") from exc

        if not response.is_success:
            return f"HTTP {response.status_code}: {response.text}", []

        raw: Any = response.json()  # Any: JSON parse boundary
        message: Any = raw.get("message", {})
        response_text: str = str(message.get("content", ""))
        raw_tool_calls: Any = message.get("tool_calls", [])

        tool_intents: list[ToolIntent] = []
        for tc in raw_tool_calls:
            func: Any = tc.get("function", {})
            tool_name: str = str(func.get("name", ""))
            arguments: dict[str, object] = func.get("arguments", {})
            tool_intents.append(
                ToolIntent(
                    tool_name=tool_name,
                    arguments=arguments,
                    raw=json.dumps(tc),
                )
            )

        return response_text, tool_intents

    def embed(self, text: str) -> list[float]:
        """Get embedding vector for text."""
        url = f"{self._config.model.endpoint_url}/api/embeddings"
        payload: dict[str, object] = {
            "model": self._config.memory.embedding_model,
            "prompt": text,
        }
        try:
            response = self._client.post(url, json=payload)
        except httpx.TimeoutException as exc:
            raise OllamaInferenceError(f"Embedding timeout: {exc}") from exc
        except httpx.ConnectError as exc:
            raise OllamaInferenceError(f"Embedding connection error: {exc}") from exc

        response.raise_for_status()
        raw: Any = response.json()  # Any: JSON parse boundary
        return [float(x) for x in raw.get("embedding", [])]

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()
