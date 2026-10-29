---
name: paper-audit
description: "Reads one study, report or benchmark claim critically: what was measured, on whom, the effect in absolute terms recomputed from its numbers, and what the design cannot show. Use for is this study any good, audit this paper, does this research actually show, check the stats in this report, is this benchmark claim sound. Not for checking a draft against sources (fact-check), a multi-source campaign (deep-research-orchestrator), raw data (data-intelligence) or survey responses (response-analyst)."
metadata:
  revision: "1.0.0"
---

# Paper audit: read one study critically and recompute its numbers

Research often rests on one study, one report or one quoted statistic. This skill reads that one document the way a careful reviewer would: find the claim and the result under it, state what the design can show at most, pull the numbers out with their locations, recompute them, and say plainly what the document shows, how strongly, and what it does not show.

The work is recomputation. `scripts/effect.py` turns a study's own counts into absolute and relative differences with intervals, and checks a printed percentage, mean or p value against the numbers beside it; `scripts/extraction_check.py` checks the extracted numbers against each other. The reading and the judgement are the model's. A skill is instructions plus tools and adds no expertise the model does not have.

## Use when

- One study, report, benchmark or statistic carries weight in something the user is deciding or writing, and the question is whether it holds up.
- A summary claims an effect ("a 40 percent reduction", "outperforms", "doubles the risk") and the user wants to know what the result underneath is.
- A vendor or press claim about an AI system or software benchmark needs reading before it is repeated.

## Not this skill

| The job | Use |
|---|---|
| Check the claims in a draft against their sources | fact-check |
| Find, compare and record many sources on a topic | deep-research-orchestrator |
| Analyse a raw data file | data-intelligence |
| Analyse survey or questionnaire responses | response-analyst |
| Weigh competing explanations of what happened | intelligence-analyst |
| Forecast or decide on the strength of the finding | oracle |
| Estimate a quantity from rough inputs | fermi |

## Inputs

- The document, in full if at all possible: the paper, the report, the vendor note. Say at once if only an abstract, a press release, a slide or a chart is available.
- The claim the user cares about, if they have one in mind. Otherwise audit the headline claim.

Start without asking. Ask only if there is no document to read.

## Tools: discover first

- **A shell with Python 3**, for `scripts/effect.py` and `scripts/extraction_check.py`. Without one, do the arithmetic by hand from the formulas in `references/methods.md`, show the working, and say it was done by hand and not checked by the script.
- **File reading**, for a PDF or a page. If the document cannot be opened, ask for the text. Never audit a paper from memory of it.
- **Search or page reading**, to look for a registration record, a protocol or a replication. Without it, record registration and replication as not checked. Do not guess.

## Procedure

1. **Say what the material is**: full text, abstract only, press release, blog post with a chart. This sets how much can be audited.
2. **Find the claim and the result that supports it.** The claim is in the summary; the result is in the tables. They often differ. Quote both, each with a locator (section, table and row, page).
3. **Classify the design and state its ceiling first.** Randomised trial, comparison of groups not formed by chance, cohort, case-control, cross-sectional survey, before and after, modelling, benchmark comparison, qualitative study, vendor report. `references/designs.md` gives what each can show at most, its usual weaknesses and the questions that matter for it.
4. **Extract the numbers** into a copy of `assets/extraction-template.json`: the groups with their sizes at the start and at analysis, each outcome's definition and whether it was the registered primary one, counts or means with spread, the time frame. Every number carries a locator. Anything the document does not give is written `not_reported`.
5. **Check the extraction:** `python scripts/extraction_check.py EXTRACTION.json`. An ERROR is a mistake in the file: go back to the document. A FINDING means a percentage disagrees with its own counts: recheck the copy, and if it was copied correctly, report it. INCOMPLETE (exit 3) is the ordinary result when the document leaves numbers out: each CANNOT CHECK line is a comparison that could not be made, and goes into the verdict as a GAP, never as a pass. The check lists everything marked not reported and prints the commands for the next step.
6. **Recompute** with `scripts/effect.py`:
   - `two-by-two` for two groups and an event: the absolute difference with its interval, the relative difference, both stated together, and the number needed to treat or harm.
   - `proportion` for one group, `means` for a continuous outcome.
   - `attrition` for loss overall and by group, and whether it is balanced.
   - `check-percent` for any percentage against its counts.
   - `check-mean` for a mean of whole-number data (a count, an answer on a numbered scale) against its sample size: some printed means cannot arise from the n beside them.
   - `check-p` for a printed p value against its test statistic and degrees of freedom, and `two-by-two --reported-p` for a p value against the counts in a two-by-two table.
   - A check that prints CANNOT CHECK (exit 3) has not passed. Record what was missing as a GAP.
   - `relative-to-absolute` when the document gives only a ratio and a baseline can be found. "50 percent more" from 2 in 1,000 is 1 extra per 1,000.
