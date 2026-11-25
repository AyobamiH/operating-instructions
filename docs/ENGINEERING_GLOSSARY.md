# Engineering glossary

Non-normative vocabulary for identifying engineering failure patterns and corrective techniques. Terms marked (descriptive) are useful working labels, not necessarily standardised terms of art. Use the [engineering standard](ENGINEERING_STANDARD.md) for required conduct. A term does not prove a diagnosis, justify deletion or grant authority.

## Architecture and responsibility

- **Misplaced responsibility:** logic belongs to another owning component.
- **Architectural erosion:** gradual degradation of intended structure.
- **Architectural drift:** implementation diverges from intended architecture.
- **Wrong-layer remediation (descriptive):** fixing a symptom outside its owning layer.
- **Abstraction violation:** bypassing or misusing an established abstraction.
- **Leaky abstraction:** internal details escape an abstraction.
- **Separation of concerns violation:** mixing independent responsibilities.
- **Tight coupling:** excessive dependency between components.
- **Low cohesion:** unrelated responsibilities accumulate in a module.
- **God object:** one object centralises excessive responsibilities.
- **Boundary violation:** improperly crossing an architectural or security boundary.
- **Layer bypassing:** accessing lower-level functionality around its intended interface.
- **Dependency inversion violation:** high-level policy depends improperly on low-level detail.
- **Circular dependency:** dependencies form a cycle.
- **Responsibility fragmentation (descriptive):** one responsibility is scattered across components.
- **Split authority (descriptive):** multiple components claim the same authority.
- **Cross-cutting concern:** concern affecting several components, such as logging.
- **Shotgun surgery:** a small change requires many unrelated edits.
- **Feature envy:** a module relies excessively on another component's data or behaviour.

## Codebase debt and competing implementations

- **Codebase cruft:** accumulated obsolete or unnecessary remnants.
- **Dead code:** unreachable code or code without observable effect.
- **Orphaned modules:** disconnected from known consumers; verify before deletion.
- **Obsolete code:** superseded by a newer implementation.
- **Legacy residue (descriptive):** remnants of an earlier implementation.
- **Redundant implementation:** unnecessarily repeated functionality.
- **Implementation sprawl (descriptive):** competing implementations accumulate.
- **Patch proliferation (descriptive):** patches accumulate without consolidation.
- **Workaround accumulation (descriptive):** temporary workarounds become permanent complexity.
- **Code duplication / cloning:** identical or substantially similar code repeated.
- **Code bloat:** unnecessary growth of code size or complexity.
- **Dependency bloat:** unnecessary libraries remain.
- **Configuration sprawl (descriptive):** excessive or competing settings.
- **Stale feature flags:** flags retained beyond their intended use.
- **Zombie code (descriptive):** dormant or retired functionality that may resurface.
- **Accidental complexity:** complexity introduced by implementation choices rather than intrinsic requirements.
- **Technical debt:** future cost caused by current implementation or design decisions.
- **Architectural debt:** technical debt affecting structural design.
- **Negative-value code (descriptive):** code whose cost exceeds its benefit.

## Defects and problem solving

- **Symptom patching (descriptive):** correcting visible effects rather than root causes.
- **Root cause analysis (RCA):** identifying underlying failure mechanisms.
- **Root cause remediation:** correcting the underlying cause.
- **Speculative engineering (descriptive):** changes founded on unverified assumptions.
- **Premature abstraction:** abstraction before a genuine need.
- **Premature optimisation:** optimisation before identifying a meaningful bottleneck.
- **Overengineering:** complexity beyond what is necessary.
- **Gold plating:** unnecessary capabilities beyond requirements.
- **Reinventing the wheel:** unnecessarily rebuilding an existing solution.
- **Not invented here syndrome:** rejecting a solution because it originated elsewhere.
- **XY problem:** pursuing an assumed intermediate solution instead of the real objective.
- **Whac-A-Mole debugging (descriptive):** repeated symptom fixes without resolution.
- **Cargo cult programming:** applying techniques without understanding their purpose.
- **Regression:** a change breaks previously working behaviour.
- **Collateral regression (descriptive):** a fix breaks an unrelated capability.
- **Non-reproducible defect:** a reported failure not yet reliably reproduced.
- **Minimal reproducible example (MRE):** smallest reliable demonstration of a defect.
- **Regression test:** test intended to detect recurrence of a failure.

