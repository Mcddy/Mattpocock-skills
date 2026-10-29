# Requirements for a small software tool

Instrument: project-intake, version 1, intake mode
Finished: 2026-10-08T20:47:03Z
Purpose: Captures what the tool is for, who uses it, what it holds and what must be in the first version, so the build can start without a long back-and-forth.
Questions shown: 27. Answered: 26. Skipped: 1. No answer: 0. Hidden by earlier answers: 1.

## Section: The job

### [job-one-line] In one sentence, what should the tool let someone do that is hard to do now?
Type: text
Answer:
> Let whoever is on the desk see which tools are out, who has them and when they are due back, without leafing through the paper book.

### [current-method] How is this job done today?
Type: single
Answer: By hand, on paper or from memory
Note:
> A bound book at the desk. Entries get skipped when it is busy.

### [pain] What goes wrong with the current way?
Type: multi
Answer:
- Mistakes creep in
- The information ends up in several places
- It cannot be done away from a desk
Note:
> Late returns are chased from memory. Two volunteers keep their own lists.

### [frequency] How often will the job be done once the tool exists?
Type: single
Answer: Several times a day

### [time-per-run] Roughly how many minutes does one run of the job take now?
Type: number, minutes
Answer: 3 minutes
Note:
> Timed three loans last Saturday: 2 to 4 minutes each, mostly finding the right page.

### [success-test] Describe one concrete situation in which you would say the tool has paid for itself.
Type: text
Answer:
> A member asks where the long clamps are. The desk volunteer looks at a phone and says: out since Tuesday, due back tomorrow, and here is who has them.
>
> Today that takes a walk to the rack and ten minutes with the book.

## Section: People and places

### [other-users] Will anyone other than you use it?
Type: single
Answer: Yes

### [user-count] How many people will use it in total?
Type: single
Answer: 6 to 20
Note:
> About a dozen desk volunteers on a roster. Members do not log in.

### [shared-entries] Do those people need to see each other's entries?
Type: single
Answer: Yes, everyone sees everything

### [devices] Where will it be used?
Type: multi
Answer:
- Phone
- Laptop or desktop

### [phone-conditions] On the phone, which of these apply?
Type: multi
Answer:
- One-handed use
- Gloves or dirty hands
Note:
> Often holding the tool being returned in the other hand.

### [comfort] The people using it are comfortable working out new software without help.
Type: likert, 5 points (1: Strongly disagree; 5: Strongly agree)
Answer: 2 of 5, Disagree
Note:
> Several volunteers avoid anything with a login. Two are very capable.

### [offline] Does it have to work with no internet connection?
Type: single
Answer: Sometimes
Note:
> The wi-fi drops out at the back of the building.

## Section: What it holds

### [records] What are the things it keeps track of? List them, one per line.
Type: text
Answer:
> Tools (name, tag number, where it lives)
> Members (name, member number)
> Loans (tool, member, date out, date due, date back)
> Faults reported on return

### [volume] About how many records will there be after a year?
Type: single
Answer: 1,001 to 10,000

### [existing-data] Is there existing data to bring in?
Type: single
Answer: Yes, in a spreadsheet or CSV file
Note:
> The tool list is in a spreadsheet, about 340 rows. Loans are only in the book.

### [sensitive] Will it hold any of these?
Type: multi
Answer:
- Names or contact details of people

### [connects] Which other tools or services must it exchange data with, if any?
Type: text
Answer: (skipped)

### [loss-cost] How much would it matter if one day of entries were lost?
Type: scale, 0 to 10 (0: Not at all; 10: A serious problem)
Answer: 7
Note:
> A lost day means not knowing who has what. It can be rebuilt by asking around, but that is a bad look.

## Section: Scope and delivery

### [priorities] Put these in order, most important first.
Type: rank
Answer:
1. Quick to enter data
2. Hard to make a mistake
3. Cheap to run
4. Useful summaries and reports
5. A polished look

### [must-have] List what it must do on day one. One per line.
Type: text
Answer:
> Sign a tool out to a member in under 30 seconds
> Sign it back in, with a note if it is damaged
> Show everything that is out, oldest first
> Show overdue loans

### [not-doing] List anything it should deliberately leave out.
Type: text
Answer:
> No payments or fines
> No booking ahead
> No member self-service in the first version

### [deadline] Is there a date it is needed by?
Type: single
Answer: Sooner is better, with no fixed date

### [help-hours] How many hours a week can you set aside to help while it is built?
Type: number, hours a week
Answer: 2.5 hours a week

### [running-cost] What monthly running cost is acceptable?
Type: single
Answer: Up to 10 a month

### [certainty] I already know exactly what I want this tool to do.
Type: likert, 4 points (1: Strongly disagree; 4: Strongly agree)
Answer: 3 of 4, Agree
Note:
> Sure about loans. Less sure whether fault reports belong in the same tool.

### [anything-else] What has not been asked that the builder should know?
Type: text
Answer:
> The desk phone is old and its screen is cracked, so big buttons matter more than looks.

End of export: 27 questions.
