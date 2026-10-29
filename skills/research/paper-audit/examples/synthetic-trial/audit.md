Paper audit: design ceiling stated, numbers recomputed from the paper's own counts, verdict in the fixed form.

Audit of a SYNTHETIC paper (`paper.md`, invented for this example). Author-run: the session that wrote the skill produced this by following its procedure. A second, reviewing session added the p value rows and finding 10 on 2026-10-09, after adding that check to the script. Script outputs are in `outputs/`.

## Bottom line

The paper does not support "reduces colds by 40 percent" as a reason to recommend the drink. Among the people analysed, 2.9% on the drink and 4.9% on usual diet recorded a symptomatic week: a difference of 2.0 percentage points. The outcome the trial registered as primary shows no clear difference, a third of the drink group was dropped from the analysis after stopping the drink, and the headline outcome was promoted to primary after follow-up had ended.

## The claim and the result it rests on

- Claim: "FOD-7 reduced colds by 40 percent (p = 0.03). [...] A daily fermented oat drink reduces colds in adults and can be recommended as a simple preventive measure." (Abstract, Results and Conclusion)
- Supporting result: a week with three or more days of cold symptoms, by diary: 24 of 816 (2.9%) against 53 of 1,080 (4.9%). (Table 2, row 1)

The claim speaks of "colds" in "adults". The result is a self-recorded symptom count among employees aged 18 to 45 who finished 12 weeks.

## Design and its ceiling

Randomised trial, two groups, no placebo, 12 weeks (Methods). At best a randomised trial shows that the intervention caused a difference in the people analysed. That ceiling holds only while the groups compared are the groups randomised. Here they are not: see finding 3.

## The numbers, recomputed

| Quantity | The paper says | Recomputed from its counts | Output |
|---|---|---|---|
| Headline outcome, drink | 24 of 816 (2.9%) | 2.9% (interval 2.0% to 4.3%) | 03 |
| Headline outcome, usual diet | 53 of 1,080 (4.9%) | 4.9% (interval 3.8% to 6.4%) | 03 |
| Relative difference | "40 percent" | risk ratio 0.60 (0.37 to 0.96): 40% lower | 03 |
| Absolute difference | not stated | 2.0 percentage points lower (0.2 to 3.7) | 03 |
| Number needed to treat | not stated | 51 (27 to 607) | 03 |
| Registered primary outcome | 31 of 816 (3.8%) against 44 of 1,080 (4.1%), p = 0.77 | 0.3 points lower (2.0 lower to 1.6 higher); risk ratio 0.93 (0.59 to 1.46) | 04 |
| p value, headline outcome | 0.03, chi-squared test | chi-square 4.61 on the counts gives 0.032: consistent | 03 |
| p value, registered outcome | 0.77, chi-squared test | chi-square 0.09 on the counts gives 0.76 (0.85 with the continuity correction): not 0.77 | 04 |
| p value, days off work | 0.19 | cannot check: no test statistic is printed and the means are given to one decimal place | none |
| Days off work | 1.9 against 2.1, p = 0.19 | 0.2 days fewer (0.5 fewer to 0.1 more); d = -0.06 | 05 |
| Lost before analysis, drink | "68 percent completed" | 384 of 1,200 lost (32.0%) | 02 |
| Lost before analysis, usual diet | "90 percent completed" | 120 of 1,200 lost (10.0%) | 02 |
| Gap in loss | "more participants left the FOD-7 group" | 22.0 percentage points (18.8 to 25.1) | 02 |
| Stomach upset | 139 of 1,200 (9.6%) | 139 of 1,200 is 11.6%; 9.6% would be 115 people | 06 |
| Stopped the drink for taste or stomach upset | "well tolerated" | 251 of 1,200 (20.9%) | 09 |

All intervals are 95 percent. Methods are named in each output file.

## Findings

1. **FACT. The 40 percent is relative; in absolute terms it is 2.0 percentage points.** (Table 2, row 1; output 03) About one fewer person with a symptomatic week for every 51 who drink it for 12 weeks. The interval for that number runs from 27 to 607, because the upper end of the difference interval is 0.2 points. Applied to the usual diet rate, 49 in 1,000 becomes about 29 in 1,000 (output 07).

2. **FACT. The primary outcome was changed after follow-up ended.** The registered primary outcome was GP-confirmed respiratory infection. In February 2026, "after follow-up had ended", the analysis plan was amended to make diary symptom days primary (Methods, Outcomes). The abstract calls the diary outcome "the primary outcome" and does not mention the change. On the registered outcome the groups are 3.8% and 4.1%: 0.3 points apart, with an interval from 2.0 lower to 1.6 higher (Table 2, row 2; output 04). The Discussion describes this as "in the same direction". GAP: who made the amendment and what data they had seen is not reported.

