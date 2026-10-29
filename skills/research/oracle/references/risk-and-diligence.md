# Risk registers and organisation due diligence

## Part A: risk register

### 1. Find the risks by walking the thing

Go end to end and ask at each step what it depends on and what happens if that fails.

| Area | Questions |
|---|---|
| Dependencies | Which supplier, platform, service or person, if gone tomorrow, stops this? Is there a second source? |
| Money | What is exposed, to whom, and for how long? What is the worst single loss? |
| Operations | What has no backup, no documentation, or one person who understands it? |
| Data and accounts | What is the damage if this account, key or dataset is lost, leaked or locked? |
| Outside parties | Who can change the terms: a regulator, a platform, a landlord, a counterparty? |
| Timing | What must happen by a date, and what if it slips? |
| Reputation | What becomes public if this goes wrong? |

For software and accounts, the six STRIDE categories are a useful checklist: spoofing (pretending to be someone), tampering (changing data), repudiation (denying an action), information disclosure, denial of service, elevation of privilege.

### 2. Describe each one

| Field | Content |
|---|---|
| Risk | One sentence |
| Mechanism | How it would actually happen |
| Consequence | What is lost, in concrete terms |
| Likelihood | A scale word with its basis, or "unknown" |
| Current control | What already limits it |
| Gap | What is missing |
| Early sign | What would be seen first |

### 3. Rank

Consequence first: anything unrecoverable goes to the top whatever its likelihood. Then likelihood. Do not multiply a three-level likelihood by a three-level impact and sort by the product. The result looks like measurement, puts a likely nuisance above an unlikely catastrophe, and hides which risks cannot be survived.

"Unknown" is a rating, and it ranks high until someone finds out. A risk nobody has assessed is not a small one.

### 4. Act on the top few

For each: the specific mitigation, who does it, by when, what it costs, and what risk remains afterwards. Then the early signs to monitor, and what to do first if one appears.

A position or investment gets the same treatment: what would hurt it (a gap in price, thin liquidity, a scheduled event, a failure at the broker or platform), the worst plausible loss in concrete terms taken from the user's own figures, and what would invalidate the thesis. The verdict on what to do with the position is the user's. This is analysis, not financial advice.

## Part B: organisation due diligence

### Scope

Organisations: companies, charities, public bodies, products and platforms. People appear only in a public role connected to the organisation: a listed director, an officer, a named spokesperson, and only as the public record shows them in that role.

Not in scope, and not done: locating individuals, home addresses, family, personal social accounts, health, beliefs, or anything about a private person. Not done: creating accounts under a false identity, contacting anyone under a pretext, accessing anything behind a login without the user's own authorised access, or probing systems. Public records and published material only.

If the request is really about a private individual, say this is outside what the skill does.

### Phases

| Phase | What to establish | Kinds of source |
|---|---|---|
| 1. Legal identity | Exact registered name, number, status, jurisdiction, registered office, listed officers | The official company or charity register for the jurisdiction; the securities regulator's filings for listed companies |
| 2. What it says about itself | Products, claims, pricing, terms, stated customers and partners | Its own site, documentation, terms, press releases. These are claims |
| 3. What the record shows | Filings, accounts where public, licences, court and regulator actions, patents and trademarks | Official registers and court or regulator databases |
| 4. Independent accounts | Coverage and analysis | Established news and trade press. Check whether several pieces trace to one release |
| 5. Signals | Hiring, funding announcements, product changes, domain and site history | Public job listings, announcements, web archives |
| 6. Risk flags | Insolvency notices, litigation, sanctions, regulatory action, inconsistencies between phases 2 and 3 | Official notices and registers |

Which register, database or archive applies depends on the country and changes over time. Find the current official one at the time of the work and record its address and the access date. Do not assume a named site still exists or is free.

### Standards

- Every finding has a source, a date, and a tag: FACT (official record read), REPORTED (a source says so), ASSESSMENT (your inference, with confidence), GAP.
- What an organisation says about itself is a claim until something independent supports it.
- Absence from a register you searched is "not found in X on this date", not "does not exist".
- Same-name organisations are common. Confirm identity by number and jurisdiction before attributing anything.
- Adverse findings need the strongest sourcing. An allegation is reported as an allegation, with who made it.

### Output

```
SUMMARY           three to five sentences: who they are, what was confirmed, the main concern, how complete this is
IDENTITY          registered details, with register and date read
FINDINGS          numbered, each tagged, sourced and dated
CLAIMS NOT CONFIRMED   what they say that nothing independent supports
RISK FLAGS        each with source; allegations marked as such
GAPS              what could not be determined and why
NEXT              what would most improve this, and what the user could request directly from the organisation
```
