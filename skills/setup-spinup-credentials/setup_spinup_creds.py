#!/usr/bin/env python3
"""
Step 0 of a Sparta new-vertical spinup: put working credentials on this machine.

Collects the ONE real secret (the Studio RLS API key) without it ever touching the
conversation transcript, proves it is live AND write-scoped against the real API,
derives every non-secret id from the API instead of asking anyone to type it, and
writes ~/.claude/credentials/spinup.env with 0600 permissions.

Never prints the key. Never accepts the key as a CLI argument (argv is visible in
`ps` and lands in shell history).

Usage:
  python3 setup_spinup_creds.py                      # interactive, validate + write
  python3 setup_spinup_creds.py --campaign Westwood  # pin a campaign's ids too
  python3 setup_spinup_creds.py --check              # validate what is already there
  python3 setup_spinup_creds.py --list               # list reachable campaigns
"""

import argparse
import getpass
import json
import os
import re
import stat
import sys
import urllib.error
import urllib.request

RLS_BASE_URL = "https://api.studio.mercor.com"
CRED_DIR = os.path.expanduser("~/.claude/credentials")
CRED_FILE = os.path.join(CRED_DIR, "spinup.env")
TAIGA_TOKEN = os.path.join(CRED_DIR, "taiga_oauth.json")

# The Studio API sits behind Cloudflare, which 403s error 1010 on a Python
# user agent. A browser UA is required on every call, not just the writes.
BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

C_OK, C_BAD, C_WARN, C_DIM, C_END = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"


def ok(m):
    print(f"  {C_OK}PASS{C_END}  {m}")


def bad(m):
    print(f"  {C_BAD}FAIL{C_END}  {m}")


def warn(m):
    print(f"  {C_WARN}WARN{C_END}  {m}")


def dim(m):
    print(f"{C_DIM}{m}{C_END}")


def api(path, key, method="GET", body=None, campaign=None, company=None, timeout=45):
    """Return (status, parsed_json_or_raw_text). Never raises on an HTTP error."""
    headers = {"Authorization": f"Bearer {key}", "User-Agent": BROWSER_UA}
    if campaign:
        headers["X-Campaign-Id"] = campaign
    if company:
        headers["X-Company-Id"] = company
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{RLS_BASE_URL}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode()
            status = r.status
    except urllib.error.HTTPError as e:
        raw, status = e.read().decode(), e.code
    except Exception as e:  # network, DNS, TLS
        return 0, {"detail": f"{type(e).__name__}: {e}"}
    try:
        return status, json.loads(raw)
    except ValueError:
        return status, raw


def prompt_key():
    """Read the key with echo off. getpass writes its prompt to the tty, not stdout."""
    if not sys.stdin.isatty():
        print(
            "This must run in a real terminal so the key can be typed with echo off.\n"
            "Run it yourself with:  python3 setup_spinup_creds.py",
            file=sys.stderr,
        )
        sys.exit(2)
    print("Studio -> your campaign -> Settings -> API -> create a key with WRITE access.")
    print("Paste it below. It will not be shown, logged, or echoed anywhere.\n")
    key = getpass.getpass("RLS_API_KEY: ").strip()
    if not key:
        print("Nothing entered.", file=sys.stderr)
        sys.exit(2)
    return key


def check_live(key):
    """The key authenticates at all. Returns the campaign list on success."""
    status, body = api("/campaigns/", key)
    if status == 200 and isinstance(body, list):
        ok(f"key authenticates, reaches {len(body)} campaign(s)")
        return body
    if status == 401:
        bad("key rejected (401). It is wrong, revoked, or was pasted with a stray character.")
    elif status == 403:
        bad(f"key authenticates but is refused (403): {body}")
    elif status == 0:
        bad(f"could not reach {RLS_BASE_URL} -- {body.get('detail')}")
    else:
        bad(f"unexpected {status} from /campaigns/: {str(body)[:200]}")
    return None


