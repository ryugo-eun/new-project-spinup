"""Wire a Sparta RL-Studio campaign so it actually RUNS.

DEFAULT MODE IS "adopt": a human clones [CLONE ME] Sparta Professionals Campaign in the Studio
UI, and this script writes in every single thing that clone leaves broken. It NEVER creates
worlds in adopt mode, so it cannot produce duplicates.

    python clone_sparta_campaign.py --dry-run    # inventory + every write, touches nothing
    python clone_sparta_campaign.py --execute    # does it

    python clone_sparta_campaign.py --mode create --execute   # legacy: create campaign + clone
                                                             # the 4 worlds itself

Required in adopt mode: SPARTA_TARGET_CAMPAIGN (the campaign the human already cloned).

WHAT A UI CLONE ACTUALLY CARRIES, measured on a real UI copy of [CLONE ME] 2026-07-29
(campaign camp_77e47999, worlds `<canonical>- copy`):
    world names ....... suffixed "- copy" (Rampart's variant is " - Copy")   -> renamed here
    hooks ............. ZERO on all four worlds                              -> ported here
    verifiers ......... ZERO                                                 -> created here
    qc_specs .......... [] (nothing clones)                                  -> forked here
    campaign configs .. world_remix_configs [], pipeline_autoqc null         -> provisioned here
    base_world_id ..... points at the SOURCE tasking world                   -> repointed here
    consensus ......... target_world_id points at VIGIL's consensus world    -> repointed here
    taiga env ......... inherited from the source, incl. inside remixes      -> re-stamped here
    default agents .... correct on a [CLONE ME] clone                        -> verified here
    SER-Heal remix .... present on the runner worlds                         -> verified here

The consensus leak is a defect in [CLONE ME] ITSELF, not in the clone: its tasking world sends
consensus labeling into Vigil's world (world_8c245e16, confirmed to be Vigil's own
[Live] Consensus Labeling). Every clone inherits it, Cadre included. Adopt mode repoints it.

Transport: curl via subprocess (Studio sits behind Cloudflare, which 403s Python urllib; curl
passes). Bodies go over stdin (-d @-), NOT the shell, so ~500KB configs and control characters
in qc_spec bodies cannot corrupt the payload.

Auth (env, never hardcode): RLS_API_KEY must reach the target AND the source campaign, so use a
BROAD / Okta-forwarded key, never a single-campaign key.
"""
import argparse, json, os, re, subprocess, sys, uuid

BASE = os.environ.get("RLS_BASE_URL", "https://api.studio.mercor.com").rstrip("/")
KEY = os.environ["RLS_API_KEY"]

# ============================ CONFIG ============================
COMPANY_ID = "comp_2fa4115109d741cd94a3c409ed89e61f"   # Sparta Studio company (shared)
ACCOUNT_ID = "acct_be8f7fcc2c554b33baa5a0c9d05496e3"   # Sparta Studio account (shared)

# adopt mode: the campaign the human already cloned in the UI. REQUIRED.
TARGET_CAMPAIGN = os.environ.get("SPARTA_TARGET_CAMPAIGN") or None
# create mode only: name for the campaign this script would create.
TARGET_NAME = os.environ.get("SPARTA_TARGET_NAME", "[CLONE ME] Sparta Professionals Campaign")

# Single lineage source: config reference, tasking AutoQC, and the builder set all come from here.
# It MUST be a COMPLETE Sparta campaign (22 tasking hooks + 9 qc_specs incl. "AutoQC" + the GWB
# 4-hook builder set + heal on the runner worlds). Verified complete 2026-07-29.
SRC_CAMPAIGN = os.environ.get("SPARTA_SRC_CAMPAIGN", "camp_4040aadecd0544a6ab7f9a97780b809f")
# Taiga env for the NEW campaign. REQUIRED, deliberately NO DEFAULT.
#
# EVERY project needs its OWN Taiga environment. Reusing another vertical's is the mistake this
# variable exists to prevent: Ryu cloned Abacus's env (2a931db7-ee3f-42d4-8125-9ff4361ed755) into
# new verticals before learning each project needs its own, so Cadre still runs on Abacus's env.
# A fresh clone inherits [CLONE ME]'s env, which is exactly what has to be overwritten, so there is
# no safe default and the script aborts rather than guess.
# How to create one: Erick Chen's walkthrough, https://www.loom.com/share/d040799ec8ab43e9ac4aa39795fdce91
TARGET_ENV_ID = os.environ.get("SPARTA_TARGET_ENV_ID") or None
TAIGA_ENV_HELP_LOOM = "https://www.loom.com/share/d040799ec8ab43e9ac4aa39795fdce91"
TAIGA_ENV_HELP_THREAD = ("https://64f4423488df355.slack.com/archives/C0BMAC5BX4G/"
                         "p1785286576111299?thread_ts=1785286398.426639&cid=C0BMAC5BX4G")
# Escape hatch for re-running against a campaign that is already partly wired (a resumed or
# repeated run). Off by default so a live campaign cannot be touched by accident.
ALLOW_REWIRE = os.environ.get("SPARTA_ALLOW_REWIRE") == "1"
SPARTA_EXTERNAL_AGENT_ID = os.environ.get("SPARTA_AGENT_ID", "agent_e8696c697c694dada2c1566d0705b6db")

# The 4 canonical Sparta world names.
WORLD_GWB       = "[LIVE] Golden World Building"
WORLD_TASKING   = "[Live New Flow] Final Tasking World"
WORLD_CONSENSUS = "[Live] Consensus Labeling"
WORLD_TEST      = "Test_T_1"
CANONICAL_WORLDS = [WORLD_GWB, WORLD_TASKING, WORLD_CONSENSUS, WORLD_TEST]
# A fresh clone of [CLONE ME] always carries all four (verified 2026-07-29), so a missing one means
# the clone did not finish. Abort rather than wire a partial campaign.
REQUIRED_WORLDS = CANONICAL_WORLDS
RUNNER_WORLDS = [WORLD_TASKING, WORLD_TEST]   # verifier + sparta_external_agent + heal + 22 hooks

# Builder AutoQC source. Default = the source campaign itself (a complete source carries the GWB
# 4-hook set + the "AutoQC" spec). Only repoint if you clone from a source lacking the builder set
# (Panacea camp_63e11a2d346e4454f6784532aaf0453a always has it).
BUILDER_SRC_CAMPAIGN = os.environ.get("SPARTA_BUILDER_SRC_CAMPAIGN", SRC_CAMPAIGN)

# SER-Heal remix, embedded literally (static, self-contained config, no campaign read needed).
HEAL_REMIX_OBJECT = {
    "id": "45eb4adf-c1ac-4235-b380-31a9d53bdd75", "name": "SER Heal",
    "remix_config_type": "custom", "remix_application_method": "in_place",
    "remix_implementation_id": "sparta_external_runner_heal", "remix_world_field_values": {},
    "remix_target_type": "task", "require_approval": False,
}

