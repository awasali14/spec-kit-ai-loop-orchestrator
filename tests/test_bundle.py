import re
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "bundle"


class BundleContractTests(unittest.TestCase):
    def test_bundle_manifest_is_pinned_and_integration_agnostic(self):
        manifest = yaml.safe_load((BUNDLE / "bundle.yml").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertEqual(manifest["bundle"]["id"], "ai-loop-orchestrator-bundle")
        self.assertRegex(manifest["bundle"]["version"], r"^\d+\.\d+\.\d+$")
        self.assertEqual(manifest["requires"]["speckit_version"], ">=0.12.9")
        self.assertNotIn("integration", manifest)
        extensions = manifest["provides"]["extensions"]
        self.assertEqual(
            extensions,
            [
                {"id": "phase-orchestrator", "version": "1.0.0"},
                {"id": "ai-loop-orchestrator", "version": "0.1.0"},
            ],
        )
        for extension in extensions:
            self.assertRegex(extension["version"], r"^\d+\.\d+\.\d+$")

    def test_bundle_contains_no_runtime_behavior(self):
        files = {
            path.relative_to(BUNDLE).as_posix()
            for path in BUNDLE.rglob("*")
            if path.is_file()
        }
        self.assertEqual(files, {"bundle.yml", "README.md", "LICENSE", "CHANGELOG.md"})
        forbidden_suffixes = {".py", ".sh", ".ps1"}
        self.assertFalse(any(Path(item).suffix in forbidden_suffixes for item in files))

    def test_bundle_description_is_not_a_runtime_authority(self):
        readme = (BUNDLE / "README.md").read_text(encoding="utf-8")
        self.assertIn("distribution layer only", readme)
        self.assertIn("Do not publish", readme)
        self.assertNotRegex(readme, re.compile(r"/speckit\.ai-loop-orchestrator\.run"))


if __name__ == "__main__":
    unittest.main()
