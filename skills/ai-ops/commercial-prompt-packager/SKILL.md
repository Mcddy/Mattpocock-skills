---
name: commercial-prompt-packager
description: "Turns a finished prompt into a sellable asset pack: tiered pricing, licence terms, sales copy adapted per channel, technical documentation and a packaging checklist, with optional Cerberus branding. Use when he says 'package this prompt', 'make this commercial', 'I want to sell this', 'create a product listing for this prompt', 'write sales copy for my prompt', 'what should I charge for this', or is building a prompt library or product line for Gumroad, Promptbase, Substack or direct client sales. Not for writing or improving the prompt itself (use meta-prompt-engineer), tuning it against tests (prompt-bench), choosing an AI tool (nexus), or packaging a skill or app rather than a prompt (use skill-creator or web-to-store)."
---

# commercial-prompt-packager

Takes a finished prompt and produces everything needed to sell it: price tiers, licence per tier, sales copy per channel, technical documentation and a checklist. Detail lives in `references/`.

## Use when

- Shaun wants to sell, license or productise a prompt or prompt set.
- He asks what to charge or how to list it on a marketplace, Substack or to a direct client.
- He is building a prompt library or product line.

## Not this skill

| The request | Goes to |
|---|---|
| Write or improve the prompt itself | meta-prompt-engineer |
| Test variants against examples | prompt-bench |
| Pick the right AI tool or platform for the prompt | nexus |
| Package a skill for other hosts | rosetta |
| Turn a web app into a mobile app | web-to-store |

## Inputs

- The finished prompt (paste it) or the prompt set.
- Target buyer, channel or channels, and Cerberus-branded or white-label. Ask for whichever is missing.

## Procedure

1. **Assess the asset.** Answer: what it does in one sentence; who buys it; the problem in the buyer's words; complexity (utility, sophisticated system prompt, full agent architecture); branding; primary channel. Run a quick quality check on the prompt. If it is poorly engineered, say so and send it to meta-prompt-engineer before packaging.
2. **Price in tiers**, by value to the buyer, not time spent. Always at least three tiers (entry, standard, premium), plus a bespoke option where adaptation is plausible. Adjust by sophistication, specificity of niche, proof, audience (business over hobbyist) and exclusivity. Ranges and tier contents: `references/pricing-and-licensing.md`. State the currency and mark ranges as starting points to verify against comparable listings.
3. **Assign a licence per tier** (personal, commercial, extended commercial, white-label) and adapt the standard protection wording. Use `references/pricing-and-licensing.md`.
4. **Write the sales copy**: headline, subheadline, pain, solution, what is included, who it is for, social proof, call to action. Then adapt for each chosen channel (marketplace, Substack, direct pitch). Use `references/sales-copy.md`.
5. **Write the technical documentation**, shorter for the entry tier, full for premium. Template in `references/tech-doc.md`.
6. **Apply branding.** Cerberus-branded: use `references/cerberus-branding.md`. White-label: strip every Cerberus reference and use neutral professional language the buyer can rebrand.
7. **Assemble the pack** in the format below and tick the checklist against what was actually produced.

## Output

```
## <Prompt name>: Commercial Asset Pack
### Pricing Tiers        (names, prices, inclusions)
### Licence Terms        (licence per tier)
### Sales Copy           (primary channel in full, others adapted)
### Technical Documentation
### Packaging Checklist
- [ ] Prompt file (clean, final)
- [ ] Technical documentation
- [ ] Sales copy, primary channel
- [ ] Sales copy, secondary channels
- [ ] Licence terms
- [ ] Pricing page copy
- [ ] Example outputs (2 to 3)
```

## Rules that always hold

- Never invent testimonials, results, sales numbers or user counts. Use a visible placeholder until real ones exist.
- Do not claim the prompt does more than it was tested to do; list known limitations honestly in the documentation.
- Licence wording is a starting template, not legal advice. Tell Shaun to have it reviewed before relying on it, and to check tax and registration obligations for sales (he is an Australian sole trader) with an accountant.
- Marketplace fees, rules and audience change. Do not state them as current; mark them verify before use.
- Direct client pitches skip marketing copy: lead with the client's own problem, add a one-paragraph capability summary, attach the documentation.
- Keep Shaun's tone: direct, authoritative, no filler.

## References

- `references/pricing-and-licensing.md`: tier table, pricing signals, licence types, protection wording (dated).
- `references/sales-copy.md`: copy architecture and channel adaptations.
- `references/tech-doc.md`: technical documentation template.
- `references/cerberus-branding.md`: Cerberus brand details and white-label rules.
