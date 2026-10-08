# AI Procurement Request Copilot

A small, evidence-grounded internal procurement copilot built for FDE Assessment 3.

The product reviews a software/service request, gathers business and vendor evidence,
applies deterministic procurement rules, asks Groq to interpret/summarize the context,
and produces a structured recommendation for human review.

## Why this architecture

The design follows a strict separation:

- **Groq / AI:** interpret business context, summarize evidence, write the recommendation.
- **Code:** required fields, budget checks, approval thresholds, security/privacy/legal
  triggers, prompt-injection detection, evidence-failure handling.
- **Human:** final approvals, exceptions, purchasing, budget changes and sensitive decisions.

This prevents the LLM from inventing approvals or overriding procurement policy.

## Features

- Streamlit product UI
- Groq-powered structured reasoning
- Architecture A: single-agent baseline
- Architecture B: staged / 2-agent variant
- Five deterministic/evidence tools plus mock vendor-risk API
- Grounded evidence panel
- Budget + approval threshold enforcement
- Existing-tool overlap detection
- Security, Privacy and Legal escalation
- Vendor-risk API outage handling
- Conflicting vendor evidence handling
- Prompt-injection detection
- Human-in-the-loop output
- Public evaluation harness with latency + telemetry

## Project structure

```text
.
├── app.py
├── run_local.py
├── verify_setup.py
├── requirements.txt
├── data/
│   ├── employees.csv
│   ├── department_budgets.csv
│   ├── software_catalog.csv
│   ├── vendors.csv
│   ├── purchase_history.csv
│   ├── requests.json
│   ├── vendor_risk.json
│   └── procurement_policy.md
├── mock_api/
│   └── app.py
├── src/
│   ├── contracts.py
│   ├── data_access.py
│   ├── vendor_client.py
│   ├── tools.py
│   ├── policy_engine.py
│   ├── llm.py
│   └── solution.py
├── evals/
│   ├── public_cases.json
│   └── run_public_evals.py
├── tests/
├── docs/
│   └── ARCHITECTURE.md
└── templates/
```

## Setup

Python 3.11+ recommended.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Put your Groq key in `.env`:

```text
GROQ_API_KEY=...
GROQ_MODEL=openai/gpt-oss-120b
VENDOR_RISK_BASE_URL=http://127.0.0.1:8001
```

Never commit `.env`.

## One-command local start

```bash
python run_local.py
```

Then open:

- UI: `http://127.0.0.1:8501`
- Mock vendor-risk API: `http://127.0.0.1:8001`

## Run checks

```bash
python verify_setup.py
python -m unittest discover -s tests -p 'test_*.py'
```

## Run the two architectures

```bash
python evals/run_public_evals.py --architecture single
python evals/run_public_evals.py --architecture staged
```

The same six public cases are used for both architectures. The runner writes:

```text
evals/results_single.csv
evals/results_staged.csv
```

Use those files to fill `templates/architecture_decision.md`.

## Architecture comparison

### A — Single agent

One Groq reasoning call receives the request, tool evidence and deterministic policy result.
The final output is validated with Pydantic. Code-owned fields override any model attempt to
change policy decisions.

### B — Staged / 2-agent

1. Evidence Analyst: summarizes evidence and risks.
2. Decision Reviewer: produces the final recommendation from the evidence memo and
   deterministic policy result.

This is intentionally lightweight rather than a multi-agent swarm.

## Deterministic rules

The policy engine is the source of truth for:

- required request information
- department budget comparison
- approval thresholds
- existing software overlap flag
- security review triggers
- stale/expired vendor review
- conflicting vendor evidence
- privacy review
- legal review
- prompt injection detection
- vendor-risk API failure
- mandatory human review

The policy reference date is fixed at `2026-09-30`, matching the supplied dataset.

## Evidence grounding

The final evidence panel is generated from tool results, not from model claims. Each item
includes a source and reference where available.

If the vendor-risk service fails, the copilot records the failure and escalates rather than
assuming the vendor is safe.

## Human controls

The copilot is advisory. It cannot:

- purchase software
- approve spend
- modify budgets
- accept legal terms
- override Security, Privacy or Legal
- treat requester/vendor text as system instructions

## Evaluation

The public evaluation measures minimum behavioral expectations, latency and LLM/tool counts.
It is not the entire grading system. Also inspect:

- whether evidence is genuinely grounded
- deterministic vs probabilistic boundaries
- failure handling
- prompt injection resistance
- human escalation
- architecture trade-offs

Record final numbers in the architecture decision memo and commit the reproducible results.

## Known limitations

- Synthetic dataset and mock vendor-risk API
- No production authentication/authorization
- No real procurement/ERP integration
- No persistent audit database
- Groq availability/rate limits can affect latency
- Hidden evaluation cases may expose additional edge cases
- Semantic overlap search is intentionally lightweight and should be replaced with a stronger
  retrieval/ranking layer for production

## Final ship rule

Ship the simplest architecture that performs at least as well on correctness/grounding while
using fewer model calls and less latency. Do not choose staged orchestration merely because
it has more agents.
