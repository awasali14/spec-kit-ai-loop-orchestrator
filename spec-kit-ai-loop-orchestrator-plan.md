# Spec Kit AI Loop Orchestrator Extension Plan

Last updated: 2026-07-10

## Goal

Create a new Spec Kit extension that automates the full AI-assisted feature
development loop from an idea/source file through Spec Kit artifact generation,
analyze convergence, phase-by-phase implementation, practical operator QA, and a
final safety run.

This extension should include or integrate the existing Phase Orchestrator so the
implementation stage can reuse the proven phase-scoped worker model:

```text
idea file
-> constitution/preflight
-> specify
-> commit specify artifacts
-> clarify
-> commit clarification updates
-> plan
-> commit plan/design artifacts
-> checklist
-> commit post-plan checklist updates
-> tasks
-> commit task breakdown
-> analyze convergence
-> commit each approved analyze fix stage
-> phase orchestrator implementation
-> commit after each implementation phase
-> official converge completeness check
-> optional human review of missed/incomplete implementation work
-> repeat phase implementation and converge when new tasks are appended
-> practical operator QA
-> commit each approved QA fix stage
-> final safety run
-> final report checkpoint when artifacts changed
```

## Product Positioning

Working name:

```text
Spec Kit AI Loop Orchestrator
```

Candidate repository name:

```text
spec-kit-ai-loop-orchestrator
```

Candidate extension ID:

```text
ai-loop-orchestrator
```

Companion bundle working name:

```text
Spec Kit AI Loop Orchestrator Bundle
```

Candidate bundle ID:

```text
ai-loop-orchestrator-bundle
```

Maintainer:

```text
awasali14
```

One-sentence description:

```text
Automate the Spec Kit lifecycle from idea file to analyze convergence, phased implementation, and practical QA with configurable human checkpoints.
```

Public explanation:

```text
Spec Kit AI Loop Orchestrator is a higher-level workflow extension for developers who want repeatable, context-managed AI development loops. It runs Spec Kit prep steps, converges analyze findings through a ledger, delegates implementation to phase-scoped workers, and validates the result with operator-style practical QA.
```

## Relationship To Phase Orchestrator

The existing `spec-kit-phase-orchestrator` extension remains the focused
implementation engine. This new extension should not replace it without a clear
reason.

Recommended relationship:

1. Keep Phase Orchestrator as the implementation stage.
2. Keep Phase Orchestrator as a separate required extension in v1; do not vendor
   or duplicate its implementation code.
3. Keep the lifecycle loop separate from the phase implementation primitive.
4. Preserve the command boundary so users can run phase orchestration
   independently even when both extensions were installed through the bundle.
5. Runtime preflight must verify that `speckit.phase-orchestrator.phase` is
   installed when AI Loop Orchestrator was installed independently.
6. Publish a thin companion Spec Kit bundle that pins tested versions of both
   extensions and installs them together without adding runtime behavior.
7. Present the bundle as the recommended one-step installation path while
   retaining documented standalone installation for each extension.
8. Release, version, test, update, and troubleshoot the two extensions
   independently. The bundle is a distribution layer, not a merged codebase or
   a third workflow authority.

## Recommended Architecture

Build AI Loop Orchestrator as a skill-backed Spec Kit extension, not as a
command-only extension and not as a skill-only prompt pack.

Recommended architecture:

```text
Spec Kit extension manifest
-> extension command wrapper
-> generated agent skill as the primary workflow and resume authority
-> helper scripts for deterministic parsing/state/safety/reporting
-> durable .ai-loop artifacts for resume and audit
-> narrow hooks for guardrails
-> Phase Orchestrator handoff for implementation
-> official /speckit.converge handoff for post-implementation completeness
```

Development-only observability remains outside that runtime architecture:

```text
Codex persisted root and subagent threads
-> separate post-run trace exporter
-> human inspection of the exported trace
```

The exporter is an external development tool, not an extension component. It
must not add tracing instructions to the generated skill, main orchestrator,
Phase Orchestrator, or any subagent, and it must not write into the repository
being tested.

Recommended distribution:

```text
spec-kit-phase-orchestrator extension (independent release)
+ spec-kit-ai-loop-orchestrator extension (independent release)
-> ai-loop-orchestrator-bundle (optional one-step installation)
```

Component responsibilities:

1. `extension.yml` declares the extension, command, requirements, config, and
   optional hooks using the official Spec Kit extension contract.
2. `commands/run.md` is the portable command wrapper for agents that use slash
   commands.
3. The generated skill, for example
   `.agents/skills/speckit-ai-loop-orchestrator/SKILL.md`, is the primary
   agent-facing workflow in skills-first integrations such as Codex skills mode.
4. Scripts own deterministic work: argument parsing, state updates, ledger
   normalization, receipt generation, git safety checks, commit candidate
   summaries, and final report assembly.
5. Hooks are guardrails only. They can validate preconditions or block unsafe
   states, but they should not run the whole loop or make judgment-heavy
   decisions.
6. Artifacts under `specs/<feature>/.ai-loop/` are the durable source of truth
   for long-run resume, audit, and cross-agent handoff.
7. Phase Orchestrator remains the implementation engine. AI Loop Orchestrator
   delegates implementation rather than duplicating the phase worker model.
8. The generated skill and `loop-state.json` remain the execution and resume
   authority. The official Spec Kit workflow engine is not the primary runtime
   for v1; native workflow packaging may be evaluated later as an additional
   entry point.
9. `/speckit.converge` is the official post-implementation completeness check.
   It does not replace the pre-implementation analyze convergence loop or
   practical operator QA.

Rationale:

1. Spec Kit extension installation provides the public packaging and command
   registration model.
2. Current skills-first agent integrations expect reusable workflows to be
   installed as `SKILL.md`-based skills with supporting files.
3. Large lifecycle loops need scripts and state files so they can survive
   context resets, compaction, interrupted sessions, and multi-agent handoffs.
4. Hooks are best for deterministic enforcement, such as blocking unsafe git
   state or verifying required artifacts exist.
5. The skill-led design works in interactive agent environments where a single
   persistent analyzer session and agent-native browser capabilities may be
   useful, while the durable state files prevent those sessions from becoming
   hidden sources of truth.

## Non-Goals

1. Do not replace official `/speckit.specify`, `/speckit.clarify`,
   `/speckit.plan`, `/speckit.tasks`, `/speckit.analyze`, or
   `/speckit.implement`.
2. Do not require zero analyze findings. Require zero unapproved Critical/High
   findings.
3. Do not let analyzer agents edit files.
4. Do not let fix agents validate their own fixes.
5. Do not require human approval at every checkpoint. All checkpoints are
   configurable.
6. Do not make hosted visual review tools mandatory.
7. Do not make prompt, commentary, reasoning-summary, or response capture a
   responsibility of the main orchestrator or any delegated agent.
8. Do not ship the development-only Codex post-run trace exporter in the
   extension package, companion bundle, release archive, or main branch.
9. Do not add an automated AI reviewer, evaluator, or additional test layer on
   top of the post-run export. The developer will inspect or analyze the export
   separately.

## Core Workflow

```text
Input idea/source file
-> Spec Kit preflight
-> Spec Kit prep
-> Prep checkpoint commits
-> Analyze convergence
-> Analyze fix checkpoint commits
-> Phase implementation
-> Per-phase implementation commits
-> Official converge completeness loop
-> Optional converge review checkpoint
-> Additional phase implementation when converge appends tasks
-> Practical operator QA
-> QA fix checkpoint commits
-> Final safety run
-> Final report checkpoint
```

## Commit Policy

Commits are first-class lifecycle checkpoints. They make long AI-assisted loops
auditable, resumable, and easier to inspect when a later stage fails.

Default behavior:

