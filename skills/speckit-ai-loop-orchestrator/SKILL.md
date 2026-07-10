---
name: speckit-ai-loop-orchestrator
description: Run or resume a durable, auditable Spec Kit feature lifecycle from an idea file through specification, clarification, planning, checklist and task generation, analyze convergence, Phase Orchestrator implementation, official implementation convergence, practical operator QA, and final safety reporting. Use for the ai-loop-orchestrator extension's full, prep, analyze, implement, converge, qa, or status modes, especially for long multi-agent work that needs clean worker boundaries, configurable human checkpoints, safe milestone commits, and crash/context-compaction recovery.
---

# Spec Kit AI Loop Orchestrator

Act as the parent lifecycle controller. Treat conversation context as a cache;
treat `specs/<feature>/.ai-loop/loop-state.json`, ledgers, receipts, decisions,
feature artifacts, and Git as the durable record.

## Establish the invocation

Use the command wrapper's parsed object. Accept exactly one mode and one target:

| Mode | Target | Run |
|---|---|---|
| `full` | idea/source file | every stage through final safety |
| `prep` | idea/source file | preflight and Spec Kit prep |
| `analyze` | feature directory | analyze convergence |
| `implement` | `tasks.md` | Phase Orchestrator implementation |
| `converge` | feature directory | official implementation convergence |
| `qa` | feature directory | practical operator QA and approved fixes |
| `status` | feature directory | read-only durable status summary |

Make `--no-commit` sticky for the whole run. Never disable only some commits.
For `full` or `prep`, initialize state after `/speckit.specify` identifies the
feature directory and immediately normalize the source into `.ai-loop/intake/`.
For all other modes, require an existing valid `loop-state.json`.

Use `.specify/extensions/ai-loop-orchestrator/` as `EXT_ROOT`. Run helpers as
`python3 EXT_ROOT/scripts/<script>.py ...`. Quote every path.

## Load only the references needed now

- At every entry or resume, read [state-and-recovery.md](references/state-and-recovery.md).
- Before preflight or configuration resolution, read
  [preflight-and-configuration.md](references/preflight-and-configuration.md).
- Before executing a lifecycle stage, read
  [workflow-stages.md](references/workflow-stages.md).
- Before any worker/analyzer/fixer/operator delegation, read
  [worker-contracts.md](references/worker-contracts.md).
- Before any human checkpoint, staging, commit, or receipt, read
  [checkpoint-and-commit-policy.md](references/checkpoint-and-commit-policy.md).

Read a selected reference completely. Do not reconstruct its rules from memory.

## Run the parent control loop

Repeat this loop before selecting every next action, including after a command,
worker return, checkpoint decision, interruption, or context compaction:

1. Reload and validate `loop-state.json`.
2. Run `ai_loop_state.py next` and reconcile any `active_operation` against its
   expected files, receipts, Git state, command outcome, and integration agent
   list. Never infer non-execution merely because an output is absent.
3. If reconciliation is ambiguous, set the stage blocked and open a required
   human checkpoint. Do not repeat a possibly non-idempotent side effect.
4. Read the authoritative `next_action`.
5. Record exactly one stable active operation before its side effect.
6. Execute or delegate only that operation.
7. Validate observable results, update the applicable ledger/receipt/agent run,
   then complete the operation with the next action.
8. Reload state and repeat.

Do not select the next action from chat memory. Automatic compaction is not a
workflow stage and does not rotate this parent. The 80% context threshold applies
only to persistent Analyzer P when the integration exposes a reliable metric.

## Keep authority boundaries strict

The parent alone:

- owns state, the analyze ledger, checkpoint decisions, and next-action choice;
- registers every direct worker before spawning it and captures native IDs;
- reviews worker output and exact diffs;
- selects files, stages, creates checkpoint commits, and records receipts;
- invokes official Spec Kit commands through the active integration;
- imports logical/native nested phase-worker records after Phase Orchestrator.

