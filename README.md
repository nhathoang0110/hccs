# hccs — Claude Code account switcher

**English** | [Tiếng Việt](README.vi.md)

A thin CLI wrapper around [`claude`](https://claude.com/claude-code) that lets you **switch between multiple Claude Code accounts without re-authenticating**, plus a local **usage & cost dashboard** with accurate per-account attribution.

```sh
hccs work --resume        # run claude as account "work", every flag passes through
hccs personal -p "hi"     # account "personal"
hccs dashboard            # per-account usage & cost, in your browser
```

`hccs <account> [args...]` is equivalent to `claude [args...]` — `--resume`, `-c`, `-p`, everything works — it just runs under the account you picked.

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

`hccs` never reads or writes tokens itself — Claude manages them per `CLAUDE_CONFIG_DIR`.

## Install

```sh
git clone <this-repo> && cd <repo-dir>
./install.sh
```

Installs `hccs` into `~/.local/bin`, registers the dashboard attribution hook, and adds the PATH line if needed. Open a new terminal afterwards.

**Requirements:** macOS or Linux, `claude` in PATH, `python3`.
On Ubuntu/Debian: `sudo apt install python3` if missing.

## Commands

| Command | Description |
|---------|-------------|
| `hccs <account> [claude args...]` | Run claude as the account, all flags pass through |
| `hccs add <account> [claude args]` | Create a new account, then log in once |
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
- Model prices can be overridden via `~/.hccs/pricing.json`: `{"claude-x": [in, out, w5m, w1h, read]}` (USD per 1M tokens).
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

## Safety

- `hccs` only **symlinks** from `~/.claude` (it never writes there except the opt-in settings.json hook entry) and keeps its data in `~/.hccs`.
- `uninstall`/`remove` only touch hccs account credentials: on macOS only the **hash-suffixed** Keychain slots are deleted (the default `Claude Code-credentials` slot is never touched); on Linux credentials live inside the account dir and are removed with it.
- `rm -rf ~/.hccs` removes symlinks only — it never follows them into `~/.claude`.
- The dashboard binds `127.0.0.1` only and validates the `Host` header (DNS-rebinding protection). The API exposes emails and usage numbers, never tokens.

## License

[MIT](LICENSE)