```yaml
commits:
  enabled: true
  after_spec_kit_step: true
  after_analyze_fix: true
  implementation_phase_commits: true
  after_converge_update: true
  after_operator_qa_fix: true
  final_report_checkpoint: true
```

Commit rules:

1. The parent orchestrator owns all staging and commit creation.
2. Clean workers, analyzers, fixers, and operator QA agents must not stage,
   commit, push, or continue into another stage.
3. Automatic checkpoint commits, including meaningful commit bodies, are the
   default main-workflow behavior. `--no-commit` or clear user wording such as
   "do not commit" is the optional opt-out and disables all
   orchestrator-created commits for that run.
4. When commits are enabled, stage only files owned by the just-completed
   lifecycle checkpoint.
5. Stop before committing if unrelated changes are mixed into files the
   checkpoint needs to stage.
6. Skip commit creation when a checkpoint makes no file changes, but record the
   no-op in the relevant receipt.
7. Never push. Pushes are always user-owned.
8. When commit mode is enabled, preflight must confirm that the project is in a
   Git worktree, Git identity is usable, HEAD/branch state is understood, and
   the files needed for the next checkpoint can be staged without including
   unrelated work.

Commit message rules:

1. Use a professional Conventional Commit subject.
2. Include a clear commit body for every orchestrator-created commit.
3. The body should summarize the checkpoint purpose, changed artifacts/files,
   validation performed, related Spec Kit stage or analyze findings, and any
   accepted risks or follow-up notes.
4. Keep the body audit-friendly without dumping full ledgers, reports, logs, or
   secrets.
5. The final report lists all preceding checkpoint commits but does not attempt
   to include the hash of its own final-report checkpoint commit. Record that
   final hash in skill state/terminal output after the commit succeeds.

### 1. Intake

The user creates a source file that describes the feature or work item.

Example:

```text
/path/to/idea-file.md
```

The loop starts from that file and treats it as the input to the Spec Kit
specification phase.

Expected command shape, subject to final extension design:

```text
/speckit.ai-loop-orchestrator.run /path/to/idea-file.md
```

or:

```text
/speckit.ai-loop-orchestrator.run --input /path/to/idea-file.md --mode full
```

### 2. Spec Kit Preflight

Before creating or updating feature artifacts, the extension must verify that
the project has been initialized with Spec Kit and that project principles exist.

Preflight checks:

1. Confirm `.specify/` exists; otherwise instruct the user to run
   `specify init` with the intended integration.
2. Confirm the installed Spec Kit version satisfies the extension minimum and
   includes `/speckit.converge`.
3. Confirm `.specify/memory/constitution.md` exists and is usable.
4. If no constitution exists, run or require `/speckit.constitution` before the
   feature loop continues. If the orchestrator runs `/speckit.constitution`,
   parent-review changed constitution artifacts and create a checkpoint commit
   before continuing.
5. Confirm the active extension command name follows the official manifest
   pattern: `speckit.{extension-id}.{command}`.
6. Confirm `speckit.phase-orchestrator.phase` is installed and callable before
   entering implementation.
7. Confirm extension hooks are not bypassed. If the orchestrator delegates to
   official Spec Kit commands, those commands handle their own before/after
   hooks. If the orchestrator implements a phase internally, it must perform the
   same hook checks for that phase.
8. When commits are enabled, perform the Git checks defined in the commit policy.
   If Git is unavailable or unsafe, stop for a decision or require the user to
   explicitly restart/continue with `--no-commit`; do not silently weaken the
   configured commit policy.

### 3. Spec Kit Prep

Run these steps in clean sessions or isolated worker contexts where supported:

```text
specify using idea file
-> commit
-> clarify
-> commit
-> plan
-> commit
-> checklist
-> commit
-> tasks
-> commit
```

Official workflow constraints:

1. `/speckit.specify` receives the idea/source-file contents as the feature
   description and focuses on what and why, not technology choices.
2. `/speckit.specify` creates the feature directory and `spec.md`; branch names
   and spec directory names are independent.
3. `/speckit.clarify` runs before `/speckit.plan` unless the user explicitly
   chooses to skip clarification for a spike or exploratory prototype.
4. `/speckit.checklist` runs after `/speckit.plan` and validates requirements
   completeness, clarity, and consistency. It is not an implementation test
   runner and should not replace runtime QA.
5. `/speckit.plan` handles the technical stack and architecture, fills the
   implementation plan, generates design artifacts, and must pass the
   constitution check before research and again after design.
6. `/speckit.tasks` runs after the plan/design artifacts and produces
   user-story-oriented, dependency-ordered tasks.
7. Test tasks are optional in official Spec Kit task generation. Generate them
   when the feature spec requests tests/TDD or the user explicitly asks for
   test-first work.
8. After each successful official Spec Kit prep command that changes files, the
   parent reviews the diff and creates one checkpoint commit before the next
   prep command runs.
9. Prep checkpoint commits use professional Conventional Commit subjects and
   bodies that identify the Spec Kit command, changed artifacts, validation or
   checklist result, and any accepted risks or follow-up notes.

Prep stage outputs:

```text
spec.md
plan.md
research.md, if generated
data-model.md, if generated
contracts/, if generated
quickstart.md, if generated
checklists/, if generated
tasks.md
```

### 4. Analyze Convergence

The analyze loop uses a parent-owned ledger and separate read-only analyzers and
write-capable fixers.

Approved analyze flow:

```text
fresh Analyzer A1 + separate fresh Analyzer A2
-> merge findings into ledger

IF A1/A2 leave no unapproved Critical/High findings:
  -> proceed immediately to implementation
ELSE:
  -> optional human checkpoint
  -> clean Fixer F1
  -> parent commit approved fixes
  -> fresh Analyzer A3

IF A3 reports no unapproved Critical/High findings:
  -> proceed immediately to implementation
ELSE:
  -> optional human checkpoint
  -> clean Fixer F2
  -> parent commit approved fixes
  -> fresh Analyzer A4

IF A4 reports no unapproved Critical/High findings:
  -> proceed immediately to implementation
ELSE:
  -> optional human checkpoint
  -> clean Fixer F3
  -> parent commit approved fixes
  -> always start persistent convergence Analyzer P after F3

PERSISTENT LOOP:
  -> Analyzer P reads current artifacts, exact prior fixer diffs, and ledger
  -> Analyzer P validates
  IF Analyzer P reports no unapproved Critical/High findings:
    -> proceed immediately to implementation
  ELSE:
    -> optional human checkpoint
    -> separate clean fixer changes only approved findings
    -> parent commit approved fixes
    -> update ledger and receipt
    -> same Analyzer P rereads current artifacts, exact fixer diff, and ledger
    -> repeat Analyzer P -> clean fixer -> Analyzer P until no unapproved
       Critical/High findings or the context/iteration limit is reached

IF still blocked or limit hit:
  -> required human checkpoint
  -> human chooses: continue with a replacement persistent analyzer,
     defer/accept specific risks, proceed despite findings, or stop
```

Analyze rules:

1. Analyzers are read-only.
2. Analyzer runs must preserve the official `/speckit.analyze` contract:
   non-destructive cross-artifact analysis only, with no file writes.
3. Remediation is a separate orchestrator step after findings are captured and,
   when configured, approved.
4. Fixers are separate clean sessions.
5. Fixers never validate their own fixes.
6. The parent orchestrator owns the ledger.
7. The workflow must not require zero findings.
8. The workflow requires zero unapproved Critical/High findings.
9. Medium/Low findings are accepted, deferred, or converted into implementation
   tasks.
10. Fresh analyzers are used for independent discovery.
11. Preserve the persistent analyzer as the fallback convergence reviewer. Its
    session memory may improve continuity, but all findings, fixes, validation
    evidence, and decisions must be persisted in the ledger so the loop can
    resume in a replacement session.
