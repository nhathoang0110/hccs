#!/usr/bin/env python3
"""hccs-dashboard — usage engine + web server for hccs.

Reads the shared transcript pool ~/.claude/projects/**/*.jsonl, attributes
every message to an account via ~/.hccs/usage/attribution.jsonl (written by
the SessionStart hook), prices usage with the Anthropic API price table
(USD, "API-equivalent" — if you are on a subscription this is NOT your real
bill), and serves a localhost dashboard.

Python 3.9+ stdlib only. Usage:
  hccs-dashboard.py --summary        # print the aggregated JSON (test/debug)
  hccs-dashboard.py --rebuild        # drop the cache and rescan everything
  hccs-dashboard.py serve [--port N] # HTTP server for the dashboard UI
"""
import bisect
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from datetime import datetime

HCCS_HOME = os.environ.get("HCCS_HOME") or os.path.expanduser("~/.hccs")
CLAUDE_DIR = os.environ.get("HCCS_CLAUDE_DIR") or os.path.expanduser("~/.claude")
PROJECTS_DIR = os.path.join(CLAUDE_DIR, "projects")
USAGE_DIR = os.path.join(HCCS_HOME, "usage")
CACHE_PATH = os.path.join(USAGE_DIR, "cache.json")
ATTR_PATH = os.path.join(USAGE_DIR, "attribution.jsonl")
PRICING_PATH = os.path.join(HCCS_HOME, "pricing.json")
CACHE_VERSION = 1

# ── Pricing ──────────────────────────────────────────────────────────────────
# USD per 1M tokens: (input, output, cache_write_5m, cache_write_1h, cache_read)
# Anthropic standard: cache write 5m = input*1.25, 1h = input*2, read = input*0.1.
# Override/extend via ~/.hccs/pricing.json: {"model": [in, out, w5m, w1h, read]}.
PRICING = {
    "claude-fable-5":     (10.0, 50.0, 12.5, 20.0, 1.0),
    "claude-mythos-5":    (10.0, 50.0, 12.5, 20.0, 1.0),
    "claude-opus-5":      (5.0, 25.0, 6.25, 10.0, 0.5),
    "claude-opus-4-8":    (5.0, 25.0, 6.25, 10.0, 0.5),
    "claude-opus-4-7":    (5.0, 25.0, 6.25, 10.0, 0.5),
    # 4-6 needs its own row: without it the prefix match falls back to
    # "claude-opus-4" and prices it at the 4.0 rate — 3x too high.
    "claude-opus-4-6":    (5.0, 25.0, 6.25, 10.0, 0.5),
    "claude-opus-4-5":    (5.0, 25.0, 6.25, 10.0, 0.5),
    "claude-opus-4-1":    (15.0, 75.0, 18.75, 30.0, 1.5),
    "claude-opus-4":      (15.0, 75.0, 18.75, 30.0, 1.5),
    "claude-sonnet-5":    (3.0, 15.0, 3.75, 6.0, 0.3),
    "claude-sonnet-4-5":  (3.0, 15.0, 3.75, 6.0, 0.3),
    "claude-sonnet-4":    (3.0, 15.0, 3.75, 6.0, 0.3),
    "claude-3-7-sonnet":  (3.0, 15.0, 3.75, 6.0, 0.3),
    "claude-haiku-4-5":   (1.0, 5.0, 1.25, 2.0, 0.1),
    "claude-3-5-haiku":   (0.8, 4.0, 1.0, 1.6, 0.08),
}


def load_pricing():
    table = dict(PRICING)
    try:
        with open(PRICING_PATH) as f:
            override = json.load(f)
        for model, rates in override.items():
            if isinstance(rates, list) and len(rates) == 5:
                table[model] = tuple(float(x) for x in rates)
    except FileNotFoundError:
        pass
    except Exception as e:
        print("hccs-dashboard: ignoring invalid pricing.json: %s" % e, file=sys.stderr)
    return table


def rates_for(model, table):
    """Rates for a model, matched progressively: exact → date suffix stripped →
    longest prefix. No match → None (caller flags it unpriced, cost 0 — never
    a silent guess)."""
    if model in table:
        return table[model]
    # claude-sonnet-5-20260203 → claude-sonnet-5
    parts = model.rsplit("-", 1)
    if len(parts) == 2 and parts[1].isdigit() and len(parts[1]) == 8 and parts[0] in table:
        return table[parts[0]]
    best = None
    for key in table:
        if model.startswith(key + "-") and (best is None or len(key) > len(best)):
            best = key
    return table[best] if best else None


