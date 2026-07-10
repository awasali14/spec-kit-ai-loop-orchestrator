# Workflow stages

Use only the requested mode's stages, but always enforce prerequisites and the
parent reload/reconcile loop.

## Preflight

Run the full checklist in `preflight-and-configuration.md`. Write a review
packet. The default preflight checkpoint is required. Do not create feature
artifacts until approved.

## Prep

Invoke each official command in a clean context, one at a time:

1. `speckit.specify`: provide normalized idea content as the feature description;
   focus on what/why, not implementation. Determine the feature directory,
   initialize `.ai-loop`, then parent-review and checkpoint.
2. `speckit.clarify`: run before plan unless the operator explicitly approved a
   spike/prototype skip. Parent-review, checkpoint, and record decisions.
3. `speckit.plan`: generate research/design artifacts and run constitution
   checks before research and after design. Parent-review and checkpoint.
4. `speckit.checklist`: validate requirements completeness/clarity/consistency;
   do not treat it as runtime testing. Parent-review and checkpoint.
5. `speckit.tasks`: generate user-story-oriented, dependency-ordered tasks.
   Include tests when spec/TDD/operator explicitly requires them. Parent-review
   and checkpoint.

Do not begin a later command until the prior command's diff, validation,
checkpoint decision, receipt, and optional commit are complete.

## Analyze convergence

Initialize the ledger, then:

```text
fresh A1 + fresh A2 -> validate JSON -> merge/dedupe ledger
```

If ready, proceed. Otherwise checkpoint, run clean F1 on approved findings,
parent-review/commit, then fresh A3. If still blocked, repeat with clean F2 and
fresh A4. If A4 is still blocked, checkpoint, run clean F3, parent-review/commit,
then always start persistent Analyzer P for validation.

Persistent loop:

1. P rereads current artifacts, exact latest fixer diff, and updated ledger.
2. Validate and merge P's schema-valid output.
3. If ready, finish analyze.
4. Otherwise checkpoint, launch a separate clean fixer for approved IDs,
   parent-review/commit, update receipt/ledger, and return to the same P.

Default persistent cycles: 3. Stop P at 80% context only when reliably
measurable; otherwise use cycle limit plus explicit self-warning. At the limit,
require a human choice: replacement P, accept specific risk, continue, proceed
despite findings, or stop. Never call a malformed pass clean.

Ledger commands:

```bash
python3 EXT_ROOT/scripts/analyze_ledger.py merge "LEDGER" "ANALYZER.json" \
  --expected-run-id "analyze-a1-001" --markdown "LEDGER.md"
python3 EXT_ROOT/scripts/analyze_ledger.py summary "LEDGER"
python3 EXT_ROOT/scripts/analyze_ledger.py update "LEDGER" \
  --id AL-0001 --status fixed \
  --validation-evidence "Fresh Analyzer A3 confirmed the fix" \
  --markdown "LEDGER.md"
```

Convert Medium/Low items to tasks, defer, accept, or leave visible as appropriate.
Only the JSON summary decides implementation readiness.

## Implementation

Require analyze readiness or an explicit human decision recorded in state. Run:

```text
speckit.phase-orchestrator.phase all specs/<feature>/tasks.md
```

Append `--no-commit` if sticky commit mode is off. Phase Orchestrator executes
one clean worker per phase, tests first when required, marks `[X]` only with
evidence, writes phase docs, runs focused validation, and commits per phase when
enabled. Stop on its blocker or failed gate. Import nested run records and phase
commit/validation summaries before marking implementation complete.

## Official implementation convergence

After known tasks complete, invoke official `speckit.converge`. Before the pass,
hash/capture `tasks.md`; after it, compare bytes and parse only appended task IDs.
Generate a converge packet every pass.

- `converged`: `tasks.md` is unchanged. Record no-op receipt; create no commit;
  proceed to QA after the configured checkpoint.
- `tasks_appended`: parent reviews append-only diff, checkpoints/commits it, then
  runs Phase Orchestrator on incomplete/new tasks and converges again.
- `blocked`: require human direction.

Default maximum: 3 passes. A clean command may not append an empty Convergence
header. Converge never fixes code and never replaces tests or operator QA.

## Practical operator QA

Choose the best available execution mode:

1. `automated`: use an agent-native browser or configured E2E command and capture
   redacted evidence.
2. `assisted_manual`: start the app when configured, issue exact numbered steps,
   and wait for human pass/fail evidence.
3. `not_runnable`: record scenarios `not_run`; require explicit acceptance or
   remain blocked.

Cover happy path, error/edge path, auth/session, refresh/reconnect, mobile/narrow
viewport, keyboard-only behavior, and realistic sequence when relevant. Time
bound startup/scenarios and clean up every parent-started process even on failure.

Validate/render JSON:

```bash
python3 EXT_ROOT/scripts/report_receipts.py operator-qa "operator-qa.json" \
  --output "operator-qa.md"
```

If P0/P1 or flow blockers exist, checkpoint, use a separate clean fixer for
approved scenario IDs, run targeted tests, parent-review/commit, then rerun QA
independently. Default maximum fix cycles: 3. Remaining `not_run` is blocking
unless converted to a complete accepted-risk decision.

## Final safety

From a clean practical state:

1. Run targeted and configured broader tests.
2. Rerun the selected operator flow; do not reuse stale success evidence.
3. Confirm no unresolved P0/P1/flow blocker or unaccepted `not_run`.
4. Confirm official converge is clean or exact gaps have approved decisions.
5. Revalidate state, ledger, receipts, tasks, phase docs, commit list, and secret
   redaction.
6. Generate the final report with `report_receipts.py final-report`.
7. Open required final acceptance. If approved and report changed, create its
   checkpoint commit. Record its hash after success without trying to put that
   hash inside the same report commit.

Recommend GO only when every gate above passes. Otherwise recommend NO-GO and
record exact blocker, decision needed, and authoritative resume action.