7. **If loss is large or unbalanced**, rerun `two-by-two` under one stated assumption about the people lost, with everyone who started in the denominators. Label it a scenario and an ASSESSMENT. It shows whether the conclusion depends on people the document does not describe; it is not an estimate.
8. **Ask the questions that change the reading**, and answer only those that apply, each with the locator of the evidence:
   - Who was sampled, and who is missing?
   - Was the comparison fair: allocation, confounders, differences at the start?
   - Was the outcome chosen in advance, or is it one of many?
   - How many dropped out, and was it balanced?
   - Is the measure the thing the claim is about, or a stand-in: a surrogate, a self-report, a benchmark score?
   - Is the effect big enough to matter, whatever its p-value?
   - Who funded it and who wrote it, and does that bear on the design choices?
   - Has anyone repeated it?
9. **For an AI or software benchmark claim**, work through `references/benchmarks.md`: what exactly was run, on what data, with what prompts and settings, how many runs and how much they vary, whether the test set could have been seen in training, whether the comparison systems were tuned as carefully, and whether the metric reflects the task. State what the number of test items allows.
10. **Write the verdict in the fixed form** (see Output). Tag each load-bearing statement FACT (in the document, with locator), ASSESSMENT (inference, with confidence) or GAP (not reported).
11. **List what is not reported** as not reported. Never assume it fine and never assume it bad.

## Failure branches

- **Only an abstract or a press release.** Say so in the first lines. The audit is of the abstract's claims, nearly everything is GAP, and the full text is asked for. Recompute only what the abstract's own numbers allow.
- **A blog post with a chart, or a slide.** Treat it as a claim with an unknown method. Say what would be needed to audit it: the source data, the sample, how it was measured.
- **A quick question about one statistic.** Answer it directly in a few lines. Recompute if the numbers are there. No extraction file and no full verdict.
- **Many papers to compare.** That is a research campaign: deep-research-orchestrator. Offer this skill for the two or three that carry the weight.
- **A specialised method outside competence** (for example a network meta-analysis, a genetic instrument, an econometric identification strategy). Say which part cannot be assessed, audit the rest, and say what kind of reader could check that part.
- **No counts, only percentages or ratios.** Compute what can be computed. If no baseline is given, the absolute effect is a GAP: say so and say what number would settle it. Do not supply a baseline from memory.
- **No shell.** Work by hand from `references/methods.md`, show the arithmetic, and say it was not machine-checked.
- **The finding bears on a health, legal or money decision.** The audit says what the document shows. It is not advice; say what a qualified person would need to confirm.
- **Named authors.** The audit is of the document. No speculation about motives. Funding and affiliation are reported as facts with their locator, and any link to design choices is marked ASSESSMENT.
- **Two of the document's own figures disagree.** Report it as a discrepancy: what was printed, what the other figure gives, where each is, and what would settle it (the denominator used, the test named, the per-person data, a question to the authors). Check the extraction first. Never call a document fraudulent, fabricated or dishonest, and never hint at it: the checks cannot show why two figures disagree, and the ordinary causes are a misprint, a different denominator or a detail left out.
- **The user asks whether the paper is fraudulent.** Say what the audit can show: which figures are inconsistent and what would resolve each. Say that no reading of one document can establish misconduct, and that this is a question for the journal or the authors' institution.
- **This skill's own ways of going wrong.** Copying a number wrongly, which no script can detect. Running `check-mean` on data that are not whole numbers. Reading CONSISTENT as "correct" when it means only "possible". Reading an interval as covering bias when it covers sampling only. Treating a clean extraction check as a verdict on the study. Inventing a grade. Treating "not reported" as "bad". Running an unpaired comparison on paired benchmark results without saying so.

## Output

The first line names the method: "Paper audit: design ceiling stated, numbers recomputed from the document's own counts, verdict in the fixed form." If the arithmetic was done by hand, the first line says so.

Then, in about a page:

1. **Bottom line.** Two or three sentences: does the document support the claim, and what is the effect in absolute terms.
2. **The claim and the result it rests on**, quoted, with locators.
3. **Design and its ceiling.**
4. **The numbers, recomputed**: a table of what the document says, what recomputation gives, and where each came from. Counts beside every percentage.
5. **Findings**, numbered, each tagged FACT, ASSESSMENT or GAP.
6. **Verdict**, always these five parts:
   - *What it shows*, scoped to the sample and the design.
   - *How strongly*, in words tied to design, size and consistency (the wording table is in `references/designs.md`). Not a grade and not a score.
   - *What it does not show.*
   - *What would change the reading.*
   - *The single most useful follow-up.*
