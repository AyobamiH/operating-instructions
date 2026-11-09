#!/usr/bin/env python3
"""Private, read-only fingerprints of tracked differences in a worktree inventory.

Hashes never replace diff review: untracked files are NOT included and identical
tracked patches on different heads are not proof of safe integration.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import pathlib
import subprocess
from collections import defaultdict

from agent_worktrees import write_private_json


def fingerprint(entry: dict) -> dict:
    output = {
        "path": entry["path"], "head": entry.get("head"), "branch": entry.get("branch"),
        "untracked_entries": entry.get("untracked_entries", 0),
        "tracked_patch_sha256": None, "tracked_names": [],
        "status": "unknown",
    }
    if entry.get("status") != "dirty" or not pathlib.Path(entry["path"]).is_dir():
        output["status"] = "not_dirty"
        return output
    path = entry["path"]
    try:
        args = ["git", "-C", path, "diff", "--no-ext-diff", "--binary", "HEAD", "--"]
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
            digest = hashlib.sha256()
            count = 0
            assert proc.stdout is not None
            for chunk in iter(lambda: proc.stdout.read(65536), b""):
                digest.update(chunk)
                count += len(chunk)
            output["tracked_patch_bytes"] = count
            _, stderr = proc.communicate(timeout=30)
            if proc.returncode:
                raise RuntimeError("git diff failed: " + stderr.decode(errors="replace")[:200])
            output["tracked_patch_sha256"] = digest.hexdigest()
        names = subprocess.run(
            ["git", "-C", path, "diff", "--no-ext-diff", "--name-only", "HEAD"],
            text=True, capture_output=True, timeout=20, check=True,
        )
        output["tracked_names"] = names.stdout.splitlines()
        output["status"] = "ok"
    except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
        output["status"] = "error"
        output["error"] = str(exc)[:300]
    return output


def triage(source: dict, workers: int) -> dict:
    records = [
        (repo["label"], entry)
        for repo in source["repositories"]
        for entry in repo["worktrees"]
        if entry["status"] == "dirty"
    ]
    def run_one(item: tuple[str, dict]) -> dict:
        label, entry = item
        return {"repo": label, **fingerprint(entry)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        analysed = sorted(pool.map(run_one, records), key=lambda r: (r["repo"], r["path"]))
    groups = defaultdict(list)
    for entry in analysed:
        if entry["status"] == "ok":
            groups[(entry["repo"], entry["head"], entry["tracked_patch_sha256"])].append(entry)
    duplicates = [
        {
            "repo": key[0], "head": key[1], "tracked_patch_sha256": key[2],
            "paths": [r["path"] for r in rows],
            "untracked_warning": any(r["untracked_entries"] for r in rows),
        }
        for key, rows in groups.items() if len(rows) > 1
    ]
    return {
        "schema_version": 1, "source_generated_utc": source["generated_utc"],
        "note": "Fingerprints cover tracked differences only; no source or untracked data copied.",
        "dirty_worktrees": len(analysed),
        "fingerprinted": sum(r["status"] == "ok" for r in analysed),
        "errors": sum(r["status"] == "error" for r in analysed),
        "duplicate_groups": sorted(duplicates, key=lambda g: (-len(g["paths"]), g["repo"])),
        "entries": analysed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.workers <= 6:
        parser.error("--workers must be 1..6")
    payload = json.loads(args.input.expanduser().read_text(encoding="utf-8"))
    result = triage(payload, args.workers)
    write_private_json(args.output.expanduser(), result)
    print(json.dumps({
        "dirty": result["dirty_worktrees"], "fingerprinted": result["fingerprinted"],
        "errors": result["errors"],
        "duplicate_tracked_patch_groups": len(result["duplicate_groups"]),
        "duplicate_tracked_patch_members": sum(len(g["paths"]) for g in result["duplicate_groups"]),
        "report": str(args.output.expanduser()),
    }))


if __name__ == "__main__":
    main()
