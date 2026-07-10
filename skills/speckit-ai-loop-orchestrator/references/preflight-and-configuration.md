# Preflight and configuration

Run this before mutations in `full` or `prep`, and validate applicable checks at
every partial-mode entry.

## Project and version

1. Confirm `.specify/` exists. Otherwise stop and instruct the operator to run
   `specify init` with the intended integration.
2. Run `specify version` and require Spec Kit `>=0.12.9`.
3. Confirm `.specify/memory/constitution.md` exists, is readable, is not empty,
   and is not an unfilled template. Treat unresolved bracket placeholders and
   template-only principle text as unusable.
4. If the constitution is absent/unusable, invoke official
   `speckit.constitution`, review its diff, and create its checkpoint before
   continuing.
5. Confirm the active command is `speckit.ai-loop-orchestrator.run`. Do not use
   an extra dotted namespace segment.

## Required command surfaces

Confirm the active integration exposes:

```text
speckit.constitution
speckit.specify
speckit.clarify
speckit.plan
speckit.checklist
speckit.tasks
speckit.analyze
speckit.converge
speckit.phase-orchestrator.phase
```

Use the integration's registered commands/skills and Spec Kit extension registry
as evidence. Do not infer availability only from a file name in another agent's
directory. If Phase Orchestrator is missing, stop with:

```text
Install Spec Kit Phase Orchestrator, re-register it for the active integration,
restart the agent if needed, and rerun this command.
```

Do not fall back to `/speckit.implement`; this extension specifically delegates
phase-scoped work to Phase Orchestrator.

## Configuration resolution

Resolve in increasing priority:

1. `defaults` from installed `extension.yml`.
2. `ai-loop-orchestrator-config.yml` beside the installed extension.
3. `ai-loop-orchestrator-config.local.yml` beside it.
4. `SPECKIT_AI_LOOP_ORCHESTRATOR_*` environment variables.
5. Explicit invocation `--no-commit`, which disables all commit checkpoints.

Persist the resolved non-secret snapshot in `loop-state.json`. Do not copy
environment secrets or machine-local commands containing credentials into state.

Validate checkpoint modes: `disabled`, `auto`, `review`, or `required`. Only
`review` may have a timeout. Its timeout must be a positive integer or null;
zero is invalid. `required` never times out. Validate limits as positive
integers and the analyzer context percentage as 1–100.

## Git

When commits are enabled:

```bash
python3 .specify/extensions/ai-loop-orchestrator/scripts/git_safety.py \
  checkpoint --repo . --require-clean-unowned
```

Require a Git worktree, usable identity, attached/understood branch, no merge
conflicts, no staged content, and a clean worktree before the first mutating
stage. Later checkpoints may preserve unrelated unstaged files only when they
are separate from checkpoint-owned files and the parent confirms workers cannot
overlap them. Never silently switch to no-commit mode.

When commits are explicitly disabled, Git is optional. Still inspect Git when
present to avoid overwriting user work.

## Capabilities and QA

Confirm the integration can create isolated contexts before analyze or
implementation. Detect browser/agent capabilities at runtime. Validate configured
start, automated, and stop commands as non-production, project-local operations;
record timeouts. The parent must track and terminate every process it starts,
including when no explicit stop command exists.

## Hooks

Official Spec Kit commands own their before/after hooks. Read the hook packet
they emit. Actually invoke and await mandatory hooks; offer optional hooks as
configured. Do not duplicate a hook's effect inside the orchestrator. The
orchestrator's own deterministic guards run directly through the helper scripts,
not through a recursive lifecycle hook.
