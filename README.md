<div align="center">
  <img src="docs/assets/logo.png" alt="hccs logo" width="110">

# hccs

**One CLI for many Claude Code identities — Anthropic, GLM, and Codex — switch instantly.**

Create as many accounts as you need, log in once each, then jump between them without re-auth.
Use **real Claude** (Anthropic OAuth), **z.ai GLM** (API key), or **ChatGPT/Codex models inside the Claude Code harness** (Claudex via local CLIProxyAPI). Skills, agents, hooks, and session history stay shared; only credentials and provider endpoints change.

[![npm](https://img.shields.io/npm/v/%40hoangnn23%2Fhccs?color=cb3837&logo=npm)](https://www.npmjs.com/package/@hoangnn23/hccs)
[![CI](https://github.com/nhathoang0110/hccs/actions/workflows/ci.yml/badge.svg)](https://github.com/nhathoang0110/hccs/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-8b5cf6)
![Dependencies](https://img.shields.io/badge/runtime%20deps-none-10b981)

**English** | [Tiếng Việt](README.vi.md)

</div>

```sh
# Multi Claude (Anthropic) — login once per account, switch forever
hccs add work && hccs add personal
hccs work --resume
hccs personal -p "review this PR"

# Same Claude Code UI, different brains
hccs glm                    # z.ai GLM (API key)
hccs codex                  # OpenAI/Codex models via Claudex
hccs codex-work --resume    # another ChatGPT account, pinned

hccs list
hccs dashboard              # per-account tokens & API-equivalent cost
```

| You want… | Command pattern |
|-----------|-----------------|
| Several Anthropic subscriptions / teams | `hccs add <name>` → `hccs <name>` |
| GLM inside Claude Code | `hccs glm` (or `hccs add myglm --provider glm`) |
| Codex/GPT models inside Claude Code | `hccs codex-login` → `hccs codex` / `hccs codex-<slot>` |
| Switch without re-login | `hccs work` · `hccs glm` · `hccs codex-shuei` |
| Resume a past session | `hccs <any-account> --resume` (history is shared) |
| See spend per identity | `hccs dashboard` |

- 🔁 **Multi-account switcher** — as many identities as you need; auth once, switch forever  
- 🧠 **Three backends in one harness** — Anthropic Claude · GLM (z.ai) · Codex/ChatGPT (Claudex)  
- 🧰 **Full passthrough** — `hccs <account> [args...]` ≡ `claude [args...]` (`--resume`, `-c`, `-p`, …)  
- 🤝 **Shared workspace** — agents, skills, hooks, plugins, projects, session history  
- 📊 **Usage dashboard** — per-account attribution, including cross-account resume  
- 🧹 **Clean uninstall** — default Claude install left alone  

![hccs dashboard](docs/assets/dashboard-dark.png)

---

## Mental model

```text
                    ┌─────────────────────────────────────┐
                    │         Claude Code harness         │
                    │   tools · skills · hooks · resume   │
                    └──────────────┬──────────────────────┘
                                   │  hccs <account>
           ┌───────────────────────┼───────────────────────┐
           ▼                       ▼                       ▼
    Anthropic OAuth            z.ai GLM              ChatGPT / Codex
    (hccs work)              (hccs glm)            (hccs codex-*)
    multi Claude logins      API key once          multi OAuth slots
```

Every **hccs account** is a named profile under `~/.hccs/accounts/<name>`.  
Switching only changes **who authenticates** and **which API endpoint/models** run — not your project files or skill library.

| Account kind | Example names | Auth (once) | Models |
|--------------|---------------|-------------|--------|
| **Claude (OAuth)** | `work`, `personal` | Anthropic login in Claude | Claude family |
| **GLM (API key)** | `glm`, `myglm` | Paste z.ai key once | `glm-*` |
| **Codex / Claudex** | `codex`, `codex-work` | `hccs codex-login <slot>` | `gpt-5.6-sol` / `terra` / `luna` · … |

---

## Install

**npm:**

```sh
npm install -g @hoangnn23/hccs
hccs setup-hook      # once — attribution for the dashboard
```

**From source:**

```sh
git clone https://github.com/nhathoang0110/hccs.git && cd hccs
./install.sh         # ~/.local/bin + hook + dashboard assets + hccs-proxy.lib
```

**Requirements:** macOS or Linux, [`claude`](https://claude.com/claude-code) on `PATH`, `python3`.  
Codex path also needs network once to download [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) (managed under `~/.hccs/proxy`).

---

## Quick start

### 1) Multi Claude accounts (Anthropic)

```sh
hccs add work          # Claude prompts Anthropic login
hccs add personal

hccs work              # use work
hccs personal          # switch — no re-login
hccs work --resume     # continue a session (shared history pool)
hccs list
```

### 2) GLM inside Claude Code

```sh
hccs glm               # first run: paste z.ai API key (hidden)
hccs glm --resume
hccs add cheap --provider glm   # same preset, another name
hccs add-token glm              # rotate key
```

Key: [z.ai API keys](https://z.ai/manage-apikey/apikey-list).

### 3) Codex / ChatGPT models inside Claude Code (Claudex)

**Important:** each ChatGPT identity is a **proxy slot**. Importing `~/.codex/auth.json` twice with **y** copies the *same* login into two slots. For a *different* ChatGPT account, decline import and use browser OAuth, or change the active Codex CLI login before import.

```sh
# Slot = one ChatGPT identity (auth once per slot)
hccs codex-login default          # y = import current ~/.codex ; N = OAuth browser
hccs codex                        # account "codex" → pin slot default

hccs codex-login work             # N → login another ChatGPT
hccs codex-work                   # account "codex-work" → pin slot work
hccs codex-work --resume

# Explicit names
hccs add team --provider codex --slot work
hccs team

hccs proxy status|start|stop      # optional; auto-started when you enter a codex account
```

**Delete a mistaken slot** (OAuth files only; does not remove Anthropic accounts):

```sh
rm -rf ~/.hccs/proxy/auth/<slot>
# if you also created hccs account codex-<slot>:
hccs remove codex-<slot>
```

### 4) Day-to-day switching

```sh
hccs work                 # Claude / Anthropic
hccs glm                  # GLM
hccs codex-work           # Codex pin work
hccs which                # last used account
hccs dashboard            # costs & readiness (codex shows slot + email when ready)
```

Same flags everywhere: `--resume`, `-c`, `-p "…"`, `--model …`, etc.

---

## How it works

Claude Code respects `CLAUDE_CONFIG_DIR`. hccs sets that per account:

```text
~/.hccs/accounts/<name>/     # CLAUDE_CONFIG_DIR
├── .claude.json             # per-account identity
├── .credentials.json        # OAuth token (Linux; macOS uses Keychain)
├── .hccs-provider.json      # provider accounts only (glm / codex marker)
├── settings.json            # provider: real file (shared settings + overlay)
└── * → symlink into ~/.claude   # agents, skills, hooks, projects, history
```

| Kind | Credentials |
|------|-------------|
| Claude OAuth | Claude’s own slots (`Claude Code-credentials-<hash>` on macOS) |
| GLM | API key in Keychain / `.provider-token` → `ANTHROPIC_AUTH_TOKEN` |
| Codex | ChatGPT OAuth under `~/.hccs/proxy/auth/<slot>/`; local gateway key for Claude→proxy |

Provider accounts get a **composed** `settings.json` each switch (`ANTHROPIC_BASE_URL` + model maps). Shared edits in `~/.claude/settings.json` keep flowing in; writes *inside* a provider session do not stick (see Limitations).

Claudex flow:

```text
claude (via hccs codex-*)
  → ANTHROPIC_BASE_URL=http://127.0.0.1:8317
  → CLIProxyAPI (hccs-managed)
  → ChatGPT/Codex OAuth for the pinned slot
  → gpt-5.6-sol / terra / luna / …
```

---

## Commands

| Command | Description |
|---------|-------------|
| `hccs <account> [claude args…]` | Run Claude Code as that account (all flags pass through) |
| `hccs add <account>` | Create account + Anthropic login once |
| `hccs add <account> --provider glm` | Create GLM API-key account |
| `hccs add <account> --provider codex [--slot name]` | Create Claudex account pinned to a slot |
| `hccs add-token <account>` | Replace GLM (API-key) token — not used for codex |
| `hccs refresh-preset <account>` | Re-apply built-in preset env, keep credentials |
| `hccs codex-login [slot]` | Load ChatGPT OAuth into a proxy slot (`--import-codex-home` non-interactive) |
| `hccs proxy status\|start\|stop` | Manage local CLIProxyAPI |
| `hccs list` / `hccs which` | List accounts / show last used |
| `hccs remove <account>` | Delete account dir + its credentials (codex **slots** kept) |
| `hccs dashboard [--port N]` | Local usage & cost UI |
| `hccs setup-hook` | Register SessionStart attribution hook |
| `hccs uninstall` | Remove hccs data/binaries; default Claude untouched |
| `hccs -h` | Help |

Name shortcuts:

- `hccs glm` → first-run creates provider `glm`  
- `hccs codex` → account `codex`, slot `default`  
- `hccs codex-work` → account `codex-work`, slot `work`  

---

## Usage & cost dashboard

```sh
hccs dashboard       # http://127.0.0.1:4780 (localhost only)
```

Per-account tokens & **API-equivalent USD** (not subscription bills), 30-day chart, model breakdown, auth panel.

- **Claude / GLM cards:** login or API-key readiness  
- **Codex cards:** `ready` when gateway + slot OAuth exist; shows **slot + ChatGPT email**  
- Attribution via SessionStart hook → `~/.hccs/usage/attribution.jsonl` (works across `--resume`)  

Optional prices in `~/.hccs/pricing.json` (USD per 1M tokens: in, out, cache write 5m/1h, cache read):

```json
{
  "glm-5.2": [1.40, 4.40, 1.40, 1.40, 0.26],
  "glm-4.7": [0.60, 2.20, 0.60, 0.60, 0.11],
  "gpt-5.6-luna": [0, 0, 0, 0, 0]
}
```

Missing models show under the dashboard warning banner and cost **0** until priced.  
Cache: `~/.hccs/usage/cache.json` (`hccs-dashboard.py --rebuild` to rescan).

---

## Uninstall

```sh
hccs uninstall
```

Stops the local proxy, removes `~/.hccs` (including proxy OAuth slots and gateway keys), binaries, dashboard share files, PATH line, and the hccs SessionStart hook. Does **not** touch the rest of `~/.claude`, default Claude login, or `~/.codex`.

---

## Limitations

- **macOS + Linux only** (no Windows).  
- Per-account `.claude.json` is seeded once; later trust/MCP tweaks do not sync across accounts.  
- Provider / non-Anthropic base URL: MCP tool search & Remote Control off by default (`ENABLE_TOOL_SEARCH=true` can re-enable search).  
- Repo `.claude/settings.json` can override account settings (hccs warns if it sets `ANTHROPIC_*`).  
- Claudex is community-style routing through a local proxy — review OpenAI/Anthropic terms for your use case.  
- Shared history means `--resume` can send an Anthropic transcript to GLM or OpenAI when you resume under those accounts.

---

## Safety

- hccs **symlinks** from `~/.claude`; data lives under `~/.hccs`.  
- macOS Keychain deletes only **hash-suffixed** hccs slots — never the default `Claude Code-credentials` entry.  
- Dashboard binds `127.0.0.1` only; API never returns tokens.  
- Provider keys / gateway tokens sit in the process environment of claude and every child (hooks, MCP, Bash tool). Use keys you accept for that blast radius.  
- First switch into a provider account prints a one-time disclosure about shared history and env visibility.

---

## License

[MIT](LICENSE)
