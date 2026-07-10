import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


class PackageContractTests(unittest.TestCase):
    def test_manifest_contract_and_required_version(self):
        manifest = yaml.safe_load((ROOT / "extension.yml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertEqual(manifest["extension"]["id"], "ai-loop-orchestrator")
        self.assertEqual(manifest["requires"]["speckit_version"], ">=0.12.9")
        command = manifest["provides"]["commands"][0]
        self.assertEqual(command["name"], "speckit.ai-loop-orchestrator.run")
        self.assertRegex(command["name"], r"^speckit\.[a-z0-9-]+\.[a-z0-9-]+$")
        self.assertEqual(manifest["config"][0]["template"], "ai-loop-orchestrator-config.template.yml")

    def test_manifest_exposes_every_commit_control(self):
        manifest = yaml.safe_load((ROOT / "extension.yml").read_text(encoding="utf-8"))
        commits = manifest["defaults"]["commits"]
        expected = {
            "enabled",
            "after_spec_kit_step",
            "after_analyze_fix",
            "implementation_phase_commits",
            "after_converge_update",
            "after_operator_qa_fix",
            "final_report_checkpoint",
        }
        self.assertEqual(set(commits), expected)
        self.assertTrue(all(commits.values()))

    def test_command_wrapper_has_description_arguments_and_skill_handoff(self):
        command = (ROOT / "commands" / "run.md").read_text(encoding="utf-8")
        self.assertTrue(command.startswith("---\n"))
        self.assertIn("description:", command.split("---", 2)[1])
        self.assertIn("$ARGUMENTS", command)
        self.assertIn("skills/speckit-ai-loop-orchestrator/SKILL.md", command)
        self.assertNotIn("TODO", command)

    def test_skill_frontmatter_and_size(self):
        path = ROOT / "skills" / "speckit-ai-loop-orchestrator" / "SKILL.md"
        content = path.read_text(encoding="utf-8")
        _, frontmatter, _ = content.split("---", 2)
        metadata = yaml.safe_load(frontmatter)
        self.assertEqual(set(metadata), {"name", "description"})
        self.assertEqual(metadata["name"], "speckit-ai-loop-orchestrator")
        self.assertLess(len(content.splitlines()), 500)
        self.assertNotIn("TODO", content)

    def test_skill_references_are_direct_and_exist(self):
        path = ROOT / "skills" / "speckit-ai-loop-orchestrator" / "SKILL.md"
        content = path.read_text(encoding="utf-8")
        references = re.findall(r"\]\(references/([^)]+)\)", content)
        self.assertEqual(len(references), 5)
        for reference in references:
            target = path.parent / "references" / reference
            self.assertTrue(target.is_file(), reference)
            self.assertNotIn("TODO", target.read_text(encoding="utf-8"))

    def test_skill_ui_metadata(self):
        path = ROOT / "skills" / "speckit-ai-loop-orchestrator" / "agents" / "openai.yaml"
        metadata = yaml.safe_load(path.read_text(encoding="utf-8"))["interface"]
        self.assertGreaterEqual(len(metadata["short_description"]), 25)
        self.assertLessEqual(len(metadata["short_description"]), 64)
        self.assertIn("$speckit-ai-loop-orchestrator", metadata["default_prompt"])

    def test_required_runtime_files_are_packaged(self):
        required = [
            "scripts/ai_loop_state.py",
            "scripts/analyze_ledger.py",
            "scripts/git_safety.py",
            "scripts/report_receipts.py",
            "schemas/analyzer-findings.schema.json",
            "schemas/operator-qa.schema.json",
            "templates/analyze-ledger.md",
            "templates/checkpoint-decisions.md",
            "templates/converge-review.md",
            "templates/operator-qa.md",
            "templates/final-report.md",
        ]
        for relative in required:
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_public_runtime_files_contain_no_private_workspace_path(self):
        runtime_roots = [
            ROOT / "commands",
            ROOT / "skills",
            ROOT / "scripts",
            ROOT / "templates",
            ROOT / "schemas",
        ]
        forbidden = "/home/awasali14/"
        for runtime_root in runtime_roots:
            for path in runtime_root.rglob("*"):
                if path.is_file() and path.suffix in {".md", ".py", ".json", ".yaml"}:
                    self.assertNotIn(forbidden, path.read_text(encoding="utf-8"), str(path))


if __name__ == "__main__":
    unittest.main()