## Source, deployment and runtime

- **Source-runtime divergence (descriptive):** running code differs from source under inspection.
- **Version skew:** components operate on differing or incompatible versions.
- **Runtime drift:** runtime diverges from expected state.
- **Configuration drift:** actual configuration differs from intended configuration.
- **Environment drift:** development, staging or production diverge.
- **Deployment drift:** deployed system differs from intended release.
- **Release gap (descriptive):** completed source work has not reached release.
- **Integration gap (descriptive):** existing components are not correctly connected.
- **Activation gap (descriptive):** installed functionality is not enabled.
- **Contract drift:** interfaces or consumers depart from agreed contracts.
- **Schema drift:** actual data schema departs from expected schema.
- **Artefact provenance:** traceability to source and build process.
- **Reproducible build:** equivalent controlled inputs produce identical outputs.
- **Immutable deployment:** deploy fixed artefacts rather than modifying them in place.
- **Desired state:** intended system state.
- **Observed state:** actual system state.
- **State reconciliation:** bringing observed and desired state into alignment.
- **Release promotion:** moving a verified release across environments.
- **Rollback:** restore a previous known version or state.
- **Roll-forward:** correct through a subsequent release.

## Testing and evidence

- **False positive:** reporting a condition that is false.
- **False negative:** missing a true condition.
- **False green (descriptive):** tests pass while a relevant defect remains.
- **Test coverage gap:** relevant behaviour is missing from tests.
- **Mock-reality gap (descriptive):** simulation fails to represent real behaviour.
- **Test fidelity:** how well a test represents intended real behaviour.
- **Test oracle:** mechanism determining correct test outcomes.
- **Flaky test:** inconsistent result under equivalent conditions.
- **Test pollution:** one test leaves state affecting another.
- **Evidence gap (descriptive):** insufficient evidence for a claim.
- **Stale evidence:** evidence no longer establishes current state.
- **Evidence integrity:** accuracy, authenticity and protection of evidence.
- **Evidence provenance:** traceability to execution, version and environment.
- **Acceptance criteria:** conditions for accepting work.
- **Definition of done:** agreed completion standard for scope.
- **Verification:** establishing conformity with specified requirements.
- **Validation:** establishing fitness for intended use.
- **Independent verification:** checking via meaningfully independent evidence or process.
- **Operational acceptance testing (OAT):** testing operational readiness.
- **User acceptance testing (UAT):** testing whether user needs are satisfied.
- **End-to-end testing (E2E):** testing the full relevant workflow.
- **Negative testing:** testing invalid inputs and adverse conditions.
- **Fault injection:** deliberately introducing faults to observe behaviour.
- **Dogfooding:** using one's own product in actual work.

## Durable execution and distributed systems

- **Idempotency:** repeated operations have the same intended effect.
- **Deduplication:** detecting and preventing duplicate processing.
- **At-most-once delivery:** zero or one delivery.
- **At-least-once delivery:** one or more deliveries under stated guarantees.
- **Effectively-once execution:** retries occur but intended effects happen once under stated assumptions.
- **Durable execution:** work survives interruption with persisted state.
- **Checkpointing:** persisting progress for resumption.
- **Crash consistency:** state remains valid or recoverable after a crash.
- **Crash recovery:** restoring correct operation after termination.
- **Replay safety:** replay does not cause unintended effects.
- **Retry semantics:** rules governing retry effects.
- **Exponential backoff:** exponentially increasing retry delays, often with jitter.
- **Retry budget:** limit on retries or their cost.
- **Poison message:** a message repeatedly fails processing.
- **Dead-letter queue (DLQ):** failed items routed for separate handling.
- **Lease:** time-limited resource ownership.
- **Fencing token:** token enforced by a resource to reject stale owners.
- **Race condition:** incorrect behaviour depends on execution timing.
- **Split-brain:** multiple participants improperly act as exclusive authority.
- **Distributed lock:** coordination of exclusive access across processes.
- **Orphaned process:** process lacking appropriate lifecycle management.
- **Resource leak:** resources remain allocated beyond useful lifetime.
- **Compensating transaction:** counteracts an earlier completed effect.
- **Transactional outbox:** records an event with a database transaction for later delivery.
- **Eventual consistency:** replicas converge when updates cease and communication succeeds.
- **State machine:** explicit states and allowed transitions.
- **Ambiguous outcome:** an effect may have occurred but confirmation is missing.

