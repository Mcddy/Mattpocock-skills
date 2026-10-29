# Methods: what the script computes and which published definition it uses

Every figure `scripts/analyse_responses.py` prints is defined here, with the source and a worked number that also appears as a test in `scripts/test_analyse_responses.py`. If a figure in a report cannot be traced to one of these, it should not be in the report.

## 1. Denominators

| Word | Meaning |
|---|---|
| respondents | Rows in the file |
| shown | Respondents the routing says saw the question. Everyone, when the question has no routing |
| not shown | Respondents routed past the question. They are not non-response and are never in a percentage for that question |
| skipped | Shown the question and left it empty. Skipped respondents stay in the "shown" denominator |
| answered | Shown the question and gave a recognised answer |

So `shown + not shown = respondents` and `answered + skipped = shown`. An answer that is not one of the instrument's options stops the run; with `--allow-unknown` it is counted as answered, under "other".

Every proportion is printed three ways where they differ: of those who answered, of those shown, of all respondents. Pick the one that matches the sentence being written and name it. "63% said yes" is not a finding; "12 of 19 who answered said yes (63%); 3 of the 22 shown the question skipped it" is.

Without an instrument the script cannot tell skipped from not shown and says so.

## 2. Interval for one proportion: Wilson score

For x of n and a standard normal quantile z (1.959964 for 95 per cent), with p = x / n:

```
centre = (p + z^2 / 2n) / (1 + z^2 / n)
half   = z * sqrt(p(1 - p) / n + z^2 / 4n^2) / (1 + z^2 / n)
interval = centre - half, centre + half
```

No continuity correction. At x = 0 the lower limit is exactly 0 and at x = n the upper limit is exactly 1.

Source: Wilson, E. B. (1927), "Probable inference, the law of succession, and statistical inference", Journal of the American Statistical Association 22(158), pages 209 to 212. It is method 3 in Newcombe, R. G. (1998), "Two-sided confidence intervals for the single proportion: comparison of seven methods", Statistics in Medicine 17, pages 857 to 872.

Why this one: the textbook interval p plus or minus z * sqrt(p(1 - p) / n) collapses to zero width at 0 of n and n of n and runs outside 0 to 1 for small n. Small n is the normal case here.

Worked: 3 of 4 gives 0.3006 to 0.9544. 5 of 9 gives 0.2667 to 0.8112. 0 of 10 gives 0 to 0.2775. The arithmetic is written out in the test `test_wilson_interval_hand_worked`.

What the interval is: how far the proportion could plausibly move with this many answers, if the respondents were a random draw from some larger group. What it is not: a correction for who was reached. A convenience sample of 400 has a narrow interval around a figure that may describe nobody but those 400.

## 3. Interval for a difference of two proportions: Newcombe hybrid score

For group 1 (x1 of n1, Wilson limits l1 and u1) and group 2 (x2 of n2, limits l2 and u2), with d = p1 - p2:

```
lower = d - sqrt((p1 - l1)^2 + (u2 - p2)^2)
upper = d + sqrt((u1 - p1)^2 + (p2 - l2)^2)
```

Source: Newcombe, R. G. (1998), "Interval estimation for the difference between independent proportions: comparison of eleven methods", Statistics in Medicine 17, pages 873 to 890, method 10. The same interval is often printed as `d -/+ z * sqrt(l1(1 - l1)/n1 + u2(1 - u2)/n2)` (and the mirror for the upper limit); the two forms are equal because a Wilson limit L satisfies (p - L)^2 = z^2 L(1 - L) / n. The test `test_difference_interval_hand_worked` computes both forms and checks they agree.

Worked: 3 of 4 against 5 of 9 gives a difference of +0.194 with interval -0.323 to +0.548. For 56 of 70 against 48 of 80 the script gives 0.0524 to 0.3339, which matches the figures the author recalls from Newcombe's own worked example; that table was not fetched in the authoring session, so treat it as corroboration, not as the check.

Reading it: if the interval includes zero, these responses do not show which group is higher. That is not evidence the groups are the same. If it excludes zero, the difference holds for a random draw of this size; whether it carries to anyone else still depends on how respondents were reached.

The script also says whether the two groups' own intervals overlap (not at all, in part, for most of their width, almost entirely, measured against the narrower interval). Overlap is the plainer picture for a reader; the interval on the difference is the one to rest a claim on.

The script never prints the word "significant". If a user asks for a test, name it, give its inputs (the two counts and denominators) and still show the interval. Do not run several comparisons and report the one that separates.

## 4. Scales

A scale question is ordered categories. The script prints the count for every point, including points nobody chose, and the middle answer (the category holding the median respondent; two categories when an even number of answers straddles a boundary).

