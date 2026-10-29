# Households paying for regular lawn mowing: estimate

Fermi estimate: factors with ranges, simulated.

Written by the authoring session from `top-down.txt`, `bottom-up.txt` and `comparison.txt` in this folder. One input is a real figure from the Australian Bureau of Statistics, read by the authoring session and read again by a reviewing session on 2026-10-09; every other input is an assessment made without research, to show the method. Do not quote the result as a market size.

## Answer

Between about 450,000 and 1.4 million Australian households pay for a regular lawn-mowing service during 2026. That is the stretch on which two independent decompositions agree. The top-down median is 620,000 and the bottom-up median is 1.3 million, a factor of two apart, so the honest summary is "several hundred thousand to a bit over a million".

If one figure is unavoidable: around 900,000, uncertain by a factor of two either way. ASSESSMENT: 900,000 is the geometric midpoint of the two medians (the square root of 620,000 x 1,300,000 is 898,000). It is not the output of either model.

Quantity: private households with six or more paid mowing visits a year. Body-corporate and commercial contracts are excluded.

Dominant uncertainty: the share of lawn-owning households that pay someone to mow. It is an assessment with a fivefold range (5% to 25%) and it alone accounts for nearly all of the top-down spread.

## What was looked up and what was assumed

| Input | Tag | Value | Basis |
|---|---|---|---|
| Occupied separate houses | FACT | 6,710,582 at the Census of 2021-08-10 | ABS, 2021 Census All persons QuickStats, Australia, read 2026-10-09. The "Dwelling structure" table, which covers occupied private dwellings excluding visitor only and other non-classifiable households, prints "Separate house 6,710,582 72.3". https://www.abs.gov.au/census/find-census-data/quickstats/2021/AUS |
| Growth in occupied separate houses since the Census | GAP, entered as an assumption | 1.03 to 1.10, uniform | Not looked up. One to two per cent a year over five years |
| Share of separate houses with a lawn | ASSESSMENT | 60% to 95%, uniform | No source found; bounds only |
| Share of those who pay for regular mowing | ASSESSMENT | 5% to 25%, lognormal | General knowledge: most mow their own. Surprised under 1 in 20 or over 1 in 4 |
| Operators running a domestic mowing round | GAP | 15,000 to 70,000, lognormal | Official business counts were not looked up in this session |
| Regular customers per operator | ASSESSMENT | 25 to 90, lognormal | 5 to 8 lawns a day on a two to four week cycle at full time; many operators are part-time |
| Share of an operator's regulars that are households | ASSESSMENT | 70% to 95%, uniform | The rest are agents, body corporates and small commercial sites |

## Two decompositions

| | Formula | Median | 90 percent range |
|---|---|---|---|
| Top-down | occupied separate houses x growth x with a lawn x paying | 620,000 | 270,000 to 1.4 million |
| Bottom-up | operators x regular customers each x share that are households | 1.3 million | 450,000 to 3.5 million |

The ranges overlap from 450,000 to 1.4 million: about 70% of the top-down range and about 60% of the bottom-up, on a log scale. Each median lies inside the other's range. The decompositions are compatible. Neither is confirmed by the other, because both rest on assessed inputs.

The bottom-up sits higher. The likeliest reasons, in order: the operator range is too high, or operators' books count customers the top-down definition excludes (one-off jobs counted as regulars), or more households pay than the 5% to 25% assumed.

## What drives it

- Top-down: the share who pay. Rank correlation +0.96; on its own it moves the result from 280,000 to 1.4 million. Nothing else in that model matters by comparison (lawn share +0.26, growth +0.04).
- Bottom-up: the number of operators (+0.74; 590,000 to 2.7 million) and customers per operator (+0.61; 670,000 to 2.4 million).

Worth finding out, in this order:

1. The operator count. An official count of gardening and lawn businesses would replace the widest bottom-up input with a fact.
2. The share of households that pay for garden services, from a household spending survey if one reports it.

The dwelling growth figure is also a gap, and closing it would change almost nothing.

## Checks

- Anchor: the result cannot exceed the number of occupied separate houses, taken as the Census count of 6,710,582 scaled up 10% (the top of the assumed growth range), which is 7,381,640. Top-down: 0 of 20,000 runs above it. Bottom-up: 45 of 20,000 (under 1%).
- Implied share: against about 7.1 million occupied separate houses (6,710,582 at mid-range growth), the top-down median is about 1 house in 12 paying for mowing and the bottom-up median is nearer 1 in 5. Both are believable, and the bottom-up one is at the high end of what the top-down assumed.

## What would change it

- "Regular" is defined as six or more visits a year. A looser definition raises the figure; operators may count their regulars more loosely than this.
- Townhouses with small lawns are left out of the top-down model, which pushes it low.
- The inputs are treated as independent. If areas with more operators also have fewer customers each, the bottom-up range is narrower than printed.

For one town instead of the country, replace the dwelling counts with that town's Census figures and the operator range with a count from a local directory. The method does not change.

## To reproduce

`top-down.json` and `bottom-up.json`, 20,000 runs each, seed 1.