7. **Not reported.**

## Rules that always hold

- A relative figure never appears without the absolute one beside it.
- Every percentage has its counts; every extracted number has a locator.
- The design's ceiling is stated before the findings, and the verdict never goes beyond it.
- Not reported is listed as not reported.
- "How strongly" is words tied to design, size and consistency. No invented grade, score or probability that the study is right.
- An interval covers sampling variation in the counts given, and the text says so where bias or loss is the larger worry.
- An inconsistency is reported as a discrepancy with what would resolve it. The audit never calls a document or its authors fraudulent.
- A check that could not be made is a GAP. It is never reported as consistent.
- Numbers come from the document in hand. Nothing is recomputed from memory of a paper.
- The audit is of the document, not of its authors.

## What has and has not been tested

Everything below was run by the session that wrote this skill or by a second session that reviewed and repaired it on 2026-10-09. Both are author-side. Nobody independent has run any of it. The numbers are from the review's reruns.

- `scripts/test_effect.py`: 35 tests, 35 passed. Every calculation is checked against hand-worked values written out in the test, and where one was found, against a published worked example that was retrieved and read: Newcombe's difference interval (four examples), the risk ratio (the SciPy documentation, citing Katz), the odds ratio (Bland and Altman, BMJ 2000), Student's t quantiles and the pooled standard deviation (NIST handbook), and the two worked examples of the GRIM test (Brown and Heathers, preprint). `references/methods.md` says for each method how far it was checked and which citations are from memory.
- The same suite with `--planted`: 36 broken copies, one planted fault each, including a copy that reports the relative risk without the absolute difference, a copy that computes the number needed to treat from the relative risk, and copies that report a pass when a check could not be made. All 47 fault checks were caught by the named tests.
- Added in review, each with hand-worked tests and planted faults: `check-mean`, `check-p`, `two-by-two --reported-p`, the CANNOT CHECK result (exit 3) in place of a silent skip, the INCOMPLETE result of the extraction check, a note on every finding saying what would settle it, and a design entry for groups not formed by chance.
- The review's own hand-computed cases, not shipped: 84 checks, each consistency check with a case that must match, a case that must not, and a case with an input missing. All passed, and six altered copies of the scripts each failed at least one. The four distribution functions behind `check-p` agreed with SciPy on 20,000 random cases to within 4e-9.
- A scratch fuzz in review, not shipped: 60,000 random command lines to `effect.py` over three seeds, called in-process, with no traceback, no exit code other than 0, 1, 2 or 3, and no NaN or infinity in any output. The authoring session reported an earlier fuzz of 100,000 command lines and mutated extraction files, which found three crashes on absurd inputs that are now refused and tested; that run was not repeated in review.
- Two complete audits of synthetic documents, a trial and a vendor benchmark note, each with its extraction file, script outputs and verdict. They travel with the source for review and were regenerated in review. A third synthetic document, written in review with a wrong p value, an impossible mean and a slipped denominator planted in it, was audited by following this procedure; all three were found and the consistent figures passed.

Not tested: any real paper. Whether a model following this procedure extracts numbers correctly from a long PDF. Paired analysis of benchmark results, which the script does not do. Fisher's exact test and p values from fitted models, which `two-by-two --reported-p` does not compute. Agreement with the statcheck package, which was not installed or run. Any model following this skill other than the session that wrote it; any real host's preview.

## Acceptance cases

The full set, with inputs, travels with the source for review.

1. A trial report whose abstract claims a "40 percent reduction". Expect: the absolute difference recomputed from the table's counts and stated beside the 40 percent; loss by group computed and called unbalanced; the change of primary outcome found in the methods and both outcomes reported; a verdict in the five parts; a list of what is not reported.
2. A vendor note claiming a model "outperforms" on 50 test items from a single run. Expect: the interval for each score and for the difference, the statement that the difference interval includes zero, the unequal prompts and the missing contamination check named, and no ranking of the systems.
3. Only an abstract is supplied. Expect: said in the first lines; the claims audited as claims; nearly everything listed as GAP; the full text asked for; no baseline invented.
4. Negative control: "A headline says a medicine doubles a risk from 1 in 10,000 to 2 in 10,000. Should I worry?" Expect: a direct answer in a few lines (1 extra per 10,000), with no extraction file and no full verdict.
