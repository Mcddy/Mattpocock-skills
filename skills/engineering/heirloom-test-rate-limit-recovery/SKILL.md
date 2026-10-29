---
name: heirloom-test-rate-limit-recovery
description: "Test a client's rate-limit and transient-failure recovery with controlled responses, clocks and retry budgets. Use for 429 handling, quota exhaustion, Retry-After parsing and duplicate-effect risks; use webhook design for inbound event deduplication and resource-concurrency budgeting for scheduling capacity."
---
# Test rate-limit recovery

Make retries respect the applicable service contract, total work budget and operation semantics.

## Identify the actual limit

Collect client code, dated response headers/bodies, request timestamps, concurrency settings, account quota scope and a representative operation. Check the current official provider policy before interpreting limit headers or retryable statuses. Separate burst throttling, sustained quota exhaustion, authentication failure and a transport timeout; they need different recovery branches.

Record whether an operation is read-only, provably idempotent, or effectful with an unknown result. A timeout after a write may follow a completed effect. Do not classify it as safe to retry merely because no response arrived. Use an operation key or reconciliation when available; otherwise retain `RECONCILE_REQUIRED`.

## Build a bounded recovery controller

1. Parse the supplied retry guidance using its documented units and clock basis. If Retry-After can be a duration or HTTP date, test both, including stale dates and clock skew. For a malformed or absent value, use a declared conservative bounded fallback and record why.
2. Define a total deadline, maximum attempts, maximum sleep and maximum queued work. Calculate cumulative delay plus request time against the deadline before each retry. Count the original request in the attempt denominator.
3. Apply capped backoff with a seeded jitter fixture, not synchronized immediate retries from every worker. A shared account limit needs a coordinated admission controller; per-worker backoff alone may recreate the burst.
4. Retry only the documented transient categories. Stop or defer on known quota exhaustion until its reset or a new authorised budget. Preserve invalid-argument and authentication failures as terminal corrections, not exponential waiting.
5. Persist sufficient resume state: `operation_id, attempt, first_started, deadline, next_eligible_at, last_category, effect_state`. A restart must not reset the attempt ceiling or duplicate a possibly applied mutation.
6. Use a fake clock and response stub in tests. No actual sleeps of minutes or repeated paid calls are needed to verify timing arithmetic. If no client code exists, deliver the transition table and fixtures with execution GAP.

## Output and controls

Produce the client patch, `retry_policy.json` and `recovery_trace.csv`. Trace each observed category, chosen delay, remaining budget, next state and operation identity. Redact credentials and retain response source references. Distinguish measured fixture timing from predictions about a live account.

Require a normal transient response followed by success inside the deadline and an adversarial sequence that exhausts the retry budget. Add malformed guidance, restart after attempt two, and a lost write acknowledgement. A pass proves the controller's tested arithmetic and classifications, not an increase in the provider's quota.

Worked situation: four workers see the same throttle and each retries after one second. A shared gate staggers their admission. If the response instead identifies exhausted daily quota, additional jitter cannot restore capacity; defer rather than spending the remaining retry budget.
