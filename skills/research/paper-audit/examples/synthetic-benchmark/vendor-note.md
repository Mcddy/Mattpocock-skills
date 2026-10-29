# SYNTHETIC DOCUMENT. INVENTED FOR THE PAPER-AUDIT EXAMPLE

Nothing below is real. There is no Model V, no System A or B, no vendor and no benchmark called CLAUSE-50. Every number was made up so that an audit has something to find. Do not cite it.

---

# Model V outperforms leading systems on contract clause questions

A results note from the vendor of Model V. Published 8 July 2026.

## Headline

Model V outperforms leading systems on CLAUSE-50, our benchmark of contract clause questions. It answered 82 percent of questions correctly, against 72 percent for System A and 68 percent for System B: up to 14 points better, with 36 percent fewer errors than System A. On the hardest questions the gap was wider still.

## What we tested

CLAUSE-50 is a set of 50 questions about contract clauses, each with one correct answer. Our solutions team wrote the questions from the same library of 1,900 agreements that we used to prepare Model V's fine-tuning data. The questions cover indemnities (20), termination (15), liability caps (10) and governing law (5).

## How we ran it

Each system answered the 50 questions once.

- Model V was run with our production prompt, which includes three worked examples of clause questions and answers.
- System A and System B were run through their public interfaces with a one-line instruction: "Answer the question about the contract."
- All systems used their default settings. We used the versions of System A and System B that were available in June.

Answers were marked correct or incorrect by two members of our team, who could see which system had produced each answer. Where they disagreed, they discussed the answer until they agreed.

## Results

### Table 1. Correct answers on CLAUSE-50

| System | Correct | Percent |
|---|---|---|
| Model V | 41 of 50 | 82% |
| System A | 36 of 50 | 72% |
| System B | 34 of 50 | 68% |

### Table 2. Selected breakdowns

| Subset | Model V | System A |
|---|---|---|
| The 12 hardest questions (chosen after scoring, as those most systems got wrong) | 9 of 12 (75%) | 5 of 12 (42%) |
| Indemnity questions (20) | 17 correct (89%) | 14 correct (70%) |

Model V made 9 errors and System A made 14, a reduction of 36 percent.

## What this means for buyers

Model V is the most accurate system available for contract review. Teams that switch can expect about one error in three to disappear.

## Availability

The CLAUSE-50 questions and the marked answers are available to customers under a confidentiality agreement.
