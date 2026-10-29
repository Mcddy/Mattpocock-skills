# QA: measured checks and visual review

Choose `film`, `ui`, `logo` or `loop` and sound policy before judging. State requirements
before examining output. A count or heuristic is evidence to inspect, not a quality score.

## Automated scope (`scripts/qa/reel_critic.py`)

| Check | Applicability and interpretation |
|---|---|
| Probe and decode | Required to obtain valid measurements; failures are runner-error |
| Frozen/near-still seconds | Film/logo review candidate outside fully declared still intervals; omitted for UI/loop |
| Staging, long shots, metronomic motion, cadence | Film review candidates; omitted for UI/logo/loop |
| Narrative score dynamics/repetition | Film review candidates; not a universal soundtrack rule |
| Luminance, banding, bitrate | Measured candidates in all modes; graphic blacks and simple content can be valid |
| Audio stream policy | `required` plus absent stream fails; `silent` plus present stream fails; `auto` imposes neither |
| Loudness/peak | Measure existing requested audio; unavailable/-inf values are unknown, not zero |
| Loop seam | Not implemented here; loop mode remains partial until separately checked |
| Contact sheet/plots/reports | Requested missing outputs are partial; final write failure is runner-error, prior failures retained |

`--allow-still START:END` accepts non-overlapping intervals inside the media duration.
Only whole one-second bins contained in those intervals are omitted from stillness
heuristics. Raw measurements remain in the report. Silent policy means no audio track;
it does not equate a present, inaudible track with absence. Review sound quality separately.

## Common receipt contract

`env_check`, `sync_check` and `reel_critic` emit one `RECEIPT {JSON}` line on stderr.

| status | Exit | Meaning |
|---|---|---|
| completed | 0 | Applicable requested checks completed; no configured hard failure |
| partial | 3 | Applicable coverage or requested output missing, no known hard failure |
| not-applicable | 0 | No applicable check, with reason; not a pass |
| failed | 2 | Applicable hard criterion ran and failed; retained even after later errors |
| runner-error | 1 | Input/tool/dependency/probe/decode prevents the job; not a product defect |

Fields include checks, coverage, errors, execution_status and quality_verdict.outcome.
The quality outcome is failed, no-hard-defect-found, undetermined or not-applicable;
none means aesthetically approved. Execution may be completed despite a failed hard
criterion. Known failures dominate later gaps; the gaps and errors remain visible.
`reel_critic` preserves info/picture/sound/flags and writes the final receipt plus output
outcomes to report.json. If writing fails, stderr retains observations. Report and
image outputs require readback/visual inspection appropriate to the deliverable.
Unchanged filmstrip/slop_lint/selftest tools do not yet implement this common adapter.

## Cue alignment (`scripts/qa/sync_check.py`)

Use only when the brief requires cue-driven sound. Median absolute offset must be
less than one frame; maximum less than two. These strict thresholds use inspected
cues and do not identify which acoustic event produced a peak. Retain the selected,
inspected and skipped counts. No selected kinds is not-applicable; all out of range
is partial, not a crash; mixed coverage stays partial unless a known failure makes
it failed. Missing/malformed/empty decoder output is runner-error. Successful load()
still returns (samples, sample_rate), and --json adds one JSON object on stdout.

## Visual review

- Film: story clarity, thought/staging, weight, contacts, arcs, continuity and the
  pacing of moving or quiet beats. Foot-slide/reach checks apply only to those actions.
- UI: immediate useful content; readable initial/final/interrupt/recovery states;
  keyboard access and focus; usable reduced motion. Resting states may be still/silent.
- Logo: recognition, silhouette, typographic hierarchy and readable lock-up; motion
  supports the mark rather than imposing a character-film narrative.
- Loop: no visible seam, unintended pause, duplicated end frame or audio discontinuity;
  use separate loop playback/frame evidence, not the scanner's mode label.
- All: hierarchy at thumbnail and intended viewing size, continuity, contrast,
  edge/gradient quality, final ratio/crop/safe zones and target-player support.

Inspect at speed, then contact sheets, relevant frame strips and full-resolution
stills. Listen where sound is required; loudness numbers do not prove it sounds right.
Record timestamp/frame, evidence, consequence and disposition. Label model visual
review accurately; never imply independent human review. Test the actual final export
and repaired frames again. No numerical average can excuse a material failed action.

## Honest delivery and comparisons

Record source-inspected / generated / rendered / exercised / measured / not run,
with exact files or frames. Keep origin and substitutions in metadata/sidecars and
handoff. No fresh render/browser/media test ran as part of this 3.1.0 code upgrade.
To claim better finished animation, use the same brief, constraints and revision
budget for old and new; hide version labels; fix defect categories in advance and
count defects, corrections and time. Say no improvement shown if that is the result.
