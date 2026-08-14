import path_setup  # noqa: F401
import unittest

from flask import Flask
from utils.i18n import t


class I18nTests(unittest.TestCase):
    def test_default_korean_without_request(self):
        self.assertIn("만료", t("coupon.expired"))
        self.assertIn("무료 체험", t("coupon.trial_expired"))

    def test_english_override(self):
        self.assertEqual(t("coupon.expired", lang="en"), "This coupon has expired.")
        self.assertEqual(t("coupon.trial_expired", lang="en"), "Your free trial has expired.")

    def test_cookie_selects_english(self):
        app = Flask(__name__)
        with app.test_request_context(headers={"Cookie": "cityflow_lang=en"}):
            self.assertEqual(t("coupon.expired"), "This coupon has expired.")


if __name__ == "__main__":
    unittest.main()
