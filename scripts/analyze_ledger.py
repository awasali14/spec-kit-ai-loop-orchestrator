#!/usr/bin/env python3
"""Normalize analyzer output into a durable, deduplicated readiness ledger."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


SCHEMA_VERSION = "1.0"
SEVERITIES = ("Critical", "High", "Medium", "Low")
SEVERITY_MAP = {item.lower(): item for item in SEVERITIES}
STATUSES = {
    "open",
    "approved_for_fix",
    "fixed",
    "partially_fixed",
    "duplicate",
    "false_positive",
    "deferred",
    "accepted_risk",
    "converted_to_task",
}
BLOCKING_STATUSES = {"open", "approved_for_fix", "partially_fixed", "deferred"}
NON_BLOCKING_STATUSES = {
    "fixed",
    "duplicate",
    "false_positive",
    "accepted_risk",
    "converted_to_task",
}


class LedgerError(ValueError):
    """Raised for malformed analyzer output or an invalid ledger transition."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _safe_relative(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LedgerError(f"{field} must be a non-empty string")
    candidate = value.strip().replace("\\", "/")
    if candidate.startswith("/") or re.match(r"^[A-Za-z]:/", candidate):
        raise LedgerError(f"{field} must not contain an absolute machine path")
    if ".." in Path(candidate.split(":", 1)[0]).parts:
        raise LedgerError(f"{field} must not escape the repository")
    return candidate


