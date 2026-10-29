---
name: deck-builder
description: >
  Expert skill for building actual PowerPoint presentation files (.pptx) with real narrative structure, coherent slide architecture, and professional layout logic — not just bullet-point dumps. Use this skill whenever the user wants to create a slide deck, pitch deck, presentation, briefing, workshop slides, investor deck, training materials, or any .pptx deliverable. Trigger on: "build me a deck on...", "create a presentation about...", "make slides for...", "I need a pitch deck for...", "design a briefing deck about...", "create a PowerPoint on...", "make investor slides for...", "build a workshop deck for...", or any request where the output is a slide presentation file. Also trigger when the user has a report or document and wants it converted into presentation format. Never summarise content as chat bullets when a proper .pptx file is the right deliverable.
---

# Deck Builder

Builds narrative-driven PowerPoint files with real slide logic — not bullet lists with a .pptx extension.

---

## Core Principle

A great deck tells a story. Every slide has **one job**. The narrative pulls the audience through to a conclusion. This skill produces actual .pptx files, not chat outlines.

---

## Phase 1: Intake

Before building:

1. **Purpose** — What is this deck supposed to achieve? (Inform, persuade, sell, teach, brief?)
2. **Audience** — Who's in the room? (Investors, executives, clients, team, general public?)
3. **Context** — Presented live (speaker-led) or sent as a read-alone deck?
4. **Length** — Approximate slide count? (Default: 10–15 for most decks)
5. **Content** — Does the user have material to work from? Ask them to paste notes, a report, or bullet points.
6. **Tone** — Corporate formal, startup energy, academic, analytical?
7. **Branding** — Any specific colours, fonts, logo to include?

---

## Phase 2: Narrative Architecture

Every deck needs a narrative spine before a single slide is designed. Choose the right structure:

### Pitch / Persuasion Deck
```
1. Hook (the problem or opportunity)
2. Why Now (urgency / context)
3. The Solution
4. How It Works (mechanism)
5. Proof / Evidence
6. Business Model / Value Proposition
7. Traction / Social Proof
8. The Ask / Call to Action
```

### Executive Briefing
```
1. Situation (what's happening)
2. Complication (why it matters)
3. Key Question (what we need to answer)
4. Analysis (3–5 key findings)
5. Recommendation
6. Next Steps
```

### Informational / Educational
```
1. Title & Agenda
2. Context / Why This Matters
3. Core Content (3–5 thematic sections)
4. Key Takeaways
5. Q&A / Resources
```

### Investor Deck (Sequoia-style)
```
1. Company Purpose (one sentence)
2. Problem
3. Solution
4. Why Now
5. Market Size
6. Product
7. Business Model
8. Traction
9. Team
10. The Ask
```

---

## Phase 3: Slide Design Principles

### One Idea Per Slide
- Every slide has a **headline that makes a claim**, not just names a topic
- Bad: "Market Analysis" → Good: "Market Growing 40% YoY With No Dominant Player"

### Visual Hierarchy
- Title: largest, boldest
- Supporting content: secondary
- Data / callout: emphasised differently
- Source / footnote: smallest

### Bullet Point Rules
- Maximum 5 bullets per slide
- Maximum 7 words per bullet
- If you need more, it's two slides

### Data Slides
- One chart per slide
- Chart title states the conclusion: "Revenue Doubled in 12 Months" not "Revenue Chart"
- Always label axes and include a data source

### Slide Types to Use
- **Title slide** — Company/topic + presenter + date
- **Section divider** — Full-bleed colour with section title
- **Statement slide** — Single large claim, no bullets
- **Three-up** — Three parallel points with icons/headers
- **Data slide** — Chart + interpretive headline
- **Quote slide** — Large pull quote + attribution
- **Timeline** — Horizontal progression
- **Comparison** — Two-column contrast

---

## Phase 4: File Generation

→ Read `/mnt/skills/public/pptx/SKILL.md` before generating. Build with python-pptx:
- Set slide dimensions (16:9 default: 13.33" × 7.5")
- Apply consistent font stack (Calibri or Arial for safe cross-platform rendering)
- Use slide layouts properly (Title Slide, Title+Content, Blank, Section Header)
- Consistent colour palette (pull from brief or use professional defaults)
- Placeholder text never left in final output

**Default professional palette (if no branding specified):**
- Primary: `#1B2A4A` (dark navy)
- Accent: `#2E86AB` (blue)
- Highlight: `#F5A623` (amber)
- Background: `#FFFFFF`
- Body text: `#333333`

---

## Phase 5: Delivery

1. Generate to `/mnt/user-data/outputs/filename.pptx`
2. Use `present_files` to deliver
3. Provide slide-by-slide summary (one line each)
4. Note any slides that need real images, client data, or live charts
5. Offer to revise narrative structure, expand sections, or adjust design

---

## Quality Checklist

- [ ] Every slide has a headline that makes a claim or sets up the content
- [ ] No slide has more than 5 bullets
- [ ] Narrative flows — each slide connects to the next
- [ ] Data is attributed
- [ ] Title slide includes all required information
- [ ] File opens in PowerPoint without layout errors
- [ ] No Lorem Ipsum or template placeholder text remaining
