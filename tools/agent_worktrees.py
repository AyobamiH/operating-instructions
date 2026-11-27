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


def is_ancestor(repo: pathlib.Path, older: str, newer: str) -> bool:
    """Read-only ancestry proof; never infer integration from a matching filename."""
    proc = subprocess.run(
        ["git", "-C", str(repo), "merge-base", "--is-ancestor", older, newer],
        capture_output=True, text=True, timeout=15, check=False,
    )
    if proc.returncode not in (0, 1):
        raise AdmissionError("Cannot establish commit ancestry: " + proc.stderr.strip()[:250])
    return proc.returncode == 0


def tracked_upstream(repo: pathlib.Path) -> str | None:
    """Local tracking ref only: upstream freshness must be verified independently."""
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify",
         "refs/remotes/origin/main^{commit}"],
        capture_output=True, text=True, timeout=15, check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def reconcile_upstreams(
    roots: list[tuple[str, pathlib.Path]], sha_by_label: dict[str, str],
    state: pathlib.Path,
) -> dict:
    """Classify every registration; no worktree, branch or lease is changed."""
    report = scan_roots(roots)
    for group in report["repositories"]:
        label, root = group["label"], pathlib.Path(group["root"])
        expected = sha_by_label.get(label, "")
        actual = tracked_upstream(root) if not group["errors"] else None
        if not re.fullmatch(r"[0-9a-f]{40}", expected) or actual != expected:
            group["errors"].append(
                "Tracked main does not match supplied exact upstream; "
                "verify GitHub and fetch before reconciliation."
            )
            for entry in group["worktrees"]:
                entry["disposition"] = "unsafe/unknown"
            continue
        group["upstream_sha"] = expected
        for entry in group["worktrees"]:
            path = pathlib.Path(entry["path"])
            if path == root:
                entry["disposition"] = (
                    "canonical-current" if entry["head"] == expected
                    else "canonical-stale-checkout"
                )
                continue
            manifest = owner_ledger(state, label, path.name)
            if manifest.is_file():
                try:
                    lease = json.loads(manifest.read_text(encoding="utf-8"))
                    if (lease.get("path") != str(path)
                        or lease.get("repo_git_common_dir") != group["git_common_dir"]
                        or lease.get("branch") != (entry.get("branch") or "").removeprefix("refs/heads/")
                        or lease.get("status") not in ("ready", "active")
                        or type(lease.get("generation")) is not int
                        or lease["generation"] < 1):
                        raise ValueError("lease identity, branch, state or generation mismatch")
                    verified_worktree_head(
                        root, path, group["git_common_dir"], lease["branch"],
                        entry["head"],
                    )
                    entry["lease"] = {
                        "status": lease.get("status"),
                        "owner": lease.get("owner"),
                        "task": lease.get("task"),
                    }
                except (AdmissionError, OSError, ValueError, TypeError, subprocess.TimeoutExpired):
                    entry["disposition"] = "unsafe/unknown"
                    continue
            if entry["status"] != "clean" or entry["locked"] or entry["prunable"]:
                entry["disposition"] = (
                    "needs-review" if entry["status"] == "dirty" else "unsafe/unknown"
                )
            elif entry["head"] == expected:
                entry["disposition"] = "upstream-current"
            elif is_ancestor(root, entry["head"], expected):
                entry["disposition"] = "upstream-integrated-needs-owner-retirement"
            else:
                entry["disposition"] = "needs-integration-or-review"
    return report


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
        # Persist the directory entry as well as the file contents.
        dirfd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
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


def verified_worktree_head(
    repo: pathlib.Path, path: pathlib.Path, git_common: str,
    branch: str, expected_head: str,
) -> str:
    """Fail closed on a changed Git registration, branch, or exact HEAD.

    This is a cooperative admission check, NOT an OS-level writer fence.
    """
    if not re.fullmatch(r"[0-9a-f]{40,64}", expected_head):
        raise AdmissionError("An exact expected worktree HEAD is required.")
    if path.is_symlink() or not path.is_dir():
        raise AdmissionError("Worktree is missing or is a symbolic link.")
    registered = [
        entry for entry in parse_worktrees(
            run_git(repo, "worktree", "list", "--porcelain")
        )
        if pathlib.Path(entry["worktree"]).resolve() == path
    ]
    if len(registered) != 1:
        raise AdmissionError("Worktree is not uniquely registered with the repository.")
    entry = registered[0]
    ref = "refs/heads/" + branch
    if (entry.get("branch") != ref or entry.get("detached")
            or entry.get("locked") or entry.get("prunable")):
        raise AdmissionError("Registered worktree branch/state does not match its lease.")
    if common_dir(path) != git_common:
        raise AdmissionError("Worktree Git common-dir identity mismatch.")
    symbolic = run_git(path, "symbolic-ref", "--quiet", "HEAD").strip()
    current = run_git(path, "rev-parse", "--verify", "HEAD").strip()
    if symbolic != ref or entry.get("HEAD") != current or current != expected_head:
        raise AdmissionError("Worktree branch or HEAD has changed since verification.")
    return current