def _string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LedgerError(f"{field} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, field: str, *, require_nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise LedgerError(f"{field} must be a list of strings")
    normalized = [item.strip() for item in value if item.strip()]
    if require_nonempty and not normalized:
        raise LedgerError(f"{field} must contain at least one item")
    return normalized


def _canonical_fingerprint(finding: dict[str, Any]) -> str:
    supplied = finding.get("fingerprint")
    if supplied is not None:
        return _string(supplied, "finding.fingerprint").lower()
    stable = {
        "category": finding["category"].casefold(),
        "title": finding["title"].casefold(),
        "artifact_refs": sorted(item.casefold() for item in finding["artifact_refs"]),
    }
    return hashlib.sha256(
        json.dumps(stable, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def validate_analyzer_output(payload: Any, expected_run_id: str | None = None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise LedgerError("analyzer output root must be an object")
    extra_root = sorted(set(payload) - {"run_id", "findings"})
    if extra_root:
        raise LedgerError(f"analyzer output contains unsupported fields: {', '.join(extra_root)}")
    run_id = _string(payload.get("run_id"), "run_id")
    if expected_run_id and run_id != expected_run_id:
        raise LedgerError(f"analyzer run_id is {run_id}, expected {expected_run_id}")
    raw_findings = payload.get("findings")
    if not isinstance(raw_findings, list):
        raise LedgerError("findings must be a list")

    findings: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_findings):
        prefix = f"findings[{index}]"
        if not isinstance(raw, dict):
            raise LedgerError(f"{prefix} must be an object")
        allowed = {
            "severity",
            "category",
            "title",
            "description",
            "artifact_refs",
            "evidence",
            "recommended_remediation",
            "fingerprint",
        }
        extra = sorted(set(raw) - allowed)
        if extra:
            raise LedgerError(f"{prefix} contains unsupported fields: {', '.join(extra)}")
        severity_raw = _string(raw.get("severity"), f"{prefix}.severity").lower()
        if severity_raw not in SEVERITY_MAP:
            raise LedgerError(f"{prefix}.severity must be Critical, High, Medium, or Low")
        artifact_refs = _string_list(
            raw.get("artifact_refs"), f"{prefix}.artifact_refs", require_nonempty=True
        )
        artifact_refs = [_safe_relative(item, f"{prefix}.artifact_refs") for item in artifact_refs]
        normalized = {
            "severity": SEVERITY_MAP[severity_raw],
            "category": _string(raw.get("category"), f"{prefix}.category"),
            "title": _string(raw.get("title"), f"{prefix}.title"),
            "description": _string(raw.get("description"), f"{prefix}.description"),
            "artifact_refs": artifact_refs,
            "evidence": _string_list(
                raw.get("evidence"), f"{prefix}.evidence", require_nonempty=True
            ),
            "recommended_remediation": _string(
                raw.get("recommended_remediation"),
                f"{prefix}.recommended_remediation",
            ),
        }
        if "fingerprint" in raw:
            normalized["fingerprint"] = raw["fingerprint"]
        normalized["fingerprint"] = _canonical_fingerprint(normalized)
        findings.append(normalized)
    return {"run_id": run_id, "findings": findings}


def new_ledger(feature_dir: str) -> dict[str, Any]:
    feature = _safe_relative(feature_dir, "feature_dir")
    timestamp = utc_now()
    return {
        "schema_version": SCHEMA_VERSION,
        "feature_dir": feature,
        "revision": 1,
        "analyzer_runs": [],
        "findings": [],
        "summary": {
            "total": 0,
            "by_severity": {severity: 0 for severity in SEVERITIES},
            "by_status": {status: 0 for status in sorted(STATUSES)},
            "blocking_critical_high": 0,
            "blocking_finding_ids": [],
            "ready_for_implementation": True,
        },
        "created_at": timestamp,
        "last_updated": timestamp,
    }


def initialize_ledger(path: str | Path, feature_dir: str) -> dict[str, Any]:
    ledger_path = Path(path)
    if ledger_path.exists():
        return load_ledger(ledger_path)
    ledger = new_ledger(feature_dir)
    validate_ledger(ledger)
    _atomic_write_json(ledger_path, ledger)
    return ledger


def load_ledger(path: str | Path) -> dict[str, Any]:
    ledger_path = Path(path)
    try:
        payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LedgerError(f"ledger not found: {ledger_path}") from exc
    except json.JSONDecodeError as exc:
        raise LedgerError(f"ledger is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise LedgerError("ledger root must be an object")
    validate_ledger(payload)
    return payload


def _accepted_risk_is_complete(finding: dict[str, Any]) -> bool:
    decision = finding.get("decision")
    return isinstance(decision, dict) and all(
        isinstance(decision.get(key), str) and decision[key].strip()
        for key in ("approver", "rationale", "scope", "timestamp")
    )


def compute_summary(findings: list[dict[str, Any]]) -> dict[str, Any]:
    severity_counts = Counter(item["severity"] for item in findings)
    status_counts = Counter(item["status"] for item in findings)
    blocking = [
        item["id"]
        for item in findings
        if item["severity"] in {"Critical", "High"}
        and (
            item["status"] in BLOCKING_STATUSES
            or (item["status"] == "accepted_risk" and not _accepted_risk_is_complete(item))
        )
    ]
    return {
        "total": len(findings),
        "by_severity": {severity: severity_counts[severity] for severity in SEVERITIES},
        "by_status": {status: status_counts[status] for status in sorted(STATUSES)},
        "blocking_critical_high": len(blocking),
        "blocking_finding_ids": blocking,
        "ready_for_implementation": not blocking,
    }


def validate_ledger(ledger: dict[str, Any]) -> None:
    required = {
        "schema_version",
        "feature_dir",
        "revision",
        "analyzer_runs",
        "findings",
        "summary",
        "created_at",
        "last_updated",
    }
    missing = sorted(required - ledger.keys())
    if missing:
        raise LedgerError(f"ledger is missing required fields: {', '.join(missing)}")
    if ledger["schema_version"] != SCHEMA_VERSION:
        raise LedgerError(f"unsupported schema_version: {ledger['schema_version']}")
    _safe_relative(ledger["feature_dir"], "feature_dir")
    if not isinstance(ledger["revision"], int) or ledger["revision"] < 1:
        raise LedgerError("revision must be a positive integer")
    if not isinstance(ledger["analyzer_runs"], list) or not isinstance(ledger["findings"], list):
        raise LedgerError("analyzer_runs and findings must be lists")

    run_ids: set[str] = set()
    for run in ledger["analyzer_runs"]:
        if not isinstance(run, dict) or not isinstance(run.get("run_id"), str):
            raise LedgerError("each analyzer run requires a run_id")
        if run["run_id"] in run_ids:
            raise LedgerError(f"duplicate analyzer run: {run['run_id']}")
        run_ids.add(run["run_id"])

    finding_ids: set[str] = set()
    fingerprints: set[str] = set()
    for finding in ledger["findings"]:
        if not isinstance(finding, dict):
            raise LedgerError("each finding must be an object")
        for key in (
            "id",
            "analyzer_run_id",
            "analyzer_run_ids",
            "severity",
            "category",
            "title",
            "description",
            "artifact_refs",
            "evidence",
            "recommended_remediation",
            "fingerprint",
            "status",
            "validation_evidence",
            "created_at",
            "updated_at",
        ):
            if key not in finding:
                raise LedgerError(f"finding is missing {key}")
        if finding["id"] in finding_ids:
            raise LedgerError(f"duplicate finding id: {finding['id']}")
        finding_ids.add(finding["id"])
        if finding["fingerprint"] in fingerprints:
            raise LedgerError(f"duplicate finding fingerprint: {finding['fingerprint']}")
        fingerprints.add(finding["fingerprint"])
        if finding["severity"] not in SEVERITIES or finding["status"] not in STATUSES:
            raise LedgerError(f"invalid severity or status for {finding['id']}")
        if finding["status"] == "fixed" and not finding["validation_evidence"]:
            raise LedgerError(f"fixed finding requires validation evidence: {finding['id']}")
        if finding["status"] == "accepted_risk" and not _accepted_risk_is_complete(finding):
            raise LedgerError(f"accepted risk requires approver, rationale, scope, and timestamp: {finding['id']}")
        for reference in finding["artifact_refs"]:
            _safe_relative(reference, f"{finding['id']}.artifact_refs")

    expected = compute_summary(ledger["findings"])
    if ledger["summary"] != expected:
        raise LedgerError("ledger summary does not match findings")


Mutator = Callable[[dict[str, Any]], bool]


def mutate_ledger(path: str | Path, mutator: Mutator) -> dict[str, Any]:
    ledger_path = Path(path)
    original = load_ledger(ledger_path)
    updated = copy.deepcopy(original)
    if not mutator(updated):
        return original
    updated["revision"] = original["revision"] + 1
    updated["summary"] = compute_summary(updated["findings"])
    updated["last_updated"] = utc_now()
    validate_ledger(updated)
    _atomic_write_json(ledger_path, updated)
    return updated


def _next_finding_id(findings: list[dict[str, Any]]) -> str:
    highest = 0
    for finding in findings:
        match = re.fullmatch(r"AL-(\d+)", finding["id"])
        if match:
            highest = max(highest, int(match.group(1)))
    return f"AL-{highest + 1:04d}"


def merge_output(
    ledger_path: str | Path,
    analyzer_output: dict[str, Any],
    *,
    expected_run_id: str | None = None,
) -> dict[str, Any]:
    normalized = validate_analyzer_output(analyzer_output, expected_run_id)
    output_hash = hashlib.sha256(
        json.dumps(normalized, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()

    def apply(ledger: dict[str, Any]) -> bool:
        prior_run = next(
            (run for run in ledger["analyzer_runs"] if run["run_id"] == normalized["run_id"]),
            None,
        )
        if prior_run:
            if prior_run["output_sha256"] == output_hash:
                return False
            raise LedgerError(
                f"analyzer run {normalized['run_id']} was already merged with different output"
            )

        timestamp = utc_now()
        by_fingerprint = {item["fingerprint"]: item for item in ledger["findings"]}
        new_count = 0
        duplicate_count = 0
        for incoming in normalized["findings"]:
            existing = by_fingerprint.get(incoming["fingerprint"])
            if existing:
                duplicate_count += 1
                existing["analyzer_run_ids"].append(normalized["run_id"])
                existing["occurrences"] += 1
                existing["last_seen_at"] = timestamp
                existing["updated_at"] = timestamp
                for key in ("artifact_refs", "evidence"):
                    existing[key] = list(dict.fromkeys(existing[key] + incoming[key]))
                if existing["status"] == "fixed":
                    existing["status"] = "partially_fixed"
                    existing["validation_evidence"].append(
                        f"Rediscovered by analyzer run {normalized['run_id']}"
                    )
                continue

            new_count += 1
            finding_id = _next_finding_id(ledger["findings"])
            finding = {
                "id": finding_id,
                "analyzer_run_id": normalized["run_id"],
                "analyzer_run_ids": [normalized["run_id"]],
                **incoming,
                "status": "open",
                "validation_evidence": [],
                "decision": None,
                "occurrences": 1,
                "created_at": timestamp,
                "updated_at": timestamp,
                "last_seen_at": timestamp,
            }
            ledger["findings"].append(finding)
            by_fingerprint[finding["fingerprint"]] = finding

        ledger["analyzer_runs"].append(
            {
                "run_id": normalized["run_id"],
                "output_sha256": output_hash,
                "reported_findings": len(normalized["findings"]),
                "new_findings": new_count,
                "duplicate_findings": duplicate_count,
                "merged_at": timestamp,
            }
        )
        return True

    return mutate_ledger(ledger_path, apply)


def update_finding(
    ledger_path: str | Path,
    *,
    finding_id: str,
    status: str,
    validation_evidence: list[str] | None = None,
    approver: str | None = None,
    rationale: str | None = None,
    scope: str | None = None,
) -> dict[str, Any]:
    if status not in STATUSES:
        raise LedgerError(f"invalid status: {status}")
    evidence = [item.strip() for item in (validation_evidence or []) if item.strip()]
    if status == "fixed" and not evidence:
        raise LedgerError("fixed status requires validation evidence")
    if status == "accepted_risk" and not all((approver, rationale, scope)):
        raise LedgerError("accepted_risk requires approver, rationale, and scope")

    def apply(ledger: dict[str, Any]) -> bool:
        finding = next((item for item in ledger["findings"] if item["id"] == finding_id), None)
        if finding is None:
            raise LedgerError(f"finding not found: {finding_id}")
        decision = None
        if status == "accepted_risk":
            decision = {
                "approver": approver,
                "rationale": rationale,
                "scope": scope,
                "timestamp": utc_now(),
            }
        changed = finding["status"] != status
        merged_evidence = list(dict.fromkeys(finding["validation_evidence"] + evidence))
        changed = changed or merged_evidence != finding["validation_evidence"]
        if status == "accepted_risk":
            prior = finding.get("decision") or {}
            changed = changed or any(prior.get(key) != value for key, value in decision.items() if key != "timestamp")
        if not changed:
            return False
        finding["status"] = status
        finding["validation_evidence"] = merged_evidence
        finding["decision"] = decision
        finding["updated_at"] = utc_now()
        return True

    return mutate_ledger(ledger_path, apply)


def _escape_markdown(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(ledger: dict[str, Any]) -> str:
    validate_ledger(ledger)
    summary = ledger["summary"]
    lines = [
        "# Analyze Convergence Ledger",
        "",
        f"Feature: `{ledger['feature_dir']}`  ",
        f"Ledger revision: `{ledger['revision']}`  ",
        f"Ready for implementation: **{'yes' if summary['ready_for_implementation'] else 'no'}**  ",
        f"Blocking Critical/High findings: **{summary['blocking_critical_high']}**",
        "",
        "| ID | Severity | Status | Category | Finding | Artifacts |",
        "|---|---|---|---|---|---|",
    ]
    for finding in ledger["findings"]:
        lines.append(
            "| {id} | {severity} | {status} | {category} | {title} | {artifacts} |".format(
                id=_escape_markdown(finding["id"]),
                severity=_escape_markdown(finding["severity"]),
                status=_escape_markdown(finding["status"]),
                category=_escape_markdown(finding["category"]),
                title=_escape_markdown(finding["title"]),
                artifacts=_escape_markdown(", ".join(finding["artifact_refs"])),
            )
        )
    if not ledger["findings"]:
        lines.append("| — | — | — | — | No findings | — |")

    lines.extend(["", "## Finding details", ""])
    for finding in ledger["findings"]:
        lines.extend(
            [
                f"### {finding['id']}: {finding['title']}",
                "",
                finding["description"],
                "",
                f"- Fingerprint: `{finding['fingerprint']}`",
                f"- Analyzer runs: {', '.join(finding['analyzer_run_ids'])}",
                f"- Evidence: {'; '.join(finding['evidence'])}",
                f"- Recommended remediation: {finding['recommended_remediation']}",
                f"- Validation evidence: {'; '.join(finding['validation_evidence']) or 'none'}",
            ]
        )
        if finding.get("decision"):
            decision = finding["decision"]
            lines.append(
                f"- Decision: accepted by {decision['approver']} for {decision['scope']} — {decision['rationale']}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_markdown(path: str | Path, ledger: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    content = render_markdown(ledger).encode("utf-8")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("ledger")
    init.add_argument("--feature-dir", required=True)
    init.add_argument("--markdown")

    merge = sub.add_parser("merge")
    merge.add_argument("ledger")
    merge.add_argument("analyzer_output")
    merge.add_argument("--expected-run-id")
    merge.add_argument("--markdown")

    update = sub.add_parser("update")
    update.add_argument("ledger")
    update.add_argument("--id", required=True)
    update.add_argument("--status", choices=sorted(STATUSES), required=True)
    update.add_argument("--validation-evidence", action="append", default=[])
    update.add_argument("--approver")
    update.add_argument("--rationale")
    update.add_argument("--scope")
    update.add_argument("--markdown")

    for command in ("summary", "validate", "render"):
        item = sub.add_parser(command)
        item.add_argument("ledger")
    sub.choices["render"].add_argument("--output", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            ledger = initialize_ledger(args.ledger, args.feature_dir)
            if args.markdown:
                write_markdown(args.markdown, ledger)
            output: Any = ledger["summary"]
        elif args.command == "merge":
            try:
                analyzer_output = json.loads(Path(args.analyzer_output).read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise LedgerError(f"analyzer output is not valid JSON: {exc}") from exc
            ledger = merge_output(
                args.ledger, analyzer_output, expected_run_id=args.expected_run_id
            )
            if args.markdown:
                write_markdown(args.markdown, ledger)
            output = ledger["summary"]
        elif args.command == "update":
            ledger = update_finding(
                args.ledger,
                finding_id=args.id,
                status=args.status,
                validation_evidence=args.validation_evidence,
                approver=args.approver,
                rationale=args.rationale,
                scope=args.scope,
            )
            if args.markdown:
                write_markdown(args.markdown, ledger)
            output = ledger["summary"]
        elif args.command == "summary":
            output = load_ledger(args.ledger)["summary"]
        elif args.command == "validate":
            ledger = load_ledger(args.ledger)
            output = {"valid": True, "revision": ledger["revision"]}
        elif args.command == "render":
            ledger = load_ledger(args.ledger)
            write_markdown(args.output, ledger)
            output = {"output": args.output, "revision": ledger["revision"]}
        else:  # pragma: no cover
            raise LedgerError("unsupported command")
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0
    except (OSError, LedgerError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
