import path_setup  # noqa: F401
import tempfile
import unittest
from pathlib import Path

import engagement.profile_store as profile_store
from engagement.scoring import points_for, tier_for
from engagement.service import EngagementService


class RankedScoringTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        profile_store.PROGRESS_PATH = Path(self._tmpdir.name) / "user_progress.json"
        self.svc = EngagementService()

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_points_and_tiers(self):
        self.assertEqual(points_for("trips_completed", 2), 24)
        self.assertEqual(points_for("accidents_cleared", 1), 20)
        self.assertEqual(tier_for(0)["id"], "bronze")
        self.assertEqual(tier_for(350)["id"], "gold")
        self.assertEqual(tier_for(2800)["id"], "master")

    def test_ranked_mode_awards_score(self):
        self.svc.on_login("racer")
        self.svc.set_play_mode("racer", "ranked")
        self.svc.apply_sim_metrics("racer", {"trips_completed": 2})
        player = self.svc.get_public("racer")
        self.assertEqual(player["play_mode"], "ranked")
        self.assertEqual(player["ranked_score"], 24)
        self.assertEqual(player["ranked_tier"], "bronze")

    def test_sandbox_does_not_award_score(self):
        self.svc.on_login("casual")
        self.svc.set_play_mode("casual", "sandbox")
        self.svc.apply_sim_metrics("casual", {"trips_completed": 5})
        self.assertEqual(self.svc.get_public("casual")["ranked_score"], 0)

    def test_unknown_mode_rejected(self):
        self.svc.on_login("player")
        ok, message, player = self.svc.set_play_mode("player", "arcade")
        self.assertFalse(ok)
        self.assertIn("모드", message)
        self.assertEqual(player["play_mode"], "ranked")

    def test_leaderboard_is_ranked_mode(self):
        self.svc.on_login("ace")
        self.svc.on_login("rookie")
        self.svc.set_play_mode("ace", "ranked")
        self.svc.set_play_mode("rookie", "ranked")
        self.svc.apply_sim_metrics("ace", {"trips_completed": 30})
        self.svc.apply_sim_metrics("rookie", {"trips_completed": 1})
        board = self.svc.leaderboard("rookie")
        self.assertEqual(board["mode"], "ranked")
        self.assertEqual(board["mode_label"], "랭킹전")
        self.assertEqual(board["leaderboard"][0]["login_id"], "ace")
        self.assertEqual(board["leaderboard"][0]["tier"], "gold")
        self.assertEqual(board["me"]["login_id"], "rookie")
        self.assertIn("trips_completed", board["rules"]["points"])

    def test_season_reset_clears_ranked_score(self):
        self.svc.on_login("season")
        self.svc.apply_sim_metrics("season", {"trips_completed": 3})
        self.assertEqual(self.svc.get_public("season")["ranked_score"], 36)

        def mutate(p):
            p["week_id"] = "1999-W01"
            p["ranked_season_id"] = "1999-W01"

        profile_store.update_profile("season", mutate)
        self.svc.apply_sim_metrics("season", {"trips_completed": 1})
        self.assertEqual(self.svc.get_public("season")["ranked_score"], 12)


if __name__ == "__main__":
    unittest.main()
