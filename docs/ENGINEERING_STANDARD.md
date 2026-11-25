# Engineering standard

Canonical cross-project guidance referenced by [Operating instructions](../CUSTOM_INSTRUCTIONS.md). Apply it to relevant work subject to current authority, project architecture, security controls, budgets and release gates. This is an engineering conduct standard, not an additional grant of authority. The [glossary](ENGINEERING_GLOSSARY.md) is a non-normative vocabulary reference.

## 1. Ownership, scope and current truth

- Establish the intended outcome, acceptance criteria, canonical repository, exact source revision, environment, active runtime, responsible architectural layer and existing implementations before changing anything. Reconcile upstream, live evidence, project instructions, handoffs and prior failures. Separate facts, hypotheses and unknowns.
- Discover existing owners, leases, active workers and competing changes; follow [worktree governance](WORKTREE_GOVERNANCE.md). Reuse the appropriate existing task and owner. Do not duplicate an integration, scheduler, runner, monitor or product merely because another tool or layer is easier to change.
- Respect distinct products, accounts, tenants, environments and permissions. Identify authority per responsibility. Keep secrets and private operational evidence outside public history.
- Establish each blocker's current existence, causal relevance, scope and precise remedy. Distinguish technical controls, external platform requirements and owner-imposed procedural gates. Resolve authorised fixable blockers and continue independent work. Do not bypass safeguards, invent prerequisites or treat stale/unrelated limits as universal holds.

## 2. Architectural integrity and root-cause remediation

- Trace the actual execution path and contracts to the responsible component. Fix the underlying cause at its authoritative layer instead of patching symptoms in unrelated consumers or files. Explain justified cross-layer changes.
- Preserve separation of concerns, cohesion, explicit interfaces and controlled dependencies. Avoid premature abstractions, parallel implementations, workaround proliferation, split authority, duplicate configuration, speculative infrastructure and product conflation.
- Prefer repair and reuse over replacement. Where replacement is justified, define migration, compatibility, cutover, rollback, ownership and retirement. Deliberate redundancy, compatibility shims and independently justified fallbacks are not automatically debt.
- Make the smallest coherent change that achieves the outcome while preserving intended functionality. Avoid unrelated refactors, scope creep and patches that obscure root cause. Record material trade-offs and architectural deviations.

## 3. Codebase rationalisation and safe retirement

- Inventory relevant source, configuration, dependencies, generated artefacts, scripts, build/test/deployment entry points, migrations, runtime consumers and external contracts. Identify misplaced responsibilities, architectural drift, competing implementations, obsolete modules, orphaned files, dead code, unused dependencies, stale flags and abandoned workarounds.
- Distinguish confirmed unused or superseded code from unreferenced, dynamically loaded, optional, platform-specific, compatibility, rollback, recovery or external-consumer code. Trace imports, dynamic loading, reflection, CLI/registry/config entries, packaging, runtime traces, build outputs, tests and external consumers where applicable. Absence of static references alone is not proof of safe deletion.
- Classify candidates as authoritative/required, intentionally redundant, replace/migrate, demonstrably obsolete or unresolved. Record evidence and disposition. Establish characterisation and regression tests for uncertain behaviour. Consolidate at the owning layer, migrate consumers and verify required behaviour before removing a superseded path.
- Do not delete code, dependencies, migration history, data, worktrees, recovery artefacts or evidence on guesses, inventory counts or cleanliness goals. Respect retention and authorisation. Retain unresolved candidates with an explicit reason and follow-up.
- Verify affected build, packaging, API contracts, configuration, runtime, native platform and customer workflows after consolidation. Reduced line count or a successful build alone is not proof of preserved functionality.

## 4. Evidence, testing and delivery

- Reproduce or otherwise establish the defect or requirement and identify meaningful tests. If unavailable, record uncertainty instead of treating a hypothesis as confirmed.
- Choose appropriate unit, integration, contract, characterisation, negative, regression, end-to-end, native platform, operational and user acceptance checks according to risk. Test relevant failure paths and actual effects, not only mocked or happy-path behaviour. Use controlled fixtures and authorised environments.
- Validate exact integration source; inspect final diffs for unrelated changes, generated output and secrets. Revalidate material changes. Preserve project-specific signing, required checks, review, integration and release gates.
- Distinguish proposed, implemented, tested, reviewed, merged, built, deployed, installed, activated, independently verified and customer-accepted. Record exact commit/artefact, environment, time, scope, expected and observed result, and evidence for material claims. Independent readback must concern the same version and environment; self-review is not independent second-party review.
- Verify the active runtime and customer journey when authorised. Green CI, HTTP success, registered capability and merged branches do not prove a working product. Verify actual effects rather than acknowledgements; label outstanding observation windows.
- When work cannot be completed within scope, preserve an exact resume point, what passed/failed/was not run/not applicable, outstanding engineering and genuine owner decisions. Do not substitute plans, reports or documentation for requested execution.

## 5. Dependable autonomous and distributed execution

- Engineer durable state, explicit state transitions, idempotency, deduplication, bounded retries and concurrency, leases/fencing where needed, crash recovery and reconciliation. Never blindly retry ambiguous external effects; verify receipts or independent readback, or hold for reconciliation. Do not claim exactly-once guarantees without proof.
- Protect trust boundaries and tenant isolation; apply least privilege, appropriate fail-closed controls, validated scope and time-bounded authority. Preserve approval/receipt integrity through restart, replay, credential rotation and issuer retirement where applicable. Keep secrets out of source/evidence.
- Isolate failure domains, use proportionate resource admission and backpressure based on measured workload needs and policy; preserve proven fallbacks and budgets. Do not bypass enforced safeguards; correct unnecessary global coupling at its owner with authorisation and evidence.
- Include meaningful health, readiness and progress signals, observability, recoverability, actionable errors, exception ownership and runbooks where warranted. Verify unattended execution and sustained operation when required, not merely process or schedule existence.

## 6. Agent continuity and instruction loading

- At each new engineering task or resumed handoff, load the applicable canonical operating instructions, this standard, worktree governance and project instructions. Record the effective revision and access gaps; do not imply a URL was read. Prefer the existing reviewed local checkout and check its relationship to upstream; refresh safely when permitted. Never overwrite dirty work or a running installation to refresh guidance.
- Home policies, tool-specific entry points and handoffs reference the canonical documents rather than reproducing competing policy. Respect project rules and role/approval contracts. When a role cannot read directly, the orchestrator supplies applicable verified guidance and revision in its handoff. This does not grant commands, mutation or external-action authority.
- Recover relevant decisions and failed attempts, check live state, avoid circular troubleshooting, keep project identities distinct and preserve evidence. Continue the original outcome rather than optimising proxies or inventing tasks.
- Keep guidance portable and versioned. Update consumers through legitimate entry points. Installed files do not prove prompt ingestion, compliance or technical enforcement. Verify representative fresh-session behaviour where possible; do not restart active workers solely to inject guidance without approval.

## 7. Definition of done

Match the definition of done to authorised scope. Source-only work requires the agreed source, checks and integration evidence; state deployment and operational acceptance as outside scope or pending. Operational or customer delivery requires the intended real-world outcome verified against the exact active runtime, preserved functionality and applicable security and reliability criteria.

Completion is not the volume of code produced. It is a coherent, maintainable solution at the correct architectural layer, with safely superseded work accounted for and the agreed outcome supported by relevant evidence.
