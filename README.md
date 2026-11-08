# Axiom Agent

Adds the nine-article Axiom Doctrine to each Hermes model turn.
Reports which articles have a loaded, enabled enforcer and which are advice only.
This plugin enforces nothing itself.

## The nine articles

| No. | Article | Enforcer |
|---|---|---|
| I | The chain of command | None: doctrine only |
| II | The instruction boundary | None: doctrine only |
| III | The gate | hermes-axioma or hermes-gatekeeper; the report lists which |
| IV | Proof over claims | standing |
| V | Trust is earned | standing |
| VI | Every refusal is recorded | tripwire |
| VII | Work is handed off, not dropped | handydandy |
| VIII | Messages follow the owner's rules | hermes-gatekeeper |
| IX | Secrets stay secret | None: doctrine only |

[Read the complete doctrine](DOCTRINE.md). The root copy and the shipped
`axiom_agent/DOCTRINE.md` are byte-identical. Compact context extracts sentences
and action labels from that file; it does not maintain a separate wording source.

## Install

Requires Python 3.10+ and Hermes's documented plugin context APIs.
Once the catalog entry is admitted:

```sh
hermes plugins install hermes-axiom-agent
hermes plugins enable hermes-axiom-agent
```

Installing this plugin does not install or enable any enforcer.

## Commands

- `/doctrine` or `/doctrine status`: nine-article install-state table.
- `/doctrine show`: the complete shipped doctrine, followed by owner additions.
- `/doctrine show 3` or `/doctrine show III`: the full text of one canonical article.
- `/doctrine plugins`: installed/enabled state and install commands for missing enforcers.

Example with none of the enforcers loaded:

```text
No. | Article | Enforcer(s) | State
I | The chain of command | none (doctrine only) | ADVISED
II | The instruction boundary | none (doctrine only) | ADVISED
III | The gate | hermes-axioma, hermes-gatekeeper | ADVISED
IV | Proof over claims | standing | ADVISED
V | Trust is earned | standing | ADVISED
VI | Every refusal is recorded | tripwire | ADVISED
VII | Work is handed off, not dropped | handydandy | ADVISED
VIII | Messages follow the owner's rules | hermes-gatekeeper | ADVISED
IX | Secrets stay secret | none (doctrine only) | ADVISED
This plugin enforces nothing itself; ENFORCED means an enforcer is loaded and enabled, not verified coverage.
0 of 9 enforced on this install
```

`ENFORCED` is an install-state label required by the doctrine, **not a security
claim**. It does not verify an enforcer's settings, health, scope, version or
whether any particular action would be stopped. Article III counts once when
either enforcer is loaded; both names appear when both are loaded. The maximum
is six of nine: articles I, II and IX always remain ADVISED. Unknown runtime
state is treated as ADVISED, never as proof of enforcement.

### How plugin state is read

Enabled state comes only from the public `ctx.has_plugin()` runtime probe.
Standing is checked under both its catalog name `standing` and manifest name
`hermes-standing`. The probe is refreshed for every report and injected turn,
not during registration while other plugins may still be loading.

There is no documented context API for inventorying disabled plugins. To report
installed state, the plugin reads manifest metadata, without importing code,
from the documented `<HERMES_HOME>/plugins/` location: flat packages and one
category level, `plugin.yaml` or `plugin.yml`. It never reads another plugin's
settings, credentials or data. A loaded runtime probe also proves installation,
including pip/bundled plugins. An inactive pip/bundled install cannot be
inventoried this way; `not found` means not found in the user-plugin metadata,
not proof of absence everywhere. Unreadable, malformed, non-regular or oversized
metadata is reported conservatively as unknown. Manifest reads are limited to
65,536 characters each, and at most 1,024 directory entries are inspected per
report. A symlinked plugin directory (for example a development checkout) is
followed, as Hermes follows it; a symlinked manifest file is never read. Every
file is checked on the opened descriptor, so a swap between check and read is
refused. Manifests that use YAML anchors, aliases or merge keys, or more than 256
flow collections, are reported as unknown without being parsed. Inside Hermes,
manifests are parsed with Hermes' own safe YAML loader, so the plugin declares
no Python dependencies. No config file is rewritten and no directory is created.

