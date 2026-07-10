# Release checklist

Use this only after internal Codex, Claude Code, and Cursor testing succeeds.

## Extension

- [ ] All tests and `git diff --check` pass from a clean checkout.
- [ ] `extension.yml` version and `CHANGELOG.md` agree.
- [ ] Spec Kit `0.12.9+` accepts `specify extension add --dev` in a clean project.
- [ ] The registered command/skill loads the installed internal skill and all
      references/scripts resolve after installation.
- [ ] The GitHub release archive installs with `specify extension add ... --from`.
- [ ] `.extensionignore` excludes tests, build output, the design plan, and the
      companion bundle from the installed runtime.
- [ ] No private paths, secrets, test state, trace exports, or post-run exporter
      code appear in the release or main branch.
- [ ] Release notes state tested agent/integration versions and Phase
      Orchestrator compatibility.

## Companion bundle

- [ ] Both pinned extension versions have published release artifacts.
- [ ] Both IDs/versions resolve from documented install-allowed catalogs.
- [ ] `specify bundle validate` succeeds online without unresolved references.
- [ ] `specify bundle build` produces the versioned ZIP.
- [ ] The built artifact installs both commands in clean Codex, Claude Code, and
      Cursor projects and reaches the Phase Orchestrator handoff.
- [ ] Reinstall is idempotent when zero, one, or both components already exist.
- [ ] Bundle update applies new pins and preserves extension config overrides.
- [ ] Bundle removal preserves components still owned by another bundle; the
      independently preinstalled-component behavior is documented.
- [ ] The bundle artifact contains only `bundle.yml`, README, LICENSE, and
      CHANGELOG and contributes no runtime behavior.

## Publication

- [ ] Create separate versioned releases for Phase Orchestrator, AI Loop
      Orchestrator, and the companion bundle.
- [ ] Verify the exact downloadable assets in fresh projects.
- [ ] Submit the two extensions and then the bundle through the official Spec
      Kit community processes with clean-install evidence.
