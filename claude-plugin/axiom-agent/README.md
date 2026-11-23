# Axiom Agent for Claude Code

The Axiom Doctrine is nine plain rules about who gives an agent orders, which actions need a yes, and what counts as done. This plugin puts the doctrine in front of Claude Code as two skills. It enforces nothing.

It is the Claude Code counterpart of [Axiom Agent for Hermes Agent](https://github.com/percyhendrux123-prog/hermes-axiom-agent). The doctrine text is the same text, copied word for word from [`DOCTRINE.md`](https://github.com/percyhendrux123-prog/hermes-axiom-agent/blob/main/DOCTRINE.md) in that repository.

## What is in it

| Skill | Command | What it does |
|---|---|---|
| `doctrine` | `/axiom-agent:doctrine` | Carries the nine articles. Claude can load it on its own when a task involves sending, spending, publishing, deploying, deleting, secrets, or text that tells it to act. You can also run it to read the doctrine, or name one article: `/axiom-agent:doctrine 3`. |
| `doctrine-status` | `/axiom-agent:doctrine-status` | You run it. Claude lists which articles have an enforcer plugin enabled in this install and which are advice only. |

## The nine articles

| No. | Article | Enforcer |
|---|---|---|
| I | The chain of command | None: doctrine only |
| II | The instruction boundary | None: doctrine only |
| III | The gate | axiom-axioma or axiom-gatekeeper |
| IV | Proof over claims | axiom-standing |
| V | Trust is earned | axiom-standing |
| VI | Every refusal is recorded | axiom-tripwire |
| VII | Work is handed off, not dropped | axiom-handydandy |
| VIII | Messages follow the owner's rules | axiom-gatekeeper |
| IX | Secrets stay secret | None: doctrine only |

The full text is in [`skills/doctrine/SKILL.md`](skills/doctrine/SKILL.md). A test checks that it contains the repository's `DOCTRINE.md` unchanged.

`ENFORCED` in the status report is an install-state label, not a security claim. It means a plugin with the listed name is installed and enabled. It does not check that plugin's settings, health, scope or version, or whether any particular action would be stopped. Articles I, II and IX stay advice only, so six of nine is the most the report can show.

The enforcer names above follow the `axiom-<name>` convention. At the time of writing only `axiom-tripwire` has shipped as a Claude Code plugin; the others are the names the matching ports are expected to use. The status skill matches those exact names only, so a plugin under a different name counts as not found.

## Before you install

- **Files it writes:** none.
- **Files it reads:** none. The status skill runs `claude plugin list --json`, a read-only listing, and uses only plugin names and enabled flags. It opens no plugin's files, settings or data.
- **Network, background processes, hooks, scripts, MCP servers, telemetry, stored credentials:** none. The plugin is two `SKILL.md` files and an icon.
- **Requires:** Claude Code. No Python, no Hermes.

## Install

```
claude plugin marketplace add percyhendrux123-prog/hermes-axiom-agent
claude plugin install axiom-agent@deploy-axiom-agent
```

To try it for one session without installing:

```
claude --plugin-dir ./claude-plugin/axiom-agent
```

## Known gaps

The Hermes plugin does things a skills-only plugin cannot. These are not reproduced, and this version does not claim parity.

- **No per-turn injection.** Hermes appends the doctrine to every model turn. A skill loads when Claude judges it relevant or when you run it, so on a turn where Claude does not load it, the doctrine is not in view. There is no setting for a compact or full form.
- **The status report is Claude's reading, not a probe.** Hermes asks its runtime whether each enforcer is loaded. Here Claude reads `claude plugin list --json` and fills in the table, so the result depends on Claude following the skill. If the command cannot run, every article is reported ADVISED.
- **No installed-but-disabled detection.** Only plugins that are listed and enabled count.
- **No owner additions file.** Hermes reads an optional `doctrine.local.md`. This version has no equivalent.
- **No `/doctrine plugins` listing of install commands.** The status skill mentions install commands only if you ask.
- **Skills are advice.** A model can ignore a skill. Nothing here blocks, approves or changes a tool call.

## What it will not do

- Block or approve any tool or model call.
- Enforce the instruction boundary, approvals, proof, trust, messaging rules or secrecy.
- Install enforcers or change their settings.
- Write files, make network calls or run background work.
- Make any setup safe, compliant or correct merely by adding doctrine text.

## Eligibility for Anthropic's plugin directory

The plugin has no hooks, scripts, mods or MCP servers, which are the components the directory refuses from unverified organizations. `claude plugin validate --strict --profile directory` passes on it. The directory also runs a safety scan and policy review that the local command does not, so this is not a prediction of the portal's result.

## Try it with no install

```
python3 -m unittest discover -s claude-plugin/tests
```

The tests check the manifests, that the plugin contains no hooks, scripts or servers, that the skill's doctrine text matches the repository's `DOCTRINE.md` byte for byte, and that the status skill's enforcer table matches the table in `DOCTRINE.md`. They use no network and write nothing.

## Undo

Run `claude plugin uninstall axiom-agent` and, if you added the marketplace, `claude plugin marketplace remove deploy-axiom-agent`. The plugin wrote nothing, so there is nothing else to delete.

## How it was made

I designed it, set the rules for what it may do, and tested it on my own system. AI agents wrote the files under my spec and review. I read Python; I don't claim to write it by hand.

Percy Keith, Deploy Axiom. MIT license. The doctrine text is dedicated to the public domain under [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/), as in the Hermes repository.
