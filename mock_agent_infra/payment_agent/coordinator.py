"""Multi-agent coordinator: researcher, deterministic verifier, one revision."""

from __future__ import annotations

from dataclasses import dataclass, field

from payment_agent.agent import Agent, AgentConfig, AgentError, AgentRun
from payment_agent.model import MockModelClient, ModelClient
from payment_agent.tools import ToolRegistry
from payment_agent.verifier import Verification, verify_report

MAX_REVISIONS = 1  # bounded: never loop indefinitely


class ResearcherModelClient(MockModelClient):
    """Same investigation behavior as the mock model; named for clarity."""


@dataclass
class Attempt:
    report: str
    verification: Verification


@dataclass
class InvestigationResult:
    query: str
    attempts: list[Attempt] = field(default_factory=list)

    @property
    def research(self) -> str:
        return self.attempts[-1].report

    @property
    def verification(self) -> Verification:
        return self.attempts[-1].verification

    @property
    def accepted(self) -> bool:
        return self.verification.passed

    @property
    def revisions(self) -> int:
        return len(self.attempts) - 1

    @property
    def final_response(self) -> str:
        verdict = "ACCEPTED" if self.accepted else "NEEDS_REVISION"
        return (
            f"=== Research Findings ===\n{self.research}\n\n"
            f"=== Verifier ===\n{self.verification}\n\n"
            f"=== Revisions: {self.revisions} ===\n"
            f"=== Verdict ===\n{verdict}"
        )


class Coordinator:
    """
    1. Researcher investigates with tools.
    2. Verifier deterministically checks the report against tool evidence.
    3. On FAIL, the report and issues go back to the researcher for ONE
       revision (it may re-query tools), then verification runs again.
    4. The result is returned with its verdict even if it still fails.
    """

    def __init__(
        self,
        researcher_model: ModelClient | None = None,
        tools: ToolRegistry | None = None,
        max_iterations: int = 6,
        max_revisions: int = MAX_REVISIONS,
    ) -> None:
        self.max_revisions = min(max_revisions, MAX_REVISIONS)
        self.researcher = Agent(
            model=researcher_model or ResearcherModelClient(),
            tools=tools or ToolRegistry(),
            config=AgentConfig(
                max_iterations=max_iterations,
                system_prompt=(
                    "You are a payment research specialist. Gather transaction, "
                    "bank, and guideline facts before summarizing. Use the format "
                    "'- Status:', '- Failure code:', '- Bank status:', "
                    "'- Guideline:', and '  * action' lines. Do not claim refunds, "
                    "settlements, or money movement."
                ),
            ),
        )

    def _research(self, prompt: str) -> tuple[str, Verification]:
        try:
            run = self.researcher.run_detailed(prompt)
        except AgentError as exc:
            run = AgentRun(answer=f"Research failed: {exc}")
        return run.answer, verify_report(run.answer, run.tool_results)

    def investigate(self, query: str) -> InvestigationResult:
        result = InvestigationResult(query=query)
        report, verification = self._research(query)
        result.attempts.append(Attempt(report, verification))

        for _ in range(self.max_revisions):
            if verification.passed:
                break
            feedback = "\n".join(f"- {i}" for i in verification.issues)
            report, verification = self._research(
                f"{query}\n\nYour previous report:\n{report}\n\n"
                f"The verifier found these problems:\n{feedback}\n\n"
                "Re-check the evidence with tools as needed and return a "
                "corrected report."
            )
            result.attempts.append(Attempt(report, verification))
        return result
