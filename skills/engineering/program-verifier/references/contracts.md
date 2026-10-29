# Supported contracts and extension boundary

Input examples:

```json
{"contract":"ascii-spaces","seed":17,"cases":200}
```

```json
{"contract":"integer-range","lower":0,"upper":3,"observations":[{"value":true,"accepted":true},{"value":3,"accepted":false}]}
```

`ascii-spaces` accepts strings, trims only U+0020 at each end, collapses consecutive U+0020 characters to one and preserves every other code point exactly. Tabs, newlines, nonbreaking spaces, combining marks and accented letters remain unchanged. This is not general whitespace normalisation or transliteration.

`integer-range` is a validator: return a boolean accepting exactly a Python `int` (excluding `bool`) in the inclusive interval. JSON literal `2.0` parses to a float and is rejected; `2` parses to int. The contract intentionally distinguishes lexical numeric forms through JSON parsing. Lower/upper are integer values, excluding bool, within +/-100000. This is not a universal JSON-number rule.

`sort-integers` accepts lists of at most 32 integers, excluding bool, and returns an ascending list retaining duplicates. Other types are rejected. Properties are order, multiset preservation, idempotence and reversal invariance. A unique sorted set would satisfy order and idempotence while violating the multiset contract.

Generation combines fixed edge controls, exhaustive short strings over a small mixed alphabet and seeded random inputs. Case count is 1..5000; every generator output stays within a 96-character/32-element bound. No external dependency is needed. Registered targets: `correct`, `whitespace`, `ascii-loss`, `coerce`, `bool-int`, `exclusive-upper`, `unique-sort`; only targets compatible with the selected contract are accepted.

Shrinking uses deletion blocks and simple character/integer replacements. Each accepted reduction must retain the original failure category under fresh oracle and target evaluation. Maximum 300 shrink attempts per failure and at most 12 reported failures bound runtime. Reported metamorphic checks cover a separately limited prefix of cases and are not a claim of exhaustive testing.

Observation mode has no executable target. It reports the supplied observations and their contract differences; it cannot honestly shrink a failure by evaluating unseen inputs. Use their inputs as a regression corpus and propose new probes separately. For integer observations use `value` and required boolean `accepted`; for text/list use `input` and either `output` or boolean `rejected:true`. Each malformed observation is rejected with its index.

Example: `A\tB -> A B` violates ASCII-space preservation; `café -> cafe` changes content. `true -> accepted` violates integer typing; `3 -> rejected` violates inclusive upper bound. The controls `A B -> A B`, `0 -> accepted`, `-1 -> rejected` must remain visible alongside defects.

Adding a new program is an implementation task, not a configuration trick: implement a reviewed pure adapter and separate contract/oracle; sandbox or prohibit effects; inspect before running; retain caller limits. Do not add arbitrary `eval`, dynamic import paths, shell command inputs, pickle deserialisation or automatic dependency installation.