A mean is printed only with `--scale-means`, and it carries the sentence that it treats the points as the numbers 1 to k, equally spaced. Use it only when comparing the same scale across waves or groups, and say that assumption in the report. Never call it a score.

`--combine "Q=Agree|Strongly agree"` gives one count for several options with its interval. Say which options were combined.

## 5. Cross-tabs

`--cross Q1 Q2` counts respondents who answered both. Rows are Q1's options, and percentages are of each row. Each row prints what one respondent is worth in percentage points (a row of 4: 25 points). Rows of ten or fewer are starred, because one answer moves them by ten points or more. That star is arithmetic about the row, not a rule about how many respondents a survey needs.

## 6. Quiz item analysis

Scoring: one point for each keyed answer. An omitted item scores nothing and is counted separately as omitted.

| Index | Definition | Source |
|---|---|---|
| Difficulty | Proportion of those shown the item who gave the keyed answer. Higher means easier | Classical test theory; the usual "p value" of an item |
| Discrimination D | Proportion correct in the upper score group minus proportion correct in the lower score group | Kelley, T. L. (1939), "The selection of upper and lower groups for the validation of test items", Journal of Educational Psychology 30(1), pages 17 to 24, which recommends groups of 27 per cent |
| Point-biserial (option) | (M1 - M0) / s * sqrt(p * q): M1 and M0 are the mean total scores of those right and wrong on the item, s the standard deviation of total scores dividing by n, p the proportion right, q = 1 - p. It equals Pearson's correlation between the 0 or 1 item score and the total | Standard definition; printed against the total and against the rest score (total minus this item), because an item is part of its own total |

Groups: k = 27 per cent of respondents, rounded, at least 1 and at most half. The upper group is everyone at or above the k-th highest score; the lower group everyone at or below the k-th lowest. Tied scores are kept together, so the groups can be larger than k and unequal, and their sizes are always printed. If the two cuts fall on the same score, no groups can be formed and D is not printed; difficulty and option counts still are. `--group-fraction` changes 27 per cent to anything from 10 to 50.

Worked: the ten-respondent, four-item table in `test_discrimination_index_hand_worked` gives upper and lower groups of four and D of +0.75, +0.50, +0.75 and +0.50; the point-biserial of its first item is 0.69 against the total and 0.36 against the rest.

Candidates the script prints, and how to read them:

| Candidate | Fires when | What to do with it |
|---|---|---|
| nearly everyone right | 9 in 10 or more correct | Fine as a warm-up. It tells nobody apart. Check the wording does not give the answer away |
| nearly everyone wrong | 1 in 5 or fewer correct | Check the key first, then the wording, then whether it was taught |
| option nobody chose | A wrong option with no takers | Replace it, unless nearly everyone was right anyway |
| wrong option chosen more by the upper group | A larger share of the upper group than the lower chose it, and at least two upper-group respondents did | Read the item: a second defensible answer, or ambiguity |
| possible miskey | The upper group's most-chosen answer is not the keyed one | Read the item against the key. If the key is wrong, fix it and run again: every total and both groups change |
| negative discrimination | D below zero | Usually a miskey or a trick; read with the two above |

The 9 in 10 and 1 in 5 lines are reading thresholds. They decide which items get a note, not which items are bad.

With few respondents every one of these is still printed, beside the group sizes and the sentence "one respondent changing one answer moves D by up to ...". With groups of 2 that step is 0.50, so D can only be -1, -0.5, 0, +0.5 or +1 and says almost nothing; report it that way. Item statistics describe how an item behaved for these people on this day.

## 7. Themes from free text

`--coding-sheet` writes one row per non-empty free-text answer: respondent id, question, text, a `screen` column naming any email address, phone number or web address found, and an empty `themes` column. Codes go in `themes`, separated by semicolons. `--themes` reads the sheet back.

A theme's count is the number of different respondents with at least one passage carrying the code. A respondent who makes the same point in three places counts once. Denominators: respondents who wrote anything, and all respondents. The number of coded passages is printed beside it in brackets and is never the headline.

Passages with no code are listed by respondent. Passages in the responses but missing from the coded sheet are reported and stay in the denominator. A code outside the codebook, a respondent or passage that does not exist, and two codes differing only in capitals are errors.

The script cannot tell whether a code was applied consistently. That needs a second coder, or the same coder on another day, applying the codebook to a sample and comparing.

## 8. What none of this can do

- Say anything about people who did not respond.
- Turn a convenience sample into an estimate for a population.
- Turn a tally from an informal questionnaire into a score on a validated scale, a type or a diagnosis.
- Show that a difference between groups was caused by the thing that distinguishes them.