12. The persistent convergence analyzer is used only when A4 reports
    Critical/High findings after the A1/A2 and A3 discovery/validation stages.
    After clean Fixer F3 remediates A4's approved findings, Analyzer P always
    performs the next validation; the workflow must not treat F3's own report as
    independent proof that the findings are fixed.
13. After every persistent-stage fix, Analyzer P must reread the current
    artifacts, the exact fixer diff, and the updated ledger before validating.
    It must not mark a finding fixed from conversation memory alone.
14. After every persistent cycle, update the ledger and analyze receipt. If the
    persistent session disappears, a replacement analyzer resumes from those
    durable artifacts rather than reconstructing history from memory.
15. Stop the persistent analyzer at 80% context usage when the integration
    exposes a reliable context metric. When it does not, use the configured
    persistent-cycle limit plus explicit analyzer self-warning; never claim a
    precise percentage that the integration cannot report.
16. If an analyze pass produces approved actionable findings, spawn a clean
    fixer after the analyze checkpoint and commit the approved fix stage before
    the next analyzer runs.
17. If an analyzer finds no actionable Critical/High items, record the result in
    the ledger and analyze receipt. Do not create a code-fix commit unless a
    ledger-only checkpoint commit is explicitly enabled.
18. Analyze fix commits must cite the related finding IDs or ledger references,
    changed artifacts/files, validation performed, and any findings accepted or
    deferred.
19. Blocking readiness is explicit: Critical/High findings in `open`,
    `approved_for_fix`, or `partially_fixed` status block implementation.
    `deferred` Critical/High findings also block unless a human records an
    approved waiver. `accepted_risk` is non-blocking only when its decision
    records the approver, rationale, scope, and timestamp.

Ledger statuses:

```text
open
approved_for_fix
fixed
partially_fixed
duplicate
false_positive
deferred
accepted_risk
converted_to_task
```

Normalized finding fields:

```text
finding id, assigned by parent
analyzer run id
severity: Critical, High, Medium, or Low
category
concise title and description
artifact/file references
specific evidence
recommended remediation
stable fingerprint for deduplication
status
validation evidence
decision/waiver reference, when applicable
timestamps
```

Analyzer output must be schema-validated before it is merged. Malformed output
is a failed analyzer pass, not a clean result.

Default analyze limits:

```text
initial fresh analyzers: 2
fresh validation analyzers after first fix: 2
persistent convergence cycles: 3
context threshold: 80% when measurable; otherwise configured cycle limit
```

### 5. Implementation

Proceed when analyze succeeds or configuration/human approval allows proceeding.

Implementation should be delegated to Phase Orchestrator:

```text
/speckit.phase-orchestrator.phase all specs/<feature>/tasks.md
```

Implementation stage behavior:

1. One clean worker per phase.
2. Tests first when tasks require tests.
3. Mark completed tasks as `[X]`.
4. Write phase documentation.
5. Run focused validation.
6. Commit one phase at a time when enabled.
7. Stop on blocker, unsafe git state, validation failure, or unresolved
   ambiguity.

Implementation commit behavior is inherited from Phase Orchestrator. Its parent
orchestrator reviews the completed phase, stages only selected-phase files, and
creates one professional Conventional Commit after validation and documentation
checks pass.
Carry forward the same commit body expectations: completed task IDs, changed
files, validation performed, and Markdown documentation path.

### 6. Official Implementation Convergence

After Phase Orchestrator completes the currently known tasks, run the official
post-implementation completeness command:

```text
/speckit.converge
```

This stage is distinct from pre-implementation analyze convergence:

```text
custom artifact analyze convergence
  -> checks consistency across spec.md, plan.md, and tasks.md before coding

/speckit.converge
  -> checks implemented code against the feature artifacts after coding
  -> appends remaining or incomplete implementation work to tasks.md
```

Converge loop:

```text
Phase Orchestrator completes current tasks
-> run /speckit.converge
-> write a converge review packet
-> optional human checkpoint so the operator can see what implementation
   missed, what new tasks were added, and why

IF converge appended tasks:
  -> parent reviews tasks.md diff
  -> parent creates a converge checkpoint commit when enabled
  -> Phase Orchestrator implements only the new/incomplete tasks
  -> per-phase implementation commits remain enabled by default
  -> run /speckit.converge again
  -> repeat until converged or limit reached

IF converge appended no tasks:
  -> record the clean result
  -> optional human checkpoint may show the clean summary without blocking
  -> proceed to practical operator QA

IF converge reaches its configured limit or exposes a blocker:
  -> required human checkpoint
  -> human chooses: continue, accept/defer specific gaps, proceed despite the
     gaps, or stop
```

Converge review packet:

```text
converge pass number
requirements/tasks found incomplete or missing
new task IDs and descriptions
affected implementation areas
evidence or artifact references
files changed by converge
proposed next action
remaining accepted/deferred gaps
```

Converge rules:

1. `/speckit.converge` does not replace automated tests or practical operator
   QA.
2. Treat tasks appended by converge as implementation work and route them back
   through Phase Orchestrator rather than fixing them inside the converge pass.
3. The parent reviews every converge-produced `tasks.md` change before staging
   or continuing.
4. A converge checkpoint commit body must list the converge pass, appended task
   IDs, implementation gaps identified, changed artifacts, validation performed,
   and the next action.
5. When converge makes no file changes, create no converge commit; record the
   no-op and clean result in the implementation receipt.
6. Default maximum converge passes: 3. Hitting the limit requires human input.
7. Every converge pass produces a human-readable packet. Whether it pauses is
   controlled by the unified checkpoint configuration.

### 7. Practical Operator QA

After implementation convergence, run an operator-style QA loop that mimics the
real manual workflow rather than only running unit tests.

Loop:

```text
start app/backend as needed
-> operator agent follows quickstart/manual scenario
-> record failures with steps, expected, actual, logs/screenshots when available
-> optional human checkpoint on findings
-> clean fixer fixes approved failures
-> targeted tests run
-> parent commit approved QA fixes
-> operator reruns flow
-> repeat until clean or limit hit
```

Operator QA should cover:

```text
happy path
edge/error path
auth/session behavior
browser refresh/reconnect behavior
mobile/narrow viewport when relevant
keyboard-only flow when relevant
realistic user/operator sequence
```

V1 uses the best available execution mode:

```text
automated:
  an available agent-native browser tool or user-supplied Playwright/Cypress/
  equivalent command executes the scenarios and captures evidence

assisted_manual:
  the orchestrator starts the application when configured, produces exact
  operator steps, and a human records pass/fail evidence

not_runnable:
  the scenario is recorded as not_run and requires explicit human acceptance
  before final release approval
```

Every scenario must end in exactly one status:

```text
passed
failed
not_run
accepted_risk
```

An unexecuted scenario must never be labeled `passed`.

Example configuration:

```yaml
operator_qa:
  start_command: "npm run dev"
  automated_command: "npm run test:e2e"
  stop_command: null
  manual_fallback: true
  require_evidence: true
  startup_timeout_seconds: 120
  scenario_timeout_seconds: 300
```

Operator QA execution rules:

1. Detect available browser/agent capabilities at runtime rather than claiming
   that every supported integration can automate a browser.
2. When an automated command or browser capability exists, run the applicable
   scenarios and record command/tool, result, and evidence.
3. When automation is unavailable and `manual_fallback` is enabled, generate
   exact numbered steps and pause for the human's results.
4. If neither automated nor assisted execution is possible, mark the scenario
   `not_run`; final acceptance must explicitly accept the gap or stop.
5. Start/stop commands must be project-configured, time-bounded, and limited to
   non-production environments. Attempt configured cleanup even after failure.
