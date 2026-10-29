# Yearly cost of a metered service: estimate

Fermi estimate: factors with ranges, simulated.

SYNTHETIC. Every input is invented to show the method. Written by the authoring session from `output.txt` in this folder. Not independently checked.

## Answer

Usage charges over the next twelve months: median about 11,000 dollars, 90 percent range 2,500 to 49,000. FACT from the run: 3,696 of 20,000 simulated years (18%) go over the 25,000 budget.

Do not refine the price or the caching figures. Measure requests per workday for the first two weeks after rollout and run the model again. Until then, set a spend alert at the budget.

## What was looked up and what was assumed

| Input | Tag | Value | Basis (all SYNTHETIC) |
|---|---|---|---|
| Price per thousand units | FACT | 0.012 | price sheet dated 2026-09-01 |
| Workdays | FACT | 230 | organisation calendar |
| Requests per workday | ASSESSMENT | 400 to 6,000, lognormal | pilot logged 900 to 1,400 from 6 users; rollout to 20 to 40 users could multiply that by 3 to 6, or adoption could stall |
| Thousand units per request | ASSESSMENT | 2 to 5, normal | pilot average 3.4; lengths vary about equally either side |
| Share served from cache | ASSESSMENT | 10% to 50%, uniform | only the pilot's worst and best weeks are known |
| Retry overhead | ASSESSMENT | 1.0 to 1.3, most likely 1.05, triangular | failed calls are billed again |

Formula: requests per workday x workdays x (1 - cached share) x thousand units per request x price x retry overhead.

## What drives it

| Input | Rank correlation with the cost | Cost with this input alone at its low and high |
|---|---|---|
| Requests per workday | +0.92 | 3,000 to 45,000 (a factor of 15) |
| Thousand units per request | +0.29 | 6,600 to 17,000 |
| Share served from cache | -0.18 | 15,000 to 8,600 |
| Retry overhead | +0.07 | 11,000 to 13,000 |

Almost all the spread comes from one input. Usage after rollout is unknown to within a factor of 15, and nothing else in the model moves the cost by more than a factor of 2.5. Two weeks of request logs would turn that input from a guess into a measurement; a better price quote or a caching study would not change the picture.

## Checks

- Budget, as a threshold: 18% of runs exceed 25,000. The model does not contradict anything; it says the budget holds in roughly four years out of five under these assumptions.
- Mean against median: the mean is 17,000 and the median 11,000. The upper tail (heavy adoption) pulls the mean up. For "what will we probably pay", read the median. For "what should we provision on average", read the mean, and say that it is a mean.
- Every input at its median gives 12,000, close to the simulated median, as expected for a product.

## What would change it

- A price change during the year. The price is fixed in the model.
- Usage and request size moving together: if heavy users also send longer documents, the upper end is higher than printed. The script draws them independently.
- Fixed fees and staff time are out of scope.

## To reproduce

`model.json`, 20,000 runs, seed 1.
