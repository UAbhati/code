# AI Payment Investigation Agent

Minimal Python project that investigates mock payment failures with a tool-using agent loop. No external API keys or databases required.

## Features

- In-memory transactions, bank statuses, and payment guidelines
- Tools: `lookup_transaction`, `lookup_bank_status`, `lookup_payment_guideline`
- `ModelClient` protocol with a deterministic `MockModelClient`
- Bounded agent loop with argument validation and error handling
- Optional multi-agent coordinator (researcher + verifier)

## Layout

```
payment_agent/
  data.py          # mock payment dataset
  tools.py         # tool handlers + registry
  model.py         # ModelClient interface + mock
  providers.py     # OpenAI-compatible adapter
  verifier.py      # deterministic claim checks
  agent.py         # bounded think/act loop
  coordinator.py   # researcher + verifier orchestration
main.py            # CLI entry point
tests/             # unit tests
```

## Run

```bash
# Single-agent investigation (default)
python main.py "Please investigate TXN101"

# Researcher + verifier
python main.py --mode multi "Please investigate TXN101"

# Other sample ids: TXN102 (pending), TXN103 (compliance hold)
```

## Test

```bash
python -m unittest discover -s tests -v
```

## Design notes

- **Model**: `ModelClient.complete(messages, tools)` receives JSON-schema tool definitions and returns either structured `ToolCall`s or a non-empty final answer; empty responses are rejected. `MockModelClient` is a *scripted* stand-in (fixed lookup order) and does not demonstrate dynamic tool choice; `providers.OpenAIChatClient` is a real OpenAI-compatible adapter (`--provider openai`, needs `OPENAI_API_KEY`, untested against the live API here). What the mock demonstrates is the orchestration.
- **Tool results** are JSON (`encode_tool_result`) with tool-call ids preserved.
- **Tool validation** is per-tool and strict: required fields, no unexpected fields, type/format checks.
- **Failure policy**: model exceptions, invalid responses, iteration limit and wall-clock deadline all raise `AgentError`; the coordinator turns that into a failed report.
- **Verifier** (`verifier.py`) is deterministic: it checks status, failure code, bank status, guideline summary and each recommended action against tool evidence, and flags unsupported refund/settlement/money-movement claims. It depends on the report line format requested in the researcher prompt.
- **Coordinator** allows exactly one revision: verifier issues go back to the researcher, which re-queries tools; the result is returned with its verdict even if it still fails.
- Transaction ids use the form `TXN101` (`TXN-101` is also accepted by the mock and normalized).