6. Track and terminate any process the orchestrator starts even when
   `stop_command` is `null`; an explicit stop command is additional project
   cleanup, not the only process-lifecycle mechanism.
7. Redact secrets and sensitive user data from logs, screenshots, receipts, and
   final reports.

Stop condition:

```text
No P0/P1 practical failures.
No unresolved flow blockers.
Targeted tests pass.
Remaining issues are accepted, deferred, or converted into follow-up tasks.
Every `not_run` scenario is explicitly accepted as a risk or remains blocking.
```

QA fix commits should include the approved practical failure IDs or scenarios,
changed files, targeted tests run, rerun result, and any accepted residual risk.

### 8. Final Safety Run

Run the final verification from a clean state where practical.

```text
run targeted tests
rerun the practical operator flow using its selected automated, assisted, or
explicit not-runnable handling
verify no new P0/P1 issues
verify official converge status is clean or explicitly accepted
produce final report
commit final report checkpoint when artifacts changed
```

Final report includes:

```text
feature/spec path
normalized source idea identity, feature-local path, and content hash
tasks completed
analyze ledger summary
phase commits
prep commits
analyze fix commits
converge passes, appended tasks, decisions, and commits
QA fix commits
tests run
operator QA scenarios and passed/failed/not_run/accepted_risk statuses
remaining accepted risks
final go/no-go recommendation
```

## Unified Human Checkpoints

Human gates, optional feedback, and review packets are one checkpoint system.
The workflow must not configure the same checkpoint independently under separate
`gates` and `human_feedback` sections.

Checkpoint modes:

```text
disabled: do not pause and do not present a packet
auto: write/show the review packet and continue
review: request an approve/revise/defer/proceed decision or free-text feedback;
        may auto-continue after a configured positive timeout
required: block until the human decides; timeouts are not allowed
```

Every enabled checkpoint produces a compact review packet containing:

```text
current stage
artifacts or implementation files changed
validation performed
open decisions
Critical/High analyze findings or P0/P1 QA failures
new tasks or missed work found by /speckit.converge
accepted/deferred risks
proposed next action
```

Human feedback may approve, revise, defer, reject a finding, accept a documented
risk, change priorities, or provide free-text direction. The parent records the
decision in the durable decision ledger and launches a focused worker when a
revision is requested. New decisions append to history rather than erasing prior
decisions.

Recommended checkpoints:

```text
preflight
after clarify
after plan
after tasks
after the initial A1/A2 analyzer batch
after fresh Analyzer A3
after fresh Analyzer A4
after every persistent Analyzer P run
when analyze reaches its context/iteration limit
after implementation phase summaries
after every /speckit.converge pass
when converge reaches its pass limit
before practical QA
after operator QA findings
before final acceptance
```

Recommended default configuration:

```yaml
human_checkpoints:
  review_packet_format: markdown
  record_decisions: true
  review_timeout_seconds: 900
  timeout_action: continue
  checkpoints:
    preflight: required
    after_clarify: review
    after_plan: review
    after_tasks: review
    after_initial_analyzers: review
    after_fresh_analyzer_a3: review
    after_fresh_analyzer_a4: review
    after_each_persistent_analyzer: review
    on_analyze_limit: required
    after_implementation_phase_summary: auto
    after_each_converge: review
    on_converge_limit: required
    before_practical_qa: review
    after_operator_findings: review
    final_acceptance: required
```

The default `after_each_converge: review` checkpoint lets the human see exactly
what implementation missed, which tasks converge appended, and what will happen
next. It may continue after the configured timeout; strict profiles can make it
required and fast profiles can make it `auto`.

Timeout rules:

1. Only `review` mode may use a timeout.
2. A positive integer starts an auto-continue timeout.
3. `null` means wait indefinitely.
4. `0` is invalid because immediate continuation is already represented by
   `auto` and previously made feedback behavior ambiguous.
5. `required` always waits for an explicit decision.

Fast automation profile overrides:

```yaml
human_checkpoints:
  checkpoints:
    after_clarify: auto
    after_plan: review
    after_tasks: auto
    after_initial_analyzers: review
    after_fresh_analyzer_a3: auto
    after_fresh_analyzer_a4: auto
    after_each_persistent_analyzer: auto
    after_each_converge: auto
    before_practical_qa: auto
    after_operator_findings: review
```

Strict review profile sets every enabled checkpoint above to `required`.

## Optional Visual Review

The workflow may optionally generate human-readable review surfaces for:

```text
analyze ledger review
post-implementation recap
operator QA findings recap
```

Agent-Native Visual Plans can be used in local-files mode for this purpose, but
it must remain optional. Markdown ledger and report files are the fallback and
the source of truth.

Privacy rule:

```text
Do not require hosted visual review services for the core workflow.
Prefer local-files mode when using visual review tooling.
```

## Candidate Extension Commands

Initial command set should stay small.

Recommended v1 command:

```text
speckit.ai-loop-orchestrator.run
```

Supported argument modes:

```text
full <idea-file>
prep <idea-file>
analyze <feature-dir>
implement <tasks.md path>
converge <feature-dir>
qa <feature-dir>
status <feature-dir>
```

Possible prompt examples:

```text
/speckit.ai-loop-orchestrator.run full "/path/to/idea-file.md"
/speckit.ai-loop-orchestrator.run analyze specs/003-feature
/speckit.ai-loop-orchestrator.run converge specs/003-feature
/speckit.ai-loop-orchestrator.run qa specs/003-feature
```

Alternative: use separate commands only if the single command becomes too large.

Official extension command constraint:

```text
extension id: ai-loop-orchestrator
command: speckit.ai-loop-orchestrator.run
pattern: speckit.{extension-id}.{command}
```

Do not use `speckit.ai-loop.run` unless the extension ID is changed to
`ai-loop`. Avoid additional dotted command segments because the official
manifest command pattern allows one extension namespace and one command name.

## Extension Packaging Requirements

The public extension must follow the official Spec Kit extension layout.

Minimum package:

```text
extension.yml
commands/
  run.md
skills/
  speckit-ai-loop-orchestrator/
    SKILL.md
    references/
scripts/
  ai_loop_state.py
  analyze_ledger.py
  git_safety.py
  report_receipts.py
templates/
  analyze-ledger.md
  checkpoint-decisions.md
  converge-review.md
  operator-qa.md
  final-report.md
hooks/
  hooks.json, optional
README.md
LICENSE
CHANGELOG.md
.extensionignore
```

Manifest requirements:

```yaml
schema_version: "1.0"
extension:
  id: "ai-loop-orchestrator"
  name: "Spec Kit AI Loop Orchestrator"
  version: "0.1.0"
  description: "Automate the Spec Kit lifecycle from idea file to phased implementation and practical QA."
  author: "awasali14"
  repository: "https://github.com/awasali14/spec-kit-ai-loop-orchestrator"
  license: "MIT"
requires:
  speckit_version: ">=0.12.9"
  tools:
    - name: "python"
      version: ">=3.11"
      required: true
    - name: "git"
      required: false
provides:
  commands:
    - name: "speckit.ai-loop-orchestrator.run"
      file: "commands/run.md"
      description: "Run the AI loop orchestration workflow."
```

Runtime command requirements, verified by preflight rather than assumed to be
installed by the manifest:

```text
speckit.constitution
speckit.specify
speckit.clarify
speckit.checklist
speckit.plan
speckit.tasks
speckit.analyze
speckit.converge
speckit.phase-orchestrator.phase
```

Git is manifest-optional because `--no-commit` is supported, but the default
commit-enabled workflow requires a usable Git worktree and identity at runtime.

Command file requirements:

1. `commands/run.md` must include frontmatter with a concise `description`.
2. Use `$ARGUMENTS` for user-provided mode/path arguments.
3. Any helper scripts referenced by the command must use relative paths that
   remain valid after Spec Kit command registration.
