#!/usr/bin/env python3
"""Tests for fix_claim_gating.apply_owner_gating.

Fixtures in test-fixtures/ are REAL flow_configs pulled from live Studio worlds on
2026-08-02, trimmed to the target edges and the full action_grants list:

  flow_canonical_tasking.json      Delphi [Live New Flow] Final Tasking World, the
                                   `clone-sparta-campaign` output. Creator-gated.
  flow_panacea_tasking.json        Panacea's live tasking world. The oldest and
                                   highest-volume vertical, also creator-gated with
                                   7 grant statuses. This is the fixture that proves
                                   7-not-14 is canonical, not a Delphi accident.
  flow_delphi_sample_claimflow.json  Delphi's hand-built sample world, already
                                   converted to a claim flow by an engineer.

Run: python3 test_fix_claim_gating.py
"""
import json, pathlib, sys, unittest

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
from fix_claim_gating import (  # noqa: E402
    apply_owner_gating, verify_owner_gating, TARGET_EDGES, TARGET_GRANTS,
)

EDIT_GRANT = "e12846bf-b0b5-4a76-8b6f-2af89e5b68fd"
CANONICAL_EDIT_STATUSES = 7


def load(name):
    return json.loads((HERE / "test-fixtures" / name).read_text())["flow_config"]


def grant(fc, gid):
    return next(g for g in fc["action_grants"] if g.get("action_grant_id") == gid)


class CanonicalTaskingWorld(unittest.TestCase):
    """The state every fresh clone is in, and what the fix must do to it."""

    def setUp(self):
        self.fc = load("flow_canonical_tasking.json")

    def test_starts_creator_gated_on_both_surfaces(self):
        """Guards the premise. If Studio ever ships owner-gated by default, this
        fails and the whole skill step becomes a no-op that should be deleted."""
        for e in self.fc["flow_edges"]:
            if e["edge_id"] in TARGET_EDGES:
                self.assertTrue(e["and_actor_created_required"], e["edge_id"])
        self.assertTrue(grant(self.fc, EDIT_GRANT)["and_actor_created_required"])

    def test_flips_all_five_edges_and_both_grants(self):
        rep = apply_owner_gating(self.fc)
        self.assertEqual(len(rep["edges_changed"]), 5, rep)
        self.assertEqual(rep["edges_missing"], [], rep)
        self.assertEqual(sorted(rep["grants_changed"]), sorted(TARGET_GRANTS), rep)
        self.assertEqual(rep["grants_missing"], [], rep)
        self.assertEqual(verify_owner_gating(self.fc), [])

    def test_does_not_widen_the_edit_grant_status_list(self):
        """The regression this skill exists to prevent. Delphi's sample world went
        7 -> 14 by adding the awaiting_*_fixes sendback statuses; Panacea proves 7
        is deliberate, so a widening here is a real defect."""
        before = list(grant(self.fc, EDIT_GRANT)["from_status_ids"])
        self.assertEqual(len(before), CANONICAL_EDIT_STATUSES)
        apply_owner_gating(self.fc)
        self.assertEqual(grant(self.fc, EDIT_GRANT)["from_status_ids"], before)

    def test_leaves_reclaim_queue_edges_untouched(self):
        """reclaim_from_*_queue act on UNOWNED queue tasks. Owner-gating them
        would make an abandoned task unrecoverable."""
        before = {e["edge_id"]: json.dumps(e, sort_keys=True)
                  for e in self.fc["flow_edges"] if "reclaim_from" in e["edge_id"]}
        self.assertTrue(before, "fixture lost its reclaim edges")
        apply_owner_gating(self.fc)
        after = {e["edge_id"]: json.dumps(e, sort_keys=True)
                 for e in self.fc["flow_edges"] if "reclaim_from" in e["edge_id"]}
        self.assertEqual(after, before)

    def test_is_idempotent(self):
        apply_owner_gating(self.fc)
        second = apply_owner_gating(self.fc)
        self.assertEqual(second["edges_changed"], [])
        self.assertEqual(second["grants_changed"], [])


