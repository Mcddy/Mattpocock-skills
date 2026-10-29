---
name: oracle
description: "Looks forward and decides: resolvable forecasts and scenario sets with a stated basis for every likelihood, risk registers, organisation due diligence from public records, decisions with a break-even test, and adversarial stress tests of a plan or thesis. Use for forecast this, what are the scenarios, what are the risks, help me decide, stress test this, due diligence on a company. Not for gathering sources (deep-research-orchestrator) or explaining what already happened (intelligence-analyst)."
metadata:
  revision: "2.0.1"
  revised-from: "oracle as exported 8 Oct 2026"
---

# Oracle: forecast, assess risk, decide, attack the plan

Five jobs that share one discipline: say what you expect, say why, say how you would know you were wrong, and commit.

| Job | When | Reference |
|---|---|---|
| Forecast or scenarios | "What will happen", "what are the scenarios", "how likely" | `references/forecasting.md` |
| Risk register | "What are the risks", "what could go wrong with" | `references/risk-and-diligence.md` |
| Organisation due diligence | "Check out this company, supplier, platform" | `references/risk-and-diligence.md` |
| Decision | "Help me decide", "should I" | `references/decisions.md` |
| Stress test | "Attack this", "what am I missing", "steelman the other side" | `references/decisions.md` |

The earlier version of this skill also contained a research protocol, an analysis module and a knowledge store. Those jobs now belong to deep-research-orchestrator, intelligence-analyst, and mnemosyne with calibrate. This skill names them as the next step when they are needed and available; it does not redo them.

## Use when

- A judgement about the future is needed, with its likelihood and tripwires.
- A choice has to be made under uncertainty and the user wants a recommendation, not a list.
- A plan, thesis or position needs someone to try to break it.
- An organisation needs checking against the public record before dealing with it.

## Not this skill

| The job | Use |
|---|---|
| Find and record sources on a topic | deep-research-orchestrator |
| Explain what happened or which story fits the evidence | intelligence-analyst |
| Score a multi-domain plan on five axes | gladiator |
| An interactive comparison of a few options | decision-board |
| Log a prediction and score it later | calibrate |
| Record a durable fact or decision | mnemosyne |

## Inputs

- The question or the decision, with its time frame.
- What the user already knows or has gathered. If nothing has been gathered and the answer depends on current facts, research comes first.
- For a decision: the options, what matters, what cannot be undone, and what loss would be unacceptable.

## Tools: discover first

- Search and page reading, for base rates, current facts and public records. Without them, say that every present-tense input is unverified.
- A shell with Python 3 for `scripts/scenario_check.py`. Without one, apply its rules by hand and say so.
- calibrate, if present, to log a forecast for later scoring. mnemosyne, if present, to record a decision. Name them as next steps only if they are actually available.

## Procedure

### Any job: start here

1. **Say which job this is** and what the output will be.
2. **Separate** what is established (with source), what is inferred, and what is unknown. Present-tense facts are looked up, not recalled.
3. **Name the ceiling**: can this be forecast at all, or only bounded? Some questions have no reference class and no mechanism you can model. Then the honest product is the range of credible outcomes and what each depends on.

### Forecast or scenarios

1. Turn the question into one that can be **resolved**: a date, and the observation that settles it.
2. **Outside view first.** Find a reference class and its base rate before looking at the specifics. If none can be found, say so; that lowers confidence and widens the range.
3. Split into sub-questions where that helps, and adjust from the base rate for the specifics, saying which way and why.
4. Build scenarios that are distinct in **cause**, not just in size. Each needs: what drives it, an early indicator, and what would falsify it. Include the one where the question's own framing is wrong.
5. Give each scenario a likelihood **only with its own basis**: a count from the reference class, a market-implied figure, a model with stated inputs. Otherwise use a word from the scale, or say there is no basis for one. There are no default percentages. A base, upside and downside split that was typed in before the analysis is a guess wearing a number.
6. Run `python scripts/scenario_check.py forecast.json`. It checks that the forecast can be resolved, that each likelihood has its own basis, and that the set is arithmetically possible.
7. State the forecast, the confidence in its own sentence, and the review trigger. Offer to log it with calibrate.

