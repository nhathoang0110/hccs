<div align="center">
  <img src="docs/assets/logo.png" alt="hccs logo" width="110">

# hccs

**Switch account Claude Code tức thì. Biết chính xác mỗi account tốn bao nhiêu.**

CLI mỏng bọc quanh [`claude`](https://claude.com/claude-code) — dùng chung một `~/.claude` (history, agents, skills, hooks), login tách riêng, kèm **dashboard usage & cost** per-account chạy local.

[![npm](https://img.shields.io/npm/v/%40hoangnn23%2Fhccs?color=cb3837&logo=npm)](https://www.npmjs.com/package/@hoangnn23/hccs)
[![CI](https://github.com/nhathoang0110/hccs/actions/workflows/ci.yml/badge.svg)](https://github.com/nhathoang0110/hccs/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-8b5cf6)
![Dependencies](https://img.shields.io/badge/runtime%20deps-none-10b981)

[English](README.md) | **Tiếng Việt**

</div>

```sh
hccs work --resume        # chạy claude dưới account "work", passthrough mọi flag
hccs personal -p "hi"     # account "personal" — không cần login lại
hccs glm                  # cũng vậy, nhưng đi qua z.ai/GLM bằng API key
hccs codex                # Claudex: harness Claude Code + model OpenAI/Codex (proxy local)
hccs dashboard            # usage & chi phí per-account, mở trong browser
```

- 🔁 **Switch tức thì** — mỗi account login một lần, sau đó `hccs <account>` là chạy
- 🧰 **Passthrough đầy đủ** — `hccs <account> [args...]` ≡ `claude [args...]` (`--resume`, `-c`, `-p`, ...)
- 🤝 **Share mọi thứ trừ auth** — agents, skills, hooks, settings, lịch sử session
- 🔌 **Provider khác** — `hccs glm` (API key z.ai) và `hccs codex` (ChatGPT/Codex qua CLIProxyAPI)
- 📊 **Trace chi phí chuẩn** — attribution per-account, đúng cả khi `--resume` chéo account
- 🧹 **Gỡ sạch** — setup Claude mặc định không bao giờ bị đụng

![hccs dashboard](docs/assets/dashboard-dark.png)

## Cơ chế

Claude Code hỗ trợ biến môi trường `CLAUDE_CONFIG_DIR`. Khi set, Claude tách **file `.claude.json`** (danh tính account) **và credential** riêng theo config dir.

`hccs` tận dụng đúng cơ chế built-in này: mỗi account là một config dir riêng dưới `~/.hccs/accounts/<name>`, và **symlink toàn bộ `~/.claude`** (agents, skills, hooks, commands, settings, projects, history) vào đó. Kết quả: **chỉ authen là tách riêng** — còn lại dùng chung, kể cả lịch sử session (`--resume` thấy được session của account khác).

```
~/.hccs/accounts/<account>/       # = CLAUDE_CONFIG_DIR
├── .claude.json                 # RIÊNG: danh tính (seed từ ~/.claude.json, bỏ oauthAccount)
├── .credentials.json            # RIÊNG: token (chỉ Linux — macOS dùng Keychain)
└── <mọi entry của ~/.claude>    # symlink → dùng chung
```

### Credential lưu ở đâu (theo OS)

| OS | Nơi lưu token | Hệ quả |
|----|---------------|--------|
| **macOS** | Keychain, slot `Claude Code-credentials-<sha256(configDir)[:8]>` | Nằm ngoài config dir → `remove`/`uninstall` phải xoá slot riêng (hccs tự làm) |
| **Linux** | File `<configDir>/.credentials.json` | Nằm trong config dir → tự cô lập, mất theo dir |
| **Provider account, macOS** | Keychain, slot `hccs-provider-<sha256(configDir)[:8]>` | Do hccs ghi; hash theo config dir nên hai `HCCS_HOME` không bao giờ đụng nhau |
| **Provider account, Linux** | File `<configDir>/.provider-token`, mode `600` | Mất theo dir |

Với account OAuth, `hccs` không bao giờ tự đọc/ghi token — Claude tự quản theo `CLAUDE_CONFIG_DIR`.
Với **provider account** thì có: API key bạn dán được lưu vào Keychain (hoặc file `600`) và export
thành `ANTHROPIC_AUTH_TOKEN` khi chạy claude. Nó không bao giờ được ghi vào `settings.json`, cũng
không bao giờ truyền qua tham số dòng lệnh.

## Provider account

Provider account chạy Claude Code qua một endpoint tương thích Anthropic bằng API key thay vì login
Anthropic. Mọi thứ còn lại vẫn như account hccs bình thường — vẫn chung agents, skills, hooks và
lịch sử session.

```sh
hccs glm                     # lần đầu hỏi API key z.ai, sau đó chạy thẳng
hccs glm --resume            # flag vẫn passthrough như thường
hccs add myglm --provider glm  # cùng preset nhưng đặt tên account khác
hccs add-token glm           # thay key khi bị xoay vòng hoặc thu hồi
hccs refresh-preset glm      # áp lại preset built-in sau khi nâng cấp hccs
```

Preset có sẵn:

| Preset | Backend | Auth |
|--------|---------|------|
| `glm` | API z.ai tương thích Anthropic | API key (hỏi một lần) |
| `codex` | [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) local → OAuth ChatGPT/Codex | `hccs codex-login` (import `~/.codex` hoặc OAuth browser) |

### Claudex (`hccs codex`)

Chạy **Claude Code** (tools, skills, `--resume`) với **model OpenAI** (`gpt-5.6-sol` / `terra` /
`luna`). hccs tải và quản lý CLIProxyAPI dưới `~/.hccs/proxy`, **pin** một slot OAuth ChatGPT
mỗi account, và **restart** proxy khi đổi pin.

```sh
hccs codex-login              # import ~/.codex hoặc OAuth → slot "default"
hccs codex                    # account "codex", slot default
hccs codex-login work         # ChatGPT khác → slot "work"
hccs codex-work --resume      # pin slot work (multi-account)
hccs proxy status|start|stop  # debug proxy (tự start khi vào codex)
```

**An toàn:** history session share giữa account — resume session Anthropic dưới `codex` sẽ gửi
transcript sang OpenAI qua proxy. Gateway key nằm trong env process (cùng blast radius provider
token khác). Đây là routing kiểu Claudex/community; tự kiểm tra điều khoản nhà cung cấp.
`hccs remove` chỉ xóa account hccs — giữ slot OAuth trong `~/.hccs/proxy/auth/`. Uninstall stop
proxy và xóa `~/.hccs` (không đụng `~/.codex`).

Lấy key GLM tại [z.ai](https://z.ai/manage-apikey/apikey-list).

**Khác biệt bên dưới.** Trong Claude Code, khối `env` của settings **thắng** biến môi trường của
tiến trình, nên endpoint và mapping model không thể chỉ export ra shell — chúng phải nằm trong
`settings.json` của chính account đó. Vì vậy provider account có một `settings.json` **thật**, được
compose lại mỗi lần switch từ `~/.claude/settings.json` dùng chung cộng với env của preset. Hooks,
permissions, statusline, plugin của bạn vẫn giữ nguyên; chỉ các key của provider được đắp lên trên.

```
~/.hccs/accounts/glm/
├── .claude.json          # danh tính per-account (không có oauthAccount)
├── .hccs-provider.json   # snapshot preset: endpoint và model nào
├── settings.json         # FILE THẬT: settings chung + env provider, compose lại mỗi lần switch
└── <mọi entry khác của ~/.claude>   # symlink, dùng chung như thường
```

Vì compose chạy lại mỗi lần switch, thay đổi trong `~/.claude/settings.json` vẫn chảy vào provider
account. Chiều ngược lại thì không — xem mục Giới hạn.

## Cài đặt

**Qua npm:**

```sh
npm install -g @hoangnn23/hccs
hccs setup-hook      # đăng ký hook attribution cho dashboard (một lần)
```

**Từ source:**

```sh
git clone <repo-này> && cd <thư-mục-repo>
./install.sh         # cài vào ~/.local/bin + tự đăng ký hook
```

**Yêu cầu:** macOS hoặc Linux, `claude` trong PATH, `python3`.
Ubuntu/Debian nếu thiếu: `sudo apt install python3`.

## Lệnh

| Lệnh | Mô tả |
|------|-------|
| `hccs <account> [claude args...]` | Chạy claude dưới account, passthrough mọi flag |
| `hccs add <account> [claude args]` | Tạo account mới rồi login một lần |
| `hccs add <account> --provider <preset>` | Tạo account dùng API key của provider (xem bên dưới) |
| `hccs add-token <account>` | Lưu hoặc thay API key của provider account |
| `hccs refresh-preset <account>` | Áp lại preset built-in, giữ nguyên key |
| `hccs list` | Liệt kê account + email |
| `hccs which` | Account dùng gần nhất |
| `hccs remove <account>` | Xoá account (config dir + credential) |
| `hccs dashboard [--port N]` | Mở dashboard usage/cost (localhost) |
| `hccs setup-hook` | Đăng ký (lại) SessionStart hook attribution |
| `hccs uninstall` | Gỡ sạch hccs, **không đụng** Claude mặc định |
| `hccs -h` \| `--help` | Trợ giúp |

## Bắt đầu nhanh

```sh
hccs add work        # tạo + login account "work"
hccs add personal    # tạo + login account "personal"

hccs work            # dùng account work
hccs personal        # đổi sang personal — KHÔNG cần login lại
hccs list            # xem account + email
```

Mỗi account login một lần duy nhất. Sau đó switch tức thì.

## Dashboard usage & chi phí

```sh
hccs dashboard       # mở http://127.0.0.1:4780 (headless thì in URL)
```

Trang localhost (chỉ bind `127.0.0.1`) hiển thị **chi phí + token per-account** (hôm nay / 7 ngày / 30 ngày / tất cả), đồ thị stacked 30 ngày (toggle cost ↔ tokens), bảng theo model, panel auth read-only. Có theme sáng/tối. Chi phí là **API-equivalent USD** (quy theo giá API Anthropic — không phải bill subscription).

**Attribution hoạt động thế nào:** transcript trong `~/.claude/projects` không chứa danh tính account, nên `install.sh` đăng ký một **SessionStart hook** (`hccs-attribution-hook`) vào `~/.claude/settings.json` (backup trước lần sửa đầu, gỡ sạch khi uninstall). Mỗi lần mở session, hook ghi `(thời điểm, session_id, account)` vào `~/.hccs/usage/attribution.jsonl`; dashboard attribute từng message theo mốc thời gian — đúng cả khi account khác `--resume` session cũ. Session không rõ nguồn hiển thị là *unattributed*.

- Máy đã cài hccs từ trước khi có dashboard? Chạy lại `./install.sh` (hoặc `hccs setup-hook`).
- Giá model override qua `~/.hccs/pricing.json`: `{"claude-x": [in, out, w5m, w1h, read]}` (USD/1M token). Model của provider không có trong bảng built-in — thêm giá ở đây, lấy đúng tên model từ cột breakdown trong dashboard. Giá list của z.ai:

  ```json
  {
    "glm-5.2": [1.40, 4.40, 1.40, 1.40, 0.26],
    "glm-4.7": [0.60, 2.20, 0.60, 0.60, 0.11]
  }
  ```

  Model nào vẫn thiếu giá sẽ hiện trong banner ⚠ trên dashboard và được tính là 0.
- Kết quả scan cache ở `~/.hccs/usage/cache.json` — mở lần sau gần như tức thì; `hccs-dashboard.py --rebuild` để scan lại từ đầu.
- Hook được bọc để **không bao giờ** làm hỏng/chậm claude startup (exit 0 vô điều kiện, không network).

## Gỡ cài đặt

```sh
hccs uninstall
```

Xoá `~/.hccs`, mọi Keychain token của account hccs, binary, dashboard (`~/.local/share/hccs`), dòng PATH, và gỡ SessionStart hook khỏi `settings.json` (chỉ đúng entry của hccs). **Không** chạm tới phần còn lại của `~/.claude`, `~/.claude.json`, hay account Claude mặc định.

## Giới hạn

- **macOS + Linux.** Chưa hỗ trợ Windows.
- `.claude.json` tách riêng mỗi account: seed từ account mặc định (giữ trust-dialog/MCP), nhưng thay đổi trust/MCP-per-project về sau không tự đồng bộ giữa các account.

Riêng provider account còn:

- **MCP tool search và Remote Control bị tắt.** Claude Code tự tắt cả hai khi `ANTHROPIC_BASE_URL` trỏ tới host không phải first-party. Đặt `ENABLE_TOOL_SEARCH=true` để bật lại cái đầu.
- **Settings sửa trong session provider không sống sót.** `settings.json` được compose lại từ file chung ở lần switch kế tiếp, nên permission grant hay thay đổi `/config` trong session provider sẽ mất. Muốn giữ thì đặt vào `~/.claude/settings.json`.
- **`.claude/settings.json` của repo xếp trên settings của account.** Claude Code ưu tiên project/local settings hơn user settings, nên một repo có thể chiếm `ANTHROPIC_BASE_URL`. hccs cảnh báo khi thấy, nhưng không ghi đè được. Flag `--settings` bạn tự truyền cũng vậy.
- Chi phí model `glm-*` hiển thị 0 cho tới khi bạn thêm giá vào `~/.hccs/pricing.json` — bảng giá built-in chỉ có model Anthropic.

## An toàn

- `hccs` chỉ **symlink** từ `~/.claude` (không ghi vào đó, trừ entry hook settings.json bạn đã đồng ý) và lưu dữ liệu trong `~/.hccs`.
- `uninstall`/`remove` chỉ đụng credential của account hccs: trên macOS chỉ xoá Keychain slot **có hash** (slot mặc định `Claude Code-credentials` không bao giờ bị đụng); trên Linux credential nằm trong config dir nên mất theo đúng account đó.
- `rm -rf ~/.hccs` chỉ xoá symlink, không follow vào `~/.claude`.
- Dashboard chỉ bind `127.0.0.1` và validate `Host` header (chống DNS-rebinding). API chỉ lộ email + số liệu usage, không bao giờ lộ token.

Hai điều nên biết trước khi dùng **provider account**. hccs in cả hai đúng một lần, ở lần đầu bạn
switch vào:

- **Lịch sử session dùng chung, nên `--resume` đi xuyên provider.** Đó chính là điểm hay của tính
  năng — nhưng resume một session vốn tạo ra với Anthropic sẽ gửi lại **toàn bộ transcript** tới
  endpoint của provider. Nếu một cuộc hội thoại có thứ bạn không muốn đưa cho bên thứ ba thì đừng
  resume nó dưới provider account.
- **API key hiện diện với mọi thứ claude khởi chạy.** Nó nằm trong biến môi trường của tiến trình,
  mà mọi hook, plugin, MCP server, lệnh statusline — và cả Bash tool của chính model — đều kế thừa.
  Đây là bản chất của cơ chế env-var mà các provider hướng dẫn; chỉ nên đưa vào provider account
  những key bạn chấp nhận để lộ với đám tooling đang cài.

## License

[MIT](LICENSE)
