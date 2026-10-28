"""Unit tests for the bounded agent loop."""

from __future__ import annotations

import unittest

from payment_agent.agent import Agent, AgentConfig, AgentError
from payment_agent.model import Message, ModelResponse, MockModelClient, ToolCall
from payment_agent.tools import ToolRegistry


class ScriptedModel:
    """Returns predetermined responses in order."""

    def __init__(self, responses: list[ModelResponse]) -> None:
        self._responses = list(responses)
        self.calls = 0

    def complete(self, messages: list[Message], tools=None) -> ModelResponse:
        self.calls += 1
        if not self._responses:
            return ModelResponse(content="fallback")
        return self._responses.pop(0)


class AgentSuccessTests(unittest.TestCase):
    def test_full_investigation_success(self) -> None:
        agent = Agent(model=MockModelClient())
        answer = agent.run("Please investigate TXN101")
        self.assertIn("TXN101", answer)
        self.assertIn("INSUFFICIENT_FUNDS", answer)
        self.assertIn("First National", answer)
        self.assertIn("Recommended actions", answer)

    def test_pending_transaction(self) -> None:
        agent = Agent(model=MockModelClient())
        answer = agent.run("Check TXN102")
        self.assertIn("TXN102", answer)
        self.assertIn("pending", answer.lower())

    def test_missing_txn_id_final_answer(self) -> None:
        agent = Agent(model=MockModelClient())
        answer = agent.run("Why did my payment fail?")
        self.assertIn("transaction id", answer.lower())


class AgentFailureTests(unittest.TestCase):
    def test_unknown_tool_is_reported_and_loop_continues(self) -> None:
        model = ScriptedModel(
            [
                ModelResponse(
                    tool_calls=[
                        ToolCall(id="1", name="does_not_exist", arguments={})
                    ]
                ),
                ModelResponse(content="Handled unknown tool gracefully."),
            ]
        )
        agent = Agent(model=model)
        answer = agent.run("investigate something")
        self.assertEqual(answer, "Handled unknown tool gracefully.")
        self.assertEqual(model.calls, 2)

    def test_invalid_arguments_do_not_crash(self) -> None:
        model = ScriptedModel(
            [
                ModelResponse(
                    tool_calls=[
                        ToolCall(
                            id="1",
                            name="lookup_transaction",
                            arguments={},  # missing transaction_id
                        )
                    ]
                ),
                ModelResponse(content="Invalid args were handled."),
            ]
        )
        agent = Agent(model=model)
        answer = agent.run("bad args")
        self.assertEqual(answer, "Invalid args were handled.")

    def test_max_iterations_exhausted(self) -> None:
        forever_tools = ModelResponse(
            tool_calls=[
                ToolCall(
                    id="loop",
                    name="lookup_transaction",
                    arguments={"transaction_id": "TXN101"},
                )
            ]
        )
        model = ScriptedModel([forever_tools, forever_tools, forever_tools])
        agent = Agent(model=model, config=AgentConfig(max_iterations=2))
        with self.assertRaises(AgentError) as ctx:
            agent.run("TXN101")
        self.assertIn("maximum iterations", str(ctx.exception).lower())

    def test_transaction_not_found_path(self) -> None:
        agent = Agent(model=MockModelClient())
        answer = agent.run("Investigate TXN999")
        self.assertIn("Could not investigate", answer)
        self.assertIn("not found", answer.lower())

    def test_empty_response_is_rejected(self) -> None:
        agent = Agent(model=ScriptedModel([ModelResponse(content="  ")]))
        with self.assertRaises(AgentError) as ctx:
            agent.run("x")
        self.assertIn("invalid model response", str(ctx.exception).lower())

    def test_model_exception_becomes_agent_error(self) -> None:
        class Boom:
            def complete(self, messages, tools=None):
                raise ConnectionError("down")

        with self.assertRaises(AgentError) as ctx:
            Agent(model=Boom()).run("x")
        self.assertIn("down", str(ctx.exception))

    def test_deadline_enforced(self) -> None:
        agent = Agent(
            model=ScriptedModel([ModelResponse(content="hi")]),
            config=AgentConfig(deadline_seconds=0),
        )
        with self.assertRaises(AgentError) as ctx:
            agent.run("x")
        self.assertIn("deadline", str(ctx.exception).lower())

    def test_tool_result_with_semicolons_survives(self) -> None:
        import json

        from payment_agent.tools import ToolResult, encode_tool_result

        result = ToolResult("t", True, {"note": "a;b=c;ok=false"})
        self.assertEqual(
            json.loads(encode_tool_result(result))["content"]["note"], "a;b=c;ok=false"
        )


if __name__ == "__main__":
    unittest.main()
