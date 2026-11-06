// Noter as a web app: the same screens as noter_tk.py, with the staff and piano drawn as SVG.
import * as notes from "./notes.js";

const NS = "http://www.w3.org/2000/svg";
const $ = (id) => document.getElementById(id);
const pick = (list) => list[Math.floor(Math.random() * list.length)];
/** Blend two #rrggbb colors; t=0 gives a, t=1 gives b. */
function mix(a, b, t) {
  const rgb = (c) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));
  const [x, y] = [rgb(a), rgb(b)];
  return "#" + x.map((v, i) => Math.round(v + (y[i] - v) * t).toString(16).padStart(2, "0")).join("");
}

// The palette lives in style.css; read it so the drawings can blend its colors.
const palette = {};
const views = [];
function readPalette() {
  const style = getComputedStyle(document.documentElement);
  for (const name of ["card", "ink", "accent", "accent-fill", "ok", "bad"]) {
    palette[name] = style.getPropertyValue("--" + name).trim();
  }
}
const C = (name) => palette[name];
readPalette();
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  readPalette();
  for (const view of views) view.draw();
});

function svgEl(parent, tag, attrs = {}, style = "") {
  const node = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (style) node.setAttribute("style", style);
  parent.appendChild(node);
  return node;
}

/** A smooth path through control points, like a Tk line with smooth=True (parabolic spline). */
function smoothPath(pts) {
  const mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
  let d = `M${pts[0]}`;
  for (let i = 1; i < pts.length - 1; i++) {
    const end = i === pts.length - 2 ? pts[i + 1] : mid(pts[i], pts[i + 1]);
    d += ` Q${pts[i]} ${end}`;
  }
  return d;
}

// ---------- Staff ----------
class StaffView {
  /** One staff (treble or bass) or a grand staff, with clefs, key signature and whole notes.
   * When clickable it shows a faint note under the pointer and reports taps as (clef, step). */
  constructor(svg, onClick = null) {
    Object.assign(this, { svg, onClick, s: 13, choice: "treble", fifths: 0, notes: [], ghost: null, clickable: false });
    views.push(this);
    new ResizeObserver(() => this.draw()).observe(svg);
    const pos = (e) => this.positionAt(e.clientY - svg.getBoundingClientRect().top);
    svg.addEventListener("pointermove", (e) => {
      if (this.clickable && (e.pointerType === "mouse" || e.buttons)) this.setGhost(pos(e));
    });
    svg.addEventListener("pointerdown", (e) => {
      if (!this.clickable || e.button !== 0) return;
      svg.setPointerCapture(e.pointerId);
      this.setGhost(pos(e));
    });
    svg.addEventListener("pointerup", (e) => {
      if (this.clickable && e.button === 0 && this.onClick) this.onClick(...pos(e));
    });
    svg.addEventListener("pointerleave", () => this.setGhost(null));
    svg.addEventListener("pointercancel", () => this.setGhost(null));
  }

  setup(choice, fifths) {
    Object.assign(this, { choice, fifths, notes: [], ghost: null });
    const s = this.s;
    // Bottom line of each staff; 2.5 spaces of room above and below for ledger lines.
    this.bottom = choice === "both" ? { treble: 6.5 * s, bass: 14.5 * s } : { [choice]: 6.5 * s };
    this.svg.setAttribute("height", Math.round(Math.max(...Object.values(this.bottom)) + 2.5 * s));
    this.draw();
  }

  /** notes: a list of [clef, step, kind] where kind is null (plain ink), "ok" or "bad". */
  setNotes(list, clickable = false) {
    Object.assign(this, { notes: list, clickable, ghost: null });
    this.svg.classList.toggle("clickable", clickable);
    this.draw();
  }

  yOf(clef, step) {
    return this.bottom[clef] - (step - notes.BOTTOM_LINE[clef]) * this.s / 2;
  }

  noteX(w) {
    const sigEnd = 8 + 3.6 * this.s + 0.95 * this.s * Math.abs(this.fifths);
    return (sigEnd + w - 8) / 2;
  }

  positionAt(y) {
    const clefs = Object.keys(this.bottom);
    let clef = clefs[0];
    if (clefs.length === 2 && y > (this.bottom.treble + this.bottom.bass - 4 * this.s) / 2) clef = "bass";
    const step = notes.BOTTOM_LINE[clef] + Math.round((this.bottom[clef] - y) / (this.s / 2));
    const [lo, hi] = notes.RANGES[clef];
    return [clef, Math.max(lo, Math.min(hi, step))];
  }

