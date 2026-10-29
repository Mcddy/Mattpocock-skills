# The calculations in effect.py: formulas, sources, and how far each was checked

Every method is named in the script's output. This file gives the formula and says what the build session did to check it. Three levels are kept apart: worked by hand, matched against a published worked example that was retrieved and read, and matched against a value recalled but not retrieved.

Notation: k events in n; p = k/n; z = the standard normal quantile for the level (1.959964 for 95 percent).

## Proportion: Wilson score interval

    centre = (p + z^2/2n) / (1 + z^2/n)
    half   = z * sqrt(p(1-p)/n + z^2/4n^2) / (1 + z^2/n)
    limits = centre - half, centre + half

Source: Wilson EB (1927). Recommended over the simple (Wald) interval in Newcombe RG (1998), Statistics in Medicine 17:857-872.

Checked: by hand for 30/1000, 20/1000, 37/120 and 41/50 (arithmetic written out in `scripts/test_effect.py`). The four examples of Newcombe's Table I (81/263, 15/148, 0/20, 1/29) are reproduced to four decimal places against values recalled from that table; the R DescTools manual confirms these are the Table I examples, but no page printing the limits was retrieved. The Newcombe difference limits below, which were retrieved, depend on this function.

## Difference between two proportions: Newcombe's hybrid score interval (method 10)

With Wilson limits (l1, u1) for p1 and (l2, u2) for p2, and d = p1 - p2:

    lower = d - sqrt((p1 - l1)^2 + (u2 - p2)^2)
    upper = d + sqrt((u1 - p1)^2 + (p2 - l2)^2)

Source: Newcombe RG (1998), Statistics in Medicine 17:873-890.

Checked: against four published examples, read from paper 127 of the WUSS 2016 proceedings, which reprints Newcombe's Table II for this method: 56/70 against 48/80 gives 0.0524 to 0.3339; 9/10 against 3/10 gives 0.1705 to 0.8090; 10/10 against 0/20 gives 0.6791 to 1.0000; 84/101 against 89/105 gives -0.1177 to 0.0851. Newcombe's own paper was not opened. Also by hand for 30/1000 against 20/1000.

## Risk ratio and odds ratio: log method

    RR = p1/p2,              se(ln RR) = sqrt(1/k1 - 1/n1 + 1/k2 - 1/n2)
    OR = (a*d)/(b*c),        se(ln OR) = sqrt(1/a + 1/b + 1/c + 1/d)
    limits = exp(ln(estimate) -/+ z * se)

Sources: Katz D, Baptista J, Azen SP, Pike MC (1978), Biometrics 34:469-474, for the risk ratio; Woolf B (1955) for the odds ratio.

Checked: the risk ratio against the worked example in the SciPy documentation for `relative_risk` (10 of 75 against 12 of 225: 2.5, interval 1.1261564 to 5.5498508), which cites Katz. The odds ratio against Bland JM and Altman DG (2000), BMJ 320:1468 (141 of 561 against 928 of 14,453: 4.89, interval 4.00 to 5.99). Both retrieved and read. Both also by hand for 30/1000 against 20/1000.

A zero cell makes the log method undefined. The script reports null with a reason and applies no correction.

## Number needed to treat or harm

    number needed = 1 / |risk difference|, rounded up to the next whole number
    interval      = 1 / (each limit of the interval for the difference)

When the interval for the difference includes zero, the number needed runs from a benefit, through infinity, to a harm, and has no finite interval. The script reports it as not estimable.

Sources: Altman DG (1998), BMJ 317:1309-1312; rounding up is the convention in the Cochrane Handbook (version 5.1, section 12.5.4).

Checked: by hand. The rounding convention was read in the Cochrane Handbook. Altman's article is behind a login and was not opened; its treatment of an interval that includes zero was read as described in the manual of the R package meta, which cites it.

## Difference in means: Welch's interval

    se = sqrt(s1^2/n1 + s2^2/n2)
    df = (s1^2/n1 + s2^2/n2)^2 / ((s1^2/n1)^2/(n1-1) + (s2^2/n2)^2/(n2-1))
    limits = (m1 - m2) -/+ t(df) * se

