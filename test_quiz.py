import random
import unittest

import quiz


class QuizTests(unittest.TestCase):
    def test_is_correct(self):
        self.assertTrue(quiz.is_correct("  Strawberry   JAM ", "strawberry jam"))
        self.assertTrue(quiz.is_correct("film", "film/movie"))
        self.assertFalse(quiz.is_correct("", "dog"))
        self.assertFalse(quiz.is_correct("cat", "dog"))

    def test_combine_skips_duplicates(self):
        words = quiz.combine([
            {"id": "a", "words": [{"sv": "hund", "en": "dog"}]},
            {"id": "b", "words": [{"sv": "hund", "en": "dog"}, {"sv": "katt", "en": "cat"}]},
        ])
        self.assertEqual([(w["sv"], w["list_id"]) for w in words], [("hund", "a"), ("katt", "b")])

    def test_session_flow(self):
        words = [{"sv": "hund", "en": "dog"}, {"sv": "katt", "en": "cat"}]
        s = quiz.Session(words, "sv-en", rng=random.Random(1))
        first = s.current.word
        self.assertEqual(s.check("wrong"), (False, True))
        self.assertIsNot(s.current.word, first)  # missed word moved back
        self.assertEqual(s.check(s.answer_of(s.current.word)), (True, True))
        self.assertIs(s.current.word, first)
        self.assertEqual(s.check(s.answer_of(first)), (True, False))  # retry doesn't count
        self.assertIsNone(s.current)
        self.assertEqual((s.mastered, s.hits, s.missed), (2, 1, [first]))

    def test_reveal_counts_as_miss(self):
        s = quiz.Session([{"sv": "hund", "en": "dog"}], "en-sv")
        self.assertEqual(s.question(s.current.word), "dog")
        self.assertTrue(s.reveal())
        self.assertEqual(s.check("hund"), (True, False))
        self.assertEqual(s.hits, 0)


if __name__ == "__main__":
    unittest.main()
