---
name: "evidence-synthesis"
description: "Runs a systematic review and, where justified, a meta-analysis: frozen protocol, logged search, screening with reasons, extraction traced to page and table, risk of bias, random-effects pooling with heterogeneity and a prediction interval, small-study checks and a certainty rating per outcome. Use when asked for a systematic review, a meta-analysis or what the body of evidence says. Not for one study (paper-audit) or a narrative brief (deep-research-orchestrator)."
---

# Evidence synthesis

Answers "what does the whole body of evidence say" with a method another reviewer could repeat: a protocol frozen and registered before searching, every exclusion logged with a reason, every number traced to its page and table, a pooled estimate only where pooling means something, and a certainty rating that says how far to trust it.

## Use when

- The question has been studied several times and the user wants the combined answer.
- The user says: systematic review, meta-analysis, pool these studies, forest plot, what does the evidence say overall, is the effect consistent across studies.
- research-agency needs prior quantitative evidence combined, not just listed.

## Not this skill

| The job | Use |
|---|---|
| Judge one study | paper-audit |
| A narrative brief or market scan | deep-research-orchestrator |
| Collect the source pages | harvest |
| Run a new study | research-agency |
| Hostile review of the finished synthesis | referee-panel |

## Tools: discover first

Check for web search and fetch, code execution, separate agents, and an established meta-analysis library (for example R's metafor, or the meta-analysis module in Python's statsmodels). Use a library when present, name the estimator it used, and cross-check the pooled estimate and between-study variance against the formulas below. Without code, compute by hand and show every step.

## Procedure