# create mode only. campaign_metadata is REQUIRED on POST /campaigns/ (else 422). Enums from the
# server: tool_use yes|no; tool_use_type mcp|terminal|cua|bua|hybrid (required iff tool_use==yes);
# agent_type single_shot|agentic_harness; turn_count single_turn|multi_turn;
# datatype sft|rlhf|autograders_rubrics|other.
CAMPAIGN_METADATA = {
    "tool_use": "yes", "tool_use_type": "hybrid", "agent_type": "agentic_harness",
    "turn_count": "multi_turn", "datatype": "rlhf",
    "input_modalities": ["text"], "output_modalities": ["text"],
}

# canonical shared Sparta ids (do not usually change)
SPARTA_EVAL_CONFIG_ID = "5502d234-7a43-4ae8-a8b6-75ce19a82186"   # sparta_agentic_grading
HEAL_REMIX_ID = "45eb4adf-c1ac-4235-b380-31a9d53bdd75"           # sparta_external_runner_heal
CONSENSUS_REMIX_IMPL = "native_rls_consensus_label_init"
CREATE_TASKING_REMIX_IMPL = "sparta_create_tasking_world"
PROMETHEUS_TARGET_REMIXES = {                                    # dropped for Sparta-only tasking
    "04c87e48-f3d5-40b7-8375-7c1c3fc78284",  # Taiga QA Finishes
    "6652e121-4c2f-4669-9480-592148e2fc4a",  # External Agent Finishes
    "5aaaf11a-1857-41f2-9800-df3fc242a63c",  # Running Agent Runner
}
BUILDER_HOOK_KEYS = ["finalize after publish", "sync after publish",
                     "pipeline autoqc completed", "helloworld"]

# Campaign-LEVEL configs. These are campaign-scoped and do NOT clone (a UI copy of [CLONE ME]
# carries world_remix_configs [] and pipeline_autoqc null, measured 2026-07-29).
#  - prometheus_sync "Sync to External Storage": the file to Taiga-storage sync, NOT the Prometheus
#    grader Sparta drops. Env-stamped to the TARGET env. Without it, Sync to External Storage
#    cannot fire and the world upload bot aborts. No public create route, so PATCH /campaigns.
#  - pipeline_autoqc: world-building QC. cprc_id + dimension_tags are shared-canonical (verbatim);
#    spec_world_id MUST be the TARGET's OWN GWB (Atria's bug: it points at Abacus's GWB).
PROMETHEUS_SYNC_NAME = "Sync to External Storage"
PIPELINE_AUTOQC_CPRC = "cprc_c02f653eb26d3d2745eb07b8"
PIPELINE_AUTOQC_DIMENSION_TAGS = ["world-quality", "world-files"]
CAMP_ANALYTICS_CONFIG = {"display_metrics": ["average_world_task_median"]}
CAMP_QC_SUBROLE_LABELS = {"subrole_preset_writer": "Expert", "subrole_preset_reviewer": "Reviewer"}

# create mode only: the world config keys worth carrying across.
CLONE_KEYS = [
    "default_orchestrator_ids", "default_judge_ids", "default_agent_ids", "default_platform_ids",
    "world_custom_fields", "world_settings", "task_schema", "world_fields_schema", "user_fields_schema",
    "task_review_feedback_schema", "trajectory_annotation_fields", "verifier_custom_fields_schema",
    "verifier_output_custom_fields_schema", "flow_config", "status_config", "world_status_config",
    "task_remix_configs", "eval_configs", "scoring_configs", "custom_views_config",
    "world_checkpoint_config", "task_invariants", "bundle_configs", "task_spec_config",
]
HOOK_KEEP = ["hook_name", "hook_enabled", "hook_source_event", "hook_source_predicate",
             "hook_target_event", "hook_target_payload", "hook_run_in_background"]
# Studio's UI clone suffixes world names. Two variants seen in the wild: "<name>- copy"
# ([CLONE ME] copy) and "<name> - Copy" (Rampart). Trailing counter seen on repeat copies.
COPY_SUFFIX_RE = re.compile(r"(\s*-\s*cop(?:y|ies)(?:\s*\(?\d+\)?)?)+\s*$", re.IGNORECASE)
# Some operators rename the clone's worlds with a vertical suffix instead, e.g.
# "Test_T_1 (Capitol)" (Capitol, 2026-08-03). Strip ONE trailing parenthetical so those worlds
# still adopt. Canonical names use square brackets, never parens, so this cannot eat part of a
# real name, and canonical_of() still requires an EXACT match on what is left.
VERTICAL_SUFFIX_RE = re.compile(r"\s*\([^()]{1,40}\)\s*$")
# Keep the world names exactly as they are instead of renaming to canonical. Opt-in only:
# every other skill (clone-studio-world, replace-instructions-link) resolves worlds by the exact
# canonical name, so a kept suffix means those tools will not find these worlds.
KEEP_WORLD_NAMES = os.environ.get("SPARTA_KEEP_WORLD_NAMES") == "1"
# ================================================================

EXECUTE = False
WARNINGS = []


def warn(msg):
    WARNINGS.append(msg)
    print(f"    !! {msg}")


def api(method, path, campaign, body=None):
    """curl transport. Body over stdin (-d @-) so nothing hits the shell."""
    url = f"{BASE}{path}"
    args = ["/usr/bin/curl", "-s", "-w", "\n%{http_code}", "-X", method,
            "-H", f"Authorization: Bearer {KEY}", "-H", f"X-Campaign-Id:{campaign}",
            "-H", f"X-Company-Id:{COMPANY_ID}", "-H", f"X-Account-Id:{ACCOUNT_ID}",
            "--globoff"]
    stdin = None
    if body is not None:
        args += ["-H", "Content-Type: application/json", "-d", "@-"]
        stdin = json.dumps(body)
    args.append(url)
    p = subprocess.run(args, capture_output=True, text=True, input=stdin)
    txt, _, code = p.stdout.rpartition("\n")
    try:
        code = int(code)
    except ValueError:
        code = 0
    try:
        data = json.loads(txt) if txt.strip() else {}
    except Exception:
        data = {"__raw": txt[:300]}
    return code, data


def worlds_list(campaign):
    """Raw world list. NOTE: this endpoint returns a SUBSET of each world. It does NOT include
    world_custom_fields, default_agent_ids or eval_configs, so never build an inventory off it."""
    code, d = api("GET", f"/worlds/?campaign_id={campaign}", campaign)
    if code != 200:
        sys.exit(f"ABORT: GET /worlds/ for {campaign} returned {code}: {str(d)[:200]}")
    lst = d["worlds"] if isinstance(d, dict) and "worlds" in d else (d if isinstance(d, list) else [])
    return lst


def canonical_of(world_name):
    """Map a possibly copy-suffixed world name onto a canonical name, or None."""
    stripped = COPY_SUFFIX_RE.sub("", (world_name or "").strip()).strip()
    for candidate in (stripped, VERTICAL_SUFFIX_RE.sub("", stripped).strip()):
        for canon in CANONICAL_WORLDS:
            if candidate.lower() == canon.lower():
                return canon
    return None