# ── Helpers ──────────────────────────────────────────────────────────────────
def parse_ts(ts):
    """ISO-8601 UTC ('...Z') → epoch seconds. Invalid → None.
    Note: on python 3.9 fromisoformat only accepts 3- or 6-digit fractions —
    Claude currently writes milliseconds (3 digits) so this is fine; messages
    with unknown formats are skipped."""
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def local_date(epoch):
    # Bucket by the user's LOCAL day (matches intuition) even though the
    # transcripts store UTC.
    return datetime.fromtimestamp(epoch).strftime("%Y-%m-%d")


def atomic_write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".cache.")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    os.replace(tmp, path)


# ── Scan + cache ─────────────────────────────────────────────────────────────
# The cache stores RAW per-message tuples (not attributed buckets): attribution
# can change retroactively without touching transcript mtimes, so aggregation
# must re-run from raw data every time — cheap (in-memory), always correct.
# Tuple: [key, ts, session_id, model, input, output, cache_w5m, cache_w1h, cache_read]

def parse_file(path):
    msgs = []
    with open(path, "r", errors="replace") as f:
        for lineno, line in enumerate(f):
            if '"assistant"' not in line:  # fast pre-filter before json.loads
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue  # corrupt/partial line → skip; mtime change triggers a rescan
            if e.get("type") != "assistant":
                continue
            msg = e.get("message") or {}
            usage = msg.get("usage")
            if not isinstance(usage, dict):
                continue
            ts = parse_ts(e.get("timestamp") or "")
            if ts is None:
                continue
            sid = e.get("sessionId") or os.path.splitext(os.path.basename(path))[0]
            mid, rid = msg.get("id"), e.get("requestId")
            # Dedup key: message.id:requestId; if missing → the entry uuid (not
            # dedupable but still counted once); as a last resort path:lineno.
            key = ("%s:%s" % (mid, rid)) if (mid and rid) else (e.get("uuid") or "%s:%d" % (path, lineno))
            cc = usage.get("cache_creation")
            if isinstance(cc, dict):
                c5 = cc.get("ephemeral_5m_input_tokens") or 0
                c1 = cc.get("ephemeral_1h_input_tokens") or 0
            else:
                # older transcripts only carry the total → treat as 5m (the
                # cheaper rate, never inflates the estimate)
                c5, c1 = usage.get("cache_creation_input_tokens") or 0, 0
            msgs.append([
                key, ts, sid, msg.get("model") or "unknown",
                usage.get("input_tokens") or 0, usage.get("output_tokens") or 0,
                c5, c1, usage.get("cache_read_input_tokens") or 0,
            ])
    return msgs


def scan(rebuild=False, progress=True):
    """Returns (files_dict, scan_ms, parsed_count). files_dict: path → {size, mtime, msgs}."""
    t0 = time.time()
    cache = {"version": CACHE_VERSION, "files": {}}
    if not rebuild:
        try:
            with open(CACHE_PATH) as f:
                loaded = json.load(f)
            if loaded.get("version") == CACHE_VERSION:
                cache = loaded
        except Exception:
            pass
    old = cache["files"]
    new_files = {}
    todo = []
    for root, _dirs, names in os.walk(PROJECTS_DIR):
        for name in names:
            if not name.endswith(".jsonl"):
                continue
            path = os.path.join(root, name)
            try:
                st = os.stat(path)
            except OSError:
                continue
            ent = old.get(path)
            if ent and ent.get("size") == st.st_size and ent.get("mtime") == st.st_mtime:
                new_files[path] = ent
            else:
                todo.append((path, st))
    for i, (path, st) in enumerate(sorted(todo)):
        if progress and len(todo) > 5:
            print("\rhccs-dashboard: scanning %d/%d" % (i + 1, len(todo)), end="", file=sys.stderr)
        new_files[path] = {"size": st.st_size, "mtime": st.st_mtime, "msgs": parse_file(path)}
    if progress and len(todo) > 5:
        print("", file=sys.stderr)
    if todo or set(old) - set(new_files):  # anything changed (incl. deleted files) → rewrite cache
        atomic_write_json(CACHE_PATH, {"version": CACHE_VERSION, "files": new_files})
    return new_files, int((time.time() - t0) * 1000), len(todo)


