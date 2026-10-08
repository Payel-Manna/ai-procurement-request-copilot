# Submission runbook

## 1. Clean setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# edit .env and add GROQ_API_KEY
python verify_setup.py
```

## 2. Local product

```bash
python run_local.py
```

Open `http://127.0.0.1:8501`.

Test at least:

- REQ-1001: low-value request
- REQ-1002: existing alternative + new vendor
- REQ-1003: source-code access
- REQ-1005: budget shortfall + sensitive vendor
- REQ-1006: missing information + prompt injection
- REQ-1009: vendor-risk outage

## 3. Automated evaluation

```bash
python evals/run_public_evals.py --architecture single
python evals/run_public_evals.py --architecture staged
```

Keep both CSV outputs for the submission/evidence.

## 4. Architecture decision

Calculate:

- pass count
- average latency
- average LLM calls
- average tool calls
- manually observed grounding/policy failures

Then fill `templates/architecture_decision.md`.

Do not fabricate performance numbers. The decision must follow the measured evidence.

## 5. Final checks

```bash
python -m unittest discover -s tests -p 'test_*.py'
git status
git diff
```

Confirm `.env` is ignored and no API key appears in tracked files.

## 6. GitHub

Suggested repository name:

`ai-procurement-request-copilot`

Suggested short description:

`Evidence-grounded AI procurement copilot with Groq, deterministic policy checks, human review, and single-vs-staged architecture evaluation.`