4. Config should live under
   `.specify/extensions/ai-loop-orchestrator/ai-loop-orchestrator-config.yml`,
   with local overrides in `ai-loop-orchestrator-config.local.yml`.
5. Never commit secrets; use environment variables such as
   `SPECKIT_AI_LOOP_ORCHESTRATOR_*` for sensitive or machine-local values.
6. Config must expose commit controls for `enabled`, `after_spec_kit_step`,
   `after_analyze_fix`, `implementation_phase_commits`,
   `after_converge_update`, `after_operator_qa_fix`, and
   `final_report_checkpoint`.

Skill file requirements:

1. The generated skill must be the complete operational workflow for
   skills-first agents.
2. The skill should support the same modes as the command wrapper: `full`,
   `prep`, `analyze`, `implement`, `converge`, `qa`, and `status`.
3. The skill must explicitly call out parent-owned duties: ledger ownership,
   worker spawning, checkpoint decisions, validation review, staging, and
   commits.
4. The skill must instruct analyzers, fixers, operator QA agents, and phase
   workers not to stage, commit, push, or continue into unrelated stages.
5. The skill should use progressive disclosure: keep the main `SKILL.md`
   focused and place templates, worker prompt rules, schemas, and examples in
   `references/` or `templates/`.
6. The skill should invoke helper scripts instead of re-deriving deterministic
   state or parsing rules in natural language.
7. The extension should test that Spec Kit installation registers the workflow
   as a native skill where the target integration supports skills.
8. The skill is the v1 execution and resume authority. It must checkpoint
   `loop-state.json` before and after every external command, worker handoff,
   commit attempt, human checkpoint, converge pass, and QA pass.
9. Before selecting each next lifecycle action, including after a worker
   returns, an external command completes, a human checkpoint resolves, or the
   integration compacts context, the parent must reload and reconcile durable
   state. It must not choose the next action from conversation memory alone.
10. The skill must register every directly delegated subagent run before
    spawning it and capture any integration-native agent ID, session ID, or task
    name returned by the spawn operation so the exact subagent can be reopened
    for debugging or continuation when the integration supports it. It must
    import the equivalent records for nested workers spawned by Phase
    Orchestrator.

Script responsibilities:

1. `ai_loop_state.py`: initialize, read, update, validate, reconcile, and
   summarize `loop-state.json`; register and update subagent runs; record and
   recover an in-flight operation; and return the authoritative next action for
   the parent orchestrator.
2. `analyze_ledger.py`: normalize findings, assign IDs, merge duplicates,
   update statuses, and summarize Critical/High readiness.
3. `git_safety.py`: inspect dirty state, detect unrelated staged files, propose
   checkpoint-owned file sets, and fail before unsafe staging.
4. `report_receipts.py`: generate receipt sections, final report summaries, and
   audit-friendly commit body inputs, including converge review packets.

Hook responsibilities:

1. Verify `.specify/` and `.specify/memory/constitution.md` exist before the
   loop starts.
2. Verify required `.ai-loop` artifacts exist before resuming a stage.
3. Block continuation when unrelated staged changes are present.
4. Optionally remind or block persistent Analyzer P when it is about to cross
   its configured context threshold. This analyzer-specific guard must not
   impose a percentage threshold or forced rotation on the main orchestrator.
5. Do not run analyzer/fixer/implementation/QA loops from hooks.

## Companion Bundle Packaging Requirements

The companion bundle is the recommended installation experience for users who
want the complete lifecycle. It must compose the two independently released
extensions through Spec Kit's bundle mechanism and must not copy their source
files or introduce new runtime behavior.

Bundle contents:

```text
bundle.yml
README.md
LICENSE
CHANGELOG.md
```

Bundle requirements:

1. Pin a tested compatible version of `spec-kit-phase-orchestrator`.
2. Pin a tested compatible version of `spec-kit-ai-loop-orchestrator`.
3. Keep the bundle integration-agnostic unless testing proves that an explicit
   integration constraint is required.
4. Document any non-default extension catalogs required to resolve either
   component.
5. Add no commands, skills, scripts, hooks, state files, or workflow behavior of
   its own.
6. Build a versioned bundle artifact with `specify bundle build` only after
   `specify bundle validate` succeeds.
7. Test installation from a clean Spec Kit project using the same artifact that
   will be published.
8. Verify that bundle installation registers both extension command surfaces
   and that AI Loop Orchestrator can call Phase Orchestrator without a dependency
   error.
9. Verify bundle update and removal behavior, including the case where one of
   the extensions was already installed independently.
10. Release new bundle versions only for tested component-version combinations;
    independent extension releases do not automatically change an existing
    bundle pin.

Installation positioning:

```text
recommended full experience:
  specify bundle install ai-loop-orchestrator-bundle

standalone phase engine:
  install spec-kit-phase-orchestrator independently

advanced/manual composition:
  install both extensions independently
```

The exact installation examples must be verified against the release catalogs
and final component IDs before publication.

## Artifacts To Produce

The extension should produce durable artifacts so clean sessions can resume
without relying on hidden conversation state.

Candidate artifact paths:

```text
specs/<feature>/.ai-loop/
├── loop-state.json
├── intake/
│   └── idea.md
├── analyze-ledger.md
├── analyze-ledger.json
├── checkpoint-decisions.md
├── converge-review.md
├── operator-qa.md
├── final-report.md
└── receipts/
    ├── prep-receipt.md
    ├── analyze-receipt.md
    ├── implementation-receipt.md
    ├── converge-receipt.md
    └── qa-receipt.md
```

State file responsibilities:

```text
schema version
loop id
extension version
overall status
current stage
monotonic state revision
active/in-flight operation and recovery policy
subagent run registry and integration-native session identifiers
last completed operation
authoritative next action
source idea file
feature directory and artifact paths
resolved config snapshot
stage status summaries
analyze attempts and ledger counts
human checkpoint decisions and defaults
commit checkpoint references
implementation phase status
official converge attempts, appended tasks, and status
operator QA status
receipt paths
timestamps
```

Recommended `loop-state.json` shape:

