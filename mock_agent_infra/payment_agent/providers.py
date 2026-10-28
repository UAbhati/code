"""Real provider adapter (OpenAI-compatible chat completions, stdlib only)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from payment_agent.model import InvalidModelResponse, Message, ModelResponse, ToolCall


class ProviderError(Exception):
    """Raised on transport or protocol failures from the provider."""


def to_openai_messages(messages: list[Message]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        if m.role == "tool":
            out.append(
                {"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content}
            )
        elif m.role == "assistant" and m.tool_calls:
            out.append(
                {
                    "role": "assistant",
                    "content": m.content or None,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }
                        for tc in m.tool_calls
                    ],
                }
            )
        else:
            out.append({"role": m.role, "content": m.content})
    return out


def to_openai_tools(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            },
        }
        for t in tools or []
    ]


def parse_openai_response(body: dict[str, Any]) -> ModelResponse:
    try:
        message = body["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise InvalidModelResponse(f"Malformed provider response: {exc}") from exc
    calls: list[ToolCall] = []
    for raw in message.get("tool_calls") or []:
        try:
            args = json.loads(raw["function"]["arguments"] or "{}")
            calls.append(
                ToolCall(
                    id=raw["id"], name=raw["function"]["name"], arguments=args
                )
            )
        except (KeyError, json.JSONDecodeError, TypeError) as exc:
            raise InvalidModelResponse(f"Malformed tool call: {exc}") from exc
    return ModelResponse(content=message.get("content") or "", tool_calls=calls)


class OpenAIChatClient:
    """ModelClient backed by an OpenAI-compatible /chat/completions endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ProviderError("OPENAI_API_KEY is not set")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def complete(
        self, messages: list[Message], tools: list[dict[str, Any]] | None = None
    ) -> ModelResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": to_openai_messages(messages),
        }
        if tools:
            payload["tools"] = to_openai_tools(tools)
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                body = json.loads(resp.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderError(f"Provider request failed: {exc}") from exc
        return parse_openai_response(body)
