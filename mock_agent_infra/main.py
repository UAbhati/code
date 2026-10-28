#!/usr/bin/env python3
"""Runnable entry point for the AI Payment Investigation Agent."""

from __future__ import annotations

import argparse
import sys

from payment_agent.agent import Agent, AgentError
from payment_agent.coordinator import Coordinator
from payment_agent.model import MockModelClient
from payment_agent.providers import ProviderError
from payment_agent.tools import ToolRegistry


def build_model(provider: str):
    if provider == "openai":
        from payment_agent.providers import OpenAIChatClient

        return OpenAIChatClient()
    return MockModelClient()


def run_single_agent(query: str, provider: str = "mock") -> str:
    agent = Agent(model=build_model(provider), tools=ToolRegistry())
    return agent.run(query)


def run_coordinator(query: str, provider: str = "mock") -> str:
    coordinator = Coordinator(researcher_model=build_model(provider))
    return coordinator.investigate(query).final_response


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI Payment Investigation Agent (mock model, in-memory data)."
    )
    parser.add_argument(
        "query",
        nargs="?",
        default="Please investigate why TXN101 failed",
        help="Investigation question (include a TXN id)",
    )
    parser.add_argument(
        "--mode",
        choices=("single", "multi"),
        default="single",
        help="single = one agent; multi = researcher + verifier coordinator",
    )
    parser.add_argument(
        "--provider",
        choices=("mock", "openai"),
        default="mock",
        help="mock = scripted offline model; openai = real model (OPENAI_API_KEY)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.mode == "multi":
            print(run_coordinator(args.query, args.provider))
        else:
            print(run_single_agent(args.query, args.provider))
        return 0
    except (AgentError, ProviderError) as exc:
        print(f"Agent error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