```json
{
  "schema_version": "1.0",
  "loop_id": "20260710-153012-003-example-feature",
  "extension_version": "0.1.0",
  "status": "running",
  "current_stage": "analyze_convergence",
  "state_revision": 42,
  "active_operation": {
    "id": "analyze-a3-merge-001",
    "type": "analyzer_result_merge",
    "status": "running",
    "agent_run_id": "analyze-a3-001",
    "expected_outputs": [
      "specs/003-example-feature/.ai-loop/analyze-ledger.json",
      "specs/003-example-feature/.ai-loop/receipts/analyze-receipt.md"
    ],
    "recovery": "verify_then_retry",
    "started_at": "2026-07-10T16:35:00+05:00"
  },
  "last_completed_operation": "analyze-a3-result-capture",
  "next_action": "reconcile_active_operation",
  "source": {
    "idea_file": "specs/003-example-feature/.ai-loop/intake/idea.md",
    "original_basename": "idea.md",
    "sha256": "<content-sha256>",
    "started_at": "2026-07-10T15:30:12+05:00",
    "started_by": "user"
  },
  "feature": {
    "directory": "specs/003-example-feature",
    "spec": "specs/003-example-feature/spec.md",
    "plan": "specs/003-example-feature/plan.md",
    "tasks": "specs/003-example-feature/tasks.md",
    "quickstart": "specs/003-example-feature/quickstart.md"
  },
  "config": {
    "commits_enabled": true,
    "checkpoint_profile": "default",
    "phase_orchestrator_command": "speckit.phase-orchestrator.phase"
  },
  "agent_runs": [
    {
      "run_id": "analyze-a3-001",
      "role": "analyzer",
      "mode": "fresh",
      "integration": "codex",
      "native_agent_id": "<integration-native-agent-id>",
      "native_session_id": "<integration-native-session-id>",
      "native_task_name": "analyze_a3",
      "reopen_supported": true,
      "parent_operation_id": "analyze-a3-spawn-001",
      "status": "returned",
      "replaces_run_id": null,
      "started_at": "2026-07-10T16:30:00+05:00",
      "last_seen_at": "2026-07-10T16:34:30+05:00"
    }
  ],
  "stages": {
    "prep": {
      "status": "complete",
      "completed_steps": [
        "specify",
        "clarify",
        "plan",
        "checklist",
        "tasks"
      ],
      "commits": []
    },
    "analyze": {
      "status": "running",
      "attempts": 2,
      "open_critical_high": 1,
      "ledger_md": "specs/003-example-feature/.ai-loop/analyze-ledger.md",
      "ledger_json": "specs/003-example-feature/.ai-loop/analyze-ledger.json"
    },
    "implementation": {
      "status": "pending",
      "completed_phases": [],
      "phase_commits": []
    },
    "converge": {
      "status": "pending",
      "attempts": 0,
      "appended_task_ids": [],
      "commits": []
    },
    "operator_qa": {
      "status": "pending",
      "open_p0_p1": null
    },
    "final_safety": {
      "status": "pending"
    }
  },
  "checkpoints": [
    {
      "id": "after_plan",
      "mode": "review",
      "decision": "approved",
      "timestamp": "2026-07-10T16:10:00+05:00"
    }
  ],
  "receipts": {
    "prep": "specs/003-example-feature/.ai-loop/receipts/prep-receipt.md",
    "analyze": "specs/003-example-feature/.ai-loop/receipts/analyze-receipt.md",
    "implementation": "specs/003-example-feature/.ai-loop/receipts/implementation-receipt.md",
    "converge": "specs/003-example-feature/.ai-loop/receipts/converge-receipt.md",
    "qa": "specs/003-example-feature/.ai-loop/receipts/qa-receipt.md"
  },
  "last_updated": "2026-07-10T16:40:00+05:00"
}
```

State file rules:

1. In the selected skill-led design, `loop-state.json` is the authoritative
   execution index and resume contract, not a log dump.
2. Do not store raw prompts, raw tool logs, secrets, or large reports in the
   state file.
3. Store detailed analyze findings in `analyze-ledger.json` and
   `analyze-ledger.md`.
4. Store practical QA detail in `operator-qa.md`.
5. Store narrative run summaries in receipts and `final-report.md`.
6. Every state update should be idempotent and safe to re-run after an
   interrupted session.
7. Update state atomically before and after every stage boundary, worker
   handoff, external command, human checkpoint, and commit attempt.
8. Do not store a private machine-local absolute idea-file path in committed
   artifacts. Copy or normalize intake into a feature-local path and record its
   basename and content hash. Machine-local path metadata belongs only in an
   ignored local file when it is needed for resume.
9. If native Spec Kit workflow packaging is added later, define an explicit
   state migration and single resume authority before enabling it; do not let
   native workflow state and `loop-state.json` independently advance the run.
10. Increment `state_revision` monotonically for every successful state
    transition so stale or duplicated updates can be detected.
11. Before causing side effects, record one `active_operation` with a stable
    operation ID, type, status, expected observable outputs, and recovery
    policy. After verification, clear it, copy its ID to
    `last_completed_operation`, and compute `next_action` atomically.
12. At the beginning of every parent control-loop iteration, reload and
    reconcile `loop-state.json`, relevant receipts, expected outputs, and Git
    state before trusting `next_action` or selecting another transition.
13. Reconciliation must classify an in-flight operation as one of: observably
    completed and safe to finalize; observably not started and safe to run;
    safe to retry idempotently with the same operation ID; or ambiguous/unsafe
    and therefore blocked on a required human checkpoint.
14. Automatic context compaction does not create a separate workflow stage and
    does not require the main orchestrator to stop or rotate. The same parent
    continues by entering the normal reload-and-reconcile control loop.
15. The 80% context rule belongs only to persistent Analyzer P. It must not be
    reused as a limit, warning threshold, or lifecycle policy for the main
    orchestrator.
16. Before spawning any prep worker, analyzer, fixer, phase worker, converge
    worker, or operator QA agent, create an `agent_runs` entry with a stable,
    loop-scoped `run_id`, role, mode, parent operation ID, and `spawn_requested`
    status. Every worker-related `active_operation` must reference that
    `run_id`.
17. After spawning, atomically record every identifier the integration exposes,
    including its native agent ID, session ID, or task name, plus whether the
    integration supports reopening that session. These fields may be `null`
    only when the integration does not expose them; never store credentials,
    transcripts, or raw prompts in the registry.
18. For debugging or continuation, the parent should use the registered native
    identifier to reopen the exact subagent when supported. Before taking any
    new action, the reopened subagent must reread the current durable state,
    relevant ledger or receipt, and exact current diff; its remembered context
    is supporting evidence, not workflow authority.
19. If a registered session is missing or cannot be reopened, mark that run
    `lost` or `unavailable`, create a new run with `replaces_run_id` pointing to
    it, and resume from durable artifacts. If a spawn result is interrupted
    before its native identifiers are recorded, reconcile through the
    integration's agent-listing capability when available; block for human
    review rather than silently spawning a possible duplicate when identity is
    ambiguous.
20. When Phase Orchestrator owns nested phase-worker spawning, its handoff
    contract must export the same logical and native identifiers. AI Loop
    Orchestrator must merge or reference those records before accepting the
    implementation handoff as complete; tracking only the outer Phase
    Orchestrator invocation is insufficient.

### Main Orchestrator Context Recovery

The main orchestrator is the parent control engine started by the human. Its
conversation context is a working cache, while `loop-state.json`, receipts,
ledgers, checkpoint decisions, implementation artifacts, and Git are the
durable workflow record.

The parent repeats this control loop until final acceptance:

```text
reload and validate durable state
-> reconcile any active operation against observable outputs and Git
-> read the authoritative next action
-> record the next active operation before side effects
-> execute or delegate exactly that operation
-> validate its observable result
-> atomically record completion and compute the next action
-> repeat
```

This loop runs after ordinary progress as well as after worker returns, command
completion, human checkpoints, interruptions, or context compaction. The parent
must not depend on detecting that compaction occurred; routine reconciliation
on every iteration makes post-compaction continuation identical to normal
continuation.

If compaction occurs between the before-operation and after-operation state
updates, the parent uses the recorded recovery policy and observable evidence.
It must never assume success or blindly repeat a potentially non-idempotent
operation. A fresh parent session is a fallback only when the original task or
session terminates; automatic compaction alone does not require replacement.

### Development-Only Post-Run Trace Exporter

Use a separate post-run exporter during internal Codex development to replace
manual inspection of the root orchestrator task and every delegated subagent
task. This tool observes persisted Codex thread data after a run; it is not part
of AI Loop Orchestrator, Phase Orchestrator, their prompts, or their runtime
state.

Separation requirements:

1. Keep the exporter in a sibling development-tool repository or an unmerged
   development branch. Do not include it in the extension manifest, generated
   skill, command wrapper, companion bundle, release archive, or main branch.
2. Do not tell the main orchestrator or any subagent that tracing is enabled.
   They must receive no logging instructions, perform no trace writes, and
   spend no context or tokens on developer observability.
3. Run the extension normally in Codex. Invoke the exporter only after the root
   task completes, fails, is cancelled, or is otherwise stopped.
4. Write exported traces outside both the tested repository and its
   `specs/<feature>/.ai-loop/` directory so trace files cannot affect Git
   safety checks, diffs, commits, task selection, or measured behavior.

Post-run collection flow:

