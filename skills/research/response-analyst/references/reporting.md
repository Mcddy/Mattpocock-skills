# Reporting: how to write the findings

The script produces counts. This file is about the sentences built on them.

## 1. Order of a findings page

1. **Method line.** First line of the reply: "Response analysis: counts over named denominators, with intervals."
2. **Answer.** Two to four findings the responses support, each with its count and denominator, and one recommendation. Tag each load-bearing claim FACT, ASSESSMENT or GAP.
3. **Who answered.** How respondents were reached, how many of how many invited, who is missing and what that probably does to the picture. This comes before any result table.
4. **Closed questions.** The full distribution for each, with who skipped. A compact table is fine.
5. **Comparisons.** Both groups' counts, then the difference with its interval.
6. **What people wrote.** Themes as the analyst's coding, the codebook, counts by respondent, two or three quotations each with respondent ids, and the case that does not fit.
7. **Quiz items**, when there is a key: how the groups were formed and their sizes, the item table, the candidates and how each was read.
8. **What these responses cannot show.** The GAP list.
9. **Next.** What to do, and what to ask next time.

About a page. If a section has nothing in it, leave it out.

## 2. Tags

| Tag | Use it for | Example |
|---|---|---|
| FACT | A count read from the file or printed by the script | "FACT. 5 of the 8 online respondents who answered reported audio problems." |
| ASSESSMENT | An inference from the counts, with a confidence word and its reason | "ASSESSMENT, moderate confidence. The pace complaint is mostly an online problem: 7 of 9 online against 3 of 14 in person, but nine people is few." |
| GAP | Something the responses do not establish | "GAP. Nothing is known about the 15 who did not respond." |

## 3. Say this, not that

| Not this | This | Why |
|---|---|---|
| "63% agreed" | "12 of 19 who answered agreed (63%, interval 41% to 81%); 3 of 22 skipped" | A percentage alone hides the size and the skips |
| "Most customers want X" | "14 of the 23 who replied want X. They were reached through the newsletter, so they are subscribers who open it" | A convenience sample describes those who answered |
| "The sample is too small to analyse" | "With 6 answers the interval runs from 30% to 90%. Here is what they said" | Small samples still yield findings; the width shows the uncertainty |
| "You need at least 30 responses" | "One more answer would move this by 17 points" | There is no universal minimum; it depends on the decision |
| "Online attendees were significantly less satisfied" | "7 of 9 online against 3 of 14 in person; difference 56 points, interval 15 to 77" | Never "significant" without the test and its inputs; the interval says more |
| "No difference between groups" | "The interval for the difference runs from minus 15 to plus 56 points: these responses do not show which group is higher" | Failing to separate two groups is not showing they are the same |
| "Average satisfaction 3.2 out of 4" | "Very useful 7, Useful 11, Slightly useful 3, Not useful 1 (of 22)" | An agreement scale is ordered categories. A mean needs the sentence that it treats them as numbers |
| "Pace was mentioned 9 times" | "5 of the 20 who wrote anything raised pace" | Count respondents. One person can mention it three times |
| "Respondents fall into three types" | "Totals ranged from 4 to 17 (of 20 items). These are tallies on an informal questionnaire" | A tally is a count, never a type or a diagnosis |
| "Item 7 is a bad question" | "Item 7 is a candidate: the 8 top scorers mostly chose B (6 of 8), and the key says C. Reading the item, B is correct, so the key is wrong" | A flag is something to read, and the reading is the finding |
| "The quiz shows who is weak" | "Scores ranged from 2 to 11 of 12 keyed answers" | A score is a count of keyed answers on this quiz on this day |

## 4. Coding free text

1. Export with `--coding-sheet`. Read every passage once before making any code.
2. Draft the codebook: five to eight codes for a few dozen passages. Each code gets a name and a one-sentence definition that says what is in and, where it helps, what is out. A second person should be able to apply it without asking. Start from `assets/codebook-template.csv`.
3. Code every passage. A passage can carry several codes. A passage that fits nothing gets no code; do not stretch a definition to cover it and do not make a code for one comment unless it matters on its own.
4. Run `--themes CODED.csv --codebook CODEBOOK.csv`. Read the list of respondents with no code and the advisories.
5. For each theme worth reporting pick two or three quotations that show its range, with respondent ids. Quote exactly. Shorten only by cutting whole sentences, and mark a cut.
6. Report at least one case that does not fit: an uncoded passage, a lone dissent, or a respondent whose answers point the other way.
7. Label the themes as the analyst's coding and show the codebook. If only one pass of coding was done, say so.

With a handful of comments (they all fit in the reply), skip the codebook and quote every one with its respondent id. Coding four comments into themes adds nothing and hides the comments.

Interview transcripts work the same way: one passage per answer or per speaker turn, a respondent id per interviewee, and counts of interviewees, not of mentions.

## 5. Privacy check before any quotation is shown

- Respondent values are replaced by ids (R01, R02, ...) unless the user asks for the originals with `--keep-ids`. Keep any id map private.
- The `screen` column catches email addresses, phone numbers and web addresses. It does not catch names, employers, job titles, places, or a detail that identifies someone in a small group ("the only night-shift nurse"). Read every quotation for those.
- If a quotation identifies its author or someone else, remove the detail and mark the removal ("[role removed]"), or paraphrase and say it is a paraphrase, or leave it out.
- In a small group a verbatim turn of phrase can identify its author to colleagues. When respondents were promised anonymity and the group is small, prefer paraphrase.
- Do not work out who a respondent is, and do not help anyone else to.

## 6. A short worked sample

SYNTHETIC. Six volunteers answered a roster check, asked face to face by the coordinator; three others on the roster were not on shift.

> Response analysis: counts over named denominators, with intervals.
>
> **Answer.** Short notice is the one thing these six agree on. FACT: 4 of the 5 who answered named it as what makes a shift hard to attend (1 of 6 skipped). With five answers the 95% interval runs from 38% to 96%. Post the roster a week ahead; it is cheap and reversible.
>
> **Who answered.** 6 of 9 on the roster, asked in person by the person who writes it. GAP: the 3 not on shift were not asked, and face-to-face answers to the coordinator may be softened.
>
> **Comparison.** Both newer volunteers (2 of 2) would swap to a fixed shift, against 2 of 4 longer-serving. The difference is 50 points with an interval from minus 24 to plus 85: these answers do not show which group is keener.
>
> **Comments, all four.** R01: "Send the roster a week earlier." R02: "Stop changing it after it is posted." R04: "Nothing, it is fine." R05: "A week of notice would fix most of it."
>
> **Cannot show.** What the roster as a whole thinks. These are six answers, reported as six answers.
