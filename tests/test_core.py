import json
import pathlib
import unittest

from solo_combinator import Application, post_money_safe, rank, score_application

EXAMPLES = pathlib.Path(__file__).resolve().parent.parent / "examples" / "applications.json"


class Tests(unittest.TestCase):
    def test_strong_app_accepted(self):
        s = score_application(
            Application(
                "x",
                mrr=50_000,
                mom_growth=0.25,
                agents=12,
                automated_share=0.9,
                monthly_burn=5000,
                cash=100_000,
                ships_per_week=6,
            )
        )
        self.assertEqual(s.decision, "accept")
        self.assertGreaterEqual(s.total, 80)

    def test_flags(self):
        s = score_application(Application("y", monthly_burn=1000, cash=1000, users=0, humans=3))
        self.assertEqual(len(s.flags), 3)
        self.assertEqual(s.decision, "pass")

    def test_rank_example_order(self):
        scores = rank(json.loads(EXAMPLES.read_text()))
        self.assertEqual(scores[0].name, "Ava / InvoiceBot")
        self.assertEqual(scores[-1].decision, "pass")

    def test_safe(self):
        r = post_money_safe(125_000, 2_000_000, 8_000_000, 2_000_000)
        self.assertAlmostEqual(r["ownership_at_conversion"], 0.0625)
        self.assertAlmostEqual(r["ownership_after_round"], 0.05)
        with self.assertRaises(ValueError):
            post_money_safe(10, 5)
        with self.assertRaises(ValueError):
            post_money_safe(125_000, 2_000_000, -8_000_000, 2_000_000)

    def test_gaming_values_and_junk_input_are_rejected(self):
        for bad in ({"monthly_burn": -50_000}, {"automated_share": 10}, {"mrr": "5000"}, {"mrr": float("nan")}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                rank([{"name": "x", "mrr": 5000, **bad}])
        for junk in (None, {"name": "x"}, [1]):
            with self.subTest(junk=junk), self.assertRaises(ValueError):
                rank(junk)


if __name__ == "__main__":
    unittest.main()