### Configuration

Set these values through Hermes plugin settings or the plugin's namespace in
`config.yaml`:

```yaml
plugins:
  entries:
    hermes-axiom-agent:
      settings:
        inject: true
        form: compact
```

`inject` defaults to `true`; `false` disables context injection, not `/doctrine`.
`form` is `compact` (default) or `full`. Compact canonical context is capped at
1,800 characters; full canonical context at 4,000, including a truncation note
when needed. Both forms include current article states. Invalid settings or an
unavailable settings reader skip injection, without blocking the turn.

The `pre_llm_call` hook returns only `{'context': text}`. Hermes appends that to
the current turn's user message; it is not a system-prompt replacement.

### Owner additions

The owner may create `<HERMES_HOME>/axiom-agent/doctrine.local.md`, for example:

```markdown
## X. Local review
Show evidence before sharing a result.

## XI. Plain language
Explain the next step without jargon.
```

The active home is resolved with `hermes_constants.get_hermes_home()`, never a
fixed path or an environment guess. The plugin does not create this file.
Additions are appended as owner-authored text, separate from the nine canonical
articles. They do not change enforcement counts or acquire an ENFORCED label.
Their entire injected section, including its label and truncation note, has a
separate 800-character cap. `/doctrine show` displays the owner file without the
context cap; `show n` selects only canonical articles I–IX. A missing or empty
file is fine. An unreadable or non-regular file (including a symbolic link, or an
`axiom-agent` folder that is a symbolic link) produces a brief notice without
exposing error details. Keep secrets and private
material out of additions: the text is sent
to the model as context by Hermes.

## What it will not do

- Block or approve any tool or model call. There is no `pre_tool_call` hook.
- Enforce the instruction boundary, approvals, proof, trust, messaging rules or secrecy.
- Import or run another plugin's code, install enforcers or change their settings.
- Make network, subprocess or model calls, start background work or write files.
- Read credentials, message history, tool output or unrelated owner files.
- Make any setup safe, compliant or correct merely by adding doctrine text.

## Enforcer plugins

These are separate plugins with their own limits and configuration:

| Plugin | Install |
|---|---|
| [standing](https://hermes-agent.nousresearch.com/docs/plugins/standing) | `hermes plugins install standing` |
| [hermes-axioma](https://hermes-agent.nousresearch.com/docs/plugins/hermes-axioma) | `hermes plugins install hermes-axioma` |
| [tripwire](https://hermes-agent.nousresearch.com/docs/plugins/tripwire) | `hermes plugins install tripwire` |
| [handydandy](https://hermes-agent.nousresearch.com/docs/plugins/handydandy) | `hermes plugins install handydandy` |
| [hermes-gatekeeper](https://hermes-agent.nousresearch.com/docs/plugins/hermes-gatekeeper) | `hermes plugins install hermes-gatekeeper` |

Enable a plugin explicitly after installing it. This package never does so.

## Contributor path

Work in a local checkout. `axiom_agent/doctrine.py` reads articles and extracts
compact rules; `context.py` handles caps and additions; `state.py` probes the
public host API and reads metadata; `service.py` serves the command and hook.
The root `__init__.py` only registers those surfaces.

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q -W error
hermes plugins validate .
hermes plugins doctor . --ci
```

Run pytest on Python 3.10 and the newest available Python. Host shims in tests
are not native Hermes validation: run validate and doctor with Hermes too, then
exercise a model turn and `/doctrine` using a throwaway home, never a real one.
Use invented data and keep local review output out of the public source tree.
Changes to doctrine wording need explicit review; keep both copies identical.
`CATALOG-ENTRY.yaml` is a draft: replace `sha: TBD` with the reviewed full commit
before submitting it. Nothing in this repository publishes or updates itself.

## License

Code: MIT, see [LICENSE](LICENSE). Both copies of `DOCTRINE.md` are dedicated to
the public domain under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/).
