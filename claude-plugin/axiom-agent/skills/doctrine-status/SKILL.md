---
name: doctrine-status
description: Report which of the nine Axiom Doctrine articles have an enabled enforcer plugin in this Claude Code install and which are advice only. Use only when the user asks for the doctrine status or enforcer state.
disable-model-invocation: true
license: MIT
---

# Doctrine status

Report, for each of the nine Axiom Doctrine articles, whether an enforcer plugin is enabled in this install. This skill only reports. It does not install, enable, disable or configure any plugin, and it does not block or approve anything.

## How to find the enabled plugins

Run `claude plugin list --json` once. It is read-only. Use only the plugin names and the enabled flag it returns. Do not open any plugin's files, settings or data.

If you cannot run it (the user declined, the command is missing, the output is not valid JSON), say so plainly and mark every article ADVISED. Unknown state is ADVISED, never ENFORCED.

## The enforcer names

An enforcer counts only when a plugin with exactly one of these names is listed and enabled. Do not match on similar names.

| No. | Article | Enforcer plugin name(s) |
|---|---|---|
| I | The chain of command | none (doctrine only) |
| II | The instruction boundary | none (doctrine only) |
| III | The gate | axiom-axioma, axiom-gatekeeper |
| IV | Proof over claims | axiom-standing |
| V | Trust is earned | axiom-standing |
| VI | Every refusal is recorded | axiom-tripwire |
| VII | Work is handed off, not dropped | axiom-handydandy |
| VIII | Messages follow the owner's rules | axiom-gatekeeper |
| IX | Secrets stay secret | none (doctrine only) |

Article III counts once when either enforcer is enabled; name both when both are. Articles I, II and IX are always ADVISED, so the most that can show as enforced is six of nine.

## What to print

One table with these columns: No., Article, Enforcer(s), State. State is ENFORCED when a matching plugin is enabled, otherwise ADVISED. Then these lines:

- `This plugin enforces nothing itself; ENFORCED means an enforcer plugin is enabled, not verified coverage.`
- `N of 9 enforced on this install`, with N counted from the table.

For each ADVISED article that has an enforcer name, you may add the install command in the form `claude plugin install <name>@<marketplace>` only if the user asks how to install it; do not run it.

ENFORCED is an install-state label, not a security claim. It does not check an enforcer's settings, health, scope or version, or whether any particular action would be stopped.