  setGhost(pos) {
    if (String(pos) !== String(this.ghost)) {
      this.ghost = pos;
      this.draw();
    }
  }

  draw() {
    const svg = this.svg, s = this.s;
    svg.replaceChildren();
    const w = svg.clientWidth;
    if (!this.bottom || !w) return;
    this.w = w;
    const x0 = 8, x1 = w - 8;
    const ink = "stroke: currentColor";
    for (const [clef, bottom] of Object.entries(this.bottom)) {
      for (let i = 0; i < 5; i++) {
        svgEl(svg, "line", { x1: x0, y1: bottom - i * s, x2: x1, y2: bottom - i * s, "stroke-width": 1 }, ink);
      }
      svgEl(svg, "line", { x1, y1: bottom - 4 * s, x2: x1, y2: bottom, "stroke-width": 1 }, ink);
      if (clef === "treble") this.trebleClef(x0 + 1.5 * s, this.yOf(clef, 32));
      else this.bassClef(x0 + 1.1 * s, this.yOf(clef, 24));
      if (this.fifths) {
        notes.signatureSteps(clef, this.fifths).forEach((step, i) => {
          const x = x0 + 3.9 * s + 0.95 * s * i, y = this.yOf(clef, step);
          this.fifths > 0 ? this.sharp(x, y) : this.flat(x, y);
        });
      }
    }
    const tops = Object.values(this.bottom).map((b) => b - 4 * s);
    svgEl(svg, "line", { x1: x0, y1: Math.min(...tops), x2: x0, y2: Math.max(...Object.values(this.bottom)),
      "stroke-width": 2 }, ink);
    if (this.ghost && !this.notes.some(([c, st]) => c === this.ghost[0] && st === this.ghost[1])) {
      this.note(...this.ghost, mix(C("card"), C("accent-fill"), 0.45));
    }
    for (const [clef, step, kind] of this.notes) this.note(clef, step, kind ? C(kind) : "currentColor");
  }

  note(clef, step, color) {
    const s = this.s, x = this.noteX(this.w), y = this.yOf(clef, step);
    const bottom = notes.BOTTOM_LINE[clef];
    const ledgers = [];
    for (let l = bottom + 10; l <= step; l += 2) ledgers.push(l);
    for (let l = bottom - 2; l >= step; l -= 2) ledgers.push(l);
    for (const ledger of ledgers) {
      const ly = this.yOf(clef, ledger);
      svgEl(this.svg, "line", { x1: x - 1.25 * s, y1: ly, x2: x + 1.25 * s, y2: ly, "stroke-width": 1.5 },
        `stroke: ${color}`);
    }
    svgEl(this.svg, "ellipse", { cx: x, cy: y, rx: 0.78 * s, ry: 0.52 * s, "stroke-width": Math.max(2, 0.24 * s) },
      `stroke: ${color}; fill: var(--card)`);
  }

  curve(points, x, y, width) {
    const pts = points.map(([px, py]) => [x + px * this.s, y + py * this.s]);
    svgEl(this.svg, "path", { d: smoothPath(pts), fill: "none", "stroke-width": width, "stroke-linecap": "round",
      "stroke-linejoin": "round" }, "stroke: currentColor");
  }

  dot(x, y, r) {
    svgEl(this.svg, "circle", { cx: x, cy: y, r }, "fill: currentColor");
  }

  /** A G clef curling around the G line at (x, y). */
  trebleClef(x, y) {
    const s = this.s;
    this.curve([[0.15, 0.35], [-0.35, 0.1], [-0.1, -0.45], [0.55, -0.35], [0.75, 0.35], [0.05, 0.95],
      [-0.75, 0.55], [-0.75, -0.35], [0.25, -1.6], [0.6, -2.9], [0.3, -3.7], [-0.1, -3.2],
      [-0.05, -1.9], [0.3, 1.5], [0.2, 2.15], [-0.3, 2.1], [-0.35, 1.7]], x, y, Math.max(2, 0.2 * s));
    this.dot(x - 0.35 * s, y + 1.7 * s, 0.2 * s);
  }

