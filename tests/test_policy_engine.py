from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.data_access import get_request, load_budgets, load_employees, load_vendors
from src.policy_engine import deterministic_checks
from src.tools import tool_search_software_catalog

ROOT = Path(__file__).resolve().parents[1]
RISK = json.loads((ROOT / "data" / "vendor_risk.json").read_text(encoding="utf-8"))


def evaluate(request_id: str) -> dict:
    request = get_request(request_id)
    employees = load_employees()
    budgets = load_budgets()
    vendors = load_vendors()
    employee = employees[employees["employee_id"] == request["requester_id"]].iloc[0].to_dict()
    budget = budgets[budgets["department"] == employee["department"]].iloc[0].to_dict()
    vendor = vendors[vendors["vendor_name"] == request["vendor_name"]].iloc[0].to_dict()
    risk = RISK[request["vendor_name"]]
    error = None
    if risk.get("force_error"):
        error = risk["error_message"]
        risk = None
    return deterministic_checks(
        request, employee, budget, vendor, risk,
        tool_search_software_catalog(request), error
    )


class PolicyEngineTests(unittest.TestCase):
    def test_low_value_request_uses_manager_threshold(self):
        d = evaluate("REQ-1001")
        self.assertIn("Manager", d["required_approvals"])
        self.assertNotIn("budget_insufficient", d["risk_flags"])

    def test_sensitive_source_code_requires_security(self):
        d = evaluate("REQ-1003")
        self.assertIn("Security", d["required_approvals"])
        self.assertIn("security_review_required", d["risk_flags"])

    def test_budget_shortfall_is_deterministic(self):
        d = evaluate("REQ-1005")
        self.assertIn("budget_insufficient", d["risk_flags"])
        self.assertIn("Finance", d["required_approvals"])
        self.assertIn("Privacy", d["required_approvals"])

    def test_prompt_injection_does_not_change_policy(self):
        d = evaluate("REQ-1006")
        self.assertIn("prompt_injection_detected", d["risk_flags"])
        self.assertIn("missing_information", d["risk_flags"])
        self.assertIn("annual cost", d["missing_information"])
        self.assertTrue(d["human_review_required"])

    def test_vendor_api_outage_is_not_favorable(self):
        d = evaluate("REQ-1009")
        self.assertIn("vendor_risk_unavailable", d["risk_flags"])
        self.assertIn("security_review_required", d["risk_flags"])
        self.assertIn("Security", d["required_approvals"])


if __name__ == "__main__":
    unittest.main()
