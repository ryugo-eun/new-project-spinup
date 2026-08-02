#!/usr/bin/env python3
"""Tests for add_claim_flow.add_claim_flow / verify_claim_flow.

Fixtures are REAL configs from live Studio worlds (2026-08-02). See
test_fix_claim_gating.py for provenance. The claim-flow fixtures carry
status_config + world_settings as well as flow_config, so they are separate files.

Run: python3 test_add_claim_flow.py
"""
import copy, json, pathlib, sys, unittest

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
from add_claim_flow import (  # noqa: E402
    add_claim_flow, verify_claim_flow, status_id_by_name,
    CLAIM_STATUS_NAME, CLAIM_EDGE_ID, TASK_WRITING_STATUS_NAME,
)

FIX = HERE / "test-fixtures"


def load(name):
    return json.loads((FIX / name).read_text())


class CanonicalWorldGetsAWorkingClaimFlow(unittest.TestCase):
    """The starting point: a normal cloned tasking world, no claim flow."""

    def setUp(self):
        self.w = load("world_canonical_tasking_claimflow.json")

    def test_starts_without_a_claim_flow(self):
        self.assertIsNone(status_id_by_name(self.w["status_config"], CLAIM_STATUS_NAME))
        self.assertNotEqual(verify_claim_flow(self.w), [],
                            "a canonical world must NOT already pass the claim-flow check")

    def test_adding_it_produces_a_coherent_claim_world(self):
        rep = add_claim_flow(self.w, new_status_id="test-claim-status-0001")
        self.assertTrue(rep["status_added"])
        self.assertTrue(rep["edge_added"])
        self.assertTrue(rep["visibility_changed"])
        self.assertEqual(verify_claim_flow(self.w), [])

    def test_the_edge_lands_on_task_writing(self):
        rep = add_claim_flow(self.w)
        expected = status_id_by_name(self.w["status_config"], TASK_WRITING_STATUS_NAME)
        self.assertEqual(rep["to_status_id"], expected)
        edge = next(e for e in self.w["flow_config"]["flow_edges"]
                    if e["edge_id"] == CLAIM_EDGE_ID)
        self.assertEqual(edge["to_status_id"], expected)

    def test_the_claimant_becomes_the_owner(self):
        add_claim_flow(self.w)
        edge = next(e for e in self.w["flow_config"]["flow_edges"]
                    if e["edge_id"] == CLAIM_EDGE_ID)
        self.assertEqual(edge["to_owned_by"], "actor")
        self.assertTrue(edge["and_actor_not_created_required"])
        self.assertNotIn("and_actor_owns_required", edge)

    def test_only_writers_see_the_button(self):
        add_claim_flow(self.w)
        edge = next(e for e in self.w["flow_config"]["flow_edges"]
                    if e["edge_id"] == CLAIM_EDGE_ID)
        self.assertEqual(edge["actor_subrole_ids"], ["subrole_preset_writer"])

    def test_visibility_gate_comes_off(self):
        """Without this the writer cannot see an unclaimed task at all."""
        self.assertTrue(self.w["world_settings"]["annotator_visibility_require_assignment"])
        add_claim_flow(self.w)
        self.assertIs(self.w["world_settings"]["annotator_visibility_require_assignment"], False)

    def test_adds_exactly_one_status_and_one_edge(self):
        before_s = len(self.w["status_config"]["status_defns"])
        before_e = len(self.w["flow_config"]["flow_edges"])
        add_claim_flow(self.w)
        self.assertEqual(len(self.w["status_config"]["status_defns"]), before_s + 1)
        self.assertEqual(len(self.w["flow_config"]["flow_edges"]), before_e + 1)

    def test_is_idempotent(self):
        add_claim_flow(self.w)
        snapshot = copy.deepcopy(self.w)
        second = add_claim_flow(self.w)
        self.assertEqual(second["status_added"], False)
        self.assertEqual(second["edge_added"], False)
        self.assertEqual(second["visibility_changed"], False)
        self.assertEqual(self.w, snapshot)

    def test_does_not_touch_existing_statuses_or_edges(self):
        before_s = json.dumps(self.w["status_config"]["status_defns"], sort_keys=True)
        before_e = {e["edge_id"]: json.dumps(e, sort_keys=True)
                    for e in self.w["flow_config"]["flow_edges"]}
        add_claim_flow(self.w)
        after_s = json.dumps([s for s in self.w["status_config"]["status_defns"]
                              if s.get("status_name") != CLAIM_STATUS_NAME], sort_keys=True)
        after_e = {e["edge_id"]: json.dumps(e, sort_keys=True)
                   for e in self.w["flow_config"]["flow_edges"] if e["edge_id"] != CLAIM_EDGE_ID}
        self.assertEqual(after_s, before_s)
        self.assertEqual(after_e, before_e)


