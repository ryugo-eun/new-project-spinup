"""Re-stamp the Taiga environment id everywhere in an RL Studio campaign.

The env id is NOT one field. It lives in at least three kinds of place, and changing only the
obvious one leaves runs pointed at the old environment while every UI surface looks correct:

  1. world_custom_fields.taiga_environment_id            on EVERY world, canonical or not
  2. task_remix_configs[*].remix_world_field_values      .taiga_environment_id / .prometheus_environment_id
  3. campaign.world_remix_configs[*]                     .world_remix_world_field_values.prometheus_environment_id
     (the "Sync to External Storage" remix)

It also invalidates the file sync: world_custom_fields.prometheus_gcs_path points into the OLD
env's storage bucket, so after a flip the runner mounts a volume that does not exist in the new
env. This script strips those pointers by default so the failure is loud, and Sync to External
Storage has to be re-run.

    python restamp_taiga_env.py --campaign camp_xxx --inventory
    python restamp_taiga_env.py --campaign camp_xxx --to <uuid> --dry-run
    python restamp_taiga_env.py --campaign camp_xxx --to <uuid> --execute
    python restamp_taiga_env.py --campaign camp_xxx --restore <backup.json> --execute

Auth (env, never hardcode): RLS_API_KEY must have WRITE scope on the target campaign. A read-only
key gets 403 "This API key has 'read' access; this endpoint requires 'write'" on the first PATCH,
before anything is changed.

Transport: curl via subprocess. Studio sits behind Cloudflare, which 403s Python urllib. Bodies
go over stdin (-d @-), never the shell.
"""
import argparse, datetime, json, os, subprocess, sys

BASE = os.environ.get("RLS_BASE_URL", "https://api.studio.mercor.com").rstrip("/")
KEY = os.environ.get("RLS_API_KEY")
COMPANY_ID = os.environ.get("RLS_COMPANY_ID", "comp_2fa4115109d741cd94a3c409ed89e61f")
ACCOUNT_ID = os.environ.get("RLS_ACCOUNT_ID", "acct_be8f7fcc2c554b33baa5a0c9d05496e3")

CAMPAIGN = None          # set from --campaign
SYNC_KEY_PREFIX = "prometheus_"


def api(method, path, body=None):
    args = ["/usr/bin/curl", "-s", "-w", "\n%{http_code}", "-X", method,
            "-H", f"Authorization: Bearer {KEY}", "-H", f"X-Campaign-Id:{CAMPAIGN}",
            "-H", f"X-Company-Id:{COMPANY_ID}", "-H", f"X-Account-Id:{ACCOUNT_ID}", "--globoff"]
    stdin = None
    if body is not None:
        args += ["-H", "Content-Type: application/json", "-d", "@-"]
        stdin = json.dumps(body)
    args.append(f"{BASE}{path}")
    p = subprocess.run(args, capture_output=True, text=True, input=stdin)
    txt, _, code = p.stdout.rpartition("\n")
    try:
        code = int(code)
    except ValueError:
        code = 0
    try:
        data = json.loads(txt) if txt.strip() else {}
    except Exception:
        data = {"__raw": txt[:400]}
    return code, data


def walk_env(obj, path=""):
    """Yield (json-path, key, value) for every *_environment_id anywhere in a blob."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k.endswith("environment_id") and isinstance(v, str) and v:
                yield (path or "$", k, v)
            else:
                yield from walk_env(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from walk_env(v, f"{path}[{i}]")


def swap_env(obj, frm, to, hits, path=""):
    """Deep copy with frm -> to, ONLY under keys ending in `environment_id`, ONLY when the
    current value is exactly `frm`. Never touches a value it was not told to touch."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            p = f"{path}.{k}"
            if k.endswith("environment_id") and v == frm:
                out[k] = to
                hits.append(p)
            else:
                out[k] = swap_env(v, frm, to, hits, p)
        return out
    if isinstance(obj, list):
        return [swap_env(v, frm, to, hits, f"{path}[{i}]") for i, v in enumerate(obj)]
    return obj


def load_campaign():
    code, camp = api("GET", f"/campaigns/{CAMPAIGN}")
    if code == 401:
        sys.exit("ABORT: 401. RLS_API_KEY is invalid or expired.")
    if code == 403:
        sys.exit(f"ABORT: 403. RLS_API_KEY is not scoped to {CAMPAIGN}. Use a key that reaches it.")
    if code != 200:
        sys.exit(f"ABORT: GET campaign -> {code}: {str(camp)[:300]}")
    return camp.get("campaign", camp)


