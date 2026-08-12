import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import build_site

POST = {
    "slug": "2026-08-13-example-story",
    "title": "How Example does X without Y",
    "story_title": "Example: X without Y",
    "story_url": "https://example.com/post",
    "domain": "example.com",
    "hn_id": 44001122,
    "hn_url": "https://news.ycombinator.com/item?id=44001122",
    "date": "2026-08-13",
    "summary": "A short summary.",
    "explainer_url": "https://scrimba.com/explain/abc123",
    "body_html": "<h2>Section</h2><p>Body.</p>",
    "points": 512,
    "num_comments": 341,
}


class TestBuildSite(unittest.TestCase):
    def test_branding(self):
        self.assertEqual(build_site.SITE_NAME, "HN, Explained")
        self.assertEqual(build_site.SITE_URL,
                         "https://ibrhmvk.github.io/hn-explained")

    def test_pills_show_hn_metadata(self):
        html = build_site.pills(POST)
        self.assertIn("▲ 512", html)
        self.assertIn('href="https://news.ycombinator.com/item?id=44001122"', html)
        self.assertIn("341 comments", html)
        self.assertIn('href="https://example.com/post"', html)
        self.assertIn("example.com", html)

    def test_pills_survive_null_url_and_bad_points(self):
        p = dict(POST, story_url=None, points=None)
        html = build_site.pills(p)
        self.assertIn("▲ ?", html)
        self.assertNotIn('href="None"', html)

    def test_post_page(self):
        html = build_site.render_post(POST)
        self.assertIn("scrimba.com/explain/abc123", html)
        self.assertIn("controls-cover", html)
        self.assertIn("HN, Explained", html)
        self.assertIn("<h2>Section</h2>", html)

    def test_index_lists_post(self):
        html = build_site.render_index([POST])
        self.assertIn("p/2026-08-13-example-story.html", html)
        self.assertIn("How Example does X without Y", html)


if __name__ == "__main__":
    unittest.main()
