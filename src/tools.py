from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .data_access import (
    get_request,
    load_budgets,
    load_employees,
    load_policy_text,
    load_software_catalog,
    load_vendors,
)
from .vendor_client import get_vendor_risk


@dataclass
class ToolContext:
    """Evidence gathered by deterministic tools before LLM reasoning."""
    request: dict
    employee: dict
    budget: dict
    vendor: dict | None
    catalog_matches: list[dict]
    vendor_risk: dict | None
    vendor_risk_error: str | None
    policy_text: str
    tool_names: list[str] = field(default_factory=list)

    @property
    def tool_calls(self) -> int:
        return len(self.tool_names)


def tool_get_request(request_id: str) -> dict:
    return get_request(request_id)


def tool_get_employee_budget(requester_id: str) -> tuple[dict, dict]:
    employees = load_employees()
    budgets = load_budgets()
    employee_rows = employees[employees["employee_id"] == requester_id]
    if employee_rows.empty:
        raise KeyError(f"Unknown requester: {requester_id}")
    employee = employee_rows.iloc[0].to_dict()
    budget_rows = budgets[budgets["department"] == employee["department"]]
    if budget_rows.empty:
        raise KeyError(f"No budget for department: {employee['department']}")
    return employee, budget_rows.iloc[0].to_dict()


def tool_search_software_catalog(request: dict) -> list[dict]:
    catalog = load_software_catalog()
    product = str(request.get("product_name") or "").lower()
    vendor = str(request.get("vendor_name") or "").lower()
    category = str(request.get("category") or "").lower()
    purpose = str(request.get("business_justification") or "").lower()

    def matches(row: Any) -> bool:
        fields = " ".join([
            str(row["product_name"]).lower(),
            str(row["vendor_name"]).lower(),
            str(row["category"]).lower(),
            str(row["notes"]).lower(),
        ])
        exact = product and product in fields
        same_vendor = vendor and vendor in fields
        same_category = category and category == str(row["category"]).lower()
        use_case_tokens = [t for t in purpose.split() if len(t) >= 5]
        semanticish = sum(t in fields for t in use_case_tokens) >= 2 if use_case_tokens else False
        return bool(exact or same_vendor or same_category or semanticish)

    return [row.to_dict() for _, row in catalog[catalog.apply(matches, axis=1)].iterrows()]


def tool_get_policy() -> str:
    return load_policy_text()


def tool_get_vendor_risk(vendor_name: str) -> tuple[dict | None, str | None]:
    try:
        return get_vendor_risk(vendor_name), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def gather_evidence(request_id: str) -> ToolContext:
    request = tool_get_request(request_id)
    employee, budget = tool_get_employee_budget(request["requester_id"])
    catalog_matches = tool_search_software_catalog(request)
    vendor_rows = load_vendors()
    vendor_match = vendor_rows[vendor_rows["vendor_name"] == request["vendor_name"]]
    vendor = None if vendor_match.empty else vendor_match.iloc[0].to_dict()
    vendor_risk, vendor_error = tool_get_vendor_risk(request["vendor_name"])
    policy_text = tool_get_policy()

    return ToolContext(
        request=request,
        employee=employee,
        budget=budget,
        vendor=vendor,
        catalog_matches=catalog_matches,
        vendor_risk=vendor_risk,
        vendor_risk_error=vendor_error,
        policy_text=policy_text,
        tool_names=[
            "get_request",
            "get_employee_budget",
            "search_software_catalog",
            "get_vendor_risk",
            "get_policy",
        ],
    )


def evidence_for_prompt(ctx: ToolContext) -> dict:
    return {
        "request": ctx.request,
        "requester": ctx.employee,
        "department_budget": ctx.budget,
        "internal_vendor_registry": ctx.vendor,
        "catalog_matches": ctx.catalog_matches,
        "external_vendor_risk": ctx.vendor_risk,
        "vendor_risk_error": ctx.vendor_risk_error,
        "policy": ctx.policy_text,
    }
