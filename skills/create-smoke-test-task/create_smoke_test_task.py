"""Create and run the Sparta smoke-test task on a campaign's Test_T_1 world.

The smoke test answers ONE question: does a task written in this campaign reach the runner, mount
its world files, and come back with a completed trajectory? Everything about it is held fixed (the
same 52 files, the same prompt, every vertical) so that the campaign under test is the only
variable. A failure is therefore a fault in the campaign, never in the task.

Phases, each of which can be run alone:

    --preflight   read-only: is this world even capable of running a task
    --files       upload the canonical 52-file fixture bundle
    --sync        fire Sync to External Storage and wait for it
    --task        create the task
    --run         fire Sparta External Runner
    --watch       poll the trajectories and give a verdict
    --all         all of the above, in order (the normal use)

Verdict is real. PASS requires a trajectory in `completed` AND evidence in its own tool output that
the world files were actually mounted in the container. "The API returned 200" is not a pass: a run
against an unpopulated volume also returns 200 and completes, and that is the exact failure this
test exists to catch.

Auth: RLS_API_KEY must have WRITE scope on the campaign (~/.claude/credentials/spinup.env).
Transport: curl. Studio is behind Cloudflare, which 403s Python urllib.
"""
import argparse, datetime, json, os, re, subprocess, sys, time, zipfile

BASE = os.environ.get("RLS_BASE_URL", "https://api.studio.mercor.com").rstrip("/")
KEY = os.environ.get("RLS_API_KEY")
COMPANY_ID = os.environ.get("RLS_COMPANY_ID", "comp_2fa4115109d741cd94a3c409ed89e61f")
ACCOUNT_ID = os.environ.get("RLS_ACCOUNT_ID", "acct_be8f7fcc2c554b33baa5a0c9d05496e3")
HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE_ZIP = os.path.join(HERE, "fixture", "world_files.zip")
FIXTURE_TASK = os.path.join(HERE, "fixture", "task.json")

# The world this is allowed to touch. Test_T_1 is the canonical Sparta test world; it exists so
# that smoke tests never land on a world real writers work in.
TEST_WORLD_NAME = "Test_T_1"
SPARTA_AGENT_ID = "agent_e8696c697c694dada2c1566d0705b6db"     # sparta_external_agent
RUNNER_IMPL = "sparta_external_runner"
SYNC_IMPL = "prometheus_sync"

CAMPAIGN = None


def api(method, path, body=None, raw=False):
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
    if raw:
        return code, txt
    try:
        return code, (json.loads(txt) if txt.strip() else {})
    except Exception:
        return code, {"__raw": txt[:400]}


def sql(query):
    code, d = api("POST", "/querier/unstructured", body={"query": query})
    if code != 200:
        sys.exit(f"ABORT: querier -> {code}: {str(d)[:300]}")
    return d.get("rows", [])


def get_world(world_id):
    code, d = api("GET", f"/worlds/{world_id}")
    if code != 200:
        sys.exit(f"ABORT: GET world {world_id} -> {code}: {str(d)[:300]}")
    return d.get("world", d)


# Some campaigns suffix their world names with the vertical, e.g. "Test_T_1 (Capitol)" (Capitol,
# 2026-08-03, kept deliberately). Accept ONE trailing parenthetical so those campaigns resolve,
# and nothing else: a live writer world like "W01 CPMP Oversight Review (Capitol)" still does not
# match, and two worlds both reducing to Test_T_1 still abort as ambiguous.
VERTICAL_SUFFIX_RE = re.compile(r"\s*\([^()]{1,40}\)\s*$")


def is_test_world_name(name):
    n = (name or "").strip()
    return n == TEST_WORLD_NAME or VERTICAL_SUFFIX_RE.sub("", n).strip() == TEST_WORLD_NAME


def find_test_world(force_world):
    """Resolve Test_T_1 in this campaign. Refuses any other world unless --world is given
    explicitly, so a smoke test can never be seeded into a live tasking world by a typo."""
    if force_world:
        w = get_world(force_world)
        if not is_test_world_name(w.get("world_name")):
            print(f"  !! --world points at {w.get('world_name')!r}, not {TEST_WORLD_NAME}. "
                  f"Continuing because you named it explicitly.")
        return w
    code, wl = api("GET", f"/worlds/?campaign_id={CAMPAIGN}")
    if code != 200:
        sys.exit(f"ABORT: GET /worlds/ -> {code}: {str(wl)[:300]}")
    lst = wl["worlds"] if isinstance(wl, dict) and "worlds" in wl else wl
    hits = [w for w in lst if is_test_world_name(w.get("world_name"))]
    if not hits:
        names = ", ".join(repr(w.get("world_name")) for w in lst)
        sys.exit(f"ABORT: no world named {TEST_WORLD_NAME!r} in {CAMPAIGN}.\n"
                 f"       Worlds present: {names}\n"
                 f"       Wire the campaign first (clone-sparta-campaign), or pass --world.")
    if len(hits) > 1:
        sys.exit(f"ABORT: {len(hits)} worlds named {TEST_WORLD_NAME!r}. Ambiguous.")
    return get_world(hits[0]["world_id"])


