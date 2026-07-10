import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import git_safety as safety  # noqa: E402


def git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    )


class GitSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name)
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.name", "Test Engineer")
        git(self.repo, "config", "user.email", "engineer@example.test")
        (self.repo / "tracked.md").write_text("base\n", encoding="utf-8")
        git(self.repo, "add", "tracked.md")
        git(self.repo, "commit", "-q", "-m", "base")

    def tearDown(self):
        self.temporary.cleanup()

    def test_non_repository_is_reported_without_exception(self):
        with tempfile.TemporaryDirectory() as other:
            inspected = safety.inspect_repository(other)
            self.assertFalse(inspected["is_worktree"])

    def test_clean_repository_has_identity_and_branch(self):
        inspected = safety.inspect_repository(self.repo)
        self.assertTrue(inspected["identity"]["usable"])
        self.assertFalse(inspected["dirty"])
        self.assertFalse(inspected["detached"])

    def test_unicode_and_spaced_untracked_path_is_preserved(self):
        name = "QA evidence ünicode file.md"
        (self.repo / name).write_text("evidence", encoding="utf-8")
        inspected = safety.inspect_repository(self.repo)
        self.assertEqual(inspected["untracked"], [name])
        checked = safety.evaluate_checkpoint(inspected, [name])
        self.assertEqual(checked["checkpoint_candidates"], [name])
        self.assertTrue(checked["safe"])

    def test_unrelated_staged_file_blocks_checkpoint(self):
        (self.repo / "unrelated.md").write_text("user work", encoding="utf-8")
        git(self.repo, "add", "unrelated.md")
        checked = safety.evaluate_checkpoint(
            safety.inspect_repository(self.repo), ["tracked.md"]
        )
        self.assertFalse(checked["safe"])
        self.assertIn("unrelated_staged_files", checked["reasons"])

    def test_pre_staged_owned_file_requires_explicit_post_stage_mode(self):
        (self.repo / "tracked.md").write_text("changed\n", encoding="utf-8")
        git(self.repo, "add", "tracked.md")
        inspection = safety.inspect_repository(self.repo)
        initial = safety.evaluate_checkpoint(inspection, ["tracked.md"])
        self.assertIn("checkpoint_files_were_already_staged", initial["reasons"])
        post_stage = safety.evaluate_checkpoint(
            inspection, ["tracked.md"], allow_pre_staged_owned=True
        )
        self.assertTrue(post_stage["safe"])

    def test_unrelated_unstaged_file_can_be_preserved(self):
        (self.repo / "unrelated.md").write_text("user work", encoding="utf-8")
        checked = safety.evaluate_checkpoint(
            safety.inspect_repository(self.repo), ["tracked.md"]
        )
        self.assertTrue(checked["safe"])
        self.assertEqual(checked["unrelated_worktree"], ["unrelated.md"])

    def test_strict_clean_mode_blocks_unrelated_unstaged_file(self):
        (self.repo / "unrelated.md").write_text("user work", encoding="utf-8")
        checked = safety.evaluate_checkpoint(
            safety.inspect_repository(self.repo),
            ["tracked.md"],
            require_clean_unowned=True,
        )
        self.assertIn("unrelated_worktree_changes", checked["reasons"])

    def test_no_commit_mode_does_not_require_identity(self):
        git(self.repo, "config", "user.name", "")
        git(self.repo, "config", "user.email", "")
        inspection = safety.inspect_repository(self.repo)
        commit = safety.evaluate_checkpoint(inspection, [])
        no_commit = safety.evaluate_checkpoint(inspection, [], commit_enabled=False)
        self.assertIn("git_identity_unusable", commit["reasons"])
        self.assertTrue(no_commit["safe"])

    def test_detached_head_blocks_commit_mode(self):
        git(self.repo, "checkout", "-q", "--detach")
        checked = safety.evaluate_checkpoint(safety.inspect_repository(self.repo), [])
        self.assertIn("detached_head", checked["reasons"])

    def test_verify_index_requires_exact_expected_set(self):
        (self.repo / "tracked.md").write_text("changed\n", encoding="utf-8")
        (self.repo / "extra.md").write_text("extra\n", encoding="utf-8")
        git(self.repo, "add", "tracked.md", "extra.md")
        inspection = safety.inspect_repository(self.repo)
        wrong = safety.verify_index(inspection, ["tracked.md"])
        self.assertIn("index_contains_unexpected_files", wrong["reasons"])
        exact = safety.verify_index(inspection, ["tracked.md", "extra.md"])
        self.assertTrue(exact["safe"])

    def test_verify_index_rejects_empty_index(self):
        checked = safety.verify_index(safety.inspect_repository(self.repo), [])
        self.assertIn("index_is_empty", checked["reasons"])

    def test_invalid_owned_path_is_rejected(self):
        with self.assertRaises(safety.GitSafetyError):
            safety.evaluate_checkpoint(safety.inspect_repository(self.repo), ["../outside"])


if __name__ == "__main__":
    unittest.main()
