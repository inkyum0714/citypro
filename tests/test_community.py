import path_setup  # noqa: F401
import unittest

from community import COMMUNITY_COMMENTS, community_page_context
from main import create_app


class CommunityFeedTests(unittest.TestCase):
    def test_snapshot_keeps_thread_authors(self):
        authors = {item["author"] for item in COMMUNITY_COMMENTS}
        ids = {item["id"] for item in COMMUNITY_COMMENTS}
        self.assertEqual(authors, {"verbatim", "cursor-grok"})
        self.assertEqual(ids, {"c12835", "c12547"})
        ctx = community_page_context()
        self.assertEqual(ctx["thread_ref"], "#1300")
        self.assertEqual(ctx["reader_url"], "https://1f916.observer")

    def test_community_page_renders_comment_template(self):
        client = create_app().test_client()
        res = client.get("/community")
        html = res.get_data(as_text=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn('class="community-comment"', html)
        self.assertIn("c12835", html)
        self.assertIn("c12547", html)
        self.assertIn("signals are node-wide this release", html)
        self.assertIn("lot cap over zoning tiles", html.lower())

    def test_guide_labels_node_wide_signals(self):
        client = create_app().test_client()
        html = client.get("/guide").get_data(as_text=True)
        self.assertIn("교차로(노드) 전체 공통", html)
        self.assertIn("접근로별 위상은 아직 없습니다", html)


if __name__ == "__main__":
    unittest.main()
