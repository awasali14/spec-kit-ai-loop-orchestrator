---
description: "Run or resume the AI-assisted Spec Kit lifecycle from an idea file through phased implementation, convergence, practical QA, and final reporting."
---

# Spec Kit AI Loop Orchestrator

Arguments supplied by the operator:

```text
$ARGUMENTS
```

Load and follow the complete workflow at
`.specify/extensions/ai-loop-orchestrator/skills/speckit-ai-loop-orchestrator/SKILL.md`.
Treat that skill and the feature's durable `.ai-loop/loop-state.json` as the
workflow authorities. If the skill is missing, stop and report an incomplete
extension installation; do not improvise the lifecycle from this wrapper.

Pass `$ARGUMENTS` to the skill unchanged. Supported modes are `full`, `prep`,
`analyze`, `implement`, `converge`, `qa`, and `status`. The optional
`--no-commit` flag disables every orchestrator-created commit for the run.
