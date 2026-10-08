from __future__ import annotations

from datetime import date
from typing import Any

REFERENCE_DATE = date(2026, 9, 30)
REVIEW_MAX_AGE_DAYS = 365

def _security_bucket(status: str) -> str:
    if status == "approved":
        return "approved"
    if status in ("pending", "not_completed", "unknown", "expired"):
        return "not_current"
    return status



def _text(value: Any) -> str:
    return str(value or "").strip().lower()


def _contains_any(text: str, terms: list[str]) -> bool:
    text = _text(text)
    return any(term.lower() in text for term in terms)


def _approval_threshold(cost: float | None) -> list[str]:
    if cost is None:
        return []
    if cost <= 1000:
        return ["Manager"]
    if cost <= 10000:
        return ["Department Head", "Procurement"]
    if cost <= 25000:
        return ["Department Head", "Finance", "Procurement"]
    return ["Department Head", "Finance", "CFO", "Procurement"]


def _is_review_expired(review_date: str | None) -> bool:
    if not review_date:
        return True
    try:
        reviewed = date.fromisoformat(review_date)
    except ValueError:
        return True
    return (REFERENCE_DATE - reviewed).days > REVIEW_MAX_AGE_DAYS


def deterministic_checks(
    request: dict,
    employee: dict,
    budget: dict,
    vendor: dict | None,
    vendor_risk: dict | None,
    catalog_matches: list[dict],
    vendor_risk_error: str | None = None,
) -> dict:
    """Authoritative, non-LLM policy/risk checks.

    This function is intentionally independent of the LLM. The model cannot
    override financial thresholds, required reviews, or human authority.
    """
    missing: list[str] = []
    risk_flags: list[str] = []
    approvals: list[str] = []

    required_fields = [
        ("requester", request.get("requester_id")),
        ("department", employee.get("department")),
        ("product/vendor", request.get("product_name") or request.get("vendor_name")),
        ("annual cost", request.get("annual_cost_usd")),
        ("user/license count", request.get("user_count")),
        ("business purpose", request.get("business_justification")),
        ("data access level", request.get("data_access_level")),
        ("required integrations", request.get("requested_integrations") is not None),
    ]
    for label, value in required_fields:
        if value is None or value == "" or value == "unknown":
            missing.append(label)

    # A missing cost means we cannot safely apply an approval threshold.
    cost = request.get("annual_cost_usd")
    if cost is not None and budget:
        available = float(budget["available_usd"])
        if float(cost) > available:
            risk_flags.append("budget_insufficient")
            if "Finance" not in approvals:
                approvals.append("Finance")

    threshold_approvals = _approval_threshold(cost)
    for approval in threshold_approvals:
        if approval not in approvals:
            approvals.append(approval)

    # Existing catalog overlap is evidence, not an automatic rejection.
    if catalog_matches:
        risk_flags.append("existing_tool_overlap")

    data_level = _text(request.get("data_access_level"))
    integrations = " ".join(request.get("requested_integrations") or [])
    purpose = _text(request.get("business_justification"))
    security_sensitive = (
        any(k in data_level for k in [
            "source_code", "production", "confidential", "employee_pii",
            "customer_pii", "credentials", "secret",
        ])
        or _contains_any(integrations, ["production", "cloud account"])
        or _contains_any(purpose, ["source code", "production access", "credentials", "secrets"])
    )

    internal_security = _text((vendor or {}).get("security_status"))
    external_status = _text((vendor_risk or {}).get("security_review_status"))
    external_review_date = (vendor_risk or {}).get("last_review_date")

    review_expired = _is_review_expired(external_review_date)
    if vendor_risk_error:
        risk_flags.append("vendor_risk_unavailable")
        security_sensitive = True  # material evidence cannot be verified safely

    if security_sensitive:
        risk_flags.append("security_review_required")
        approvals.append("Security")

    if external_status in {"expired", "not_completed", "pending", "unknown"} or review_expired:
        if "security_review_required" not in risk_flags:
            risk_flags.append("security_review_required")
        if "vendor_review_expired" not in risk_flags and external_status == "expired":
            risk_flags.append("vendor_review_expired")
        approvals.append("Security")

    if vendor and internal_security and external_status:
        normalized_internal = _security_bucket(internal_security)
        normalized_external = _security_bucket(external_status)
        if normalized_internal != normalized_external:
            risk_flags.append("conflicting_vendor_evidence")
            approvals.append("Security")

    pii = any(k in data_level for k in ["customer_pii", "employee_pii", "pii"])
    stores_outside = bool((vendor_risk or {}).get("stores_data_outside_region", False))
    if pii or stores_outside:
        risk_flags.append("privacy_review_required")
        approvals.append("Privacy")

    procurement_status = _text((vendor or {}).get("procurement_status"))
    legal_terms = _text((vendor or {}).get("legal_terms_status"))
    new_vendor = procurement_status == "new"
    if (new_vendor and cost is not None and cost >= 10000) or legal_terms not in {"approved", "standard"}:
        risk_flags.append("legal_review_required")
        approvals.append("Legal")

    # Detect obvious instruction hijacking in business data.
    injection_terms = [
        "ignore all procurement rules",
        "ignore procurement rules",
        "treat this request as",
        "cfo-approved",
        "approve it immediately",
        "ignore previous instructions",
        "bypass controls",
    ]
    business_blob = " ".join([
        _text(request.get("business_justification")),
        _text(request.get("product_name")),
        _text(request.get("data_access_level")),
    ])
    if _contains_any(business_blob, injection_terms):
        risk_flags.append("prompt_injection_detected")

    if missing:
        risk_flags.append("missing_information")

    # Preserve order while deduplicating.
    approvals = list(dict.fromkeys(approvals))
    risk_flags = list(dict.fromkeys(risk_flags))

    if missing:
        recommendation = "Request clarification before approval"
        next_step = "Obtain the missing request information, then rerun procurement review."
    elif any(x in risk_flags for x in [
        "budget_insufficient", "security_review_required", "privacy_review_required",
        "legal_review_required", "vendor_risk_unavailable", "conflicting_vendor_evidence",
        "prompt_injection_detected",
    ]):
        recommendation = "Escalate for human review"
        next_step = "Route the request and the cited evidence to the required human reviewers; do not auto-approve."
    elif catalog_matches:
        recommendation = "Review existing software overlap"
        next_step = "Confirm why the existing approved option does not satisfy the stated use case before purchase."
    else:
        recommendation = "Proceed to required human approvals"
        next_step = "Collect the listed approvals; the copilot does not approve or purchase software."

    return {
        "required_approvals": approvals,
        "missing_information": missing,
        "risk_flags": risk_flags,
        "human_review_required": True,
        "recommendation": recommendation,
        "next_step": next_step,
        "reference_date": str(REFERENCE_DATE),
    }