Source for the formulas: NIST/SEMATECH e-Handbook of Statistical Methods, section 1.3.5.3. Student's t quantiles are computed from the regularised incomplete beta function by continued fraction.

Checked: the t quantiles against the NIST table (section 1.3.6.7.2) for ten values of the degrees of freedom, and, for fractional degrees of freedom, against a separate numerical integration of the t density. The interval by hand for a small example. The pooled standard deviation and the equal-variance statistic against the NIST worked example (6.34260 and -12.62059). NIST's page prints no unequal-variance result for that example, so the Welch standard error and degrees of freedom for it are hand-worked only.

## Standardised difference: Cohen's d

    pooled SD = sqrt(((n1-1)*s1^2 + (n2-1)*s2^2) / (n1 + n2 - 2))
    d = (m1 - m2) / pooled SD

Source: Cohen J (1988), Statistical Power Analysis for the Behavioral Sciences.

Checked: by hand; the pooled SD against the NIST example above. d is a convention. The script attaches no size label to it.

## Percentage consistency

A reported percentage with q decimal places is consistent with k of n when

    | 100k/n - reported | <= 0.5 * 10^(-q)

computed in exact fractions. A tie passes. This is the idea behind the GRIM test for means (Brown and Heathers 2017), applied to percentages. The rule itself is arithmetic and needs no source.

## A mean against its sample size (`check-mean`)

When every response is a whole number (a count, an answer on a numbered scale), n responses have a whole-number total T, so the mean is T/n. A scale averaged over L items has n x L responses. A reported mean with q decimal places is possible when some whole T satisfies

    | T / (n x L) - reported | <= 0.5 * 10^(-q)

computed in exact fractions; a tie passes. When n x L is at least 10^q every printed value is possible, the test can say nothing, and the script reports CANNOT CHECK and exits 3.

Source: Brown NJL and Heathers JAJ (2017), "The GRIM Test", Social Psychological and Personality Science 8(4):363-369 (journal details confirmed from the Crossref record on 2026-10-09).

Checked: against the two worked examples in the authors' preprint (PeerJ Preprints 2064, read 2026-10-09). A mean of 5.19 from 28 people is impossible, because 145/28 rounds to 5.18 and 146/28 to 5.21 (preprint page 4). A mean of 6.28 from 52 people is impossible, because 327/52 is 6.29 (page 9). The limit of fewer than 100 for two decimal places, and multiplying by the number of items, are on pages 5 to 6 and 10 to 11. Also by hand for five further cases written out in `scripts/test_effect.py`. The preprint's own procedure rounds the product once and compares; the script instead asks whether any whole total gives the printed value, which reaches the same verdict and also handles ties.

What it cannot do: it applies only to whole-number data. A mean of measurements, or of items scored in halves, is not covered. A mismatch has ordinary causes: fewer people answered that item than the table's n, the figure was cut short, or it is a misprint. The output lists nearby sample sizes that would fit.

## A p value against its test statistic (`check-p`)

    z                 two-sided p = erfc(|z| / sqrt 2)
    t, d degrees      two-sided p = I_x(d/2, 1/2),  x = d / (d + t^2)
    chi-square, d     p = Q(d/2, x/2)                        (upper tail)
    F, d1 and d2      p = I_x(d2/2, d1/2),  x = d2 / (d2 + d1 F)   (upper tail)

I is the regularised incomplete beta function and Q the regularised upper incomplete gamma function, each computed by series or continued fraction. The statistic is taken as printed: 2.13 could have been anything from 2.125 to 2.135, so the p value is a small range. The reported p is compared at the precision printed: "p = 0.04" covers 0.035 to 0.045. The two are consistent when those ranges meet. "p < x" is consistent when the lowest p in the range is below x. For t and z the script also says whether a one-sided test would match.

