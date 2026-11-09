#!/usr/bin/env python3
"""Private, checksummed recovery capture of exact tracked Git differences.

Captures HEAD->index, index->working-tree and HEAD->working-tree patches separately.
Untracked files are catalogued but NEVER copied or staged automatically. Running
worktrees are neither locked nor modified; drift is reported, not concealed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import tempfile

from agent_worktrees import write_private_json

MAX_PATCH_BYTES = 32 * 1024 * 1024
SECRET_FILENAME = re.compile(
    r"(^|/)(\.env($|\.)|id_[er]sa|.*\.(pem|p12|pfx|key)$|"
    r".*(?:secret|credential|token|private.key).*)", re.I
)


def git_bytes(path: str, args: list[str], destination: pathlib.Path) -> dict:
    fd, temp = tempfile.mkstemp(prefix=".capture-", dir=destination.parent)
    h = hashlib.sha256()
    size = 0
    try:
        with os.fdopen(fd, "wb") as fh, subprocess.Popen(
            ["git", "-C", path, "diff", "--no-ext-diff", "--binary", *args, "--"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ) as proc:
            assert proc.stdout
            for chunk in iter(lambda: proc.stdout.read(65536), b""):
                size += len(chunk)
                if size > MAX_PATCH_BYTES:
                    proc.kill()
                    proc.wait()
                    raise RuntimeError("Patch exceeds bounded size; capture requires manual review.")
                fh.write(chunk)
                h.update(chunk)
            _, stderr = proc.communicate(timeout=45)
            if proc.returncode:
                raise RuntimeError("Git diff failed: " + stderr.decode(errors="replace")[:240])
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, destination)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return {"file": destination.name, "sha256": h.hexdigest(), "bytes": size}


def list_untracked(path: str) -> dict:
    result = subprocess.run(
        ["git", "-C", path, "ls-files", "--others", "--exclude-standard", "-z"],
        capture_output=True, timeout=35, check=True,
    )
    paths = [x.decode("utf-8", errors="surrogateescape") for x in result.stdout.split(b"\0") if x]
    if len(paths) > 10000:
        return {"status": "too_many", "count": len(paths), "items": []}
    root = pathlib.Path(path)
    items = []
    total = 0
    for relative in paths:
        p = root / relative
        try:
            stat = p.lstat()  # Never follow untracked symlinks.
            length = stat.st_size if p.is_file() and not p.is_symlink() else 0
            total += length
            items.append({
                "path": relative, "size_bytes": length, "symlink": p.is_symlink(),
                "sensitive_name": bool(SECRET_FILENAME.search(relative)),
            })
        except FileNotFoundError:
            items.append({"path": relative, "missing_during_capture": True})
    return {"status": "enumerated", "count": len(items), "bytes_regular": total, "items": items}


def capture(source: dict, output: pathlib.Path) -> dict:
    output = output.expanduser().resolve()
    if output.exists():
        raise RuntimeError("Immutable capture destination already exists: " + str(output))
    output.mkdir(parents=True, mode=0o700)
    os.chmod(output, 0o700)
    ledger = {
        "schema_version": 1,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_generated_utc": source["source_generated_utc"],
        "note": "PRIVATE: never publish patches or untracked paths; no files were modified in working repositories.",
        "records": [],
    }
    for entry in source["entries"]:
        if entry["status"] != "ok":
            continue
        path = entry["path"]
        id_ = hashlib.sha256(path.encode("utf-8")).hexdigest()[:24]
        directory = output / id_
        directory.mkdir(mode=0o700)
        row = {
            "repo": entry["repo"], "path": path, "head": entry["head"],
            "expected_patch_sha256": entry["tracked_patch_sha256"],
            "status": "started",
        }
        try:
            head = subprocess.run(
                ["git", "-C", path, "rev-parse", "HEAD"], capture_output=True,
                text=True, timeout=10, check=True,
            ).stdout.strip()
            if head != entry["head"]:
                raise RuntimeError("HEAD changed since fingerprint snapshot.")
            row["head_to_worktree"] = git_bytes(path, ["HEAD"], directory / "head-to-worktree.patch")
            if row["head_to_worktree"]["sha256"] != entry["tracked_patch_sha256"]:
                raise RuntimeError("Tracked patch drifted since fingerprint snapshot.")
            row["head_to_index"] = git_bytes(
                path, ["--cached", "HEAD"], directory / "head-to-index.patch"
            )
            row["index_to_worktree"] = git_bytes(
                path, [], directory / "index-to-worktree.patch"
            )
            row["untracked"] = list_untracked(path)
            # If source drifted mid-capture, do not label as a consistent snapshot.
            verify = hashlib.sha256(subprocess.run(
                ["git", "-C", path, "diff", "--no-ext-diff", "--binary", "HEAD", "--"],
                capture_output=True, timeout=45, check=True,
            ).stdout).hexdigest()
            after = subprocess.run(
                ["git", "-C", path, "rev-parse", "HEAD"], capture_output=True,
                text=True, timeout=10, check=True,
            ).stdout.strip()
            if verify != entry["tracked_patch_sha256"] or after != head:
                raise RuntimeError("Working source changed during capture.")
            row["status"] = "captured"
        except Exception as exc:
            row["status"] = "drift_or_error"
            row["error"] = str(exc)[:300]
        ledger["records"].append(row)
    write_private_json(output / "capture-manifest.json", ledger)
    return ledger


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.input.expanduser().read_text(encoding="utf-8"))
    result = capture(report, args.output)
    print(json.dumps({
        "captured": sum(x["status"] == "captured" for x in result["records"]),
        "drift_or_error": sum(x["status"] != "captured" for x in result["records"]),
        "untracked_files_enumerated": sum(
            x.get("untracked", {}).get("count", 0) for x in result["records"]
        ),
        "suspected_sensitive_names": sum(
            x.get("sensitive_name", False)
            for rec in result["records"] for x in rec.get("untracked", {}).get("items", [])
        ),
        "manifest": str(args.output.expanduser() / "capture-manifest.json"),
    }))


if __name__ == "__main__":
    main()
