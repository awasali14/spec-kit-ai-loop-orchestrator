#!/usr/bin/env python3
"""Durable state manager for Spec Kit AI Loop Orchestrator.

The state file is a compact execution index, not a transcript.  Every mutation
is validated and atomically replaced so an interrupted agent session can reload
and reconcile before selecting another lifecycle action.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


SCHEMA_VERSION = "1.0"
EXTENSION_VERSION = "0.1.0"
STAGES = (
    "preflight",
    "prep",
    "analyze",
    "implementation",
    "converge",
    "operator_qa",
    "final_safety",
)
MODES = ("full", "prep", "analyze", "implement", "converge", "qa", "status")
STAGE_STATUSES = {"pending", "running", "complete", "blocked", "skipped"}
LOOP_STATUSES = {"running", "blocked", "complete", "stopped"}
OPERATION_STATUSES = {"planned", "running"}
RECOVERY_POLICIES = {
    "verify_only",
    "verify_then_retry",
    "retry_idempotent",
    "require_human",
}
AGENT_STATUSES = {
    "spawn_requested",
    "spawned",
    "running",
    "returned",
    "complete",
    "failed",
    "lost",
    "unavailable",
    "cancelled",
}


class StateError(ValueError):
    """Raised when state or a requested transition is invalid."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe_relative(value: str | Path, field: str = "path") -> str:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise StateError(f"{field} must be a repository-relative path: {value}")
    normalized = path.as_posix().lstrip("./")
    if not normalized or normalized == ".":
        raise StateError(f"{field} must not be empty")
    return normalized


def _relative_to_root(path: str | Path, root: Path, field: str) -> tuple[Path, str]:
    candidate = Path(path)
    absolute = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        relative = absolute.relative_to(root.resolve())
    except ValueError as exc:
        raise StateError(f"{field} must stay within the repository: {path}") from exc
    return absolute, _safe_relative(relative, field)


def _atomic_write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    _atomic_write_bytes(path, encoded)


def _stage_defaults() -> dict[str, dict[str, Any]]:
    return {
        "preflight": {"status": "pending", "checks": {}},
        "prep": {"status": "pending", "completed_steps": [], "commits": []},
        "analyze": {
            "status": "pending",
            "attempts": 0,
            "open_critical_high": None,
            "ledger_md": None,
            "ledger_json": None,
            "commits": [],
        },
        "implementation": {
            "status": "pending",
            "completed_phases": [],
            "phase_commits": [],
        },
        "converge": {
            "status": "pending",
            "attempts": 0,
            "appended_task_ids": [],
            "commits": [],
        },
        "operator_qa": {
            "status": "pending",
            "attempts": 0,
            "open_p0_p1": None,
        },
        "final_safety": {"status": "pending"},
    }


