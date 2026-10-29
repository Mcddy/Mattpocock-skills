# Study designs: what each can show, where each usually fails, what to ask

State the ceiling before anything else. A design sets the most a study can conclude even if everything in it was done well. The questions in the last column are the ones that most often change the reading for that design; answer only those that apply, each with a locator, and record the rest as not reported in the extraction file's `reporting` list. The item names in brackets are the ones `scripts/extraction_check.py` expects for that design.

| Design | The most it can show | Usual weaknesses | Questions that matter most |
|---|---|---|---|
| Randomised trial | That the intervention caused a difference, in the people analysed, over the period followed | Loss that differs between groups; people analysed in a group other than the one they were assigned to; outcomes chosen or changed after the data came in; no blinding with a self-reported outcome; a comparison group given nothing | Was the outcome registered before the trial, and is that the one in the headline? (`registration`) How was allocation hidden from those enrolling? (`allocation_method`) Who knew the allocation? (`blinding`) Was everyone randomised analysed? (`analysis_population`) Why did people leave, by group? (`reasons_for_loss`) |
| Comparison of groups not formed by chance (an experiment allocated by class, site, seat, date or choice) | That the groups differed after the intervention. Cause only if the groups were alike in everything else, which this design does not ensure | The groups differed before anything was done; whoever formed the groups knew what each would get; more than one thing differs between the groups; the person measuring knew the groups | How were the groups formed, and by whom? (`how_groups_were_formed`) Were the groups alike at the start, on what evidence? (`baseline_comparison`) What else differed between them besides the intervention? (`other_differences_between_groups`) Who knew the groups when the outcome was measured? (`blinding`) (`reasons_for_loss`) |
| Cohort (people followed over time, exposure not assigned) | That an exposure and an outcome go together over time in this group. Not that one causes the other | People who choose or receive the exposure differ in other ways; adjustment covers only what was measured; loss to follow-up | How were people selected, and who could not be? (`how_participants_were_selected`) How was the exposure measured, and before the outcome? (`exposure_measurement`) Which differences were adjusted for, and which obvious ones were not? (`confounders_adjusted`) (`reasons_for_loss`) |
| Case-control (people with the outcome compared with people without, looking back) | That past exposure is more common among cases than controls. An odds ratio, not a risk | Controls drawn from a different population; exposure recalled differently by people who became ill; rare exposures | Where did the controls come from, and would they have been cases had they fallen ill? (`how_cases_and_controls_were_selected`) Was exposure recorded before the outcome or recalled after? (`exposure_measurement`) (`confounders_adjusted`) |
| Cross-sectional survey | What this sample said or had at one moment. No order of events, so no cause | Who was reachable and who answered; question wording; self-report | How was the sample drawn? (`sampling_method`) What share responded? (`response_rate`) What exactly was asked? (`question_wording`) Were results weighted, and to what? (`weighting`) |
| Before and after (one group measured twice) | That something changed between two dates | Anything else that changed in the period; the group was chosen because it was unusually bad and drifted back; measurement changed | Is there a comparison group that did not get the change? (`comparison_group`) What else changed? (`other_changes_in_the_period`) Was the measure the same both times? (`measurement_same_before_and_after`) |
| Modelling or simulation | What follows from the stated assumptions and inputs | Results driven by one assumption; no test against outcomes that later occurred; ranges that reflect only some of the uncertainty | Which assumptions carry the result? (`assumptions`) Where do the inputs come from? (`input_data_sources`) Has the model been checked against what happened? (`validation_against_outcomes`) What happens when the main assumption moves? (`sensitivity_analysis`) |
| Benchmark comparison | How these systems scored on these items under these settings | See `references/benchmarks.md` | See `references/benchmarks.md` |
| Vendor report | What the vendor chose to show about its own product | Everything under benchmark, plus selection of what to publish | As for a benchmark, and who ran, marked and published it (`funding`, `author_affiliations`) |
| Qualitative study (interviews, observation) | The range of experiences and reasons found in the people studied. Not how common they are | Who was reachable; the analyst's own reading; quotations chosen to fit | How were participants found? (`how_participants_were_selected`) How were themes derived, and by how many people? (`analysis_method`, `who_coded_the_data`) |

Asked of every design: who paid and who wrote it (`funding`, `author_affiliations`); whether the data can be obtained (`data_availability`); whether anyone has repeated it (`replication`).

## Reading the numbers, whatever the design

- **Relative and absolute together.** A ratio with no baseline says nothing about size. Find the comparison group's rate and state both: `effect.py two-by-two` from counts, `effect.py relative-to-absolute` from a ratio and a baseline.
- **The denominator.** Check who is in it. "Of those analysed", "of those who responded" and "of those randomised" give different percentages from the same events.
- **One outcome among many.** If ten outcomes were measured and one is reported in the headline, the headline's p-value does not mean what it says. Count the outcomes in the tables.
- **A surrogate is not the thing.** A laboratory value, a self-report, a click or a benchmark score stands in for what the claim is about. Say what the stand-in is and how well it is known to track the real outcome. If that is not established, it is a GAP.
- **Size before significance.** A difference can have a small p-value and be too small to matter, or a large p-value and an interval that includes effects that would matter. Report the interval and judge the size in the outcome's own units.
- **Absence of evidence.** "No significant difference" from a small study is not evidence of no difference. Look at how wide the interval is.

## Words for "how strongly"

Tie the wording to design, size and consistency. Do not invent a grade or a score.

| Wording | Use it when |
|---|---|
| Strongly | The design can support the claim, the analysis kept the design's protection, the interval excludes effects too small to matter, and other studies agree |
| Moderately | The design can support the claim and was mostly kept, but it is one study, or the interval is wide, or one weakness could move the result |
| Weakly | The design could support the claim but lost its protection in the analysis, or the result rests on one outcome among several, or the interval nearly reaches no effect |
| Not at all, or cannot tell | The design cannot support this kind of claim, or the numbers needed are not reported |

Say which of these conditions decided the wording.
