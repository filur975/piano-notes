import importlib.util
import os
import tempfile
import unittest

import store

HAS_TK = importlib.util.find_spec("tkinter") is not None


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_file = store.DATA_FILE
        store.DATA_FILE = os.path.join(self.tmp.name, "lists.json")

    def tearDown(self):
        store.DATA_FILE = self.old_file
        self.tmp.cleanup()

    def test_example_list_created(self):
        self.assertEqual(len(store.load_data()["lists"]), 1)
        self.assertTrue(os.path.exists(store.DATA_FILE))

    def test_corrupt_file_backed_up(self):
        with open(store.DATA_FILE, "w") as f:
            f.write("{not json")
        self.assertEqual(len(store.load_data()["lists"]), 1)
        self.assertTrue(os.path.exists(store.DATA_FILE + ".bak"))

    def test_clean_words_keeps_counters(self):
        old = [{"sv": "bil", "en": "car", "correct": 3, "wrong": 1}]
        words = store.clean_words([{"sv": " bil ", "en": "car"}, {"sv": "", "en": "x"}, {"sv": "hus", "en": "house"}],
                                  old)
        self.assertEqual(words, [{"sv": "bil", "en": "car", "correct": 3, "wrong": 1},
                                 {"sv": "hus", "en": "house", "correct": 0, "wrong": 0}])

    @unittest.skipUnless(HAS_TK, "tkinter not installed")
    def test_desktop_save_record_delete(self):
        import glosor_tk
        lst = glosor_tk.save_list(None, "Test", [{"sv": "bil", "en": "car"}, {"sv": "", "en": "x"}])
        self.assertEqual(len(lst["words"]), 1)
        glosor_tk.record_result({**lst["words"][0], "list_id": lst["id"]}, True)
        lst = glosor_tk.save_list(lst["id"], "Nytt", [{"sv": "bil", "en": "car"}])
        self.assertEqual(lst["words"][0]["correct"], 1)
        glosor_tk.delete_list(lst["id"])
        self.assertEqual(len(glosor_tk.load_lists()), 1)  # only the example list left


if __name__ == "__main__":
    unittest.main()
