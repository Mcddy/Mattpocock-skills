# Teaching examples

Historical producer outputs, retained byte-for-byte apart from this README. They are teaching evidence from the earlier authoring session, not newly validated canonical outputs of revision 1.2.0. Their HTML, JSON and fixture data have not been regenerated.

Both galleries were made by the authoring session by running `scripts/state_gallery.py`. Nobody else has run them. Open either `gallery.html` in a browser: no server is needed to read a finished sheet.

## stock-count-gallery

A gallery of the forge skill's reference app (a stock count with a small server), 10 states x 4 themes x 2 widths = 80 frames.

| File | What it is |
|---|---|
| `stock-count.states.json` | The states file: input |
| `seed_items.json`, `seed.py` | SYNTHETIC stock (twelve invented items, two with very long names) and the script that posts it to a loopback server: input |
| `gallery.html` | The sheet, 883,867 bytes: output |
| `gallery.json` | Every measured fact for the 80 frames: output |

The embedded frames are reduced so the file stays under 900 kB: 390-wide frames are embedded at 70 percent, 1280-wide frames at 56 percent, WebP quality 30. An opened frame says so. At that reduction the names, counts and messages in an opened wide frame are readable and the small monospaced item codes are soft. An earlier run of the same 80 frames, with the wide frames at 1024 px, wrote 2,449,795 bytes. The full-size pictures the run wrote to `frames/` and `sheets/` are not shipped, because the skill folder holds no images.

To regenerate (ports are examples; the reference app is the forge skill's `assets/reference-app/server.py`):

```
python server.py --port 8181 --db /tmp/stock.db &          # the copy with stock in it
python server.py --port 8182 --db /tmp/stock-empty.db &    # the copy with nothing in it, for the empty state
python seed.py http://127.0.0.1:8181 seed_items.json
python ../../scripts/state_gallery.py stock-count.states.json --out out --image-scale 0.7 --max-image-width 720 --quality 30
```

The run took about four and a half minutes in the authoring session. The stock list read from the server before and after the run was byte for byte the same, so no step saved anything.

### What the sheet showed (the author's reading)

Measured: 0 of 80 frames with a measured problem, 0 not reached. Lowest text contrast per theme: paper 5.86, slate 5.73, ember 7.35, night 7.99. No sideways overflow and no cut-off text in any frame, including the two long names at 390.

Looked at, at full size: all ten states at 390 wide (five in paper, five in ember), and populated (slate), long names (paper), destructive confirm (night), busy (night) and validation error (paper) at 1280. The remaining frames were seen only at thumbnail size on the sheet, or not at all, and nothing is claimed about them beyond the measurements.

| State | What the frame shows | Finding |
|---|---|---|
| loading | The tally reads "Loading the count." and four ghost rows stand where the list will be | Design assessment, fairly sure: a ghost row is about half the height of a real row at 390, so the list will jump when it arrives |
| empty | "Nothing on the sheet yet", how to add the first item, and a button to the form | None |
| populated, with low stock | Twelve rows; a low row has a stripe and the words "Low: at or below 1" | None. At 390 the first row starts about 300 px down, after the search, filter and step controls: worth knowing for a counting task |
| no search results | 'Nothing matches "torque wrench"', what the search looks at, "Show everything" | None |
| validation error | The server's reason under each field in bold with a heavier border, typed values kept, focus on the first bad field | Design assessment, low confidence: "is required" and "must be a whole number" are fragments that lean on the label above them |
| refused by a rule | "Only 3 in stock. The count cannot go below zero." in the row, count still 3 | None |
| server down | "The server did not answer", that nothing changed, "Try again" | None |
| destructive confirm | The question in the row, naming the item and its count, "Keep it" and "Remove" | Not captured: the step confirms that focus is on "Keep it", but no focus ring shows, because focus arrived after a pointer click. A keyboard user would see one; this sheet does not prove it |
| long names | Both long names wrap inside their rows at both widths; the seven-digit count fits | Design assessment, fairly sure: at 390 the longer tally pushes the Display button onto its own line, so the header is 56 px taller in this state than in the others |
| busy | The pressed row's minus, plus and Remove are dimmed | Design assessment, fairly sure: waiting is shown by dimming alone. Nothing says "saving" in words |

Not captured at all: hover, the success confirmation after a write (it would change stored data), and any real device.

Craft test on the whole sheet, from the frames that were looked at: no failure. The awkward cases hold (long names, zero items, a refused action, a lost connection), after each action the page says what happened, and the page is specific to counting stock. The four assessments above are improvements. Whether every control works was not tested here; a gallery captures states, it does not try every control.

## planted-defects

A small page written for this example, with three defects planted on purpose and one state that cannot be reached. 5 states x 2 themes x 2 widths = 20 frames.

| File | What it is |
|---|---|
| `parcel-shelf.html` | SYNTHETIC page: a front-desk log of parcels waiting to be collected. Its comments mark the planted defects: input |
| `parcel-shelf.states.json` | The states file. Themes are switched by clicking the page's own theme control: input |
| `gallery.html` | The sheet, 282,315 bytes, frames at full size: output |
| `gallery.json` | The measured facts: output |

Regenerate with `python ../../scripts/state_gallery.py parcel-shelf.states.json --out out`.

What the gallery shows, and how each thing is found:

| Planted | Found by | Where on the sheet |
|---|---|---|
| Sideways overflow at 390: a carrier reference that never wraps | **Measured.** "Overflows sideways by 65 px" | long reference at 390, in both themes. Not at 1280, and not in any other state |
| Low-contrast muted text in the dusk theme | **Measured.** "5 text elements below contrast (lowest 2.31)" in populated, 2 in long reference | The dusk frames of the two states that draw muted text, at both widths. The dusk frames of empty and validation error draw none and are clean |
| An empty state that shows nothing at all | **Only by looking.** All four empty frames say "No measured problem" | The empty row: its "Should show" line asks for a sentence and a first action, and the frames show a header and a form with nothing between them |
| A state that cannot be reached (`collected parcels` clicks a control the page does not have) | **Reported.** "Not reached", with the failed step and the reason | Four labelled empty frames in the last row |

So 9 of 20 frames have a measured problem (5 measured defects in reached frames, plus the 4 not reached), and `--fail-on-problems` exits 1 on this file. The blank empty state is in none of those counts. That is the reason the skill tells the model to look.

The second defect also shows why every state is captured: a theme's weak colour is only measured in the states that use it.
