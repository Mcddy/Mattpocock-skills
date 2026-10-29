---
name: perf-lab
description: Diagnose and improve measured software performance using controlled paired benchmarks, correctness checks, scaling experiments, call counts and allocation traces. Use for reproducible latency and resource experiments; never infer hardware bottlenecks or production speedups from synthetic timings.
---

# Perf Lab

Define the required output, workload, environment, cache state and resource budget before timing. Performance evidence applies only to equivalent successful work. Preserve corrupt and failed runs as rejected observations instead of letting their fast timings win.

Read [experiment contracts](references/experiments.md). `scripts/perf.py bench` runs reviewed, bounded standard-library group-aggregation implementations with paired alternating order, controlled cold/warm definitions, scaling sizes, measured timings and separate call/allocation profiles. `scripts/perf.py records` analyses supplied experiment records without calling them measurements made here. Neither mode runs arbitrary imported programs.

For real code, inspect the workload and implementation, build a narrowly scoped adapter, and preserve the same correctness oracle before and after the change. Authorisation to benchmark does not permit host-wide tuning, process termination, security changes, background services or package installation. Check supported instrumentation instead of inventing CPU counters or unavailable hardware details.

Keep wall-clock timing, allocation peaks, interpreter call counts and application operation counters separate. Profile overhead is real: profiling runs must not supply the clean timing comparison. Stratify by cache/workload conditions. Use actual pair IDs when present; do not fabricate matched pairs from arbitrary rows. Retain run order, discarded outcomes and all numerical units.

Report effect sizes and distributions, uncertainty where supported, run budget and scaling observations. Explain a bottleneck only as far as controlled intervention and measured counters justify. A faster output-corrupting variant is rejected, a warm-versus-cold comparison is confounded, and a log-log slope is an observed range fit rather than proof of asymptotic complexity. Make concrete implementation recommendations, with plain subject-specific prose and no generic architecture filler. If a visual explorer helps, use warm customisable presentation with actual workload, strata and failure filters.
