"""Clone RL Studio worlds (config-only) into a target campaign AND make them correct.

A plain config clone leaves 5 things wrong (all learned the hard way cloning
Abacus<-Vigil and Atria<-Abacus). This script fixes them:
  1. re-stamp taiga_environment_id to the TARGET env (world_custom_fields + baked-in remix refs)
  2. create the world-level Sparta verifier (never cloned) on runner worlds
  3. repoint the Create Tasking World remix base_world_id -> target's own [Live New Flow]
  4. scrub SOURCE-campaign env/id references everywhere
  5. (world FILE bundle is out of band -> world-upload-bot / multipart file-replace)

Dry-run by default. See SKILL.md for the why.

Auth: env vars. Never hardcode secrets. RLS_API_KEY must reach BOTH campaigns
(campaign-scoped keys won't; use Okta-forwarded creds / a broad-access key).
  RLS_API_KEY, RLS_BASE_URL (default https://api.studio.mercor.com)
Usage:  python clone_and_wire_world.py --dry-run   |   --execute
"""
import argparse, json, os, sys
import requests

BASE = os.environ.get("RLS_BASE_URL", "https://api.studio.mercor.com").rstrip("/")
KEY = os.environ["RLS_API_KEY"]
COMPANY = os.environ.get("RLS_COMPANY_ID", "comp_2fa4115109d741cd94a3c409ed89e61f")
ACCOUNT = os.environ.get("RLS_ACCOUNT_ID", "acct_be8f7fcc2c554b33baa5a0c9d05496e3")

# ---- EDIT for your clone --------------------------------------------------
SRC_CAMPAIGN   = "camp_XXXX"          # source campaign
TARGET_CAMPAIGN = None                 # None -> create TARGET_NAME; else existing camp_ id
TARGET_NAME    = "Atria"
# Target names, NOT the source names: a world this script creates is a test world, so every name
# needs a test marker (see assert_out_of_cron_scope). Keys below must match these names exactly.
WORLDS_TO_CLONE = ["[TEST] Consensus Labeling", "[TEST] Final Tasking World", "[TEST] Golden World Building"]
WORLDS_NEEDING_RUNNER = ["[TEST] Final Tasking World"]  # get a world-level verifier
WORLD_BUILDING_WORLD  = "[TEST] Golden World Building"  # holds the Create Tasking World remix
TARGET_LIVE_NEW_FLOW_NAME = "[TEST] Final Tasking World"  # base_world_id should point here (in target)
SRC_WORLD_NAMES = {  # target name -> the SOURCE world it is cloned from
    "[TEST] Consensus Labeling": "[Live] Consensus Labeling",
    "[TEST] Final Tasking World": "[Live New Flow] Final Tasking World",
    "[TEST] Golden World Building": "[LIVE] Golden World Building",
}
TARGET_ENV_ID  = "2a931db7-ee3f-42d4-8125-9ff4361ed755"          # TARGET campaign's Taiga env
SOURCE_ENV_ID  = "fc7bfb41-c425-4984-bd36-9c020d7489ad"          # SOURCE env to scrub (set to source's)
SPARTA_EVAL_CONFIG_ID = "5502d234-7a43-4ae8-a8b6-75ce19a82186"   # sparta_agentic_grading
SPARTA_EXTERNAL_AGENT_ID = ""  # TARGET campaign's sparta_external_agent id (agents are campaign-scoped).
                               # Copy it from a known-good runner world's default_agent_ids in the target
                               # campaign. Runner worlds get their default_agent_ids PATCHed to this if the
                               # cloned default isn't a sparta_external_agent (clones often carry a loop_agent).
                               # REQUIRED when a runner world's cloned default is wrong: the script ABORTS
                               # rather than leaving a loop_agent world behind.
# ---------------------------------------------------------------------------

# A world made by this script is a TEST world. Two independent things keep the automated Studio
# Doctor sweeps off it, and the script enforces both:
#   1. NAME must match one of the sweeps' deny patterns, and
#   2. world_description must NOT start with the GWB spawn stamp.
# The sweeps' in-scope rule is `world_description LIKE 'Tasking world from builder task %' AND NOT
# (name ILIKE any deny pattern)`, from panacea-cli-slack `lib/flow/world-scope.ts`. A plain clone
# COPIES the source description, so cloning a real writer world inherits the stamp and the sweeps
# would advance tasks and fire agent runs in a test world. Hence the rewrite below.
GWB_STAMP = "Tasking world from builder task "          # keep in sync with lib/flow/world-scope.ts
CRON_DENIED_NAME_MARKERS = ["test", "donottouch", "do not task", "do_not_task"]