1. **Freeze and register the protocol before searching** (PROSPERO, OSF or an internal timestamped record). Population, intervention or exposure, comparator, outcomes (primary first, with time point), eligible designs, setting, date range, languages, the effect measure, the pooling model, planned subgroups and sensitivity analyses. Record a timestamp or hash. Later changes are listed as deviations.
2. **Search and log it.** For each source (bibliographic databases, trial and study registries, preprint servers, reference lists, forward citation chasing), record the exact query, date run and hits. Search registries and grey literature deliberately, because published studies lean positive. List sources that could not be searched, such as paywalled databases.
3. **Screen.** Remove duplicates. Screen titles and abstracts, then full texts, against the frozen criteria. Log every full-text exclusion with its reason. Where separate agents exist, two screeners independently assess every full text against the criteria, a third resolves disagreements, and agreement is reported (Cohen's kappa); screeners that are copies of the same model are labelled as such. Link multiple reports of one study so each study, and each participant, counts once.
4. **Extract.** Per study: design, population, numbers per arm, outcome definitions and time points, the effect estimate or the counts, means and standard deviations needed to compute one, funding and conflicts. Record the page or table for every number. Double-extract the primary outcome where possible. Every imputation (for example a standard deviation derived from a confidence interval) is recorded with its formula and assumption.
5. **Rate risk of bias** per study and outcome with an established tool for the design (RoB 2 for randomised trials, ROBINS-I or ROBINS-E for non-randomised studies, QUADAS-2 for diagnostic accuracy, or the field's equivalent), giving a judgement and reason per domain.
6. **Put effects on one scale.** Ratio measures on the log scale; continuous outcomes as a mean difference when all studies use one scale, otherwise Hedges' g, aligning direction across scales and never mixing change-score and final-value standard deviations in one standardised mean difference. Handle unit-of-analysis problems: adjust cluster trials for the design effect, split or combine shared arms in multi-arm trials, never treat several outcomes from one study as independent. For rare events, do not apply a blanket 0.5 continuity correction; use a method suited to sparse data and show the sensitivity.
7. **Decide whether to pool.** Pool only when populations, interventions, comparators and outcomes are alike enough that one average means something. Otherwise give a structured narrative synthesis: group studies, summarise direction and size of effect, and never count studies by statistical significance.
8. **Pool with random effects by default.** Prefer REML or Paule-Mandel for the between-study variance; DerSimonian-Laird underestimates it when studies are few. Use the Hartung-Knapp-Sidik-Jonkman interval, especially with fewer than about ten studies; when its scaling factor q is below 1, also report the interval with q set to 1. Report the pooled estimate with its 95% interval, tau-squared and tau, I-squared, Q with its degrees of freedom, and the 95% prediction interval. Back-transform ratio measures for presentation. A common-effect model is a sensitivity analysis unless justified.
9. **Explore heterogeneity only as planned.** Prespecified subgroups or meta-regression, roughly ten studies per covariate, reported as exploratory, with the ecological-fallacy caveat.
10. **Check small-study effects.** A funnel plot and a regression test only with ten or more studies: Egger's for mean differences, Peters' or Harbord's for odds ratios (Egger's gives false positives there), and a sample-size-based variant for standardised mean differences. Asymmetry is not proof of publication bias; heterogeneity, chance and artefact also cause it. Trim-and-fill and selection models are sensitivity analyses, not corrections. Compare registered with published studies where possible.
11. **Sensitivity analyses.** Leave-one-out; exclude high risk-of-bias studies; an alternative variance estimator; common-effect against random-effects; alternative imputations and effect measures.
12. **Rate certainty per outcome with GRADE.** Randomised evidence starts high; non-randomised evidence starts low (or high when rated with ROBINS-I). Downgrade for risk of bias, inconsistency, indirectness, imprecision and publication bias. Upgrade, normally only non-randomised evidence not already downgraded, for a large effect, a dose-response gradient, or when all plausible residual confounding would reduce the observed effect. Result: high, moderate, low or very low, each change explained.
13. **Report to PRISMA 2020**: flow counts (identified, deduplicated, screened, excluded, full texts assessed with reasons, included), study table, risk-of-bias table, forest plot, and a summary-of-findings table giving absolute effects (for example per 1,000 people) where a baseline risk is known.

## Formulas

Study i has effect y_i with variance v_i; k studies.

- Log odds ratio from a 2x2 table (a, b events and non-events in arm 1; c, d in arm 2): y = ln(ad / bc), v = 1/a + 1/b + 1/c + 1/d.
- Log risk ratio: y = ln[(a/(a+b)) / (c/(c+d))], v = 1/a - 1/(a+b) + 1/c - 1/(c+d).
- Hedges' g: pooled SD s = sqrt[((n1-1)s1^2 + (n2-1)s2^2) / (n1+n2-2)]; d = (m1-m2)/s; J = 1 - 3/(4(n1+n2) - 9); g = J d; v = J^2 [ (n1+n2)/(n1 n2) + d^2 / (2(n1+n2)) ].
- Common-effect weights w_i = 1/v_i; weighted mean y_w = sum(w_i y_i) / sum(w_i); Q = sum w_i (y_i - y_w)^2.
- DerSimonian-Laird: tau^2 = max(0, (Q - (k-1)) / (sum w_i - sum w_i^2 / sum w_i)).
- Paule-Mandel: tau^2 = 0 if Q <= k - 1; otherwise solve sum w*_i (y_i - mu(tau^2))^2 = k - 1, with w*_i and mu as defined below.
- Random-effects weights w*_i = 1/(v_i + tau^2); mu = sum(w*_i y_i) / sum(w*_i); SE(mu) = sqrt(1 / sum w*_i).
- I^2 = max(0, (Q - (k-1)) / Q), as a percentage.
- Hartung-Knapp-Sidik-Jonkman: q = sum w*_i (y_i - mu)^2 / (k-1); SE_HK = sqrt(q / sum w*_i); interval mu +/- t(k-1, 0.975) SE_HK.
- Prediction interval (k >= 3): mu +/- t(k-2, 0.975) sqrt(tau^2 + SE(mu)^2).

With fewer than five studies, tau-squared is very imprecise and the report says so. With two studies there is no prediction interval.

## Rules that always hold

- The protocol is frozen and registered before searching; deviations are listed.
- One study counts once, and so does each participant.
- Every number is traced to its page or table; every imputation is recorded.
- Never invent a study, a result or a search hit. Zero eligible studies is a finding.
- Never pool what does not belong together, and never count studies by significance.
- The prediction interval and the certainty rating are reported beside the pooled estimate.
- Compute in code where possible, seeded and with versions stated.
- Load-bearing claims are tagged FACT, REPORTED, ASSESSMENT, MODEL_OUTPUT or GAP.
- Writing: the answer and its certainty first, Australian spelling, no long dashes.

## Host strengths, used when present

- Web search and fetch: logged searches with dates, registry checks, full texts.
- Separate agents: independent dual screening and extraction, with agreement reported.
- Code execution: effect sizes, pooling, forest and funnel plots, all reproducible.
- An installed meta-analysis library: the primary computation, cross-checked by the formulas.
- None of these: hand computation shown step by step, labelled single-reviewer.

## Output

First line, one of:
- "Evidence synthesis: k studies, N participants; pooled [measure] X (95% CI a to b), prediction interval c to d; certainty: [level]."
- "Evidence synthesis: k studies; not pooled because [reason]; narrative result: [one sentence]; certainty: [level]."

Then: PRISMA flow counts, study and risk-of-bias tables, the forest plot, heterogeneity and sensitivity results, small-study checks (or why they were not run), the summary-of-findings table, protocol deviations, and the search log.

## Routing checks

Should trigger: "do a meta-analysis of these 12 trials"; "systematic review of whether X reduces Y"; "what does the overall evidence say on Z, pooled".
Should not trigger: "is this one trial any good" (paper-audit); "give me an overview of research on X" (deep-research-orchestrator); "run an experiment on X" (research-agency).

## What has and has not been tested

Written by Claude on 22 October 2026 to fill a gap found in an audit of the installed research skills: none performed systematic review or meta-analysis, and paper-audit names meta-analysis as outside its competence. Formulas follow standard references (Borenstein and colleagues' introduction to meta-analysis; the Cochrane Handbook). Checked on 22 October 2026: on the 13 BCG vaccine trials (log risk ratio), the hand formulas reproduced metafor's published DerSimonian-Laird results to four decimals (Q 152.2330, I-squared 92.12%, tau-squared 0.3088, pooled -0.7141, SE 0.1787), and matched statsmodels 0.15 for Paule-Mandel (tau-squared 0.3181) and the Hartung-Knapp-Sidik-Jonkman interval (-1.1078 to -0.3204). Hedges' g matched a textbook worked example (g 0.5924, variance 0.0411). An independent reviewer checked the methods and its fixes are applied. Not yet tested: the prediction interval against a library, routing, and a full run on a real review.