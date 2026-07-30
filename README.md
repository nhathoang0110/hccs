<div align="center">
  <img src="docs/assets/logo.png" alt="hccs logo" width="110">

# hccs

**Switch Claude Code accounts instantly. Know exactly what each one spends.**

A thin wrapper around [`claude`](https://claude.com/claude-code) — one shared `~/.claude` (history, agents, skills, hooks), separate logins, and a local per-account **usage & cost dashboard**.

[![npm](https://img.shields.io/npm/v/%40hoangnn23%2Fhccs?color=cb3837&logo=npm)](https://www.npmjs.com/package/@hoangnn23/hccs)
[![CI](https://github.com/nhathoang0110/hccs/actions/workflows/ci.yml/badge.svg)](https://github.com/nhathoang0110/hccs/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-8b5cf6)
![Dependencies](https://img.shields.io/badge/runtime%20deps-none-10b981)

**English** | [Tiếng Việt](README.vi.md)

</div>

```sh
hccs work --resume        # run claude as account "work", every flag passes through
hccs personal -p "hi"     # account "personal" — no re-login
hccs glm                  # same, but through z.ai/GLM with an API key
hccs dashboard            # per-account usage & cost, in your browser
```

- 🔁 **Instant switching** — log in once per account, then `hccs <account>` just works
- 🧰 **Full passthrough** — `hccs <account> [args...]` ≡ `claude [args...]` (`--resume`, `-c`, `-p`, ...)
- 🤝 **Everything shared except auth** — agents, skills, hooks, settings, session history
- 🔌 **Other providers too** — `hccs glm` runs Claude Code against z.ai with an API key
- 📊 **Accurate cost tracking** — per-account attribution, correct even across cross-account `--resume`
- 🧹 **Clean uninstall** — your default Claude setup is never touched

![hccs dashboard](docs/assets/dashboard-dark.png)

## How it works

Claude Code supports the `CLAUDE_CONFIG_DIR` environment variable. When set, Claude keeps a separate **`.claude.json`** (account identity) **and separate credentials** per config dir.

`hccs` builds on exactly that built-in mechanism: each account is its own config dir under `~/.hccs/accounts/<name>`, with **everything in `~/.claude`** (agents, skills, hooks, commands, settings, projects, history) **symlinked in**. The result: **only authentication is separate** — everything else is shared, including session history (`--resume` sees sessions started under other accounts).

```
~/.hccs/accounts/<account>/       # = CLAUDE_CONFIG_DIR
├── .claude.json                 # PER-ACCOUNT: identity (seeded from ~/.claude.json, minus oauthAccount)
├── .credentials.json            # PER-ACCOUNT: token (Linux only — macOS uses the Keychain)
└── <every entry of ~/.claude>   # symlink → shared
```

### Where credentials live (per OS)

| OS | Token storage | Consequence |
|----|---------------|-------------|
| **macOS** | Keychain, slot `Claude Code-credentials-<sha256(configDir)[:8]>` | Outside the config dir → `remove`/`uninstall` must delete the slot (hccs does) |
| **Linux** | File `<configDir>/.credentials.json` | Inside the config dir → isolated automatically, removed with the dir |
| **Provider accounts, macOS** | Keychain, slot `hccs-provider-<sha256(configDir)[:8]>` | Written by hccs; hashed on the config dir so two `HCCS_HOME` trees never collide |
| **Provider accounts, Linux** | File `<configDir>/.provider-token`, mode `600` | Removed with the dir |

For OAuth accounts `hccs` never reads or writes tokens — Claude manages them per
`CLAUDE_CONFIG_DIR`. For **provider accounts** it does: the API key you paste is stored in the
Keychain (or a `600` file) and exported as `ANTHROPIC_AUTH_TOKEN` when launching claude. It is never
written into `settings.json`, and never passed as a command-line argument.

## Provider accounts

A provider account runs Claude Code against an Anthropic-compatible endpoint using an API key
instead of an Anthropic login. Everything else still behaves like a normal hccs account — same
shared agents, skills, hooks, and session history.

```sh
hccs glm                     # first run asks for the z.ai API key, then just runs
hccs glm --resume            # flags pass through as usual
hccs add myglm --provider glm  # same preset under a different account name
hccs add-token glm           # replace a rotated or revoked key
hccs refresh-preset glm      # re-apply the built-in preset after an hccs upgrade
```

Available presets: `glm` (z.ai — `https://api.z.ai/api/anthropic`, GLM-4.7/5.2). Get a key at
[z.ai](https://z.ai/manage-apikey/apikey-list).

**How it differs under the hood.** A settings `env` block outranks the process environment in
Claude Code, so the endpoint and model mapping cannot simply be exported — they have to live in the
account's own `settings.json`. hccs therefore gives a provider account a **real** `settings.json`,
recomposed on every switch from your shared `~/.claude/settings.json` plus the preset's env. Your
hooks, permissions, statusline, and plugins carry over; only the provider keys are layered on top.

```
~/.hccs/accounts/glm/
├── .claude.json          # per-account identity (no oauthAccount)
├── .hccs-provider.json   # preset snapshot: which endpoint and models
├── settings.json         # REAL file: shared settings + provider env, recomposed each switch
└── <every other entry of ~/.claude>   # symlinked, shared as usual
```

Because the composition re-runs on every switch, edits to `~/.claude/settings.json` keep flowing
into provider accounts. The reverse is not true — see Limitations.

## Install

**Via npm:**

```sh
npm install -g @hoangnn23/hccs
hccs setup-hook      # register the dashboard attribution hook (once)
```

**From source:**

```sh
git clone <this-repo> && cd <repo-dir>
./install.sh         # installs into ~/.local/bin + registers the hook
```

**Requirements:** macOS or Linux, `claude` in PATH, `python3`.
On Ubuntu/Debian: `sudo apt install python3` if missing.

## Commands

| Command | Description |
|---------|-------------|
| `hccs <account> [claude args...]` | Run claude as the account, all flags pass through |
| `hccs add <account> [claude args]` | Create a new account, then log in once |
| `hccs add <account> --provider <preset>` | Create an API-key account for a provider (see below) |
| `hccs add-token <account>` | Store or replace a provider account's API key |
| `hccs refresh-preset <account>` | Re-apply the built-in preset, keeping the key |
| `hccs list` | List accounts and emails |
| `hccs which` | Most recently used account |
| `hccs remove <account>` | Delete an account (config dir + credentials) |
| `hccs dashboard [--port N]` | Open the usage/cost dashboard (localhost) |
| `hccs setup-hook` | (Re-)register the SessionStart attribution hook |
| `hccs uninstall` | Remove hccs completely, **default Claude untouched** |
| `hccs -h` \| `--help` | Help |

## Quick start

```sh
hccs add work        # create + log in account "work"
hccs add personal    # create + log in account "personal"

hccs work            # use account work
hccs personal        # switch to personal — NO re-login
hccs list            # accounts + emails
```

Each account logs in once. After that, switching is instant.

## Usage & cost dashboard

```sh
hccs dashboard       # opens http://127.0.0.1:4780 (prints the URL when headless)
```

A localhost page (bound to `127.0.0.1` only) showing **per-account cost and tokens** (today / 7 days / 30 days / all time), a 30-day stacked chart (cost ↔ tokens toggle), a per-model breakdown, and a read-only auth panel. Light and dark themes. Costs are **API-equivalent USD** (computed from Anthropic API prices — not your subscription bill).

**How attribution works:** transcripts in `~/.claude/projects` carry no account identity, so `install.sh` registers a **SessionStart hook** (`hccs-attribution-hook`) in `~/.claude/settings.json` (backed up before the first edit, fully removed on uninstall). On every session start the hook appends `(timestamp, session_id, account)` to `~/.hccs/usage/attribution.jsonl`; the dashboard attributes each message by time interval — correct even when another account `--resume`s an existing session. Sessions with unknown origin are shown as *unattributed*.

- Machine installed before the dashboard existed? Run `./install.sh` again (or `hccs setup-hook`).
- Model prices can be overridden via `~/.hccs/pricing.json`: `{"claude-x": [in, out, w5m, w1h, read]}` (USD per 1M tokens). Provider models are not in the built-in table — price them here, using the exact model name from the dashboard's per-model breakdown. For z.ai list prices:

  ```json
  {
    "glm-5.2": [1.40, 4.40, 1.40, 1.40, 0.26],
    "glm-4.7": [0.60, 2.20, 0.60, 0.60, 0.11]
  }
  ```

  Anything still missing a price is listed under the ⚠ banner on the dashboard and counted as 0.
- Scan results are cached in `~/.hccs/usage/cache.json` — subsequent opens are near-instant; `hccs-dashboard.py --rebuild` rescans from scratch.
- The hook is wrapped so it can **never** fail or slow down claude startup (unconditional exit 0, no network).

## Uninstall

```sh
hccs uninstall
```

Removes `~/.hccs`, every hccs account's Keychain token, the binaries, the dashboard (`~/.local/share/hccs`), the PATH line, and the SessionStart hook from `settings.json` (only the hccs entry). Does **not** touch the rest of `~/.claude`, `~/.claude.json`, or the default Claude account.

## Limitations

- **macOS + Linux.** No Windows support.
- `.claude.json` is per-account: it is seeded from the default account (keeping trust dialogs/MCP), but later per-project trust/MCP changes do not sync between accounts.

Provider accounts additionally:

- **MCP tool search and Remote Control are off.** Claude Code disables both when `ANTHROPIC_BASE_URL` points at a non-first-party host. Set `ENABLE_TOOL_SEARCH=true` to re-enable the former.
- **Settings written inside a provider session do not survive.** `settings.json` is recomposed from the shared file on the next switch, so a permission grant or `/config` change made in a provider session is dropped. Put anything you want to keep in `~/.claude/settings.json`.
- **A repo's `.claude/settings.json` outranks the account's.** Claude Code ranks project and local settings above user settings, so a repo can capture `ANTHROPIC_BASE_URL`. hccs warns when it sees that, but cannot override it. The same applies to a `--settings` flag you pass yourself.
- Cost for `glm-*` models shows as 0 until you add prices to `~/.hccs/pricing.json` — the built-in table only covers Anthropic models.

## Safety

- `hccs` only **symlinks** from `~/.claude` (it never writes there except the opt-in settings.json hook entry) and keeps its data in `~/.hccs`.
- `uninstall`/`remove` only touch hccs account credentials: on macOS only the **hash-suffixed** Keychain slots are deleted (the default `Claude Code-credentials` slot is never touched); on Linux credentials live inside the account dir and are removed with it.
- `rm -rf ~/.hccs` removes symlinks only — it never follows them into `~/.claude`.
- The dashboard binds `127.0.0.1` only and validates the `Host` header (DNS-rebinding protection). The API exposes emails and usage numbers, never tokens.

Two things worth knowing before you use a **provider account**. hccs prints both once, the first time
you switch into one:

- **Session history is shared, so `--resume` crosses providers.** That is the point of the feature —
  but resuming a session that was created against Anthropic replays its **entire transcript** to the
  provider's endpoint. If a conversation contains something you would not send to a third party,
  don't resume it under a provider account.
- **The API key is visible to everything claude starts.** It lives in the process environment, which
  every hook, plugin, MCP server, statusline command — and the model's own Bash tool — inherits.
  This is inherent to the env-var mechanism the providers document; only give a provider account keys
  you are willing to expose to the tooling you have installed.

## License

[MIT](LICENSE)
