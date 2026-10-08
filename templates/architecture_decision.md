# Architecture Decision Memo

> Fill the numeric fields from `evals/results_single.csv` and `evals/results_staged.csv` after
> running the same public evaluation set on both architectures. Keep this memo under 500 words.

## Decision

**Ship:** `<single agent | staged / 2-agent>`

## Evidence

| Metric | Single | Staged / 2-agent |
|---|---:|---:|
| Public cases meeting minimum expectations | `<run>` | `<run>` |
| Avg latency | `<run>` | `<run>` |
| Avg LLM calls | `<run>` | `<run>` |
| Avg tool calls | `<run>` | `<run>` |
| Notable policy/grounding failures | `<run>` | `<run>` |

## Trade-offs

The single-agent design has one model reasoning pass, lower latency and less orchestration.
The staged design adds a second reasoning pass and therefore increases latency/cost, but
can separate evidence analysis from final decision review. Both architectures share the same
deterministic policy engine and evidence tools.

## Risks / limitations

Validate model reliability on hidden requests, provider outages, unusual overlap cases,
conflicting vendor records, and adversarial business text. The mock dataset is synthetic,
so production deployment would also need access controls, audit logging, real procurement
integrations, privacy review, and stronger observability.

## Why this is the right MVP

The shipped architecture should be the simplest one that matches or exceeds the staged
variant on correctness and grounding while reducing latency and LLM calls. If staged is
materially more reliable on hidden-style cases, prefer it despite the extra call.
