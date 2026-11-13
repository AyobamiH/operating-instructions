# Git worktree governance and source-reconciliation contract

Scope: owner-operated engineering machines and all assistants touching the owner's Git projects. This governs **where** new work happens and how it is handed off. It never overrides each repository's approvals, source authority, deployment gates, secret controls or active job ownership.

## Canonical paths and authorities

- Canonical project repositories remain their own upstream Git repositories. Do not create a second "source of truth" or treat a working directory name as a release identity.
- On each authorised host, use the **host-private allowlist** at `~/.config/agent-worktrees/repositories.json` to identify current canonical repositories. Never substitute an installed release or guess from names. Confirm live source, PR and deployed heads before work.
- The portable tool is `tools/agent_worktrees.py` in `AyobamiH/operating-instructions`. Machine-private reports and leases belong under `~/.local/state/agent-worktrees`. New task worktrees belong under `~/.local/share/agent-worktrees/<project>/<task>` by default. Admission requires a host-allowlisted root and exact full base commit SHA. No ad-hoc home-root or `/tmp` worktrees for enduring engineering work.
- Existing legacy worktrees are *grandfathered for inspection and recovery*, not automatically deleted, adopted or migrated. Protected runtime/installed checkouts remain in their existing product-specific locations.
- Canonical work and handoff artefacts stay in the project repository/PR where appropriate; private working patches, secrets and host inventories stay private, outside public Git history.

## Required sequence for every agent

1. **Discover:** read the project's `AGENTS.md`, current PR/branch/CI state, recent handoff, live owner/lease and existing worktrees before creating anything. Use the inventory command. Check that the proposed task isn't already being executed by another owner.
2. **Admit:** select one project, one bounded task identifier, one agent owner, one exact base commit and a concise purpose. Create a managed worktree and durable lease using `agent_worktrees.py admit`. If a matching active lease exists, reuse that same location; if any mismatch occurs, stop and reconcile instead of claiming or resetting someone else's work.
3. **Build and verify:** change only the admitted task. Never write project source to home root, `/tmp`, production releases or CI evidence directories. Keep test logs outside tracked source, and document exact-source evidence/limitations.
4. **Integrate:** inspect staged, unstaged and untracked files; detect secrets and generated output before any `git add`. Commit *only* verified coherent work, signed where required. Push to the correct upstream project and update its existing PR, or open one suitable PR when absent. Follow repository-specific reviews, protections and release gates. A merged PR may not equal a deployed, accepted release.
5. **Reconcile:** after current remote main/readback and owner confirmation, record whether each branch's source is included by ancestry/content, whether tests and release gates pass, and whether an unfinished dirty tree still contains unique work. Assign an explicit disposition: `active-owned`, `needs-review`, `needs-integration`, `upstream-integrated`, `evidence-only`, `unsafe/unknown`. Do not infer integration from matching filenames or commit messages.
6. **Retire, only after proof:** archive private, bounded recovery evidence with integrity checks; require clean tracked/untracked status, no live runtime/runner dependency and a recorded upstream disposition. A stale registration can be pruned only after its path and ref provenance are confirmed. Never bulk-remove, reset, clean, force-push, auto-merge or delete worktree directories from inventory counts.

## Current machine command examples

Inventory is read-only with a private JSON report. Supply every distinct Git-common-dir group:

```bash
python3 tools/agent_worktrees.py inventory \
  --repo clawsweeper=/path/to/clawsweeper-source \
  --repo clawsweeper-tracing=/path/to/tracing-source \
  --repo post-once=/path/to/post-once-source
```

Create a new task worktree only when no other active owner is already doing the task:

```bash
python3 tools/agent_worktrees.py admit \
  --repo /path/to/clawsweeper-source \
  --project clawsweeper \
  --task issue-123 \
  --owner named-agent \
  --purpose "Bounded issue 123 correction" \
  --base <verified-full-commit-sha>
```

On admission, a private lease records the source Git-common-dir, requested base and resolved commit, owner, task, branch and path. File-locking makes concurrent **cooperating users of this tool** serial. Other unmanaged shell commands can bypass it; this is not yet a universal Git filesystem permission boundary. Any agent bypassing the command is noncompliant and must be remediated at its own launcher/admission layer.

### Preventing stale-worktree reuse

An idempotent admission is refused when the existing leased tree is clean,
its HEAD is behind the locally tracked origin/main, and its commit is already
an ancestor of that main. That tree remains untouched; the owner must reconcile
and admit a fresh task before writing new work. Dirty trees are preserved for
explicit recovery rather than being automatically replaced.

Run a **read-only** exact-upstream reconciliation after independently verifying
GitHub's full main SHA and confirming local origin/main matches it:

    python3 tools/agent_worktrees.py reconcile \
      --repo poststeward-showcase=/path/to/allowlisted-showcase \
      --upstream poststeward-showcase=<40-character verified GitHub main SHA>

The private report records which trees are clean and upstream-integrated,
which retain dirty work, and which require further branch review. A
ready/owned lease is not a deletion instruction. Reconciliation never checks
out source, mutates leases, removes worktrees or alters a running service.
It fails closed when the supplied SHA and tracked main differ. The supplied
SHA must first be checked against GitHub; local tracking refs alone are not
proof of current upstream state.

## Safe handling of the legacy estate

- The snapshot records Git registration (including prunable/missing), detached/branch, tracked staged/unstaged changes and normal-mode untracked entries. The untracked entry count may represent entire directories and is not an exhaustive file count.
- Inventory is a starting point, **not** a proof that changed code is unique, correct, safe to commit or not already integrated upstream. Correlate actual diffs and content hashes with approved PR heads, merged source and existing recovery archives.
- A branch named `release` or `security` carries no authority on its own. Identify exact Git object SHA and any work still dirty in that checkout.
- Prefer existing ClawSweeper recovery archives and owner handoffs. Do not recapture large payloads or move archived evidence onto the shared D: volume while a local-CI owner job or archive move is in progress.
- The Post-Once installed release and its running processes are protected; direct source or worktree mutations to installed release directories are prohibited.
- Freeze no system globally. Keep shared CI admission, Cloudflare migration and tracing guardrails unchanged until their own owners release them.

## Proof of closure

For each project, closure requires an inventory with no unexplained worktree/branch, each unique change accounted for by a signed commit or a documented evidence-only disposition, upstream PR/merge readback where relevant, every protected gate resolved, and an independently observed deployed runtime where release is claimed. A clean directory, a successful local test or a GitHub merge alone is not sufficient.