## Infrastructure, CI and capacity

- **Admission control:** deciding whether work can enter an execution system.
- **Resource contention:** workloads compete for limited resources.
- **Resource starvation:** a workload cannot obtain resources needed to progress.
- **Head-of-line blocking:** a blocked item prevents subsequent work.
- **Backpressure:** restraining incoming work to match capacity.
- **Concurrency limit:** maximum simultaneous in-flight work.
- **Parallelism:** multiple tasks executing simultaneously.
- **Capacity planning:** matching resources to workloads.
- **Workload isolation:** preventing workloads interfering.
- **Failure domain:** portion affected by a common failure.
- **Blast radius:** scope of potential damage.
- **Single point of failure (SPOF):** one dependency can disable the relevant system.
- **Cascading failure:** one failure triggers others.
- **Bulkhead isolation:** separating failure domains to limit propagation.
- **Circuit breaker:** temporarily preventing calls to a failing dependency.
- **Graceful degradation:** preserving essential service during partial failure.
- **Failover:** transfer responsibility to an alternative.
- **Failback:** return responsibility to the primary.
- **Control plane:** management and coordination layer.
- **Data plane:** layer carrying out workloads or processing data.
- **Runner affinity:** routing jobs to runners with required attributes.
- **Admission false rejection (descriptive):** rejecting a workload that could safely run.
- **Policy overconstraint (descriptive):** restrictions beyond justified safety needs.
- **Unnecessary global coupling (descriptive):** an unrelated global condition blocks independent work.

## Security, authorisation and governance

- **Principle of least privilege:** grant only required permissions.
- **Privilege escalation:** obtaining authority beyond originally granted privileges.
- **Privilege creep:** unnecessary privileges accumulate.
- **Trust boundary:** a point where trust assumptions change.
- **Security boundary:** enforced separation protecting resources.
- **Confused deputy problem:** a privileged component is induced to misuse its authority.
- **Credential leakage:** protected credentials become exposed.
- **Credential rotation:** replacing credentials securely.
- **Tenant isolation:** preventing unauthorised access across customers.
- **Broken object-level authorisation (BOLA):** failure to verify access to a specific object.
- **Fail-open:** allowing an operation when a protection mechanism fails.
- **Fail-closed:** denying an operation when a protection mechanism fails.
- **Default-deny:** rejecting unless explicitly permitted.
- **Defence in depth:** multiple complementary protection layers.
- **Time-of-check to time-of-use (TOCTOU):** state changes between validation and use.
- **Security theatre (descriptive):** apparent protection without meaningful security.
- **Approval scope creep (descriptive):** extending approval beyond intended scope.
- **Compensating control:** an alternative safeguard addressing a requirement.
- **Policy enforcement point (PEP):** component enforcing a policy decision.
- **Policy decision point (PDP):** component determining a policy decision.
- **Supply chain integrity:** assurance that dependencies and delivery artefacts have not been compromised.
- **Audit trail:** traceable record of actions, decisions and changes.
- **Procedural gate:** process requirement imposed by governance.
- **Enforced control:** restriction enforced by an actual system or platform.

## Reliability and operations

- **Observability:** inferring internal state from emitted signals.
- **Monitoring:** tracking predefined conditions and measurements.
- **Instrumentation:** adding mechanisms for collecting signals.
- **Telemetry:** operational data emitted by a system.
- **Silent failure:** failure without an appropriate signal.
- **Liveness:** whether a system can continue or eventually make progress.
- **Readiness:** whether a system is prepared to accept work.
- **Availability:** whether a service is accessible when required.
- **Reliability:** correct performance over a specified interval and conditions.
- **Resilience:** ability to withstand and recover from failures.
- **Recoverability:** ability to restore correct state and operation.
- **Self-healing:** automatic recovery from defined failures.
- **Operational maturity:** degree of dependable, maintainable operation.
- **Service-level indicator (SLI):** measured service characteristic.
- **Service-level objective (SLO):** target level of service performance.
- **Error budget:** permitted failure within an SLO window.
- **Mean time to recovery (MTTR):** average time to restore operation; specify the metric definition.
- **Canary deployment:** exposing a release to limited usage before wider rollout.
- **Soak testing:** extended operation to detect sustained-use defects.
- **Synthetic monitoring:** simulated workflows probing service behaviour.
- **Incident reconciliation (descriptive):** determining outcomes and unresolved effects after an incident.
- **Operational runbook:** documented operation and recovery procedures.
- **Toil:** repetitive, manual, automatable operational work.

