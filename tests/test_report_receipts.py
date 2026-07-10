import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import report_receipts as reports  # noqa: E402


def qa_payload(status="passed", severity=None, decision=None):
    return {
        "mode": "automated",
        "scenarios": [
            {
                "id": "QA-001",
                "title": "Complete the happy path",
                "status": status,
                "severity": severity,
                "flow_blocker": False,
                "steps": ["Open the app", "Submit the form"],
                "expected": "The record is created",
                "actual": "The record is created",
                "evidence": ["e2e report"],
                "decision": decision,
            }
        ],
        "validations": ["npm run test:e2e passed"],
    }


class ReportReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_redacts_common_secret_shapes(self):
        text = reports.redact_text(
            "token=topsecret Bearer abc.def.ghi sk-abcdefghijklmnopqrstuvwxyz"
        )
        self.assertNotIn("topsecret", text)
        self.assertNotIn("abc.def.ghi", text)
        self.assertNotIn("sk-abcdefghijklmnopqrstuvwxyz", text)

    def test_commit_body_requires_files_and_validation(self):
        with self.assertRaises(reports.ReportError):
            reports.render_commit_body(
                stage="plan", purpose="Record plan", changed_files=[], validations=[]
            )
        body = reports.render_commit_body(
            stage="plan",
            purpose="Record the reviewed technical plan.",
            changed_files=["specs/003/plan.md"],
            validations=["Constitution checks passed"],
            references=["speckit.plan"],
        )
        self.assertIn("Lifecycle checkpoint: plan", body)
        self.assertIn("Changed files:", body)

    def test_receipt_append_is_idempotent(self):
        entry = reports.render_receipt_entry(
            operation_id="plan-commit-001",
            stage="prep",
            checkpoint="Plan checkpoint",
            changed_files=["specs/003/plan.md"],
            validations=["Plan reviewed"],
            commit_hash="abcdef1",
            commit_subject="docs: record technical plan",
            commit_body_summary="Capture the reviewed architecture.",
        )
        path = self.root / "prep-receipt.md"
        self.assertTrue(reports.append_receipt(path, entry, "plan-commit-001"))
        self.assertFalse(reports.append_receipt(path, entry, "plan-commit-001"))
        self.assertEqual(path.read_text().count("receipt:plan-commit-001"), 1)

    def test_no_op_receipt_requires_reason(self):
        with self.assertRaises(reports.ReportError):
            reports.render_receipt_entry(
                operation_id="clean-converge",
                stage="converge",
                checkpoint="Converge pass 1",
                changed_files=[],
                validations=["Converge reported clean"],
            )
        entry = reports.render_receipt_entry(
            operation_id="clean-converge",
            stage="converge",
            checkpoint="Converge pass 1",
            changed_files=[],
            validations=["Converge reported clean"],
            no_op_reason="tasks.md was byte-for-byte unchanged",
        )
        self.assertIn("not created", entry)

    def test_receipt_rejects_non_conventional_subject(self):
        with self.assertRaises(reports.ReportError):
            reports.render_receipt_entry(
                operation_id="op",
                stage="prep",
                checkpoint="Specify",
                changed_files=["spec.md"],
                validations=["reviewed"],
                commit_hash="abcdef1",
                commit_subject="update spec",
                commit_body_summary="Updated it.",
            )

    def test_converge_review_renders_appended_tasks(self):
        payload = {
            "pass_number": 2,
            "outcome": "tasks_appended",
            "incomplete_items": ["FR-003 is partial"],
            "new_tasks": [{"id": "T042", "description": "Complete FR-003"}],
            "affected_areas": ["src/service.py"],
            "evidence": ["Missing error path"],
            "changed_files": ["specs/003/tasks.md"],
            "proposed_next_action": "Run Phase Orchestrator for the new phase.",
            "remaining_gaps": [],
        }
        rendered = reports.render_converge_review(payload)
        self.assertIn("T042", rendered)
        self.assertIn("Pass: **2**", rendered)

    def test_converged_payload_cannot_claim_appended_tasks(self):
        with self.assertRaises(reports.ReportError):
            reports.validate_converge_payload(
                {
                    "pass_number": 1,
                    "outcome": "converged",
                    "new_tasks": [{"id": "T1", "description": "Impossible"}],
                    "proposed_next_action": "Continue",
                }
            )

    def test_not_run_qa_is_blocking_and_never_passed(self):
        validated = reports.validate_qa_payload(qa_payload(status="not_run"))
        self.assertFalse(validated["summary"]["ready"])
        self.assertEqual(validated["summary"]["counts"]["passed"], 0)

    def test_failed_p1_or_flow_blocker_is_blocking(self):
        validated = reports.validate_qa_payload(qa_payload(status="failed", severity="P1"))
        self.assertEqual(validated["summary"]["blocking_scenario_ids"], ["QA-001"])

    def test_accepted_qa_risk_requires_decision(self):
        with self.assertRaises(reports.ReportError):
            reports.validate_qa_payload(qa_payload(status="accepted_risk"))
        decision = {
            "approver": "engineer",
            "rationale": "External sandbox unavailable",
            "scope": "Internal smoke test",
            "timestamp": "2026-07-10T12:00:00Z",
        }
        validated = reports.validate_qa_payload(
            qa_payload(status="accepted_risk", decision=decision)
        )
        self.assertTrue(validated["summary"]["ready"])

    def test_operator_markdown_contains_evidence(self):
        rendered = reports.render_operator_qa(qa_payload())
        self.assertIn("QA-001", rendered)
        self.assertIn("e2e report", rendered)

    def test_final_report_includes_preceding_commits_and_automatic_go(self):
        state = {
            "loop_id": "loop-1",
            "status": "running",
            "feature": {"directory": "specs/003"},
            "source": {
                "idea_file": "specs/003/.ai-loop/intake/idea.md",
                "sha256": "a" * 64,
            },
            "stages": {
                "implementation": {"completed_phases": [1], "completed_task_ids": ["T001"]},
                "converge": {"status": "complete", "attempts": 1, "appended_task_ids": []},
            },
        }
        ledger = {
            "summary": {
                "total": 0,
                "blocking_critical_high": 0,
                "ready_for_implementation": True,
                "by_status": {"accepted_risk": 0},
            }
        }
        commits = [
            {
                "stage": "prep",
                "hash": "abcdef1",
                "subject": "docs: record feature specification",
                "body_summary": "Record reviewed requirements.",
                "changed_files": ["specs/003/spec.md"],
            }
        ]
        rendered = reports.render_final_report(state, ledger, qa_payload(), commits)
        self.assertIn("Final recommendation: **GO**", rendered)
        self.assertIn("`abcdef1`", rendered)
        self.assertIn("preceding checkpoint commits", rendered)

    def test_final_report_is_no_go_when_qa_blocks(self):
        state = {
            "loop_id": "loop-1",
            "status": "running",
            "feature": {"directory": "specs/003"},
            "source": {"idea_file": "specs/003/.ai-loop/intake/idea.md", "sha256": "a" * 64},
            "stages": {"implementation": {}, "converge": {"status": "complete"}},
        }
        ledger = {"summary": {"ready_for_implementation": True, "by_status": {}}}
        rendered = reports.render_final_report(state, ledger, qa_payload(status="not_run"), [])
        self.assertIn("Final recommendation: **NO-GO**", rendered)


if __name__ == "__main__":
    unittest.main()
