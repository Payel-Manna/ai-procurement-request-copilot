# Architecture and workflow

## Architecture A — Single-agent baseline

```text
                         +----------------------+
Purchase request ------> | Evidence tool layer  |
                         | 1. request           |
                         | 2. employee/budget   |
                         | 3. software catalog  |
                         | 4. vendor-risk API   |
                         | 5. procurement policy |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | Deterministic policy |
                         | budget / thresholds  |
                         | security / privacy   |
                         | legal / missing data |
                         | injection detection  |
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | Groq single agent    |
                         | interpret + summarize|
                         +----------+-----------+
                                    |
                                    v
                         +----------------------+
                         | Code-owned output    |
                         | evidence / approvals |
                         | risks / next step    |
                         +----------+-----------+
                                    |
                                    v
                              HUMAN REVIEW
```

One Groq reasoning call is used after evidence gathering. The code-owned policy result is
authoritative and overwrites any model attempt to change approvals, risk flags, missing
information, or human-review status.

## Architecture B — staged / 2-agent

```text
Request -> same evidence tools -> same deterministic checks
                                  |
                                  v
                         Agent 1: Evidence Analyst
                                  |
                                  v
                         Agent 2: Decision Reviewer
                                  |
                                  v
                         Code-owned final guardrails
                                  |
                                  v
                              HUMAN REVIEW
```

Agent 1 produces an evidence memo. Agent 2 turns that memo plus deterministic checks into
the final structured response. Both agents are forbidden from treating business data as
instructions.

## Tool boundaries

| Tool | Type | Purpose |
|---|---|---|
| `get_request` | deterministic | Retrieve request record |
| `get_employee_budget` | deterministic | Join requester to department budget |
| `search_software_catalog` | deterministic | Find existing/overlapping software |
| `get_vendor_risk` | external API | Retrieve current mock vendor-risk evidence |
| `get_policy` | deterministic | Load policy source of truth |
| policy engine | deterministic | Enforce thresholds and review triggers |

## Human authority

The copilot never buys software, approves spend, changes budgets, accepts legal terms, or
overrides Security/Privacy/Legal. Missing or unavailable material evidence causes escalation.