  /** An F clef: a dot on the F line at (x, y), an arc and two dots around the line. */
  bassClef(x, y) {
    const s = this.s;
    this.dot(x, y, 0.34 * s);
    this.curve([[-0.1, -0.1], [0.2, -0.85], [0.95, -0.85], [1.3, -0.1], [1.0, 1.0], [-0.2, 2.4]], x, y,
      Math.max(2, 0.24 * s));
    for (const dy of [-0.5, 0.5]) this.dot(x + 1.8 * s, y + dy * s, 0.13 * s);
  }

  sharp(x, y) {
    const s = this.s;
    for (const dx of [-0.18, 0.18]) {
      svgEl(this.svg, "line", { x1: x + dx * s, y1: y - 1.05 * s - dx * 0.3 * s, x2: x + dx * s,
        y2: y + 1.05 * s - dx * 0.3 * s, "stroke-width": Math.max(1, 0.1 * s) }, "stroke: currentColor");
    }
    for (const dy of [-0.33, 0.33]) {
      svgEl(this.svg, "line", { x1: x - 0.42 * s, y1: y + (dy + 0.12) * s, x2: x + 0.42 * s,
        y2: y + (dy - 0.12) * s, "stroke-width": Math.max(2, 0.22 * s) }, "stroke: currentColor");
    }
  }

  flat(x, y) {
    const s = this.s;
    svgEl(this.svg, "line", { x1: x - 0.25 * s, y1: y - 1.6 * s, x2: x - 0.25 * s, y2: y + 0.5 * s,
      "stroke-width": Math.max(1, 0.12 * s) }, "stroke: currentColor");
    this.curve([[-0.25, 0.5], [0.3, 0.0], [0.35, -0.35], [0.05, -0.45], [-0.25, -0.15]], x, y, Math.max(2, 0.16 * s));
  }
}

// ---------- Piano ----------
const WHITE_KEY = "#ffffff", BLACK_KEY = "#1c1c1e";
const MIN_KEY_WIDTH = 22; // narrower than this and the piano scrolls sideways instead

class PianoView {
  /** A piano keyboard. Keys can be marked ("ok", "bad", "target") and named underneath. */
  constructor(svg, scroller, onClick = null) {
    Object.assign(this, { svg, scroller, onClick, keyH: 124, labelH: 26, whites: [], marks: {}, labels: {},
      clickable: false, hover: null, pressed: null });
    svg.setAttribute("height", this.keyH + this.labelH);
    views.push(this);
    new ResizeObserver(() => this.draw()).observe(scroller);
    const keyAt = (e) => {
      const r = svg.getBoundingClientRect();
      return this.keyAt(e.clientX - r.left, e.clientY - r.top);
    };
    svg.addEventListener("pointermove", (e) => { if (e.pointerType === "mouse") this.setHover(keyAt(e)); });
    svg.addEventListener("pointerleave", () => this.setHover(null));
    svg.addEventListener("pointerdown", (e) => {
      if (e.button !== 0) return;
      this.pressed = keyAt(e);
      this.draw();
    });
    svg.addEventListener("pointerup", (e) => {
      const m = this.pressed;
      this.pressed = null;
      if (m !== null && m === keyAt(e) && this.onClick) this.onClick(m);
      this.draw();
    });
    // Fires when the touch turns into a sideways scroll: that is not a key press.
    svg.addEventListener("pointercancel", () => { this.pressed = null; this.draw(); });
  }

  setRange(lo, hi) {
    this.whites = [];
    for (let m = lo; m <= hi; m++) if (notes.isWhite(m)) this.whites.push(m);
    this.draw();
  }

  setMarks(marks = {}, labels = {}, clickable = false) {
    Object.assign(this, { marks, labels, clickable, hover: null, pressed: null });
    this.svg.classList.toggle("clickable", clickable);
    this.draw();
  }

