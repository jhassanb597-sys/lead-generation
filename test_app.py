"""Unit tests for Lead Empire core helpers (stdlib unittest, no pytest dep)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
from app import clean_url


class TestCleanUrl(unittest.TestCase):
    def test_google_url_q_strips_utm_params(self):
        # /url?q= with utm_* params must fall through to the shared trim loop
        dirty = ("https://www.google.com/url?q=https://example.com/page?"
                 "utm_source=google&utm_medium=cpc&sa=U&ved=123")
        self.assertEqual(clean_url(dirty), "https://example.com/page")

    def test_plain_url_keeps_path_strips_utm(self):
        self.assertEqual(
            clean_url("https://example.com/page?utm_source=x&ved=1"),
            "https://example.com/page",
        )

    def test_na_passthrough(self):
        self.assertEqual(clean_url("N/A"), "N/A")
        self.assertEqual(clean_url(""), "N/A")


if __name__ == "__main__":
    unittest.main()