def assert_out_of_cron_scope(name, description):
    """Refuse to create a world an automated sweep could pick up."""
    if not any(m in (name or "").lower() for m in CRON_DENIED_NAME_MARKERS):
        sys.exit(f"ABORT: {name!r} carries no test marker, so the Studio Doctor sweeps would treat it as a "
                 f"real writer world. Put one of {CRON_DENIED_NAME_MARKERS} in the name.")
    if (description or "").startswith(GWB_STAMP):
        sys.exit(f"ABORT: {name!r} would carry the GWB spawn stamp in its description, which puts it IN "
                 "scope for the sweeps. Use test_description().")


def test_description(src_world_id):
    """Description for a cloned test world: records lineage, never the GWB spawn stamp."""
    return (f"[clone-test] config clone of {src_world_id} from {SRC_CAMPAIGN}. Test world, not a "
            "builder-spawned writer world. Out of scope for the Studio Doctor automated sweeps.")

CLONE_KEYS = [
    "default_orchestrator_ids","default_judge_ids","default_agent_ids","default_platform_ids",
    "world_custom_fields","world_settings","task_schema","world_fields_schema","user_fields_schema",
    "task_review_feedback_schema","trajectory_annotation_fields","verifier_custom_fields_schema",
    "verifier_output_custom_fields_schema","flow_config","status_config","world_status_config",
    "task_remix_configs","eval_configs","scoring_configs","custom_views_config","world_checkpoint_config",
    "task_invariants","bundle_configs","task_spec_config",
]


def req(method, path, camp, **kw):
    h = {"Authorization": f"Bearer {KEY}", "X-Campaign-Id": camp, "X-Company-Id": COMPANY,
         "X-Account-Id": ACCOUNT, "Content-Type": "application/json"}
    url = f"{BASE}{path}"
    for _ in range(3):  # manual redirect: API 307s slashless paths to http:// and strips auth
        r = requests.request(method, url, headers=h, allow_redirects=False, **kw)
        if r.status_code not in (301, 302, 307, 308):
            return r
        url = r.headers["location"].replace("http://", "https://", 1); kw.pop("params", None)
    return r


def retarget_env(obj):
    """Replace every SOURCE_ENV_ID with TARGET_ENV_ID anywhere in a json-able object (scrub)."""
    return json.loads(json.dumps(obj).replace(SOURCE_ENV_ID, TARGET_ENV_ID))


def assert_sparta(world):
    for e in (world.get("eval_configs") or []):
        if "prometheus" in str(e.get("eval_defn_id", "")).lower():
            sys.exit(f"ABORT: Prometheus grader on {world['world_name']!r}. Fix to Sparta first.")


