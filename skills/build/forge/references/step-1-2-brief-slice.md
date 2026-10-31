# Steps 1 and 2: brief, tier and first slice

Read before steps 1 and 2.

Six lines. Tag every fact: **confirmed** (the user said it: quote it), **inferred** (your reading: give the reason) or **preference** (a taste, not a constraint). An explicit statement stays confirmed; an inference is never promoted because it is convenient. These tags open the design pack's requirement ledger:

- **Who** uses it, on what device, how often.
- **The one job**, and **the hardest judgement** in it: what makes the decision hard, what an expert checks first, what goes wrong for newcomers. (Invoicing: what is overdue, and is the GST right? Stock: what is about to run out?)
- **What it keeps**, and for how long. This decides whether there is a back end.
- **Where it is delivered.** A chat preview cannot run a server. A static host cannot keep shared data. A phone cannot reach a server bound to another computer's 127.0.0.1.
- **Conventions**: locale, time zone, 12 or 24 hour, currency format, spelling. Take them from the user; state the ones you inferred.
- **Works means**: one sentence a stranger could check by using it.

Then the **tier** from the request (`references/tiers.md`): **Demo** (one HTML file to try an idea), **Repo** (the default: a project run the way developers run it, with `run.bat`, checks and git) or **Release** (a Windows app with an icon, built by `build_exe.bat`). When two readings fit, take the lower tier and say what moving up adds. Start the assumptions list.

### 2. Name the first slice

Write the full vision down separately and keep it. Then pick one flow that crosses every layer the finished thing will have **and keeps the hardest part on the path**. Rank the claims that could sink the approach (an integration, a latency, a race, working offline) and put the top one inside the slice. A stand-in for the uncertain part cannot prove that part.

With a back end, the slice is accepted only with all four of:

1. a write that succeeds and is shown back from storage, not from the page's memory;
2. a write the server refuses for a rule (a duplicate, a clash, a limit), with the refusal shown to the user;
3. input the server rejects as invalid, with the reason beside the field it concerns;
4. the data still there after the server restarts.

A list that renders sample data is not a slice, and neither is a form that stores to a variable. If an outside integration cannot be reached, build against its documented contract with saved fixtures, label the stub where a reader will see it, and report the live boundary as unresolved. A stub never counts toward a claim that the integration works.
