#!/usr/bin/env python3
"""Flip the per-stage review-claim edges from creator-gated to owner-gated on a
campaign's live tasking world(s), so the task's OWNER (the writer) sees the
"Start ... Review" / "Start Preference Labels" action, not only its creator.

Canonical Sparta flow gates these on and_actor_created_required=true, which only
works where creator==owner (true on Panacea/Vigil). Where a vertical's tasks are
created centrally and owned by different writers (creator!=owner), the writer is
locked out. This sets created=false, owns=true on those 5 edges.

Leaves the two `reclaim_from_*_queue` edges alone (they act on unowned queue
tasks; owner-gating would break them).

Config from spinup.env (gitignored). Dry-run by default; --apply to write.
Reuses the same spinup.env as provision_hooks.py (RLS_API_KEY, CAMPAIGN_ID,
COMPANY_ID, ACCOUNT_ID, TARGET_WORLD_IDS).
"""
import json, sys, pathlib, urllib.request, urllib.error

HERE = pathlib.Path(__file__).parent
TARGET_EDGES = {
    "start_task_autoqc_review",
    "start_agent_run_review",
    "start_failure_analysis_autoqc_review",
    "start_preference_labels_autoqc_review",
    "advance_to_preference_labels",
}

def load_env():
    f = HERE / "spinup.env"
    if not f.exists():
        sys.exit("Missing spinup.env — copy spinup.env.example and fill in RLS_API_KEY + IDs.")
    env = {}
    for line in f.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1); env[k.strip()] = v.strip()
    return env

CFG = load_env()
def need(k):
    v = CFG.get(k, "").strip()
    if not v: sys.exit(f"spinup.env: {k} required.")
    return v

BASE = CFG.get("RLS_BASE_URL", "https://api.studio.mercor.com").rstrip("/")
H = {"Authorization": f"Bearer {need('RLS_API_KEY')}", "X-Campaign-Id": need("CAMPAIGN_ID"),
     "X-Company-Id": need("COMPANY_ID"), "X-Account-Id": need("ACCOUNT_ID"),
     "Content-Type": "application/json"}
WORLDS = [w.strip() for w in need("TARGET_WORLD_IDS").split(",") if w.strip()]
APPLY = "--apply" in sys.argv

def req(method, path, body=None):
    url = f"{BASE}{path}"
    for _ in range(3):
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(url, data=data, headers=H, method=method)
        try:
            with urllib.request.urlopen(r) as resp:
                return resp.status, json.loads(resp.read() or "null")
        except urllib.error.HTTPError as e:
            if e.code in (301,302,307,308):
                url = e.headers["Location"].replace("http://","https://",1); continue
            return e.code, e.read().decode()[:300]
    return 0, "redirect loop"

for wid in WORLDS:
    st, w = req("GET", f"/worlds/{wid}")
    if st >= 400: sys.exit(f"GET {wid} failed ({st}): {w}")
    fc = w["flow_config"]
    (HERE / f"backup_flow_{wid}.json").write_text(json.dumps(fc))
    changed = []
    for e in fc["flow_edges"]:
        if e["edge_id"] in TARGET_EDGES:
            if e.get("and_actor_created_required") or not e.get("and_actor_owns_required"):
                e["and_actor_created_required"] = False
                e["and_actor_owns_required"] = True
                changed.append(e["edge_id"])
    present = {e["edge_id"] for e in fc["flow_edges"]} & TARGET_EDGES
    missing = TARGET_EDGES - present
    print(f"\n{wid} v{w['version']}: {len(present)}/5 target edges present"
          + (f"  MISSING={sorted(missing)}" if missing else ""))
    print(f"  would flip -> owner-gated: {sorted(changed)}")
    if not APPLY:
        continue
    st, res = req("PATCH", f"/worlds/{wid}", {"flow_config": fc})
    if st >= 400: sys.exit(f"  PATCH failed ({st}): {res}")
    _, chk = req("GET", f"/worlds/{wid}")
    bad = [e["edge_id"] for e in chk["flow_config"]["flow_edges"]
           if e["edge_id"] in TARGET_EDGES and (e["and_actor_created_required"] or not e["and_actor_owns_required"])]
    print(f"  applied. verify: {'OK all owner-gated' if not bad else 'STILL WRONG: '+str(bad)}")
print("\nDRY RUN — add --apply to write." if not APPLY else "\nDone.")
