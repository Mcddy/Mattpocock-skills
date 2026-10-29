---
name: protocol-lab
description: Explore bounded distributed-protocol interleavings and faults with an explicit-state model checker, shortest counterexample traces and replay. Use for retries, deduplication, acknowledgements, crash recovery and model safety, rather than component-only property tests.
---

# Protocol Lab

Translate the protocol into explicit state, enabled events, durable versus volatile fields, transaction boundaries and network assumptions. State the safety invariant separately from liveness and fairness. Never infer eventual delivery merely from repeated retries.

Read [model and replay contracts](references/contracts.md). `scripts/check.py` ships a runnable append-service model with lost/reordered/duplicated messages, retry and restart. It also explores user-supplied finite transition graphs without interpreting executable expressions. That graph must faithfully encode the protocol; checking it cannot validate an omitted transition.

Run bounded breadth-first exploration, retain the shortest discovered violation and replay its exact action sequence. A durable deduplication control and a delivered-acknowledgement control establish useful contrasts. An atomic transaction must include both the operation identity and the mutation; a durable ID recorded separately after mutation leaves a crash window.

Report explored depth, visited states, frontier/budget exhaustion, enabled faults, state symmetry assumptions and the supplied invariant. A bounded no-counterexample result is not a global protocol proof. The bundled state model does not call a service or execute imported implementations. Inspect and author an explicitly approved adapter before replay against a real implementation; compare state observations at each step rather than just its final return value.

For unknown commit outcomes, describe a real reconciliation operation keyed by stable operation ID. A query may establish committed, absent or unavailable. Do not retry a non-idempotent mutation blindly or fabricate a resolved outcome during a partition. Use a purposeful sequence diagram or trace table when it helps; warm, customisable display should make durable state and uncertainty legible. Avoid a generic architecture dashboard or unsupported reliability promises.