# ── Attribution ──────────────────────────────────────────────────────────────
def load_attribution():
    """session_id → ([ts...] sorted, [account...]) for time-based bisect lookup."""
    raw = {}
    try:
        with open(ATTR_PATH) as f:
            for line in f:
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                ts = parse_ts(e.get("ts") or "")
                sid, acc = e.get("session_id"), e.get("account")
                if ts is None or not sid or not acc:
                    continue
                raw.setdefault(sid, []).append((ts, acc))
    except FileNotFoundError:
        pass
    out = {}
    for sid, entries in raw.items():
        entries.sort()
        out[sid] = ([t for t, _ in entries], [a for _, a in entries])
    return out


def resolve_account(attr, sid, ts):
    """Account = the LAST attribution entry with ts <= message ts (correct for
    cross-account --resume). A message earlier than every entry (slight clock
    skew) falls back to the first entry."""
    ent = attr.get(sid)
    if not ent:
        return "unattributed"
    times, accounts = ent
    i = bisect.bisect_right(times, ts)
    return accounts[i - 1] if i > 0 else accounts[0]


# ── Aggregation ──────────────────────────────────────────────────────────────
ZERO = ("input", "output", "cache_w5m", "cache_w1h", "cache_read")


def cost_of(row, rates):
    if rates is None:
        return 0.0
    return sum(row[k] * r for k, r in zip(ZERO, rates)) / 1e6


def aggregate(files):
    attr = load_attribution()
    pricing = load_pricing()
    seen = set()
    buckets = {}          # (account, date, model) → sums
    unattr_sessions = set()
    total_msgs = 0
    for path in sorted(files):
        for key, ts, sid, model, tin, tout, c5, c1, cr in files[path]["msgs"]:
            if key in seen:
                continue  # duplicate from a session fork/copy → count once
            seen.add(key)
            total_msgs += 1
            acc = resolve_account(attr, sid, ts)
            if acc == "unattributed":
                unattr_sessions.add(sid)
            b = buckets.setdefault((acc, local_date(ts), model), {
                "input": 0, "output": 0, "cache_w5m": 0, "cache_w1h": 0,
                "cache_read": 0, "msgs": 0, "last_ts": 0.0,
            })
            b["input"] += tin; b["output"] += tout
            b["cache_w5m"] += c5; b["cache_w1h"] += c1; b["cache_read"] += cr
            b["msgs"] += 1
            if ts > b["last_ts"]:
                b["last_ts"] = ts
    unpriced = set()
    for (acc, date, model), b in buckets.items():
        rates = rates_for(model, pricing)
        if rates is None and any(b[k] for k in ZERO):
            unpriced.add(model)
        b["cost"] = round(cost_of(b, rates), 6)
    return buckets, {
        "unattributed_sessions": len(unattr_sessions),
        "unpriced_models": sorted(unpriced),
        "total_msgs": total_msgs,
        "file_count": len(files),
    }


# ── Account info ─────────────────────────────────────────────────────────────
def _email_of(claude_json_path):
    try:
        with open(claude_json_path) as f:
            return json.load(f).get("oauthAccount", {}).get("emailAddress")
    except Exception:
        return None


def _keychain_slot(cfgdir):
    # Matches hccs/cli.js: "Claude Code-credentials-" + sha256(configDir)[:8]
    return "Claude Code-credentials-" + hashlib.sha256(cfgdir.encode()).hexdigest()[:8]


def _provider_of(cfgdir):
    """Preset name of a provider account, or None. The marker must be a real
    file — same rule as hccs is_provider(): every ~/.claude entry is symlinked
    into each account, so a planted symlink must not pass as provider state."""
    path = os.path.join(cfgdir, ".hccs-provider.json")
    if os.path.islink(path) or not os.path.isfile(path):
        return None
    try:
        with open(path) as f:
            return json.load(f).get("provider") or None
    except Exception:
        return None


def _provider_slot(cfgdir):
    # Matches hccs provider_slot(): "hccs-provider-" + sha256(configDir)[:8]
    return "hccs-provider-" + hashlib.sha256(cfgdir.encode()).hexdigest()[:8]


