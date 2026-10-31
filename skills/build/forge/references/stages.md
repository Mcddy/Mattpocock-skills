# Stages and automation rules

Read at the start of a build, and again when deciding whether to stop for the user.

Forge runs on its own from the request to the finished app and stops twice, at the two decisions that are the user's to make.

| Stage | What happens | Stops for the user |
|---|---|---|
| 1. Brief and tier | The brief, the tier (Demo, Repo, Release) and an assumptions list | No |
| 2. First slice | One flow through every layer, hardest part on the path | No |
| 3. Design pack | Requirements, two or three architectures with one recommended, diagrams, decision records, contract, ledger, learning notes, rendered as a design page | **Stop A: architecture** (not for a Demo) |
| 4. Back end | Storage, rules, API and its checks, broken once on purpose | No |
| 5. Main screen and board | The populated main screen in 16 directions, three recommended | **Stop B: look** |
| 6. The rest of the app | Every screen and state in the chosen direction | No |
| 7. Verify | Scripts, then the craft test | No |
| 8. Package and report | The tier's deliverable, the report and what to learn from this build | No |

**Automation rules.**
- Ask nothing outside the two stops. When something is unclear, take the reasonable reading, write it in the assumptions list (in `docs/design.md` and the report) and carry on; the user can correct it at a stop.
- At a stop, send one short message and wait. If nobody can answer (a scheduled run, "just build it", "you pick"), take the recommendation, say so in one line, keep the options on file so the user can switch later, and continue. If the user asked to skip the stops, skip them the same way.
- Deploying, spending money, sending messages, publishing and deleting real data still need the user's go-ahead for that action, whatever the stops say.
- **Teach as you go.** Design notes and the report are written for someone learning software engineering, by default a first-year IT student: a "why this, not that" note on each big decision, new terms explained the first time they appear, and the mistakes beginners and AI tools usually make at each layer, with how this build avoided them. Push a little; never condescend. If the user says they are experienced, keep only the decisions and the mistakes.
