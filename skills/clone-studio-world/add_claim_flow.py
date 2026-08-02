#!/usr/bin/env python3
"""OPT-IN: convert a tasking world from writer-creates-own-task to SPL-seeds-and-writer-claims.

Default Sparta flow assumes the writer creates their own task, so creator == owner
everywhere. Some verticals want central tasking instead: an SPL pre-seeds tasks and a
writer picks one up. That needs three changes that only make sense together, and the
world is broken if you apply a subset:

  1. A `Available for Claim` status, where seeded tasks wait.
  2. A `claim_sample_task` edge out of it into Task Writing, with `to_owned_by: actor`
     and `and_actor_not_created_required: true`, so the claimant becomes the owner.
  3. `world_settings.annotator_visibility_require_assignment = false`, or the writer
     cannot SEE an unclaimed task and the button never renders.

And then `fix_claim_gating.py` is MANDATORY, because every permission in the canonical
flow gates on `and_actor_created_required`, which is now false for the claimant.

Off by default in the skill: 5 of 5 live Sparta verticals (Panacea, Abacus, Atria,
Rampart, and Delphi's own canonical worlds as of 2026-08-02) do NOT use this. It is
modelled on Delphi's hand-built `Delphi · Sample World 1`
(`world_48aed704fcc94a698c66d7a0ff2d5e49`), the first world to need it.

This does NOT widen the `task_edit_content` grant's `from_status_ids`. Delphi's sample
world went 7 -> 14 by adding the `awaiting_*_fixes` sendback statuses; Panacea proves 7
is the spec. See the docstring in fix_claim_gating.py.

Usage:
  python3 add_claim_flow.py                 # dry run against TARGET_WORLD_IDS
  python3 add_claim_flow.py --apply
"""
import json, sys, pathlib, urllib.request, urllib.error, uuid

HERE = pathlib.Path(__file__).parent

CLAIM_STATUS_NAME = "Available for Claim"
CLAIM_EDGE_ID = "claim_sample_task"
TASK_WRITING_STATUS_NAME = "Task Writing"

