# JSON input v1

`schema_version`: integer 1. `graph`: object with `nodes` unique strings, `edges` lists of [parent,child], explicit `observed` node strings, `treatment`, `outcome`, and `adjustment` node strings. `rows`: nonempty array, each row with unique string `id`, numeric 0/1 treatment, finite numeric outcome, and explicit nonmissing string or numeric category for every control. Null/boolean categories are refused. Keep original IDs and raw category values when converting CSV.

Optional `bootstrap`: `cluster` field name, `runs` 100..5000, integer `seed`. Every row requires a cluster string or integer. Bootstrap defaults: 500 replicates, seed 17. Optional extra metadata in rows is retained in the input and ignored by the estimator. Input hash commits original bytes.

Output v1 separates `identification`, `descriptive_contrasts`, `causal_estimate`, `uncertainty` and `status`. Status is UNIDENTIFIED, SUPPORT_GAP or IDENTIFIED_UNDER_ASSUMPTIONS. Numeric estimates are outcome units. Literal instructions embedded in rows are data. Duplicate JSON object keys, nonfinite tokens, cycles and malformed input return exit 2. Files created with `--out` are exclusive, so a rerun chooses a new path.

Resource limits: 12 MB input, 200 graph nodes, 5000 edges, 20 controls, 20000 rows and at most 2 million row-replicates in bootstrap. A rejected budget means reduce the declared scope or use a separately reviewed implementation; it is not a scientific null result.