def load_worlds():
    code, wl = api("GET", f"/worlds/?campaign_id={CAMPAIGN}")
    if code != 200:
        sys.exit(f"ABORT: GET /worlds/ -> {code}: {str(wl)[:300]}")
    lst = wl["worlds"] if isinstance(wl, dict) and "worlds" in wl else (wl if isinstance(wl, list) else [])
    full = []
    for w in lst:
        wid = w["world_id"]
        c, d = api("GET", f"/worlds/{wid}")
        if c != 200:
            sys.exit(f"ABORT: GET world {wid} -> {c}. Inventory incomplete, refusing to write.")
        full.append(d.get("world", d))
    return full


def inventory(camp, worlds, quiet=False):
    """Every env reference in the campaign. Returns {env_id: count}."""
    counts = {}

    def note(env):
        counts[env] = counts.get(env, 0) + 1

    if not quiet:
        print(f"campaign {CAMPAIGN} ({camp.get('campaign_name')})")
    for p, k, v in walk_env({"world_remix_configs": camp.get("world_remix_configs") or []}):
        note(v)
        if not quiet:
            print(f"  CAMPAIGN {p}.{k} = {v}")
    for w in worlds:
        rows = list(walk_env({"world_custom_fields": w.get("world_custom_fields") or {},
                              "task_remix_configs": w.get("task_remix_configs") or []}))
        gcs = (w.get("world_custom_fields") or {}).get("prometheus_gcs_path")
        if not quiet:
            print(f"  {w.get('world_name')!r}  {w['world_id']}")
            if not rows:
                print("      (no env reference)")
        for p, k, v in rows:
            note(v)
            if not quiet:
                print(f"      {p}.{k} = {v}")
        if gcs and not quiet:
            print(f"      prometheus_gcs_path -> {gcs}")
    if not quiet:
        print("\n  env id totals: " + ", ".join(f"{e} x{n}" for e, n in sorted(counts.items())))
    return counts


def do_restore(path):
    with open(path) as f:
        b = json.load(f)
    if b["campaign_id"] != CAMPAIGN:
        sys.exit(f"ABORT: backup is for {b['campaign_id']}, not {CAMPAIGN}")
    print(f"restoring backup {b['stamp']} ({b['to_env']} -> {b['from_env']})")
    return b


