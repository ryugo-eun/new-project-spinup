#!/usr/bin/env python3
"""Wire ONE Studio world exactly the way a CAMPAIGN clone wires it.

There is no second hook implementation here. This script imports
`clone-sparta-campaign/clone_sparta_campaign.py` (the current engine, adopt mode 2026-07-29) and
calls its own functions, so a single cloned world ends up with the same hooks, the same forked
qc_specs, the same verifier, the same sparta_external_agent and the same SER-Heal remix that
`clone-sparta-campaign` produces:

  fork_campaign_specs()  fork the campaign-scoped qc_specs, by name, idempotent
  port_hooks()           port the hook chain read LIVE off the source tasking world,
                         remapping qc_spec ids in the PAYLOAD and the PREDICATE,
                         dropping the 3 Prometheus targets, skipping hooks whose target
                         remix is absent from the target world
  wire_runner_worlds()   world-level Sparta verifier + sparta_external_agent + SER-Heal remix

The hook set is never read from a stored file. The old `canonical_hooks.json` capture drifted to
18 of 22 hooks and was deleted for exactly that reason: the source of truth is the live
`[Live New Flow] Final Tasking World` in the source campaign, which is what a campaign clone ports.

Usage
  export RLS_API_KEY=...                     # must reach BOTH campaigns
  export SPARTA_SRC_CAMPAIGN=camp_...        # default: the [CLONE ME] template campaign
  python3 wire_world.py --campaign camp_TARGET --world world_TARGET [--builder] [--execute]

Dry run by default. --builder wires the 4-hook Golden World Building set instead of the tasking set.
"""
import argparse, importlib.util, pathlib, sys

ENGINE = (pathlib.Path(__file__).resolve().parent.parent
          / "clone-sparta-campaign" / "clone_sparta_campaign.py")
CANONICAL_TASKING_HOOKS = 22   # verified live on the [CLONE ME] tasking world, 2026-07-29
CANONICAL_BUILDER_HOOKS = 4


def load_engine():
    if not ENGINE.exists():
        sys.exit(f"ABORT: engine not found at {ENGINE}. clone-studio-world delegates its hook and "
                 "runner wiring to clone-sparta-campaign; both skills must be installed.")
    spec = importlib.util.spec_from_file_location("clone_sparta_campaign", ENGINE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)          # safe: the engine guards main() behind __main__
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", required=True, help="TARGET campaign id (camp_...)")
    ap.add_argument("--world", required=True, help="TARGET world id (world_...)")
    ap.add_argument("--builder", action="store_true", help="wire the GWB 4-hook set, not tasking")
    ap.add_argument("--execute", action="store_true", help="write (default is a dry run)")
    a = ap.parse_args()

    eng = load_engine()
    eng.EXECUTE = a.execute
    tag = "EXECUTE" if a.execute else "DRY-RUN"
    src = eng.SRC_CAMPAIGN
    src_canon = eng.WORLD_GWB if a.builder else eng.WORLD_TASKING
    expected = CANONICAL_BUILDER_HOOKS if a.builder else CANONICAL_TASKING_HOOKS

    print(f"[{tag}] source campaign {src}, reference world {src_canon!r}")
    src_worlds = eng.match_canonical_worlds(src, [src_canon])
    src_world_id = src_worlds[src_canon]["world_id"]

    # The hook set, read LIVE. Never a stored capture.
    _, ref_hooks = eng.api("GET", f"/hooks/world/{src_world_id}", src)
    ref_hooks = ref_hooks if isinstance(ref_hooks, list) else []
    if not ref_hooks:
        sys.exit(f"ABORT: reference world {src_world_id} returned 0 hooks. Wrong campaign, wrong "
                 "world, or a key that cannot read it. Refusing to wire from an empty reference.")
    print(f"[{tag}] reference carries {len(ref_hooks)} hooks "
          f"({sum(1 for h in ref_hooks if not h.get('hook_enabled'))} of them disabled, preserved as-is)")

    # Same target-world checks the campaign engine makes, on the one world we were given.
    _, tgt = eng.api("GET", f"/worlds/{a.world}", a.campaign)
    if not tgt.get("world_id"):
        sys.exit(f"ABORT: cannot read target world {a.world} in {a.campaign}.")
    label = tgt.get("world_name") or a.world
    print(f"[{tag}] target {label!r} ({a.world}) in {a.campaign}")

    qcmap = eng.fork_campaign_specs(src, a.campaign)
    eng.port_hooks(ref_hooks, a.world, a.campaign, qcmap, drop_prometheus=True, label=label)

    if not a.builder:
        # Reuse the engine's runner wiring verbatim by pointing its canonical list at this world.
        eng.RUNNER_WORLDS = [label]
        eng.wire_runner_worlds(a.campaign, {label: tgt})

    # Verify against the live count, because port_hooks dedupes BY HOOK NAME and the canonical set
    # contains repeated names (4x "Auto-sync on ready for delivery", 2x "...preference labels").
    # On a re-run after a partial failure it will skip every duplicate of a name already present,
    # so a silent shortfall is possible. The count check turns that into a loud one.
    _, final = eng.api("GET", f"/hooks/world/{a.world}", a.campaign)
    final = final if isinstance(final, list) else []
    if a.execute:
        if len(final) == expected:
            print(f"\nOK: {label!r} has {len(final)} hooks, matching the canonical set.")
        else:
            sys.exit(f"\nNOT DONE: {label!r} has {len(final)} hooks, canonical is {expected}. "
                     "port_hooks dedupes by name and the set has repeated names, so re-running will "
                     "NOT fill the gap. Diff against the reference world and create the missing "
                     "hooks explicitly.")
    else:
        print(f"\nDRY RUN. Target currently has {len(final)} hooks; canonical is {expected}. "
              "Re-run with --execute to write.")


if __name__ == "__main__":
    main()