def is_sparta_external_agent(agent_id, camp):
    """True if this agent's config is sparta_external_agent (the runner requires it in default_agent_ids)."""
    a = req("GET", f"/agents/{agent_id}", camp).json()
    cfg = (a or {}).get("agent_config") or {}
    return cfg.get("agent_config_id") == "sparta_external_agent"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--execute", action="store_true"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(); execute = a.execute and not a.dry_run; tag = "EXECUTE" if execute else "DRY-RUN"

    src_camp = next(c for c in req("GET", "/campaigns/", SRC_CAMPAIGN).json() if c["campaign_id"] == SRC_CAMPAIGN)
    target = TARGET_CAMPAIGN
    if not target:
        print(f"[{tag}] create campaign {TARGET_NAME!r}")
        target = req("POST", "/campaigns/", SRC_CAMPAIGN, json={"campaign_name": TARGET_NAME,
                     "company_id": src_camp["company_id"], "account_id": src_camp["account_id"]}).json()["campaign_id"] if execute else "<new>"

    src_worlds = {w["world_name"]: w for w in req("GET", "/worlds/", SRC_CAMPAIGN, params={"campaign_id": SRC_CAMPAIGN}).json()}
    for n in WORLDS_TO_CLONE:
        srcn = SRC_WORLD_NAMES.get(n)
        assert srcn, f"ABORT: no source world mapped for target {n!r} (fill SRC_WORLD_NAMES)"
        assert srcn in src_worlds, f"ABORT: source world not found: {srcn}"
    new_ids = {}  # name -> new world_id

    # 1-2. clone config + re-stamp env to target
    for name in WORLDS_TO_CLONE:
        src_wid = src_worlds[SRC_WORLD_NAMES[name]]["world_id"]
        src = req("GET", f"/worlds/{src_wid}", SRC_CAMPAIGN).json()
        assert_sparta(src)
        desc = test_description(src_wid)
        assert_out_of_cron_scope(name, desc)
        print(f"\n[{tag}] clone {name!r}")
        if not execute:
            new_ids[name] = "<new>"; continue
        new = req("POST", "/worlds/", target, json={"world_name": name, "campaign_id": target,
                  "world_description": desc, "domain": src.get("domain")}).json()
        payload = retarget_env({k: src[k] for k in CLONE_KEYS if k in src})   # scrub source env everywhere
        wcf = {k: v for k, v in (payload.get("world_custom_fields") or {}).items() if not k.startswith("prometheus_")}
        if name in WORLDS_NEEDING_RUNNER or wcf.get("taiga_environment_id"):
            wcf["taiga_environment_id"] = TARGET_ENV_ID
        payload["world_custom_fields"] = wcf
        req("PATCH", f"/worlds/{new['world_id']}", target, json=payload)
        new_ids[name] = new["world_id"]; print(f"  -> {new['world_id']} (env re-stamped, source refs scrubbed)")

    # 3. world-level Sparta verifier on runner worlds
    for name in WORLDS_NEEDING_RUNNER:
        wid = new_ids.get(name)
        print(f"[{tag}] verifier on {name!r} ({wid})")
        if execute and wid:
            # The verifier grades with the SPARTA config. Confirm the world actually carries a Sparta
            # grading eval_config first: a verifier pointing at a config the world does not have, or a
            # world whose grader is anything but sparta_agentic_grading, is a broken runner world.
            evals = req("GET", f"/worlds/{wid}", target).json().get("eval_configs") or []
            defns = [str(e.get("eval_defn_id", "")) for e in evals]
            if "sparta_agentic_grading" not in defns:
                sys.exit(f"ABORT: {name!r} has no sparta_agentic_grading eval_config (has {defns}). "
                         "The grader must be Sparta, never Prometheus, never a loop agent.")
            existing = [v for v in req("GET", f"/verifiers/world/{wid}", target).json().get("verifiers", []) if v.get("task_id") is None]
            if not existing:
                req("POST", "/verifiers/", target, json={"world_id": wid, "task_id": None,
                    "eval_config_id": SPARTA_EVAL_CONFIG_ID, "verifier_values": {}, "verifier_index": 0})
                print("  created world-level Sparta verifier")
            elif len(existing) == 1:
                print("  world-level verifier already present (exactly 1)")
            else:
                sys.exit(f"ABORT: {name!r} has {len(existing)} world-level verifiers; the runner requires "
                         "exactly 1. Delete the extras before running.")
            # 3b. default agent must be sparta_external_agent (clones often carry a loop_agent ->
            #     runner preflight fails 'no_sparta_external_agent'). default_agent_ids is a full-replace list.
            cur = req("GET", f"/worlds/{wid}", target).json().get("default_agent_ids") or []
            if any(is_sparta_external_agent(aid, target) for aid in cur):
                print("  default agent OK (sparta_external_agent present)")
            else:
                # Fail closed. A runner world left on a loop_agent (what a clone often carries) is a
                # broken world that looks finished, so never just warn and move on.
                if not SPARTA_EXTERNAL_AGENT_ID:
                    sys.exit(f"ABORT: {name!r} default agent is {cur} (not sparta_external_agent) and "
                             "SPARTA_EXTERNAL_AGENT_ID is unset. Copy the id from a known-good runner world "
                             "in this campaign and re-run.")
                if not is_sparta_external_agent(SPARTA_EXTERNAL_AGENT_ID, target):
                    sys.exit(f"ABORT: SPARTA_EXTERNAL_AGENT_ID {SPARTA_EXTERNAL_AGENT_ID} is not a "
                             "sparta_external_agent in this campaign. Agents are campaign-scoped: get the id "
                             "from a runner world in the TARGET campaign.")
                req("PATCH", f"/worlds/{wid}", target, json={"default_agent_ids": [SPARTA_EXTERNAL_AGENT_ID]})
                after = req("GET", f"/worlds/{wid}", target).json().get("default_agent_ids") or []
                if not any(is_sparta_external_agent(aid, target) for aid in after):
                    sys.exit(f"ABORT: PATCH did not take on {name!r}; default_agent_ids is still {after}.")
                print(f"  default agent was wrong (had {cur}) -> set to sparta_external_agent, verified")

    # 4. repoint Create Tasking World base_world_id -> target's own [Live New Flow]
    wb = new_ids.get(WORLD_BUILDING_WORLD); lnf = new_ids.get(TARGET_LIVE_NEW_FLOW_NAME)
    print(f"[{tag}] repoint base_world_id on {WORLD_BUILDING_WORLD!r} -> {lnf}")
    if execute and wb and lnf:
        w = req("GET", f"/worlds/{wb}", target).json(); trc = w.get("task_remix_configs") or []
        for r in trc:
            if r.get("remix_implementation_id") == "sparta_create_tasking_world":
                r.setdefault("remix_world_field_values", {})["base_world_id"] = lnf
        req("PATCH", f"/worlds/{wb}", target, json={"task_remix_configs": trc}); print("  repointed")

    # 5. verify: no source-campaign refs remain
    print(f"\n[{tag}] verify — scan target worlds for source env {SOURCE_ENV_ID} / campaign {SRC_CAMPAIGN}")
    print("  (run the SKILL.md cross-campaign scan query; and GET /verifiers/world/{id} == 1 each runner world)")
    print(f"\nDONE ({tag}). Step 6 (world FILE bundle) is out of band — use the world-upload-bot.")


if __name__ == "__main__":
    main()