def match_canonical_worlds(campaign, require):
    """Resolve the campaign's worlds onto the canonical names, through any copy suffix.

    Aborts on ambiguity (two worlds claiming one canonical name) because guessing which one to
    wire is worse than not wiring. Aborts if a world in `require` is absent."""
    found = {}
    for w in worlds_list(campaign):
        canon = canonical_of(w.get("world_name"))
        if not canon:
            continue
        found.setdefault(canon, []).append(w)
    for canon, hits in sorted(found.items()):
        if len(hits) > 1:
            names = ", ".join(f"{h['world_name']!r} ({h['world_id']})" for h in hits)
            sys.exit(f"ABORT: {len(hits)} worlds map onto {canon!r}: {names}\n"
                     "       Ambiguous adoption. Delete or rename the extras in the UI first.")
    resolved = {c: hits[0] for c, hits in found.items()}
    missing_required = [c for c in require if c not in resolved]
    if missing_required:
        present = ", ".join(repr(w.get("world_name")) for w in worlds_list(campaign)) or "(none)"
        sys.exit(f"ABORT: required world(s) missing from {campaign}: {missing_required}\n"
                 f"       Worlds present: {present}\n"
                 "       Clone [CLONE ME] Sparta Professionals Campaign in the Studio UI first.")
    return resolved


def check_source_lineage(src):
    """A broken source clones broken. Confirm the source really is a complete Sparta campaign
    before wiring anything off it."""
    print(f"[0] source lineage check: {src}")
    src_worlds = match_canonical_worlds(src, REQUIRED_WORLDS)
    tasking = src_worlds[WORLD_TASKING]["world_id"]
    gwb = src_worlds[WORLD_GWB]["world_id"]
    _, th = api("GET", f"/hooks/world/{tasking}", src)
    th = th if isinstance(th, list) else []
    if len(th) < 20:
        sys.exit(f"    ABORT: source tasking world has {len(th)} hooks, expected ~22. "
                 "Point SPARTA_SRC_CAMPAIGN at a complete campaign.")
    _, bh = api("GET", f"/hooks/world/{gwb}", src)
    bh = bh if isinstance(bh, list) else []
    builder = [h for h in bh if any(k in (h.get("hook_name") or "").lower() for k in BUILDER_HOOK_KEYS)]
    if len(builder) < 4:
        sys.exit(f"    ABORT: source GWB has {len(builder)}/4 builder hooks. "
                 "Point SPARTA_BUILDER_SRC_CAMPAIGN at a complete campaign (Panacea camp_63e11a2d).")
    specs = campaign_specs(src)
    if not any(s.get("name") == "AutoQC" for s in specs):
        sys.exit("    ABORT: source has no campaign spec named 'AutoQC'.")
    print(f"    OK: tasking {len(th)} hooks, GWB {len(builder)}/4 builder hooks, "
          f"{len(specs)} qc_specs incl. AutoQC")
    return src_worlds


def campaign_specs(campaign):
    _, d = api("GET", f"/qc-specs/?campaign_id={campaign}", campaign)
    return (d.get("specs", []) if isinstance(d, dict) else (d or [])) or []


def scrub(obj, replacements):
    s = json.dumps(obj)
    for a, b in replacements.items():
        if a and b and a != b:
            s = s.replace(a, b)
    return json.loads(s)


def stamp_remix_envs(remixes, target_env):
    """Set every *_environment_id inside every remix's field values to target_env.

    Match on the KEY, never on a list of remix names: the set of remixes carrying an env id grew
    from two to five the first time anyone looked (Abacus, 2026-07-30), and `prometheus_environment_id`
    does not share the `taiga_` prefix.

    This runs INDEPENDENTLY of world_custom_fields. Capitol (2026-08-03) had the custom field
    already correct on both runner worlds while four remix values still pointed at Abacus's env,
    so gating the remix pass on the custom field leaves exactly Atria's defect in place: a wrong
    remix env reads as an empty Taiga result, which the advance sweeps answer with a re-dispatch.

    Returns (new_remixes, [(remix_name, key, old_value)]) and never changes the remix count."""
    out = json.loads(json.dumps(remixes or []))
    fixed = []
    for r in out:
        vals = r.get("remix_world_field_values")
        if not isinstance(vals, dict):
            continue
        for k, v in list(vals.items()):
            if k.endswith("_environment_id") and isinstance(v, str) and v and v != target_env:
                fixed.append((r.get("remix_name") or r.get("id"), k, v))
                vals[k] = target_env
    return out, fixed


def require_taiga_env():
    """No env, no run. Every project needs its OWN Taiga environment, and there is no safe default:
    a fresh clone carries the source's env, and reusing another vertical's is the exact mistake
    this guard exists to stop."""
    if TARGET_ENV_ID:
        print(f"    taiga env: {TARGET_ENV_ID}")
        return
    sys.exit(
        "ABORT: SPARTA_TARGET_ENV_ID is not set, and there is no default on purpose.\n"
        "       EVERY project needs its OWN Taiga environment. A fresh clone carries the source's\n"
        "       env, so leaving it alone would silently point this vertical's runs at another\n"
        "       vertical's environment (Cadre still runs on Abacus's for exactly this reason).\n"
        "\n"
        "       If the vertical does not have a Taiga env yet, it has to be created first.\n"
        f"       How to create one (Erick Chen): {TAIGA_ENV_HELP_LOOM}\n"
        f"       Slack thread for context:       {TAIGA_ENV_HELP_THREAD}\n"
        "\n"
        "       Then re-run with SPARTA_TARGET_ENV_ID=<the new env id>."
    )


def check_target_is_fresh(target, tgt_worlds):
    """Refuse to touch anything except a brand new clone.

    This skill exists to wire a campaign a human JUST cloned. A fresh clone of [CLONE ME] carries
    zero hooks and zero qc_specs (verified on camp_77e47999, 2026-07-29). Anything with hooks or
    specs is either already wired or a LIVE campaign, and this script renames worlds and patches
    campaign settings, so running it on Panacea or Vigil by mistake would be real damage.

    Set SPARTA_ALLOW_REWIRE=1 to override, for resuming a run that died part way through."""
    hooks_by_world = {}
    for canon, w in tgt_worlds.items():
        _, h = api("GET", f"/hooks/world/{w['world_id']}", target)
        hooks_by_world[canon] = len(h if isinstance(h, list) else [])
    specs = len(campaign_specs(target))
    total_hooks = sum(hooks_by_world.values())
    if not total_hooks and not specs:
        print(f"    freshness: OK, 0 hooks and 0 qc_specs, this is an unwired clone")
        return
    detail = ", ".join(f"{c}={n}" for c, n in sorted(hooks_by_world.items()) if n)
    if ALLOW_REWIRE:
        warn(f"target is NOT a fresh clone ({specs} qc_specs, hooks: {detail or 'none'}), but "
             f"SPARTA_ALLOW_REWIRE=1 is set, so continuing. Everything below is idempotent by "
             f"name, but this will still rename worlds and patch campaign settings.")
        return
    sys.exit(
        f"ABORT: {target} is not a fresh clone. It already has {specs} qc_specs"
        f"{' and hooks: ' + detail if detail else ''}.\n"
        "       This skill wires a campaign a human JUST cloned. A campaign with hooks is either\n"
        "       already wired or LIVE, and this script renames worlds and patches campaign\n"
        "       settings, so it will not touch it.\n"
        "       If you are resuming a run that died part way, re-run with SPARTA_ALLOW_REWIRE=1."
    )