# Shapes lifted verbatim from the live world that introduced this, minus the ids that
# have to be resolved per world.
CLAIM_STATUS_DEFN = {
    "status_name": CLAIM_STATUS_NAME,
    "action_theme": "#e0f2fe",
    "qualifies_done": False,
    "qualifies_ready_for_delivery": False,
    "frozen": False,
}
CLAIM_EDGE = {
    "edge_id": CLAIM_EDGE_ID,
    "to_owned_by": "actor",
    "transition_name": "Claim Task",
    "action_theme": "#16a34a",
    "action_theme_icon": "Hand",
    "actor_roles": ["campaign_admin", "campaign_annotator"],
    "actor_subrole_ids": ["subrole_preset_writer"],
    "and_actor_not_created_required": True,
    "ui_annotator_primary": True,
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
            if e.code in (301, 302, 307, 308):
                url = e.headers["Location"].replace("http://", "https://", 1); continue
            return e.code, e.read().decode()[:300]
    return 0, "redirect loop"


def status_id_by_name(status_config, name):
    for s in status_config.get("status_defns") or []:
        if s.get("status_name") == name:
            return s.get("status_id")
    return None


def add_claim_flow(world, new_status_id=None):
    """Mutate a world dict in place. Returns a report; idempotent.

    Raises ValueError when the world has no `Task Writing` status, because a claim edge
    with nowhere to land would create an inescapable status.
    """
    sc = world.setdefault("status_config", {})
    fc = world.setdefault("flow_config", {})
    ws = world.setdefault("world_settings", {})
    defns = sc.setdefault("status_defns", [])
    edges = fc.setdefault("flow_edges", [])

    target = status_id_by_name(sc, TASK_WRITING_STATUS_NAME)
    if not target:
        raise ValueError(f"world has no {TASK_WRITING_STATUS_NAME!r} status; refusing to add a "
                         f"claim edge with nowhere to land")

    rep = {"status_added": False, "edge_added": False, "visibility_changed": False}

    claim_status_id = status_id_by_name(sc, CLAIM_STATUS_NAME)
    if not claim_status_id:
        claim_status_id = new_status_id or str(uuid.uuid4())
        defns.append(dict(CLAIM_STATUS_DEFN, status_id=claim_status_id))
        rep["status_added"] = True

    if not any(e.get("edge_id") == CLAIM_EDGE_ID for e in edges):
        edges.append(dict(CLAIM_EDGE,
                          from_status_ids=[claim_status_id],
                          to_status_id=target))
        rep["edge_added"] = True

    if ws.get("annotator_visibility_require_assignment") is not False:
        ws["annotator_visibility_require_assignment"] = False
        rep["visibility_changed"] = True

    rep["claim_status_id"] = claim_status_id
    rep["to_status_id"] = target
    return rep


def verify_claim_flow(world):
    """Returns a list of problems; empty means the world is a coherent claim world."""
    sc = world.get("status_config") or {}
    fc = world.get("flow_config") or {}
    ws = world.get("world_settings") or {}
    bad = []

    sid = status_id_by_name(sc, CLAIM_STATUS_NAME)
    if not sid:
        bad.append(f"missing {CLAIM_STATUS_NAME!r} status")
    edge = next((e for e in fc.get("flow_edges") or [] if e.get("edge_id") == CLAIM_EDGE_ID), None)
    if not edge:
        bad.append(f"missing {CLAIM_EDGE_ID} edge")
    else:
        if edge.get("from_status_ids") != [sid]:
            bad.append(f"{CLAIM_EDGE_ID} does not leave {CLAIM_STATUS_NAME!r}")
        if edge.get("to_owned_by") != "actor":
            bad.append(f"{CLAIM_EDGE_ID} does not transfer ownership to the actor")
        if not edge.get("and_actor_not_created_required"):
            bad.append(f"{CLAIM_EDGE_ID} would let the creator claim their own task")
        if edge.get("and_actor_owns_required"):
            bad.append(f"{CLAIM_EDGE_ID} is owner-gated, so nobody can ever claim")
        if edge.get("to_status_id") not in {s.get("status_id") for s in sc.get("status_defns") or []}:
            bad.append(f"{CLAIM_EDGE_ID} lands on a status this world does not have")
    if ws.get("annotator_visibility_require_assignment") is not False:
        bad.append("annotator_visibility_require_assignment is not false, so writers cannot "
                   "see an unclaimed task and the Claim button never renders")
    return bad


def main():
    init_env()
    for wid in WORLDS:
        st, w = req("GET", f"/worlds/{wid}")
        if st >= 400: sys.exit(f"GET {wid} failed ({st}): {w}")
        (HERE / f"backup_claimflow_{wid}.json").write_text(json.dumps(
            {k: w.get(k) for k in ("status_config", "flow_config", "world_settings")}))

        rep = add_claim_flow(w)
        print(f"\n{wid} v{w['version']} ({w.get('world_name')})")
        print(f"  status {CLAIM_STATUS_NAME!r}: {'ADD' if rep['status_added'] else 'already present'}"
              f"  id={rep['claim_status_id']}")
        print(f"  edge {CLAIM_EDGE_ID}: {'ADD' if rep['edge_added'] else 'already present'}"
              f"  -> {rep['to_status_id']}")
        print(f"  annotator_visibility_require_assignment: "
              f"{'set to false' if rep['visibility_changed'] else 'already false'}")
        if not APPLY:
            continue
        body = {"status_config": w["status_config"], "flow_config": w["flow_config"],
                "world_settings": w["world_settings"]}
        st, res = req("PATCH", f"/worlds/{wid}", body)
        if st >= 400: sys.exit(f"  PATCH failed ({st}): {res}")
        _, chk = req("GET", f"/worlds/{wid}")
        bad = verify_claim_flow(chk)
        print(f"  applied. verify: {'OK coherent claim world' if not bad else 'PROBLEMS: ' + str(bad)}")
    print("\nDRY RUN — add --apply to write." if not APPLY else
          "\nDone. NOW RUN fix_claim_gating.py --apply, or the claimant cannot edit what they claimed.")


if __name__ == "__main__":
    main()