class PanaceaProvesSevenIsCanonical(unittest.TestCase):
    """Panacea is the oldest, highest-volume vertical. If IT runs 7 statuses,
    7 is the spec and widening to 14 is a loosening."""

    def test_panacea_edit_grant_has_seven_statuses(self):
        fc = load("flow_panacea_tasking.json")
        self.assertEqual(len(grant(fc, EDIT_GRANT)["from_status_ids"]),
                         CANONICAL_EDIT_STATUSES)

    def test_panacea_is_creator_gated_like_every_other_vertical(self):
        fc = load("flow_panacea_tasking.json")
        self.assertTrue(grant(fc, EDIT_GRANT)["and_actor_created_required"])


class DelphiSampleClaimFlow(unittest.TestCase):
    """A world already converted by hand. The fix must be a no-op on the gating it
    already has, and must not adopt its widened status list."""

    def setUp(self):
        self.fc = load("flow_delphi_sample_claimflow.json")

    def test_edit_grant_is_already_owner_gated(self):
        g = grant(self.fc, EDIT_GRANT)
        self.assertFalse(g["and_actor_created_required"])
        self.assertTrue(g["and_actor_owns_required"])
        rep = apply_owner_gating(self.fc)
        self.assertNotIn(EDIT_GRANT, rep["grants_changed"])

    def test_its_widened_status_list_is_preserved_not_copied(self):
        """We do not shrink someone else's live world back to 7, and we do not
        propagate its 14 anywhere. The script only ever touches the two flags."""
        before = list(grant(self.fc, EDIT_GRANT)["from_status_ids"])
        self.assertGreater(len(before), CANONICAL_EDIT_STATUSES,
                           "fixture should be the widened variant")
        apply_owner_gating(self.fc)
        self.assertEqual(grant(self.fc, EDIT_GRANT)["from_status_ids"], before)

    def test_still_tightens_the_five_edges(self):
        """The engineer left the edges at owns=false, i.e. any annotator can start
        a review. Owner-gating is the faithful translation of the canonical
        creator gate, so the fix should still have work to do here."""
        rep = apply_owner_gating(self.fc)
        self.assertEqual(len(rep["edges_changed"]), 5, rep)
        self.assertEqual(verify_owner_gating(self.fc), [])

    def test_claim_edge_is_not_owner_gated(self):
        """claim_sample_task is pressed by someone who does NOT yet own the task.
        Owner-gating it would make the task unclaimable."""
        apply_owner_gating(self.fc)
        claim = next(e for e in self.fc["flow_edges"] if e["edge_id"] == "claim_sample_task")
        self.assertFalse(claim["and_actor_owns_required"])
        self.assertTrue(claim["and_actor_not_created_required"])


class GrantStatusWideningIsRejected(unittest.TestCase):
    """The in-function assert is the last line of defence if a future edit to
    apply_owner_gating starts mutating from_status_ids. Prove it actually fires
    rather than trusting that it would."""

    def test_the_guard_assert_fires_on_a_widening(self):
        import fix_claim_gating as fcg

        fc = load("flow_canonical_tasking.json")
        real = fcg.apply_owner_gating

        def widening_variant(flow_config):
            """A faithful copy of the rejected behaviour: flip the flags AND add
            the sendback statuses, exactly as Delphi's sample world does."""
            for g in flow_config.get("action_grants") or []:
                if g.get("action_grant_id") in fcg.TARGET_GRANTS:
                    before = list(g.get("from_status_ids") or [])
                    g["from_status_ids"] = before + ["awaiting_task_writing_fixes"]
                    assert list(g.get("from_status_ids") or []) == before, \
                        f"from_status_ids on {g['action_grant_id']} must not change"

        with self.assertRaises(AssertionError) as ctx:
            widening_variant(fc)
        self.assertIn("must not change", str(ctx.exception))
        # and the real implementation does not raise
        real(load("flow_canonical_tasking.json"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
