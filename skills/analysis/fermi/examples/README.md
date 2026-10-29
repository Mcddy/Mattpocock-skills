# Examples: fermi

Two worked runs. Every `.txt` and `.json` output is the real, unedited output of `scripts/fermi.py` on the model beside it. Each `estimate.md` was written by the authoring session, following the skill's procedure, from those outputs. A second session reviewed them on 2026-10-09, replaced the dwelling inputs of the top-down model with one published figure it had opened and confirmed, regenerated every output and brought the first estimate into line. Nobody outside those two sessions has checked them.

## local-service-market

One quantity estimated two ways: a top-down model from dwelling counts and a bottom-up model from operators.

One input of the top-down model is real: 6,710,582 occupied separate houses at the 2021 Census, from the Australian Bureau of Statistics page "2021 Census All persons QuickStats, Australia" (https://www.abs.gov.au/census/find-census-data/quickstats/2021/AUS), read on 2026-10-09 and confirmed that day by a second session. An earlier draft derived occupied dwellings by subtracting 1,043,776 unoccupied dwellings from the 10,852,208 private dwellings on the "Housing: Census, 2021" page. That gives 9,808,432, which the QuickStats page does not support (it counts 9,275,217 occupied private dwellings once visitor-only and non-classifiable households are left out), so the derived figure was replaced by the published one. Every other input in both models is the authoring session's unresearched assessment, there to show the method. The result is not a market size to quote.

| File | What it is |
|---|---|
| `top-down.json`, `bottom-up.json` | The two models |
| `top-down.txt`, `bottom-up.txt` | Output of each |
| `comparison.txt` | Output of `--compare` on the two |
| `estimate.md` | The written estimate, about one page |

To regenerate, from this folder:

```
python ../../scripts/fermi.py top-down.json > top-down.txt
python ../../scripts/fermi.py bottom-up.json > bottom-up.txt
python ../../scripts/fermi.py --compare top-down.json bottom-up.json > comparison.txt
```

## api-cost

Yearly usage charges for a metered service. All inputs are SYNTHETIC. It shows the sensitivity table picking the one input worth measuring, an anchor used as a budget threshold, and a mean well above the median.

| File | What it is |
|---|---|
| `model.json` | The model |
| `output.txt`, `output.json` | Text and `--json` output of the same run |
| `estimate.md` | The written estimate |

```
python ../../scripts/fermi.py model.json > output.txt
python ../../scripts/fermi.py model.json --json > output.json
```

The same model and seed give the same output on any Python 3.8 or later, so a rerun should match these files byte for byte.
