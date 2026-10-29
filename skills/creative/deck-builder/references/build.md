# Building the file

Use the host's pptx file skill for file mechanics when one exists. This is the fallback and the checklist either way.

## python-pptx
- Slide size 16:9, 13.33 by 7.5 inches.
- Font stack Calibri or Arial for safe rendering on any machine.
- Use the built-in layouts (Title Slide, Title and Content, Section Header, Blank) rather than free-floating text boxes where a placeholder fits.
- One palette throughout, from the brief or the default below.
- Set alt text on images; keep body text at 18 pt or larger on live-presented decks.
- Native charts (`chart_data`) rather than pasted images, so numbers stay editable.

## Default palette (when no branding is given)
- Primary `#1B2A4A` dark navy
- Accent `#2E86AB` blue
- Highlight `#F5A623` amber
- Background `#FFFFFF`
- Body text `#333333`

## Final checks
- Every slide has a claim headline or a clear setup headline.
- No slide over 5 bullets.
- No placeholder, lorem ipsum or template text left.
- Title slide has topic, presenter and date.
- File reopens without error.
