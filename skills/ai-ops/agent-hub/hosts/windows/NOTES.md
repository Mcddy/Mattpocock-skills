# agent-hub on Windows (Shaun's desktop)

Host-specific facts for the agent-hub skill. Nothing here applies on another machine.

## Workspace folder

`C:\Users\Shaun\Desktop\07_🗺️_SYSTEM\_AGENT_WORKSPACE`

Use this path as the workspace folder when `SKILL.md` asks for one.

## Machines

The workspace's `CONTEXT/MACHINES.md` refers to two machines by short name:

- S1: Windows, where commands run as Windows commands.
- S2: Linux, where commands run as Linux commands.

Cowork cannot execute on S1 or S2. Anything needing a real command on either machine is never a Cowork task.

## Agent log

Real work on his machines is logged by appending to `ChatGPT/Projects/codex-agent-registry/README.md` inside the workspace folder.