3. **FACT. Loss was heavy and unbalanced, and those who stopped the drink were removed.** 384 of 1,200 (32.0%) were lost from the drink group against 120 of 1,200 (10.0%) from usual diet (Figure 1; output 02). 251 of the 384 were "withdrawn and not followed further" because they stopped the drink (Methods, Analysis; Figure 1). The analysis is therefore of completers, not of everyone randomised. ASSESSMENT (moderate confidence): the groups compared are no longer the randomised groups. The drink group now contains only people who tolerated a fermented drink for 12 weeks, and nothing in the paper shows they resemble the usual diet group in how often they catch or record colds. GAP: baseline figures for all 2,400 randomised are not shown (note under Table 1), and no outcomes are given for anyone lost.

4. **ASSESSMENT (one scenario, not an estimate). The headline result does not survive a modest assumption about the people lost.** If those lost from both groups had recorded symptomatic weeks at the usual diet completers' rate (53 of 1,080), the drink group would have 24 + 384 x 53/1,080 = 43 of 1,200 and the usual diet group 53 + 120 x 53/1,080 = 59 of 1,200. That is 3.6% against 4.9%: 1.3 points lower, with an interval from 3.0 lower to 0.3 higher, which includes zero (output 08). Other assumptions give other answers. The point is that the conclusion depends on people the paper does not describe.

5. **FACT. Nobody was blinded and the headline outcome is self-recorded.** There was no placebo; participants knew their group and wrote their own diary (Methods). ASSESSMENT (moderate confidence): a diary outcome can move with expectation. The outcome that does not rest on the participant's own record, confirmation by a general practitioner, shows almost no difference.

6. **FACT. One percentage in the paper disagrees with its own count.** Table 3 gives stomach upset as 139 (9.6%) of 1,200. 139 of 1,200 is 11.6% (output 06). The count 139 also appears in Figure 1, so the percentage is the likelier error. The abstract's "well tolerated" sits beside 251 of 1,200 (20.9%) who stopped the drink because of taste or stomach upset (Figure 1; output 09).

7. **FACT. The secondary outcome shows no clear difference.** Days off work: 0.2 fewer on the drink, interval from 0.5 fewer to 0.1 more (Table 2, row 3; output 05). GAP: how days off were recorded is not stated.

8. **FACT. The sample is narrower than the conclusion.** Employees aged 18 to 45 at two sites of one company, with long-term illness excluded, over one winter (Methods, Participants; Discussion). The conclusion is about "adults".

9. **FACT. The manufacturer funded the trial, took part in its design, approved publication and employs two of the five authors.** (Funding and interests) ASSESSMENT (low to moderate confidence): this bears on three design choices that each favour the product: no placebo, a completers analysis, and the change of primary outcome. It is not evidence that anything was done improperly.

10. **FACT. One p value is not the one its counts give, and nothing turns on it.** Table 2 prints p = 0.77 for the registered outcome and the Methods name a chi-squared test. Pearson's chi-square on 31 of 816 against 44 of 1,080 is 0.09, which gives p = 0.76; with the continuity correction it gives 0.85 (output 04). The headline p of 0.03 does match its counts (output 03). The gap is one unit in the second decimal place and leaves the reading of that outcome unchanged: no clear difference either way. What would settle it: the exact test and software the authors used. GAP: the p value for days off work cannot be checked, because the paper prints no test statistic and gives the means to one decimal place.

## Verdict

**What it shows.** Among healthy employees aged 18 to 45 who completed 12 weeks, fewer of those assigned the drink recorded a week with three or more days of cold symptoms: 2.9% against 4.9%.

**How strongly.** Weakly. A randomised design was used, but the analysis dropped 32% of one group and 10% of the other, so the comparison no longer has the protection randomisation gives. The outcome was self-recorded by people who knew their group. It became the primary outcome after follow-up ended. The interval for the difference reaches to within 0.2 points of zero, and the registered outcome shows nothing clear. This is one trial.

**What it does not show.** That the drink prevents respiratory infections. What happens to everyone who starts the drink, a fifth of whom stopped because of taste or stomach upset. Any effect in older adults, in people with long-term illness, or beyond 12 weeks. That it "can be recommended".

**What would change the reading.** The headline and registered outcomes analysed in all 2,400 people randomised. Evidence that the February amendment was made by people who had not seen outcome data. A replication with a placebo drink and an outcome not recorded by the participant.

**Most useful follow-up.** Ask the authors for the registered primary outcome in everyone randomised, analysed in the group they were assigned to, together with the dated amendment.

## Not reported

Listed as not reported; none is assumed fine and none is assumed bad.

- Baseline characteristics of everyone randomised
- Outcomes for the 504 people lost
- Who made the February amendment and what they had seen
- How the allocation list was concealed from those enrolling participants
- How days off work were recorded
- Whether the data or analysis code can be obtained
- Any replication
