import sys, os, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from pick_story import eligible

HIT = {"objectID": "101", "title": "A story", "url": "https://ex.com/a",
       "points": 250, "num_comments": 90}


def hit(**over):
    h = dict(HIT)
    h.update(over)
    return h


class TestEligible(unittest.TestCase):
    def test_maps_fields(self):
        [c] = eligible([HIT], set())
        self.assertEqual(c, {"hn_id": 101, "title": "A story",
                             "url": "https://ex.com/a", "points": 250,
                             "num_comments": 90,
                             "hn_url": "https://news.ycombinator.com/item?id=101"})

    def test_filters_low_points_and_covered(self):
        hits = [hit(objectID="1", points=99), hit(objectID="2"), hit(objectID="3")]
        got = eligible(hits, seen_ids={3})
        self.assertEqual([c["hn_id"] for c in got], [2])

    def test_sorts_by_points_and_caps_at_10(self):
        hits = [hit(objectID=str(i), points=100 + i) for i in range(15)]
        got = eligible(hits, set())
        self.assertEqual(len(got), 10)
        self.assertEqual(got[0]["points"], 114)

    def test_null_url_kept_and_missing_fields_safe(self):
        [c] = eligible([hit(url=None, points=150, num_comments=None)], set())
        self.assertIsNone(c["url"])
        self.assertEqual(c["num_comments"], 0)


if __name__ == "__main__":
    unittest.main()
