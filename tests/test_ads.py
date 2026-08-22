import path_setup  # noqa: F401
import os
import unittest
from unittest.mock import patch

from ads import (
    BLOCKED_AD_CATEGORIES,
    ads_txt_body,
    adsense_display_unit_html,
    adsense_loader_src,
    filter_house_ads,
    public_ads_config,
)
from main import create_app
from utils.variables import BASE_DIR


class AdsConfigTests(unittest.TestCase):
    def test_defaults_to_family_safe_house_ads(self):
        cfg = public_ads_config()
        self.assertTrue(cfg["enabled"])
        self.assertTrue(cfg["exclude_adult"])
        self.assertEqual(cfg["provider"], "house")
        self.assertEqual(cfg["format"], "hybrid")
        self.assertEqual(cfg["layout"], "top_network_sidebar_network_card_house")
        self.assertEqual(cfg["max_ad_content_rating"], "PG")
        self.assertFalse(cfg["tag_for_child_directed_treatment"])
        self.assertIn("adult", cfg["blocked_categories"])
        self.assertIn("sexual", BLOCKED_AD_CATEGORIES)
        self.assertTrue(cfg["house_ads"])
        self.assertEqual(cfg["placeholder_client"], "ca-pub-YOUR_CLIENT_ID")
        self.assertEqual(cfg["placeholder_slot"], "YOUR_AD_SLOT_ID")
        self.assertEqual(cfg["adsense_slots"], [])
        self.assertEqual(cfg["consent_storage_key"], "cityflow_ad_consent")
        self.assertTrue(cfg["auto_ads_public_only"])
        self.assertEqual(cfg["placements"]["card"]["adsense_slot"], "")

    def test_filters_adult_house_inventory(self):
        kept = filter_house_ads(
            [
                {"id": "ok", "categories": ("games",)},
                {"id": "bad", "categories": ("adult", "games")},
            ]
        )
        self.assertEqual([ad["id"] for ad in kept], ["ok"])

    def test_env_publisher_and_dedicated_slots(self):
        env = {
            "ADSENSE_CLIENT_ID": "ca-pub-1234567890123456",
            "ADSENSE_SLOT_TOP": "1111111111",
            "ADSENSE_SLOT_SIDEBAR": "2222222222",
            "ADFIT_UNIT_ID": "DAN-topunit",
        }
        with patch.dict(os.environ, env, clear=False):
            cfg = public_ads_config()
            self.assertEqual(cfg["adsense_client"], "ca-pub-1234567890123456")
            self.assertEqual(cfg["adsense_slot_top"], "1111111111")
            self.assertEqual(cfg["adsense_slot_sidebar"], "2222222222")
            self.assertEqual(cfg["placements"]["top"]["adsense_slot"], "1111111111")
            self.assertEqual(cfg["placements"]["sidebar"]["adsense_slot"], "2222222222")
            self.assertEqual(cfg["adfit_unit"], "DAN-topunit")
            self.assertEqual(cfg["provider"], "hybrid")
            self.assertIn("google.com, pub-1234567890123456, DIRECT", ads_txt_body(cfg["adsense_client"]))
            app = create_app()
            client = app.test_client()
            ads_txt = client.get("/ads.txt")
            self.assertEqual(ads_txt.status_code, 200)
            self.assertIn(b"google.com, pub-1234567890123456, DIRECT", ads_txt.data)

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
        self.assertIn("max_ad_content_rating", html)
        self.assertIn("rankBoard", html)
        self.assertIn("adSlot", html)
        self.assertIn("sidebarDisplayAd", html)
        self.assertIn("ad-container", html)
        self.assertIn("ca-pub-YOUR_CLIENT_ID", html)
        self.assertIn("YOUR_AD_SLOT_ID", html)
        self.assertIn("adConsentBar", html)
        self.assertIn("ad-exclude", html)
        self.assertIn("랭킹전", html)

    def test_public_pages_without_login(self):
        app = create_app()
        client = app.test_client()
        guide = client.get("/guide")
        self.assertEqual(guide.status_code, 200)
        guide_html = guide.get_data(as_text=True)
        self.assertIn("CITYFLOW_ADS", guide_html)
        self.assertIn("IDM", guide_html)
        self.assertIn("adConsentBar", guide_html)
        ranks = client.get("/ranks")
        self.assertEqual(ranks.status_code, 200)
        self.assertIn("publicRankList", ranks.get_data(as_text=True))
        community = client.get("/community")
        self.assertEqual(community.status_code, 200)
        community_html = community.get_data(as_text=True)
        self.assertIn("c12835", community_html)
        self.assertIn("verbatim", community_html)
        self.assertIn("node-wide this release", community_html)
        self.assertIn("/community", client.get("/login").get_data(as_text=True))
        login = client.get("/login")
        self.assertEqual(login.status_code, 200)
        self.assertIn("CITYFLOW_ADS", login.get_data(as_text=True))
        board = client.get("/api/engagement/leaderboard")
        self.assertEqual(board.status_code, 200)
        self.assertTrue(board.get_json().get("ok"))
        ads_txt = client.get("/ads.txt")
        self.assertEqual(ads_txt.status_code, 404)

    def test_display_ads_snippet_matches_official_format(self):
        client = "ca-pub-XXXXXXXXXXXXXXXX"
        slot = "XXXXXXXXXX"
        html = adsense_display_unit_html(client, slot)
        self.assertIn('class="adsbygoogle"', html)
        self.assertIn('style="display:block"', html)
        self.assertIn(f'data-ad-client="{client}"', html)
        self.assertIn(f'data-ad-slot="{slot}"', html)
        self.assertIn('data-ad-format="auto"', html)
        self.assertIn('data-full-width-responsive="true"', html)
        self.assertEqual(
            adsense_loader_src(client),
            f"https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={client}",
        )

    def test_frontend_ads_js_uses_display_ads_snippet(self):
        src = (BASE_DIR / "frontend" / "js" / "ads.js").read_text(encoding="utf-8")
        self.assertIn("pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=", src)
        self.assertIn("crossOrigin: 'anonymous'", src)
        self.assertIn('data-ad-format="auto"', src)
        self.assertIn('data-full-width-responsive="true"', src)
        self.assertIn('style="display:block"', src)
        self.assertIn("(window.adsbygoogle = window.adsbygoogle || []).push({})", src)
        self.assertIn("requestNonPersonalizedAds", src)
        self.assertNotIn("pickRandomSlot", src)
        self.assertIn("prefersKoreanDemand", src)

    def test_index_template_has_official_adsense_loader(self):
        html = (BASE_DIR / "frontend" / "templates" / "_ad_head.html").read_text(encoding="utf-8")
        self.assertIn(
            "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=",
            html,
        )
        self.assertIn('crossorigin="anonymous"', html)
        self.assertIn("pauseAdRequests", html)


if __name__ == "__main__":
    unittest.main()