class MatchesTheHandBuiltWorld(unittest.TestCase):
    """The engineer's world is the reference implementation. What this script produces
    must be recognisably the same thing, or we have invented a second dialect."""

    def test_hand_built_world_passes_our_own_verifier(self):
        real = load("world_delphi_sample_claimflow.json")
        self.assertEqual(verify_claim_flow(real), [])

    def test_our_edge_matches_the_hand_built_edge_field_for_field(self):
        real = load("world_delphi_sample_claimflow.json")
        theirs = next(e for e in real["flow_config"]["flow_edges"]
                      if e["edge_id"] == CLAIM_EDGE_ID)
        mine_world = load("world_canonical_tasking_claimflow.json")
        add_claim_flow(mine_world)
        mine = next(e for e in mine_world["flow_config"]["flow_edges"]
                    if e["edge_id"] == CLAIM_EDGE_ID)
        # ids are per-world, everything else must agree
        skip = {"from_status_ids", "to_status_id"}
        theirs_cmp = {k: v for k, v in theirs.items() if k not in skip and v not in (False, None)}
        mine_cmp = {k: v for k, v in mine.items() if k not in skip and v not in (False, None)}
        self.assertEqual(mine_cmp, theirs_cmp)

    def test_adding_it_to_the_hand_built_world_is_a_no_op(self):
        real = load("world_delphi_sample_claimflow.json")
        snapshot = copy.deepcopy(real)
        rep = add_claim_flow(real)
        self.assertEqual((rep["status_added"], rep["edge_added"], rep["visibility_changed"]),
                         (False, False, False))
        self.assertEqual(real, snapshot)


class RefusesIncoherentWorlds(unittest.TestCase):
    def test_refuses_a_world_with_no_task_writing_status(self):
        """A claim edge with nowhere to land would create an inescapable status, which
        would strand every seeded task."""
        w = load("world_canonical_tasking_claimflow.json")
        w["status_config"]["status_defns"] = [
            s for s in w["status_config"]["status_defns"]
            if s.get("status_name") != TASK_WRITING_STATUS_NAME]
        with self.assertRaises(ValueError) as ctx:
            add_claim_flow(w)
        self.assertIn("nowhere to land", str(ctx.exception))

    def test_verifier_catches_a_partial_apply_missing_visibility(self):
        """The most likely half-done state: status and edge added, visibility left on.
        The button exists and no writer can see it."""
        w = load("world_canonical_tasking_claimflow.json")
        add_claim_flow(w)
        w["world_settings"]["annotator_visibility_require_assignment"] = True
        bad = verify_claim_flow(w)
        self.assertTrue(any("Claim button never renders" in b for b in bad), bad)

    def test_verifier_catches_an_owner_gated_claim_edge(self):
        """Owner-gating the claim edge makes the task permanently unclaimable, and it is
        the exact mistake someone would make while running fix_claim_gating too broadly."""
        w = load("world_canonical_tasking_claimflow.json")
        add_claim_flow(w)
        next(e for e in w["flow_config"]["flow_edges"]
             if e["edge_id"] == CLAIM_EDGE_ID)["and_actor_owns_required"] = True
        bad = verify_claim_flow(w)
        self.assertTrue(any("nobody can ever claim" in b for b in bad), bad)

    def test_verifier_catches_an_edge_pointing_at_a_deleted_status(self):
        w = load("world_canonical_tasking_claimflow.json")
        add_claim_flow(w)
        edge = next(e for e in w["flow_config"]["flow_edges"] if e["edge_id"] == CLAIM_EDGE_ID)
        edge["to_status_id"] = "status-that-does-not-exist"
        bad = verify_claim_flow(w)
        self.assertTrue(any("lands on a status this world does not have" in b for b in bad), bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
