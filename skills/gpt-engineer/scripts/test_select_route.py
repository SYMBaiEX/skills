import copy
import unittest

from routes import SUPPORTED_MODELS
from select_route import hook_identity, plan


def request(model="gpt-5.6-luna"):
    return {"parent": {"model": model, "effort": "high", "source": "runtime-turn", "subjectId": "parent"},
            "capabilities": {"models": list(SUPPORTED_MODELS), "efforts": {m: ["low", "medium", "high"] for m in SUPPORTED_MODELS},
                             "modelSelector": True, "effortSelector": True}}


class RouteTests(unittest.TestCase):
    def test_all_four_parents_remain_selected(self):
        for model in SUPPORTED_MODELS:
            result = plan(request(model))
            self.assertEqual(result["spawn"], {"model": model, "reasoning_effort": "high", "fork_turns": "none"})
            self.assertEqual(result["effectiveChild"], {"model": None, "effort": None, "serviceTier": None})

    def test_unknown_or_saved_parent_does_not_guess(self):
        for source in ("configuration", "self-description", "unavailable"):
            value = request()
            value["parent"]["source"] = source
            self.assertEqual(plan(value)["action"], "parent-only")

    def test_explicit_mixed_policy_preserves_parent(self):
        value = request("gpt-5.6-sol")
        value.update(policy="mixed-model", child={"model": "gpt-5.6-luna", "effort": "medium"})
        result = plan(value)
        self.assertEqual(result["parent"]["effectiveModel"], "gpt-5.6-sol")
        self.assertEqual(result["spawn"]["model"], "gpt-5.6-luna")

    def test_mismatch_and_legacy_fail(self):
        for model in ("gpt-6-astra", "gpt-5.4"):
            value = request()
            value["child"] = {"model": model}
            with self.assertRaises(ValueError):
                plan(value)

    def test_unavailable_capability_keeps_direct_work(self):
        for capability in ("modelSelector", "effortSelector"):
            value = request()
            value["capabilities"][capability] = False
            self.assertEqual(plan(value)["action"], "parent-only")
        value = request()
        value["child"] = {"serviceTier": "fast"}
        self.assertEqual(plan(value)["action"], "parent-only")

    def test_child_evidence_subject_and_mismatch(self):
        value = request()
        value["childId"] = "child"
        value["effectiveChild"] = {"source": "runtime-child", "subjectId": "child", "model": "gpt-5.6-luna"}
        self.assertEqual(plan(value)["effectiveChild"]["model"], "gpt-5.6-luna")
        for update in ({"subjectId": "parent"}, {"source": "codex-hook"}, {"model": "gpt-6-astra"}):
            bad = copy.deepcopy(value)
            bad["effectiveChild"].update(update)
            with self.assertRaises(ValueError):
                plan(bad)

    def test_hook_never_promotes_child_or_leaks_text(self):
        for event in ("SubagentStart", "SubagentStop", "Unknown"):
            result = hook_identity({"hook_event_name": event, "model": "gpt-6-astra", "prompt": "SECRET"})
            self.assertIsNone(result["model"])
            self.assertNotIn("SECRET", str(result))
        self.assertEqual(hook_identity({"hook_event_name": "Stop", "model": "gpt-5.6-sol"})["model"], "gpt-5.6-sol")

    def test_invalid_input(self):
        for value in ([], {"policy": "cheap"}, {"policy": "mixed-model"}, {"parent": []}):
            with self.assertRaises(ValueError):
                plan(value)

    def test_parent_hook_normalizer_round_trips_into_planner(self):
        value = request("gpt-5.6-sol")
        value["parent"] = hook_identity({"hook_event_name": "Stop", "model": "gpt-5.6-sol"})
        value["child"] = {"effort": "medium"}
        result = plan(value)
        self.assertEqual(result["spawn"]["model"], "gpt-5.6-sol")
        self.assertEqual(result["parent"]["effectiveModel"], "gpt-5.6-sol")


if __name__ == "__main__":
    unittest.main()