### Risk register

1. List what could go wrong by walking the thing end to end: dependencies, single points of failure, people, money, data, outside parties, timing.
2. For each: the mechanism, the consequence, what already limits it, the gap, and the early sign.
3. Rank by **consequence first**, then likelihood in words. Do not multiply two rough ratings into a score; the product hides which risks are unsurvivable.
4. Mark anything you could not assess as unknown. Unknown is never low.
5. For the top few: a specific mitigation, who does it, and what is left over afterwards.

### Organisation due diligence

Scope: organisations, and people only in their public role as an officer or spokesperson of one. Public records and published material only. See `references/risk-and-diligence.md` for the phases and source types. Every finding is sourced, dated and tagged, and gaps are listed. This is not a background check on an individual, and it does not locate people or gather personal details.

### Decision

1. Classify: how much is at stake, and can it be undone? That sets the depth. Reversible and small: decide quickly and move. Irreversible or large: do all of the following.
2. State the options, including doing nothing and the one nobody has proposed.
3. Say what would make each option the right one.
4. **Ruin first.** If an option has an outcome the user could not recover from, that is decided before any weighing.
5. Weigh. Where gain and loss can be put in the same unit, compute the **break-even probability** rather than inventing the odds. First settle what the two figures mean, because the same pair gives different answers:
   - **Net outcomes**: U ahead if it works, D behind if it does not. The option pays only if the chance of success exceeds D / (U + D).
   - **A cost paid either way**: C is spent whatever happens, and success brings in G before the cost, or avoids a loss of G. The option pays only if the chance exceeds C / G.

   "Spend 4k to avoid a 12k loss" is the second kind: the 4k is gone either way, so break-even is one third, not one quarter. Say which reading was used. If the wording does not settle it, give both figures and what each assumes; do not pick one silently. Then ask whether the real chance is plausibly above the figure, and on what evidence. `scripts/scenario_check.py` does this arithmetic for a forecast file that carries a `decision` block, and refuses a block that does not name its convention; for a bare decision the arithmetic is one division, shown in the reply. With three or more outcomes the two-outcome formula does not apply: write the complete payoff and probability table or stay qualitative, as `references/decisions.md` section 4 sets out.
6. Run a pre-mortem: it is a year on and this failed; what happened? Then the reverse: it went better than hoped; why?
7. **Commit.** One recommendation, the assumption that would reverse it, the tripwire that should trigger a rethink, and the first action. If the evidence cannot separate two options, say that, and recommend the cheaper to reverse.

### Stress test

1. Attack the strongest version of the plan, not a weak one.
2. List the most serious objections, each with the mechanism by which it would cause failure. Rate each fatal, serious, manageable or minor. For fatal and serious ones, give a fix or say there is none.
3. Steelman the opposing view: its best evidence, and why informed people hold it.
4. Audit the assumptions: stated or unstated, supported or not, and what follows if each fails.
5. Verdict: robust, needs work, seriously flawed or broken. Start with the problem. If it survives, say so plainly; do not manufacture an objection.

## Failure branches

- **No basis for a probability.** Use the scale's words or say none can be given, and say what data would provide one. Do not supply a number because the format has a slot for it.
- **The user wants a number anyway.** Give the range the word stands for, and the break-even figure if it is a decision. Say in one sentence that a single figure would be invented.
- **The question cannot be resolved as asked** ("will it go well?"). Rewrite it into one that can, and say what was changed.
- **Money, investment or trading.** Give the scenarios, what would invalidate the thesis, the break-even arithmetic and the risks. The position, its size and the decision are the user's. Say once that this is analysis and not financial advice, and do not produce entry, stop or target prices from nothing.
- **Legal, medical or safety stakes.** Give the analysis and say what a qualified professional would need to confirm.
- **The facts are missing.** Do the research first (deep-research-orchestrator if present), or mark the inputs unverified and carry that through to the confidence.
- **A person is the subject.** Public role only. No profiling of character, health, beliefs or private life, and no inference about them.
- **Everything looks fine.** Say so. A stress test that finds nothing fatal is a result.