def admit(
    repo: pathlib.Path, project: str, task: str, owner: str, purpose: str,
    base: str, state: pathlib.Path, workspace: pathlib.Path,
    trusted_roots: dict[str, str],
    expected_head: str | None = None, expected_generation: int | None = None,
) -> dict:
    # New worktrees only; existing work remains owned by its original executor.
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
            try:
                previous = json.loads(manifest.read_text(encoding="utf-8"))
            except (ValueError, TypeError) as exc:
                raise AdmissionError("Existing lease is malformed; recover it independently.") from exc
            if not isinstance(previous, dict):
                raise AdmissionError("Existing lease is not a record.")
            # Never turn a released/revoked/recovery lease back into ready.
            # Existing-owner re-entry requires an exact generation and HEAD.
            match = (
                previous.get("schema_version") == SCHEMA
                and previous.get("project") == project
                and previous.get("task") == task
                and previous.get("owner") == owner
                and previous.get("source_root") == str(repo)
                and previous.get("repo_git_common_dir") == root_gitdir
                and previous.get("base_sha") == base_sha
                and previous.get("branch") == "agent/" + task
                and previous.get("path") == str(path)
                and previous.get("purpose") == purpose
                and previous.get("status") in ("ready", "active")
                and type(previous.get("generation")) is int
                and previous["generation"] >= 1
                and previous["generation"] == expected_generation
            )
            if not match:
                raise AdmissionError(
                    "Existing lease identity, state or generation mismatch; "
                    "requires owner-led reconciliation."
                )
            if expected_head is None:
                raise AdmissionError("Readmission requires --expected-head for the exact Git revision.")
            current = verified_worktree_head(
                repo, path, root_gitdir, previous["branch"], expected_head
            )
            if not is_ancestor(repo, base_sha, current):
                raise AdmissionError("Worktree HEAD is outside the approved base lineage.")
            upstream = tracked_upstream(repo)
            if (upstream and current != upstream
                    and status_entry({"worktree": str(path), "HEAD": current})["status"] == "clean"
                    and is_ancestor(repo, current, upstream)):
                raise AdmissionError(
                    "Existing clean lease is upstream-integrated and behind "
                    "tracked main; reconcile/retire it, then admit a fresh task."
                )
            # A successful readmission is read-only and preserves 'active'.
            return previous
        if expected_head is not None and expected_head != base_sha:
            raise AdmissionError("New task expected HEAD must equal its exact base SHA.")
        if expected_generation is not None and expected_generation != 1:
            raise AdmissionError("New task generation must be one.")
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
            "generation": 1, "admitted_head": base_sha,
            "status": "reserved",
        }
        write_private_json(manifest, record)
        prefix.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            run_git(repo, "worktree", "add", "-b", branch, str(path), base_sha, timeout=60)
            verified_worktree_head(repo, path, root_gitdir, branch, base_sha)
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
    review = subs.add_parser(
        "reconcile",
        help="Read-only, exact-upstream reconciliation; writes private disposition report.",
    )
    review.add_argument("--repo", action="append", required=True, metavar="LABEL=PATH")
    review.add_argument("--upstream", action="append", required=True, metavar="LABEL=FULL_SHA")
    review.add_argument("--output", type=pathlib.Path)
    create = subs.add_parser("admit", help="Reserve a bounded, owner-labelled worktree.")
    for arg in ("repo", "project", "task", "owner", "purpose", "base"):
        create.add_argument("--" + arg, required=True)
    create.add_argument(
        "--expected-head",
        help="Full expected Git HEAD, mandatory for existing-lease readmission.",
    )
    create.add_argument(
        "--expected-generation", type=int,
        help="Lease generation, mandatory for existing-lease readmission.",
    )
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
    if args.command == "reconcile":
        roots, upstreams = [], {}
        for item in args.repo:
            if "=" not in item:
                parser.error("--repo requires LABEL=PATH")
            label, path = item.split("=", 1)
            if not label or not path or label in [r[0] for r in roots]:
                parser.error("missing or duplicate --repo label/path")
            roots.append((label, pathlib.Path(path)))
        for item in args.upstream:
            if "=" not in item:
                parser.error("--upstream requires LABEL=FULL_SHA")
            label, sha = item.split("=", 1)
            if label in upstreams or not re.fullmatch(r"[0-9a-f]{40}", sha):
                parser.error("duplicate label or non-exact SHA")
            upstreams[label] = sha
        if set(upstreams) != {label for label, _ in roots}:
            parser.error("each --repo needs exactly one --upstream")
        report = reconcile_upstreams(roots, upstreams, state)
        output = (args.output or state / "reconciliation-current.json").expanduser()
        write_private_json(output, report)
        for group in report["repositories"]:
            counts = Counter(w["disposition"] for w in group["worktrees"])
            print(json.dumps({"repo": group["label"], "dispositions": dict(counts),
                              "errors": group["errors"]}, sort_keys=True))
        print("LOCAL_PRIVATE_REPORT=" + str(output.resolve()))
        return 2 if any(g["errors"] for g in report["repositories"]) else 0
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
            host_config['projects'], args.expected_head, args.expected_generation,
        )
    except (AdmissionError, OSError, subprocess.TimeoutExpired) as exc:
        print("ADMISSION_DENIED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
