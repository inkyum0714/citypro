import path_setup  # noqa: F401
import unittest

from pathlib import Path

from ads import (
    BLOCKED_AD_CATEGORIES,
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
        self.assertEqual(cfg["format"], "card")
        self.assertEqual(cfg["max_ad_content_rating"], "PG")
        self.assertFalse(cfg["tag_for_child_directed_treatment"])
        self.assertIn("adult", cfg["blocked_categories"])
        self.assertIn("sexual", BLOCKED_AD_CATEGORIES)
        self.assertTrue(cfg["house_ads"])
        self.assertEqual(cfg["placeholder_client"], "ca-pub-YOUR_CLIENT_ID")
        self.assertEqual(cfg["placeholder_slot"], "YOUR_AD_SLOT_ID")
        self.assertEqual(cfg["adsense_slots"], [])

    def test_filters_adult_house_inventory(self):
        kept = filter_house_ads(
            [
                {"id": "ok", "categories": ("games",)},
                {"id": "bad", "categories": ("adult", "games")},
            ]
        )
        self.assertEqual([ad["id"] for ad in kept], ["ok"])

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
        self.assertIn("랭킹전", html)

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

    def test_index_template_has_official_adsense_loader(self):
        html = (BASE_DIR / "frontend" / "templates" / "index.html").read_text(encoding="utf-8")
        self.assertIn(
            "https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=",
            html,
        )
        self.assertIn('crossorigin="anonymous"', html)


if __name__ == "__main__":
    unittest.main()
