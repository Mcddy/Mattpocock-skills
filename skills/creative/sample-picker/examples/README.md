Historical teaching examples; producer tests describe earlier source runs, not current canonical output proof.

# Examples

Three pickers, each made by the authoring session by following the skill's procedure: write the data, validate it, build it with `scripts/build_picker.py`, drive it with `scripts/test_picker.py`. Nobody else has run them. All content is SYNTHETIC: the note-taking tool, the product called Stallbook and the invoice clients are invented.

Open any `.html` file in a browser. No server is needed.

| File | What it is |
|---|---|
| `theme-picker.json` | Input. Five colour themes for a note-taking tool (three light with the warm one leading, two dark), on a real-looking note, field, table and buttons, with density and text size tweaks |
| `theme-picker.html` | Output. The built picker. Each card shows nine measured contrast pairs for its theme |
| `heading-copy-picker.json` | Input. Four versions of a product page heading and sub-line, with alignment, heading size and a show-the-buttons tweak |
| `heading-copy-picker.html` | Output. Each version drawn in the page's header: brand, navigation, heading, sub-line, two buttons, footnote |
| `table-layout-picker.json` | Input. Three layouts of the same eight invoices (table, cards, compact list), with density and row shading tweaks |
| `table-layout-picker.html` | Output. Each layout drawn at a phone width (360) and a wide width (960) side by side, with its height and whether it scrolls sideways |
| `*.choice.txt` | Output. The short text block the Result view produced after the page was driven. This is what a person pastes back |
| `*.choice.json` | Output. The same session in the JSON form |

## How the choices were produced

`python scripts/test_picker.py examples/NAME.html --save-choice examples` drove each page in a browser the way a person would: shortlist the last two options, compare them, open the last one, change the first tweak, choose it, leave a note, open Result. The saved files are what the page then showed at 1280 wide in a plain tab.

So the chosen option in each file is the test journey's, not a considered preference, and the note is test text with quotation marks, an accented letter and a line break in it, to prove those survive. The measured facts are real measurements from that browser.

Each saved choice parses back, in both forms, to the same object:

```
python scripts/parse_choice.py examples/theme-picker.choice.txt --picker examples/theme-picker.json
python scripts/parse_choice.py examples/theme-picker.choice.json --picker examples/theme-picker.html
```

In the authoring session both commands exited 0 for all three pickers, and the two forms were equal once the saved time was set aside. `parse_choice.py` adds two advisories for the theme choice: a note was left, and the chosen option is not the recommended one.

## Regenerate

```
python scripts/validate_picker.py examples/theme-picker.json
python scripts/build_picker.py examples/theme-picker.json --out examples/theme-picker.html
python scripts/test_picker.py examples/theme-picker.html --save-choice examples
```

and the same for the other two. The saved time in the choice files will differ, and nothing else should.

## What to look at

- **Theme picker.** The same note in five sets of colours. The lowest measured pair on each card: Warm paper 5.61, Linen and ink 5.72, Sage desk 5.42, Ember 7.33, Slate night 7.82. Those five figures matched the shared contrast checker run on the same specimen (`theme-picker.html#solo=OPTION-ID`).
- **Heading picker.** At 1280 wide, open "Leads with the result": its heading takes three lines in the header where "Says what it is" takes two. The measured line count sits beside each, and a list of the four headings in prose would not have shown it.
- **Layout picker.** On a phone-width screen the Compare view shows one option at a time, switched by the two large tabs above the bottom bar. The table reports that it scrolls sideways at 360 (685 px of content); the cards are 2.0 phone screens tall; the compact list is 1.0 and scrolls nowhere.
