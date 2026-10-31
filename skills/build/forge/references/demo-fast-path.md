# Demo fast path

Read when the tier is Demo, before step 1.

**Demo fast path.** For a Demo, steps 1, 5, 6, 7 and 8 apply; steps 2 to 4 (slice acceptance, design pack, contract, back end) do not, and there is no Stop A.
- Requirements are the promises the page makes ("Saved in this browser only", "Undo"), each with a status.
- Checks: `delivery_check.py` on the packed file in a tab, again with `--reduced-motion` and with `--block-outside`; `render_gate.py` per state; `contrast_check.py`; `dead_controls.py` and `target_size.py` with `--prep-js` for a populated state; `ui_candidates.py`. Break the UI steps once on purpose (plant a rounding or state bug and watch a step fail).
- An app that opens empty loads labelled sample data on `?sample=1`, and the board gets `--query sample=1`, so the live board shows it populated.
- With no design page, the report carries the learning notes and a short glossary itself, plus what moving to Repo would add.
