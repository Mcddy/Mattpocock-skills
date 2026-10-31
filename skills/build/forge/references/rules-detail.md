# Rules that always hold, in full

Read at the start of a build. SKILL.md carries the short form of each rule; this is the full wording, and it wins if the two differ in detail.

- Nothing is described as working unless it ran in this session. Nothing is described as deployed unless it is.
- No placeholder handlers, controls that do nothing, or sample data presented as results. Never invent proof: clients, testimonials, metrics, logos, awards and "trusted by" rows stay empty or labelled as sample.
- The server owns the rules. Client-side checks are a courtesy.
- One error shape across the API. Messages shown to people say what happened and what to do, and never expose internals.
- Only safe operations are retried automatically. Timeouts are always set. An unknown outcome is shown as unknown.
- Secrets never appear in code, the page, logs, commits or examples. Example configuration uses obvious placeholders.
- Queries are parameterised. Text from users or the server goes on the page as text, never as markup.
- Money is stored in integer minor units with its currency. Time is stored by kind (see step 3). Dates, times, numbers and money are formatted with `Intl` in the user's locale, never by hand, except where the user wrote their own forms ("8:00", "60 min"), which win. `Intl` is the starting point, not the last word: en-AU writes "Sept" and "Mon, 2 Mar", so apply the user's forms; a native date input shows the browser's own format, so show the chosen date beside it in the user's form. A local event is shown in its own zone, with the zone named when the viewer's differs.
- The user's spelling and punctuation apply to the interface, server messages and docs. When a mark is ruled out, rewrite the sentence; a lookalike character is the same habit.
- Destructive commands, including in your own shell, are never chained with ordinary ones and are labelled with what they destroy.
- Version-specific facts (packages, model names, prices, platform limits) are looked up when used and dated.
- A clean scan is not a quality verdict. The craft test (step 7) is made by looking at the render.
- Words claim no more than the evidence. A label, KPI name, badge or summary drawn from data takes its wording from what the data is: sample, synthetic, candidate, measured or validated. A score over a synthetic corpus ranks candidates; it never "confirms" anything.
- Origin survives fallbacks. A path that can answer with mock, sample or cached data instead of the live source marks `origin` (live, sample or mock) in the response or a sidecar, in the handoff, and on screen wherever a user would otherwise take it for live. A file produced is not proof the provider worked.
- Each check ends with one RECEIPT line: **completed**, **failed**, **partial** (an applicable check did not run), **runner_error** (the tool could not run) or **usage_error** (`references/results.md`). Report it verbatim. Partial and runner_error are never a pass.
- Where a reference file or an older script copy disagrees with this file, this file wins. Scripts from forge 3.3.2 print their version with `--version`. A script that rejects a flag used here, or prints an older version, is a version mismatch: report that check as runner_error with the mismatch, hold it, and do not work around it by dropping the flag.
