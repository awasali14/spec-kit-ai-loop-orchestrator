# Spec Kit AI Loop Orchestrator Bundle

This integration-agnostic bundle installs the tested lifecycle pair:

- Spec Kit Phase Orchestrator `1.0.0`
- Spec Kit AI Loop Orchestrator `0.1.0`

The bundle is a distribution layer only. It adds no commands, skills, scripts,
hooks, state files, or runtime behavior.

## Pre-release status

The manifest is ready for structural validation. Do not publish or recommend
the one-step bundle install until both pinned extensions have versioned release
artifacts and resolvable entries in an install-allowed extension catalog.

After the component catalogs are available:

```bash
specify bundle validate --path /path/to/bundle
specify bundle build --path /path/to/bundle --output /path/to/dist
specify bundle install /path/to/dist/ai-loop-orchestrator-bundle-0.1.0.zip
```

Validate install, update, removal, idempotency, and command registration in
clean Codex, Claude Code, and Cursor projects before publishing the artifact.

Until then, internal engineers should install both extensions independently by
local development path as documented in the extension testing guide.