def check_write_scope(key, campaigns, pinned=None):
    """
    Prove the key can WRITE, not just read.

    A read-scoped key passes every GET in this script and then fails at runbook
    step 4 with a confusing 403. The discriminator, verified against a known
    read key and a known write key on 2026-08-07:

        write key -> 400 {"detail":"At least one field must be provided for update"}
        read key  -> 403 {"detail":"This API key has 'read' access; this endpoint requires 'write'."}

    PATCH with an empty body is a proven no-op: the target world was byte-identical
    before and after (490,488 bytes, identical checksum). The API rejects the body
    before touching the record, so nothing is mutated.
    """
    # Two separate reasons a probe can come back useless, and they must not be
    # confused with each other:
    #   * the campaign has no world to probe against;
    #   * the caller lacks the ROLE to write on that particular campaign, which
    #     says nothing about the KEY's scope.
    # Testing only the first campaign hit both: once an empty test project (the
    # check silently skipped itself and still printed clean), once a campaign the
    # operator had no write role on (reported "inconclusive" for a perfectly good
    # key). So scan on, and only stop early on a verdict that is truly about the key.
    candidates = [pinned] if pinned else [c for c in campaigns if not c.get("archived_at")]
    tried = 0
    last = None
    for c in candidates[:25]:
        camp, comp = c["campaign_id"], c["company_id"]
        status, body = api(f"/worlds/?campaign_id={camp}", key, campaign=camp, company=comp)
        # GET /worlds/ returns {"worlds": [...]}, NOT a bare list. Treating it as a
        # list made this probe skip itself on a campaign with 43 worlds.
        worlds = body.get("worlds", []) if isinstance(body, dict) else body
        if status != 200 or not isinstance(worlds, list) or not worlds:
            continue
        world_id = worlds[0].get("world_id")
        if not world_id:
            continue

        tried += 1
        status, body = api(
            f"/worlds/{world_id}", key, method="PATCH", body={}, campaign=camp, company=comp
        )
        detail = body.get("detail", "") if isinstance(body, dict) else str(body)
        last = (c.get("campaign_name"), status, detail)

        if status == 400 and "at least one field" in detail.lower():
            ok(f"key has WRITE access (probed on {c.get('campaign_name')}, nothing modified)")
            return True
        if status == 403 and "read" in detail.lower() and "access" in detail.lower():
            # This one IS about the key, so stop: no other campaign will differ.
            bad(
                "key is READ-ONLY. Every step through 5b will 403 on its first PATCH.\n"
                "        Mint a new key in Studio with write access and re-run."
            )
            return False
        # Anything else (role permissions, a locked world) is campaign-specific.
        # Keep looking for a campaign this operator can actually write on.

    if tried == 0:
        warn(
            "no reachable campaign has a world yet, so write scope could NOT be tested. "
            "This is expected before runbook step 4. Re-run after the campaign is cloned:\n"
            "        python3 setup_spinup_creds.py --check"
        )
        return None
    name, status, detail = last
    warn(
        f"write scope UNPROVEN after {tried} campaign(s). The key is not provably "
        f"read-only, but nothing confirmed it can write either.\n"
        f"        Last was {name}: HTTP {status} {detail[:90]}\n"
        f"        Re-run with --campaign <YourVertical> once its campaign exists; that is "
        f"the only campaign whose answer matters."
    )
    return None


def pick_campaign(campaigns, name):
    """Match a campaign by name, case-insensitively, preferring an exact match."""
    live = [c for c in campaigns if not c.get("archived_at")]
    exact = [c for c in live if (c.get("campaign_name") or "").lower() == name.lower()]
    if exact:
        return exact[0], []
    hits = [c for c in live if name.lower() in (c.get("campaign_name") or "").lower()]
    if len(hits) == 1:
        return hits[0], []
    return None, hits


def check_taiga():
    if os.path.exists(TAIGA_TOKEN):
        ok(f"Taiga token present at {TAIGA_TOKEN}")
        return True
    warn(
        "no Taiga token yet. It is a Google OAuth login, not a key you paste.\n"
        "        The first Taiga call opens a browser once and caches the token here.\n"
        "        Nothing in runbook steps 1-15 needs it; the ops skills do."
    )
    return False


def shell_quote(v):
    """Single-quote for POSIX sh. Values containing & or spaces break a bare `. file`."""
    return "'" + str(v).replace("'", "'\\''") + "'"


def read_existing():
    if not os.path.exists(CRED_FILE):
        return {}
    out = {}
    with open(CRED_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip("'\"")
    return out


def write_creds(key, campaign=None, extra=None):
    os.makedirs(CRED_DIR, mode=0o700, exist_ok=True)
    existing = read_existing()
    vals = {
        "RLS_BASE_URL": RLS_BASE_URL,
        "RLS_API_KEY": key,
    }
    if campaign:
        vals["RLS_CAMPAIGN_ID"] = campaign["campaign_id"]
        vals["RLS_COMPANY_ID"] = campaign["company_id"]
        vals["RLS_ACCOUNT_ID"] = campaign["account_id"]
        vals["VERTICAL_NAME"] = campaign.get("campaign_name", "")
    else:
        for k in ("RLS_CAMPAIGN_ID", "RLS_COMPANY_ID", "RLS_ACCOUNT_ID", "VERTICAL_NAME"):
            if existing.get(k):
                vals[k] = existing[k]
    if extra:
        vals.update(extra)
    for k, v in existing.items():
        vals.setdefault(k, v)

    lines = [
        "# Sparta new-vertical spinup credentials.",
        "# Written by the setup-spinup-credentials skill. chmod 0600, never committed.",
        "# Load with:  set -a; . ~/.claude/credentials/spinup.env; set +a",
        "# Values are single-quoted on purpose: an unquoted & or space breaks sourcing.",
        "",
    ]
    for k, v in vals.items():
        lines.append(f"{k}={shell_quote(v)}")
    tmp = CRED_FILE + ".tmp"
    with open(tmp, "w") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)  # 0600 before it is visible at the real path
    os.replace(tmp, CRED_FILE)
    return vals