def inventory(target, tgt_worlds):
    """Read-only pass. Print what the clone actually carried, BEFORE any write. This doubles as
    the answer to 'what did my clone bring across', which nothing else tells you."""
    print("\n[1] INVENTORY (read-only, per world via GET /worlds/{id})")
    full = {}
    for canon in CANONICAL_WORLDS:
        w = tgt_worlds.get(canon)
        if not w:
            tag = "MISSING (required)" if canon in REQUIRED_WORLDS else "missing (optional)"
            print(f"    {canon!r}: {tag}")
            continue
        code, d = api("GET", f"/worlds/{w['world_id']}", target)
        if code != 200:
            sys.exit(f"ABORT: GET /worlds/{w['world_id']} returned {code}")
        full[canon] = d
        wcf = d.get("world_custom_fields") or {}
        _, hooks = api("GET", f"/hooks/world/{w['world_id']}", target)
        hooks = hooks if isinstance(hooks, list) else []
        remixes = d.get("task_remix_configs") or []
        env = wcf.get("taiga_environment_id")
        gcs = wcf.get("prometheus_gcs_path")
        print(f"    {canon}")
        print(f"      id            {d['world_id']}")
        name_note = ""
        if d.get("world_name") != canon:
            name_note = ("   <- kept (SPARTA_KEEP_WORLD_NAMES=1)" if KEEP_WORLD_NAMES
                         else "   <- will rename to canonical")
        print(f"      name          {d.get('world_name')!r}{name_note}")
        will_stamp = env != TARGET_ENV_ID and (canon in RUNNER_WORLDS or bool(env))
        print(f"      taiga env     {env}{'   <- will re-stamp' if will_stamp else ''}")
        print(f"      hooks         {len(hooks)}")
        print(f"      agents        {d.get('default_agent_ids')}")
        if canon in RUNNER_WORLDS:
            heal = any(r.get("id") == HEAL_REMIX_ID or
                       r.get("remix_implementation_id") == "sparta_external_runner_heal"
                       for r in remixes)
            print(f"      SER-Heal      {'present' if heal else 'ABSENT, will add'}")
        if gcs and d["world_id"] not in str(gcs):
            print(f"      gcs_path      STALE (does not contain this world id), will strip "
                  f"prometheus_* keys")
        for r in remixes:
            vals = r.get("remix_world_field_values") or {}
            if r.get("remix_implementation_id") == CREATE_TASKING_REMIX_IMPL:
                print(f"      base_world_id {vals.get('base_world_id')}")
            if r.get("remix_implementation_id") == CONSENSUS_REMIX_IMPL:
                print(f"      consensus ->  {vals.get('target_world_id')}")
    specs = campaign_specs(target)
    _, camp = api("GET", f"/campaigns/{target}", target)
    cs = camp.get("campaign_settings") or {}
    wrc = camp.get("world_remix_configs") or []
    names = [s.get("name") for s in specs]
    print(f"    campaign-level")
    print(f"      qc_specs             {len(specs)}: {sorted(set(names))}")
    print(f"      world_remix_configs  {[r.get('name') for r in wrc] or '[] (will provision)'}")
    print(f"      pipeline_autoqc      enabled={cs.get('pipeline_autoqc_enabled')}, "
          f"configs={len(cs.get('pipeline_autoqc_configs') or [])}")
    return full


def rename_to_canonical(target, tgt_worlds):
    """Studio's UI clone suffixes every world name. Every other skill (clone-studio-world,
    replace-instructions-link, this script's own re-runs) resolves worlds by the exact
    canonical name, so put the names back. Verified PATCH world_name -> 200, 2026-07-29."""
    print("\n[2] rename worlds to canonical names")
    if KEEP_WORLD_NAMES:
        print("    SKIPPED: SPARTA_KEEP_WORLD_NAMES=1, names left as-is")
        for c, w in sorted(tgt_worlds.items()):
            if w.get("world_name") != c:
                warn(f"world name kept as {w['world_name']!r} (canonical is {c!r}); "
                     f"clone-studio-world and replace-instructions-link match on the exact "
                     f"canonical name and will NOT find this world")
        return
    todo = [(c, w) for c, w in tgt_worlds.items() if w.get("world_name") != c]
    if not todo:
        print("    all names already canonical")
        return
    for canon, w in todo:
        print(f"    {w['world_name']!r} -> {canon!r}  ({w['world_id']})")
        if not EXECUTE:
            continue
        code, _ = api("PATCH", f"/worlds/{w['world_id']}", target, body={"world_name": canon})
        if code != 200:
            warn(f"rename failed [{code}] for {w['world_id']}, left as {w['world_name']!r}")
        else:
            w["world_name"] = canon


def restamp_env_and_strip_prometheus(target, full):
    """Re-stamp the Taiga env and drop a stale file-sync pointer.

    The env id appears in world_custom_fields AND inside remix_world_field_values (QA_Results,
    Trigger Promo QC Report), so replace the old value across the whole config, not just the
    custom field. A stale prometheus_gcs_path makes the runner mount the SOURCE world's files
    (platform_has_environment=False, empty or wrong trajectories), and it is the nastiest defect
    because everything else still looks correct."""
    print("\n[3] re-stamp Taiga env + strip stale prometheus_* runtime keys")
    for canon, d in full.items():
        wid = d["world_id"]
        wcf = dict(d.get("world_custom_fields") or {})
        old_env = wcf.get("taiga_environment_id")
        remixes = d.get("task_remix_configs") or []
        body = {}
        if old_env and old_env != TARGET_ENV_ID:
            wcf = scrub(wcf, {old_env: TARGET_ENV_ID})
            remixes = scrub(remixes, {old_env: TARGET_ENV_ID})
            body["task_remix_configs"] = remixes
            print(f"    {canon}: env {old_env} -> {TARGET_ENV_ID} (custom fields + remixes)")
        # Independent of the custom field: any *_environment_id in any remix must be the target env.
        stamped, fixed = stamp_remix_envs(remixes, TARGET_ENV_ID)
        if fixed:
            if len(stamped) != len(remixes):
                sys.exit(f"ABORT: remix count changed on {canon} "
                         f"({len(remixes)} -> {len(stamped)}). Refusing to PATCH.")
            body["task_remix_configs"] = stamped
            for rname, key, oldv in fixed:
                print(f"    {canon}: remix {rname!r} {key} {oldv} -> {TARGET_ENV_ID}")
        if canon in RUNNER_WORLDS or wcf.get("taiga_environment_id"):
            wcf["taiga_environment_id"] = TARGET_ENV_ID
        gcs = wcf.get("prometheus_gcs_path")
        if gcs and wid not in str(gcs):
            stale = [k for k in wcf if k.startswith("prometheus_")]
            wcf = {k: v for k, v in wcf.items() if not k.startswith("prometheus_")}
            print(f"    {canon}: stripped {len(stale)} stale prometheus_* keys "
                  f"(pointed at another world). Re-sync via Sync to External Storage.")
        if wcf != (d.get("world_custom_fields") or {}):
            body["world_custom_fields"] = wcf
        if not body:
            print(f"    {canon}: env already {TARGET_ENV_ID}, no stale file pointer")
            continue
        if EXECUTE:
            code, _ = api("PATCH", f"/worlds/{wid}", target, body=body)
            if code != 200:
                warn(f"env/prometheus PATCH failed [{code}] on {canon}")
            else:
                d["world_custom_fields"] = body.get("world_custom_fields", d.get("world_custom_fields"))
                if "task_remix_configs" in body:
                    d["task_remix_configs"] = body["task_remix_configs"]


