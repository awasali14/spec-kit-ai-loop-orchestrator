import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import ai_loop_state as state  # noqa: E402


class AiLoopStateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.idea = self.root.parent / f"idea source {Path(self.temporary.name).name}.md"
        self.idea.write_text("# Idéa\n\nBuild the thing.\n", encoding="utf-8")
        self.state_path, self.initial = state.initialize_state(
            repo_root=self.root,
            feature_dir="specs/003-feature with spaces",
            idea_file=self.idea,
            loop_id="test-loop",
        )

    def tearDown(self):
        self.idea.unlink(missing_ok=True)
        self.temporary.cleanup()

    def test_init_copies_and_normalizes_intake_without_absolute_source(self):
        payload = state.load_state(self.state_path)
        copied = self.root / payload["source"]["idea_file"]
        self.assertEqual(copied.read_bytes(), self.idea.read_bytes())
        self.assertEqual(payload["source"]["original_basename"], self.idea.name)
        self.assertNotIn(str(self.idea.parent), json.dumps(payload))
        self.assertEqual(payload["state_revision"], 1)

    def test_init_is_idempotent_for_same_idea(self):
        _, again = state.initialize_state(
            repo_root=self.root,
            feature_dir="specs/003-feature with spaces",
            idea_file=self.idea,
        )
        self.assertEqual(again["state_revision"], 1)

    def test_init_rejects_feature_outside_repository(self):
        with self.assertRaises(state.StateError):
            state.initialize_state(
                repo_root=self.root,
                feature_dir=self.root.parent / "outside",
                idea_file=self.idea,
            )

    def test_start_and_complete_operation_are_idempotent(self):
        started = state.start_operation(
            self.state_path,
            operation_id="prep-specify-001",
            operation_type="external_command",
            expected_outputs=["specs/003-feature with spaces/spec.md"],
        )
        self.assertEqual(started["state_revision"], 2)
        duplicate = state.start_operation(
            self.state_path,
            operation_id="prep-specify-001",
            operation_type="external_command",
            expected_outputs=["specs/003-feature with spaces/spec.md"],
        )
        self.assertEqual(duplicate["state_revision"], 2)
        complete = state.complete_operation(
            self.state_path,
            operation_id="prep-specify-001",
            next_action="run_clarify",
            stage="prep",
            stage_status="running",
        )
        self.assertEqual(complete["state_revision"], 3)
        duplicate_complete = state.complete_operation(
            self.state_path,
            operation_id="prep-specify-001",
            next_action="ignored_on_idempotent_replay",
        )
        self.assertEqual(duplicate_complete["state_revision"], 3)

    def test_second_active_operation_is_rejected(self):
        state.start_operation(
            self.state_path, operation_id="one", operation_type="command"
        )
        with self.assertRaises(state.StateError):
            state.start_operation(
                self.state_path, operation_id="two", operation_type="command"
            )

    def test_reconcile_observes_complete_expected_outputs(self):
        output = "specs/003-feature with spaces/spec.md"
        state.start_operation(
            self.state_path,
            operation_id="one",
            operation_type="command",
            expected_outputs=[output],
        )
        target = self.root / output
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("done", encoding="utf-8")
        result = state.classify_reconciliation(
            state.load_state(self.state_path), repo_root=self.root
        )
        self.assertEqual(result["classification"], "observably_completed")

    def test_reconcile_does_not_assume_missing_output_means_not_started(self):
        state.start_operation(
            self.state_path,
            operation_id="one",
            operation_type="commit",
            expected_outputs=["receipt.md"],
            recovery="verify_only",
        )
        result = state.classify_reconciliation(
            state.load_state(self.state_path), repo_root=self.root
        )
        self.assertEqual(result["classification"], "ambiguous_requires_human")

    def test_reconcile_allows_same_id_for_idempotent_retry(self):
        state.start_operation(
            self.state_path,
            operation_id="one",
            operation_type="ledger_merge",
            expected_outputs=["ledger.json"],
            recovery="retry_idempotent",
        )
        result = state.classify_reconciliation(
            state.load_state(self.state_path), repo_root=self.root
        )
        self.assertEqual(result["classification"], "safe_idempotent_retry")
        self.assertEqual(result["operation_id"], "one")

    def test_set_stage_merges_values_and_is_idempotent(self):
        updated = state.set_stage(
            self.state_path,
            stage="analyze",
            status="running",
            next_action="spawn_a1_a2",
            values={"attempts": 1, "open_critical_high": 2},
        )
        self.assertEqual(updated["stages"]["analyze"]["attempts"], 1)
        same = state.set_stage(
            self.state_path,
            stage="analyze",
            status="running",
            next_action="spawn_a1_a2",
            values={"attempts": 1, "open_critical_high": 2},
        )
        self.assertEqual(same["state_revision"], updated["state_revision"])

    def test_checkpoint_history_preserves_decisions_without_duplicate_replay(self):
        first = state.record_checkpoint(
            self.state_path,
            checkpoint_id="after_plan",
            mode="review",
            decision="approved",
            approver="engineer",
            rationale="Architecture is acceptable",
        )
        replay = state.record_checkpoint(
            self.state_path,
            checkpoint_id="after_plan",
            mode="review",
            decision="approved",
            approver="engineer",
            rationale="Architecture is acceptable",
        )
        self.assertEqual(len(replay["checkpoints"]), 1)
        self.assertEqual(replay["state_revision"], first["state_revision"])

    def test_agent_registry_records_native_identity(self):
        registered = state.register_agent(
            self.state_path,
            run_id="analyze-a1-001",
            role="analyzer",
            mode="fresh",
            integration="codex",
            parent_operation_id="spawn-a1",
        )
        self.assertEqual(registered["agent_runs"][0]["status"], "spawn_requested")
        attached = state.update_agent(
            self.state_path,
            run_id="analyze-a1-001",
            status="running",
            native_agent_id="agent-123",
            native_session_id="session-456",
            native_task_name="analyze_a1",
            reopen_supported=True,
        )
        run = attached["agent_runs"][0]
        self.assertEqual(run["native_agent_id"], "agent-123")
        self.assertTrue(run["reopen_supported"])

    def test_agent_registration_is_idempotent_but_conflicts_fail(self):
        kwargs = dict(
            run_id="fixer-001",
            role="fixer",
            mode="clean",
            parent_operation_id="spawn-fixer",
        )
        first = state.register_agent(self.state_path, **kwargs)
        replay = state.register_agent(self.state_path, **kwargs)
        self.assertEqual(first["state_revision"], replay["state_revision"])
        with self.assertRaises(state.StateError):
            state.register_agent(self.state_path, **{**kwargs, "role": "analyzer"})

    def test_replacement_agent_links_to_lost_run(self):
        state.register_agent(
            self.state_path,
            run_id="persistent-001",
            role="analyzer",
            mode="persistent",
            parent_operation_id="spawn-p1",
        )
        state.update_agent(
            self.state_path, run_id="persistent-001", status="lost"
        )
        replaced = state.register_agent(
            self.state_path,
            run_id="persistent-002",
            role="analyzer",
            mode="persistent",
            parent_operation_id="spawn-p2",
            replaces_run_id="persistent-001",
        )
        self.assertEqual(replaced["agent_runs"][1]["replaces_run_id"], "persistent-001")

    def test_invalid_absolute_durable_path_is_rejected(self):
        payload = state.load_state(self.state_path)
        payload["feature"]["spec"] = "/private/spec.md"
        with self.assertRaises(state.StateError):
            state.validate_state(payload)

    def test_atomic_writes_leave_no_temporary_files(self):
        state.set_stage(
            self.state_path,
            stage="prep",
            status="running",
            next_action="run_specify",
        )
        leftovers = list(self.state_path.parent.glob(f".{self.state_path.name}.*"))
        self.assertEqual(leftovers, [])

    def test_invocation_parser_supports_all_modes_and_no_commit(self):
        parsed = state.parse_invocation(
            ["full", "idea files/feature ü.md", "--no-commit"]
        )
        self.assertEqual(
            parsed,
            {
                "mode": "full",
                "target": "idea files/feature ü.md",
                "no_commit": True,
            },
        )
        for mode in state.MODES:
            self.assertEqual(state.parse_invocation([mode, "target"])["mode"], mode)

    def test_invocation_parser_rejects_unknown_options_and_extra_paths(self):
        with self.assertRaises(state.StateError):
            state.parse_invocation(["full", "idea.md", "--force"])
        with self.assertRaises(state.StateError):
            state.parse_invocation(["status", "one", "two"])


if __name__ == "__main__":
    unittest.main()