def _has_provider_token(cfgdir):
    if platform.system() == "Darwin":
        r = subprocess.run(
            ["security", "find-generic-password", "-a", os.environ.get("USER", ""),
             "-s", _provider_slot(cfgdir)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return r.returncode == 0
    return os.path.exists(os.path.join(cfgdir, ".provider-token"))


def _has_credentials(cfgdir):
    """cfgdir=None → the 'default' account (unsuffixed Keychain slot)."""
    if platform.system() == "Darwin":
        slot = "Claude Code-credentials" if cfgdir is None else _keychain_slot(cfgdir)
        r = subprocess.run(
            ["security", "find-generic-password", "-a", os.environ.get("USER", ""), "-s", slot],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return r.returncode == 0
    base = CLAUDE_DIR if cfgdir is None else cfgdir
    return os.path.exists(os.path.join(base, ".credentials.json"))


def list_accounts(buckets):
    """Cards: hccs accounts + default + other:* (seen in usage). 'unattributed'
    gets NO card — it only appears in the meta footnote."""
    accounts = {}
    acc_dir = os.path.join(HCCS_HOME, "accounts")
    if os.path.isdir(acc_dir):
        for name in sorted(os.listdir(acc_dir)):
            cfg = os.path.join(acc_dir, name)
            if not os.path.isdir(cfg):
                continue
            prov = _provider_of(cfg)
            accounts[name] = {
                "name": name,
                "kind": "provider" if prov else "hccs",
                "provider": prov,
                # A provider account authenticates with an API key, so it has no
                # oauthAccount and "logged_in" means "an API key is stored".
                "email": None if prov else _email_of(os.path.join(cfg, ".claude.json")),
                "logged_in": _has_provider_token(cfg) if prov else _has_credentials(cfg),
                # Claude Code does not document how ANTHROPIC_AUTH_TOKEN behaves
                # when the config dir also holds an OAuth login. Surface it —
                # matching hccs has_oauth(): a stored credential OR a leftover
                # identity block in .claude.json both count.
                "oauth_mixed": bool(prov and (
                    _has_credentials(cfg)
                    or _email_of(os.path.join(cfg, ".claude.json"))
                )),
            }
    accounts["default"] = {
        "name": "default", "kind": "default",
        "email": _email_of(os.path.expanduser("~/.claude.json")),
        "logged_in": _has_credentials(None),
    }
    for (acc, _d, _m) in buckets:
        if acc.startswith("other:") and acc not in accounts:
            accounts[acc] = {"name": acc, "kind": "other", "email": None, "logged_in": None}
    return accounts


# ── Summary (API payload) ────────────────────────────────────────────────────
def build_summary(rebuild=False, progress=True):
    files, scan_ms, parsed = scan(rebuild=rebuild, progress=progress)
    buckets, meta = aggregate(files)
    accounts = list_accounts(buckets)

    today = local_date(time.time())
    d7 = local_date(time.time() - 6 * 86400)
    d30 = local_date(time.time() - 29 * 86400)

    def blank():
        return {"input": 0, "output": 0, "cache_w5m": 0, "cache_w1h": 0,
                "cache_read": 0, "msgs": 0, "cost": 0.0}

    def add(dst, b):
        for k in ("input", "output", "cache_w5m", "cache_w1h", "cache_read", "msgs"):
            dst[k] += b[k]
        dst["cost"] = round(dst["cost"] + b["cost"], 6)

    acc_totals = {}   # acc → {today,d7,d30,all,last_ts}
    daily = {}        # date → acc → {cost, tokens, output}
    by_model = {}
    unattr_tot = blank()
    for (acc, date, model), b in buckets.items():
        if acc == "unattributed":
            add(unattr_tot, b)
        else:
            t = acc_totals.setdefault(acc, {"today": blank(), "d7": blank(),
                                            "d30": blank(), "all": blank(), "last_ts": 0.0})
            add(t["all"], b)
            if date >= d30:
                add(t["d30"], b)
            if date >= d7:
                add(t["d7"], b)
            if date == today:
                add(t["today"], b)
            if b["last_ts"] > t["last_ts"]:
                t["last_ts"] = b["last_ts"]
            if date >= d30:
                d = daily.setdefault(date, {}).setdefault(acc, {"cost": 0.0, "tokens": 0, "output": 0})
                d["cost"] = round(d["cost"] + b["cost"], 6)
                d["tokens"] += sum(b[k] for k in ZERO)
                d["output"] += b["output"]
        m = by_model.setdefault(model, blank())
        add(m, b)

    out_accounts = []
    for name, info in accounts.items():
        t = acc_totals.get(name, {"today": blank(), "d7": blank(), "d30": blank(),
                                  "all": blank(), "last_ts": 0.0})
        info.update(t)
        info["last_used"] = (datetime.fromtimestamp(t["last_ts"]).strftime("%Y-%m-%d %H:%M")
                             if t["last_ts"] else None)
        del info["last_ts"]
        out_accounts.append(info)
    # accounts that only exist in usage data (e.g. removed ones) still get a card
    for name, t in acc_totals.items():
        if name not in accounts:
            out_accounts.append({"name": name, "kind": "removed", "email": None,
                                 "logged_in": None, "today": t["today"], "d7": t["d7"],
                                 "d30": t["d30"], "all": t["all"],
                                 "last_used": datetime.fromtimestamp(t["last_ts"]).strftime("%Y-%m-%d %H:%M") if t["last_ts"] else None})
    out_accounts.sort(key=lambda a: -a["all"]["cost"])

    meta.update({
        "unattributed": unattr_tot,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "scan_ms": scan_ms, "files_parsed": parsed,
        "pricing_note": "API-equivalent USD (not your subscription bill)",
    })
    return {
        "accounts": out_accounts,
        "daily": [{"date": d, "accounts": daily[d]} for d in sorted(daily)],
        "by_model": {m: v for m, v in sorted(by_model.items(), key=lambda kv: -kv[1]["cost"])},
        "meta": meta,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────
def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    if argv[0] == "--summary":
        print(json.dumps(build_summary(), indent=2, ensure_ascii=False))
        return 0
    if argv[0] == "--rebuild":
        s = build_summary(rebuild=True)
        print("rebuild done: %d files, %d msgs, scanned in %dms" % (
            s["meta"]["file_count"], s["meta"]["total_msgs"], s["meta"]["scan_ms"]))
        return 0
    if argv[0] == "serve":
        return serve(argv[1:])
    print("hccs-dashboard: unknown command %r (use --summary | --rebuild | serve)" % argv[0],
          file=sys.stderr)
    return 1


def serve(args):
    import argparse
    import webbrowser
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    p = argparse.ArgumentParser(prog="hccs dashboard")
    p.add_argument("--port", type=int, default=4780)
    p.add_argument("--no-open", action="store_true", help="do not open the browser")
    ns = p.parse_args(args)
    # UI file: next to this script (install.sh layout) or in ./dashboard
    # (repo/npm package layout).
    here = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(here, "index.html")
    if not os.path.exists(html_path):
        html_path = os.path.join(here, "dashboard", "index.html")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            # Reject DNS rebinding: only accept localhost/127.0.0.1 Host headers.
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            if host not in ("127.0.0.1", "localhost", "[::1]", ""):
                self.send_error(403, "invalid host")  # reason must be ASCII (latin-1 status line)
                return
            if self.path in ("/", "/index.html"):
                try:
                    with open(html_path, "rb") as f:
                        body = f.read()
                except OSError:
                    self.send_error(500, "index.html missing - run ./install.sh again")
                    return
                self._send(200, "text/html; charset=utf-8", body)
            elif self.path == "/api/data":
                body = json.dumps(build_summary(progress=False),
                                  ensure_ascii=False).encode()
                self._send(200, "application/json; charset=utf-8", body)
            else:
                self.send_error(404)

        def _send(self, code, ctype, body):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):  # quiet — no terminal spam
            pass

    httpd = None
    for i in range(10):  # port busy → try +1, up to 10 times
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", ns.port + i), Handler)
            break
        except OSError:
            continue
    if httpd is None:
        print("hccs-dashboard: could not bind any port in %d..%d" % (ns.port, ns.port + 9),
              file=sys.stderr)
        return 1
    url = "http://127.0.0.1:%d" % httpd.server_address[1]
    print("hccs dashboard: %s  (Ctrl+C to stop)" % url)
    if not ns.no_open:
        try:
            webbrowser.open(url)  # headless/SSH: fails silently, URL printed above
        except Exception:
            pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