def repoint_world_refs(target, full, src_worlds):
    """Repoint every cross-campaign world reference at the target's own worlds.

    Three separate jobs, because they fail in three different ways:
      a) base_world_id on the GWB Create Tasking World remix points at the SOURCE tasking world,
         so world building spawns tasking worlds into the source campaign.
      b) the consensus remix target_world_id points at VIGIL's consensus world. This is a defect
         in [CLONE ME] itself, inherited by every clone (Cadre included), so it can NOT be fixed
         by pairing source ids to target ids. Repoint it at the target's own consensus world.
      c) anything else still naming a source world id gets remapped by canonical-name pairing,
         which replaces the src_to_new map the old clone loop used to build."""
    print("\n[4] repoint cross-campaign world references")
    src_by_id = {w["world_id"]: canon for canon, w in src_worlds.items()}
    pair = {sid: full[canon]["world_id"] for sid, canon in src_by_id.items() if canon in full}
    own_consensus = full.get(WORLD_CONSENSUS, {}).get("world_id")
    own_tasking = full.get(WORLD_TASKING, {}).get("world_id")
    intended = {}   # canon -> the remix config we mean to end up with, written or not

    for canon, d in full.items():
        wid = d["world_id"]
        remixes = json.loads(json.dumps(d.get("task_remix_configs") or []))
        before = json.dumps(remixes)
        notes = []
        for r in remixes:
            vals = r.get("remix_world_field_values")
            if not isinstance(vals, dict):
                continue
            if r.get("remix_implementation_id") == CREATE_TASKING_REMIX_IMPL and own_tasking:
                if vals.get("base_world_id") != own_tasking:
                    notes.append(f"base_world_id {vals.get('base_world_id')} -> {own_tasking}")
                    vals["base_world_id"] = own_tasking
            if r.get("remix_implementation_id") == CONSENSUS_REMIX_IMPL:
                cur = vals.get("target_world_id")
                if own_consensus and cur != own_consensus:
                    notes.append(f"consensus target_world_id {cur} -> {own_consensus} "
                                 f"(was another campaign's consensus world)")
                    vals["target_world_id"] = own_consensus
                elif not own_consensus and cur:
                    warn(f"{canon}: consensus remix points at {cur} and this campaign has no "
                         f"[Live] Consensus Labeling world of its own. Left as is. Consensus "
                         f"labeling will write into another campaign until a consensus world "
                         f"exists here.")
        remixes = scrub(remixes, pair)
        intended[canon] = remixes
        if json.dumps(remixes) == before:
            print(f"    {canon}: no world refs to repoint")
            continue
        for n in notes:
            print(f"    {canon}: {n}")
        if json.dumps(remixes) != before and not notes:
            print(f"    {canon}: remapped source world ids by canonical-name pairing")
        if EXECUTE:
            code, _ = api("PATCH", f"/worlds/{wid}", target, body={"task_remix_configs": remixes})
            if code != 200:
                warn(f"repoint PATCH failed [{code}] on {canon}")
            else:
                d["task_remix_configs"] = remixes

    # Report anything the fixes above do NOT resolve. Name pairing cannot catch a reference to a
    # world that is not one of the canonical four, so this is the backstop. Scan the INTENDED
    # config, not the stored one, so a dry run reports the state after the fixes rather than before.
    own_ids = {d["world_id"] for d in full.values()}
    for canon, d in full.items():
        blob = json.dumps(intended.get(canon, d.get("task_remix_configs") or []))
        foreign = {m for m in re.findall(r"world_[0-9a-f]{32}", blob) if m not in own_ids}
        if foreign:
            warn(f"{canon}: would still reference world id(s) outside this campaign: "
                 f"{sorted(foreign)}. Nothing in this script knows what they should point at, "
                 f"so check them by hand.")


def wire_runner_worlds(target, full):
    """Per runner world: world-level Sparta verifier, sparta_external_agent default, SER-Heal."""
    print("\n[5] wire runner worlds (verifier + sparta_external_agent + SER-Heal remix)")
    for canon in RUNNER_WORLDS:
        d = full.get(canon)
        if not d:
            print(f"    {canon}: absent, skipping")
            continue
        wid = d["world_id"]
        print(f"    {canon} ({wid})")
        # Verifier. GET /verifiers/world UNDER-REPORTS, so treat a hit as proof of presence but
        # never treat an empty result as proof of absence: POST and read the result.
        _, vd = api("GET", f"/verifiers/world/{wid}", target)
        vs = vd.get("verifiers") if isinstance(vd, dict) else vd
        has_verifier = bool([v for v in (vs or []) if v.get("task_id") is None])
        if has_verifier:
            print("      world-level verifier already present")
        elif not EXECUTE:
            print("      would create world-level Sparta verifier")
        else:
            code, res = api("POST", "/verifiers/", target, body={
                "world_id": wid, "task_id": None, "eval_config_id": SPARTA_EVAL_CONFIG_ID,
                "verifier_values": {}, "verifier_index": 0})
            if code in (200, 201):
                print("      + world-level Sparta verifier")
            else:
                warn(f"{canon}: verifier POST returned [{code}] {str(res)[:140]}. If this says "
                     f"the verifier exists, that is fine; otherwise the runner will fail with "
                     f"'Found 0 world-level verifier(s)'.")
        agents = d.get("default_agent_ids") or []
        ok = False
        for aid in agents:
            _, ad = api("GET", f"/agents/{aid}", target)
            if (ad.get("agent_config") or {}).get("agent_config_id") == "sparta_external_agent":
                ok = True
                break
        if ok:
            print("      default agent is sparta_external_agent")
        else:
            print(f"      default agent -> sparta_external_agent {SPARTA_EXTERNAL_AGENT_ID} "
                  f"(was {agents})")
            if EXECUTE:
                code, _ = api("PATCH", f"/worlds/{wid}", target,
                              body={"default_agent_ids": [SPARTA_EXTERNAL_AGENT_ID]})
                if code != 200:
                    warn(f"{canon}: default agent PATCH failed [{code}], runner will fail with "
                         f"no_sparta_external_agent")
        remixes = d.get("task_remix_configs") or []
        if any(r.get("id") == HEAL_REMIX_ID or
               r.get("remix_implementation_id") == "sparta_external_runner_heal" for r in remixes):
            print("      SER-Heal remix present")
        else:
            print("      + SER-Heal remix (embedded literal)")
            if EXECUTE:
                new = remixes + [dict(HEAL_REMIX_OBJECT)]
                code, _ = api("PATCH", f"/worlds/{wid}", target, body={"task_remix_configs": new})
                if code != 200:
                    warn(f"{canon}: heal remix PATCH failed [{code}], the 2 heal hooks stay dead")
                else:
                    d["task_remix_configs"] = new