```text
select the stored root task by explicit thread ID
or by latest non-ephemeral root task matching repository and time
-> read persisted root turns with thread/read(includeTurns: true)
-> page full persisted turns/items when supported
-> discover child threads from collaboration/spawn records
-> recursively read every analyzer, fixer, phase worker, converge worker,
   operator-QA worker, and other descendant thread
-> order the selected records into one root-and-subagent timeline
-> write human-readable Markdown plus machine-readable JSON/JSONL
```

Export only the developer-facing execution narrative needed to inspect how the
skill was followed:

```text
user prompts
agent messages whose phase is commentary
displayed reasoning summaries, when exposed by the integration
subagent delegation prompts and parent/child thread relationships
context-compaction markers
agent messages whose phase is final_answer
turn/thread completion, failure, cancellation, or interruption status
every persisted tool call, with tool name/type and invocation/completion status
```

Place each tool call in its correct timeline position, but do not export its
result or output. Also omit detailed tool arguments, tool inputs, command
stdout/stderr, web-search contents, and file-change payloads. The exporter
targets the visible execution narrative analogous to Codex's expanded "Worked
for ..." section, not low-level tool tracing and not hidden chain-of-thought.

Recommended output shape:

```text
<external-trace-root>/<run-id>/
├── trace-report.md
├── trace-events.jsonl
├── trace-tree.json
├── export-status.json
└── threads/
    ├── <root-thread-id>.json
    └── <child-thread-id>.json
```

Compaction behavior:

1. Compaction does not require the orchestrator to emit a final answer first.
2. Completed pre-compaction commentary and displayed reasoning-summary items
   remain earlier persisted thread items and must appear before the exported
   `contextCompaction` marker.
3. Commentary produced after compaction follows that marker in the same thread
   timeline; an eventual final answer appears only when the task actually
   finishes.
4. Track compaction independently for the root thread and every subagent
   thread. Multiple compactions are valid.
5. If a run ends without a final answer, export all completed persisted items
   and mark the thread or run incomplete. A partially streamed item that was
   never persisted as complete may be unavailable to a post-run exporter.
6. Post-run export is expected to recover persisted completed items, not every
   token delta, transient streaming notification, hidden reasoning token, or
   data already truncated by the Codex client or tool.

`export-status.json` should make collection completeness visible without adding
another evaluation layer:

```text
root thread found and non-ephemeral
all available turn/item pages exported
expected descendant thread count
exported descendant thread count
missing or incomplete thread IDs
compaction count per thread
overall export status
```

Developer workflow:

```text
run the extension normally in Codex
-> run one post-run export command for the target repository/latest root task
-> developer manually inspects or independently analyzes the export
```

Do not add an automated reviewer, grading agent, evaluation prompt, or further
test pipeline on top of the export. The exporter ends after producing the trace
and completeness metadata.

Expected overhead:

1. A usable exporter covering the root task, recursive subagent discovery,
   commentary/reasoning extraction, compaction markers, and Markdown/JSON
   output is approximately one to two development days.
2. There is no orchestrator/subagent context or token overhead during the run.
3. Post-run collection should normally take seconds, with longer multi-agent
   histories taking proportionally longer to read and serialize.

Receipt responsibilities:

```text
stage/checkpoint name
changed files summary
commit hash, if created
commit subject, if created
commit body summary, if created
no-op reason, if no commit was created
validation performed
accepted risks or follow-up notes
```

## Safety Rules

1. Never run destructive git commands by default.
2. Never push to remotes.
3. Never stage unrelated changes.
4. Stop if unrelated changes are mixed with loop-owned changes in the same file.
5. Never let workers, analyzers, fixers, or operator QA agents stage or commit.
6. Keep secrets out of ledgers, reports, prompts, examples, fixtures, and commit
   bodies.
7. Keep analyzers read-only.
8. Keep fixers scoped to approved findings.
9. Keep operator QA reports concise and evidence-based.
10. Stop persistent analyzer work at 80% context when reliably measurable;
    otherwise stop at the configured cycle limit or explicit degradation signal.
11. Make every auto-proceed decision visible in the final report.
12. Do not rely on hidden conversation state for resume; write stage progress to
    `.ai-loop` artifacts.
13. Treat the generated skill as the agent workflow authority and scripts as the
    deterministic state authority.

## Resolved Design Decisions

1. AI Loop Orchestrator should be skill-backed as its primary agent workflow,
   matching current skills-first Spec Kit/Codex direction and the installed
   Phase Orchestrator pattern.
2. The public package should still be a Spec Kit extension, because extension
   packaging is the portable installation and command registration mechanism.
3. The workflow should not be skill-only. Durable scripts and `.ai-loop`
   artifacts are required for resume, audit, safety checks, and cross-agent
   handoff.
4. Hooks should be narrow guardrails, not the main orchestrator.
5. `loop-state.json` should live under `specs/<feature>/.ai-loop/` as the
   machine-readable authoritative resume index for the skill-led v1 runtime.
6. Do not use the native Spec Kit workflow engine as a second runtime authority
   in v1. It may be evaluated later only with an explicit state migration and
   single-authority design.
7. Keep Phase Orchestrator as a separate required extension rather than
   vendoring its code, and publish a thin optional bundle that pins and installs
   tested versions of Phase Orchestrator and AI Loop Orchestrator together.
8. Run official `/speckit.converge` after phase implementation and route newly
   appended tasks back through Phase Orchestrator until converged or a human
   decides otherwise.
9. Use one unified human checkpoint system that includes review packets,
   approval decisions, and optional free-text feedback.
10. V1 operator QA is hybrid: use automated browser/QA capabilities when
    available, fall back to assisted manual execution, and mark unavailable
    scenarios `not_run` rather than `passed`.
11. Automatic checkpoint commits with professional bodies remain enabled by
    default; `--no-commit` is the explicit optional opt-out.
12. Development tracing uses a separate Codex post-run exporter that reads the
    persisted root and descendant subagent threads without changing any agent
    prompt or runtime behavior. Its output is for direct developer analysis;
    no automated reviewer or additional evaluation layer is required.

## Open Design Questions

1. Should `speckit.ai-loop-orchestrator.run full` create a feature branch, or
   leave branch management to existing Spec Kit/Git extensions?
2. Should visual review support be implemented in v1 or documented as an
   optional integration?

## V1 Scope Recommendation

Build v1 around the core loop without over-expanding:

1. Intake from idea file.
2. Spec Kit prep sequencing.
3. Analyze ledger and convergence protocol.
4. Phase Orchestrator handoff for implementation.
5. Official `/speckit.converge` loop with optional human review after every pass.
6. Hybrid practical operator QA using automated execution when available,
   assisted manual execution otherwise, and explicit `not_run` handling.
7. Final safety run and final report.
8. Unified configurable human checkpoints.
9. Native skill-backed workflow registration for skills-first integrations.
10. Helper scripts for state, ledger, git safety, converge review packets, and
    receipts.
11. A companion Spec Kit bundle that provides the recommended one-step install
    while preserving both extensions as independently releasable components.

Defer advanced features:

1. Hosted visual review integration.
2. A bundled browser automation engine and tool-specific adapters beyond the
   v1 generic browser-capability/user-command interface.
3. Multi-project dashboards.
4. CI integration.
5. Open-source catalog submission until the loop has been tested by internal
   engineers.

## Testing Plan

Test this extension on internal production-like workflows before open sourcing.
Use the testing and release lessons from:

```text
the Spec Kit Phase Orchestrator extension publication plan
```

The test strategy is intentionally multi-agent. The extension must prove that it
is a Spec Kit extension with portable command instructions, not a Codex-only
workflow.

Three-phase agent testing order:

1. Codex: first validation pass, because the workflow and authoring loop start
   here.
2. Claude Code: second validation pass, to prove the command text and extension
   registration are not Codex-specific.
