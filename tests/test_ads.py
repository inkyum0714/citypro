import path_setup  # noqa: F401
import unittest

from ads import BLOCKED_AD_CATEGORIES, public_ads_config
from main import create_app


class AdsConfigTests(unittest.TestCase):
    def test_defaults_to_family_safe_house_ads(self):
        cfg = public_ads_config()
        self.assertTrue(cfg["enabled"])
        self.assertTrue(cfg["exclude_adult"])
        self.assertEqual(cfg["provider"], "house")
        self.assertIn("adult", cfg["blocked_categories"])
        self.assertIn("sexual", BLOCKED_AD_CATEGORIES)

    def test_index_includes_top_ad_bar(self):
        app = create_app()
        client = app.test_client()
        with client.session_transaction() as sess:
            sess["login_id"] = "adviewer"
            sess["name"] = "Ad Viewer"
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("topAdBar", html)
        self.assertIn("CITYFLOW_ADS", html)
        self.assertIn("exclude_adult", html)


if __name__ == "__main__":
    unittest.main()
