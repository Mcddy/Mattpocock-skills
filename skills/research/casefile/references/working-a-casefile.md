# Working a casefile: inputs, views, rules and files

Read this when preparing the inputs for `scripts/build_casefile.py`, when explaining the page to the user, or when a change is refused and the reason has to be given.

## 1. Inputs to the builder

The ledger is the two CSV files that deep-research-orchestrator's `ledger_check.py` reads. Column names and order are fixed.

| File | Columns |
|---|---|
| Sources | `source_id, title, publisher, address, tier, published, accessed, read_level, family, notes` |
| Claims | `claim_id, question_id, statement, status, source_ids, locator, load_bearing, confidence, conflicts_with, conflict_class, resolution` |

| Field | Allowed values |
|---|---|
| `tier` | `primary`, `peer_reviewed`, `secondary`, `aggregator`, `unverified` |
| `read_level` | `full`, `section` (both count as opened), `snippet`, `relayed` (neither counts as opened) |
| `status` | `FACT`, `REPORTED`, `ASSESSMENT`, `MODEL_OUTPUT`, `GAP` |
| `load_bearing` | `yes`, `no` |
| `confidence` | `high`, `moderate`, `low`, or blank. Needed for an ASSESSMENT |
| `conflict_class` | `scope_mismatch`, `time_supersession`, `method_difference`, `direct_conflict`, `insufficient_evidence` |
| `source_ids`, `conflicts_with` | ids separated by `;` |
| dates | real calendar dates written `YYYY-MM-DD`, not in the future; `published` may be blank |

The CSV format has no place for the wording of questions or for assessments. Those go in an optional JSON file passed with `--extra`:

```json
{"questions": [{"id": "Q1", "text": "Which standard is harmonised under the Directive?"}],
 "assessments": [{"id": "A1", "question_id": "Q1", "judgement": "One sentence or two.",
   "likelihood": "likely", "confidence": "moderate",
   "confidence_reason": "Why the confidence is what it is.",
   "claim_ids": ["C1", "C2"], "written": "2026-10-09"}]}
```

`likelihood` is one of: almost no chance, very unlikely, unlikely, roughly even chance, likely, very likely, almost certain, no basis. Likelihood and confidence are separate fields on purpose. An assessment must name at least one claim that exists. Write an assessment into this file only if the user or an analysis skill actually made that judgement; the builder does not invent one, and neither should the model.

## 2. The views

| View | What it is for |
|---|---|
| Ledger | Claims under their questions, each with its status tag, whether the answer depends on it, and a one-line summary of its sources. Search, and filters by question, status, source tier, load-bearing, open conflict, and source older than a chosen number of days |
| Sources | Every source with tier, how much was read, age, and the claims that rest on it |
| Conflicts | Each pair side by side with its class, both statements, their sources and the note on each side. Open pairs come first. Recording, reclassifying or settling a pair writes to both claims |
| Check | The ledger rules run over the whole casefile: errors, and the same advisory notes `ledger_check.py` gives |
| Activity | The log of changes made in the page, newest first |
| Keep and export | The casefile export and import, the two CSV files, the Markdown brief, CSV import, and Start again |

Three counts sit above the views because each one changes what can be written: open conflicts (with how many are direct), load-bearing claims that are only REPORTED, and gaps. Each is a button: the first opens the Conflicts view and the other two filter the ledger to those claims. The page has no summary panel of totals beyond these and the count beside each view's name.

## 3. Lineage, in both directions

Opening any item shows what it rests on and what rests on it, each one click away.

