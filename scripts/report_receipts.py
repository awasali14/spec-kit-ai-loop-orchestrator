#!/usr/bin/env python3
"""Generate redacted receipts, review packets, QA summaries, and final reports."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CONVENTIONAL_SUBJECT = re.compile(
    r"^(?:feat|fix|docs|test|refactor|chore|build|ci|perf|style|revert)"
    r"(?:\([^)]+\))?!?: .+"
)
QA_STATUSES = {"passed", "failed", "not_run", "accepted_risk"}
QA_MODES = {"automated", "assisted_manual", "not_runnable"}
SECRET_PATTERNS = (
    (re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"), "[REDACTED_OPENAI_KEY]"),
    (re.compile(r"\bgh[opurs]_[A-Za-z0-9]{20,}\b"), "[REDACTED_GITHUB_TOKEN]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED_AWS_ACCESS_KEY]"),
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*"), "Bearer [REDACTED]"),
    (
        re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*([^\s,;]+)"),
        r"\1=[REDACTED]",
    ),
)


class ReportError(ValueError):
    """Raised when report input is invalid or unsafe."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def redact_text(value: Any) -> str:
    text = str(value)
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _clean_text(value: Any, field: str, *, required: bool = True) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str) or (required and not value.strip()):
        raise ReportError(f"{field} must be a {'non-empty ' if required else ''}string")
    return redact_text(value.strip())


def _safe_path(value: str, field: str = "path") -> str:
    normalized = _clean_text(value, field).replace("\\", "/")
    candidate = Path(normalized)
    if candidate.is_absolute() or re.match(r"^[A-Za-z]:/", normalized) or ".." in candidate.parts:
        raise ReportError(f"{field} must be a repository-relative path")
    return candidate.as_posix().lstrip("./")


def _clean_list(value: Any, field: str, *, paths: bool = False) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ReportError(f"{field} must be a list of strings")
    if paths:
        return [_safe_path(item, field) for item in value]
    return [redact_text(item.strip()) for item in value if item.strip()]