## Output

Lead with the answer. Then:

- **Forecast**: the resolvable question, the forecast with likelihood, confidence in a separate sentence, the scenarios with basis, indicator and falsifier, the review trigger.
- **Risk register**: a table (risk, mechanism, consequence, likelihood in words, current control, gap, early sign), the top few with mitigations, what was not assessed.
- **Due diligence**: summary, findings each tagged with source and date, risk flags, gaps, what would improve it.
- **Decision**: recommendation, why, the assumption that would reverse it, the tripwire, the first action, what was not established.
- **Stress test**: verdict, ranked weaknesses with mechanism and fix, dangerous assumptions, the strongest opposing case, bottom line.

## Rules that always hold

- No likelihood without its own basis. No default percentages.
- Likelihood and confidence are stated in separate sentences.
- A forecast has a date and a way to resolve it, or it is not called a forecast.
- Unknown is never reported as low.
- Rough ratings are not multiplied into a score.
- A recommendation is committed to, with what would reverse it.
- Analysis about money is not advice; the decision is the user's.
- Nothing is inferred about a person's private life or character.

## What has and has not been tested

**Correction in revision 2.0.1.** An independent reviewer found two defects. `scenario_check.py` printed NaN as a successful break-even for two equal payoffs of 1e308. And the worked example read "spend 4k to save 12k" as net outcomes (25 percent) when the 4k is paid either way (one third). The script now requires a decision to name its payoff convention (`net` or `gross`), refuses one that does not, scales the figures before adding them so large values cannot overflow, reports any non-finite derived value as an error, and writes strict JSON. The decision procedure, `references/decisions.md` section 4 and the acceptance cases were corrected to match, and the two-outcome formula is no longer applied per scenario when there are three or more outcomes. The correction was author-tested on 9 Oct 2026: the paired case (net 25.0, gross 33.3 on the same two figures), a decision with no convention (refused), equal payoffs of 1e308 (50.0), four other extreme pairs, eight malformed decisions (each refused), 3,000 random pairs compared with exact fractions, and a copy with the old arithmetic put back, which prints NaN and fails the check. It has not been independently retested. The stored behaviour reply for case 3 was corrected by hand and is not a fresh model run.

Run in this package's build session: `scenario_check.py` on a well-formed forecast (passes; break-even computed as 25 percent for a net gain of 12,000 against a net loss of 4,000), on the earlier version's 55/25/20 split with one shared basis (fails: one basis cannot explain three likelihoods), on a malformed file (fourteen errors) and on two mutually exclusive outcomes both called likely or better (fails as incoherent).

Not tested: any model following this skill other than the session that wrote it; whether forecasts made with it are accurate, which only scoring over time can show; any due diligence run against live registers.

## Acceptance cases

Four of the cases in words. The full set, with negative controls and input files, travels with the source for review; `assets/forecast-example.json` is a well-formed forecast to copy from.

1. "Will the replacement part arrive by the end of January?" with ten past orders supplied. Expect: a resolvable question, a base rate from the ten orders, scenarios each with its own basis, an indicator and a falsifier, no default split, likelihood and confidence in separate sentences.
2. "Base case 55, upside 25, downside 20. Sound right?" with no data. Expect: the split is challenged as having no basis; words or "no basis" are offered instead; the question is asked what the numbers were derived from.
3. "Should I spend 4k now to maybe save 12k on a failure later?" Expect: ruin checked first; the 4k named as paid either way, so break-even is one third (4,000 / 12,000), not 25 percent; the question turned to whether the real chance is above that; a committed recommendation with what would reverse it. Its pair: "12k ahead if it comes off, 4k behind if not" is net outcomes, and break-even is 25 percent.
4. Negative control: "Why did our churn spike last month?" Expect: intelligence-analyst leads.