3. Cursor: third validation pass, to prove the workflow survives another
   supported editor/agent environment.

VS Code is optional for the initial release. Test VS Code after the first public
release if time allows or if the official integration docs make it necessary for
submission confidence.

Lessons to carry forward from Phase Orchestrator testing:

1. Prefer portable wording such as `isolated worker context or subagent, if
   supported`; do not require Codex-specific workers.
2. Recheck official Spec Kit integration docs before release instead of
   hardcoding unverified agent-specific paths.
3. Test `specify extension add --dev` in a disposable Spec Kit project.
4. If a new integration is added after the extension is installed, remove and
   re-add or re-register the extension as needed, then confirm the command
   wrapper appears for that integration.
5. Test install from the GitHub release archive before submitting to the Spec
   Kit extension catalog.
6. Record manual test results per agent, including agent name, command, result,
   validation command, wrapper/registration evidence, and caveats.

Minimum validation:

1. Run on a small feature from an idea file.
2. Run on a medium feature with at least three task phases.
3. Confirm analyze ledger prevents repeated rediscovery from blocking progress.
4. Confirm unified human checkpoints run in `disabled`, `auto`, `review`, and
   `required` modes, including valid timeout behavior.
5. Confirm Phase Orchestrator handoff works for `all` mode.
6. Confirm commits are created after each successful Spec Kit prep command that
   changes files.
7. Confirm analyze flow runs A1/A2, ledger/checkpoint, clean F1, parent commit,
   fresh A3, clean F2, fresh A4, and only then the persistent fallback when
   Critical/High findings remain.
8. Confirm persistent Analyzer P rereads current artifacts, the exact fixer diff,
   and the updated ledger after every separate clean fixer pass.
9. Confirm a replacement persistent analyzer can resume solely from durable
   ledger/state/receipt artifacts after the original session is terminated.
10. Confirm malformed analyzer output fails schema validation and cannot be
    interpreted as a clean pass.
11. Confirm implementation commit behavior is inherited from Phase Orchestrator
   and remains one parent-owned commit per completed phase.
12. Confirm `/speckit.converge` runs after implementation, appends incomplete
    work as tasks when applicable, and routes those tasks back through Phase
    Orchestrator.
13. Confirm the after-converge review packet shows missed work, appended task
    IDs, evidence, files changed, and proposed next action in `review` mode.
14. Confirm a clean converge pass creates no empty commit, while an appended-task
    pass creates the configured parent-owned checkpoint commit.
15. Confirm converge stops at its pass limit and requires a human decision.
16. Confirm every orchestrator-created commit includes a professional
   Conventional Commit subject and a meaningful body.
17. Confirm automatic commits are enabled by default across prep, analyze fixes,
    implementation, converge updates, QA fixes, and final report checkpoints.
18. Confirm `--no-commit` and config disable commits across every stage without
    silently changing any other workflow behavior.
19. Confirm commit-enabled preflight stops safely outside a Git worktree, with
    unusable identity, or when checkpoint files overlap unrelated work.
20. Confirm final report is sufficient for a human engineer to audit the run,
    including commit hashes, subjects, body summaries, and changed-file
    summaries.
21. Confirm operator QA uses automated browser/command execution when available,
    assisted manual steps otherwise, and never converts `not_run` into `passed`.
22. Confirm QA startup/scenario timeouts, configured cleanup, evidence capture,
    and secret redaction.
23. Confirm `loop-state.json` supports automatic context compaction and
    crash-and-resume before and after every stage boundary, worker handoff,
    human checkpoint, external command, and commit attempt.
24. Confirm rerunning an interrupted state update is idempotent and does not
    duplicate ledger findings, tasks, receipts, or commits.
25. Confirm no private local paths are present in public examples or committed
    state, including idea files supplied from outside the repository.
26. Confirm paths containing spaces and Unicode work for intake, feature paths,
    scripts, and commit candidate selection.
27. Confirm the extension can be installed from a local dev path using
   `specify extension add --dev`.
28. Confirm `extension.yml` passes manifest validation, requires a Spec Kit
    version that provides `/speckit.converge`, and every command follows
   the `speckit.{extension-id}.{command}` naming pattern.
29. Confirm the registered command appears in Codex after local installation.
30. Confirm the registered command appears and runs in Claude Code after local
    installation or re-registration.
31. Confirm the registered command appears and runs in Cursor after local
    installation or re-registration.
32. Confirm Phase Orchestrator dependency preflight fails with an actionable
    installation message when its command is absent.
33. Confirm the release archive installs cleanly in a disposable Spec Kit
    project before catalog submission.
34. Confirm `specify bundle validate` resolves the pinned Phase Orchestrator and
    AI Loop Orchestrator versions from the documented catalogs.
35. Confirm the built bundle artifact installs both extensions in a clean Spec
    Kit project and registers both command surfaces for Codex, Claude Code, and
    Cursor.
36. Confirm the bundled AI Loop Orchestrator reaches the Phase Orchestrator
    handoff without triggering the missing-dependency preflight failure.
37. Confirm installing the bundle is idempotent when one or both component
    extensions are already installed.
38. Confirm bundle update applies the newly pinned tested versions and preserves
    supported extension-level configuration overrides.
39. Confirm bundle removal does not remove a component that remains required by
    another installed bundle, and document observed behavior for a component
    that was installed independently before the bundle.
40. Confirm the bundle contains no runtime commands, skills, scripts, hooks, or
    copied extension implementation files.
41. Force main-orchestrator context loss immediately after recording an active
    operation, after its side effect succeeds but before completion is recorded,
    after a worker returns, and during commit preparation; confirm reconciliation
    resumes without duplicating durable findings, tasks, receipts, commits, or
    other side effects. Any necessary re-execution must be classified as a safe
    retry and retain the same operation ID.
42. Confirm `ai_loop_state.py` reconciliation distinguishes observable success,
    observable non-execution, safe idempotent retry with the same operation ID,
    and ambiguous/unsafe state that requires human review.
43. Confirm the parent reloads durable state before every next lifecycle action
    and continues normally through context compaction without applying
    persistent Analyzer P's 80% context policy to the main orchestrator.
44. Confirm every delegated subagent receives a stable logical run ID and that
    all integration-native agent IDs, session IDs, or task names exposed by the
    spawn operation are recorded and linked to the parent operation, including
    nested phase-worker records exported by Phase Orchestrator.
45. Confirm a debugging or continuation path can reopen the exact recorded
    subagent when the integration supports it, and otherwise creates a
    replacement linked through `replaces_run_id` that resumes solely from
    durable artifacts without duplicating work.

## Publication Strategy

1. Keep this private/internal until the loop is tested by fellow engineers.
2. Collect failure cases and tune the analyze convergence protocol.
3. Publish Phase Orchestrator and AI Loop Orchestrator as independent extension
   releases with an explicitly tested compatibility pairing.
4. Build and publish the companion bundle only after both pinned extension
   artifacts and their catalog entries are resolvable from a clean project.
5. Make the bundle the recommended full-experience installation path while
   documenting standalone Phase Orchestrator and manual two-extension installs.
6. Prepare public READMEs, examples, extension manifests, bundle manifest,
   licenses, changelogs, and release notes.
7. Include an agent-support note that says Codex, Claude Code, and Cursor are
   tested for the initial release, with VS Code listed as optional/future unless
   it is also tested.
8. Open source only after the workflow produces consistently useful final
   results across the three required agent phases.
9. Create versioned GitHub releases for each verified extension and for the
   bundle artifact.
10. Submit each extension through the official Spec Kit Extension Submission
    process after its public release archive is verified.
11. Submit the companion bundle through the official Bundle Submission process
    after its manifest, component resolution, clean installation, update, and
    removal behavior are verified.