def initialize_state(
    *,
    repo_root: Path,
    feature_dir: str | Path,
    idea_file: str | Path,
    extension_version: str = EXTENSION_VERSION,
    commits_enabled: bool = True,
    checkpoint_profile: str = "default",
    loop_id: str | None = None,
) -> tuple[Path, dict[str, Any]]:
    root = repo_root.resolve()
    feature_absolute, feature_relative = _relative_to_root(feature_dir, root, "feature_dir")
    idea_absolute = Path(idea_file).expanduser().resolve()
    if not idea_absolute.is_file():
        raise StateError(f"idea_file does not exist or is not a file: {idea_file}")

    content = idea_absolute.read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    ai_loop_dir = feature_absolute / ".ai-loop"
    intake_path = ai_loop_dir / "intake" / "idea.md"
    state_path = ai_loop_dir / "loop-state.json"
    if state_path.exists():
        existing = load_state(state_path)
        if existing["source"]["sha256"] == digest:
            return state_path, existing
        raise StateError(f"state already exists for a different idea: {state_path}")

    _atomic_write_bytes(intake_path, content)
    receipts_dir = f"{feature_relative}/.ai-loop/receipts"
    started_at = utc_now()
    generated_loop_id = loop_id or (
        datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        + "-"
        + Path(feature_relative).name
    )
    state: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "loop_id": generated_loop_id,
        "extension_version": extension_version,
        "status": "running",
        "current_stage": "preflight",
        "state_revision": 1,
        "active_operation": None,
        "last_completed_operation": None,
        "next_action": "run_preflight",
        "source": {
            "idea_file": f"{feature_relative}/.ai-loop/intake/idea.md",
            "original_basename": idea_absolute.name,
            "sha256": digest,
            "started_at": started_at,
            "started_by": "user",
        },
        "feature": {
            "directory": feature_relative,
            "spec": f"{feature_relative}/spec.md",
            "plan": f"{feature_relative}/plan.md",
            "tasks": f"{feature_relative}/tasks.md",
            "quickstart": f"{feature_relative}/quickstart.md",
        },
        "config": {
            "commits_enabled": bool(commits_enabled),
            "checkpoint_profile": checkpoint_profile,
            "phase_orchestrator_command": "speckit.phase-orchestrator.phase",
        },
        "agent_runs": [],
        "stages": _stage_defaults(),
        "checkpoints": [],
        "receipts": {
            "prep": f"{receipts_dir}/prep-receipt.md",
            "analyze": f"{receipts_dir}/analyze-receipt.md",
            "implementation": f"{receipts_dir}/implementation-receipt.md",
            "converge": f"{receipts_dir}/converge-receipt.md",
            "qa": f"{receipts_dir}/qa-receipt.md",
        },
        "last_updated": started_at,
    }
    validate_state(state)
    _atomic_write_json(state_path, state)
    return state_path, state