Analyzers remain read-only. Fixers, prep workers, phase workers, converge
workers, and operator QA agents never stage, commit, push, or continue into
another stage. A fixer never validates its own fix. Operator QA never fixes its
own finding. Never push.

Require isolated worker contexts for analyzer/fixer separation and Phase
Orchestrator. If the integration cannot provide clean contexts, stop at a
required human checkpoint rather than weakening role separation.

## Execute the lifecycle

For `full`, run these stages in order. Partial modes enter at their named stage
only after prerequisites and durable state validate.

1. Preflight Spec Kit, constitution, required commands, Phase Orchestrator,
   configuration, Git, and integration capabilities.
2. Run official prep: specify → clarify → plan → checklist → tasks. Parent-review
   and checkpoint each changed command result before the next command.
3. Run analyze convergence: fresh A1+A2; clean fix and fresh A3; clean fix and
   fresh A4; then persistent P with separate clean fixers only if blocking
   findings remain. Proceed when the JSON ledger reports zero unapproved
   Critical/High blockers.
4. Invoke `speckit.phase-orchestrator.phase all <tasks.md>`, preserving its
   parent-owned per-phase commit behavior unless `--no-commit` is active.
5. Run official `/speckit.converge`. Route appended tasks back through Phase
   Orchestrator and repeat, up to the configured limit.
6. Execute operator QA using an available agent-native browser or configured
   command, otherwise assisted manual steps. Record unavailable execution as
   `not_run`, never `passed`.
7. Run targeted tests and the selected operator flow from a clean practical
   state, confirm converge/risk status, generate the final report, and perform
   final acceptance.

Use the detailed stage algorithms and limits in `workflow-stages.md`. Official
commands retain their own before/after hooks; actually invoke mandatory hooks
and wait for them. Do not replace official Spec Kit commands with improvised
file edits.

## Gate progress with deterministic outputs

- Schema-validate analyzer output before merging it with `analyze_ledger.py`.
  Malformed output is a failed pass, never a clean result.
- Trust analyze readiness only from the normalized JSON ledger summary.
- Treat Critical/High `open`, `approved_for_fix`, `partially_fixed`, and
  `deferred` findings as blocking. An `accepted_risk` is non-blocking only with
  approver, rationale, scope, and timestamp.
- Generate a converge review packet for every pass. A clean pass changes no
  `tasks.md` bytes and creates no empty commit.
- Validate operator QA with `report_receipts.py operator-qa`. Every scenario is
  exactly `passed`, `failed`, `not_run`, or `accepted_risk`.
- Stop normal progress on P0/P1 failures, flow blockers, unaccepted `not_run`
  scenarios, unsafe Git, validation failures, limits, or ambiguity.

## Commit only reviewed checkpoints

When commits are enabled, use `git_safety.py checkpoint` before staging, inspect
the diff, stage explicit paths, then use `git_safety.py verify-index` before
committing. Use a professional Conventional Commit subject and a meaningful body
from `report_receipts.py commit-body`. Record the outcome in the stage receipt.

Skip a commit when there is no checkpoint-owned change; record why. Stop if an
owned file mixes unrelated work or the index contains unrelated content. Never
amend or reset user work. Never push.

## Finish or report status

For `status`, make no lifecycle changes. Validate state and ledgers, inspect Git
read-only, and report current stage, revision, active operation and reconciliation
class, next action, analyze blockers, implementation/converge/QA progress,
checkpoint commits, and required human decision.

For final safety, generate `.ai-loop/final-report.md` from durable inputs. The
report lists preceding commits but not the hash of its own checkpoint. After a
final-report commit succeeds, record that hash in state and terminal output.
Return GO only when analyze is ready, implementation convergence is complete,
QA has no blocking scenario, targeted validation passes, and final acceptance is
approved. Otherwise return NO-GO with exact blockers and resume action.