def report_perms():
    mode = stat.S_IMODE(os.stat(CRED_FILE).st_mode)
    if mode == 0o600:
        ok(f"{CRED_FILE} is 0600 (only you can read it)")
    else:
        bad(f"{CRED_FILE} is {oct(mode)}, expected 0600. Run: chmod 600 {CRED_FILE}")


def main():
    p = argparse.ArgumentParser(description="Step 0: set up spinup credentials.")
    p.add_argument("--campaign", help="Campaign name to pin ids for, e.g. Westwood")
    p.add_argument("--check", action="store_true", help="Validate existing credentials, write nothing")
    p.add_argument("--list", action="store_true", help="List reachable campaigns and exit")
    args = p.parse_args()

    print("\nStep 0: spinup credentials\n" + "=" * 48)

    existing = read_existing()
    if args.check or args.list:
        key = existing.get("RLS_API_KEY")
        if not key:
            bad(f"no RLS_API_KEY in {CRED_FILE}. Run without --check to set it up.")
            sys.exit(1)
        dim(f"using the key already in {CRED_FILE}")
    else:
        if existing.get("RLS_API_KEY"):
            print(f"\n{CRED_FILE} already has a key.")
            # Default to KEEPING it. A non-interactive run must never fall through to
            # a prompt that crashes, and must never silently discard a working key.
            answer = ""
            if sys.stdin.isatty():
                answer = input("Replace it? [y/N] ").strip().lower()
            if answer != "y":
                key = existing["RLS_API_KEY"]
                dim("keeping the existing key, re-validating it")
            else:
                key = prompt_key()
        else:
            key = prompt_key()

    print("\nValidating against the live API")
    campaigns = check_live(key)
    if campaigns is None:
        sys.exit(1)

    if args.list:
        live = sorted(
            (c for c in campaigns if not c.get("archived_at")),
            key=lambda c: (c.get("campaign_name") or "").lower(),
        )
        print(f"\n{len(live)} reachable campaign(s):\n")
        for c in live:
            print(f"  {c['campaign_id']}  {c.get('role','?'):<16} {c.get('campaign_name')}")
        sys.exit(0)

    pinned = None
    if args.campaign:
        pinned, hits = pick_campaign(campaigns, args.campaign)
        if not pinned:
            if hits:
                bad(f"{len(hits)} campaigns match {args.campaign!r}. Be more specific:")
                for c in hits[:10]:
                    print(f"        {c.get('campaign_name')}")
            else:
                bad(
                    f"no reachable campaign matches {args.campaign!r}. "
                    "If it is not cloned yet (runbook step 4), re-run this after."
                )
            sys.exit(1)
        ok(f"campaign {pinned.get('campaign_name')} -> {pinned['campaign_id']}")
        ok(f"ids derived from the API, not typed: company + account")
        role = pinned.get("role")
        if role == "campaign_admin":
            ok(f"your role is campaign_admin")
        else:
            warn(
                f"your role on this campaign is {role!r}, not campaign_admin. "
                "port-vertical-dashboards reads a TRUNCATED view as a non-admin and would "
                "then overwrite the target with it."
            )
    elif existing.get("RLS_CAMPAIGN_ID"):
        pinned = next(
            (c for c in campaigns if c["campaign_id"] == existing["RLS_CAMPAIGN_ID"]), None
        )
        if pinned:
            dim(f"  ..  campaign already pinned: {pinned.get('campaign_name')}")

    check_write_scope(key, campaigns, pinned)
    check_taiga()

    if args.check:
        report_perms()
        print("\nChecked. Nothing written.\n")
        return

    write_creds(key, pinned)
    report_perms()

    print(f"\nWritten to {CRED_FILE}")
    print("Load it in any shell with:")
    print("  set -a; . ~/.claude/credentials/spinup.env; set +a")
    if not args.campaign and not (pinned and pinned.get("campaign_id")):
        print(
            "\nNo campaign pinned yet, which is correct before runbook step 4.\n"
            "Once the campaign is cloned, re-run:\n"
            "  python3 setup_spinup_creds.py --campaign <VerticalName>"
        )
    print()


if __name__ == "__main__":
    main()
