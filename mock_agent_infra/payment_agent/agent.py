"""Bounded agent loop with tool execution and error handling."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from payment_agent.model import (
    InvalidModelResponse,
    Message,
    ModelClient,
)
from payment_agent.tools import ToolRegistry, ToolResult, encode_tool_result


class AgentError(Exception):
    """Raised when the agent cannot produce a final answer."""


@dataclass
class AgentConfig:
    max_iterations: int = 6
    # Overall wall-clock budget, checked before every model call. A single
    # in-flight call is bounded by the client's own timeout.
    deadline_seconds: float = 60.0
    system_prompt: str = (
        "You are a payment investigation agent. Use tools to look up "
        "transactions, bank status, and guidelines, then explain findings. "
        "Only state facts returned by tools."
    )


@dataclass
class AgentRun:
    """Final answer plus the tool evidence gathered while producing it."""

    answer: str
    tool_results: list[ToolResult] = field(default_factory=list)


class Agent:
    """
    Runs a bounded think -> tool-call -> observe loop.

    Failure policy: any model exception, invalid (empty) response, exhausted
    iteration budget, or missed deadline raises ``AgentError``. Tool failures
    are not fatal; they are returned to the model as ``ok: false`` results.
    """

    def __init__(
        self,
        model: ModelClient,
        tools: ToolRegistry | None = None,
        config: AgentConfig | None = None,
    ) -> None:
        self.model = model
        self.tools = tools or ToolRegistry()
        self.config = config or AgentConfig()

    def run(self, query: str) -> str:
        return self.run_detailed(query).answer

    def run_detailed(self, query: str) -> AgentRun:
        messages: list[Message] = [
            Message(role="system", content=self.config.system_prompt),
            Message(role="user", content=query),
        ]
        tool_schemas = self.tools.list_tools()
        results: list[ToolResult] = []
        deadline = time.monotonic() + self.config.deadline_seconds

        for _ in range(self.config.max_iterations):
            if time.monotonic() >= deadline:
                raise AgentError(
                    f"Deadline of {self.config.deadline_seconds}s exceeded."
                )
            try:
                response = self.model.complete(messages, tool_schemas)
                response.validate()
            except InvalidModelResponse as exc:
                raise AgentError(f"Invalid model response: {exc}") from exc
            except Exception as exc:  # noqa: BLE001 - defined failure policy
                raise AgentError(f"Model call failed: {exc}") from exc

            if response.is_final:
                return AgentRun(answer=response.content, tool_results=results)

            messages.append(
                Message(
                    role="assistant",
                    content=response.content,
                    tool_calls=list(response.tool_calls),
                )
            )
            for tool_call in response.tool_calls:
                result = self.tools.execute(tool_call.name, tool_call.arguments)
                results.append(result)
                messages.append(
                    Message(
                        role="tool",
                        content=encode_tool_result(result),
                        tool_call_id=tool_call.id,
                    )
                )

        raise AgentError(
            f"Exceeded maximum iterations ({self.config.max_iterations}) "
            "without a final answer."
        )