# ------------------------------------------------------------------ phases

def preflight(w):
    """Every reason a task can fail to reach the runner, checked before anything is written."""
    print("\n[preflight]")
    wid = w["world_id"]
    ok = True

    def chk(label, good, detail=""):
        nonlocal ok
        print(f"  {'PASS' if good else 'FAIL'}  {label}{(': ' + detail) if detail else ''}")
        if not good:
            ok = False

    settings = w.get("world_settings") or {}
    chk("world not locked", not settings.get("world_locked"))
    chk("new tasks allowed", not settings.get("prevent_new_tasks"))

    env = (w.get("world_custom_fields") or {}).get("taiga_environment_id")
    chk("taiga_environment_id set", bool(env), env or "MISSING")

    agents = w.get("default_agent_ids") or []
    chk("default agent = sparta_external_agent", SPARTA_AGENT_ID in agents, str(agents))

    remixes = w.get("task_remix_configs") or []
    runner = next((r for r in remixes if r.get("remix_implementation_id") == RUNNER_IMPL), None)
    chk("Sparta External Runner remix present", bool(runner),
        (runner or {}).get("name", "MISSING"))

    # Hooks: there is no `hooks` table in the querier ("not available for querying"), so read the
    # router. Zero hooks means the task strands in "Running Task AutoQC" and never reaches the
    # runner at all, which is the single most common cause of a dead smoke test.
    code, hd = api("GET", f"/hooks/world/{wid}")
    hooks = hd.get("hooks", hd) if isinstance(hd, dict) else hd
    nhook = len(hooks) if isinstance(hooks, list) else 0
    chk("hooks attached", nhook > 0, f"{nhook} hooks")

    # Verifier: GET /verifiers/world UNDER-REPORTS (documented in clone-sparta-campaign, and
    # confirmed on Delphi, whose runner works while this returns 0). A hit proves presence; a miss
    # proves nothing, so this is reported, never failed on. The runner is the real check.
    code, vd = api("GET", f"/verifiers/world/{wid}")
    vlist = vd.get("verifiers", vd) if isinstance(vd, dict) else vd
    nver = len(vlist) if isinstance(vlist, list) else 0
    print(f"  INFO  world-level verifiers reported: {nver} "
          f"(this endpoint under-reports; 0 is not proof of absence)")

    code, cfgs = api("GET", f"/world-remix/campaign/{CAMPAIGN}/configs")
    lst = cfgs if isinstance(cfgs, list) else (cfgs.get("configs") or [])
    sync = next((r for r in lst if r.get("world_remix_implementation_id") == SYNC_IMPL), None)
    chk("campaign has Sync to External Storage", bool(sync), (sync or {}).get("name", "MISSING"))

    if not ok:
        print("\n  Preflight failed. Fix the FAILs above before seeding; a task written into this\n"
              "  world would strand rather than run. clone-sparta-campaign / clone-studio-world\n"
              "  own hooks, verifier and default agent; restamp-taiga-env owns the env.")
    return ok, runner, sync


def upload_files(w, replace):
    """Push the canonical 52-file bundle as the world's snapshot."""
    print("\n[files]")
    wid = w["world_id"]
    code, snap = api("GET", f"/snapshots/world/{wid}")
    existing = (snap.get("files") or []) if code == 200 else []
    if existing and not replace:
        print(f"  world already carries {len(existing)} file(s). Leaving them alone.")
        print("  Pass --replace-files to overwrite with the fixture bundle.")
        return
    if not os.path.exists(FIXTURE_ZIP):
        sys.exit(f"ABORT: fixture bundle missing at {FIXTURE_ZIP}")
    tmp = os.path.join(HERE, ".fixture_unpacked")
    with zipfile.ZipFile(FIXTURE_ZIP) as z:
        names = [n for n in z.namelist() if not n.endswith("/")]
        z.extractall(tmp)
    print(f"  uploading {len(names)} file(s) from the fixture bundle")
    args = ["/usr/bin/curl", "-s", "-w", "\n%{http_code}", "-X", "POST",
            "-H", f"Authorization: Bearer {KEY}", "-H", f"X-Campaign-Id:{CAMPAIGN}",
            "-H", f"X-Company-Id:{COMPANY_ID}", "-H", f"X-Account-Id:{ACCOUNT_ID}", "--globoff"]
    for n in names:
        # multipart filename carries the TARGET path, which is how the server nests it
        args += ["-F", f"files=@{os.path.join(tmp, n)};filename={n}"]
    args.append(f"{BASE}/snapshots/world/{wid}/update")
    p = subprocess.run(args, capture_output=True, text=True)
    txt, _, code = p.stdout.rpartition("\n")
    # The endpoint answers 201 Created, not 200 (Capitol, 2026-08-03): a 200-only check aborted
    # AFTER all 52 files had already landed, so the run looked like an upload failure when the
    # upload had succeeded. Accept any 2xx and let the file-count check below be the real gate.
    if not code.strip().startswith("2"):
        sys.exit(f"ABORT: snapshot update -> {code}: {txt[:400]}")
    print(f"  new snapshot: {json.loads(txt).get('snapshot_id')}")
    # Re-read rather than trust the POST body. A partial upload must fail here, because the runner
    # mounting 40 of 52 files still produces a run that completes.
    code, snap = api("GET", f"/snapshots/world/{wid}")
    landed = (snap.get("files") or []) if code == 200 else []
    if len(landed) != len(names):
        sys.exit(f"ABORT: snapshot holds {len(landed)} file(s) after upload, expected {len(names)}. "
                 f"Do not run the test against a partial volume.")
    print(f"  verified {len(landed)} file(s) in the world snapshot")