## Git and collaborative engineering

- **Canonical repository:** authoritative repository for a project.
- **Source of truth:** authoritative source for a particular fact, state or responsibility.
- **Upstream:** original or authoritative project from which a consumer derives.
- **Downstream:** project or distribution depending on upstream.
- **Fork divergence:** a fork develops differences from upstream.
- **Branch divergence:** branches accumulate different changes.
- **Merge conflict:** changes cannot be combined automatically.
- **Integration conflict:** changes combine mechanically but conflict in behaviour.
- **Semantic conflict:** independently valid changes become incorrect together.
- **Competing pull requests:** independent PRs address overlapping work.
- **Superseded pull request:** a PR replaced by another approach.
- **Commit contamination (descriptive):** unrelated changes included in a commit.
- **Dirty worktree:** working directory has uncommitted changes.
- **Atomic commit:** one coherent, logically complete change.
- **Protected branch:** branch governed by enforced modification requirements.
- **Required status check:** enforced condition for integration.
- **Exact-source verification (descriptive):** checking the precise intended revision.
- **Maintainer alignment (descriptive):** fitting project conventions and responsibilities.
- **Upstream-first remediation (descriptive):** repairing authoritative source rather than patching consumers.
- **Ownership conflict:** multiple actors attempt overlapping mutations.

## AI agent failure patterns

- **Context loss:** earlier relevant information is unavailable or lost.
- **Context fragmentation (descriptive):** information scattered across sessions or systems.
- **Context contamination (descriptive):** unrelated project or task information influences current work.
- **Context drift (descriptive):** departure from original task context.
- **Goal displacement:** intermediate goals replace the intended outcome.
- **Task substitution (descriptive):** performing an easier task instead of the requested one.
- **Scope creep:** work expands beyond agreed scope.
- **Tool-selection error (descriptive):** using an unsuitable tool despite an existing suitable capability.
- **Tool-use hallucination (descriptive):** claiming tool actions or results that did not occur.
- **Ungrounded reasoning:** conclusions lack evidence.
- **Premature conclusion:** declaring diagnosis or resolution before verification.
- **False blocker (descriptive):** a reported obstacle does not prevent the requested work.
- **Blocker conflation (descriptive):** applying an obstacle to independent work.
- **Circular troubleshooting (descriptive):** repeating investigation without new evidence or progress.
- **Execution loop (descriptive):** repeated actions produce no meaningful progress.
- **Analysis paralysis:** excessive investigation prevents execution.
- **Planning churn (descriptive):** repeated planning replaces implementation.
- **Approval churn (descriptive):** unnecessarily reopening settled approval decisions.
- **Human-in-the-loop dependency:** a workflow requires human participation.
- **Automation bias:** uncritically trusting automated conclusions.
- **Goal misalignment:** agent behaviour does not serve the objective.
- **Reward hacking:** optimising proxy reward in a way that undermines intended goals.
- **Proxy optimisation (descriptive):** improving convenient measures rather than meaningful outcomes.
- **Completion theatre (descriptive):** appearance of completion without the agreed outcome.
- **Product conflation (descriptive):** treating distinct products as one.

## Product and customer outcomes

- **Feature completeness:** required features are implemented.
- **Functional correctness:** behaviour conforms to requirements.
- **Production readiness:** necessary conditions for production operation are satisfied.
- **Operational readiness:** systems and owners can operate dependably.
- **Product-market fit:** a product satisfies meaningful market demand.
- **Value realisation:** expected benefits achieved in actual use.
- **Capability discovery:** users can find and understand functionality.
- **Discoverability gap (descriptive):** existing functionality is difficult to find.
- **Usability gap (descriptive):** existing functionality is difficult to use effectively.
- **Workflow fragmentation (descriptive):** tasks unnecessarily divided across systems.
- **Broken handoff (descriptive):** work fails to transfer between stages.
- **Happy-path engineering (descriptive):** success cases prioritised over failure paths.
- **Last-mile engineering (descriptive):** remaining work required to make functionality usable.
- **Minimum viable product (MVP):** smallest product for testing meaningful customer value.
- **Minimum marketable product (MMP):** product sufficiently complete for its intended market.
- **Feature factory (descriptive):** producing features without measuring value.
- **Outcome-driven engineering (descriptive):** evaluating success against practical outcomes.
- **Output-outcome gap (descriptive):** delivered artefacts do not establish intended results.
- **Goodhart's law:** when a measure becomes a target it may cease to be a good measure.

