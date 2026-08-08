#!/usr/bin/env python3
"""Port a Sparta vertical's RL Studio dashboards (custom query views) onto another vertical.

A Studio "dashboard" is a `custom query view`: one saved SQL query rendered as a table,
stored per campaign. A freshly cloned vertical gets NONE of them, so its reviewers open
Studio and see nothing, while the source vertical has a full pipeline-stage set.

Auth: reads RLS_API_KEY from the environment (source ~/.claude/credentials/spinup.env first:
`set -a; . ~/.claude/credentials/spinup.env; set +a`). Never prints the key. Company/account
default to the shared Sparta Studio ids; override with RLS_COMPANY_ID / RLS_ACCOUNT_ID.
Base URL: RLS_BASE_URL (default prod).

GOTCHA: direct requests to api.studio.mercor.com return Cloudflare 403 error 1010 unless a
browser User-Agent is sent (default Python-urllib UA is blocked) - this script sets one.

GOTCHA: the write endpoint is PUT and it REPLACES the target campaign's ENTIRE set. There is
no create-one or delete-one route. So `port` always sends the complete desired final set, and
prints anything the replace would delete before it writes.

GOTCHA: GET filters by the caller's role. A campaign_admin sees every view; anyone else sees
only what passes conditional_render_filter. Run as an admin or the "source set" will be short.
A null conditional_render_filter means ADMIN-ONLY, not "everyone".

Usage:
  # what does a campaign have today?
  port_vertical_dashboards.py list <campaign_id>

  # preview the port (dry run, writes nothing)
  port_vertical_dashboards.py port <source_campaign_id> <target_campaign_id> <target_name>

  # actually write, after reading the dry run
  port_vertical_dashboards.py port <src_camp> <tgt_camp> <target_name> --apply

Per-vertical repointing, all verified rather than assumed:
  - every in-SQL reference to the source campaign id follows the target campaign
  - a view scoped to a single world_id (e.g. "Pipeline Fixes") is repointed at the target's
    own GOLDEN_WORLD_NAME world, and ONLY if that world carries the status the SQL filters
    on; otherwise the view is skipped rather than shipped permanently empty
  - descriptions naming the source vertical are rewritten, since they render in the target UI
Anything else is a verbatim clone: task status ids are shared across Sparta verticals.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

KEY = os.environ["RLS_API_KEY"]
BASE = os.environ.get("RLS_BASE_URL", "https://api.studio.mercor.com").rstrip("/")
COMPANY = os.environ.get("RLS_COMPANY_ID", "comp_2fa4115109d741cd94a3c409ed89e61f")
ACCOUNT = os.environ.get("RLS_ACCOUNT_ID", "acct_be8f7fcc2c554b33baa5a0c9d05496e3")

# Cloudflare blocks the default urllib UA with a 403 error 1010.
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"

# The world every Sparta vertical keeps its pipeline-fix statuses on.
GOLDEN_WORLD_NAME = "[LIVE] Golden World Building"

# The four-clause world-name filter that keeps test/golden/staging worlds out of a dashboard.
# An older, looser `NOT IN ('golden_world_MAV', ...)` shows up on hand-made views; treat its
# presence as a reason to overwrite that view rather than keep it.
TIGHT_EXCLUSIONS = (
    "NOT ILIKE '%test%'",
    "NOT ILIKE '%golden%'",
    "NOT ILIKE '[LIVE]%'",
    "NOT ILIKE '[OLD]%'",
)

# Fields the server stamps. Excluded when comparing two views for equality.
SERVER_FIELDS = ("created_at", "updated_at", "created_by", "updated_by")


def headers(campaign_id):
    return {
        "Authorization": f"Bearer {KEY}",
        "X-Campaign-Id": campaign_id,
        "X-Company-Id": COMPANY,
        "X-Account-Id": ACCOUNT,
        "Content-Type": "application/json",
        "User-Agent": UA,
    }


def call(campaign_id, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, headers=headers(campaign_id), method=method
    )
    try:
        with urllib.request.urlopen(req) as r:
            raw = r.read().decode()
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> {e.code} {e.read().decode()[:400]}")
    return json.loads(raw) if raw else None


def as_list(resp):
    """/worlds/ is not consistently a bare array; accept the wrapped shapes too."""
    if isinstance(resp, list):
        return resp
    for k in ("worlds", "items", "data", "results"):
        if isinstance(resp, dict) and isinstance(resp.get(k), list):
            return resp[k]
    return []


def get_views(campaign_id):
    return call(campaign_id, "GET", f"/campaigns/{campaign_id}/custom-query-views")


def pt(iso):
    if not iso:
        return "(unknown)"
    s = iso.replace("Z", "+00:00")
    return (
        datetime.fromisoformat(s)
        .astimezone(ZoneInfo("America/Los_Angeles"))
        .strftime("%Y-%m-%d %I:%M:%S %p %Z")
    )


def stable(v):
    return json.dumps({k: v[k] for k in sorted(v) if k not in SERVER_FIELDS}, sort_keys=True)


def world_scoped(sql):
    """A view pinned to one explicit world_id needs no name exclusions; the id is stricter."""
    import re

    return bool(re.search(r"world_id\s*=\s*'world_[0-9a-f]{32}'", sql))


def cmd_list(campaign_id):
    views = get_views(campaign_id)
    print(f"{len(views)} views on {campaign_id}\n")
    for v in sorted(views, key=lambda x: x["cqview_name"]):
        gate = "admin-only" if v["conditional_render_filter"] is None else "role-gated"
        excl = "world-scoped" if world_scoped(v["sql_query"]) else (
            "tight-excl"
            if all(e in v["sql_query"] for e in TIGHT_EXCLUSIONS)
            else "LOOSE-EXCL"
        )
        print(f"  {v['cqview_id']:<52} {gate:<11} {excl:<13} {v['cqview_name']}")
    if views:
        print(f"\nlast written (PT): {pt(views[0].get('updated_at'))}")


def resolve_golden_world(target_camp, target_label, status_id):
    """Find the target's GOLDEN_WORLD_NAME world and prove it carries `status_id`.

    Returns (world_id, note). world_id is "" when the view must be skipped instead.
    """
    worlds = as_list(call(target_camp, "GET", f"/worlds/?campaign_id={target_camp}"))

    # Some verticals keep a trailing "(Vertical)" suffix on their world names (Ryu's call for
    # Capitol, 2026-08-03), so an exact-name match finds nothing and the view gets skipped even
    # though the world is right there. Strip ONE trailing parenthetical before comparing, the
    # same normalisation clone-sparta-campaign's matcher uses.
    def canon(name):
        return re.sub(r"\s*\([^()]*\)\s*$", "", name or "").strip()

    golden = next(
        (w for w in worlds if canon(w.get("world_name")) == GOLDEN_WORLD_NAME), None
    )
    if not golden:
        return "", (
            f"{target_label} has no world named \"{GOLDEN_WORLD_NAME}\" "
            f"({len(worlds)} worlds) - skipping the world-scoped view"
        )
    w = call(target_camp, "GET", f"/worlds/{golden['world_id']}")
    # World statuses live at status_config.status_defns, NOT .statuses.
    defns = (w.get("status_config") or {}).get("status_defns") or []
    hit = next((s for s in defns if s.get("status_id") == status_id), None)
    if not hit:
        return "", (
            f"{target_label}'s \"{golden['world_name']}\" does NOT carry status {status_id} "
            f"- skipping rather than shipping a permanently empty dashboard"
        )
    return golden["world_id"], (
        f"world-scoped view -> {target_label} \"{golden['world_name']}\" "
        f"({golden['world_id']}), carries \"{hit['status_name']}\""
    )


def cmd_port(src_camp, tgt_camp, target_name, apply_it):
    import re

    target_name = target_name.lower()
    target_label = target_name.capitalize()

    source = get_views(src_camp)
    before = get_views(tgt_camp)
    if not source:
        sys.exit(f"source campaign {src_camp} has no views (or you lack admin there)")

    # Derive the source's short name from its view ids so nothing is hardcoded.
    prefixes = {
        m.group(1)
        for v in source
        if (m := re.match(r"^cqview_([a-z0-9]+)_", v["cqview_id"]))
    }
    src_name = prefixes.pop() if len(prefixes) == 1 else ""
    src_label = src_name.capitalize() if src_name else "(source)"

    print(f"source {src_camp} ({src_label}): {len(source)} views")
    print(f"target {tgt_camp} ({target_label}) before: {len(before)} views")
    if before:
        print("  " + ", ".join(v["cqview_name"] for v in before))

    # A view pinned to one world id cannot be ported as-is; find the target's own world.
    to_world, from_world, note = "", "", "no world-scoped view in the source set"
    scoped = next((v for v in source if world_scoped(v["sql_query"])), None)
    if scoped:
        from_world = re.search(r"world_id\s*=\s*'(world_[0-9a-f]{32})'", scoped["sql_query"]).group(1)
        status_m = re.search(r"task_status_id\s*=\s*'([0-9a-f-]{36})'", scoped["sql_query"])
        if not status_m:
            note = f"cannot read the status filter out of \"{scoped['cqview_name']}\" - skipping it"
        else:
            to_world, note = resolve_golden_world(tgt_camp, target_label, status_m.group(1))
    print(f"\n{note}")

    ported = []
    for v in source:
        if world_scoped(v["sql_query"]) and not to_world:
            continue
        sql = v["sql_query"].replace(src_camp, tgt_camp)
        if to_world and from_world:
            sql = sql.replace(from_world, to_world)
        desc = v["cqview_description"]
        if desc and src_label != "(source)":
            desc = re.sub(src_label, target_label, desc, flags=re.IGNORECASE)
        new = {k: v[k] for k in v if k not in SERVER_FIELDS}
        new["cqview_id"] = (
            v["cqview_id"].replace(f"cqview_{src_name}_", f"cqview_{target_name}_", 1)
            if src_name and v["cqview_id"].startswith(f"cqview_{src_name}_")
            else f"cqview_{target_name}_{v['cqview_id'].removeprefix('cqview_')}"
        )
        new["campaign_id"] = tgt_camp
        new["cqview_description"] = desc
        new["sql_query"] = sql
        ported.append(new)

    print(f"\nporting {len(ported)} views to {target_label}:")
    for v in ported:
        print(f"  {v['cqview_id']:<52} {v['cqview_name']}")

    leaks = [
        v
        for v in ported
        if src_camp in v["sql_query"]
        or (from_world and from_world in v["sql_query"])
        or v["campaign_id"] != tgt_camp
        or (src_name and src_name in f"{v['cqview_id']} {v['cqview_description'] or ''}".lower())
    ]
    if leaks:
        sys.exit(
            f"\nREFUSING TO WRITE: {len(leaks)} view(s) still reference {src_label}: "
            + ", ".join(v["cqview_name"] for v in leaks)
        )

    dropped = [b for b in before if not any(p["cqview_name"] == b["cqview_name"] for p in ported)]
    if dropped:
        print(
            f"\nWARNING: PUT replaces the whole set, so these existing {target_label} views "
            "would be DELETED: " + ", ".join(v["cqview_name"] for v in dropped)
        )

    if not apply_it:
        print("\nDRY RUN - nothing written. Re-run with --apply to PUT.")
        return

    print("\nPUT ...")
    call(
        tgt_camp,
        "PUT",
        f"/campaigns/{tgt_camp}/custom-query-views",
        {"custom_query_views_config": ported},
    )

    # Verify against intent, not against the payload we just sent.
    live = get_views(tgt_camp)
    by_id = {v["cqview_id"]: v for v in live}
    bad = 0
    for want in ported:
        got = by_id.get(want["cqview_id"])
        problems = []
        if not got:
            problems.append("missing after write")
        else:
            if got["campaign_id"] != tgt_camp:
                problems.append("wrong campaign_id")
            if src_camp in got["sql_query"] or (src_name and src_name in got["sql_query"].lower()):
                problems.append(f"still mentions {src_label}")
            if not world_scoped(got["sql_query"]):
                missing = [e for e in TIGHT_EXCLUSIONS if e not in got["sql_query"]]
                if missing:
                    problems.append(f"missing {len(missing)} tight exclusion(s)")
        if problems:
            bad += 1
            print(f"FAIL  {want['cqview_name']}: {'; '.join(problems)}")

    gated = sum(1 for v in live if v["conditional_render_filter"] is not None)
    print(f"\n{target_label} after: {len(live)} views, {bad} with problems")
    print(f"  {gated} role-gated, {len(live) - gated} admin-only")
    print(f"  written at (PT): {pt(live[0].get('updated_at'))}")
    if bad:
        sys.exit(1)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    apply_it = "--apply" in sys.argv
    if not args:
        sys.exit(__doc__)
    if args[0] == "list" and len(args) == 2:
        cmd_list(args[1])
    elif args[0] == "port" and len(args) == 4:
        cmd_port(args[1], args[2], args[3], apply_it)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
