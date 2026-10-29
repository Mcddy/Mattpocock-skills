---
name: replicate-lab
description: Independently reproduce a supplied computational claim, reconcile units and normalisation, and compare actual results against predeclared tolerances. Use for paper-to-code replication and discrepancy diagnosis, not literature discovery alone.
---

# Replicate Lab

Deliver an inspectable implementation and a discrepancy ledger. A mismatch can mean a different convention, incomplete method specification, implementation error or a failed replication. It is not by itself disproof or misconduct.

Read [the contract and method](references/contract.md) before preparing inputs. First map the supplied equation, data, figure and reported values to an independently written minimal implementation. Record each adopted assumption. Keep an author's notebook as evidence; inspect it before any authorised execution. Never import notebook cells, expression strings or arbitrary modules through the helper.

The bundled `scripts/reconcile.py` is a reusable comparison engine with four explicit reference kernels and dimension-aware unit conversion. Other scientific methods need a separately inspected implementation, whose output can enter the `supplied-results` comparison mode. Declare tolerance before running; do not silently widen it until a discrepancy passes.

Run `python scripts/reconcile.py input.json --out output.json`. Output is exclusive: use a fresh path. Keep raw reported and reproduced values, original units, implementation identifier and source locator. A successful comparison means agreement within the stated numerical tolerance, not equivalence of the paper's design or truth of the scientific theory.

Inspect failed rows and repeat with one named assumption changed. Explain what changed numerically, retain both runs and preserve unsuccessful replications. Distinguish author-supplied output, independently executed output and analytic control. Use a concise equation/discrepancy table rather than a generic dashboard. For visual comparison, plot actual quantities with labelled units and error/tolerance bands.

Examples: `assets/unit-control.json` passes a metre/centimetre control. A request to “reproduce this decay result” should trigger this skill. “Find papers about decay” routes to research; “is this observational conclusion causal?” routes to Paper Audit or causal analysis.

Authorship: Codex continuation, after Shaun authorised completion without Claude. Producer tests do not establish independent acceptance.
