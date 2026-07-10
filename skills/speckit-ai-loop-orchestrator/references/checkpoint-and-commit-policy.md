# Checkpoints and commits

Read this before every human checkpoint, staging action, commit attempt, or
receipt update.

## Unified human checkpoints

Modes:

- `disabled`: do not pause or present a packet.
- `auto`: write/show the packet and continue, recording auto-proceed.
- `review`: request approve/revise/defer/proceed or free-text feedback; a
  configured positive timeout may continue with the configured action.
- `required`: block for an explicit decision; never time out.

Every enabled packet includes stage, changed artifacts/code, validation,
decisions, blocking analyze or QA findings, converge-appended tasks, risks, and
proposed next action. Record decisions in state and append to
`checkpoint-decisions.md`; never erase previous decisions.

Open required checkpoints for ambiguous recovery, limits, unsafe Git, missing
required capabilities, unaccepted `not_run` QA, and final acceptance.

## Parent-owned checkpoint algorithm

1. Reload state and confirm the completed operation/stage.
2. Identify only files owned by this checkpoint.
3. Run the Git candidate guard before staging:

   ```bash
   python3 .specify/extensions/ai-loop-orchestrator/scripts/git_safety.py \
     checkpoint --repo . \
     --owned-file "path/one" --owned-file "path/two"
   ```

4. Review the exact diff. Stop if an owned file mixes unrelated edits. Preserve
   unrelated files unstaged.
5. If candidates are empty, append a no-op receipt and do not commit.
6. Record a stable commit-attempt operation in state.
7. Generate the body:

   ```bash
   python3 .specify/extensions/ai-loop-orchestrator/scripts/report_receipts.py \
     commit-body --stage "plan" \
     --purpose "Record the reviewed technical plan." \
     --changed-file "specs/003-example/plan.md" \
     --validation "Constitution checks passed" \
     --reference "speckit.plan"
   ```

8. Stage explicit paths with `git add -- <paths>`. Never use `git add .`, `-A`,
   or a broad directory when it includes unrelated content.
9. Verify the exact index:

   ```bash
   python3 .specify/extensions/ai-loop-orchestrator/scripts/git_safety.py \
     verify-index --repo . --expected-file "specs/003-example/plan.md"
   ```

10. Commit with a professional Conventional Commit subject and the generated
    body. Never push.
11. Capture the hash, append the receipt idempotently by operation ID, complete
    state, and reload before continuing.

## Commit contents

Commit bodies identify:

- checkpoint purpose and Spec Kit stage;
- exact changed files/artifacts;
- validation/review performed;
- related task/finding/scenario/pass IDs;
- accepted risk and follow-up.

Typical subjects:

```text
docs: record feature specification
docs: clarify feature requirements
docs: add technical implementation plan
docs: add feature quality checklist
docs: add implementation task breakdown
fix: resolve analyze findings AL-0001 and AL-0003
docs: append convergence tasks
fix: resolve operator QA scenarios QA-002 and QA-004
docs: record AI loop final report
```

## Checkpoint ownership

- Prep: only artifacts changed by that one official command plus state/receipt.
- Analyze fix: only approved fixer files plus ledger, state, and receipt.
- Implementation: Phase Orchestrator owns its one commit per phase.
- Converge: only appended `tasks.md` plus packet, state, and receipt.
- QA fix: only approved fix files plus QA artifact, state, and receipt.
- Final report: final report and its pre-commit state/receipt changes.

When `--no-commit` is active, never stage or commit at any stage. Still review
diffs and append no-commit receipts. The setting does not weaken validation,
checkpoints, analyzer independence, converge, or QA.
