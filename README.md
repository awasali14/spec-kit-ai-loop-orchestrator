# Spec Kit AI Loop Orchestrator

Spec Kit AI Loop Orchestrator is a skill-backed Spec Kit extension that runs a
feature from an idea file through specification, artifact analysis, phased
implementation, implementation convergence, practical QA, and final safety
review. Durable state and receipts make long agent runs resumable and auditable.

> **Pre-release:** `0.1.0` is ready for internal engineering validation, not
> public catalog use. Review extension source before installing it.

## What it orchestrates

```text
idea file -> specify -> clarify -> plan -> checklist -> tasks
          -> analyze convergence -> Phase Orchestrator implementation
          -> /speckit.converge -> practical operator QA -> final report
```

The extension keeps judgment with the parent agent while deterministic helpers
own state transitions, finding normalization, Git safety, and audit reports.
Checkpoint commits are enabled by default and can be disabled for an entire run
with `--no-commit`.

## Requirements

- Spec Kit `0.12.9` or newer, initialized in the target project. Version
  `0.12.9` includes the required converge command and current bundle/skills
  fixes used by this package.
- Python `3.11` or newer.
- The independent
  [Spec Kit Phase Orchestrator](https://github.com/awasali14/spec-kit-phase-orchestrator)
  extension and its `speckit.phase-orchestrator.phase` command.
- Git with a usable identity for the default commit-enabled mode. Git is not
  required when the run explicitly uses `--no-commit`.

The runtime preflight also checks that the standard Spec Kit commands through
`speckit.converge` are registered. A missing command stops the run with an
actionable message instead of silently weakening the workflow.

## Local development installation

From an initialized disposable Spec Kit project:

```bash
specify extension add --dev /path/to/spec-kit-ai-loop-orchestrator
```

Restart the active coding agent if it does not discover the new command
immediately. Confirm registration with:

```bash
specify extension list
specify extension info ai-loop-orchestrator
```

Install Phase Orchestrator separately, or use the companion bundle after both
component versions are available through the configured extension catalogs.

## Usage

```text
/speckit.ai-loop-orchestrator.run full "/path/to/idea file.md"
/speckit.ai-loop-orchestrator.run status specs/003-example
/speckit.ai-loop-orchestrator.run analyze specs/003-example
/speckit.ai-loop-orchestrator.run implement specs/003-example/tasks.md
/speckit.ai-loop-orchestrator.run converge specs/003-example
/speckit.ai-loop-orchestrator.run qa specs/003-example
```

Supported modes are `full`, `prep`, `analyze`, `implement`, `converge`, `qa`,
and `status`. Quote paths containing spaces. Use `--no-commit` only when the
operator intentionally owns all lifecycle commits.

## Configuration

After installation, copy the shipped template to the project configuration:

```bash
cp .specify/extensions/ai-loop-orchestrator/ai-loop-orchestrator-config.template.yml \
  .specify/extensions/ai-loop-orchestrator/ai-loop-orchestrator-config.yml
```

Place machine-only overrides in
`ai-loop-orchestrator-config.local.yml`. Environment variables prefixed with
`SPECKIT_AI_LOOP_ORCHESTRATOR_` have the highest priority. Do not put secrets in
configuration, ledgers, receipts, reports, or commit messages.

## Safety model

- Only the parent orchestrator stages and commits; it never pushes.
- Analyzers are read-only. Fixers and workers change only their assigned scope.
- Unapproved Critical/High analyze findings and P0/P1 practical failures block
  normal progression.
- Every side effect is registered as an in-flight operation before execution
  and reconciled against durable outputs before another action is selected.
- Unexecuted QA scenarios remain `not_run`; they are never reported as passed.

## Development

Run the unit suite from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

The detailed design record remains in
[spec-kit-ai-loop-orchestrator-plan.md](./spec-kit-ai-loop-orchestrator-plan.md).

## Branch strategy

- `main` contains production-ready, releasable work.
- `dev` is the integration branch for ongoing development.
- Development changes are promoted from `dev` through review after internal
  agent testing.
