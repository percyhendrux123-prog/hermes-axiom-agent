# SPEC: hermes-axiom-agent v0.1.0

Plugin name: `hermes-axiom-agent`. Title: "Axiom Agent". Author: Percy Keith Stewart. License: MIT (code); DOCTRINE.md CC0.
Install line for docs: `hermes plugins install hermes-axiom-agent`.

## What it is (one sentence)
It installs the Axiom Doctrine (DOCTRINE.md, nine articles) into a Hermes agent, and shows the owner which articles are enforced on this install and which are advice only.

## Why
Hermes setups have tools, memory, schedules and sub-agents, but no shared order those parts obey. The five governance plugins (standing, hermes-axioma, tripwire, handydandy, hermes-gatekeeper) each enforce one part. This plugin is the map: the rules, plus an honest report of which walls are actually standing.

## Features (v0.1.0)
1. **Doctrine in context.** `pre_llm_call` hook returns `{'context': <compact doctrine>}` (same mechanism as hermes-ref/example-axioma-__init__.py line 70). Compact form: the axiom line + the nine articles as one short line each, plus one line per article saying ENFORCED (plugin name) or ADVISED. Hard cap 1,800 characters; a test asserts the cap. Text is built from DOCTRINE.md shipped inside the package (single source of truth; a test asserts every article heading in DOCTRINE.md appears in the compact form).
2. **`/doctrine` command** (register_command). Subcommands:
   - `/doctrine` (default `status`): table of the nine articles: number, title, enforcer plugin(s), state = `ENFORCED` (an enforcer is installed and enabled), `ADVISED` (doctrine only, or no enforcer installed). Article III counts as ENFORCED if either enforcer is present, and lists which. End with a one-line count, e.g. `5 of 9 enforced on this install`.
   - `/doctrine show [n]`: full text of the doctrine or of article n.
   - `/doctrine plugins`: the five enforcer plugins with installed/enabled state and the install line for any missing one.
   Detect plugin state through Hermes's public plugin API only (read hermes-ref/developer-guide-plugins and the example plugins; if no public API exposes other plugins' enabled state, read the documented config/plugins location read-only, and document that in README). Never import another plugin's code.
3. **Owner additions.** Optional owner file `<HERMES_HOME>/axiom-agent/doctrine.local.md`: extra articles the owner writes (numbered X, XI ...). Appended to the compact context (still under a separate 800-char cap, truncated with a note) and shown by `/doctrine show`. Missing file = fine. Use `get_hermes_home()` (or the documented equivalent), never a hardcoded path.
4. **Config** (plugin config, documented): `inject: true|false` (default true), `form: compact|full` (default compact; full still capped at 4,000 chars).

## Hard rules
- The plugin enforces nothing itself and says so in README, `/doctrine` footer, and catalog description. It never blocks or approves a tool call. No `pre_tool_call` hook.
- No network calls, no subprocess, no model calls, no file writes (v0.1.0 is read-only; it reads its own package files, the optional owner file, and plugin state).
- No private or personal content: no names of people other than the author line, no client names, no phone numbers, no internal agent names (no "AXIOM", "Lily", card codes, profile names like appbuilder/codereview), no local paths from any real machine. Tests and examples use invented data.
- Python 3.10+ syntax; pytest with `-W error`; tests for: compact build + caps, article parity with DOCTRINE.md, status table for each combination of enforcers present/absent (mock the plugin-state reader), owner file present/absent/oversized/unreadable, inject off, command parsing incl. bad args.
- Files: plugin.yaml (name, version 0.1.0, description, author, hooks/commands declared as the developer guide requires), `__init__.py` register(ctx), package dir `axiom_agent/`, DOCTRINE.md (copy, byte-identical to repo root), README.md, CHANGELOG.md, LICENSE (MIT, Percy Keith Stewart), CATALOG-ENTRY.yaml draft (shape from hermes-ref/plugin-catalog.md + catalog-submission.md; `sha: TBD`, maintainer `percyhendrux123-prog`), tests/.
- README shape: what it does (3 lines), the nine articles as a table with enforcer column, install, `/doctrine` sample output, what it will not do, the five enforcer plugins with install lines, contributor path. Plain English, no hype words, no emojis.
- Remove `hermes-ref/` and SPEC.md from the final tree (they are scaffold); keep a clean public history is NOT required, but the final commit must not contain them. If a refusal gate blocks the delete, leave them and say so in the review request.
- Commit after each module. No push, no PR, no install into any real Hermes home.

## Done =
`pytest -q -W error` all green on 3.10 and the newest Python available; then `kanban_request_review` with the commit list, test summary, and any open questions.
