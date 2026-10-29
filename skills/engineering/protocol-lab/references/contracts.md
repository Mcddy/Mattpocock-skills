# Explicit model contracts

## Append model

```json
{"kind":"append","strategy":"volatile","operations":["op7"],"max_sends":2,"max_events":8,"max_states":10000,"max_messages":3}
```

Strategy `volatile` records deduplication IDs in memory; restart clears them. `durable` persists ID and append in one atomic model transition. IDs carry an immutable payload equal to their ID in this bounded model. At most 3 IDs, 1..3 sends per ID, queue capacity 1..6, depth 1..16, 1..100000 states. The checker runs no external system and no arbitrary input program.

Client-send enqueues a write; any queued write or acknowledgement can be delivered or dropped; writes can be duplicated within the queue cap; crash stops server write delivery, clears volatile IDs and retains durable records; restart resumes delivery. A delivered write performs a single atomic append/dedup step and queues its acknowledgement if capacity permits. Client retries use the same ID. The invariant is at most one durable record per ID. Delivered acknowledgement stops future sends for that ID, although already queued duplicates can still arrive.

BFS retains a predecessor for each canonical state and reconstructs the shortest trace to its first invariant failure. State includes queue order, durable log, dedup IDs, client completions and send counts. Repeated crash or message loss cannot demonstrate eventual completion. `liveness_claim` is always UNPROVEN; an explicit drop-only schedule shows why universal eventual-delivery fails when no fairness assumption is supplied. Fairness is not silently inserted.

Replay: `check.py --replay trace.json` takes a result object or an array of exact action objects. Every action must be enabled at its step; otherwise it refuses the trace with the first invalid index. This replays the model only. Implementation trace-refinement requires a separately inspected adapter; the included checker never imports arbitrary code or sends network traffic.

## Finite graph model

```json
{"kind":"graph","initial":"idle","states":{"idle":{"safe":true},"done":{"safe":true},"duplicate":{"safe":false}},"transitions":[{"from":"idle","to":"done","event":"append"},{"from":"done","to":"duplicate","event":"retry"}],"max_events":5,"max_states":100}
```

Up to 1000 explicit states and 10000 transitions; state records contain a required boolean `safe`. IDs and events are nonempty strings; all transition endpoints must exist. No code, expressions, implicit fairness or state generation is evaluated. This mode is useful for independently specified finite models, including deadlock inspection (reachable states with no outgoing transitions). Deadlock can be an intended terminal state; the checker lists it instead of automatically declaring a safety violation.

## Worked outcome

For volatile IDs, a shortest violation can involve send, delivery, crash, restart, retry and delivery. A missing acknowledgement makes the client uncertain; restart erases the volatile identity, so retry appends again. Durable atomic deduplication avoids this duplicate in the bounded exploration. A lost acknowledgement still leaves completion unknown to the client. This distinction remains even if no safety counterexample is found.
