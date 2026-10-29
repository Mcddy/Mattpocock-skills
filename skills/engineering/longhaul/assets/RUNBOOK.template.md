# Runbook

## Start
- Command to start a session:
- Environment needed (variables, services, ports):

## Commands
- Run all checks:
- Run the app:

## Session routine
1. Read the last 30 lines of STATUS.md.
2. Run all checks.
3. Take the first feature in FEATURES.json that does not pass.
4. State the plan in three lines, then work.
5. Commit. Append to STATUS.md.

## Recover
- If checks that passed now fail: stop new work, fix the regression first.
- If blocked on a decision the spec does not settle: write the question in STATUS.md and stop.
