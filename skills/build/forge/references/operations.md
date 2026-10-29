# Operations: packaging, deployment, keeping it running

Load this when a flow in scope needs it. Nothing here is built by default; each part enters through the component ledger in `architecture.md`.

Deploying, registering a domain, creating an account, spending money, and publishing are the user's decisions. A request to build is not a request to deploy. Prepare the files and the commands, and stop before the step that acts outside this session unless the user asked for that step.

Everything named below (base images, action versions, platform features, prices) changes. Look it up at the time of use and date it. None of the examples in this file was run in this package's session.

## 1. Configuration and secrets

- Configuration comes from the environment. The code reads it once at start and fails with a clear message if something required is missing.
- A committed example file lists every variable with an obviously fake value (`DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/NAME`). Real values are never committed, pasted into a chat, placed in a page, or printed in logs.
- Example files follow the rule they sit beside: a compose file never carries a literal password.
- Seed data runs only by an explicit command or a development flag. Data you generated is labelled as sample in the data itself; data the user supplied or asked for by name is theirs and is not relabelled. Starting against an empty database without the flag shows the empty state.
- A local app holding real records ships a backup command (SQLite's backup API to a folder the user chooses) and a restore that has been run once (section 6).
- If a secret has been exposed, cleaning the file does not undo it. The owner rotates it.

## 2. Containers

Use one when the target takes containers, or when setup differs between machines enough to cause failures. A single process on a stock runtime does not need one.

```dockerfile
# Pin the base image to a specific current version; check what is current when you write this.
FROM python:3-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser
EXPOSE 8000
CMD ["python", "server.py", "--port", "8000"]
```

- Run as a non-root user. Do not copy secrets or local data files into the image; use an ignore file.
- Data lives in a named volume or an attached database, never in the container's own file system.
- Give each service a health check, and make dependants wait on it.
- Pass secrets from the environment or the platform's secret store: `POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set this in the environment}`.

### Everyday commands

```bash
docker compose up -d          # start in the background
docker compose logs -f        # follow logs; Ctrl-C stops following, not the services
docker compose ps             # what is running
docker compose down           # stop and remove containers; named volumes and their data are kept
```

### Destructive commands: read before running

These are listed apart on purpose: chaining `down -v` after an ordinary start-and-logs line, or treating `system prune -a` as routine, destroys data by accident. Run each of these only on purpose, alone, after checking what it will remove.

| Command | What it destroys |
|---|---|
| `docker compose down -v` | The containers **and every named volume in the project, including the database's data** |
| `docker system prune -a` | Every stopped container, every unused network, the build cache, and **every image not used by a running container**, across all projects on the machine |
| `docker volume rm NAME` / `docker volume prune` | The named volume's data / every volume not attached to a container |

Before any of them: confirm which project and machine you are on, and that a backup exists and has been restored at least once. An agent does not run these without the user asking for that exact effect.

## 3. Deployment

- Choose the host from the ledger: does the app need a long-running process, a database, scheduled jobs, a static site only? Compare current offerings and prices at the time; do not rank platforms from recall.
- One command or one pipeline deploys. The same artefact goes to every environment, with configuration from that environment.
- Schema changes run as a scripted, repeatable step before the new code serves traffic. A change that removes or renames something the old code reads needs two releases.
- Know how to go back: the previous version stays deployable, and you know whether the data change can be reversed.
- Before deploying anything with SQLite or local files, look up whether the host's disk survives a redeploy or restart. If it doesn't, attach a volume or use a managed database.
- Keep two step files. The full set (restarts, parallel writes, deletes) is for local and scratch environments only. A smoke set is for a live address: health, read-only lists, and one create-read-delete in a marked test account, deleting only ids it created.
- After deploying, run the smoke steps against the deployed address, create a throwaway record, restart or redeploy through the host, read it back, and exercise the page there. "Deployed" in a report means this was done.

## 4. Continuous integration

A pipeline is worth having once there are checks to run. Minimum: on every change, install pinned dependencies, run the checks, fail loudly. Deployment from the pipeline is a second, separate job that depends on the first and uses a secret held by the platform.

```yaml
# Sketch only. Check current action versions and your platform's syntax before use.
name: checks
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.x" }
      - run: python scripts/api_check.py http://127.0.0.1:8765 assets/reference-app/api-steps.json --start "python assets/reference-app/server.py --port 8765 --db /tmp/ci.db"
```

## 5. Knowing it is broken

- A health address that touches the real dependencies (the reference app's does a database round trip). It is only useful if something calls it and someone is told when it fails.
- Logs: one line per request with a request id, the route, the status and the time taken. Never the body, headers or secrets. Content that has to be kept to debug or audit (a model reply, a webhook payload) is redacted, stored apart from the request log with restricted access, and deleted after a set retention period; see `backend.md` section 8.
- An alert goes to a channel the owner reads, says what failed and since when, and does not repeat every minute. Sending messages to people or services needs the user to have set that up; the skill writes the code and does not register webhooks or bots itself.
- Alerts driven by a model's output follow `backend.md` section 8.

## 6. Backup and restore

- Decide what loss is acceptable and how long a restore may take, in plain numbers.
- Back up on a schedule to somewhere other than the machine that holds the data. For SQLite use the database's own backup command or API, not a copy of a file that may be mid-write.
- Restore to a scratch location and run the API checks against it. Until that has been done once, the backup is untested.

## 7. Cost

List what will bill: host, database, storage, outbound data, each outside API. For each, look up the current price and the free allowance, and multiply by expected use. State the date and the source. If a number cannot be found, write that it could not be found; do not estimate from memory.

## 8. Words for the report

The status words are defined in `SKILL.md` step 10; this table restates them for operations work.

| Word | Means |
|---|---|
| Written | The files exist. Nothing was executed |
| Run locally | Executed in this session, with the command and result shown |
| Run in a frame stand-in | Exercised inside a local sandboxed frame |
| Run in the delivered surface | Exercised in the actual product preview or on the actual device |
| Deployed | Running at an address, and the checks were run against that address |

Use the weakest word that is true.