def sync_files(w, sync_cfg, wait):
    """Fire Sync to External Storage and wait for the stamp to advance.

    REQUIRED, never optional. The runner mounts what this step copied into the environment's
    storage; without it the container gets an empty or another environment's volume. This aborts
    rather than proceeding on an unconfirmed sync, because a run on an empty volume still returns
    200 and still completes, so continuing would produce a green result that means nothing.
    """
    print("\n[sync]")
    wid = w["world_id"]
    before = (get_world(wid).get("world_custom_fields") or {}).get("prometheus_clean_sync_run_at")
    code, res = api("POST", f"/world-remix/world/{wid}/remix",
                    body={"world_remix_config_id": sync_cfg["id"]})
    if code not in (200, 201, 202):
        sys.exit(f"ABORT: sync remix -> {code}: {str(res)[:300]}")
    print(f"  fired {sync_cfg.get('name')!r}, waiting up to {wait}s")
    for _ in range(wait // 10):
        time.sleep(10)
        c = get_world(wid).get("world_custom_fields") or {}
        if c.get("prometheus_clean_sync_run_at") and c.get("prometheus_clean_sync_run_at") != before:
            print(f"  synced at {c.get('prometheus_clean_sync_run_at')}, "
                  f"status={c.get('prometheus_sync_status')}")
            return True
    sys.exit(f"ABORT: the sync stamp did not advance within {wait}s, so the files are NOT confirmed\n"
             f"       in the environment's storage. Running now would produce a completed\n"
             f"       trajectory against an empty volume, which is a meaningless pass.\n"
             f"       Check the world in Studio, then re-run with --sync (raise --sync-wait if it\n"
             f"       is merely slow).")


def create_task(w, reuse):
    """Seed the canonical task via the bulk import route."""
    print("\n[task]")
    wid = w["world_id"]
    fx = json.load(open(FIXTURE_TASK))
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    name = fx["task_name_template"].format(date=today)

    rows = sql(f"select task_id, task_name from tasks where world_id='{wid}' "
               f"and task_name like 'Smoke Test%' and archived_at is null order by created_at desc")
    if rows and reuse:
        print(f"  reusing existing {rows[0]['task_name']!r} ({rows[0]['task_id']})")
        return rows[0]["task_id"]
    if rows:
        print(f"  note: {len(rows)} existing smoke task(s); creating another. "
              f"--reuse-task would have used {rows[0]['task_id']}")

    code, schema = api("GET", f"/worlds/{wid}/task-import-schema")
    if code != 200:
        sys.exit(f"ABORT: task-import-schema -> {code}: {str(schema)[:300]}")
    task = {"task_name": name, "task_data_id": None, "notes": None, "custom_fields": {},
            "task_prompt_messages": fx["task_prompt_messages"], "verifiers": []}
    print(f"  creating {name!r}")
    code, res = api("POST", f"/worlds/{wid}/import-tasks", body={"tasks": [task]})
    if code not in (200, 201):
        sys.exit(f"ABORT: import-tasks -> {code}: {str(res)[:400]}")
    rows = sql(f"select task_id from tasks where world_id='{wid}' and task_name='{name}' "
               f"order by created_at desc limit 1")
    if not rows:
        sys.exit("ABORT: import reported success but the task is not queryable. Investigate.")
    print(f"  created {rows[0]['task_id']} ({res.get('total_tasks')} task(s) imported)")
    return rows[0]["task_id"]


def run_task(task_id, runner):
    print("\n[run]")
    code, res = api("POST", f"/task-remix/{task_id}/in-place",
                    body={"remix_config_id": runner["id"], "remix_runtime_field_values": None})
    if code not in (200, 201, 202):
        sys.exit(f"ABORT: runner remix -> {code}: {str(res)[:400]}")
    print(f"  fired {runner.get('name')!r} on {task_id}")


def watch(task_id, wait):
    """Verdict. PASS needs a completed trajectory whose OWN tool output proves the world files
    were mounted in the container."""
    print(f"\n[watch] up to {wait}s")
    fx = json.load(open(FIXTURE_TASK))
    marker = os.path.basename(fx["expected_mounted_files"][0])
    deadline = time.time() + wait
    while True:
        rows = sql(f"select trajectory_status, count(*) n from trajectories "
                   f"where task_id='{task_id}' group by 1")
        counts = {r["trajectory_status"]: r["n"] for r in rows}
        print(f"  {datetime.datetime.now().strftime('%H:%M:%S')}  " +
              (", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "no trajectories yet"))
        if counts.get("completed"):
            break
        if counts.get("failed") and not counts.get("running"):
            print("\n  FAIL: trajectories failed with none completed.")
            return False
        if time.time() > deadline:
            print("\n  INCONCLUSIVE: no completed trajectory in time. Re-run with --watch.")
            return False
        time.sleep(20)

    rows = sql(f"select trajectory_id, trajectory_messages from trajectories "
               f"where task_id='{task_id}' and trajectory_status='completed' "
               f"order by created_at desc limit 1")
    msgs = rows[0]["trajectory_messages"] or []
    mounted = any(marker in (m.get("content") or "") for m in msgs if m.get("role") == "tool")
    print(f"\n  trajectory {rows[0]['trajectory_id']} completed, {len(msgs)} messages")
    if not mounted:
        print(f"  FAIL: no tool output mentions {marker}. The container ran against an EMPTY or\n"
              f"        wrong volume. This is the failure the smoke test exists to catch: check\n"
              f"        the world's file sync and its taiga_environment_id.")
        return False
    print(f"  PASS: the container listed {marker}, so the world files really mounted.")
    return True


def main():
    global CAMPAIGN
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--world", help=f"override the {TEST_WORLD_NAME} lookup")
    ap.add_argument("--task", dest="task_id", help="skip creation, act on this task")
    ap.add_argument("--all", action="store_true")
    for f in ("preflight", "files", "sync", "run", "watch"):
        ap.add_argument(f"--{f}", action="store_true")
    ap.add_argument("--create-task", action="store_true")
    ap.add_argument("--reuse-task", action="store_true", help="reuse an existing smoke task")
    ap.add_argument("--replace-files", action="store_true", help="overwrite existing world files")
    ap.add_argument("--sync-wait", type=int, default=300)
    ap.add_argument("--watch-wait", type=int, default=900)
    a = ap.parse_args()

    if not KEY:
        sys.exit("ABORT: RLS_API_KEY is not set.")
    CAMPAIGN = a.campaign
    phases = {p: getattr(a, p if p != "task" else "create_task")
              for p in ("preflight", "files", "sync", "create_task", "run", "watch")}
    if a.all or not any(phases.values()):
        phases = {k: True for k in phases}

    w = find_test_world(a.world)
    print(f"campaign {CAMPAIGN}")
    print(f"world    {w.get('world_name')!r} {w['world_id']}")

    runner = sync_cfg = None
    if phases["preflight"] or a.all:
        ok, runner, sync_cfg = preflight(w)
        if not ok and (a.all or phases["run"]):
            sys.exit(1)
    if runner is None:
        runner = next((r for r in (w.get("task_remix_configs") or [])
                       if r.get("remix_implementation_id") == RUNNER_IMPL), None)
    if sync_cfg is None:
        code, cfgs = api("GET", f"/world-remix/campaign/{CAMPAIGN}/configs")
        lst = cfgs if isinstance(cfgs, list) else (cfgs.get("configs") or [])
        sync_cfg = next((r for r in lst if r.get("world_remix_implementation_id") == SYNC_IMPL), None)

    if phases["files"]:
        upload_files(w, a.replace_files)
    if phases["sync"]:
        if not sync_cfg:
            sys.exit("ABORT: the campaign has no prometheus_sync world remix, so the files cannot\n"
                     "       be synced into the environment and no run would be meaningful.\n"
                     "       clone-sparta-campaign provisions it.")
        sync_files(w, sync_cfg, a.sync_wait)

    task_id = a.task_id
    if phases["create_task"] and not task_id:
        task_id = create_task(w, a.reuse_task)
    if phases["run"]:
        if not task_id:
            sys.exit("ABORT: --run needs --task or a created task.")
        run_task(task_id, runner)
    if phases["watch"]:
        if not task_id:
            sys.exit("ABORT: --watch needs --task.")
        ok = watch(task_id, a.watch_wait)
        print(f"\n  task: https://studio.mercor.com/tasks/{task_id}")
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
