#!/usr/bin/env python3
"""Fail-closed worktree inventory and bounded, owner-labelled worktree admission.

No existing worktree is changed by scan. No command here performs commit, push,
merge, prune, reset, deletion, service control or production deployment.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import fcntl
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from collections import Counter
from contextlib import contextmanager

SCHEMA = 1
NAME = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")


class AdmissionError(RuntimeError):
    pass


def run_git(path: pathlib.Path, *args: str, timeout: int = 15) -> str:
    proc = subprocess.run(
        ["git", "-C", str(path), *args], capture_output=True, text=True,
        timeout=timeout, check=False,
    )
    if proc.returncode:
        raise AdmissionError(
            "git " + " ".join(args[:3]) + " failed in " + str(path)
            + ": " + proc.stderr.strip()[:300]
        )
    return proc.stdout


def common_dir(path: pathlib.Path) -> str:
    value = run_git(path, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()
    return str(pathlib.Path(value).resolve())


def parse_worktrees(output: str) -> list[dict]:
    entries = []
    for block in output.strip().split("\n\n"):
        result = {}
        for line in block.splitlines():
            key, sep, value = line.partition(" ")
            if key:
                result[key] = value if sep else True
        if "worktree" in result:
            entries.append(result)
    return entries


def status_entry(entry: dict) -> dict:
    path = pathlib.Path(entry["worktree"])
    result = {
        "path": str(path), "head": entry.get("HEAD"), "branch": entry.get("branch"),
        "detached": bool(entry.get("detached")), "locked": bool(entry.get("locked")),
        "prunable": bool(entry.get("prunable")), "exists": path.is_dir(),
        "status": "unknown", "staged": 0, "unstaged": 0,
        "untracked_entries": 0, "reported_changed_entries": 0,
    }
    if not result["exists"]:
        result["status"] = "missing"
        return result
    try:
        lines = run_git(
            path, "status", "--porcelain=v1", "--untracked-files=normal", timeout=18
        ).splitlines()
        for line in lines:
            if len(line) < 3:
                continue
            x, y = line[0], line[1]
            result["reported_changed_entries"] += 1
            if x == "?" and y == "?":
                result["untracked_entries"] += 1
            else:
                result["staged"] += int(x not in (" ", "?"))
                result["unstaged"] += int(y not in (" ", "?"))
        result["status"] = "dirty" if lines else "clean"
    except (AdmissionError, subprocess.TimeoutExpired, OSError) as exc:
        result["status"] = "error"
        result["error"] = str(exc)[:250]
    return result


def scan_roots(roots: list[tuple[str, pathlib.Path]], workers: int = 4) -> dict:
    data = {
        "schema_version": SCHEMA,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "note": "Local snapshot, not an up-to-date GitHub PR or deployment verdict.",
        "repositories": [],
    }
    seen = set()
    for label, root in roots:
        root = root.expanduser().resolve()
        group = {
            "label": label, "root": str(root), "git_common_dir": None,
            "worktrees": [], "summary": {}, "errors": [],
        }
        try:
            git_common = common_dir(root)
            group["git_common_dir"] = git_common
            if git_common in seen:
                raise AdmissionError("Duplicate Git common directory: " + git_common)
            seen.add(git_common)
            items = parse_worktrees(run_git(root, "worktree", "list", "--porcelain"))
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                group["worktrees"] = sorted(
                    list(pool.map(status_entry, items)), key=lambda e: e["path"]
                )
            counts = Counter(w["status"] for w in group["worktrees"])
            group["summary"] = {
                "registered": len(items),
                "clean": counts["clean"], "dirty": counts["dirty"],
                "missing": counts["missing"], "errors": counts["error"],
                "untracked_entries": sum(w["untracked_entries"] for w in group["worktrees"]),
                "staged_entries": sum(w["staged"] for w in group["worktrees"]),
                "unstaged_entries": sum(w["unstaged"] for w in group["worktrees"]),
                "detached": sum(w["detached"] for w in group["worktrees"]),
                "locked": sum(w["locked"] for w in group["worktrees"]),
                "prunable": sum(w["prunable"] for w in group["worktrees"]),
            }
        except (AdmissionError, subprocess.TimeoutExpired, OSError) as exc:
            group["errors"].append(str(exc)[:500])
        data["repositories"].append(group)
    return data


def write_private_json(path: pathlib.Path, payload: dict) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    fd, tmp = tempfile.mkstemp(prefix=".writing-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as writer:
            json.dump(payload, writer, indent=2, sort_keys=True)
            writer.write("\n")
            writer.flush()
            os.fsync(writer.fileno())
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@contextmanager
def exclusive_lock(path: pathlib.Path):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with open(path, "a+", encoding="utf-8") as handle:
        os.chmod(path, 0o600)
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def verify_name(value: str) -> str:
    if not NAME.fullmatch(value):
        raise AdmissionError("Identifier must be lowercase letters/numbers/hyphens (2-63 characters).")
    return value


def owner_ledger(state: pathlib.Path, project: str, task: str) -> pathlib.Path:
    return state / "leases" / project / (task + ".json")


def admit(
    repo: pathlib.Path, project: str, task: str, owner: str, purpose: str,
    base: str, state: pathlib.Path, workspace: pathlib.Path,
    trusted_roots: dict[str, str],
) -> dict:
    # The existing repos remain untouched; only a new managed worktree is created.
    project, task, owner = map(verify_name, (project, task, owner))
    if not purpose.strip() or len(purpose) > 250:
        raise AdmissionError("A bounded purpose (1-250 characters) is required.")
    repo = repo.expanduser().resolve(strict=True)
    if project not in trusted_roots or repo != pathlib.Path(trusted_roots[project]).expanduser().resolve(strict=True):
        raise AdmissionError('Project/repository pair is not present in the trusted host allowlist.')
    if not re.fullmatch(r'[0-9a-fA-F]{40,64}', base):
        raise AdmissionError('Admission requires an exact full commit SHA, not a mutable ref.')
    state = state.expanduser().resolve()
    workspace = workspace.expanduser().resolve()
    prefix = workspace / project
    path = prefix / task
    manifest = owner_ledger(state, project, task)
    lock = state / "locks" / (project + ".lock")
    with exclusive_lock(lock):
        root_gitdir = common_dir(repo)
        base_sha = run_git(repo, "rev-parse", "--verify", base + "^{commit}").strip()
        if manifest.exists():
            previous = json.loads(manifest.read_text(encoding="utf-8"))
            match = (
                previous.get("owner") == owner
                and previous.get("repo_git_common_dir") == root_gitdir
                and previous.get("base_sha") == base_sha
                and previous.get("path") == str(path)
                and previous.get("purpose") == purpose
            )
            if not match:
                raise AdmissionError("Existing lease does not match requested owner/base/purpose.")
            if path.is_dir() and common_dir(path) == root_gitdir:
                previous["status"] = "ready"
                write_private_json(manifest, previous)
                return previous
            # Do not silently recycle a missing worktree or an unknown directory.
            raise AdmissionError("Existing lease has no valid worktree; requires manual recovery.")
        if path.exists() or path.is_symlink():
            raise AdmissionError("Unowned workspace destination already exists: " + str(path))
        branch = "agent/" + task
        branch_exists = subprocess.run(
            ["git", "-C", str(repo), "show-ref", "--verify", "--quiet", "refs/heads/" + branch],
            check=False,
        ).returncode == 0
        if branch_exists:
            raise AdmissionError("Branch already exists without a matching owner lease: " + branch)
        # Reserve before the external git side effect, for interruption recovery.
        record = {
            "schema_version": SCHEMA, "project": project, "task": task,
            "owner": owner, "purpose": purpose, "path": str(path),
            "source_root": str(repo), "repo_git_common_dir": root_gitdir,
            "branch": branch, "base_sha": base_sha, "base_requested": base,
            "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "status": "reserved",
        }
        write_private_json(manifest, record)
        prefix.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            run_git(repo, "worktree", "add", "-b", branch, str(path), base_sha, timeout=60)
            record["status"] = "ready"
        except Exception as exc:
            record["status"] = "requires_recovery"
            record["error"] = str(exc)[:500]
            raise
        finally:
            write_private_json(manifest, record)
        return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state-dir", type=pathlib.Path,
        default=pathlib.Path("~/.local/state/agent-worktrees"),
    )
    subs = parser.add_subparsers(dest="command", required=True)
    audit = subs.add_parser("inventory", help="Read-only worktree scan; writes private JSON.")
    audit.add_argument("--repo", action="append", required=True, metavar="LABEL=PATH")
    audit.add_argument("--output", type=pathlib.Path)
    audit.add_argument("--workers", type=int, default=4)
    create = subs.add_parser("admit", help="Reserve a bounded, owner-labelled worktree.")
    for arg in ("repo", "project", "task", "owner", "purpose", "base"):
        create.add_argument("--" + arg, required=True)
    create.add_argument(
        "--workspace", type=pathlib.Path,
        default=pathlib.Path("~/.local/share/agent-worktrees"),
    )
    create.add_argument(
        "--config", type=pathlib.Path,
        default=pathlib.Path("~/.config/agent-worktrees/repositories.json"),
        help='Host-local allowlist of project names to canonical source roots.',
    )
    args = parser.parse_args()
    state = args.state_dir.expanduser()
    if args.command == "inventory":
        if not 1 <= args.workers <= 8:
            parser.error("--workers must be in range 1..8")
        roots = []
        for item in args.repo:
            if "=" not in item:
                parser.error("--repo requires LABEL=PATH")
            label, path = item.split("=", 1)
            if not label or not path:
                parser.error("--repo requires LABEL=PATH")
            roots.append((label, pathlib.Path(path)))
        report = scan_roots(roots, workers=args.workers)
        output = args.output or (state / "inventory-current.json")
        write_private_json(output.expanduser(), report)
        for group in report["repositories"]:
            print(json.dumps({"repo": group["label"], **group["summary"], "errors": group["errors"]}))
        print("LOCAL_PRIVATE_REPORT=" + str(output.expanduser().resolve()))
        return 2 if any(g["errors"] or g["summary"].get("errors") for g in report["repositories"]) else 0
    try:
        host_config = json.loads(args.config.expanduser().read_text(encoding='utf-8'))
        result = admit(
            pathlib.Path(args.repo), args.project, args.task, args.owner,
            args.purpose, args.base, state, args.workspace,
            host_config['projects'],
        )
    except (AdmissionError, OSError, subprocess.TimeoutExpired) as exc:
        print("ADMISSION_DENIED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
