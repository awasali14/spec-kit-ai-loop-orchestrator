import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import analyze_ledger as ledger  # noqa: E402


def output(run_id="analyze-a1", severity="High", fingerprint=None):
    finding = {
        "severity": severity,
        "category": "consistency",
        "title": "Requirement is not covered",
        "description": "FR-003 has no corresponding task.",
        "artifact_refs": ["specs/003-example/spec.md:42", "specs/003-example/tasks.md"],
        "evidence": ["FR-003 exists but no task cites it"],
        "recommended_remediation": "Add a task that implements FR-003.",
    }
    if fingerprint:
        finding["fingerprint"] = fingerprint
    return {"run_id": run_id, "findings": [finding]}


class AnalyzeLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name) / "analyze-ledger.json"
        ledger.initialize_ledger(self.path, "specs/003-example")

    def tearDown(self):
        self.temporary.cleanup()

    def test_new_ledger_is_ready_and_empty(self):
        current = ledger.load_ledger(self.path)
        self.assertTrue(current["summary"]["ready_for_implementation"])
        self.assertEqual(current["revision"], 1)

    def test_merge_assigns_parent_id_and_blocks_on_high(self):
        merged = ledger.merge_output(self.path, output())
        self.assertEqual(merged["findings"][0]["id"], "AL-0001")
        self.assertEqual(merged["summary"]["blocking_finding_ids"], ["AL-0001"])
        self.assertFalse(merged["summary"]["ready_for_implementation"])

    def test_independent_runs_deduplicate_by_fingerprint(self):
        ledger.merge_output(self.path, output("analyze-a1", fingerprint="stable-1"))
        merged = ledger.merge_output(self.path, output("analyze-a2", fingerprint="stable-1"))
        self.assertEqual(len(merged["findings"]), 1)
        finding = merged["findings"][0]
        self.assertEqual(finding["analyzer_run_ids"], ["analyze-a1", "analyze-a2"])
        self.assertEqual(finding["occurrences"], 2)
        self.assertEqual(merged["analyzer_runs"][1]["duplicate_findings"], 1)

    def test_same_run_same_output_is_idempotent(self):
        first = ledger.merge_output(self.path, output())
        replay = ledger.merge_output(self.path, output())
        self.assertEqual(replay["revision"], first["revision"])
        self.assertEqual(len(replay["analyzer_runs"]), 1)

    def test_same_run_with_different_output_fails(self):
        ledger.merge_output(self.path, output())
        with self.assertRaises(ledger.LedgerError):
            ledger.merge_output(self.path, output(severity="Critical"))

    def test_malformed_output_does_not_mutate_ledger(self):
        before = self.path.read_bytes()
        malformed = output()
        del malformed["findings"][0]["evidence"]
        with self.assertRaises(ledger.LedgerError):
            ledger.merge_output(self.path, malformed)
        self.assertEqual(self.path.read_bytes(), before)

    def test_unexpected_analyzer_fields_are_rejected(self):
        malformed = output()
        malformed["findings"][0]["status"] = "fixed"
        with self.assertRaises(ledger.LedgerError):
            ledger.merge_output(self.path, malformed)

    def test_clean_analyzer_run_is_recorded(self):
        merged = ledger.merge_output(
            self.path, {"run_id": "analyze-clean", "findings": []}
        )
        self.assertEqual(merged["analyzer_runs"][0]["reported_findings"], 0)
        self.assertTrue(merged["summary"]["ready_for_implementation"])

    def test_fixed_requires_validation_evidence(self):
        ledger.merge_output(self.path, output())
        with self.assertRaises(ledger.LedgerError):
            ledger.update_finding(self.path, finding_id="AL-0001", status="fixed")
        fixed = ledger.update_finding(
            self.path,
            finding_id="AL-0001",
            status="fixed",
            validation_evidence=["Analyzer A3 confirmed FR-003 maps to T019"],
        )
        self.assertTrue(fixed["summary"]["ready_for_implementation"])

    def test_rediscovered_fixed_finding_becomes_partially_fixed(self):
        ledger.merge_output(self.path, output("a1", fingerprint="stable"))
        ledger.update_finding(
            self.path,
            finding_id="AL-0001",
            status="fixed",
            validation_evidence=["Fixer changed tasks.md"],
        )
        rediscovered = ledger.merge_output(
            self.path, output("a3", fingerprint="stable")
        )
        self.assertEqual(rediscovered["findings"][0]["status"], "partially_fixed")
        self.assertFalse(rediscovered["summary"]["ready_for_implementation"])

    def test_accepted_risk_requires_complete_decision(self):
        ledger.merge_output(self.path, output())
        with self.assertRaises(ledger.LedgerError):
            ledger.update_finding(
                self.path,
                finding_id="AL-0001",
                status="accepted_risk",
                approver="engineer",
            )
        accepted = ledger.update_finding(
            self.path,
            finding_id="AL-0001",
            status="accepted_risk",
            approver="engineer",
            rationale="The dependent service is not yet available",
            scope="Internal validation only",
        )
        self.assertTrue(accepted["summary"]["ready_for_implementation"])

    def test_deferred_high_remains_blocking(self):
        ledger.merge_output(self.path, output())
        deferred = ledger.update_finding(
            self.path, finding_id="AL-0001", status="deferred"
        )
        self.assertFalse(deferred["summary"]["ready_for_implementation"])

    def test_open_medium_does_not_block_implementation(self):
        merged = ledger.merge_output(self.path, output(severity="Medium"))
        self.assertTrue(merged["summary"]["ready_for_implementation"])

    def test_absolute_artifact_reference_is_rejected(self):
        bad = output()
        bad["findings"][0]["artifact_refs"] = ["/home/user/private/spec.md"]
        with self.assertRaises(ledger.LedgerError):
            ledger.merge_output(self.path, bad)

    def test_expected_run_id_is_enforced(self):
        with self.assertRaises(ledger.LedgerError):
            ledger.merge_output(self.path, output(), expected_run_id="analyze-a2")

    def test_markdown_render_contains_readiness_and_finding(self):
        merged = ledger.merge_output(self.path, output())
        rendered = ledger.render_markdown(merged)
        self.assertIn("Ready for implementation: **no**", rendered)
        self.assertIn("AL-0001", rendered)
        target = self.path.with_suffix(".md")
        ledger.write_markdown(target, merged)
        self.assertEqual(target.read_text(encoding="utf-8"), rendered)

    def test_summary_tampering_fails_validation(self):
        current = ledger.merge_output(self.path, output())
        current["summary"]["blocking_critical_high"] = 0
        with self.assertRaises(ledger.LedgerError):
            ledger.validate_ledger(current)


if __name__ == "__main__":
    unittest.main()
