# Spec Kit AI Loop Orchestrator

Automate the Spec Kit lifecycle from an idea file through analyze convergence,
phased implementation, and practical QA with configurable human checkpoints.

## Status

This extension is currently in the planning stage. See the
[extension plan](./spec-kit-ai-loop-orchestrator-plan.md) for the proposed
workflow, architecture, and delivery roadmap.

## Branch strategy

- `main` contains production-ready, releasable work.
- `dev` is the integration branch for ongoing development.
- Development changes are merged into `dev`, then promoted to `main` through a
  pull request when ready for production.

## Related project

AI Loop Orchestrator is designed to use the independent Spec Kit Phase
Orchestrator extension as its phase-scoped implementation engine.
