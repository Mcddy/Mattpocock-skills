# Reference and asset index

Read when you need to know which file holds what. The full list of what each reference and asset contains.

Read a reference when the work reaches it, and always before the step that names it. This file carries the essentials of each, so a build never stalls on a reference.

| File | Holds |
|---|---|
| `references/tiers.md` | Demo, Repo and Release: how the tier is chosen, what each delivers, how each runs and reports |
| `references/reference-method.md` | Step 4b: choosing a shipped-product analog by work surface, what transfers and what never does, mechanisms per surface |
| `references/results.md` | The result contract every check script follows: statuses, exit codes per tool, receipts, how to report them |
| `references/design.md` | The design pack and Stop A: requirements, options, diagrams, decision records, the learning layer (why notes, glossary, mistakes), the stop message |
| `references/architecture.md` | Kinds of build, sizing, the component ledger, when to split |
| `references/backend.md` | Ownership of rules, contract, validation, errors, persistence, migrations, time and money, retries and idempotency, local-server exposure, model output as untrusted input, auth, secrets |
| `references/visual.md` | The visual bar, the token contract, the sixteen board directions plus Ink Paper and when each fits, the board and Stop B, bold layout moves, illustration, photography, expressive motion, tells and foundations, the Dribbble lens |
| `references/frontend.md` | Composition from the task, identity and fonts by delivery, motion, states, words on the page, the delivery container, the craft test, checks |
| `references/operations.md` | Containers, deployment, CI, health, backup, cost. Destructive commands are separated and labelled |
| `assets/design-template.md` | The design pack to fill in, with working Mermaid examples |
| `assets/visual-kit/` | Tokens and components for the sixteen board directions plus Ink Paper (`kit.css`, `kit2.css`, `kit3.css`), `kit-dir.js` for the live board, open-licence fonts, the clay illustration core with dog and plant packs, an example screen. Its README says what to copy |
| `assets/release/` | Release tier templates: the desktop launcher, the PyInstaller spec, `build_exe.bat`, pinned build requirements |
| `assets/reference-app-plants/` | "Plant round", the canonical reference build: every back-end rule with its checks, the visual kit on a new subject, its design pack (`docs/`), `run.bat` and a tested `release/` folder. Read it for patterns, not to restyle. One gap is kept on purpose for teaching and named on its README's first line |
| `assets/reference-app/` | "Stock count", a teaching example from an earlier version, not a reference: its README's first line says so and lists what not to copy |
