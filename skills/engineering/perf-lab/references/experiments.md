# Reproducible performance experiments

## Executable control

```text
python scripts/perf.py bench --sizes 40,80,160 --repeats 5 --seconds 8 --cache cold
```

The built-in workload is a seeded list of records with integer group/value fields. Baseline rescans the entire list for every record; candidate aggregates groups once and looks up each record's result. Both must return all `(record_id, group_total)` pairs in original order. `corrupt` deliberately drops a record and is retained as a failed-equivalence control. This is an in-memory software experiment, not a database or I/O measurement.

Sizes: 2..2000, at most 5 distinct increasing sizes. Repeats: 3..15. Time budget: 0.1..20 seconds, checked between bounded calls; it cannot pre-empt a single function invocation. Defaults are modest. Cold means no pre-call warmup; warm means an untimed invocation of both implementations before each pair. Neither arm uses a persistent application cache, so these labels are warmup conditions, not invented disk-cache resets. Order alternates baseline/candidate and candidate/baseline by repeat. Input creation, output hashing and equivalence checks occur outside the timed region. Record nanosecond timing as milliseconds without overclaiming resolution.

Pair results use matching `(size,repeat)` identifiers and the median of baseline/candidate timing ratios. A seeded bootstrap resamples actual pairs for a descriptive 95% interval; small microbenchmark intervals do not establish production effects or independent populations. Also retain medians and p90s per arm and size. Python/version/platform-family and clock implementation are recorded; no hostname, username or credentials are inspected.

The largest completed workload gets separately timed cProfile and tracemalloc runs for baseline/candidate. Traced Python allocation peak is not process RSS. Interpreter function calls are not hardware counters. The analytic comparison counter records list-element inspections and is explicitly a software-work count. Scaling fits log(median timing) against log(size) across at least three completed sizes; noisy short timings, GC, scheduling and cache effects limit interpretation. Do not convert an observed exponent into a universal complexity proof.

## Supplied records

```text
python scripts/perf.py records --measurements measurements.csv --outputs outputs.json --expected required_output.json
```

CSV required columns: `run_id,arm,cache_mode,elapsed_ms,exit_code,output_id`. Optional `pair_id` supplies real matching identities; duplicates within an arm/stratum/pair are rejected. Records must have finite nonnegative milliseconds, integer exit status, nonempty IDs/arm/cache mode and a referenced output. Output JSON maps IDs to actual output objects; expected JSON is the exact expected object. JSON canonical serialisation preserves boolean/number distinctions. A nonzero exit, missing output or unequal output rejects that run from speed comparisons while preserving the reason. Every baseline and candidate comparison stays within the same cache stratum.

When pair IDs are absent, report unpaired arm summaries and median ratio with that limitation. No inferential paired interval is produced. With pair IDs, report only complete matched pairs and retain unmatched IDs. Timing from supplied files is labelled `supplied_records`, not `executed_here`. Operation traces may explain a proposed experiment but are not automatically attributed to measured timing categories; overlapping profiler totals must not be added as disjoint durations.

For a real optimisation report, include workload/output hashes, input contract, reversible patch, unchanged correctness checks, timing distribution, sample exclusions, instrumentation overhead and an executable rerun. New APIs or dependencies need appropriate current primary documentation and permission boundaries. The shipped runner has no network, subprocess, imported-target or automatic-install path.
