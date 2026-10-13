"""Music logic for Noter: staff positions, key signatures and piano keys, kept separate from the GUI.

A staff position is a diatonic step: octave * 7 + letter index, so C4 (middle C) is 28.
A piano key is a MIDI number: middle C is 60.
"""
import random

import quiz

LETTERS = "CDEFGAB"
SEMITONES = [0, 2, 4, 5, 7, 9, 11]
SHARP_ORDER = "FCGDAEB"
FLAT_ORDER = "BEADGCF"

MIDDLE_C = 28
# The ranges from the classic beginner chart: left hand G2–C4, right hand C4–G5.
RANGES = {"treble": (MIDDLE_C, 39), "bass": (18, MIDDLE_C)}
BOTTOM_LINE = {"treble": 30, "bass": 18}  # E4 and G2
CLEF_NAMES = {"treble": "diskantklav", "bass": "basklav"}
# Where the sharps and flats of a key signature sit on the treble staff; the bass staff is two octaves lower.
SIGNATURE_STEPS = {1: [38, 35, 39, 36, 33, 37, 34], -1: [34, 37, 33, 36, 32, 35, 31]}

KEYS = list(range(-7, 8))  # number of sharps (positive) or flats (negative)


def step_of(letter, octave):
    return octave * 7 + LETTERS.index(letter)


def alterations(fifths):
    """{letter: +1 or -1} for the key signature with this many sharps/flats."""
    order = SHARP_ORDER if fifths > 0 else FLAT_ORDER
    sign = 1 if fifths > 0 else -1
    return {letter: sign for letter in order[:abs(fifths)]}


def note_name(letter, alt):
    """Swedish note names: H is B natural, B is B flat; sharps end in -iss, flats in -ess."""
    if letter == "B":
        return {-1: "B", 0: "H", 1: "Hiss"}[alt]
    if alt == 1:
        return letter + "iss"
    if alt == -1:
        return {"E": "Ess", "A": "Ass"}.get(letter, letter + "ess")
    return letter


def key_name(fifths):
    letter = LETTERS[(fifths * 4) % 7]
    alt = (fifths * 7 - SEMITONES[LETTERS.index(letter)] + 6) % 12 - 6
    return note_name(letter, alt) + "-dur"


def signature_text(fifths):
    if fifths == 0:
        return "inga förtecken"
    return f"{abs(fifths)} {'♯' if fifths > 0 else '♭'}"


def signature_steps(clef, fifths):
    shift = 0 if clef == "treble" else -14
    return [s + shift for s in SIGNATURE_STEPS[1 if fifths > 0 else -1][:abs(fifths)]]


def note_at(step, fifths):
    """The note written at this staff position in this key."""
    octave, i = divmod(step, 7)
    letter = LETTERS[i]
    alt = alterations(fifths).get(letter, 0)
    return {"step": step, "midi": 12 * (octave + 1) + SEMITONES[i] + alt, "name": note_name(letter, alt)}


def name_of_key(midi, fifths):
    """What to call a piano key in this key: its name from the key signature if it has one,
    otherwise its plain name, otherwise with a sharp in sharp keys and a flat in flat keys."""
    alts = alterations(fifths)
    for options in ([(l, alts.get(l, 0)) for l in LETTERS], [(l, 0) for l in LETTERS],
                    [(l, -1 if fifths < 0 else 1) for l in LETTERS]):
        for letter, alt in options:
            if (SEMITONES[LETTERS.index(letter)] + alt - midi) % 12 == 0:
                return note_name(letter, alt)


def clefs_of(choice):
    return ["treble", "bass"] if choice == "both" else [choice]


def make_notes(choice, fifths, direction):
    """One question per staff position in range. Going from key to note, a key is only asked once
    (middle C is on both staves)."""
    notes, seen = [], set()
    for clef in clefs_of(choice):
        lo, hi = RANGES[clef]
        for step in range(lo, hi + 1):
            note = {**note_at(step, fifths), "clef": clef}
            if direction == "key-staff" and note["midi"] in seen:
                continue
            seen.add(note["midi"])
            notes.append(note)
    return notes


def piano_range(choice, fifths):
    """Lowest and highest MIDI key to draw: every possible answer plus a white key on each side."""
    midis = [n["midi"] for n in make_notes(choice, fifths, "staff-key")]
    lo, hi = min(midis) - 1, max(midis) + 1
    while not is_white(lo):
        lo -= 1
    while not is_white(hi):
        hi += 1
    return lo, hi


def is_white(midi):
    return midi % 12 in SEMITONES


class Session(quiz.Session):
    """A practice round of notes. direction is "staff-key" (see a note, click the key) or
    "key-staff" (see a key, click the staff). The given answer is a MIDI number."""

    def __init__(self, notes, direction, fifths, rng=random):
        super().__init__(notes, direction, rng)
        self.fifths = fifths

    def matches(self, given, note):
        return given == note["midi"]
