import random
import unittest

import notes


class NotesTests(unittest.TestCase):
    def test_key_names(self):
        names = [notes.key_name(f) for f in notes.KEYS]
        self.assertEqual(names, ["Cess-dur", "Gess-dur", "Dess-dur", "Ass-dur", "Ess-dur", "B-dur", "F-dur", "C-dur",
                                 "G-dur", "D-dur", "A-dur", "E-dur", "H-dur", "Fiss-dur", "Ciss-dur"])

    def test_signature(self):
        self.assertEqual(notes.alterations(2), {"F": 1, "C": 1})
        self.assertEqual(notes.alterations(-3), {"B": -1, "E": -1, "A": -1})
        self.assertEqual(notes.signature_steps("treble", 2), [38, 35])
        self.assertEqual(notes.signature_steps("bass", -1), [20])

    def test_f_line_in_d_major_is_f_sharp(self):
        f5 = notes.note_at(notes.step_of("F", 5), 2)
        self.assertEqual((f5["name"], f5["midi"]), ("Fiss", 78))
        self.assertEqual(notes.note_at(notes.step_of("F", 5), 0)["midi"], 77)
        self.assertEqual(notes.note_at(notes.step_of("B", 4), -1)["name"], "B")
        self.assertEqual(notes.note_at(notes.step_of("B", 4), 0)["name"], "H")
        self.assertEqual(notes.note_at(notes.MIDDLE_C, 0)["midi"], 60)

    def test_name_of_key(self):
        self.assertEqual(notes.name_of_key(66, 2), "Fiss")
        self.assertEqual(notes.name_of_key(65, 2), "F")  # F natural is not in D major, but has a plain name
        self.assertEqual(notes.name_of_key(68, 2), "Giss")
        self.assertEqual(notes.name_of_key(68, -1), "Ass")
        self.assertEqual(notes.name_of_key(59, -7), "Cess")

    def test_make_notes(self):
        both = notes.make_notes("both", 0, "staff-key")
        self.assertEqual(len(both), 23)  # 12 + 11, middle C once on each staff
        self.assertEqual(len(notes.make_notes("both", 0, "key-staff")), 22)
        self.assertEqual([n["name"] for n in notes.make_notes("treble", 0, "staff-key")][:3], ["C", "D", "E"])

    def test_piano_range_covers_flats_and_sharps(self):
        lo, hi = notes.piano_range("both", -6)  # G2 becomes Gess = F#2
        self.assertTrue(notes.is_white(lo) and notes.is_white(hi))
        self.assertLess(lo, 42)
        self.assertGreater(notes.piano_range("treble", 7)[1], 80)  # G#5

    def test_session(self):
        items = notes.make_notes("treble", 0, "staff-key")
        s = notes.Session(items, "staff-key", 0, rng=random.Random(2))
        note = s.current.word
        self.assertEqual(s.check(note["midi"] + 1), (False, True))
        self.assertEqual(s.mastered, 0)
        while s.current is not None:
            s.check(s.current.word["midi"])
        self.assertEqual((s.hits, s.missed), (len(items) - 1, [note]))


if __name__ == "__main__":
    unittest.main()
