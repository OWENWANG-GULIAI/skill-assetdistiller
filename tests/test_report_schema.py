import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReportSchemaTests(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads((ROOT / "references" / "report_schema.json").read_text(encoding="utf-8"))

    def test_contract_centers_four_core_outputs_instead_of_resume_inventory(self):
        required = set(self.schema["required"])
        self.assertTrue({
            "executive_summary", "top_assets", "moat_analysis", "customer_segments",
            "monetization_offers", "primary_offer", "expert_interview", "roadmap", "evidence_ledger"
        }.issubset(required))
        self.assertNotIn("resume_inventory", required)
        self.assertNotIn("primary_mvp", required)

    def test_top_assets_are_exactly_three_and_have_transparent_scores(self):
        top_assets = self.schema["properties"]["top_assets"]
        self.assertEqual(top_assets["minItems"], 3)
        self.assertEqual(top_assets["maxItems"], 3)
        asset = self.schema["$defs"]["asset"]
        self.assertTrue({
            "name", "source_experience", "high_value_problem", "key_decision",
            "counterintuitive_insight", "solution_mechanism", "deliverables",
            "result_evidence", "portability", "moat", "score_breakdown",
            "score_total", "maturity", "can_sell", "cannot_promise", "evidence_gap"
        }.issubset(asset["required"]))
        score_ref = asset["properties"]["score_breakdown"]["$ref"].split("/")[-1]
        self.assertEqual(
            set(self.schema["$defs"][score_ref]["required"]),
            {"problem_value", "result_evidence", "moat", "portability", "product_readiness"},
        )

    def test_offers_customers_and_interview_have_bounded_counts(self):
        offers = self.schema["properties"]["monetization_offers"]
        customers = self.schema["properties"]["customer_segments"]
        questions = self.schema["$defs"]["expert_interview"]["properties"]["questions"]
        self.assertEqual((offers["minItems"], offers["maxItems"]), (3, 5))
        self.assertEqual((customers["minItems"], customers["maxItems"]), (2, 4))
        self.assertEqual((questions["minItems"], questions["maxItems"]), (2, 3))

    def test_offer_contains_value_price_boundary_and_priority_evidence(self):
        offer = self.schema["$defs"]["offer"]
        self.assertTrue({
            "name", "category", "audience", "trigger", "paid_problem", "cost_of_inaction",
            "mechanism", "deliverables", "scope_excluded", "price_test", "pricing_basis",
            "high_ticket_condition", "score_breakdown", "score_total", "priority",
            "feasibility", "evidence_links", "validation_action"
        }.issubset(offer["required"]))


if __name__ == "__main__":
    unittest.main()
