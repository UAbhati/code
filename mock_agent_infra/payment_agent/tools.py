"""Tool definitions, validation, and registry for payment investigation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable

from payment_agent import data


_JSON_TYPES: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
}


@dataclass(frozen=True)
class ToolSpec:
    """A tool plus its JSON-schema style argument definition.

    ``properties`` maps argument name -> {"type": ..., "description": ...,
    optional "pattern"/"enum"}. Unknown arguments are rejected.
    """

    name: str
    description: str
    properties: dict[str, dict[str, Any]]
    required: tuple[str, ...]
    handler: Callable[[dict[str, Any]], dict[str, Any]]

    @property
    def required_args(self) -> tuple[str, ...]:
        return self.required

    def json_schema(self) -> dict[str, Any]:
        """Provider-ready schema for the tool's parameters."""
        return {
            "type": "object",
            "properties": self.properties,
            "required": list(self.required),
            "additionalProperties": False,
        }


@dataclass
class ToolResult:
    tool_name: str
    ok: bool
    content: dict[str, Any] | str
    error: str | None = None


class ToolError(Exception):
    """Raised when a tool cannot complete successfully."""


def lookup_transaction(args: dict[str, Any]) -> dict[str, Any]:
    txn_id = args["transaction_id"]
    txn = data.TRANSACTIONS.get(txn_id)
    if txn is None:
        raise ToolError(f"Transaction not found: {txn_id}")
    return dict(txn)


def lookup_bank_status(args: dict[str, Any]) -> dict[str, Any]:
    bank_ref = args["bank_ref"]
    status = data.BANK_STATUSES.get(bank_ref)
    if status is None:
        raise ToolError(f"Bank status not found: {bank_ref}")
    return dict(status)


def lookup_payment_guideline(args: dict[str, Any]) -> dict[str, Any]:
    topic = args["topic"]
    guideline = data.GUIDELINES.get(topic)
    if guideline is None:
        raise ToolError(f"Guideline not found: {topic}")
    return dict(guideline)


DEFAULT_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="lookup_transaction",
        description="Look up a payment transaction by its id (e.g. TXN101).",
        properties={
            "transaction_id": {
                "type": "string",
                "pattern": r"^TXN\d+$",
                "description": "Transaction id such as TXN101.",
            }
        },
        required=("transaction_id",),
        handler=lookup_transaction,
    ),
    ToolSpec(
        name="lookup_bank_status",
        description="Look up bank rail status by bank_ref (e.g. BR-7788).",
        properties={
            "bank_ref": {"type": "string", "description": "Bank reference."}
        },
        required=("bank_ref",),
        handler=lookup_bank_status,
    ),
    ToolSpec(
        name="lookup_payment_guideline",
        description="Look up investigation guidelines by failure code or PENDING.",
        properties={
            "topic": {
                "type": "string",
                "description": "Failure code (e.g. INSUFFICIENT_FUNDS) or PENDING.",
            }
        },
        required=("topic",),
        handler=lookup_payment_guideline,
    ),
)


def encode_tool_result(result: ToolResult) -> str:
    """Serialize a tool result as JSON for the tool-role message."""
    return json.dumps(
        {
            "tool_name": result.tool_name,
            "ok": result.ok,
            "content": result.content,
            "error": result.error,
        },
        default=str,
    )


class ToolRegistry:
    """Registers tools and executes them with argument validation."""

    def __init__(self, tools: tuple[ToolSpec, ...] | None = None) -> None:
        self._tools: dict[str, ToolSpec] = {}
        selected = DEFAULT_TOOLS if tools is None else tools
        for tool in selected:
            self.register(tool)

    def register(self, tool: ToolSpec) -> None:
        self._tools[tool.name] = tool

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.json_schema(),
            }
            for t in self._tools.values()
        ]

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)

    def validate_args(self, tool: ToolSpec, args: dict[str, Any]) -> str | None:
        if not isinstance(args, dict):
            return "Arguments must be a dictionary"
        missing = [key for key in tool.required if key not in args]
        if missing:
            return f"Missing required arguments: {', '.join(missing)}"
        unexpected = [key for key in args if key not in tool.properties]
        if unexpected:
            return f"Unexpected arguments: {', '.join(sorted(unexpected))}"
        empty = [
            key for key in tool.required if args[key] is None or args[key] == ""
        ]
        if empty:
            return f"Empty required arguments: {', '.join(empty)}"
        for key, value in args.items():
            schema = tool.properties[key]
            expected = _JSON_TYPES.get(schema.get("type", "string"), (str,))
            # bool is an int subclass; don't let True pass as an integer
            if not isinstance(value, expected) or (
                isinstance(value, bool) and bool not in expected
            ):
                return f"Argument '{key}' must be of type {schema.get('type')}"
            if "enum" in schema and value not in schema["enum"]:
                return f"Argument '{key}' must be one of {schema['enum']}"
            pattern = schema.get("pattern")
            if pattern and not re.match(pattern, value):
                return f"Argument '{key}' has invalid format"
        return None

    def execute(self, name: str, args: dict[str, Any]) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(
                tool_name=name,
                ok=False,
                content={},
                error=f"Unknown tool: {name}",
            )

        validation_error = self.validate_args(tool, args)
        if validation_error:
            return ToolResult(
                tool_name=name,
                ok=False,
                content={},
                error=validation_error,
            )

        try:
            content = tool.handler(args)
            return ToolResult(tool_name=name, ok=True, content=content)
        except ToolError as exc:
            return ToolResult(tool_name=name, ok=False, content={}, error=str(exc))
        except Exception as exc:  # noqa: BLE001 - surface unexpected tool failures
            return ToolResult(
                tool_name=name,
                ok=False,
                content={},
                error=f"Tool failure: {exc}",
            )
