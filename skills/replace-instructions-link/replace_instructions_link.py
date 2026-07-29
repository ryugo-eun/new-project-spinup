#!/usr/bin/env python3
"""Replace an instructions-doc link inside RL Studio world layouts.

Cloned Sparta worlds inherit the OLD Vigil instructions Google-Doc link inside
`instructions_card` modules, in BOTH world_settings.module_layout and
module_layout_draft. This tool finds an old string (a Google-Doc ID, or a full
URL) and replaces it with the vertical's own, preserving all other world_settings.

Auth: reads RLS_API_KEY from the environment (source ~/Desktop/MERCOR/.env.local
first: `set -a; . ~/Desktop/MERCOR/.env.local; set +a`). Never prints the key.
Company/account default to the shared Sparta Studio ids; override with
RLS_COMPANY_ID / RLS_ACCOUNT_ID. Base URL: RLS_BASE_URL (default prod).

GOTCHA: direct requests to api.studio.mercor.com return Cloudflare 403 error 1010
unless a browser User-Agent is sent (default Python-urllib UA is blocked) — this
script sets one.

Usage:
  # list every world in a campaign + how many times OLD appears in its layout
  replace_instructions_link.py scan <campaign_id> <old_str>

  # swap OLD->NEW in one world (add --dry-run to preview counts, no write)
  replace_instructions_link.py replace <world_id> <campaign_id> <old_str> <new_str> [--dry-run]

Notes:
  - Prefer replacing just the Google-Doc ID substring (keeps any ?tab=... suffix
    and the markdown label intact). Pass a full URL as OLD/NEW only when the target
    is not another Google Doc (e.g. swapping to an instructions-hub URL).
  - The list endpoint returns module_layout=null, so scan does a full per-world GET.
  - PATCH /worlds/{id} REPLACES the whole world_settings; this reads-modifies-writes
    the full object, changing only the two layout fields.
  - Canonical OLD Vigil instructions doc id: 1nvj9D-IW7dBQyn-lOaXTINZoxVEJJ1R4GwzNgMOUi7U
"""
import os, sys, json, urllib.request, urllib.error

KEY = os.environ["RLS_API_KEY"]
BASE = os.environ.get("RLS_BASE_URL", "https://api.studio.mercor.com").rstrip("/")
COMPANY = os.environ.get("RLS_COMPANY_ID", "comp_2fa4115109d741cd94a3c409ed89e61f")
ACCOUNT = os.environ.get("RLS_ACCOUNT_ID", "acct_be8f7fcc2c554b33baa5a0c9d05496e3")

def headers(campaign_id):
    return {
        "Authorization": f"Bearer {KEY}",
        "X-Campaign-Id": campaign_id,
        "X-Company-Id": COMPANY,
        "X-Account-Id": ACCOUNT,
        "Content-Type": "application/json",
        # browser UA dodges Cloudflare error 1010
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    }

def call(method, path, campaign_id, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers(campaign_id), method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:600]

def do_scan(campaign_id, old):
    st, res = call("GET", f"/worlds/?campaign_id={campaign_id}", campaign_id)
    if st != 200:
        print(f"list failed {st}: {res}"); sys.exit(1)
    for w in res["worlds"]:
        wid = w["world_id"]
        s, full = call("GET", f"/worlds/{wid}", campaign_id)
        if s != 200:
            print(f"{wid}\t{w['world_name']}\tGET_FAILED {s}"); continue
        cnt = json.dumps(full.get("world_settings", {})).count(old)
        if cnt:
            print(f"{wid}\t{w['world_name']}\told={cnt}")

def do_replace(world_id, campaign_id, old, new, dry):
    st, world = call("GET", f"/worlds/{world_id}", campaign_id)
    if st != 200:
        print(f"GET failed {st}: {world}"); sys.exit(1)
    ws = world["world_settings"]
    before = json.dumps(ws).count(old)
    for k in ("module_layout", "module_layout_draft"):
        if ws.get(k):
            ws[k] = json.loads(json.dumps(ws[k]).replace(old, new))
    after_old = json.dumps(ws).count(old)
    after_new = json.dumps(ws).count(new)
    print(f"world={world_id} ({world.get('world_name')}) old_before={before} old_after={after_old} new_after={after_new}")
    if dry:
        print("DRY RUN, no PATCH"); return
    if before == 0:
        print("nothing to change, skipping PATCH"); return
    st, resp = call("PATCH", f"/worlds/{world_id}", campaign_id, {"world_settings": ws})
    print(f"PATCH status={st}")
    if st >= 300:
        print(f"PATCH body: {resp}"); sys.exit(1)
    st, w2 = call("GET", f"/worlds/{world_id}", campaign_id)
    vs = json.dumps(w2["world_settings"])
    print(f"VERIFY new_id_count={vs.count(new)} old_id_count={vs.count(old)}")

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "scan":
        do_scan(sys.argv[2], sys.argv[3])
    elif mode == "replace":
        do_replace(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], "--dry-run" in sys.argv)
    else:
        print(__doc__); sys.exit(2)
