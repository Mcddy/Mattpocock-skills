# Scheduling contract and worked example

Input JSON:

```json
{"capacity":2,"tasks":[{"id":"draft","duration":3,"resource":1,"after":[]},{"id":"review","duration":2,"resource":2,"after":["draft"]}]}
```

`capacity`, `duration` and `resource` are positive integers, excluding booleans. IDs are unique nonempty strings. `after` is a list of distinct existing task IDs. Tasks run indivisibly on integer ticks in `[start,start+duration)`. The resource is renewable: simultaneous demands sum to at most capacity. No release times, deadlines, multiple resources or setup times are implied. Optional `units`, `objective` and `time_semantics` must agree with these semantics. Maximum 12 tasks and duration total 120 ticks keep the bundled core bounded.

Result starts are keyed by task ID. The serial topological schedule is a feasible upper bound unless validation detects a cycle or oversized resource demand. The lower bound is the maximum of longest dependency path and ceiling(total resource work/capacity). The search tries each integer makespan from that bound upward, assigning all start choices in dependency order. The first feasible horizon is optimal only when every smaller horizon was exhaustively rejected. `--max-nodes` limits attempted assignments; hitting it yields UNRESOLVED with the retained serial incumbent, not infeasible. INFEASIBLE is reserved for explicit cycles or tasks requiring more capacity than exists.

The verifier checks start types, all IDs, nonnegative starts, dependency finish times and aggregate demand across sorted interval endpoints. Its method deliberately differs from the solver's tick occupancy array. The oracle enumerates every start tuple under each horizon, checks constraints independently and refuses spaces above `--max-combinations`. It is a small-case cross-check, not a production solver.

Example above has makespan 5; starting review at tick 2 violates the dependency even when resource capacity would fit. A task needing resource 3 is infeasible under capacity 2. A horizon search interrupted at one assignment remains unresolved. Report each distinction.

Inspect helpers before execution. They read explicit local JSON files and emit JSON on stdout; redirect into a chosen workspace file. They never execute imported programs, install packages, contact networks or rewrite inputs. Reject duplicate JSON keys and non-finite constants. Returned witnesses belong to this supplied model only.
