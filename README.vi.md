<div align="center">
  <img src="docs/assets/logo.png" alt="hccs logo" width="110">

# hccs

**Một CLI cho nhiều identity Claude Code — Anthropic, GLM và Codex — switch tức thì.**

Tạo bao nhiêu account cũng được, login mỗi cái một lần, rồi nhảy qua lại không re-auth.
Dùng **Claude thật** (OAuth Anthropic), **GLM z.ai** (API key), hoặc **model ChatGPT/Codex trong harness Claude Code** (Claudex qua CLIProxyAPI local). Skills, agents, hooks, history session vẫn share; chỉ credential và endpoint đổi.

[![npm](https://img.shields.io/npm/v/%40hoangnn23%2Fhccs?color=cb3837&logo=npm)](https://www.npmjs.com/package/@hoangnn23/hccs)
[![CI](https://github.com/nhathoang0110/hccs/actions/workflows/ci.yml/badge.svg)](https://github.com/nhathoang0110/hccs/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-8b5cf6)
![Dependencies](https://img.shields.io/badge/runtime%20deps-none-10b981)

[English](README.md) | **Tiếng Việt**

</div>

```sh
# Nhiều acc Claude (Anthropic) — login 1 lần / acc, switch mãi
hccs add work && hccs add personal
hccs work --resume
hccs personal -p "review PR này"

# Cùng UI Claude Code, backend khác nhau
hccs glm                    # z.ai GLM (API key)
hccs codex                  # model OpenAI/Codex (Claudex)
hccs codex-work --resume    # ChatGPT acc khác, đã pin

hccs list
hccs dashboard              # token & cost quy đổi API per-account
```

| Bạn muốn… | Cách dùng |
|-----------|-----------|
| Nhiều subscription / team Anthropic | `hccs add <tên>` → `hccs <tên>` |
| GLM trong Claude Code | `hccs glm` (hoặc `hccs add myglm --provider glm`) |
| Model Codex/GPT trong Claude Code | `hccs codex-login` → `hccs codex` / `hccs codex-<slot>` |
| Switch không login lại | `hccs work` · `hccs glm` · `hccs codex-shuei` |
| Resume session cũ | `hccs <account bất kỳ> --resume` (history share) |
| Xem chi tiêu theo identity | `hccs dashboard` |

- 🔁 **Multi-account** — bao nhiêu identity cũng được; auth một lần, switch mãi  
- 🧠 **Ba backend một harness** — Claude Anthropic · GLM (z.ai) · Codex/ChatGPT (Claudex)  
- 🧰 **Passthrough đầy đủ** — `hccs <account> [args...]` ≡ `claude [args...]`  
- 🤝 **Workspace chung** — agents, skills, hooks, plugins, projects, history  
- 📊 **Dashboard usage** — attribution per-account, kể cả resume chéo  
- 🧹 **Uninstall sạch** — Claude mặc định không bị đụng  

![hccs dashboard](docs/assets/dashboard-dark.png)

---

## Mô hình tư duy

```text
                    ┌─────────────────────────────────────┐
                    │         Harness Claude Code         │
                    │   tools · skills · hooks · resume   │
                    └──────────────┬──────────────────────┘
                                   │  hccs <account>
           ┌───────────────────────┼───────────────────────┐
           ▼                       ▼                       ▼
    OAuth Anthropic            z.ai GLM              ChatGPT / Codex
    (hccs work)              (hccs glm)            (hccs codex-*)
    nhiều login Claude       API key 1 lần         nhiều OAuth slot
```

Mỗi **account hccs** là profile dưới `~/.hccs/accounts/<tên>`.  
Switch chỉ đổi **ai authen** và **endpoint/model** — không đổi source project hay skill library.

| Loại account | Ví dụ tên | Auth (1 lần) | Model |
|--------------|-----------|--------------|--------|
| **Claude (OAuth)** | `work`, `personal` | Login Anthropic trong Claude | Claude family |
| **GLM (API key)** | `glm`, `myglm` | Dán key z.ai một lần | `glm-*` |
| **Codex / Claudex** | `codex`, `codex-work` | `hccs codex-login <slot>` | `gpt-5.6-sol` / `terra` / `luna` · … |

---

## Cài đặt

**npm:**

```sh
npm install -g @hoangnn23/hccs
hccs setup-hook      # một lần — attribution cho dashboard
```

**Từ source:**

```sh
git clone https://github.com/nhathoang0110/hccs.git && cd hccs
./install.sh         # ~/.local/bin + hook + dashboard + hccs-proxy.lib
```

**Cần có:** macOS hoặc Linux, [`claude`](https://claude.com/claude-code) trong `PATH`, `python3`.  
Đường Codex lần đầu cần mạng để tải [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) (hccs quản trong `~/.hccs/proxy`).

---

## Bắt đầu nhanh

### 1) Nhiều account Claude (Anthropic)

```sh
hccs add work          # Claude hỏi login Anthropic
hccs add personal

hccs work              # dùng work
hccs personal          # switch — không login lại
hccs work --resume     # tiếp session (pool history chung)
hccs list
```

### 2) GLM trong Claude Code

```sh
hccs glm               # lần đầu: dán API key z.ai (ẩn)
hccs glm --resume
hccs add cheap --provider glm
hccs add-token glm     # xoay key
```

Key: [z.ai API keys](https://z.ai/manage-apikey/apikey-list).

### 3) Codex / ChatGPT trong Claude Code (Claudex)

**Quan trọng:** mỗi identity ChatGPT = một **proxy slot**.  
Import `~/.codex/auth.json` hai lần với **y** = copy **cùng một** login vào hai slot.  
Muốn ChatGPT **khác**: chọn **N** (OAuth browser), hoặc đổi login Codex CLI rồi mới import.

```sh
# Slot = một ChatGPT (auth 1 lần / slot)
hccs codex-login default          # y = import ~/.codex ; N = OAuth browser
hccs codex                        # account "codex" → pin slot default

hccs codex-login work             # N → login ChatGPT khác
hccs codex-work                   # account "codex-work" → pin slot work
hccs codex-work --resume

hccs add team --provider codex --slot work
hccs team

hccs proxy status|start|stop      # tuỳ chọn; tự start khi vào account codex
```

**Xóa slot lỡ import:**

```sh
rm -rf ~/.hccs/proxy/auth/<slot>
hccs remove codex-<slot>   # nếu đã tạo account hccs tương ứng
```

### 4) Switch hàng ngày

```sh
hccs work                 # Claude / Anthropic
hccs glm                  # GLM
hccs codex-work           # Codex pin work
hccs which
hccs dashboard            # cost + trạng thái (codex hiện slot + email khi ready)
```

Flag giống nhau: `--resume`, `-c`, `-p "…"`, `--model …`, …

---

## Cơ chế

Claude Code tôn trọng `CLAUDE_CONFIG_DIR`. hccs set per account:

```text
~/.hccs/accounts/<tên>/      # CLAUDE_CONFIG_DIR
├── .claude.json             # identity per-account
├── .credentials.json        # OAuth (Linux; macOS dùng Keychain)
├── .hccs-provider.json      # chỉ provider (glm / codex)
├── settings.json            # provider: file thật (settings chung + overlay)
└── * → symlink ~/.claude    # agents, skills, hooks, projects, history
```

| Loại | Credential |
|------|------------|
| Claude OAuth | Slot Claude (`Claude Code-credentials-<hash>` trên macOS) |
| GLM | API key Keychain / `.provider-token` → `ANTHROPIC_AUTH_TOKEN` |
| Codex | OAuth ChatGPT trong `~/.hccs/proxy/auth/<slot>/` + gateway key local |

Provider: mỗi lần switch **compose** lại `settings.json` (`ANTHROPIC_BASE_URL` + map model).  
Sửa `~/.claude/settings.json` vẫn chảy vào; ghi *trong* session provider không bền (xem Giới hạn).

Luồng Claudex:

```text
claude (qua hccs codex-*)
  → ANTHROPIC_BASE_URL=http://127.0.0.1:8317
  → CLIProxyAPI (hccs quản)
  → OAuth ChatGPT của slot đang pin
  → gpt-5.6-sol / terra / luna / …
```

---

## Lệnh

| Lệnh | Mô tả |
|------|--------|
| `hccs <account> [claude args…]` | Chạy Claude Code với account đó (passthrough flag) |
| `hccs add <account>` | Tạo account + login Anthropic một lần |
| `hccs add <account> --provider glm` | Account GLM (API key) |
| `hccs add <account> --provider codex [--slot tên]` | Account Claudex pin slot |
| `hccs add-token <account>` | Đổi key GLM — **không** dùng cho codex |
| `hccs refresh-preset <account>` | Áp lại preset built-in, giữ credential |
| `hccs codex-login [slot]` | Nạp OAuth ChatGPT vào slot (`--import-codex-home` non-interactive) |
| `hccs proxy status\|start\|stop` | Quản CLIProxyAPI local |
| `hccs list` / `hccs which` | Liệt kê / account vừa dùng |
| `hccs remove <account>` | Xóa account (slot codex **giữ**) |
| `hccs dashboard [--port N]` | UI usage & cost local |
| `hccs setup-hook` | Đăng ký hook attribution |
| `hccs uninstall` | Gỡ hccs; Claude mặc định nguyên |
| `hccs -h` | Help |

Shortcut tên:

- `hccs glm` → tạo provider `glm` lần đầu  
- `hccs codex` → account `codex`, slot `default`  
- `hccs codex-work` → account `codex-work`, slot `work`  

---

## Dashboard usage & cost

```sh
hccs dashboard       # http://127.0.0.1:4780 (chỉ localhost)
```

Token & **USD quy đổi API** (không phải bill subscription), chart 30 ngày, breakdown model, auth panel.

- **Claude / GLM:** trạng thái login / API key  
- **Codex:** `ready` khi có gateway + OAuth slot; hiện **slot + email ChatGPT**  
- Attribution qua SessionStart hook → `~/.hccs/usage/attribution.jsonl`  

Giá tuỳ chọn `~/.hccs/pricing.json` (USD / 1M token: in, out, cache write 5m/1h, cache read):

```json
{
  "glm-5.2": [1.40, 4.40, 1.40, 1.40, 0.26],
  "glm-4.7": [0.60, 2.20, 0.60, 0.60, 0.11],
  "gpt-5.6-luna": [0, 0, 0, 0, 0]
}
```

Model thiếu giá = 0 + banner cảnh báo. Cache: `~/.hccs/usage/cache.json`.

---

## Gỡ cài

```sh
hccs uninstall
```

Stop proxy, xóa `~/.hccs` (kể cả slot OAuth + gateway), binary, share dashboard, dòng PATH, hook SessionStart.  
**Không** đụng phần còn lại của `~/.claude`, login Claude mặc định, hay `~/.codex`.

---

## Giới hạn

- **Chỉ macOS + Linux.**  
- `.claude.json` per-account seed một lần; trust/MCP sau đó không sync chéo account.  
- Base URL không-Anthropic: MCP tool search & Remote Control tắt mặc định.  
- `.claude/settings.json` của repo có thể đè settings account (hccs cảnh báo nếu set `ANTHROPIC_*`).  
- Claudex là routing kiểu community qua proxy local — tự xem ToS OpenAI/Anthropic.  
- History share → `--resume` session Anthropic dưới GLM/Codex = gửi transcript sang provider đó.

---

## An toàn

- hccs **symlink** từ `~/.claude`; data nằm `~/.hccs`.  
- Keychain macOS chỉ xóa slot **có hash** của hccs — không đụng `Claude Code-credentials` mặc định.  
- Dashboard chỉ bind `127.0.0.1`; API không trả token.  
- Key/gateway nằm trong env process của claude và mọi con (hooks, MCP, Bash tool).  
- Lần đầu vào provider account in disclosure một lần (history share + env).

---

## License

[MIT](LICENSE)
