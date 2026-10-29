Paper audit: design ceiling stated, numbers recomputed from the note's own counts, verdict in the fixed form.

Audit of a SYNTHETIC vendor note (`vendor-note.md`, invented for this example). Author-run: the session that wrote the skill produced this by following its procedure. Script outputs are in `outputs/`.

## Bottom line

"Outperforms" is not supported. On 50 questions, 82% against 72% is a difference of 5 questions, and the 95 percent interval for that difference runs from 7 points worse to 26 points better. The comparison was also not like for like: Model V had a prompt with worked examples and questions drawn from its own fine-tuning library; the other systems had a one-line instruction.

## The claim and the result it rests on

- Claim: "Model V outperforms leading systems on CLAUSE-50 [...] up to 14 points better, with 36 percent fewer errors than System A. [...] Model V is the most accurate system available for contract review." (Headline; What this means for buyers)
- Supporting result: Model V 41 of 50 (82%), System A 36 of 50 (72%), System B 34 of 50 (68%). (Table 1)

## Design and its ceiling

A vendor's benchmark comparison: one run of three systems on 50 questions the vendor wrote and marked (What we tested; How we ran it). At best this shows how these answers were marked on these questions on that day. It cannot rank the systems in general, and it cannot separate the model from the prompt it was given.

## The numbers, recomputed

| Quantity | The note says | Recomputed from its counts | Output |
|---|---|---|---|
| Model V | 41 of 50 (82%) | 82% (interval 69% to 90%) | 02 |
| System A | 36 of 50 (72%) | 72% (interval 58% to 83%) | 02 |
| System B | 34 of 50 (68%) | 68% (interval 54% to 79%) | 02 |
| Model V against System A | "outperforms" | 10 points, which is 5 questions (interval 7 worse to 26 better) | 03 |
| Model V against System B | "up to 14 points better" | 14 points, which is 7 questions (interval 3 worse to 30 better) | 04 |
| Errors, Model V against System A | "36 percent fewer errors" | 9 against 14 of 50: risk ratio 0.64 (0.31 to 1.35); the same 5 questions | 07 |
| The 12 hardest questions | 9 of 12 (75%) against 5 of 12 (42%) | 33 points (interval 5 worse to 61 better) | 05 |
| Indemnity questions, Model V | 17 correct (89%) of 20 | 17 of 20 is 85%; no count out of 20 gives 89% | 06 |

All intervals are 95 percent. Each question is worth 2 percentage points.

## What a 50-question set allows

FACT (outputs 02 to 04): it places Model V's accuracy on questions like these somewhere between 69% and 90%, and System A's between 58% and 83%. Those ranges overlap for most of their length. The intervals for both differences include zero, so these results are compatible with Model V being better, with no difference, and with Model V being slightly worse.

ASSESSMENT (an illustration by recomputation, not a power calculation): the same percentages on 200 questions would give an interval for the difference of 1.7 to 18.1 points, and on 400 questions 4.2 to 15.7 (outputs 08 and 09). A set several times larger would be needed before a 10 point gap could be told from none.

One caution on method. All three systems answered the same 50 questions, so the right analysis is paired, question by question. GAP: per-question results are not published, so only the unpaired interval can be computed here. A paired analysis could be narrower or wider, depending on how often the systems fail the same questions.

## Findings

1. **FACT. The headline gap is 5 questions, and its interval includes zero.** (Table 1; output 03) The gap to System B is 7 questions, interval 3 points worse to 30 better (output 04).

2. **FACT. "36 percent fewer errors" is the same 5 questions stated relatively.** 9 errors against 14 (Results, last line; output 07). "About one error in three" disappearing (What this means for buyers) is that ratio presented as an expectation; its interval runs from 69% fewer to 35% more.

3. **FACT. The systems were not run on equal terms.** Model V used the vendor's production prompt with three worked examples. Systems A and B got one line and no examples (How we ran it). ASSESSMENT (high confidence): any difference could come from the prompt as easily as from the model. GAP: no run of Systems A and B with a comparable prompt, and no run of Model V with the one-line instruction.

4. **FACT. The questions come from the library used to prepare Model V's fine-tuning data.** (What we tested) GAP: no check for overlap between the test questions and that data is reported. ASSESSMENT (moderate confidence): overlap would favour Model V and would not carry over to a buyer's own contracts.

5. **FACT. One run each, with no measure of run-to-run variation.** (How we ran it) GAP: settings are given only as "default", and the versions of Systems A and B only as those "available in June".

6. **FACT. Marking was done by two vendor staff who could see which system produced each answer.** (How we ran it) GAP: how often the two markers disagreed is not reported.

7. **FACT. The "hardest questions" were chosen after scoring.** They are "those most systems got wrong" (Table 2). On them the gap is 33 points with an interval from 5 worse to 61 better (output 05). ASSESSMENT (high confidence): picking a subset by looking at the results will tend to show a gap, whether or not one exists.

8. **FACT. One percentage disagrees with its own count.** Table 2 gives 17 correct (89%) on 20 indemnity questions. 17 of 20 is 85%, and no whole count out of 20 gives 89% (output 06). 17 of 19 would (output 10). GAP: whether a question was dropped is not said.

9. **FACT. "The most accurate system available" rests on a comparison with two systems.** (What this means for buyers; Table 1)

## Verdict

**What it shows.** On one run of 50 vendor-written questions, Model V with a tuned prompt was marked correct on 41, System A with a one-line prompt on 36 and System B on 34.

**How strongly.** Very weakly as evidence that the model is better. The differences are 5 and 7 questions with intervals that include zero. The prompts differed, the questions share a source with the fine-tuning data, the markers were not blind, and there was a single run. ASSESSMENT (moderate confidence): any one of these could plausibly produce a gap of this size.

**What it does not show.** That Model V is more accurate than Systems A and B on contract questions in general. That it is "the most accurate system available". That a buyer's error rate would fall by a third. Anything about a buyer's own documents.

**What would change the reading.** The same prompt and examples for all systems. Several runs each, with the spread reported. A few hundred questions written by someone outside the vendor from documents not used in training. Marking without sight of which system answered. Per-question results, so the comparison can be paired.

**Most useful follow-up.** Ask for the per-question results and the exact prompts, then rerun all three systems on your own sample of clause questions with one shared prompt.

## Not reported

Listed as not reported; none is assumed fine and none is assumed bad.

- Run-to-run variation
- Any check for overlap between the test questions and the fine-tuning data
- Per-question results
- Agreement between the two markers
- The settings used, and the versions of Systems A and B
- Any independent replication