def fork_campaign_specs(src_campaign, target):
    """Fork every campaign-scoped qc_spec from src into target (by name, idempotent).
    Returns {src_qc_spec_id: target_qc_spec_id}."""
    src = {}
    for s in campaign_specs(src_campaign):
        src.setdefault(s["name"], s)
    tgt = {s["name"]: s for s in campaign_specs(target)}
    m = {}
    for name, s in src.items():
        if name in tgt:
            m[s["qc_spec_id"]] = tgt[name]["qc_spec_id"]
            continue
        print(f"    fork spec {name!r}")
        if not EXECUTE:
            m[s["qc_spec_id"]] = f"<new:{name}>"
            continue
        # Read the full spec: the list endpoint may not carry the whole body.
        _, fs = api("GET", f"/qc-specs/{s['qc_spec_id']}", src_campaign)
        fs = fs if fs.get("spec") is not None else s
        code, res = api("POST", "/qc-specs/", target, body={
            "campaign_id": target, "scope_type": "campaign", "scope_id": target,
            "subject_kind": fs.get("subject_kind", "task"), "name": name,
            "description": fs.get("description"), "status": fs.get("status", "live"),
            "spec": fs.get("spec")})
        if code not in (200, 201) or not res.get("qc_spec_id"):
            sys.exit(f"      ABORT fork {name!r} [{code}]: {str(res)[:200]}")
        m[s["qc_spec_id"]] = res["qc_spec_id"]
    return m


def port_hooks(ref_hooks, tgt_world, target, qcmap, drop_prometheus, label):
    """Copy hooks onto tgt_world, remapping qc_spec ids in the payload AND the predicate.
    Idempotent by hook name. Remapping only the payload leaves scrub/stage-advance hooks silently
    never firing, which is why the predicate pass exists."""
    print(f"    hooks -> {label} ({tgt_world})")
    existing = set()
    tgt_remix_ids = None
    if target != "<new>":
        _, ex = api("GET", f"/hooks/world/{tgt_world}", target)
        existing = {h.get("hook_name") for h in (ex if isinstance(ex, list) else [])}
        _, w = api("GET", f"/worlds/{tgt_world}", target)
        tgt_remix_ids = {r.get("id") for r in (w.get("task_remix_configs") or [])}
    made = skipped = failed = 0
    for h in ref_hooks:
        rid = (h.get("hook_target_payload") or {}).get("remix_id", "")
        if drop_prometheus and rid in PROMETHEUS_TARGET_REMIXES:
            continue
        nm = h.get("hook_name")
        if nm in existing:
            skipped += 1
            continue
        body = {k: h.get(k) for k in HOOK_KEEP}
        body["world_id"] = tgt_world
        tp = dict(body.get("hook_target_payload") or {})
        if tp.get("qc_spec_id") in qcmap:
            tp["qc_spec_id"] = qcmap[tp["qc_spec_id"]]
        body["hook_target_payload"] = tp
        preds = json.loads(json.dumps(body.get("hook_source_predicate") or []))
        for p in preds:
            if isinstance(p, dict) and p.get("value") in qcmap:
                p["value"] = qcmap[p["value"]]
        body["hook_source_predicate"] = preds
        if tgt_remix_ids is not None and tp.get("remix_id") and tp["remix_id"] not in tgt_remix_ids:
            print(f"      SKIP (target remix absent): {nm}")
            skipped += 1
            continue
        if not EXECUTE:
            made += 1
            continue
        code, res = api("POST", "/hooks/", target, body=body)
        if code in (200, 201):
            made += 1
        else:
            failed += 1
            print(f"      FAIL [{code}] {nm}: {str(res)[:140]}")
    print(f"      created {made}, skipped {skipped}" + (f", FAILED {failed}" if failed else ""))
    if failed:
        warn(f"{label}: {failed} hook(s) failed to create, the chain is incomplete")


def wire_autoqc(target, full, src_worlds):
    """Tasking AutoQC (fork specs + port the 22-hook chain) and builder AutoQC (fork the AutoQC
    spec + the 4-hook GWB set). A clone carries ZERO hooks and ZERO specs, so without this the
    tasks strand in 'Running ... AutoQC' and world building never finalizes or syncs."""
    print("\n[6] tasking AutoQC (fork qc_specs + port the tasking hook chain)")
    qcmap = fork_campaign_specs(SRC_CAMPAIGN, target)
    src_tasking = src_worlds[WORLD_TASKING]["world_id"]
    _, ref_hooks = api("GET", f"/hooks/world/{src_tasking}", SRC_CAMPAIGN)
    ref_hooks = ref_hooks if isinstance(ref_hooks, list) else []
    for canon in RUNNER_WORLDS:
        if canon in full:
            port_hooks(ref_hooks, full[canon]["world_id"], target, qcmap,
                       drop_prometheus=True, label=canon)

    print("\n[7] builder AutoQC (fork the AutoQC spec + the 4-hook builder set on GWB)")
    bsrc = BUILDER_SRC_CAMPAIGN
    bsrc_worlds = src_worlds if bsrc == SRC_CAMPAIGN else match_canonical_worlds(bsrc, [WORLD_GWB])
    bgwb = bsrc_worlds[WORLD_GWB]["world_id"]
    autoqc_src = next((s for s in campaign_specs(bsrc) if s.get("name") == "AutoQC"), None)
    if not autoqc_src:
        sys.exit(f"    ABORT: builder source {bsrc} has no campaign spec named 'AutoQC'.")
    print(f"    builder source: {bsrc} (GWB {bgwb}, AutoQC {autoqc_src['qc_spec_id']})")
    # The AutoQC spec reads the spec FILE uploaded to the task, so it is domain agnostic and can be
    # forked verbatim. When the builder source IS the config source (the normal case) step 6 already
    # forked it, so reuse that mapping instead of forking a second time.
    autoqc_new = qcmap.get(autoqc_src["qc_spec_id"])
    if autoqc_new:
        print(f"    AutoQC spec already forked in step 6 -> {autoqc_new}")
    else:
        autoqc_new = next((s["qc_spec_id"] for s in campaign_specs(target)
                           if s.get("name") == "AutoQC"), None)
        if autoqc_new:
            print(f"    AutoQC spec already in target: {autoqc_new}")
        else:
            autoqc_new = fork_campaign_specs(bsrc, target).get(autoqc_src["qc_spec_id"])
    _, bhooks = api("GET", f"/hooks/world/{bgwb}", bsrc)
    bhooks = [h for h in (bhooks if isinstance(bhooks, list) else [])
              if any(k in (h.get("hook_name") or "").lower() for k in BUILDER_HOOK_KEYS)]
    if len(bhooks) < 4:
        warn(f"builder source has only {len(bhooks)}/4 builder hooks")
    bmap = {autoqc_src["qc_spec_id"]: autoqc_new} if autoqc_new else {}
    port_hooks(bhooks, full[WORLD_GWB]["world_id"], target, bmap,
               drop_prometheus=False, label=WORLD_GWB)