## Portfolio, delivery and unfinished work

- **Work in progress (WIP):** work started but not completed.
- **Excessive WIP:** too much unfinished work simultaneously.
- **WIP limit:** limit on concurrent unfinished work.
- **Project sprawl (descriptive):** uncontrolled proliferation of projects.
- **Portfolio fragmentation (descriptive):** insufficient coordination of related initiatives.
- **Delivery bottleneck:** constraint limiting delivery throughput.
- **Critical path:** dependency sequence determining earliest completion.
- **Dependency management:** coordinating work with prerequisites.
- **Dependency hell:** overly complex or conflicting dependencies.
- **Bus factor:** minimum number of people whose loss would critically impair a project.
- **Handoff failure (descriptive):** essential context or responsibilities lost during transfer.
- **Knowledge silo:** important knowledge is isolated.
- **Decision debt (descriptive):** unresolved decisions accumulate and obstruct progress.
- **Documentation debt:** missing or outdated documentation increases cost.
- **Maintenance burden:** ongoing cost of supporting systems.
- **Sunk cost fallacy:** continuing because of past investment rather than future value.
- **Opportunity cost:** benefit sacrificed by choosing one activity over another.
- **Delivery debt (descriptive):** developed work accumulates without integration, release or acceptance.
- **Engineering closeout (descriptive):** completing outstanding engineering, verification and handoff obligations.
- **Decommissioning:** safely retiring a system or capability.

## Corrective techniques

- **Architectural audit:** inspect responsibilities and boundaries.
- **Dependency analysis:** trace dependencies and consumers.
- **Impact analysis:** determine effects of a proposed change.
- **Root cause isolation:** narrow a failure to its responsible mechanism.
- **Architectural conformance testing:** check implementation against architectural rules.
- **Codebase rationalisation (descriptive):** systematically reduce unnecessary complexity.
- **Implementation consolidation (descriptive):** consolidate competing implementations into an authoritative solution.
- **Canonicalisation:** establish and consistently use a standard representation or authority.
- **Modularisation:** divide functionality into coherent, bounded modules.
- **Decoupling:** reduce unnecessary dependencies between components.
- **Encapsulation:** hide implementation details behind controlled interfaces.
- **Refactoring:** improve internal structure while preserving intended behaviour.
- **Behaviour-preserving migration:** move functionality without unintended observable change.
- **Characterisation testing:** capture existing behaviour before modifying unfamiliar code.
- **Contract testing:** verify interacting components respect agreed interfaces.
- **Static analysis:** examine code without executing it.
- **Dynamic analysis:** examine actual execution behaviour.
- **Mutation testing:** deliberately modify code to assess test effectiveness.
- **Differential testing:** compare implementations under equivalent inputs.
- **Chaos engineering:** controlled experiments to learn how systems withstand failures.
- **Performance profiling:** measure execution time and resource consumption.
- **Capacity benchmarking:** measure realistic resource requirements.
- **Remediation verification (descriptive):** establish that a correction removes the targeted defect.
- **Architectural fitness functions:** automated checks protecting architectural characteristics.
- **Dependency pruning:** remove demonstrably unnecessary dependencies.
- **Dead code elimination:** remove code established as unnecessary or unreachable.

## Engineering disciplines and principles

- **Architectural integrity:** maintaining responsibility ownership and architectural boundaries.
- **Evidence-driven software engineering (descriptive):** grounding decisions and completion in relevant reproducible evidence.
- **Dependability engineering:** engineering for reliability, availability, maintainability, safety and security as applicable.
- **Site reliability engineering (SRE):** applying software engineering to service operation and reliability.
- **Systems engineering:** coordinating a complete system and its lifecycle.
- **Agentic systems engineering (descriptive):** designing autonomous agents with bounded authority, durable execution and verifiable effects.