def _atomic_write(path: str | Path, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def render_commit_body(
    *,
    stage: str,
    purpose: str,
    changed_files: list[str],
    validations: list[str],
    references: list[str] | None = None,
    risks: list[str] | None = None,
) -> str:
    stage_value = _clean_text(stage, "stage")
    purpose_value = _clean_text(purpose, "purpose")
    files = [_safe_path(item, "changed_file") for item in changed_files]
    checks = _clean_list(validations, "validations")
    refs = _clean_list(references, "references")
    residual = _clean_list(risks, "risks")
    if not files:
        raise ReportError("a commit body requires at least one changed file")
    if not checks:
        raise ReportError("a commit body requires at least one validation")
    lines = [
        purpose_value,
        "",
        f"Lifecycle checkpoint: {stage_value}",
        "",
        "Changed files:",
        *[f"- {item}" for item in files],
        "",
        "Validation:",
        *[f"- {item}" for item in checks],
    ]
    if refs:
        lines.extend(["", "References:", *[f"- {item}" for item in refs]])
    lines.extend(
        [
            "",
            "Accepted risks / follow-up:",
            *([f"- {item}" for item in residual] if residual else ["- None recorded."]),
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_receipt_entry(
    *,
    operation_id: str,
    stage: str,
    checkpoint: str,
    changed_files: list[str],
    validations: list[str],
    commit_hash: str | None = None,
    commit_subject: str | None = None,
    commit_body_summary: str | None = None,
    no_op_reason: str | None = None,
    risks: list[str] | None = None,
) -> str:
    operation = _clean_text(operation_id, "operation_id")
    stage_value = _clean_text(stage, "stage")
    checkpoint_value = _clean_text(checkpoint, "checkpoint")
    files = [_safe_path(item, "changed_file") for item in changed_files]
    checks = _clean_list(validations, "validations")
    residual = _clean_list(risks, "risks")
    if not checks:
        raise ReportError("a receipt requires at least one validation or review record")
    if commit_hash:
        commit_hash = _clean_text(commit_hash, "commit_hash")
        if not re.fullmatch(r"[0-9a-fA-F]{7,64}", commit_hash):
            raise ReportError("commit_hash must be a 7-64 character hexadecimal hash")
        subject = _clean_text(commit_subject, "commit_subject")
        if not CONVENTIONAL_SUBJECT.fullmatch(subject):
            raise ReportError("commit_subject must use Conventional Commit format")
        body_summary = _clean_text(commit_body_summary, "commit_body_summary")
        no_op = None
    else:
        subject = None
        body_summary = None
        no_op = _clean_text(no_op_reason, "no_op_reason")
    lines = [
        f"<!-- receipt:{operation} -->",
        f"## {checkpoint_value}",
        "",
        f"- Operation ID: `{operation}`",
        f"- Stage: `{stage_value}`",
        f"- Recorded: `{utc_now()}`",
        f"- Changed files: {', '.join(f'`{item}`' for item in files) if files else 'none'}",
    ]
    if commit_hash:
        lines.extend(
            [
                f"- Commit: `{commit_hash}`",
                f"- Subject: {subject}",
                f"- Commit body summary: {body_summary}",
            ]
        )
    else:
        lines.append(f"- Commit: not created — {no_op}")
    lines.extend(
        [
            f"- Validation: {'; '.join(checks)}",
            f"- Accepted risks / follow-up: {'; '.join(residual) if residual else 'none'}",
            "",
        ]
    )
    return "\n".join(lines)


def append_receipt(path: str | Path, entry: str, operation_id: str) -> bool:
    target = Path(path)
    existing = target.read_text(encoding="utf-8") if target.exists() else "# Lifecycle Receipt\n\n"
    marker = f"<!-- receipt:{operation_id} -->"
    if marker in existing:
        return False
    content = existing.rstrip() + "\n\n" + entry.rstrip() + "\n"
    _atomic_write(target, content)
    return True


def validate_converge_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ReportError("converge payload must be an object")
    allowed = {
        "pass_number",
        "outcome",
        "incomplete_items",
        "new_tasks",
        "affected_areas",
        "evidence",
        "changed_files",
        "proposed_next_action",
        "remaining_gaps",
    }
    extra = sorted(set(payload) - allowed)
    if extra:
        raise ReportError(f"converge payload has unsupported fields: {', '.join(extra)}")
    pass_number = payload.get("pass_number")
    if not isinstance(pass_number, int) or isinstance(pass_number, bool) or pass_number < 1:
        raise ReportError("pass_number must be a positive integer")
    outcome = payload.get("outcome")
    if outcome not in {"converged", "tasks_appended", "blocked"}:
        raise ReportError("outcome must be converged, tasks_appended, or blocked")
    tasks_raw = payload.get("new_tasks", [])
    if not isinstance(tasks_raw, list):
        raise ReportError("new_tasks must be a list")
    tasks = []
    for index, task in enumerate(tasks_raw):
        if not isinstance(task, dict) or set(task) != {"id", "description"}:
            raise ReportError(f"new_tasks[{index}] requires only id and description")
        tasks.append(
            {
                "id": _clean_text(task["id"], f"new_tasks[{index}].id"),
                "description": _clean_text(
                    task["description"], f"new_tasks[{index}].description"
                ),
            }
        )
    if outcome == "tasks_appended" and not tasks:
        raise ReportError("tasks_appended outcome requires at least one new task")
    if outcome == "converged" and tasks:
        raise ReportError("converged outcome cannot contain new tasks")
    return {
        "pass_number": pass_number,
        "outcome": outcome,
        "incomplete_items": _clean_list(payload.get("incomplete_items"), "incomplete_items"),
        "new_tasks": tasks,
        "affected_areas": _clean_list(payload.get("affected_areas"), "affected_areas"),
        "evidence": _clean_list(payload.get("evidence"), "evidence"),
        "changed_files": _clean_list(payload.get("changed_files"), "changed_files", paths=True),
        "proposed_next_action": _clean_text(
            payload.get("proposed_next_action"), "proposed_next_action"
        ),
        "remaining_gaps": _clean_list(payload.get("remaining_gaps"), "remaining_gaps"),
    }


def _bullets(items: list[str], empty: str = "None.") -> list[str]:
    return [f"- {item}" for item in items] if items else [f"- {empty}"]


def render_converge_review(payload: dict[str, Any]) -> str:
    data = validate_converge_payload(payload)
    task_lines = (
        [f"- `{item['id']}` — {item['description']}" for item in data["new_tasks"]]
        or ["- None."]
    )
    return "\n".join(
        [
            "# Implementation Convergence Review",
            "",
            f"- Pass: **{data['pass_number']}**",
            f"- Outcome: **{data['outcome']}**",
            f"- Changed files: {', '.join(f'`{item}`' for item in data['changed_files']) if data['changed_files'] else 'none'}",
            "",
            "## Incomplete or missing work",
            "",
            *_bullets(data["incomplete_items"]),
            "",
            "## Appended tasks",
            "",
            *task_lines,
            "",
            "## Affected implementation areas",
            "",
            *_bullets(data["affected_areas"]),
            "",
            "## Evidence",
            "",
            *_bullets(data["evidence"]),
            "",
            "## Remaining accepted or deferred gaps",
            "",
            *_bullets(data["remaining_gaps"]),
            "",
            "## Proposed next action",
            "",
            data["proposed_next_action"],
            "",
        ]
    )


def validate_qa_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ReportError("operator QA payload must be an object")
    if payload.get("mode") not in QA_MODES:
        raise ReportError("operator QA mode must be automated, assisted_manual, or not_runnable")
    scenarios_raw = payload.get("scenarios")
    if not isinstance(scenarios_raw, list) or not scenarios_raw:
        raise ReportError("operator QA requires at least one scenario")
    scenarios = []
    identifiers: set[str] = set()
    for index, raw in enumerate(scenarios_raw):
        prefix = f"scenarios[{index}]"
        if not isinstance(raw, dict):
            raise ReportError(f"{prefix} must be an object")
        identifier = _clean_text(raw.get("id"), f"{prefix}.id")
        if identifier in identifiers:
            raise ReportError(f"duplicate QA scenario id: {identifier}")
        identifiers.add(identifier)
        status = raw.get("status")
        if status not in QA_STATUSES:
            raise ReportError(f"{prefix}.status is invalid")
        severity = raw.get("severity")
        if severity is not None and severity not in {"P0", "P1", "P2", "P3"}:
            raise ReportError(f"{prefix}.severity must be P0, P1, P2, P3, or null")
        decision = raw.get("decision")
        if status == "accepted_risk":
            if not isinstance(decision, dict) or not all(
                isinstance(decision.get(key), str) and decision[key].strip()
                for key in ("approver", "rationale", "scope", "timestamp")
            ):
                raise ReportError(
                    f"{prefix}.accepted_risk requires approver, rationale, scope, and timestamp"
                )
        scenarios.append(
            {
                "id": identifier,
                "title": _clean_text(raw.get("title"), f"{prefix}.title"),
                "status": status,
                "severity": severity,
                "flow_blocker": bool(raw.get("flow_blocker", False)),
                "steps": _clean_list(raw.get("steps"), f"{prefix}.steps"),
                "expected": _clean_text(raw.get("expected", ""), f"{prefix}.expected", required=False),
                "actual": _clean_text(raw.get("actual", ""), f"{prefix}.actual", required=False),
                "evidence": _clean_list(raw.get("evidence"), f"{prefix}.evidence"),
                "decision": decision,
            }
        )
    validations = _clean_list(payload.get("validations"), "validations")
    blocking = [
        item["id"]
        for item in scenarios
        if item["status"] == "not_run"
        or (
            item["status"] == "failed"
            and (item["severity"] in {"P0", "P1"} or item["flow_blocker"])
        )
    ]
    counts = Counter(item["status"] for item in scenarios)
    return {
        "mode": payload["mode"],
        "scenarios": scenarios,
        "validations": validations,
        "summary": {
            "counts": {status: counts[status] for status in sorted(QA_STATUSES)},
            "blocking_scenario_ids": blocking,
            "ready": not blocking,
        },
    }


def render_operator_qa(payload: dict[str, Any]) -> str:
    data = validate_qa_payload(payload)
    lines = [
        "# Practical Operator QA",
        "",
        f"- Execution mode: **{data['mode']}**",
        f"- Ready: **{'yes' if data['summary']['ready'] else 'no'}**",
        f"- Blocking scenarios: {', '.join(data['summary']['blocking_scenario_ids']) or 'none'}",
        "",
        "| Scenario | Status | Severity | Flow blocker |",
        "|---|---|---|---|",
    ]
    for scenario in data["scenarios"]:
        lines.append(
            f"| {scenario['id']}: {scenario['title']} | {scenario['status']} | {scenario['severity'] or '—'} | {'yes' if scenario['flow_blocker'] else 'no'} |"
        )
    lines.extend(["", "## Scenario evidence", ""])
    for scenario in data["scenarios"]:
        lines.extend(
            [
                f"### {scenario['id']}: {scenario['title']}",
                "",
                f"- Status: `{scenario['status']}`",
                f"- Steps: {'; '.join(scenario['steps']) or 'not recorded'}",
                f"- Expected: {scenario['expected'] or 'not recorded'}",
                f"- Actual: {scenario['actual'] or 'not recorded'}",
                f"- Evidence: {'; '.join(scenario['evidence']) or 'none'}",
                "",
            ]
        )
    lines.extend(["## Targeted validation", "", *_bullets(data["validations"], "Not recorded."), ""])
    return "\n".join(lines)


def _read_json(path: str | Path, label: str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReportError(f"{label} is not valid JSON: {exc}") from exc


def validate_commits(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise ReportError("commits input must be a list")
    commits = []
    for index, raw in enumerate(payload):
        if not isinstance(raw, dict):
            raise ReportError(f"commits[{index}] must be an object")
        subject = _clean_text(raw.get("subject"), f"commits[{index}].subject")
        if not CONVENTIONAL_SUBJECT.fullmatch(subject):
            raise ReportError(f"commits[{index}].subject is not Conventional Commit format")
        commit_hash = _clean_text(raw.get("hash"), f"commits[{index}].hash")
        if not re.fullmatch(r"[0-9a-fA-F]{7,64}", commit_hash):
            raise ReportError(f"commits[{index}].hash is invalid")
        commits.append(
            {
                "stage": _clean_text(raw.get("stage"), f"commits[{index}].stage"),
                "hash": commit_hash,
                "subject": subject,
                "body_summary": _clean_text(
                    raw.get("body_summary"), f"commits[{index}].body_summary"
                ),
                "changed_files": _clean_list(
                    raw.get("changed_files"), f"commits[{index}].changed_files", paths=True
                ),
            }
        )
    return commits


def render_final_report(
    state: dict[str, Any],
    analyze_ledger: dict[str, Any],
    qa_payload: dict[str, Any],
    commits_payload: list[dict[str, Any]],
    *,
    recommendation: str = "auto",
) -> str:
    for key in ("loop_id", "feature", "source", "stages", "status"):
        if key not in state:
            raise ReportError(f"state is missing {key}")
    if "summary" not in analyze_ledger:
        raise ReportError("analyze ledger is missing summary")
    qa = validate_qa_payload(qa_payload)
    commits = validate_commits(commits_payload)
    analyze_ready = bool(analyze_ledger["summary"].get("ready_for_implementation"))
    converge_ready = state["stages"].get("converge", {}).get("status") == "complete"
    computed_go = analyze_ready and converge_ready and qa["summary"]["ready"]
    if recommendation not in {"auto", "go", "no-go"}:
        raise ReportError("recommendation must be auto, go, or no-go")
    final_recommendation = ("go" if computed_go else "no-go") if recommendation == "auto" else recommendation
    implementation = state["stages"].get("implementation", {})
    converge = state["stages"].get("converge", {})
    lines = [
        "# AI Loop Final Report",
        "",
        f"- Loop ID: `{state['loop_id']}`",
        f"- Feature: `{_safe_path(state['feature']['directory'], 'feature.directory')}`",
        f"- Source intake: `{_safe_path(state['source']['idea_file'], 'source.idea_file')}`",
        f"- Source SHA-256: `{_clean_text(state['source']['sha256'], 'source.sha256')}`",
        f"- Final recommendation: **{final_recommendation.upper()}**",
        "",
        "## Implementation summary",
        "",
        f"- Completed task IDs: {', '.join(implementation.get('completed_task_ids', [])) or 'not recorded'}",
        f"- Completed phases: {', '.join(str(item) for item in implementation.get('completed_phases', [])) or 'none'}",
        f"- Converge passes: {converge.get('attempts', 0)}",
        f"- Converge-appended tasks: {', '.join(converge.get('appended_task_ids', [])) or 'none'}",
        "",
        "## Analyze convergence",
        "",
        f"- Total findings: {analyze_ledger['summary'].get('total', 0)}",
        f"- Blocking Critical/High: {analyze_ledger['summary'].get('blocking_critical_high', 0)}",
        f"- Ready for implementation: {'yes' if analyze_ready else 'no'}",
        "",
        "## Practical operator QA",
        "",
        f"- Mode: {qa['mode']}",
        f"- Blocking scenarios: {', '.join(qa['summary']['blocking_scenario_ids']) or 'none'}",
    ]
    for scenario in qa["scenarios"]:
        lines.append(f"- `{scenario['id']}` {scenario['title']}: **{scenario['status']}**")
    lines.extend(["", "## Checkpoint commits", ""])
    if commits:
        for commit in commits:
            files = ", ".join(f"`{item}`" for item in commit["changed_files"]) or "none"
            lines.extend(
                [
                    f"### {commit['stage']}: `{commit['hash']}`",
                    "",
                    f"- Subject: {commit['subject']}",
                    f"- Changed files: {files}",
                    f"- Body summary: {commit['body_summary']}",
                    "",
                ]
            )
    else:
        lines.extend(["No checkpoint commits were recorded.", ""])
    lines.extend(
        [
            "## Accepted risks and release decision",
            "",
            f"- Analyze accepted risks: {analyze_ledger['summary'].get('by_status', {}).get('accepted_risk', 0)}",
            f"- QA accepted risks: {qa['summary']['counts'].get('accepted_risk', 0)}",
            f"- Recommendation: **{final_recommendation.upper()}**",
            "",
            "> This report intentionally lists only preceding checkpoint commits. The hash of a commit that adds or updates this final report is recorded in durable state and terminal output after that commit succeeds.",
            "",
        ]
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    body = sub.add_parser("commit-body")
    body.add_argument("--stage", required=True)
    body.add_argument("--purpose", required=True)
    body.add_argument("--changed-file", action="append", default=[])
    body.add_argument("--validation", action="append", default=[])
    body.add_argument("--reference", action="append", default=[])
    body.add_argument("--risk", action="append", default=[])
    body.add_argument("--output")

    receipt = sub.add_parser("record-receipt")
    receipt.add_argument("receipt")
    receipt.add_argument("--operation-id", required=True)
    receipt.add_argument("--stage", required=True)
    receipt.add_argument("--checkpoint", required=True)
    receipt.add_argument("--changed-file", action="append", default=[])
    receipt.add_argument("--validation", action="append", default=[])
    receipt.add_argument("--commit-hash")
    receipt.add_argument("--commit-subject")
    receipt.add_argument("--commit-body-summary")
    receipt.add_argument("--no-op-reason")
    receipt.add_argument("--risk", action="append", default=[])

    converge = sub.add_parser("converge-review")
    converge.add_argument("input")
    converge.add_argument("--output", required=True)

    qa = sub.add_parser("operator-qa")
    qa.add_argument("input")
    qa.add_argument("--output", required=True)

    final = sub.add_parser("final-report")
    final.add_argument("--state", required=True)
    final.add_argument("--ledger", required=True)
    final.add_argument("--qa", required=True)
    final.add_argument("--commits", required=True)
    final.add_argument("--recommendation", choices=("auto", "go", "no-go"), default="auto")
    final.add_argument("--output", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "commit-body":
            content = render_commit_body(
                stage=args.stage,
                purpose=args.purpose,
                changed_files=args.changed_file,
                validations=args.validation,
                references=args.reference,
                risks=args.risk,
            )
            if args.output:
                _atomic_write(args.output, content)
                result: Any = {"output": args.output}
            else:
                print(content, end="")
                return 0
        elif args.command == "record-receipt":
            content = render_receipt_entry(
                operation_id=args.operation_id,
                stage=args.stage,
                checkpoint=args.checkpoint,
                changed_files=args.changed_file,
                validations=args.validation,
                commit_hash=args.commit_hash,
                commit_subject=args.commit_subject,
                commit_body_summary=args.commit_body_summary,
                no_op_reason=args.no_op_reason,
                risks=args.risk,
            )
            changed = append_receipt(args.receipt, content, args.operation_id)
            result = {"receipt": args.receipt, "changed": changed}
        elif args.command == "converge-review":
            content = render_converge_review(_read_json(args.input, "converge input"))
            _atomic_write(args.output, content)
            result = {"output": args.output}
        elif args.command == "operator-qa":
            content = render_operator_qa(_read_json(args.input, "operator QA input"))
            _atomic_write(args.output, content)
            result = {"output": args.output}
        elif args.command == "final-report":
            content = render_final_report(
                _read_json(args.state, "state"),
                _read_json(args.ledger, "ledger"),
                _read_json(args.qa, "operator QA"),
                _read_json(args.commits, "commits"),
                recommendation=args.recommendation,
            )
            _atomic_write(args.output, content)
            result = {"output": args.output}
        else:  # pragma: no cover
            raise ReportError("unsupported command")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ReportError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
