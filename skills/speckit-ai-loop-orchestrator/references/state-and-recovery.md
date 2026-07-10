# State and recovery

Use this reference at every entry, resume, and parent control-loop iteration.

## State paths

For feature `specs/003-example`, use:

```text
specs/003-example/.ai-loop/
├── loop-state.json
├── intake/idea.md
├── analyze-ledger.json
├── analyze-ledger.md
├── checkpoint-decisions.md
├── converge-review.md
├── operator-qa.json
├── operator-qa.md
├── final-report.md
└── receipts/
```

Never persist the source's machine-local absolute path. The state initializer
copies the content, stores its original basename and SHA-256, and records only a
feature-local path.

## Initialize

After official specify creates or identifies the feature directory:

```bash
python3 .specify/extensions/ai-loop-orchestrator/scripts/ai_loop_state.py init \
  --repo-root . \
  --feature-dir "specs/003-example" \
  --idea-file "/operator/source idea.md"
```

Add `--no-commit` when selected at invocation. Repeating initialization with the
same source hash is safe. A different hash at an existing state path is an error.

Initialize the analyze ledger before the first analyzer:

```bash
python3 .specify/extensions/ai-loop-orchestrator/scripts/analyze_ledger.py init \
  "specs/003-example/.ai-loop/analyze-ledger.json" \
  --feature-dir "specs/003-example" \
  --markdown "specs/003-example/.ai-loop/analyze-ledger.md"
```

## Start and complete operations

Use stable loop-scoped IDs. Record an operation before a command, spawn, human
checkpoint, converge pass, QA pass, or commit attempt:

```bash
python3 .specify/extensions/ai-loop-orchestrator/scripts/ai_loop_state.py \
  start-operation "STATE" \
  --id "prep-plan-command-001" \
  --type "external_command" \
  --expected-output "specs/003-example/plan.md" \
  --recovery verify_then_retry
```

After independent validation:

```bash
python3 .specify/extensions/ai-loop-orchestrator/scripts/ai_loop_state.py \
  complete-operation "STATE" \
  --id "prep-plan-command-001" \
  --stage prep --stage-status running \
  --next-action "review_plan_diff"
```

Recovery policies:

- `retry_idempotent`: missing outputs permit a retry with the same operation ID.
- `verify_then_retry`: require affirmative non-execution evidence before retry.
- `verify_only`: never automatically retry.
- `require_human`: ambiguity always opens a required checkpoint.

Expected outputs prove completion when all exist. Their absence does not prove a
non-idempotent side effect never happened.

## Reload and reconcile

At every loop iteration:

```bash
python3 .specify/extensions/ai-loop-orchestrator/scripts/ai_loop_state.py validate "STATE"
python3 .specify/extensions/ai-loop-orchestrator/scripts/ai_loop_state.py \
  next "STATE" --repo-root .
```

Classify active work as:

- `observably_completed`: validate the result, then finalize state without
  repeating the operation.
- `observably_not_started`: execute the recorded operation once.
- `safe_idempotent_retry`: repeat with the same ID; do not mint another ID.
- `ambiguous_requires_human`: block and request a decision.

Supply `--evidence-status` only after collecting affirmative external evidence.
Never use it to force progress.

## Register delegated agents

Start the spawn operation, then register its logical run before spawning:

```bash
python3 .specify/extensions/ai-loop-orchestrator/scripts/ai_loop_state.py \
  register-agent "STATE" \
  --run-id "analyze-a1-001" --role analyzer --mode fresh \
  --parent-operation-id "spawn-analyze-a1-001" --integration codex
```

Immediately after spawn, capture every exposed identifier:

```bash
python3 .specify/extensions/ai-loop-orchestrator/scripts/ai_loop_state.py \
  update-agent "STATE" --run-id "analyze-a1-001" --status running \
  --native-agent-id "ID" --native-session-id "SESSION" \
  --native-task-name "analyze_a1" --reopen-supported
```

Update status on return, failure, cancellation, loss, or completion. If a
session is lost, mark it `lost`, create a replacement with `--replaces-run-id`,
and make the replacement reread state, the exact current diff, and relevant
ledger/receipt. If identity after an interrupted spawn is ambiguous, inspect the
integration's agent list and block rather than spawning a possible duplicate.

After Phase Orchestrator, import every exposed nested phase-worker identifier.
When the integration exposes no native identifier, register the logical phase
worker with null native fields and its observed final status; never invent IDs.

## Stage and checkpoint state

State updates around a commit can span the commit boundary. Record the commit
operation before staging. After commit success, record its hash and complete the
operation; include that state update in the next checkpoint. Do not amend a
reviewed commit merely to insert its own hash. For the final report checkpoint,
record its hash in state and terminal output after success as explicitly allowed
by the final-report contract.