  /** When the piano is wider than the screen, scrolls so these keys (or the middle) are in view. */
  reveal(...midis) {
    const keys = this.geometry();
    const centers = midis.filter((m) => keys[m]).map((m) => (keys[m][0] + keys[m][1]) / 2);
    const x = centers.length ? (Math.min(...centers) + Math.max(...centers)) / 2 : this.width / 2;
    this.scroller.scrollTo({ left: x - this.scroller.clientWidth / 2,
      behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  }

  /** {midi: [x1, x2, isBlack]} for every key. */
  geometry() {
    const ww = (this.width - 1) / Math.max(1, this.whites.length), bw = ww * 0.58;
    const keys = {};
    this.whites.forEach((m, i) => {
      keys[m] = [i * ww, (i + 1) * ww, false];
      if (i && !notes.isWhite(m - 1)) keys[m - 1] = [i * ww - bw / 2, i * ww + bw / 2, true];
    });
    return keys;
  }

  keyAt(x, y) {
    if (!this.clickable || y < 0 || y >= this.keyH) return null;
    const keys = Object.entries(this.geometry()).map(([m, g]) => [Number(m), ...g]);
    const black = keys.find(([, x1, x2, b]) => b && x1 <= x && x < x2 && y < this.keyH * 0.62);
    if (black) return black[0];
    const white = keys.find(([, x1, x2, b]) => !b && x1 <= x && x < x2);
    return white ? white[0] : null;
  }

  setHover(m) {
    if (m !== this.hover) {
      this.hover = m;
      this.draw();
    }
  }

  draw() {
    const svg = this.svg;
    this.width = Math.max(this.scroller.clientWidth, this.whites.length * MIN_KEY_WIDTH);
    svg.setAttribute("width", this.width);
    svg.replaceChildren();
    if (!this.whites.length || !this.scroller.clientWidth) return;
    const keys = this.geometry();
    const edge = mix(WHITE_KEY, "#000000", 0.28);
    for (const black of [false, true]) {
      for (const [mStr, [x1, x2, isBlack]] of Object.entries(keys)) {
        if (isBlack !== black) continue;
        const m = Number(mStr), base = black ? BLACK_KEY : WHITE_KEY, kind = this.marks[m];
        let fill = base;
        if (kind) fill = mix(base, kind === "target" ? C("accent-fill") : C(kind), black ? 0.8 : 0.5);
        else if (m === this.pressed) fill = mix(base, C("accent-fill"), black ? 0.4 : 0.3);
        else if (m === this.hover) fill = mix(base, C("accent-fill"), black ? 0.3 : 0.14);
        // Only the bottom corners are rounded; white keys share a 1px edge with their neighbour.
        const y2 = this.keyH * (black ? 0.62 : 1), r = black ? 3 : 5;
        const [a, b] = black ? [x1, x2] : [x1 + 0.5, x2 + 0.5];
        const outline = `M${a} 0 V${y2 - r} Q${a} ${y2} ${a + r} ${y2} H${b - r} Q${b} ${y2} ${b} ${y2 - r} V0`;
        svgEl(svg, "path", { d: outline + " Z", "data-midi": m, "data-mark": kind || "" }, `fill: ${fill}`);
        if (!black) svgEl(svg, "path", { d: outline, fill: "none", "stroke-width": 1 }, `stroke: ${edge}`);
        if (m === 60 && !kind) { // middle C
          svgEl(svg, "circle", { cx: (x1 + x2) / 2, cy: y2 - 14, r: 3 }, "fill: var(--muted)");
        }
      }
    }
    for (const [mStr, text] of Object.entries(this.labels)) {
      const [x1, x2] = keys[mStr], kind = this.marks[mStr];
      const color = kind === "target" ? C("accent") : kind ? C(kind) : C("ink");
      const t = svgEl(svg, "text", { x: (x1 + x2) / 2, y: this.keyH + this.labelH / 2 + 2, "text-anchor": "middle",
        "dominant-baseline": "middle" }, `fill: ${color}`);
      t.textContent = text;
    }
  }
}

// ---------- Screens ----------
const keyTitle = (f) => `${notes.keyName(f)} · ${notes.signatureText(f)}`;

function keyHelp(fifths) {
  if (fifths === 0) return "Inga ♯ eller ♭: alla toner spelas på de vita tangenterna.";
  const changed = Object.entries(notes.alterations(fifths))
    .map(([letter, alt]) => `${letter.replace("B", "H")} blir ${notes.noteName(letter, alt)}`).join(", ");
  return `Förtecknen gäller alla oktaver: ${changed}.`;
}

function load(key, fallback) {
  try { return JSON.parse(localStorage.getItem("noter." + key)) ?? fallback; } catch { return fallback; }
}
function save(key, value) {
  try { localStorage.setItem("noter." + key, JSON.stringify(value)); } catch { /* private mode */ }
}

const home = {
  depth: 0,
  init() {
    this.staff = new StaffView($("home-staff"));
    this.fifths = load("fifths", 0);
    this.clef = load("clef", "treble");
    $("key-prev").onclick = () => this.stepKey(-1);
    $("key-next").onclick = () => this.stepKey(1);
    for (const b of $("clef").querySelectorAll("button")) {
      b.onclick = () => { this.clef = b.dataset.value; this.refresh(); };
    }
    for (const b of document.querySelectorAll("[data-start]")) {
      b.onclick = () => show("quiz", [this.clef, this.fifths, b.dataset.start]);
    }
  },
  show() { this.refresh(); },
  stepKey(step) {
    this.fifths = Math.max(notes.KEYS[0], Math.min(notes.KEYS.at(-1), this.fifths + step));
    this.refresh();
  },
  refresh() {
    if (!notes.KEYS.includes(this.fifths)) this.fifths = 0;
    if (!["treble", "bass", "both"].includes(this.clef)) this.clef = "treble";
    save("fifths", this.fifths);
    save("clef", this.clef);
    $("key-title").textContent = keyTitle(this.fifths);
    $("key-help").textContent = keyHelp(this.fifths);
    $("key-prev").disabled = this.fifths === notes.KEYS[0];
    $("key-next").disabled = this.fifths === notes.KEYS.at(-1);
    for (const b of $("clef").querySelectorAll("button")) b.setAttribute("aria-checked", b.dataset.value === this.clef);
    this.staff.setup(this.clef, this.fifths);
  },
};

const quiz = {
  depth: 1,
  init() {
    this.staff = new StaffView($("quiz-staff"), (clef, step) => this.staffClicked(clef, step));
    this.piano = new PianoView($("piano"), $("piano-scroll"), (midi) => this.keyClicked(midi));
    $("quit").onclick = () => goHome();
    $("reveal").onclick = () => this.reveal();
    $("next").onclick = () => this.nextNote();
  },
  show(choice, fifths, direction, items = null) {
    this.settings = [choice, fifths, direction];
    this.session = new notes.Session(items || notes.makeNotes(choice, fifths, direction), direction, fifths);
    this.staff.setup(choice, fifths);
    this.piano.setRange(...notes.pianoRange(choice, fifths));
    $("progress-fill").style.transition = "none";
    this.nextNote();
    $("progress-fill").offsetWidth; // apply the 0% width before turning the animation back on
    $("progress-fill").style.transition = "";
    this.piano.reveal();
  },
  get toKey() { return this.session.direction === "staff-key"; },
  nextNote() {
    const s = this.session;
    if (s.current === null) return show("summary", [s, this.settings]);
    this.answered = false;
    const note = s.current.note;
    if (this.toKey) {
      $("prompt").textContent = "Vilken tangent är det här? Tryck på pianot.";
      this.staff.setNotes([[note.clef, note.step, null]]);
      this.piano.setMarks({}, {}, true);
    } else {
      $("prompt").textContent = "Var står den här tonen? Tryck i notsystemet.";
      this.staff.setNotes([], true);
      this.piano.setMarks({ [note.midi]: "target" });
      this.piano.reveal(note.midi);
    }
    this.showFeedback();
    $("next").hidden = true;
    $("reveal").hidden = false;
    this.updateProgress();
  },
  updateProgress() {
    const s = this.session;
    $("progress-fill").style.width = `${(100 * s.mastered) / s.total}%`;
    $("progress-text").textContent = `${s.mastered} av ${s.total} toner klara · ${notes.keyName(s.fifths)}`;
  },
  keyClicked(midi) {
    if (this.answered || !this.toKey) return;
    const note = this.session.current.note;
    const [ok] = this.session.check(midi);
    const marks = { [note.midi]: "ok" }, labels = { [note.midi]: note.name };
    if (!ok) [marks[midi], labels[midi]] = ["bad", notes.nameOfKey(midi, this.session.fifths)];
    this.piano.setMarks(marks, labels);
    this.piano.reveal(note.midi, midi);
    this.staff.setNotes([[note.clef, note.step, ok ? "ok" : null]]);
    this.afterAnswer(ok, `Rätt tangent: ${note.name}`);
  },
  staffClicked(clef, step) {
    if (this.answered || this.toKey) return;
    const note = this.session.current.note;
    const clicked = notes.noteAt(step, this.session.fifths);
    const [ok] = this.session.check(clicked.midi);
    this.staff.setNotes(ok ? [[clef, step, "ok"]] : [[note.clef, note.step, "ok"], [clef, step, "bad"]]);
    const marks = { [note.midi]: "ok" }, labels = { [note.midi]: note.name };
    if (!ok) [marks[clicked.midi], labels[clicked.midi]] = ["bad", clicked.name];
    this.piano.setMarks(marks, labels);
    this.piano.reveal(note.midi, clicked.midi);
    this.afterAnswer(ok, `Tonen ${note.name} står här`);
  },
  reveal() {
    if (this.answered) return;
    const note = this.session.current.note;
    this.session.reveal();
    this.staff.setNotes([[note.clef, note.step, "ok"]]);
    this.piano.setMarks({ [note.midi]: "ok" }, { [note.midi]: note.name });
    this.piano.reveal(note.midi);
    this.answered = true;
    this.showResult("bad", pick(notes.REVEAL_MSGS), `Det är ${note.name}`);
  },
  afterAnswer(ok, answer) {
    this.answered = true;
    if (ok) this.showResult("ok", pick(notes.CORRECT_MSGS), this.toKey ? answer : "");
    else this.showResult("bad", pick(notes.WRONG_MSGS), answer);
  },
  showFeedback(kind = null, message = "", answer = "") {
    const box = $("feedback");
    box.className = "feedback" + (kind ? " " + kind : "");
    box.replaceChildren();
    if (!kind) return;
    for (const [cls, text] of [["message", message], ["answer", answer]]) {
      if (!text) continue;
      const div = document.createElement("div");
      div.className = cls;
      div.textContent = text;
      box.appendChild(div);
    }
  },
  showResult(kind, message, answer) {
    this.showFeedback(kind, message, answer);
    $("reveal").hidden = true;
    $("next").hidden = false;
    $("next").focus({ preventScroll: true });
    this.updateProgress();
  },
};

const summary = {
  depth: 2,
  init() {
    $("retry").onclick = () => show("quiz", [...this.settings, this.session.missed], "back");
    $("again").onclick = () => show("quiz", this.settings, "back");
    $("home-btn").onclick = () => goHome();
  },
  show(session, settings) {
    Object.assign(this, { session, settings });
    $("score").textContent = `${session.hits} av ${session.total}`;
    const items = [...session.all].sort((a, b) => a.note.midi - b.note.midi || a.note.clef.localeCompare(b.note.clef));
    $("results").replaceChildren(...items.map((item) => {
      const n = item.note, ok = Boolean(item.firstTry);
      const li = document.createElement("li");
      li.className = ok ? "ok" : "bad";
      for (const [cls, text] of [["mark", ok ? "✓" : "✗"],
        ["name", n.name + (n.step === notes.MIDDLE_C ? " (mitt-C)" : "")], ["where", notes.CLEF_NAMES[n.clef]]]) {
        const span = document.createElement("span");
        span.className = cls;
        span.textContent = text;
        li.appendChild(span);
      }
      return li;
    }));
    const missed = session.missed.length > 0;
    $("retry").hidden = !missed;
    $("again").style.gridColumn = missed ? "" : "1 / -1";
    (missed ? $("retry") : $("again")).focus({ preventScroll: true });
  },
};

// ---------- Navigation ----------
const screens = { home, quiz, summary };
let current = null;

/** Screens enter along the direction you travel: deeper from the right, back from the left. */
function show(name, args = [], direction = null) {
  const screen = screens[name];
  if (direction === null && current) direction = screen.depth >= current.depth ? "fwd" : "back";
  for (const [n, s] of Object.entries(screens)) $(n).hidden = s !== screen;
  const el = $(name);
  el.classList.remove("back");
  el.style.animation = "none";
  el.offsetWidth; // restart the entry animation
  el.style.animation = direction ? "" : "none";
  el.classList.toggle("back", direction === "back");
  // On phones the Back button should leave the quiz, not the app.
  if (name !== "home" && !history.state) history.pushState({ inQuiz: true }, "");
  current = screen;
  screen.show(...args);
  window.scrollTo(0, 0);
}

function goHome() {
  if (history.state) history.back(); // popstate shows the home screen
  else show("home");
}

window.addEventListener("popstate", () => { if (current !== home) show("home", [], "back"); });

for (const s of Object.values(screens)) s.init();
if (history.state) history.replaceState(null, "");
show("home");

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("sw.js").catch(() => {}));
}
