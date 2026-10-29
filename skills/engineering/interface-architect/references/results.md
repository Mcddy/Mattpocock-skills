# Interface Architect check results

This package contains five exact check scripts vendored from accepted Forge 3.3.2: `contrast_check.py`, `dead_controls.py`, `delivery_check.py`, `target_size.py` and `ui_candidates.py`. Their native `--version` and receipt version intentionally remain `forge 3.3.2`, recording the code's source rather than the Interface Architect package revision. No other Forge tool is bundled or implied by this guide.

## Native statuses and report categories

Preserve the native word and exit code beside the command; use the report category below without claiming the script printed a different word.

| Native status | Exit | Report category | Meaning |
|---|---|---|---|
| `completed` | 0 | completed | The tool finished its bounded check. Candidate scans can complete with findings; this is not a product-quality or accessibility pass. |
| `failed` | 1 | failed | A check ran and found a failure according to that tool and its flags. |
| `partial` | 3 | partial | Coverage is incomplete, such as unmeasured text, undecided target exceptions or an unexercised interaction. It is not a pass. |
| `runner_error` | 4 | runner-error | The tool could not do its job or deliver its receipt, including an unavailable dependency, crash or receipt write failure. |
| `usage_error` | 2 | runner-error | The command/input is invalid, so no product result was established. Retain native `usage_error` and exit 2, record invalid command/input as the reason, and correct the command without dropping a required check. |

The five agreed report categories are completed, partial, not-applicable, failed and runner-error. Not-applicable is a separate, reasoned report item for a criterion exemption or a check outside the agreed scope. These scripts do not emit a native overall `not-applicable` status. Exempt disabled text is different from contrast the scanner could not measure. Missing capability, no targets, no steps or an untested interaction is not an exemption.

## What each check establishes

| Tool | Bounded result and missing coverage |
|---|---|
| `ui_candidates.py` | Lists source DEFECT/CANDIDATE findings by rule. Default exit 0 means the scan ran, even with defects; use `--fail-on-defect` to make confirmed source defects exit 1. Read and verify findings; patterns do not judge the design. |
| `contrast_check.py` | Measures text contrast in the selected page state. Below-threshold measured text exits 1; unmeasured text or nothing measured makes the otherwise clean run partial. It does not audit all contrast or accessibility requirements. |
| `target_size.py` | Checks 24-by-24 CSS-pixel geometry and spacing, not a legal minimum or certification. Undecided exceptions, overlapping targets or no targets make the run partial; `--fail-on-unresolved` makes undecided exceptions exit 1. Declared inline targets and the page's observed sentence heuristic still need review against the actual criterion. |
| `dead_controls.py` | Lists controls with no observed effect, mouse-only candidates, composite reach and optional `--keyboard` activation results. It does not use exit 1 for candidates. Missing/unclickable/over-limit controls, unresolved composite reach or nothing activated makes the run partial. Inspect all reported keyboard coverage even when the scan completes; a request or changed element does not prove the promised action succeeded. |
| `delivery_check.py` | Exercises explicit semantic steps. A failed tab/frame step or blocked form can exit 1; no steps makes an otherwise clean run partial. `--tab-only` exercises a confirmed normal-origin tab without claiming a frame run. A stand-in is never proof of a particular host. |

For normal web origins or native shells, preserve real forms, storage, downloads and keyboard submit behaviour. Keep frame-only failures as preview limitations when that frame is not the delivered surface. For a sandboxed preview or unknown surface, retain the strict delivery handling in the protocol and name the assumption.

## Receipts and safe execution scope

The last stderr line is `RECEIPT {JSON}`. `--receipt FILE` also writes the JSON to the named file; choose a fresh path because an existing file can be overwritten. `--help` and `--version` print no receipt. If a receipt cannot be written, `product_status` and `product_exit` retain the product result, while the overall status becomes `runner_error`, exit 4. Preserve both rather than reporting the undelivered product result as a completed run.

Record command, tool version, environment, intended semantic observation, actual result and coverage. Read the receipt back: a hash shows file identity, not that the intended control, data or promised action was checked. Native exit 3 used to mean unavailable runner in the older Interface scripts; it now means partial, while runner failures use 4. `dead_controls.py --json` replaces `controls_tried` with `activated`, adds row `outcome` and keyboard/composite sections. No other script in this package consumes that old key.

Browser checks load page code and can make network requests. Dead-controls clicks include delete/send actions; preparation JavaScript and keyboard checks can repeat effects after fresh loads. Use only authorised throwaway/test copies with throwaway data. Delivery steps and form probes can trigger site JavaScript handlers. `--block-outside` is an optional resilience test and permits same-origin writes; it is not a no-write sandbox. Honour unavailable browser capability and host restrictions. This guide grants no installation, network, deletion or account authority.

Current offline, syntax and preservation checks are recorded in the revision handoff. Browser execution, host activation and any improvement in finished outputs require their own evidence.
