"""Quiz logic for Glosor, kept separate from the GUI so it can be tested."""
import random
import re

CORRECT_MSGS = ["Bra jobbat! 🎉", "Rätt! Fortsätt så! 🌟", "Precis så! 👏", "Snyggt! 🚀", "Superbra! 😀"]
WRONG_MSGS = ["Nästan! Det är bra att du försöker 💪", "Inte riktigt, men du lär dig! 🌱",
              "Ingen fara, du klarar den nästa gång! 😊"]
REVEAL_MSGS = ["Här är svaret – du får se det igen strax 👀", "Bra att du kollar! Vi tar det igen senare 🙂"]


def normalize(s):
    return re.sub(r"\s+", " ", s.strip().lower())


def is_correct(given, expected):
    given = normalize(given)
    if not given:
        return False
    options = [normalize(o) for o in expected.split("/")]
    return normalize(expected) == given or given in options


def combine(lists):
    """Words from several lists; identical word pairs are only asked once."""
    seen, words = set(), []
    for lst in lists:
        for w in lst["words"]:
            key = (w["sv"], w["en"])
            if key not in seen:
                seen.add(key)
                words.append({**w, "list_id": lst["id"]})
    return words


class Item:
    def __init__(self, word):
        self.word = word
        self.first_try = None  # None until the first answer, then True/False


class Session:
    """One practice round. A missed word comes back a few words later."""

    def __init__(self, words, direction, rng=random):
        self.direction = direction  # "sv-en" or "en-sv"
        self.queue = [Item(w) for w in words]
        rng.shuffle(self.queue)
        self.all = self.queue[:]
        self.total = len(words)
        self.mastered = 0

    @property
    def current(self):
        return self.queue[0] if self.queue else None

    def question(self, word):
        return word["sv"] if self.direction == "sv-en" else word["en"]

    def answer_of(self, word):
        return word["en"] if self.direction == "sv-en" else word["sv"]

    def matches(self, given, word):
        return is_correct(given, self.answer_of(word))

    def _first_attempt(self, item, ok):
        """True if this was the first attempt (so the result should be recorded)."""
        if item.first_try is not None:
            return False
        item.first_try = ok
        return True

    def _requeue(self, item):
        self.queue.pop(0)
        self.queue.insert(min(len(self.queue), 3), item)

    def check(self, given):
        """Returns (correct, first_attempt) for the current word."""
        item = self.current
        ok = self.matches(given, item.word)
        first = self._first_attempt(item, ok)
        if ok:
            self.queue.pop(0)
            self.mastered += 1
        else:
            self._requeue(item)
        return ok, first

    def reveal(self):
        """Gives up on the current word. Returns first_attempt."""
        item = self.current
        first = self._first_attempt(item, False)
        self._requeue(item)
        return first

    @property
    def hits(self):
        return sum(1 for i in self.all if i.first_try)

    @property
    def missed(self):
        return [i.word for i in self.all if not i.first_try]
