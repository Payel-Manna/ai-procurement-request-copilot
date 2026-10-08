from __future__ import annotations

from .contracts import ProcurementDecision, RunTelemetry
from .policy_engine import deterministic_checks
from .tools import gather_evidence

from .llm import single_agent, staged_agent



def _grounded_evidence(ctx, deterministic) -> list:
    """Create evidence items only from tool results; never from model-generated facts."""
    from .contracts import EvidenceItem

    evidence = [
        EvidenceItem(
            source="request_data",
            finding=(
                f"{ctx.request['product_name']} requested from {ctx.request['vendor_name']} "
                f"for {ctx.employee['department']}; annual cost={ctx.request.get('annual_cost_usd')!r}, "
                f"users={ctx.request.get('user_count')!r}, data_access={ctx.request.get('data_access_level')!r}."
            ),
            reference=ctx.request["request_id"],
        ),
        EvidenceItem(
            source="department_budget",
            finding=(
                f"{ctx.employee['department']} has ${ctx.budget['available_usd']} available "
                f"software budget in the 2026-09-30 snapshot."
            ),
            reference=ctx.employee["department"],
        ),
    ]
    if ctx.catalog_matches:
        names = ", ".join(str(x["product_name"]) for x in ctx.catalog_matches[:5])
        evidence.append(EvidenceItem(
            source="software_catalog",
            finding=f"Potential existing/overlapping approved software: {names}.",
            reference="software_catalog.csv",
        ))
    if ctx.vendor:
        evidence.append(EvidenceItem(
            source="vendor_registry",
            finding=(
                f"Internal vendor status={ctx.vendor.get('procurement_status')}, "
                f"security={ctx.vendor.get('security_status')}, "
                f"security_review_date={ctx.vendor.get('security_review_date')!r}, "
                f"legal_terms={ctx.vendor.get('legal_terms_status')}."
            ),
            reference=ctx.vendor.get("vendor_id"),
        ))
    if ctx.vendor_risk:
        evidence.append(EvidenceItem(
            source="vendor_risk_api",
            finding=(
                f"External risk service reports security_review_status="
                f"{ctx.vendor_risk.get('security_review_status')}, "
                f"risk_level={ctx.vendor_risk.get('risk_level')}, "
                f"last_review_date={ctx.vendor_risk.get('last_review_date')!r}, "
                f"outside_region={ctx.vendor_risk.get('stores_data_outside_region')}."
            ),
            reference="vendor-risk API",
        ))
    elif ctx.vendor_risk_error:
        evidence.append(EvidenceItem(
            source="vendor_risk_api",
            finding=f"Vendor-risk evidence could not be verified: {ctx.vendor_risk_error}",
            reference="vendor-risk API",
        ))

    if deterministic["missing_information"]:
        evidence.append(EvidenceItem(
            source="deterministic_policy_checks",
            finding="Missing required information: " + ", ".join(deterministic["missing_information"]),
            reference="procurement_policy.md §1",
        ))
    if deterministic["risk_flags"]:
        evidence.append(EvidenceItem(
            source="deterministic_policy_checks",
            finding="Policy/risk flags: " + ", ".join(deterministic["risk_flags"]),
            reference="procurement_policy.md",
        ))
    evidence.append(EvidenceItem(
        source="deterministic_policy_checks",
        finding="Required human approvals: " + (", ".join(deterministic["required_approvals"]) or "none identified"),
        reference="procurement_policy.md §4-§8",
    ))
    return evidence


def handle_request(request_id: str, architecture: str = "single") -> ProcurementDecision:
    """Run one of the two assessment architectures.

    Both architectures share the same evidence tools and deterministic policy engine.
    Architecture A uses one Groq reasoning call; Architecture B uses two lightweight
    Groq stages: evidence analyst -> decision reviewer.
    """
    if architecture not in {"single", "staged"}:
        raise ValueError("architecture must be 'single' or 'staged'")

    telemetry = RunTelemetry(llm_calls=0, tool_calls=0, tool_names=[])

    ctx = gather_evidence(request_id)
    telemetry.tool_calls = ctx.tool_calls
    telemetry.tool_names = ctx.tool_names

    deterministic = deterministic_checks(
        request=ctx.request,
        employee=ctx.employee,
        budget=ctx.budget,
        vendor=ctx.vendor,
        vendor_risk=ctx.vendor_risk,
        catalog_matches=ctx.catalog_matches,
        vendor_risk_error=ctx.vendor_risk_error,
    )

    if architecture == "single":
        decision = single_agent(ctx, deterministic, telemetry)
    else:
        decision = staged_agent(ctx, deterministic, telemetry)

    # Evidence and policy outputs are code-owned, not model-owned.
    decision.evidence = _grounded_evidence(ctx, deterministic)
    decision.required_approvals = deterministic["required_approvals"]
    decision.missing_information = deterministic["missing_information"]
    decision.risk_flags = deterministic["risk_flags"]
    decision.human_review_required = True
    decision.next_step = deterministic["next_step"]
    decision.telemetry = telemetry
    return decision
