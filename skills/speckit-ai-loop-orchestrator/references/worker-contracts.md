# Worker contracts

Read this before every delegation. Give workers only task-local context and
durable artifact paths. Do not give them parent continuation instructions.

## Universal worker boundary

Every worker receives these rules:

```text
Work only on the assigned role and scope.
Do not stage, commit, push, reset, switch branches, or invoke another stage.
Do not edit or reinterpret loop-state.json.
Do not record secrets, private paths, raw prompts, or tool logs.
Return changed/read files, concise evidence, validation, blockers, and status.
Stop after the assigned handoff.
```

The parent registers the run before spawn and captures native identifiers after
spawn. The worker rereads current durable inputs at start; remembered context is
never authoritative.

## Prep worker

Assign exactly one official Spec Kit prep command. Provide normalized intake,
current constitution, current feature artifacts, and the command goal. The
worker runs/invokes only that official command and returns its artifact list and
summary. The parent reviews the diff and owns the checkpoint commit before the
next prep worker.

## Analyzer

Analyzers are read-only. Provide current `spec.md`, `plan.md`, `tasks.md`,
constitution, relevant ledger, run ID, and role (`fresh` or `persistent`). For a
persistent validation after a fix, also provide the exact fixer diff and updated
ledger. Require JSON matching `schemas/analyzer-findings.schema.json`:

```json
{
  "run_id": "analyze-a1-001",
  "findings": [
    {
      "severity": "High",
      "category": "coverage",
      "title": "Requirement has no task",
      "description": "FR-003 is not represented in tasks.md.",
      "artifact_refs": ["specs/003-example/spec.md:42", "specs/003-example/tasks.md"],
      "evidence": ["FR-003 exists; no task cites or implements it"],
      "recommended_remediation": "Add a traceable task for FR-003.",
      "fingerprint": "stable-coverage-fr003"
    }
  ]
}
```

The analyzer never assigns ledger IDs or statuses and never edits files. If its
output is malformed, the pass failed; do not merge it as a clean pass.

## Fixer

Use a separate clean fixer only after the parent approves findings. Provide:

- exact approved ledger IDs and remediation scope;
- current artifacts and constitution;
- forbidden files and unrelated current changes;
- required focused validation for the parent or next analyzer.

The fixer edits only approved artifacts, returns an exact changed-file summary
and recommended validation, and stops. It does not mark ledger findings fixed
and does not validate its own correction. The parent reviews/stages/commits;
the next independent analyzer validates.

## Persistent Analyzer P

Use P only after A4 still reports blocking Critical/High findings and a clean F3
has changed approved items. On every cycle, make P reread current artifacts,
the exact fixer diff, and the updated ledger. Persist all conclusions. Reuse P
only while its context is reliable. At 80% measured context, or the configured
cycle limit/explicit self-warning when context is not measurable, stop and open
the configured checkpoint. A replacement resumes solely from durable artifacts.

## Phase Orchestrator

Invoke the installed `speckit.phase-orchestrator.phase all <tasks.md>` command.
Do not spawn phase workers yourself in parallel with it. Preserve its one-clean-
worker-per-phase, tests-first, task-checkbox, documentation, focused-validation,
and parent-owned commit contract. Pass `--no-commit` when the loop's sticky
commit mode is off.

After return, review task checkboxes, phase docs, validation, commits, and nested
worker records. Import every exposed native ID. If none are exposed, register
the observed logical phase run with null native fields rather than inventing an
identifier.

## Converge worker

Invoke official `speckit.converge` after implementation. It may inspect code and
append only a new Convergence phase to `tasks.md`; it must not fix code or rewrite
existing tasks/spec/plan. The parent compares `tasks.md` byte-for-byte, extracts
new task IDs, and builds a packet accepted by `report_receipts.py converge-review`.

## Operator QA agent

Provide quickstart/manual scenarios, acceptance criteria, configured commands,
timeouts, non-production environment, and evidence rules. The QA agent executes
and reports only; it never fixes. Require JSON accepted by
`schemas/operator-qa.schema.json` and `report_receipts.py operator-qa`.

An unexecuted scenario is `not_run`. An accepted risk requires approver,
rationale, scope, and timestamp. Record steps, expected, actual, evidence, and
P0–P3 severity when failed. Redact secrets and personal data.

## QA fixer

Use a clean fixer for parent-approved failed scenario IDs only. Provide exact
reproduction, evidence, affected scope, and targeted tests. The fixer returns
changed files and tests but does not rerun or reclassify operator QA. Parent
reviews/commits, then the operator QA agent reruns the flow independently.