def load_state(path: str | Path) -> dict[str, Any]:
    state_path = Path(path)
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise StateError(f"state file not found: {state_path}") from exc
    except json.JSONDecodeError as exc:
        raise StateError(f"state file is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise StateError("state root must be an object")
    validate_state(payload)
    return payload


def validate_state(state: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "loop_id",
        "extension_version",
        "status",
        "current_stage",
        "state_revision",
        "active_operation",
        "next_action",
        "source",
        "feature",
        "agent_runs",
        "stages",
        "checkpoints",
        "receipts",
        "last_updated",
    }
    missing = sorted(required - state.keys())
    if missing:
        raise StateError(f"state is missing required fields: {', '.join(missing)}")
    if state["schema_version"] != SCHEMA_VERSION:
        raise StateError(f"unsupported schema_version: {state['schema_version']}")
    if state["status"] not in LOOP_STATUSES:
        raise StateError(f"invalid loop status: {state['status']}")
    if state["current_stage"] not in STAGES:
        raise StateError(f"invalid current_stage: {state['current_stage']}")
    if not isinstance(state["state_revision"], int) or state["state_revision"] < 1:
        raise StateError("state_revision must be a positive integer")
    if not isinstance(state["next_action"], str) or not state["next_action"]:
        raise StateError("next_action must be a non-empty string")

    for key in ("idea_file",):
        _safe_relative(state["source"][key], f"source.{key}")
    for key, value in state["feature"].items():
        _safe_relative(value, f"feature.{key}")
    for key, value in state["receipts"].items():
        _safe_relative(value, f"receipts.{key}")

    if set(state["stages"]) != set(STAGES):
        raise StateError("stages must contain exactly the supported lifecycle stages")
    for stage_name, stage in state["stages"].items():
        if not isinstance(stage, dict) or stage.get("status") not in STAGE_STATUSES:
            raise StateError(f"invalid status for stage {stage_name}")

    operation = state["active_operation"]
    if operation is not None:
        if not isinstance(operation, dict):
            raise StateError("active_operation must be an object or null")
        for key in ("id", "type", "status", "expected_outputs", "recovery", "started_at"):
            if key not in operation:
                raise StateError(f"active_operation is missing {key}")
        if operation["status"] not in OPERATION_STATUSES:
            raise StateError("invalid active operation status")
        if operation["recovery"] not in RECOVERY_POLICIES:
            raise StateError("invalid active operation recovery policy")
        if not isinstance(operation["expected_outputs"], list):
            raise StateError("active_operation.expected_outputs must be a list")
        for output in operation["expected_outputs"]:
            _safe_relative(output, "active_operation.expected_outputs")

    if not isinstance(state["agent_runs"], list):
        raise StateError("agent_runs must be a list")
    run_ids: set[str] = set()
    for run in state["agent_runs"]:
        if not isinstance(run, dict) or not run.get("run_id"):
            raise StateError("every agent run requires a run_id")
        if run["run_id"] in run_ids:
            raise StateError(f"duplicate agent run_id: {run['run_id']}")
        run_ids.add(run["run_id"])
        if run.get("status") not in AGENT_STATUSES:
            raise StateError(f"invalid agent status for {run['run_id']}")
    for run in state["agent_runs"]:
        replacement = run.get("replaces_run_id")
        if replacement and replacement not in run_ids:
            raise StateError(f"replacement target is not registered: {replacement}")


Mutator = Callable[[dict[str, Any]], bool]


def mutate_state(path: str | Path, mutator: Mutator) -> dict[str, Any]:
    state_path = Path(path)
    original = load_state(state_path)
    updated = copy.deepcopy(original)
    changed = mutator(updated)
    if not changed:
        return original
    updated["state_revision"] = original["state_revision"] + 1
    updated["last_updated"] = utc_now()
    validate_state(updated)
    _atomic_write_json(state_path, updated)
    return updated


def start_operation(
    path: str | Path,
    *,
    operation_id: str,
    operation_type: str,
    expected_outputs: list[str] | None = None,
    recovery: str = "verify_then_retry",
    agent_run_id: str | None = None,
) -> dict[str, Any]:
    if recovery not in RECOVERY_POLICIES:
        raise StateError(f"invalid recovery policy: {recovery}")
    outputs = [_safe_relative(item, "expected_output") for item in (expected_outputs or [])]

    def apply(state: dict[str, Any]) -> bool:
        active = state["active_operation"]
        desired = {
            "id": operation_id,
            "type": operation_type,
            "status": "running",
            "agent_run_id": agent_run_id,
            "expected_outputs": outputs,
            "recovery": recovery,
        }
        if active:
            comparable = {key: active.get(key) for key in desired}
            if comparable == desired:
                return False
            raise StateError(f"operation already active: {active['id']}")
        if state.get("last_completed_operation") == operation_id:
            return False
        desired["started_at"] = utc_now()
        state["active_operation"] = desired
        state["next_action"] = "reconcile_active_operation"
        return True

    return mutate_state(path, apply)


def complete_operation(
    path: str | Path,
    *,
    operation_id: str,
    next_action: str,
    stage: str | None = None,
    stage_status: str | None = None,
) -> dict[str, Any]:
    if stage is not None and stage not in STAGES:
        raise StateError(f"invalid stage: {stage}")
    if stage_status is not None and stage_status not in STAGE_STATUSES:
        raise StateError(f"invalid stage status: {stage_status}")

    def apply(state: dict[str, Any]) -> bool:
        active = state["active_operation"]
        if active is None:
            if state.get("last_completed_operation") == operation_id:
                return False
            raise StateError("no operation is active")
        if active["id"] != operation_id:
            raise StateError(f"active operation is {active['id']}, not {operation_id}")
        state["active_operation"] = None
        state["last_completed_operation"] = operation_id
        state["next_action"] = next_action
        if stage is not None:
            state["current_stage"] = stage
        if stage_status is not None:
            target = stage or state["current_stage"]
            state["stages"][target]["status"] = stage_status
        return True

    return mutate_state(path, apply)


def classify_reconciliation(
    state: dict[str, Any], *, repo_root: Path, evidence_status: str | None = None
) -> dict[str, Any]:
    operation = state["active_operation"]
    if operation is None:
        return {"classification": "no_active_operation", "operation_id": None}
    allowed_evidence = {"completed", "not_started", "retryable", "ambiguous"}
    if evidence_status is not None and evidence_status not in allowed_evidence:
        raise StateError(f"invalid evidence_status: {evidence_status}")

    outputs = operation["expected_outputs"]
    present = [item for item in outputs if (repo_root / item).exists()]
    missing = [item for item in outputs if item not in present]
    if evidence_status == "completed" or (outputs and not missing):
        classification = "observably_completed"
    elif evidence_status == "not_started":
        classification = "observably_not_started"
    elif evidence_status == "retryable":
        classification = "safe_idempotent_retry"
    elif evidence_status == "ambiguous" or (present and missing):
        classification = "ambiguous_requires_human"
    elif operation["recovery"] == "retry_idempotent":
        classification = "safe_idempotent_retry"
    elif operation["recovery"] == "require_human":
        classification = "ambiguous_requires_human"
    else:
        # Missing outputs alone cannot prove a non-idempotent side effect never
        # happened. The parent must supply affirmative evidence or pause.
        classification = "ambiguous_requires_human"
    return {
        "classification": classification,
        "operation_id": operation["id"],
        "recovery": operation["recovery"],
        "present_outputs": present,
        "missing_outputs": missing,
    }


def set_stage(
    path: str | Path,
    *,
    stage: str,
    status: str,
    next_action: str,
    values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if stage not in STAGES:
        raise StateError(f"invalid stage: {stage}")
    if status not in STAGE_STATUSES:
        raise StateError(f"invalid stage status: {status}")

    def apply(state: dict[str, Any]) -> bool:
        desired = dict(values or {})
        desired["status"] = status
        changed = (
            state["current_stage"] != stage
            or state["next_action"] != next_action
            or any(state["stages"][stage].get(key) != value for key, value in desired.items())
        )
        if not changed:
            return False
        state["current_stage"] = stage
        state["next_action"] = next_action
        state["stages"][stage].update(desired)
        if status == "blocked":
            state["status"] = "blocked"
        elif state["status"] == "blocked":
            state["status"] = "running"
        return True

    return mutate_state(path, apply)


def record_checkpoint(
    path: str | Path,
    *,
    checkpoint_id: str,
    mode: str,
    decision: str,
    approver: str | None = None,
    rationale: str | None = None,
) -> dict[str, Any]:
    if mode not in {"disabled", "auto", "review", "required"}:
        raise StateError(f"invalid checkpoint mode: {mode}")

    def apply(state: dict[str, Any]) -> bool:
        comparable = {
            "id": checkpoint_id,
            "mode": mode,
            "decision": decision,
            "approver": approver,
            "rationale": rationale,
        }
        if state["checkpoints"]:
            previous = state["checkpoints"][-1]
            if all(previous.get(key) == value for key, value in comparable.items()):
                return False
        state["checkpoints"].append({**comparable, "timestamp": utc_now()})
        return True

    return mutate_state(path, apply)


def register_agent(
    path: str | Path,
    *,
    run_id: str,
    role: str,
    mode: str,
    parent_operation_id: str,
    integration: str | None = None,
    replaces_run_id: str | None = None,
    status: str = "spawn_requested",
) -> dict[str, Any]:
    if status not in AGENT_STATUSES:
        raise StateError(f"invalid agent status: {status}")

    def apply(state: dict[str, Any]) -> bool:
        existing = next((run for run in state["agent_runs"] if run["run_id"] == run_id), None)
        immutable = {
            "run_id": run_id,
            "role": role,
            "mode": mode,
            "integration": integration,
            "parent_operation_id": parent_operation_id,
            "replaces_run_id": replaces_run_id,
        }
        if existing:
            if all(existing.get(key) == value for key, value in immutable.items()):
                return False
            raise StateError(f"agent run_id already registered with different data: {run_id}")
        if replaces_run_id and not any(
            run["run_id"] == replaces_run_id for run in state["agent_runs"]
        ):
            raise StateError(f"replacement target is not registered: {replaces_run_id}")
        timestamp = utc_now()
        state["agent_runs"].append(
            {
                **immutable,
                "native_agent_id": None,
                "native_session_id": None,
                "native_task_name": None,
                "reopen_supported": None,
                "status": status,
                "started_at": timestamp,
                "last_seen_at": timestamp,
            }
        )
        return True

    return mutate_state(path, apply)


def update_agent(
    path: str | Path,
    *,
    run_id: str,
    status: str,
    native_agent_id: str | None = None,
    native_session_id: str | None = None,
    native_task_name: str | None = None,
    reopen_supported: bool | None = None,
) -> dict[str, Any]:
    if status not in AGENT_STATUSES:
        raise StateError(f"invalid agent status: {status}")

    def apply(state: dict[str, Any]) -> bool:
        run = next((item for item in state["agent_runs"] if item["run_id"] == run_id), None)
        if run is None:
            raise StateError(f"agent run is not registered: {run_id}")
        updates = {
            "status": status,
            "native_agent_id": native_agent_id,
            "native_session_id": native_session_id,
            "native_task_name": native_task_name,
            "reopen_supported": reopen_supported,
        }
        changed = any(value is not None and run.get(key) != value for key, value in updates.items())
        changed = changed or run["status"] != status
        if not changed:
            return False
        for key, value in updates.items():
            if value is not None or key == "status":
                run[key] = value
        run["last_seen_at"] = utc_now()
        return True

    return mutate_state(path, apply)


def state_summary(state: dict[str, Any]) -> dict[str, Any]:
    return {
        "loop_id": state["loop_id"],
        "status": state["status"],
        "current_stage": state["current_stage"],
        "state_revision": state["state_revision"],
        "active_operation": (
            state["active_operation"]["id"] if state["active_operation"] else None
        ),
        "next_action": state["next_action"],
        "feature_directory": state["feature"]["directory"],
        "stages": {name: value["status"] for name, value in state["stages"].items()},
        "agent_runs": len(state["agent_runs"]),
    }


def parse_invocation(arguments: list[str]) -> dict[str, Any]:
    """Parse the portable command's small, deliberately strict argument surface."""
    tokens = list(arguments)
    if tokens and tokens[0] == "--":
        tokens = tokens[1:]
    no_commit = False
    positionals: list[str] = []
    for token in tokens:
        if token == "--no-commit":
            no_commit = True
        elif token.startswith("--"):
            raise StateError(f"unsupported option: {token}")
        else:
            positionals.append(token)
    if not positionals:
        raise StateError(f"mode is required; choose one of: {', '.join(MODES)}")
    mode = positionals[0].lower()
    if mode not in MODES:
        raise StateError(f"unsupported mode: {positionals[0]}")
    if len(positionals) != 2:
        raise StateError(f"{mode} mode requires exactly one idea, feature, or tasks path")
    return {"mode": mode, "target": positionals[1], "no_commit": no_commit}


def _json_object(value: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("value must decode to a JSON object")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    invocation = sub.add_parser("parse-invocation")
    invocation.add_argument("arguments", nargs=argparse.REMAINDER)

    init = sub.add_parser("init", help="Initialize durable state and normalized intake")
    init.add_argument("--feature-dir", required=True)
    init.add_argument("--idea-file", required=True)
    init.add_argument("--repo-root", default=".")
    init.add_argument("--extension-version", default=EXTENSION_VERSION)
    init.add_argument("--loop-id")
    init.add_argument("--no-commit", action="store_true")
    init.add_argument("--checkpoint-profile", default="default")

    for name in ("show", "validate", "next"):
        item = sub.add_parser(name)
        item.add_argument("state")
    show = sub.choices["show"]
    show.add_argument("--summary", action="store_true")
    next_parser = sub.choices["next"]
    next_parser.add_argument("--repo-root", default=".")
    next_parser.add_argument(
        "--evidence-status", choices=("completed", "not_started", "retryable", "ambiguous")
    )

    start = sub.add_parser("start-operation")
    start.add_argument("state")
    start.add_argument("--id", required=True)
    start.add_argument("--type", required=True)
    start.add_argument("--expected-output", action="append", default=[])
    start.add_argument("--recovery", choices=sorted(RECOVERY_POLICIES), default="verify_then_retry")
    start.add_argument("--agent-run-id")

    complete = sub.add_parser("complete-operation")
    complete.add_argument("state")
    complete.add_argument("--id", required=True)
    complete.add_argument("--next-action", required=True)
    complete.add_argument("--stage", choices=STAGES)
    complete.add_argument("--stage-status", choices=sorted(STAGE_STATUSES))

    stage = sub.add_parser("set-stage")
    stage.add_argument("state")
    stage.add_argument("--stage", choices=STAGES, required=True)
    stage.add_argument("--status", choices=sorted(STAGE_STATUSES), required=True)
    stage.add_argument("--next-action", required=True)
    stage.add_argument("--values", type=_json_object, default={})

    checkpoint = sub.add_parser("record-checkpoint")
    checkpoint.add_argument("state")
    checkpoint.add_argument("--id", required=True)
    checkpoint.add_argument("--mode", choices=("disabled", "auto", "review", "required"), required=True)
    checkpoint.add_argument("--decision", required=True)
    checkpoint.add_argument("--approver")
    checkpoint.add_argument("--rationale")

    register = sub.add_parser("register-agent")
    register.add_argument("state")
    register.add_argument("--run-id", required=True)
    register.add_argument("--role", required=True)
    register.add_argument("--mode", required=True)
    register.add_argument("--parent-operation-id", required=True)
    register.add_argument("--integration")
    register.add_argument("--replaces-run-id")
    register.add_argument("--status", choices=sorted(AGENT_STATUSES), default="spawn_requested")

    update = sub.add_parser("update-agent")
    update.add_argument("state")
    update.add_argument("--run-id", required=True)
    update.add_argument("--status", choices=sorted(AGENT_STATUSES), required=True)
    update.add_argument("--native-agent-id")
    update.add_argument("--native-session-id")
    update.add_argument("--native-task-name")
    reopen = update.add_mutually_exclusive_group()
    reopen.add_argument("--reopen-supported", dest="reopen_supported", action="store_true")
    reopen.add_argument("--reopen-unsupported", dest="reopen_supported", action="store_false")
    update.set_defaults(reopen_supported=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "parse-invocation":
            output = parse_invocation(args.arguments)
        elif args.command == "init":
            path, result = initialize_state(
                repo_root=Path(args.repo_root),
                feature_dir=args.feature_dir,
                idea_file=args.idea_file,
                extension_version=args.extension_version,
                commits_enabled=not args.no_commit,
                checkpoint_profile=args.checkpoint_profile,
                loop_id=args.loop_id,
            )
            output: Any = {"state_path": path.as_posix(), "state": state_summary(result)}
        elif args.command == "show":
            result = load_state(args.state)
            output = state_summary(result) if args.summary else result
        elif args.command == "validate":
            result = load_state(args.state)
            output = {"valid": True, "state_revision": result["state_revision"]}
        elif args.command == "next":
            result = load_state(args.state)
            output = {
                "next_action": result["next_action"],
                "reconciliation": classify_reconciliation(
                    result,
                    repo_root=Path(args.repo_root).resolve(),
                    evidence_status=args.evidence_status,
                ),
            }
        elif args.command == "start-operation":
            result = start_operation(
                args.state,
                operation_id=args.id,
                operation_type=args.type,
                expected_outputs=args.expected_output,
                recovery=args.recovery,
                agent_run_id=args.agent_run_id,
            )
            output = state_summary(result)
        elif args.command == "complete-operation":
            result = complete_operation(
                args.state,
                operation_id=args.id,
                next_action=args.next_action,
                stage=args.stage,
                stage_status=args.stage_status,
            )
            output = state_summary(result)
        elif args.command == "set-stage":
            result = set_stage(
                args.state,
                stage=args.stage,
                status=args.status,
                next_action=args.next_action,
                values=args.values,
            )
            output = state_summary(result)
        elif args.command == "record-checkpoint":
            result = record_checkpoint(
                args.state,
                checkpoint_id=args.id,
                mode=args.mode,
                decision=args.decision,
                approver=args.approver,
                rationale=args.rationale,
            )
            output = state_summary(result)
        elif args.command == "register-agent":
            result = register_agent(
                args.state,
                run_id=args.run_id,
                role=args.role,
                mode=args.mode,
                parent_operation_id=args.parent_operation_id,
                integration=args.integration,
                replaces_run_id=args.replaces_run_id,
                status=args.status,
            )
            output = state_summary(result)
        elif args.command == "update-agent":
            result = update_agent(
                args.state,
                run_id=args.run_id,
                status=args.status,
                native_agent_id=args.native_agent_id,
                native_session_id=args.native_session_id,
                native_task_name=args.native_task_name,
                reopen_supported=args.reopen_supported,
            )
            output = state_summary(result)
        else:  # pragma: no cover - argparse enforces the command set
            parser.error("unsupported command")
            return 2
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0
    except (OSError, StateError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
