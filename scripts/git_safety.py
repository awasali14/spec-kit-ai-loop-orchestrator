#!/usr/bin/env python3
"""Read-only Git safety checks for parent-owned lifecycle checkpoint commits."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


class GitSafetyError(RuntimeError):
    """Raised when repository inspection cannot be completed."""


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitSafetyError("git executable was not found") from exc
    if check and result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise GitSafetyError(detail or f"git {' '.join(args)} failed")
    return result


def _decode_paths(content: bytes) -> list[str]:
    return sorted(
        item.decode("utf-8", errors="surrogateescape")
        for item in content.split(b"\0")
        if item
    )


def _normalize_path(value: str, field: str = "path") -> str:
    if not isinstance(value, str) or not value.strip():
        raise GitSafetyError(f"{field} must be a non-empty repository-relative path")
    normalized = value.strip().replace("\\", "/")
    candidate = Path(normalized)
    if candidate.is_absolute() or re.match(r"^[A-Za-z]:/", normalized) or ".." in candidate.parts:
        raise GitSafetyError(f"{field} must be a repository-relative path: {value}")
    return candidate.as_posix().lstrip("./")


def inspect_repository(repo: str | Path = ".") -> dict[str, Any]:
    requested = Path(repo).resolve()
    probe = _git(requested, "rev-parse", "--is-inside-work-tree", check=False)
    if probe.returncode != 0 or probe.stdout.strip() != b"true":
        return {
            "is_worktree": False,
            "repo_root": None,
            "branch": None,
            "detached": None,
            "head": None,
            "identity": {"usable": False, "name": None, "email": None},
            "staged": [],
            "unstaged": [],
            "untracked": [],
            "conflicts": [],
            "dirty": False,
        }

    root_text = _git(requested, "rev-parse", "--show-toplevel").stdout.decode(
        "utf-8", errors="surrogateescape"
    ).strip()
    root = Path(root_text).resolve()
    branch_result = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    branch = (
        branch_result.stdout.decode("utf-8", errors="surrogateescape").strip()
        if branch_result.returncode == 0
        else None
    )
    head_result = _git(root, "rev-parse", "--verify", "HEAD", check=False)
    head = head_result.stdout.decode("ascii", errors="replace").strip() or None
    name = _git(root, "config", "--get", "user.name", check=False).stdout.decode(
        "utf-8", errors="replace"
    ).strip()
    email = _git(root, "config", "--get", "user.email", check=False).stdout.decode(
        "utf-8", errors="replace"
    ).strip()
    staged = _decode_paths(_git(root, "diff", "--cached", "--name-only", "-z").stdout)
    unstaged = _decode_paths(_git(root, "diff", "--name-only", "-z").stdout)
    untracked = _decode_paths(
        _git(root, "ls-files", "--others", "--exclude-standard", "-z").stdout
    )
    conflicts = _decode_paths(
        _git(root, "diff", "--name-only", "--diff-filter=U", "-z").stdout
    )
    return {
        "is_worktree": True,
        "repo_root": root.as_posix(),
        "branch": branch,
        "detached": branch is None and head is not None,
        "head": head,
        "identity": {
            "usable": bool(name and email),
            "name": name or None,
            "email": email or None,
        },
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
        "conflicts": conflicts,
        "dirty": bool(staged or unstaged or untracked or conflicts),
    }


def evaluate_checkpoint(
    inspection: dict[str, Any],
    owned_files: list[str],
    *,
    commit_enabled: bool = True,
    allow_pre_staged_owned: bool = False,
    require_clean_unowned: bool = False,
) -> dict[str, Any]:
    owned = sorted({_normalize_path(path, "owned_file") for path in owned_files})
    staged = set(inspection.get("staged", []))
    unstaged = set(inspection.get("unstaged", []))
    untracked = set(inspection.get("untracked", []))
    conflicts = set(inspection.get("conflicts", []))
    changed = staged | unstaged | untracked | conflicts
    owned_set = set(owned)
    owned_changed = sorted(changed & owned_set)
    unowned_staged = sorted(staged - owned_set)
    owned_pre_staged = sorted(staged & owned_set)
    unowned_worktree = sorted((unstaged | untracked | conflicts) - owned_set)
    reasons: list[str] = []

    if not inspection.get("is_worktree"):
        reasons.append("not_in_git_worktree")
    if conflicts:
        reasons.append("unresolved_merge_conflicts")
    if unowned_staged:
        reasons.append("unrelated_staged_files")
    if owned_pre_staged and not allow_pre_staged_owned:
        reasons.append("checkpoint_files_were_already_staged")
    if require_clean_unowned and unowned_worktree:
        reasons.append("unrelated_worktree_changes")
    if commit_enabled:
        if not inspection.get("identity", {}).get("usable"):
            reasons.append("git_identity_unusable")
        if inspection.get("detached"):
            reasons.append("detached_head")

    return {
        "safe": not reasons,
        "commit_enabled": commit_enabled,
        "reasons": reasons,
        "owned_files": owned,
        "checkpoint_candidates": owned_changed,
        "owned_pre_staged": owned_pre_staged,
        "unrelated_staged": unowned_staged,
        "unrelated_worktree": unowned_worktree,
        "conflicts": sorted(conflicts),
        "requires_parent_diff_review": owned_changed,
        "parent_attestation": (
            "Confirm checkpoint candidates contain only work from the completed lifecycle stage."
            if owned_changed
            else "No checkpoint-owned changes detected. Record a no-op receipt; do not create an empty commit."
        ),
    }


def verify_index(
    inspection: dict[str, Any], expected_files: list[str], *, allow_subset: bool = False
) -> dict[str, Any]:
    expected = {_normalize_path(path, "expected_file") for path in expected_files}
    staged = set(inspection.get("staged", []))
    unexpected = sorted(staged - expected)
    missing = sorted(expected - staged)
    reasons: list[str] = []
    if not inspection.get("is_worktree"):
        reasons.append("not_in_git_worktree")
    if inspection.get("conflicts"):
        reasons.append("unresolved_merge_conflicts")
    if unexpected:
        reasons.append("index_contains_unexpected_files")
    if missing and not allow_subset:
        reasons.append("expected_files_are_not_staged")
    if not staged:
        reasons.append("index_is_empty")
    return {
        "safe": not reasons,
        "reasons": reasons,
        "staged": sorted(staged),
        "expected": sorted(expected),
        "unexpected": unexpected,
        "missing": missing,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect")
    inspect.add_argument("--repo", default=".")

    checkpoint = sub.add_parser("checkpoint")
    checkpoint.add_argument("--repo", default=".")
    checkpoint.add_argument("--owned-file", action="append", default=[])
    checkpoint.add_argument("--no-commit", action="store_true")
    checkpoint.add_argument("--allow-pre-staged-owned", action="store_true")
    checkpoint.add_argument("--require-clean-unowned", action="store_true")

    verify = sub.add_parser("verify-index")
    verify.add_argument("--repo", default=".")
    verify.add_argument("--expected-file", action="append", default=[])
    verify.add_argument("--allow-subset", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        inspection = inspect_repository(args.repo)
        if args.command == "inspect":
            result = inspection
            exit_code = 0 if inspection["is_worktree"] else 2
        elif args.command == "checkpoint":
            result = evaluate_checkpoint(
                inspection,
                args.owned_file,
                commit_enabled=not args.no_commit,
                allow_pre_staged_owned=args.allow_pre_staged_owned,
                require_clean_unowned=args.require_clean_unowned,
            )
            exit_code = 0 if result["safe"] else 2
        elif args.command == "verify-index":
            result = verify_index(
                inspection, args.expected_file, allow_subset=args.allow_subset
            )
            exit_code = 0 if result["safe"] else 2
        else:  # pragma: no cover
            raise GitSafetyError("unsupported command")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return exit_code
    except GitSafetyError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