Source for the approach: Nuijten MB, Hartgerink CHJ, van Assen MALM, Epskamp S and Wicherts JM (2016), "The prevalence of statistical reporting errors in psychology (1985-2013)", Behavior Research Methods 48(4):1205-1226 (Crossref record confirmed 2026-10-09). The statcheck manual by the first author, read the same day, describes recomputing p from the statistic and degrees of freedom, allowing for rounding of the statistic ("a reported t value of 2.35 could correspond to an actual value of 2.345 to 2.354"), treating one-sided tests, and treating "p <" differently from "p =". This script was written from that description. It is not statcheck, was not compared with statcheck's output, and makes no claim to agree with it case by case.

Checked: each distribution against closed forms that can be worked by hand, written out in the tests. With 1 degree of freedom the t tail is 1 - (2/pi) atan(t); with 2 it is 1 - t/sqrt(2 + t^2). The chi-square tail is exp(-x/2) with 2 degrees of freedom, exp(-x/2)(1 + x/2) with 4, and erfc(sqrt(x/2)) with 1. F with 2 and d degrees is (1 + 2F/d)^(-d/2), and F with 1 and d is the square of t with d. Table values (t = 12.7062 with 1, 4.3027 with 2, 2.0484 with 28; chi-square 5.9915, 9.4877, 3.8415) each give 0.05. A reviewing session also compared the four functions with SciPy 1.18 on 20,000 random cases, with degrees of freedom up to a million: the largest absolute difference was 4e-9. SciPy is not shipped and is not needed.

What it cannot do: tell whether the right test was used, whether the degrees of freedom are right, or whether a correction (for several comparisons, for unequal variances, for sphericity) explains the printed value. Without degrees of freedom a t, chi-square or F statistic has no p value: CANNOT CHECK, exit 3.

## A p value against a two-by-two table (`two-by-two --reported-p`)

    chi-square = N (ad - bc)^2 / (row1 x row2 x col1 x col2),  1 degree of freedom
    with the continuity correction: (|ad - bc| - N/2)^2 in place of (ad - bc)^2, not below zero

The reported p is consistent if either version gives it at the precision printed. Counts are exact, so no allowance for rounding of the statistic is needed. If a row or a column of the table is empty the statistic is undefined: CANNOT CHECK, exit 3.

Sources: the standard formulas (Pearson's chi-square; the continuity correction is Yates's). No page was retrieved for them; they are textbook arithmetic and are checked by hand.

Checked: by hand for 10 of 20 against 5 of 20 (2.666667, p = 0.102470; corrected 1.706667, p = 0.191418) and for 24 of 816 against 53 of 1,080 (4.61209, p = 0.03175), written out in the tests. A reviewing session found the same four values and the two for 31 of 816 against 44 of 1,080 with SciPy's `chi2_contingency`.

What it cannot do: Fisher's exact test, or a p value from a fitted or adjusted model. A mismatch names these as possible explanations.

## Citations not retrieved

Wilson (1927), Woolf (1955) and Cohen (1988) are cited from memory as the usual attributions. Their pages were not opened, so no page numbers are given for them. Brown and Heathers (2017) and Nuijten and others (2016) were confirmed against their Crossref records on 2026-10-09; the first was read as its preprint and the second through the statcheck manual, and neither journal article was opened. Every other reference above was read, directly or through the secondary source named beside it.

## What none of these can do

They describe sampling variation in the counts given. They do not adjust for confounding, for loss to follow-up, for many outcomes being tested, or for clustering. For two systems scored on the same items they ignore pairing. Where any of those applies, say so beside the number.

## What a mismatch is, and is not

`check-percent`, `check-mean`, `check-p`, `two-by-two --reported-p`, `attrition` and the extraction check each compare one of the document's figures with another. A mismatch means the two cannot both be right as printed. It has ordinary causes: a misprint, a different denominator, a one-sided test, a correction nobody mentioned, a number copied wrongly into the extraction. Each output says what would settle it. None of these checks can show why two figures disagree, and the audit never says or implies that a document is fraudulent, fabricated or dishonest. It reports the discrepancy, where it is, and what would resolve it.

A check that could not be made (CANNOT CHECK, or INCOMPLETE from the extraction check) is reported as a GAP. It is never written up as a pass.
