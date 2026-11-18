"""Applications from form exports, revenue from Stripe exports, shipping from git."""

import contextlib
import io
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest
from datetime import date

from solo_combinator.__main__ import main
from solo_combinator.intake import git_ships_per_week, load_applications, stripe_metrics

# column layout of Stripe's payments export ("Unified payments" CSV)
STRIPE = (
    "id,Created date (UTC),Amount,Amount Refunded,Currency,Converted Amount,Converted Amount Refunded,Fee,Status\n"
    "ch_1,2026-07-03 10:00:00,1000.00,0.00,usd,1000.00,0.00,29.30,Paid\n"
    "ch_2,2026-08-03 10:00:00,1100.00,0.00,usd,1100.00,0.00,32.20,Paid\n"
    "ch_3,2026-09-03 10:00:00,1300.00,100.00,usd,1300.00,100.00,38.00,Paid\n"
    "ch_4,2026-10-02 10:00:00,1500.00,0.00,usd,1500.00,0.00,43.80,Paid\n"
    "ch_5,2026-10-09 10:00:00,900.00,0.00,usd,900.00,0.00,26.40,Failed\n"
    "ch_6,2026-11-01 10:00:00,1600.00,0.00,usd,1600.00,0.00,46.70,Paid\n"
)


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = main(list(argv))
    return code, out.getvalue()


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, name, text):
        p = self.dir / name
        p.write_text(text, encoding="utf-8")
        return str(p)

    def test_form_export_with_loose_headers(self):
        path = self.put(
            "form.csv",
            "Timestamp,Company,Monthly revenue ($),MoM growth %,How many AI agents do you run?,"
            "% of work automated,Team size,Monthly burn,Cash in bank,Ships per week\n"
            '2026-11-01,Ava / InvoiceBot,"$42,000",18%,14,85,1,6000,90000,6\n'
            "2026-11-02,Cy / Idea,0,0,1,10,1,2000,4000,1\n",
        )
        apps = load_applications(path)
        self.assertEqual(apps[0]["name"], "Ava / InvoiceBot")
        self.assertEqual(apps[0]["mrr"], 42000)
        self.assertAlmostEqual(apps[0]["mom_growth"], 0.18)
        self.assertAlmostEqual(apps[0]["automated_share"], 0.85)
        self.assertEqual(apps[0]["agents"], 14)
        code, out = run("rank", path)
        self.assertEqual(code, 0, out)
        self.assertLess(out.index("Ava"), out.index("Cy"))

    def test_form_errors_name_the_line(self):
        with self.assertRaisesRegex(ValueError, "line 3"):
            load_applications(self.put("bad.csv", "Company,MRR\nA,100\nB,lots\n"))
        with self.assertRaisesRegex(ValueError, "name"):
            load_applications(self.put("noname.csv", "MRR,Burn\n1,2\n"))

    def test_stripe_export_gives_mrr_and_growth(self):
        m = stripe_metrics(self.put("stripe.csv", STRIPE), today=date(2026, 11, 18))
        self.assertEqual(m["mrr"], 1500.0)  # October; the failed charge is not revenue
        self.assertEqual(m["months"]["2026-09"], 1200.0)  # refund taken off
        # (1500/1200 - 1) + (1200/1100 - 1) + (1100/1000 - 1), averaged
        self.assertAlmostEqual(m["mom_growth"], round(((1500 / 1200) + (1200 / 1100) + (1100 / 1000) - 3) / 3, 4))
        with self.assertRaisesRegex(ValueError, "Amount"):
            stripe_metrics(self.put("x.csv", "id,foo\n1,2\n"))

    @unittest.skipUnless(shutil.which("git"), "git not installed")
    def test_git_commit_days_per_week(self):
        repo = self.dir / "repo"
        repo.mkdir()
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com"}
        env.update(GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        for i, day in enumerate(("2026-11-02", "2026-11-02", "2026-11-05", "2026-11-10")):
            env["GIT_COMMITTER_DATE"] = env["GIT_AUTHOR_DATE"] = f"{day}T12:00:00"
            subprocess.run(
                ["git", "-C", str(repo), "commit", "-q", "--allow-empty", "-m", f"c{i}"], check=True, env=env
            )
        self.assertEqual(git_ships_per_week(str(repo), 2, today=date(2026, 11, 12)), 1.5)  # 3 days / 2 weeks
        with self.assertRaises(ValueError):
            git_ships_per_week(str(self.dir))


if __name__ == "__main__":
    unittest.main()