def main():
    global CAMPAIGN
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", required=True, help="camp_... to re-stamp. NO default, on purpose")
    ap.add_argument("--to", help="target Taiga env uuid")
    ap.add_argument("--from", dest="frm",
                    help="env uuid to replace. Required when the campaign holds more than one")
    ap.add_argument("--inventory", action="store_true", help="report every env reference, write nothing")
    ap.add_argument("--restore", help="path to a backup json written by an earlier run")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--keep-sync", action="store_true",
                    help="keep the prometheus_* file-sync pointers. They point into the OLD env's "
                         "bucket, so the runner mounts a volume that does not exist. Default is to "
                         "strip them, which forces a re-run of Sync to External Storage")
    ap.add_argument("--backup-dir", default=os.getcwd())
    a = ap.parse_args()

    if not KEY:
        sys.exit("ABORT: RLS_API_KEY is not set.")
    CAMPAIGN = a.campaign
    execute = a.execute and not a.dry_run
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    camp = load_campaign()
    worlds = load_worlds()

    if a.inventory:
        inventory(camp, worlds)
        return

    # ---------- restore path ----------
    if a.restore:
        b = do_restore(a.restore)
        if not execute:
            print(f"DRY-RUN: would restore {len(b['worlds'])} world(s) + the campaign remix configs.")
            return
        for wid, saved in b["worlds"].items():
            body = {"world_custom_fields": saved["world_custom_fields"],
                    "task_remix_configs": saved["task_remix_configs"]}
            c, r = api("PATCH", f"/worlds/{wid}", body=body)
            if c != 200:
                sys.exit(f"ABORT: restore PATCH world {wid} -> {c}: {str(r)[:300]}")
            print(f"  restored {saved['world_name']}")
        c, r = api("PATCH", f"/campaigns/{CAMPAIGN}",
                   body={"world_remix_configs": b["campaign_world_remix_configs"]})
        if c != 200:
            sys.exit(f"ABORT: restore PATCH campaign -> {c}: {str(r)[:300]}")
        print("  restored campaign world_remix_configs")
        return

    if not a.to:
        sys.exit("ABORT: --to is required (or use --inventory / --restore).")

    # ---------- work out what we are replacing ----------
    counts = inventory(camp, worlds, quiet=True)
    present = sorted(e for e in counts if e != a.to)
    frm = a.frm
    if not frm:
        if len(present) == 0:
            sys.exit(f"ABORT: campaign is already entirely on {a.to}, nothing to do.")
        if len(present) > 1:
            detail = ", ".join(f"{e} x{counts[e]}" for e in present)
            sys.exit(f"ABORT: campaign holds {len(present)} different env ids ({detail}).\n"
                     f"       Ambiguous. Pass --from explicitly, once per env id.")
        frm = present[0]
    if frm == a.to:
        sys.exit("ABORT: --from and --to are the same.")
    if frm not in counts:
        sys.exit(f"ABORT: {frm} does not appear anywhere in this campaign. Run --inventory.")

    print(f"campaign {CAMPAIGN} ({camp.get('campaign_name')})")
    print(f"  FROM {frm}  ({counts[frm]} reference(s))")
    print(f"  TO   {a.to}")
    print(f"  mode {'EXECUTE' if execute else 'DRY-RUN'}"
          f"{'' if a.keep_sync else '  (+ strip stale prometheus_* file-sync pointers)'}\n")

    backup = {"stamp": stamp, "campaign_id": CAMPAIGN, "campaign_name": camp.get("campaign_name"),
              "from_env": frm, "to_env": a.to,
              "campaign_world_remix_configs": camp.get("world_remix_configs") or [], "worlds": {}}
    planned = []

    for w in worlds:
        wid, name = w["world_id"], w.get("world_name")
        wcf = w.get("world_custom_fields") or {}
        remixes = w.get("task_remix_configs") or []
        backup["worlds"][wid] = {"world_name": name, "world_custom_fields": wcf,
                                 "task_remix_configs": remixes}
        hits = []
        new_wcf = swap_env(wcf, frm, a.to, hits)
        new_remixes = swap_env(remixes, frm, a.to, hits)
        stripped = []
        if hits and not a.keep_sync:
            stripped = sorted(k for k in new_wcf if k.startswith(SYNC_KEY_PREFIX))
            if stripped:
                new_wcf = {k: v for k, v in new_wcf.items() if not k.startswith(SYNC_KEY_PREFIX)}
        body = {}
        if new_wcf != wcf:
            body["world_custom_fields"] = new_wcf
        if new_remixes != remixes:
            body["task_remix_configs"] = new_remixes
        if not body:
            print(f"  {name}: nothing to change")
            continue
        print(f"  {name} ({wid})")
        for h in hits:
            print(f"      env {h}")
        if stripped:
            print(f"      strip {len(stripped)} prometheus_* sync keys "
                  f"(pointed into {frm}'s bucket): {', '.join(stripped)}")
        planned.append((wid, name, body))

    chits = []
    wrc = camp.get("world_remix_configs") or []
    new_wrc = swap_env(wrc, frm, a.to, chits)
    camp_body = {"world_remix_configs": new_wrc} if new_wrc != wrc else None
    if camp_body:
        print("  CAMPAIGN world_remix_configs")
        for h in chits:
            print(f"      env {h}")

    path = os.path.join(a.backup_dir, f"taiga_env_backup_{CAMPAIGN}_{stamp}.json")
    with open(path, "w") as f:
        json.dump(backup, f, indent=1)
    print(f"\nbackup: {path}")

    if not execute:
        print(f"\nDRY-RUN. {len(planned)} world PATCH(es) + {1 if camp_body else 0} campaign PATCH.")
        return

    done = 0
    for wid, name, body in planned:
        c, r = api("PATCH", f"/worlds/{wid}", body=body)
        if c != 200:
            print(f"\n  FAILED on {name} ({wid}) -> {c}: {str(r)[:300]}")
            print(f"  {done} of {len(planned)} worlds were written. The campaign is PARTIAL.")
            print(f"  Roll back:  --restore {path} --execute")
            sys.exit(1)
        done += 1
        print(f"  PATCHED {name}")
    if camp_body:
        c, r = api("PATCH", f"/campaigns/{CAMPAIGN}", body=camp_body)
        if c != 200:
            print(f"\n  FAILED on the campaign -> {c}: {str(r)[:300]}")
            print(f"  All {done} worlds were written but the campaign remix was NOT. PARTIAL.")
            print(f"  Roll back:  --restore {path} --execute")
            sys.exit(1)
        print("  PATCHED campaign world_remix_configs")

    # ---------- verify by re-reading ----------
    print("\nverifying...")
    after = inventory(load_campaign(), load_worlds(), quiet=True)
    left = after.get(frm, 0)
    if left:
        print(f"  !! {left} reference(s) to {frm} STILL PRESENT. Re-run --inventory and investigate.")
        sys.exit(1)
    print(f"  clean: 0 references to {frm}, {after.get(a.to, 0)} to {a.to}")
    if not a.keep_sync:
        print("\nNEXT: re-run Sync to External Storage on the world you are testing. The file "
              "sync pointers were stripped, so nothing is mounted in the new env until it runs.")


if __name__ == "__main__":
    main()