- **Assessment.** The claims it rests on, each followed by its sources with tier, read level and dates. Above them, the support in words: `Rests on 3 claims: 2 FACT, 1 REPORTED.` and `Weakest support: 1 REPORTED claim (C2). A REPORTED claim is what a source says, not yet established.` The order from weakest to strongest is GAP, MODEL_OUTPUT, ASSESSMENT, REPORTED, FACT. This is a description, never a score.
- **Claim.** Its sources, and the assessments that rest on it. Status buttons, the load-bearing switch, and its conflicts.
- **Source.** Every claim that depends on it and every assessment downstream, then **If this source falls**: for each dependent claim, one of
  - it would be left with no source at all;
  - it would lose its only opened source, and what is left was never opened;
  - it could no longer be a FACT, because no remaining source is opened, addressed and at secondary tier or better;
  - it would still rest on the sources named;

  followed by each assessment that rests on a claim left unsupported. Nothing is changed by looking; this is a reading of the ledger as it stands.

## 4. Rules the page enforces as changes are made

A refused change says why, in the page, and changes nothing. Where a rule overlaps `ledger_check.py` the wording is the checker's.

| Attempt | Refusal |
|---|---|
| Set a claim to FACT with no source, no locator, no opened source, no source with an address, or nothing at secondary tier or better | `claim C2: cannot be a FACT: no source has an address. Use REPORTED, or open a better source` (and the matching sentence for each other cause) |
| Mark a MODEL_OUTPUT claim load-bearing, or set a load-bearing claim to MODEL_OUTPUT | `claim C5: MODEL_OUTPUT cannot be load-bearing. Open what it cites and record that as a new claim` |
| Save an ASSESSMENT claim, or an assessment, with no confidence | refused, naming the item |
| Save an assessment that rests on no claims | `rests on no claims. An assessment cannot rest on nothing` |
| Refer to an id that does not exist, reuse an id, or enter a date that is not a real `YYYY-MM-DD` date | refused, naming the field |
| Delete a source that claims rest on, or a claim an assessment rests on, in a way that would break a rule | refused, naming what depends on it |

Status changes, deletions, conflict changes and imports are each one undo step.

Conflicts: `direct_conflict` and `insufficient_evidence` stay open until both claims carry a resolution note. The other three classes record why two claims differ without contradicting each other and are not counted as open.

## 5. Files in and out

| Action | Result |
|---|---|
| Export the casefile | One JSON envelope (`app` casefile, `schema` 1, a `content_id` derived from the title and the built ledger) with everything: questions, sources, claims, assessments, activity log. Offered as a download and as text in a box. This is the durable copy |
| Import a casefile | Checked before anything changes: JSON, app, schema, the data against every ledger rule, then `content_id`. A file for a different casefile is named and asked about in the page. A refused import changes nothing |
| Show the two CSV files | The ledger in the exact format `ledger_check.py` accepts. An unmodified ledger comes back byte for byte. Questions' wording, assessments and the log are not in this format |
| Import two CSV files | Both are checked with the ledger rules first. Problems are listed with file and line number. Any error means nothing changes. If the new ledger drops claims that an assessment rests on, the page names those assessments and asks before removing them |
| Build the brief | Markdown assembled only from the ledger: an empty Answer section for the user to write, assessments, findings with their tags, sources with tier and access date, open conflicts, gaps. It adds no wording or judgement of its own |

## 6. Where the data lives

The page autosaves to the first of these that works: a host storage object, the browser's storage, memory. It says which in a sentence. In a sandboxed chat preview the sentence is `Not saved: this page cannot store data here. Export to keep your work`, and it means exactly that. A casefile reopened from the built file starts from the ledger it was built with unless the browser kept later work or an export is imported.

## 7. What a casefile cannot tell

It checks bookkeeping. It cannot tell whether a source is right, whether a locator says what the claim says, whether the search was thorough, or whether an assessment is sound. A ledger with no errors is a tidy ledger. The judgement recorded in an assessment is the user's, or comes from an analysis the user accepted.

## 8. Neighbours

| Step | Skill |
|---|---|
| Gather sources and build the ledger | deep-research-orchestrator |
| Weigh competing explanations over the ledger | intelligence-analyst |
| Forecast, assess risk or decide from it | oracle |
| Check a finished draft against sources | fact-check |
| Work the ledger over time, record assessments, keep the lot | this skill |

Judgements reached with those skills come back into the casefile as assessments resting on named claims.
