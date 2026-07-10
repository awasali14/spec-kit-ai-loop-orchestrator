# Internal engineering test guide

Use a disposable project and Spec Kit `0.12.9` or newer. Do not test the first
run in a repository containing valuable uncommitted work.

## 1. Prepare Spec Kit and source checkouts

Confirm the CLI:

```bash
specify version
```

If it is older than `0.12.9`, follow the official upgrade guidance. One pinned
installation form is:

```bash
uv tool install specify-cli --force \
  --from git+https://github.com/github/spec-kit.git@v0.12.9
```

Download or clone both repositories beside each other:

```text
spec-kit-phase-orchestrator/
spec-kit-ai-loop-orchestrator/
```

Do not use the companion bundle for this initial test; its catalog resolution
remains intentionally unpublished until both extension releases exist.

## 2. Create a disposable project

For Codex:

```bash
specify init ai-loop-test-codex --integration codex --offline \
  --ignore-agent-tools
cd ai-loop-test-codex
specify extension add --dev /path/to/spec-kit-phase-orchestrator
specify extension add --dev /path/to/spec-kit-ai-loop-orchestrator
specify extension list
specify extension info ai-loop-orchestrator
```

Confirm both extension commands are registered. In skills-based Codex, the
generated command skill is normally:

```text
.agents/skills/speckit-ai-loop-orchestrator-run/SKILL.md
```

Also confirm the installed extension contains:

```text
.specify/extensions/ai-loop-orchestrator/skills/
  speckit-ai-loop-orchestrator/SKILL.md
```

Copy and review the config template if changing defaults:

```bash
cp .specify/extensions/ai-loop-orchestrator/ai-loop-orchestrator-config.template.yml \
  .specify/extensions/ai-loop-orchestrator/ai-loop-orchestrator-config.yml
```

Restart the coding agent after installation. Re-add the extensions if a new
integration is installed after them.

## 3. Run the first feature

Create an idea file outside the feature directory, including at least one path
with spaces or Unicode during the portability pass. Invoke:

```text
/speckit.ai-loop-orchestrator.run full "/path/to/idea source ü.md"
```

Skills-first agents may expose the equivalent as:

```text
$speckit-ai-loop-orchestrator-run full "/path/to/idea source ü.md"
```

Start with a small feature, then a medium feature with at least three task
phases. Keep automatic commits enabled for the primary run. Repeat a shorter run
with `--no-commit`.

## 4. Required evidence

Record for each run:

- agent and version;
- Spec Kit and both extension versions;
- exact invocation and result;
- registered command/skill path;
- generated feature and `.ai-loop` paths;
- all checkpoint commit hashes, subjects, and body summaries;
- tests and operator scenarios run;
- failures, recovery steps, caveats, and final GO/NO-GO.

Verify these high-risk behaviors:

1. Prep changes produce one parent-owned commit per changed official command.
2. Analyzer A1/A2 output deduplicates; malformed JSON fails rather than passing.
3. A fixer cannot validate itself, stage, or commit.
4. Fresh A3/A4 precede persistent P; P rereads exact fixer diffs.
5. Killing P permits durable replacement without duplicate findings.
6. Phase Orchestrator runs `all`, creates one validated commit per phase, and
   returns task/docs evidence.
7. Official converge appends only new tasks, creates no empty clean commit, and
   routes new work back through Phase Orchestrator.
8. Converge stops at its pass limit for a required decision.
9. Automated QA runs when available; assisted steps work otherwise; unexecuted
   scenarios stay `not_run` and block until accepted.
10. Startup/scenario timeouts and parent-started process cleanup work on failure.
11. Git safety stops on unrelated staged work, detached HEAD, missing identity,
    merge conflicts, or mixed owned-file edits.
12. `--no-commit` disables every checkpoint commit without weakening gates.
13. Context loss after operation registration, side-effect success, worker
    return, and commit preparation reconciles without duplicate side effects.
14. The final report contains the source hash, findings, tasks/phases, commits,
    converge passes, QA statuses, tests, risks, and recommendation.
15. No machine-local source path, secret, raw prompt, or tool log appears in
    committed artifacts.

## 5. Agent portability order

Repeat installation and a representative run in this order:

1. Codex (`--integration codex`)
2. Claude Code (`--integration claude`)
3. Cursor (`--integration cursor-agent`)

Confirm the registered wrapper appears in each integration's native skill or
command directory and that the portable command text resolves official command
names correctly. VS Code is optional for the initial internal release.

## 6. Result record

| Agent | Version | Feature size | Command registered | Full run | `--no-commit` | Resume test | Notes |
|---|---|---|---|---|---|---|---|
| Codex | | small + medium | | | | | |
| Claude Code | | representative | | | | | |
| Cursor | | representative | | | | | |

Report reproducible failures with the relevant durable artifacts and Git diff,
but remove secrets and private paths. Do not add runtime tracing instructions to
the orchestrator or workers.
