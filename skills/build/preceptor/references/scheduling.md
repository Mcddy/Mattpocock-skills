# The review schedule, exactly

The cards in a course page are scheduled by SM-2. The same arithmetic exists twice: in `scripts/sm2.py` (the reference) and in the page's JavaScript. `scripts/test_logic.py` compares the two on 9,630 grade sequences, and `scripts/test_engine.py` drives a card through the page and compares what it stores with `sm2.py --trace`.

## The algorithm as published

FACT (source: SuperMemo archive, "Application of a computer to improve the results obtained in working with the SuperMemo method", section on algorithm SM-2, read 9 Oct 2026):

1. Each item starts with an E-Factor of 2.5.
2. Intervals in days: I(1) = 1, I(2) = 6, and for n above 2, I(n) = I(n-1) * EF. A fractional interval is rounded up.
3. Each response is graded 0 to 5: 5 perfect response; 4 correct after a hesitation; 3 correct with serious difficulty; 2 incorrect, where the correct answer seemed easy to recall; 1 incorrect, the correct answer remembered; 0 complete blackout.
4. After each repetition: EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)). If EF falls below 1.3 it is set to 1.3.
5. If the grade is below 3, repetitions start again from the beginning, without changing the E-Factor.
6. Items graded below 4 are repeated in the same day's session until each scores at least 4.

## How it is held

The E-Factor is stored as a whole number of hundredths (`ef100`: 2.5 is 250). Every change the formula can produce is a whole number of hundredths, so nothing is ever rounded and the Python and JavaScript versions cannot drift:

| Grade | Change to the E-Factor | Next interval |
|---|---|---|
| 5 | +0.10 | next in the sequence |
| 4 | 0 | next in the sequence |
| 3 | -0.14 | next in the sequence |
| 2, 1, 0 | none (a lapse never changes it) | 1 day |

A card's record is `{n, interval, ef100, due, last, reviews, lapses, again}`. `n` is the index of the interval the card is waiting through. One pure function, `sm2(n, interval, ef100, q)`, returns the new `n`, `interval` and `ef100`. It reads no clock and touches no page.

## Three decisions the publication leaves open

ASSESSMENT, each stated so it can be challenged. Confidence that these are faithful readings: moderate to high for the first two; the third is a deliberate departure.

1. **Which E-Factor sets the next interval.** The one just updated by the grade. The published steps are in that order: grade, modify the E-Factor, then use it.
2. **What "start from the beginning" gives.** After a lapse the card waits I(1) = 1 day, and the next successful review moves it to I(2) = 6 days: the sequence 1, 6, ... "as if the item was memorised anew". Some common implementations give 1, 1, 6 after a lapse. This one does not.
3. **A cap.** An interval is capped at 36,500 days so that a due date always exists. The published algorithm has no cap. The cap is first reached at the tenth straight grade of 5, 65 years after the card was first seen.

A fourth point is a reading, not a departure: the same-day repeats of rule 6 **do not change the schedule**. The publication does not say they should, and treating them as drill keeps one grade a day as the only thing that moves a due date.

## The four buttons

The page offers four buttons and says what each records:

| Button | Grade | Meaning shown to the learner |
|---|---|---|
| Again | 1 | Incorrect. The card starts again at 1 day. E-Factor unchanged. Comes back today. |
| Hard | 3 | Correct with serious difficulty. E-Factor falls by 0.14. Comes back today. |
| Good | 4 | Correct after a hesitation. E-Factor unchanged. |
| Easy | 5 | Perfect response. E-Factor rises by 0.10. |

Grades 0 and 2 exist in SM-2 and are accepted by the function, but no button records them. Since every grade below 3 has the same effect on the schedule, nothing is lost by offering one lapse button.

## The clock

- A day is a whole local calendar day on the device's clock, written `YYYY-MM-DD`. There are no times of day and no time zones in a schedule.
- A card is due when its due date is today or earlier. The page shows the date it takes as today.
- The page remembers the latest day it has seen for the course. If the device clock is later set **backwards**, due dates are still judged against that latest day: nothing becomes un-due, no schedule is recomputed, and the footer says so. Reviews done meanwhile are dated with the latest day seen.
- A clock set far forwards makes cards due early. The page cannot detect that, and once it has seen the later day it keeps it.
- A test clock, `?today=YYYY-MM-DD` in the address, is read only when the page's `html` element carries a `data-test` attribute. Shipped courses do not carry it.

## Worked examples

A new card, each review done on the day it falls due. E-Factor shown to two places.

| Grades | Interval after each grade (days) | E-Factor after each grade |
|---|---|---|
| 5, 5, 5, 5, 5 | 1, 6, 17, 50, 150 | 2.60, 2.70, 2.80, 2.90, 3.00 |
| 4, 4, 4, 4 | 1, 6, 15, 38 | 2.50 throughout |
| 3 ten times | 1, 6, 13, 26, 47, 79, 121, 167, 218, 284 | 2.36, 2.22, 2.08, 1.94, 1.80, 1.66, 1.52, 1.38, 1.30, 1.30 |
| 5, 4, 2, 3, 5 | 1, 6, 1, 6, 16 | 2.60, 2.60, 2.60, 2.46, 2.56 |
| 4, 4, 4, 1, 4, 4 | 1, 6, 15, 1, 6, 15 | 2.50 throughout |

The arithmetic behind three of those cells:

- Third 5 in a row: EF is 2.80, and 6 * 2.80 = 16.8, rounded up to 17.
- Fourth 4 in a row: 15 * 2.50 = 37.5, rounded up to 38.
- 5, 4, 2, 3, 5: the 2 is a lapse, so the interval returns to 1 and EF stays 2.60. The 3 lowers EF to 2.46 and, being the second success since the lapse, gives 6. The 5 raises EF to 2.56, and 6 * 2.56 = 15.36, rounded up to 16.

Reproduce any row with `python scripts/sm2.py --trace "5,4,2,3,5" --start 2026-10-09`. `python scripts/sm2.py --selftest` checks these tables and four deliberately wrong variants.

## What a review does to mastery

Nothing a review does can demonstrate an objective; only a gate does that. A scheduled review graded Good or Easy records the date the card's objective was last recalled, which keeps a demonstrated objective off the "due for a check" list. A scheduled review graded Again adds one to that objective's count on the weakness map. Activity points for reviews are counted separately and say nothing about competence.

## What the page does not do

- It does not remind, notify or run in the background. Cards are due when the learner opens the page.
- It does not limit new cards per day, spread reviews to even out load, or add random variation to intervals.
- It does not decay anything silently. An objective's evidence is shown with its date, and old evidence is listed, not discounted.
- It does not check the grades. The learner marks their own recall, so the schedule is only as honest as the marking.
- It does not model memory. SM-2 is a simple published rule, used here because it can be stated and tested exactly, not because it is the most accurate scheduler there is.
