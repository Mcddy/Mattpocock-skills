---
name: program-verifier
description: Derive executable contracts, generate semantic and metamorphic cases, compare implementations with an independent oracle, and shrink failures into a regression corpus. Use for bounded component correctness and observed parser or validator defects; passing finite tests is not arbitrary-program certification.
---

# Program Verifier

Begin with exact observable semantics: types, lexical distinctions, permitted normalisation, errors, state and side effects. Preserve Unicode, quotes, integers and user content where the contract requires it. Challenge the oracle with valid neighbouring controls before trusting it.

Read [contracts and safe execution](references/contracts.md). The bundled standard-library engine provides seeded generation, differential checks, metamorphic properties and bounded shrinking for three explicit contracts: ASCII-space normalisation, strict integer-range acceptance and integer-list sorting. Its registered implementations include deliberate defects for demonstration. It never evaluates code from an input or imports an arbitrary target module.

- For supplied observations, use `scripts/verify.py observations.json --observations`. Diagnose false accepts, false rejects and changed values without executing the supplied implementation. Do not call a shorter invented observation a tested minimal failure.
- For executable checks, use a reviewed registered implementation with `--target`. Inspect a task-specific adapter before adding an authorised target; constrain input size, exceptions and execution budget. External programs, untrusted notebooks and imported code require separate inspection and authorisation. No network or installation is implied.
- Keep the oracle, target and metamorphic checks separate. The oracle is a specification implementation, not the target copied with a new name. For normalisation, check preservation of non-ASCII spaces and all other characters as well as idempotence. Idempotence alone would accept destructive normalisation.
- Shrink a discovered failure while retaining its failure category. Store original and smaller input, observed output, expected output and shrink attempts. Greedy local minimality is not a mathematical globally smallest witness. Run saved regressions after any repair.

Report actual case counts, seed, supported domains, retained failures, skipped or capped work and explicit limits. Make concise defect explanations tied to inputs and output differences; avoid generic code-review padding. A warm failure explorer is optional, with reversible filters and full original data available. No passing badge may hide a skipped oracle or untested execution path.
