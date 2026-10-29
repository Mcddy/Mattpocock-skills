# Automation reference

Every workflow is described as **Trigger, Retrieve, Act, Post**.

- Trigger: schedule, event, webhook, threshold or cascade.
- Retrieve: live data, memory, documents, APIs.
- Act: one single-purpose agent job.
- Post: save, send, notify or feed the next stage.

## Workflows for Shaun's domains

| Workflow | Trigger | Retrieve | Act | Post |
|---|---|---|---|---|
| Daily Cerberus brief | 6am schedule | Overnight price action, news, sentiment data | Three-lens analysis, brief, risk flags | Formatted draft to Substack or his inbox |
| Trade signal monitor | Price threshold breach (charting webhook) | Current levels | Rapid three-lens assessment at signal time | Signal brief to Telegram with a go or no-go recommendation |
| Research synthesis | New URL or document in the inbox folder | The item | Extract, summarise, tag, connect | Structured note added to the knowledge base |
| Prompt quality audit | New prompt file in the library | Test cases | Run, score against the rubric, note improvements | Audit report saved beside the prompt |

Human review before anything is published or acted on. A signal brief is a prompt to look, not an order.

## Stack

| Function | Tool |
|---|---|
| Scheduling | n8n, APScheduler, cron |
| Notifications | Telegram bot |
| Data ingestion | Perplexity API, RSS |
| Storage | PostgreSQL, Notion API |
| Deployment | Railway, Render |

Hosting providers and APIs change; verify before committing. Building and deploying: nexus-prime. A simple scheduled task: schedule.