def wire_campaign_configs(target, full):
    """Campaign-LEVEL configs. Measured absent on a real UI copy of [CLONE ME] 2026-07-29
    (world_remix_configs [], pipeline_autoqc null), so these always need provisioning.
    PATCH /campaigns is a partial merge, so campaign_metadata survives."""
    print("\n[8] campaign-level configs (prometheus_sync + pipeline_autoqc, env/GWB-stamped)")
    _, camp = api("GET", f"/campaigns/{target}", target)
    existing = camp.get("world_remix_configs") or []
    have_sync = any(r.get("world_remix_implementation_id") == "prometheus_sync" for r in existing)
    gwb_id = full[WORLD_GWB]["world_id"]
    if have_sync:
        print(f"    world_remix: prometheus_sync already present, re-stamping env {TARGET_ENV_ID}")
        wrc = json.loads(json.dumps(existing))
        for r in wrc:
            if r.get("world_remix_implementation_id") == "prometheus_sync":
                r.setdefault("world_remix_world_field_values", {})
                r["world_remix_world_field_values"]["prometheus_environment_id"] = TARGET_ENV_ID
    else:
        print(f"    world_remix: + prometheus_sync {PROMETHEUS_SYNC_NAME!r} -> env {TARGET_ENV_ID}")
        wrc = existing + [{
            "id": str(uuid.uuid4()), "name": PROMETHEUS_SYNC_NAME,
            "remix_config_type": "custom", "remix_application_method": "in_place",
            "world_remix_implementation_id": "prometheus_sync",
            "world_remix_world_field_values": {"sync_mode": "clean",
                                              "prometheus_environment_id": TARGET_ENV_ID},
            "files_application_method": "add",
        }]
    print(f"    pipeline_autoqc -> spec_world_id {gwb_id} (this campaign's OWN GWB)")
    settings = dict(camp.get("campaign_settings") or {})
    settings["pipeline_autoqc_enabled"] = True
    settings["pipeline_autoqc_configs"] = [{
        "role": "default", "function_id": None, "cprc_id": PIPELINE_AUTOQC_CPRC,
        "runtime_field_values": {"spec_world_id": gwb_id,
                                 "dimension_tags": PIPELINE_AUTOQC_DIMENSION_TAGS},
    }]
    settings["analytics_config"] = CAMP_ANALYTICS_CONFIG
    settings["file_chat_enabled"] = True
    settings["qc_subrole_labels"] = CAMP_QC_SUBROLE_LABELS
    if EXECUTE:
        code, res = api("PATCH", f"/campaigns/{target}", target,
                        body={"world_remix_configs": wrc, "campaign_settings": settings})
        if code != 200:
            sys.exit(f"    ABORT campaign-config PATCH [{code}]: {str(res)[:200]}")
        print("      + world_remix_configs (prometheus_sync) + campaign_settings "
              "(pipeline_autoqc, analytics_config, file_chat_enabled, qc_subrole_labels)")


def verify(target, full):
    """Re-read everything from the API. Never report success off what we intended to write."""
    print("\n[9] VERIFY (re-read from the API)")
    ok = True
    own_ids = {d["world_id"] for d in full.values()}
    for canon in RUNNER_WORLDS:
        if canon not in full:
            continue
        wid = full[canon]["world_id"]
        _, hooks = api("GET", f"/hooks/world/{wid}", target)
        hooks = hooks if isinstance(hooks, list) else []
        good = len(hooks) >= 22
        ok &= good
        print(f"    {'OK ' if good else '!! '}{canon}: {len(hooks)} hooks (expect 22)")
    if WORLD_GWB in full:
        gwb = full[WORLD_GWB]["world_id"]
        _, bh = api("GET", f"/hooks/world/{gwb}", target)
        bh = bh if isinstance(bh, list) else []
        builder = [h for h in bh if any(k in (h.get("hook_name") or "").lower()
                                        for k in BUILDER_HOOK_KEYS)]
        good = len(builder) >= 4
        ok &= good
        print(f"    {'OK ' if good else '!! '}{WORLD_GWB}: {len(builder)}/4 builder hooks")
        tgt_spec_ids = {s["qc_spec_id"] for s in campaign_specs(target)}
        stale = []
        for h in bh:
            for p in (h.get("hook_source_predicate") or []):
                v = isinstance(p, dict) and p.get("value")
                if isinstance(v, str) and v.startswith("qcs") and v not in tgt_spec_ids:
                    stale.append((h.get("hook_name"), v))
        if stale:
            ok = False
            print(f"    !! builder hook predicate(s) point at a spec outside this campaign: {stale}")
        else:
            print("    OK  builder hook predicates point at this campaign's own specs")
    specs = [s.get("name") for s in campaign_specs(target)]
    good = "AutoQC" in specs and len(specs) >= 9
    ok &= good
    print(f"    {'OK ' if good else '!! '}qc_specs: {len(specs)} incl. AutoQC={('AutoQC' in specs)}")
    for canon, d in full.items():
        _, w = api("GET", f"/worlds/{d['world_id']}", target)
        env = (w.get("world_custom_fields") or {}).get("taiga_environment_id")
        blob = json.dumps(w.get("task_remix_configs") or [])
        foreign = {m for m in re.findall(r"world_[0-9a-f]{32}", blob) if m not in own_ids}
        if KEEP_WORLD_NAMES:
            name_ok = canonical_of(w.get("world_name")) == canon
            name_desc = f"kept {w.get('world_name')!r}"
        else:
            name_ok = w.get("world_name") == canon
            name_desc = "canonical" if name_ok else repr(w.get("world_name"))
        env_ok = (env == TARGET_ENV_ID) or (canon not in RUNNER_WORLDS and not env)
        _, bad_remix_envs = stamp_remix_envs(w.get("task_remix_configs") or [], TARGET_ENV_ID)
        good = name_ok and env_ok and not foreign and not bad_remix_envs
        ok &= good
        print(f"    {'OK ' if good else '!! '}{canon}: "
              f"name={name_desc}, env={env}, "
              f"foreign world refs={sorted(foreign) or 'none'}")
        if bad_remix_envs:
            for rname, key, oldv in bad_remix_envs:
                print(f"        !! remix {rname!r} {key} still {oldv}")
    _, camp = api("GET", f"/campaigns/{target}", target)
    cs = camp.get("campaign_settings") or {}
    cfgs = cs.get("pipeline_autoqc_configs") or []
    spec_world = (cfgs[0].get("runtime_field_values") or {}).get("spec_world_id") if cfgs else None
    good = bool(WORLD_GWB in full and spec_world == full[WORLD_GWB]["world_id"])
    ok &= good
    print(f"    {'OK ' if good else '!! '}pipeline_autoqc spec_world_id={spec_world} "
          f"(want this campaign's own GWB)")
    sync = [r for r in (camp.get("world_remix_configs") or [])
            if r.get("world_remix_implementation_id") == "prometheus_sync"]
    senv = (sync[0].get("world_remix_world_field_values") or {}).get("prometheus_environment_id") if sync else None
    good = bool(sync) and senv == TARGET_ENV_ID
    ok &= good
    print(f"    {'OK ' if good else '!! '}prometheus_sync present={bool(sync)}, env={senv}")
    # Verifier presence is deliberately NOT asserted here: GET /verifiers/world under-reports, so
    # a clean read is not evidence. Step 5 reports the POST result, which is.
    return ok


