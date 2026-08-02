#!/usr/bin/env python3
"""Flip creator-gated permissions to owner-gated on a campaign's live tasking
world(s), so the task's OWNER (the writer who holds it) can act on it, not only
whoever created it.

Canonical Sparta flow gates on and_actor_created_required=true, which only works
where creator==owner (true on Panacea/Vigil). Where a vertical's tasks are created
centrally and owned by different writers (creator!=owner), the writer is locked
out. That is exactly what a claim flow creates, so run this alongside
`--claim-flow` in wire_world.py.

Two surfaces need it, and BOTH are required:

  1. The 5 per-stage review-claim EDGES. Without these the writer never sees the
     "Start ... Review" / "Start Preference Labels" button.
  2. The `task_edit_content` action GRANTS. Without these the writer sees the
     button, presses it, and then cannot edit the task they just claimed.

Surface 2 was added 2026-08-02 after diffing Delphi's hand-built sample world
(`world_48aed704fcc94a698c66d7a0ff2d5e49`), whose engineer had found the grant
independently. Gating once at the grant is the better placement.

WHY THE GRANT'S from_status_ids ARE LEFT ALONE (7, not 14). Delphi's sample world
also widened grant e12846bf from the canonical 7 statuses to 14, adding the five
`awaiting_*_fixes` sendback statuses plus Needs QC Revision and Running Preference
Labels AutoQC. That is a LOOSENING, not a fix, and it was checked before being
rejected: Panacea (oldest, highest-volume) also runs 7, and every `Needs ... Fixes`
status there carries a `Start ... Fixes` edge into one of those same 7 editable
statuses. The Needs-Fixes status is a deliberate non-editable waiting room with a
one-click door back in. Widening the grant makes tasks editable inside the waiting
room. Do not "fix" this again.

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

# task_edit_content grants that gate on WHO, and so break under a claim flow.
# Keyed by action_grant_id because these ids are stable across every Sparta
# vertical (verified on Panacea, Abacus, Atria, Rampart and Delphi 2026-08-02).
TARGET_GRANTS = {
    # writer/reviewer editing across the 7 working statuses. Canonical: created=true.
    "e12846bf-b0b5-4a76-8b6f-2af89e5b68fd",
    # reviewer editing at Agent Runner & QC Review. Canonical: neither flag set,
    # i.e. ANY reviewer. Under a claim flow the claiming reviewer should own it.
    "grant_edit_reviewer_agent_runner_qc",
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

# Env loading is deferred into main() so that apply_owner_gating / verify_owner_gating
# can be imported by the test without a real spinup.env or a live API key.
CFG, BASE, H, WORLDS = {}, "https://api.studio.mercor.com", {}, []
APPLY = "--apply" in sys.argv

def need(k):
    v = CFG.get(k, "").strip()
    if not v: sys.exit(f"spinup.env: {k} required.")
    return v

def init_env():
    global CFG, BASE, H, WORLDS
    CFG = load_env()
    BASE = CFG.get("RLS_BASE_URL", "https://api.studio.mercor.com").rstrip("/")
    H = {"Authorization": f"Bearer {need('RLS_API_KEY')}", "X-Campaign-Id": need("CAMPAIGN_ID"),
         "X-Company-Id": need("COMPANY_ID"), "X-Account-Id": need("ACCOUNT_ID"),
         "Content-Type": "application/json"}
    WORLDS = [w.strip() for w in need("TARGET_WORLD_IDS").split(",") if w.strip()]

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

def apply_owner_gating(fc):
    """Mutate a world's flow_config in place: creator-gated -> owner-gated, on the
    5 review-claim edges AND the task_edit_content grants.

    Returns a report dict. Never touches from_status_ids on a grant; asserts so,
    because widening it is the loosening this skill explicitly rejects.

    Pure and side-effect-free apart from the mutation, so it is unit-testable
    against a saved world config. See test_fix_claim_gating.py.
    """
    edges_changed = []
    for e in fc["flow_edges"]:
        if e["edge_id"] in TARGET_EDGES:
            if e.get("and_actor_created_required") or not e.get("and_actor_owns_required"):
                e["and_actor_created_required"] = False
                e["and_actor_owns_required"] = True
                edges_changed.append(e["edge_id"])

    # Surface 2: the task_edit_content grants. from_status_ids is deliberately
    # untouched — see the module docstring for why 7 and not 14.
    grants = fc.get("action_grants") or []
    grants_changed = []
    for g in grants:
        if g.get("action_grant_id") in TARGET_GRANTS:
            before = list(g.get("from_status_ids") or [])
            if g.get("and_actor_created_required") or not g.get("and_actor_owns_required"):
                g["and_actor_created_required"] = False
                g["and_actor_owns_required"] = True
                grants_changed.append(g["action_grant_id"])
            after = list(g.get("from_status_ids") or [])
            assert after == before, \
                f"from_status_ids on {g['action_grant_id']} must not change: {len(before)} -> {len(after)}"

    edges_present = {e["edge_id"] for e in fc["flow_edges"]} & TARGET_EDGES
    grants_present = {g.get("action_grant_id") for g in grants} & TARGET_GRANTS
    return {
        "edges_changed": sorted(edges_changed),
        "edges_missing": sorted(TARGET_EDGES - edges_present),
        "edges_present": len(edges_present),
        "grants_changed": sorted(grants_changed),
        "grants_missing": sorted(TARGET_GRANTS - grants_present),
        "grants_present": len(grants_present),
    }


def verify_owner_gating(fc):
    """Re-read check. Returns the ids that are still NOT owner-gated."""
    bad = [e["edge_id"] for e in fc["flow_edges"]
           if e["edge_id"] in TARGET_EDGES
           and (e.get("and_actor_created_required") or not e.get("and_actor_owns_required"))]
    bad += [g["action_grant_id"] for g in (fc.get("action_grants") or [])
            if g.get("action_grant_id") in TARGET_GRANTS
            and (g.get("and_actor_created_required") or not g.get("and_actor_owns_required"))]
    return bad


def main():
    init_env()
    for wid in WORLDS:
        st, w = req("GET", f"/worlds/{wid}")
        if st >= 400: sys.exit(f"GET {wid} failed ({st}): {w}")
        fc = w["flow_config"]
        (HERE / f"backup_flow_{wid}.json").write_text(json.dumps(fc))

        rep = apply_owner_gating(fc)

        print(f"\n{wid} v{w['version']}: {rep['edges_present']}/{len(TARGET_EDGES)} target edges present"
              + (f"  MISSING={rep['edges_missing']}" if rep["edges_missing"] else ""))
        print(f"  edges would flip -> owner-gated: {rep['edges_changed']}")
        print(f"  {rep['grants_present']}/{len(TARGET_GRANTS)} target grants present"
              + (f"  MISSING={rep['grants_missing']}" if rep["grants_missing"] else ""))
        print(f"  grants would flip -> owner-gated: {rep['grants_changed']}")
        if not APPLY:
            continue
        st, res = req("PATCH", f"/worlds/{wid}", {"flow_config": fc})
        if st >= 400: sys.exit(f"  PATCH failed ({st}): {res}")
        _, chk = req("GET", f"/worlds/{wid}")
        bad = verify_owner_gating(chk["flow_config"])
        print(f"  applied. verify: {'OK all owner-gated' if not bad else 'STILL WRONG: '+str(bad)}")
    print("\nDRY RUN — add --apply to write." if not APPLY else "\nDone.")


if __name__ == "__main__":
    main()
