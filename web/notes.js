// Music logic for Noter, ported from notes.py: staff positions, key signatures and piano keys.
//
// A staff position is a diatonic step: octave * 7 + letter index, so C4 (middle C) is 28.
// A piano key is a MIDI number: middle C is 60.

export const LETTERS = "CDEFGAB";
export const SEMITONES = [0, 2, 4, 5, 7, 9, 11];
const SHARP_ORDER = "FCGDAEB";
const FLAT_ORDER = "BEADGCF";

export const MIDDLE_C = 28;
// The ranges from the classic beginner chart: left hand G2–C4, right hand C4–G5.
export const RANGES = { treble: [MIDDLE_C, 39], bass: [18, MIDDLE_C] };
export const BOTTOM_LINE = { treble: 30, bass: 18 }; // E4 and G2
export const CLEF_NAMES = { treble: "diskantklav", bass: "basklav" };
// Where the sharps and flats of a key signature sit on the treble staff; the bass staff is two octaves lower.
const SIGNATURE_STEPS = { 1: [38, 35, 39, 36, 33, 37, 34], [-1]: [34, 37, 33, 36, 32, 35, 31] };

// Number of sharps (positive) or flats (negative).
export const KEYS = Array.from({ length: 15 }, (_, i) => i - 7);

export const CORRECT_MSGS = ["Bra jobbat! 🎉", "Rätt! Fortsätt så! 🌟", "Precis så! 👏", "Snyggt! 🚀", "Superbra! 😀"];
export const WRONG_MSGS = ["Nästan! Det är bra att du försöker 💪", "Inte riktigt, men du lär dig! 🌱",
  "Ingen fara, du klarar den nästa gång! 😊"];
export const REVEAL_MSGS = ["Här är svaret – du får se det igen strax 👀", "Bra att du kollar! Vi tar det igen senare 🙂"];

// Python-style modulo (never negative).
const mod = (a, n) => ((a % n) + n) % n;

export function stepOf(letter, octave) {
  return octave * 7 + LETTERS.indexOf(letter);
}

/** {letter: +1 or -1} for the key signature with this many sharps/flats. */
export function alterations(fifths) {
  const order = fifths > 0 ? SHARP_ORDER : FLAT_ORDER;
  const sign = fifths > 0 ? 1 : -1;
  const result = {};
  for (const letter of order.slice(0, Math.abs(fifths))) result[letter] = sign;
  return result;
}

/** Swedish note names: H is B natural, B is B flat; sharps end in -iss, flats in -ess. */
export function noteName(letter, alt) {
  if (letter === "B") return { [-1]: "B", 0: "H", 1: "Hiss" }[alt];
  if (alt === 1) return letter + "iss";
  if (alt === -1) return { E: "Ess", A: "Ass" }[letter] ?? letter + "ess";
  return letter;
}

export function keyName(fifths) {
  const letter = LETTERS[mod(fifths * 4, 7)];
  const alt = mod(fifths * 7 - SEMITONES[LETTERS.indexOf(letter)] + 6, 12) - 6;
  return noteName(letter, alt) + "-dur";
}

export function signatureText(fifths) {
  if (fifths === 0) return "inga förtecken";
  return `${Math.abs(fifths)} ${fifths > 0 ? "♯" : "♭"}`;
}

export function signatureSteps(clef, fifths) {
  const shift = clef === "treble" ? 0 : -14;
  return SIGNATURE_STEPS[fifths > 0 ? 1 : -1].slice(0, Math.abs(fifths)).map((s) => s + shift);
}

/** The note written at this staff position in this key. */
export function noteAt(step, fifths) {
  const octave = Math.floor(step / 7), i = mod(step, 7);
  const letter = LETTERS[i];
  const alt = alterations(fifths)[letter] ?? 0;
  return { step, midi: 12 * (octave + 1) + SEMITONES[i] + alt, name: noteName(letter, alt) };
}

/** What to call a piano key in this key: its name from the key signature if it has one,
 * otherwise its plain name, otherwise with a sharp in sharp keys and a flat in flat keys. */
export function nameOfKey(midi, fifths) {
  const alts = alterations(fifths);
  const letters = [...LETTERS];
  for (const options of [letters.map((l) => [l, alts[l] ?? 0]), letters.map((l) => [l, 0]),
    letters.map((l) => [l, fifths < 0 ? -1 : 1])]) {
    for (const [letter, alt] of options) {
      if (mod(SEMITONES[LETTERS.indexOf(letter)] + alt - midi, 12) === 0) return noteName(letter, alt);
    }
  }
}

export function clefsOf(choice) {
  return choice === "both" ? ["treble", "bass"] : [choice];
}

/** One question per staff position in range. Going from key to note, a key is only asked once
 * (middle C is on both staves). */
export function makeNotes(choice, fifths, direction) {
  const notes = [], seen = new Set();
  for (const clef of clefsOf(choice)) {
    const [lo, hi] = RANGES[clef];
    for (let step = lo; step <= hi; step++) {
      const note = { ...noteAt(step, fifths), clef };
      if (direction === "key-staff" && seen.has(note.midi)) continue;
      seen.add(note.midi);
      notes.push(note);
    }
  }
  return notes;
}

export function isWhite(midi) {
  return SEMITONES.includes(mod(midi, 12));
}

/** Lowest and highest MIDI key to draw: every possible answer plus a white key on each side. */
export function pianoRange(choice, fifths) {
  const midis = makeNotes(choice, fifths, "staff-key").map((n) => n.midi);
  let lo = Math.min(...midis) - 1, hi = Math.max(...midis) + 1;
  while (!isWhite(lo)) lo--;
  while (!isWhite(hi)) hi++;
  return [lo, hi];
}

function shuffle(list, rng) {
  for (let i = list.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [list[i], list[j]] = [list[j], list[i]];
  }
}

/** One practice round. direction is "staff-key" (see a note, click the key) or "key-staff"
 * (see a key, click the staff). A missed note comes back a few notes later. */
export class Session {
  constructor(notes, direction, fifths, rng = Math.random) {
    this.direction = direction;
    this.fifths = fifths;
    this.queue = notes.map((note) => ({ note, firstTry: null })); // firstTry: null until answered
    shuffle(this.queue, rng);
    this.all = [...this.queue];
    this.total = notes.length;
    this.mastered = 0;
  }

  get current() {
    return this.queue[0] ?? null;
  }

  /** True if this was the first attempt (so it counts in the score). */
  _firstAttempt(item, ok) {
    if (item.firstTry !== null) return false;
    item.firstTry = ok;
    return true;
  }

  _requeue(item) {
    this.queue.shift();
    this.queue.splice(Math.min(this.queue.length, 3), 0, item);
  }

  /** Answers the current note with a piano key. Returns [correct, firstAttempt]. */
  check(midi) {
    const item = this.current;
    const ok = midi === item.note.midi;
    const first = this._firstAttempt(item, ok);
    if (ok) {
      this.queue.shift();
      this.mastered++;
    } else {
      this._requeue(item);
    }
    return [ok, first];
  }

  /** Gives up on the current note. Returns firstAttempt. */
  reveal() {
    const item = this.current;
    const first = this._firstAttempt(item, false);
    this._requeue(item);
    return first;
  }

  get hits() {
    return this.all.filter((i) => i.firstTry).length;
  }

  get missed() {
    return this.all.filter((i) => !i.firstTry).map((i) => i.note);
  }
}
