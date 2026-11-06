// The same checks as test_notes.py, for the JavaScript port. Run: node --test web/
import { test } from "node:test";
import assert from "node:assert/strict";

import * as notes from "./notes.js";

test("key names", () => {
  assert.deepEqual(notes.KEYS.map(notes.keyName), ["Cess-dur", "Gess-dur", "Dess-dur", "Ass-dur", "Ess-dur",
    "B-dur", "F-dur", "C-dur", "G-dur", "D-dur", "A-dur", "E-dur", "H-dur", "Fiss-dur", "Ciss-dur"]);
});

test("signature", () => {
  assert.deepEqual(notes.alterations(2), { F: 1, C: 1 });
  assert.deepEqual(notes.alterations(-3), { B: -1, E: -1, A: -1 });
  assert.deepEqual(notes.signatureSteps("treble", 2), [38, 35]);
  assert.deepEqual(notes.signatureSteps("bass", -1), [20]);
});

test("F line in D major is F sharp", () => {
  const f5 = notes.noteAt(notes.stepOf("F", 5), 2);
  assert.deepEqual([f5.name, f5.midi], ["Fiss", 78]);
  assert.equal(notes.noteAt(notes.stepOf("F", 5), 0).midi, 77);
  assert.equal(notes.noteAt(notes.stepOf("B", 4), -1).name, "B");
  assert.equal(notes.noteAt(notes.stepOf("B", 4), 0).name, "H");
  assert.equal(notes.noteAt(notes.MIDDLE_C, 0).midi, 60);
});

test("name of key", () => {
  assert.equal(notes.nameOfKey(66, 2), "Fiss");
  assert.equal(notes.nameOfKey(65, 2), "F"); // F natural is not in D major, but has a plain name
  assert.equal(notes.nameOfKey(68, 2), "Giss");
  assert.equal(notes.nameOfKey(68, -1), "Ass");
  assert.equal(notes.nameOfKey(59, -7), "Cess");
});

test("make notes", () => {
  assert.equal(notes.makeNotes("both", 0, "staff-key").length, 23); // 12 + 11, middle C once on each staff
  assert.equal(notes.makeNotes("both", 0, "key-staff").length, 22);
  assert.deepEqual(notes.makeNotes("treble", 0, "staff-key").slice(0, 3).map((n) => n.name), ["C", "D", "E"]);
});

test("piano range covers flats and sharps", () => {
  const [lo, hi] = notes.pianoRange("both", -6); // G2 becomes Gess = F#2
  assert.ok(notes.isWhite(lo) && notes.isWhite(hi));
  assert.ok(lo < 42);
  assert.ok(notes.pianoRange("treble", 7)[1] > 80); // G#5
});

test("session", () => {
  const items = notes.makeNotes("treble", 0, "staff-key");
  const s = new notes.Session(items, "staff-key", 0);
  const note = s.current.note;
  assert.deepEqual(s.check(note.midi + 1), [false, true]);
  assert.equal(s.mastered, 0);
  while (s.current !== null) s.check(s.current.note.midi);
  assert.equal(s.hits, items.length - 1);
  assert.deepEqual(s.missed, [note]);
});