def create_mode(src_worlds):
    """LEGACY path: create the campaign and clone the 4 worlds. Kept behind --mode create for
    when the Studio UI clone is unavailable.

    HARD GUARD: refuses to run against a campaign that already has any canonical world. The old
    behaviour ran the clone loop unconditionally, so pointing it at an already-cloned campaign
    produced FOUR DUPLICATE WORLDS."""
    print(f"[1] create mode: campaign {TARGET_NAME!r}")
    target = TARGET_CAMPAIGN
    if target:
        present = [w.get("world_name") for w in worlds_list(target)
                   if canonical_of(w.get("world_name"))]
        if present:
            sys.exit(f"ABORT: {target} already has canonical world(s): {present}\n"
                     "       Cloning would create DUPLICATES. Use adopt mode (the default) to "
                     "wire this campaign instead.")
        print(f"    using existing empty target campaign {target}")
    else:
        if not EXECUTE:
            print(f"    would POST /campaigns/ {TARGET_NAME!r}")
            target = "<new>"
        else:
            code, d = api("POST", "/campaigns/", "none", body={
                "campaign_name": TARGET_NAME, "account_id": ACCOUNT_ID,
                "campaign_settings": {"campaign_metadata": CAMPAIGN_METADATA}})
            if code != 201 or not d.get("campaign_id"):
                sys.exit(f"    ABORT create [{code}]: {d}")
            target = d["campaign_id"]
            print(f"    -> {target}")

    print("\n[2] clone the 4 world configs")
    for canon in CANONICAL_WORLDS:
        if canon not in src_worlds:
            print(f"    {canon}: absent from source, skipping")
            continue
        src = src_worlds[canon]
        _, full_src = api("GET", f"/worlds/{src['world_id']}", SRC_CAMPAIGN)
        for e in (full_src.get("eval_configs") or []):
            if "prometheus" in str(e.get("eval_defn_id", "")).lower():
                sys.exit(f"ABORT: Prometheus grader on {canon!r}. Fix the source to Sparta first.")
        print(f"    clone {canon!r}")
        if not EXECUTE:
            continue
        _, created = api("POST", "/worlds/", target, body={
            "world_name": canon, "campaign_id": target,
            "world_description": full_src.get("world_description"),
            "domain": full_src.get("domain")})
        nid = created.get("world_id")
        if not nid:
            sys.exit(f"      ABORT: world create returned no id: {str(created)[:200]}")
        payload = {k: full_src[k] for k in CLONE_KEYS if k in full_src}
        api("PATCH", f"/worlds/{nid}", target, body=payload)
        print(f"      -> {nid}")
    if not EXECUTE:
        print("\n    (dry run) create mode stops here. Re-run with --execute, then the adopt "
              "steps below run against the new campaign.")
        return None
    return target


def main():
    global EXECUTE
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--mode", choices=["adopt", "create"],
                    default=os.environ.get("SPARTA_MODE", "adopt"))
    a = ap.parse_args()
    EXECUTE = a.execute and not a.dry_run
    tag = "EXECUTE" if EXECUTE else "DRY-RUN"
    print(f"===== clone_sparta_campaign [{tag}] mode={a.mode} =====\n")

    src_worlds = check_source_lineage(SRC_CAMPAIGN)

    if a.mode == "create":
        target = create_mode(src_worlds)
        if not target:
            return
    else:
        target = TARGET_CAMPAIGN
        if not target:
            sys.exit("ABORT: adopt mode needs SPARTA_TARGET_CAMPAIGN, the campaign the human "
                     "already cloned in the Studio UI.\n"
                     "       To create the campaign and clone the worlds instead, pass "
                     "--mode create.")
        code, camp = api("GET", f"/campaigns/{target}", target)
        if code != 200:
            sys.exit(f"ABORT: cannot read target campaign {target} [{code}]. Check the key reaches it.")
        print(f"    target: {camp.get('campaign_name')!r} ({target})")
        if target == SRC_CAMPAIGN:
            sys.exit("ABORT: target == source. That would wire the template onto itself.")

    tgt_worlds = match_canonical_worlds(target, REQUIRED_WORLDS)
    if a.mode == "adopt":
        check_target_is_fresh(target, tgt_worlds)
    require_taiga_env()
    full = inventory(target, tgt_worlds)
    rename_to_canonical(target, tgt_worlds)
    for canon, w in tgt_worlds.items():
        if canon in full:
            full[canon]["world_name"] = w.get("world_name")
    restamp_env_and_strip_prometheus(target, full)
    repoint_world_refs(target, full, src_worlds)
    wire_runner_worlds(target, full)
    wire_autoqc(target, full, src_worlds)
    wire_campaign_configs(target, full)

    if EXECUTE:
        ok = verify(target, full)
    else:
        ok = None
        print("\n[9] VERIFY skipped in dry run (nothing was written)")

    print(f"\n===== {tag} target={target} " +
          ("" if ok is None else ("ALL CHECKS PASSED" if ok else "CHECKS FAILED, see !! lines")) +
          " =====")
    if WARNINGS:
        print(f"\n{len(WARNINGS)} warning(s):")
        for w in WARNINGS:
            print(f"  !! {w}")
    print("\nStill manual, by design:")
    print("  1. World FILES never clone. Upload files to the Test_T_1 world, fire Sync to")
    print("     External Storage, then run a task. That is the pipeline test.")
    print("  2. Put the Studio campaign link on the vertical's Mercor Teams project. Nothing")
    print("     automates this and it is the step people forget.")


if __name__ == "__main__":
    main()
