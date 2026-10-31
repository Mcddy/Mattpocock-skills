# Failure branches

Read when a delivery surface cannot run a server, a codebase or brand already exists, extra architecture is requested, a model output triggers an action, a check cannot run, or the craft test fails.

- **The delivery place cannot run a server.** Say so first. Offer what is true: a Demo that keeps state in the page and says it will not persist; the host's own storage if this session has it; or the full app as files to run elsewhere. Never present typed-in data as a working back end.
- **There is an existing codebase or brand.** Read its structure, conventions and tokens first and follow them. Its tokens fill the kit's token names and win over every direction (skip Stop B unless the user asks for options); its existing architecture is the recommended option at Stop A unless it cannot meet a requirement. Don't introduce a second way of doing something it already does.
- **The user asks for more architecture than the scope needs.** Build it, mark each component "requested", route the slice through it, note the running cost in one line.
- **A model's output will trigger an action.** Treat it as untrusted input: parse, validate against a schema, bound it, act only on an allowed set, with a timeout and a spending ceiling (`references/backend.md`).
- **A check cannot run here.** Report its status (runner_error, or partial for the part that did not run) with the command. Do not describe the result you expect.
- **The page passes the scripts and fails the craft test.** It is not done. Say which question failed and fix the composition or the words.
