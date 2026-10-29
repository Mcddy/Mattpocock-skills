# Writing the sitrep

`scripts/sitrep_diff.py OLD.json NEW.json --markdown` prints the skeleton in the right order. This file is for completing it, and for doing the comparison by hand when there is no shell.

## Order

1. **High priority.** New, changed and withdrawn items whose requirement is high priority.
2. **Indicators.** Any that changed status, with the evidence.
3. **Other changes.** Medium before low.
4. **Not checked this run.** Unreachable sources with the items resting on them, and items carried forward.
5. **No change.** One line: how many were rechecked and found the same.
6. **What it means.** One or two sentences, ASSESSMENT, with a confidence.
7. **The updated watch file**, in full.

If nothing changed: one line, then the file. No headings, no recap of the state, no "as a reminder".

## Wording

| Category | Say | Never say |
|---|---|---|
| New | The statement, its status, source id and tier, the date read | "Breaking", "significant development" |
| Changed | Was, then now, side by side | Only the new statement, leaving the reader to recall the old one |
| Withdrawn | What the source said before, that it no longer says it, and what it says now or that it is silent. Then what else in the file bears on the same question | "False", "no longer true", "debunked", "turned out to be wrong" |
| Unreachable | Which source, how it failed, which items rest on it and the date they stand at | "No change" for those items |
| Carried forward | The item ids and their dates | Anything implying they were rechecked |
| Conflict | Both statements, each with its source, as separate items | A middle value, or the one that seems likelier presented alone |
| Indicator seen | What was watched for, what was seen, where, and what it was said in advance to mean | A new interpretation invented after the fact |

A withdrawal on a high-priority requirement is where a reader is most likely to jump to the opposite conclusion. Say in the same bullet what the withdrawal does not show, and point to the item that does bear on it.

## Length

One screen. Trim statements to their changed part in the sitrep; the full text is in the file. If one screen is not enough, the watch has too many requirements or the run was left too long, and the first line says which.

## Doing the comparison by hand

Say it was done by hand. Then, by id and by nothing else:

1. Ids in the new state and not the old: new.
2. Ids in the old state and not the new: withdrawn, if one of their sources was reached this run. If none was, the item should not have been removed; put it back.
3. Ids in both: changed if the statement, status, sources or requirement differ; otherwise unchanged, and rechecked only if its date is today.
4. Indicators whose status differs.
5. Sources marked unreachable today, and what rests on them.
6. Count: new, changed and withdrawn items plus indicator status changes.

Do not pair a new id with a missing id because the text is close. If one is the other reworded, restore the old id and it becomes a changed item.

## A worked sample

SYNTHETIC, to show shape and length. A watch with three requirements; R1 is high priority.

> **Sitrep, changes since last run.** Port fees watch. Run 2026-09-08 against 2026-09-01: 3 changes.
>
> **High priority** (R1: has the final rule been published?)
> - WITHDRAWN F2. Was REPORTED, S2 secondary: a draft was expected within weeks. The trade note has been rewritten and no longer gives a timing. That is not a report that the draft is cancelled: the register (F1, FACT, S1 primary, read today) still shows no rule.
>
> **Indicators**
> - I2 (R2) went from not seen to seen on 2026-09-08: the fee schedule shows a fee above 100. It shows 120. Evidence: S1 primary.
>
> **Other changes**
> - CHANGED F3 (R2, low). FACT, S1 primary. Was: the fee is 80. Now: the fee is 120.
>
> **Not checked this run**
> - S3 (forum) wants a login. F4 stands as of 2026-09-01.
>
> **No change:** F1 rechecked and the same. I1 not seen.
>
> **What it means** (ASSESSMENT, moderate confidence): the fee rise has happened ahead of the rule, so budget on 120 now. Nothing read today says when the rule will come.
>
> Updated watch file follows.

And the unchanged case, whole:

> **Sitrep, changes since last run.** Port fees watch: no change since 2026-09-01. 4 of 4 items rechecked, all 3 sources reached. Updated watch file follows.

## The baseline

For a first run there is nothing to compare. Lead with "Sitrep baseline", then for each requirement in priority order: where it stands (the items, with status and source), what is not established (the GAP items), and which indicator would change the answer. Then the file. Keep the same one-screen limit.
