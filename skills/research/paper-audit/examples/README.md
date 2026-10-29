# Examples for paper-audit

Two complete audits, made by the session that wrote the skill by following the skill's own procedure. A second session reviewed them on 2026-10-09, regenerated every output with the repaired scripts, and added the p value checks to the trial audit (its finding 10). Nobody outside those two sessions has checked them.

Both documents audited are SYNTHETIC: invented for this purpose and labelled as invented at the top. No real paper, product, vendor or author is involved, and nothing here should be cited.

## synthetic-trial/

A two-page invented trial report whose abstract claims a "40 percent reduction".

| File | What it is |
|---|---|
| `paper.md` | The invented paper |
| `extraction.json` | The numbers extracted from it, each with a locator, and what is marked not reported |
| `outputs/01-extraction-check.txt` | `extraction_check.py` on that file: one finding (a percentage that disagrees with its count), two advisories (unbalanced loss; a changed primary outcome) |
| `outputs/02-...` to `09-...` | `effect.py` output for loss by group, the headline outcome, the registered outcome (each with the paper's p value checked against the counts), the continuous outcome, the inconsistent percentage, the relative claim in absolute terms, one scenario for the people lost, and the share who stopped the drink |
| `audit.md` | The written audit and verdict |

What the audit finds: the 40 percent is 2.0 percentage points (2.9% against 4.9%); 32% of one group and 10% of the other were lost, and those who stopped the drink were removed; the primary outcome was changed after follow-up ended, and the registered one shows no clear difference. It also finds one percentage and one p value that do not match their own counts, and treats both as discrepancies to be explained, not as evidence of anything more.

## synthetic-benchmark/

An invented vendor note claiming a model "outperforms" on a 50-question benchmark.

| File | What it is |
|---|---|
| `vendor-note.md` | The invented note |
| `extraction.json` | The extraction file |
| `outputs/01-extraction-check.txt` | The check: one finding (17 of 20 is not 89%) |
| `outputs/02-...` to `10-...` | `effect.py` output for each system's score, the two comparisons, the post hoc subset, the inconsistent percentage, the errors comparison, and two illustrations of what a larger test set would allow |
| `audit.md` | The written audit and verdict |

What the audit finds: 82% against 72% is 5 questions, with a 95 percent interval from 7 points worse to 26 better; the systems were given different prompts; the questions share a source with the model's fine-tuning data; one run, no variance, unblinded marking.

## To regenerate

From inside either folder:

```
python ../../scripts/extraction_check.py extraction.json
```

It prints the `effect.py` commands for each outcome. The exact command behind each output file is the first word of its name plus the counts shown in its first lines; for example `outputs/03-two-by-two-headline-outcome.txt` is

```
python ../../scripts/effect.py two-by-two --a-events 24 --a-total 816 --b-events 53 --b-total 1080 --a-label "FOD-7" --b-label "Usual diet" --treated a --event bad --reported-p 0.03
```

Output 04 is the same command on the registered outcome's counts with `--reported-p 0.77`; it exits 1 because that p value does not match.

The outputs are deterministic and should match byte for byte.

## To test it

- Every number in each `audit.md` table names the output file it came from. Open the file and compare.
- Change a count in `extraction.json` so that a percentage no longer fits, and `extraction_check.py` should report a FINDING.
- `python ../../scripts/test_effect.py` runs the calculators' own tests against hand-worked and published values; `--planted` shows each test failing on a broken copy.
