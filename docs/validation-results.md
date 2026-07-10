# Internal validation results

Date: 2026-07-10

Extension: Spec Kit AI Loop Orchestrator `0.1.0`

Branch: `dev`

## Automated validation

- `python3 -m unittest discover -s tests -v`: **70 passed**.
- Skill Creator `quick_validate.py`: **valid**.
- `git diff --check`: **clean**.
- Extension and configuration YAML: **parsed successfully**.
- Analyzer and operator QA JSON schemas: **parsed successfully**.
- Package contract checks: command namespace, Spec Kit minimum, config/defaults,
  commit controls, required runtime files, skill frontmatter/size/references,
  and absence of private workspace paths all passed.
- Bundle contract checks: exact two pinned extensions, integration-agnostic
  manifest, and no runtime behavior all passed.

## Official Spec Kit 0.12.9 smoke validation

An isolated `uvx` runtime pinned to official Spec Kit `v0.12.9` was used in a
disposable Codex project.

Passed:

1. `specify init ... --integration codex --offline`.
2. Local development installation of Phase Orchestrator `1.0.0`.
3. Local development installation of AI Loop Orchestrator `0.1.0`.
4. Both extensions listed enabled with one command each and no hooks.
5. AI Loop Orchestrator metadata reported category `process` and effect
   `read-write`.
6. Codex registered
   `.agents/skills/speckit-ai-loop-orchestrator-run/SKILL.md`.
7. Codex registered `.agents/skills/speckit-converge/SKILL.md` and
   `.agents/skills/speckit-phase-orchestrator-phase/SKILL.md`.
8. The installed wrapper retained correct skill handoff and argument parsing
   instructions.
9. The installed runtime included every helper, schema, template, internal
   skill, and reference.
10. The installed runtime excluded tests, the design plan, and companion bundle
    as required by `.extensionignore`.
11. `specify bundle validate --offline` reported the companion bundle
    well-formed and valid with both local components installed.

## Installed helper pipeline

The installed extension, not the source-tree scripts, successfully exercised:

1. strict `full` invocation parsing with a spaced Unicode idea path and sticky
   `--no-commit`;
2. source normalization and SHA-256 state initialization into a feature path
   containing spaces;
3. analyze ledger initialization, schema-valid clean result merge, Markdown
   rendering, and readiness validation;
4. analyze, implementation, converge, operator QA, and final-safety state
   transitions with monotonic revisions;
5. operator QA validation/rendering;
6. automatic final report generation with a GO recommendation;
7. final state and ledger validation; and
8. a scan confirming no disposable absolute path was written under `.ai-loop`.

## Handoff status

The extension is ready for internal engineer testing from a source checkout or
development archive using Spec Kit `0.12.9+`. The remaining validation is
deliberately human/agent integration testing:

- run a real small and medium feature through the complete lifecycle in Codex;
- repeat representative portability runs in Claude Code and Cursor;
- capture practical operator QA and crash/context-recovery evidence; and
- tune the workflow from those results before public release.

The companion bundle is not yet the installation path for this test. Publish it
only after both pinned extensions have release artifacts and install-allowed
catalog entries, then complete online bundle install/update/removal testing.
