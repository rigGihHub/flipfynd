import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fetch_tradera_pages
import src.tradera_fetcher as tradera_fetcher


class FetchStateProgressTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state_path = Path(self.tmp.name) / "state.json"
        self.state_patch = patch.object(tradera_fetcher, "STATE_PATH", self.state_path)
        self.state_patch.start()

    def tearDown(self):
        self.state_patch.stop()
        self.tmp.cleanup()

    def test_progress_state_tracks_page_and_counts(self):
        tradera_fetcher.start_fetch_run("all")
        tradera_fetcher.start_fetch_category("Hockey - NHL")
        tradera_fetcher.record_fetch_progress("Hockey - NHL", 4, 4, 160, 37)
        state = tradera_fetcher.load_fetch_state()
        run = state["active_run"]
        self.assertEqual(run["current_category"], "Hockey - NHL")
        self.assertEqual(run["current_page"], 4)
        self.assertEqual(run["category_items_seen"], 160)
        self.assertEqual(run["category_new_items"], 37)
        self.assertTrue(state["categories"]["Hockey - NHL"]["running"])

    def test_completed_category_is_recorded(self):
        tradera_fetcher.start_fetch_run("all")
        tradera_fetcher.start_fetch_category("Hockey - NHL")
        tradera_fetcher.finish_fetch_category("Hockey - NHL", 8, 300, 40, "slut")
        state = tradera_fetcher.load_fetch_state()
        self.assertIn("Hockey - NHL", state["active_run"]["completed_categories"])
        self.assertFalse(state["categories"]["Hockey - NHL"]["running"])
        self.assertEqual(state["categories"]["Hockey - NHL"]["last_pages_scanned"], 8)


class ProgressivePersistenceTests(unittest.TestCase):
    def test_fetch_one_category_saves_each_page_before_completion(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "items.json"
            state = Path(td) / "state.json"

            def fake_fetch(**kwargs):
                callback = kwargs["page_callback"]
                item1 = {"titel": "One", "lank": "https://example/1", "source_category": "Hockey - NHL"}
                item2 = {"titel": "Two", "lank": "https://example/2", "source_category": "Hockey - NHL"}
                callback(category_name="Hockey - NHL", page_number=1, page_items=[item1], pages_scanned=1, items_seen=1, new_items=1)
                self.assertEqual(len(tradera_fetcher.load_items(output)), 1)
                callback(category_name="Hockey - NHL", page_number=2, page_items=[item2], pages_scanned=2, items_seen=2, new_items=2)
                self.assertEqual(len(tradera_fetcher.load_items(output)), 2)
                tradera_fetcher.record_fetch_summary("Hockey - NHL", 2, 2, 2, "test")
                return [item1, item2], []

            with patch.object(tradera_fetcher, "STATE_PATH", state), \
                 patch.object(fetch_tradera_pages, "fetch_tradera_category", side_effect=fake_fetch):
                fetch_tradera_pages.fetch_one_category("Hockey - NHL", "full", False, output, 20)
                self.assertEqual(len(tradera_fetcher.load_items(output)), 2)


if __name__ == "__main__":
    unittest.main()
