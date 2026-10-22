import json
import tempfile
import unittest
from pathlib import Path

from careergraph import config as C
from careergraph.build import build
from careergraph.reason import KnowledgeGraph, answer
from careergraph.render import render
from fixtures import THREADS


class Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = Path(tempfile.mkdtemp())
        build(THREADS, cls.dir, min_comments=1, max_threads=100, source="synthetic test fixture")
        cls.kg = KnowledgeGraph(cls.dir)

    def test_all_node_types_present(self):
        for t in ("Question", "Situation", "Option", "Advice", "Outcome", "Factor", "Author"):
            self.assertTrue(self.kg.by_type[t], t)

    def test_json_state_is_valid_and_matches_sqlite(self):
        data = json.loads((self.dir / "knowledge_state.json").read_text(encoding="utf-8"))
        self.assertEqual(sum(len(v) for v in data["nodes"].values()), len(self.kg.nodes))
        self.assertIn("edge_types", data["schema"])

    def test_disagreement_edge(self):
        self.assertIn(("DISAGREES", "adv:c11"), [(t, d) for t, d, _ in self.kg.out["adv:c13"]])

    def test_new_situation(self):
        v = answer(self.kg, "I have 2 YOE at TCS, 4.5 LPA, got a product offer of 12 LPA, 90 days notice")
        self.assertEqual(v["parsed_situation"]["current_tier"], "service")
        self.assertGreaterEqual(v["evidence_base"]["similar_situations"], 3)
        self.assertIsNotNone(v["recommendation"])
        self.assertIn(v["recommendation"]["confidence"], ("low", "medium", "high"))
        self.assertTrue(v["outcomes"])
        top = v["option_scores"][0]
        if v["recommendation"]["confidence"] != "low":
            self.assertGreaterEqual(sum(top["outcomes"][k] for k in ("good", "bad", "mixed")), 2)
        self.assertIn("RECOMMENDATION", render(v))

    def test_experience_thread_gives_outcomes_only(self):
        self.assertNotIn("q:t6", self.kg.q_situation)
        self.assertNotIn("adv:c61", self.kg.nodes)
        sid, props = self.kg.edges("out:c61", "FROM")[0]
        s = self.kg.nodes[sid]
        self.assertEqual((s["source"], s["current_tier"], props["inherited"]), ("experience_thread", "service", True))
        self.assertEqual((self.kg.nodes["out:c62"]["chose"], self.kg.nodes["out:c62"]["polarity"]), ("switch_now", "good"))

    def test_tactics_are_tips_not_decisions(self):
        v = answer(self.kg, "2 YOE at TCS, 4 LPA, offer from Amazon at 18 LPA, 90 days notice")
        self.assertIn(v["recommendation"]["option"], C.MAIN_OPTIONS)
        self.assertTrue(all(r["option"] in C.MAIN_OPTIONS for r in v["option_scores"]))
        self.assertIn("negotiate", [t["option"] for t in v["tips"]])

    def test_only_decisions_that_fit_are_scored(self):
        v = answer(self.kg, "2 YOE at TCS, 4 LPA, offer from Amazon at 18 LPA, 90 days notice")
        self.assertEqual(v["position"], "offer_in_hand")
        self.assertTrue({r["option"] for r in v["option_scores"]} <= set(C.APPLICABLE["offer_in_hand"]))
        f = answer(self.kg, "Final year student, got a TCS offer at 3.6 LPA. Should I join or wait for product?")
        self.assertEqual(f["position"], "fresher")
        self.assertNotIn("resign_without_offer", [r["option"] for r in f["option_scores"]])

    def test_unusable_input(self):
        v = answer(self.kg, "hello there")
        self.assertIsNone(v["recommendation"])
        self.assertTrue(v["warnings"])


if __name__ == "__main__":
    unittest.main()
