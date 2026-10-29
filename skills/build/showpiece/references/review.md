# Research-informed generation and revision

These mechanisms are design/engineering judgments informed by primary research, not experimentally validated guarantees for these skills or hostile audiences.

| Evidence | Mechanism | Limit |
| --- | --- | --- |
| [Doshi & Hauser](https://doi.org/10.1126/sciadv.adn5290): individual story ratings improved while outputs converged | Choose different arguments/compositions before polishing; inspect repeated collection rhythm | Short stories do not establish interface outcomes |
| [Wadinambiarachchi et al.](https://doi.org/10.1145/3613904.3642919): image-generator support increased fixation in a 60-person task | Form independent directions; name the reference lesson and how work differs | Specific ideation study |
| [Sharma et al.](https://arxiv.org/abs/2310.13548): assistant/preference evaluation can favor agreement | Critique brief and artifact; allow disagreement; require localized evidence | Historical models/tasks |
| [Zheng et al.](https://arxiv.org/html/2306.05685v4): model judges show position/verbosity biases | Derive acceptance independently; equalise context and swap order for consequential comparisons | Preference is not truth or human acceptance |
| [Kalai et al.](https://arxiv.org/abs/2509.04664): accuracy incentives can reward guessing | Allow omission/uncertainty; compare factual commitments | No universal hallucination fix |
| [Bellaiche et al.](https://link.springer.com/article/10.1186/s41235-023-00499-6): labels changed identical-painting evaluations | Separate quality criticism from process attitudes; no false human attribution | No directly sampled hostile audience established |

## Executable review loop

1. Before the candidate's self-description, derive what the reader/user should understand or do. Derive expected computations independently.
2. Inspect real content and rendering. Exercise relevant actions, difficult states, recovery and responsive recomposition. Ask applicable review lenses for the highest-impact weakness; no invented defect quota.
3. Record `location → observation → consequence → correction → check`. Verify criticism itself: models can call a record empty when a valid extra field remains, or suggest unmeasured business gains.
4. Fix the highest-impact weakness and compare under the same conditions. Change the organising idea when weak, instead of adding polish. Repeat affected checks.
5. Keep hard acceptance separate from taste: factual support, data semantics, operation and access cannot be offset by appeal. Correct implementation still needs editorial judgment. Model confidence is not human approval.

## Requested human-versus-AI screening

When the user sets a screening pass condition, preserve it explicitly. Before screening, freeze the candidate, viewing conditions and neutral question. Use fresh judge chats separate from improvement consultations, with the same artifact and prompt for each judge; supply no desired answer, production story, previous verdict or skill text. Retain full answers, uncertainty and visible reasons. If the user requires both judges to say HUMAN-MADE, one AI-MADE or inconclusive answer means the criterion is not met. Technical passes, compliments and low-confidence near misses cannot substitute.

Ask for a separate concrete quality critique. Verify its reasons against the artifact and runtime: a focus ring, familiar style or ordinary bug does not establish origin. Revise substantive defects and direction, preserving accessibility, truth and useful scope information. New rounds require a meaningful candidate change; retain all results instead of rerolling an unchanged artifact until a preferred answer appears. A same-chat follow-up is dependent feedback and cannot be reported as a fresh trial. A passed screen establishes that trial's answers, not actual authorship, population acceptance or general skill efficacy.
