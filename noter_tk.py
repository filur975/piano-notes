"""Noter: practise reading notes and finding them on the piano, as a desktop app (Tkinter).

Shares the look, widgets and window code with Glosor.
"""
import random
import tkinter as tk
from tkinter import ttk

import notes
import quiz
from glosor_tk import CanvasList, Feedback, GlosorApp, ProgressBar, Screen, elide, mix, plain

WHITE_KEY, BLACK_KEY = "#ffffff", "#1c1c1e"


class StaffView(tk.Canvas):
    """One staff (treble or bass) or a grand staff, with clefs, key signature and whole notes.
    When clickable it shows a faint note under the mouse and reports clicks as (clef, step)."""

    def __init__(self, master, app, on_click=None):
        super().__init__(master, highlightthickness=0, background=app.c["card"], width=1, height=1)
        self.app, self.on_click, self.s = app, on_click, app.px(13)
        self.choice, self.fifths, self.notes, self.ghost, self.clickable = "treble", 0, [], None, False
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<Motion>", self.motion)
        self.bind("<Leave>", lambda e: self.set_ghost(None))
        self.bind("<ButtonRelease-1>", self.click)

    def setup(self, choice, fifths):
        self.choice, self.fifths, self.notes, self.ghost = choice, fifths, [], None
        s = self.s
        # Bottom line of each staff; 2.5 spaces of room above and below for ledger lines.
        if choice == "both":
            self.bottom = {"treble": 6.5 * s, "bass": 14.5 * s}
        else:
            self.bottom = {choice: 6.5 * s}
        self.configure(height=round(max(self.bottom.values()) + 2.5 * s))
        self.draw()

    def set_notes(self, notes_, clickable=False):
        """notes_: a list of (clef, step, kind) where kind is None (plain ink), "ok" or "bad"."""
        self.notes, self.clickable, self.ghost = notes_, clickable, None
        self.configure(cursor="hand2" if clickable else "")
        self.draw()

    def y_of(self, clef, step):
        return self.bottom[clef] - (step - notes.BOTTOM_LINE[clef]) * self.s / 2

    def note_x(self):
        sig_end = self.app.px(8) + 3.6 * self.s + 0.95 * self.s * abs(self.fifths)
        return (sig_end + self.winfo_width() - self.app.px(8)) / 2

    def position_at(self, y):
        clefs = list(self.bottom)
        clef = clefs[0]
        if len(clefs) == 2 and y > (self.bottom["treble"] + self.bottom["bass"] - 4 * self.s) / 2:
            clef = "bass"
        step = notes.BOTTOM_LINE[clef] + round((self.bottom[clef] - y) / (self.s / 2))
        lo, hi = notes.RANGES[clef]
        return clef, max(lo, min(hi, step))

    def motion(self, event):
        self.set_ghost(self.position_at(event.y) if self.clickable else None)

    def set_ghost(self, pos):
        if pos != self.ghost:
            self.ghost = pos
            self.draw()

    def click(self, event):
        if self.clickable and self.on_click:
            self.on_click(*self.position_at(event.y))

    # ----- drawing -----
    def draw(self):
        self.delete("all")
        if not hasattr(self, "bottom"):
            return
        c, s, px = self.app.c, self.s, self.app.px
        w = self.winfo_width()
        x0, x1 = px(8), w - px(8)
        lw = max(1, px(1))
        for clef, bottom in self.bottom.items():
            for i in range(5):
                self.create_line(x0, bottom - i * s, x1, bottom - i * s, fill=c["ink"], width=lw)
            self.create_line(x1, bottom - 4 * s, x1, bottom, fill=c["ink"], width=lw)
            if clef == "treble":
                self.treble_clef(x0 + 1.5 * s, self.y_of(clef, 32))
            else:
                self.bass_clef(x0 + 1.1 * s, self.y_of(clef, 24))
            for i, step in enumerate(notes.signature_steps(clef, self.fifths) if self.fifths else []):
                x, y = x0 + 3.9 * s + 0.95 * s * i, self.y_of(clef, step)
                self.sharp(x, y) if self.fifths > 0 else self.flat(x, y)
        tops = [b - 4 * s for b in self.bottom.values()]
        self.create_line(x0, min(tops), x0, max(self.bottom.values()), fill=c["ink"], width=max(2, px(2)))
        if self.ghost and not any(n[:2] == self.ghost for n in self.notes):
            self.note(*self.ghost, mix(c["card"], c["accent_fill"], 0.45))
        for clef, step, kind in self.notes:
            self.note(clef, step, c[kind] if kind else c["ink"])

    def note(self, clef, step, color):
        s, x, y = self.s, self.note_x(), self.y_of(clef, step)
        bottom = notes.BOTTOM_LINE[clef]
        ledgers = list(range(bottom + 10, step + 1, 2)) + list(range(bottom - 2, step - 1, -2))
        for ledger in ledgers:
            ly = self.y_of(clef, ledger)
            self.create_line(x - 1.25 * s, ly, x + 1.25 * s, ly, fill=color, width=max(1, self.app.px(1.5)))
        rx, ry = 0.78 * s, 0.52 * s
        self.create_oval(x - rx, y - ry, x + rx, y + ry, outline=color, fill=self["background"],
                         width=max(2, 0.24 * s))

    def curve(self, points, x, y, width, **kw):
        s = self.s
        coords = [v for px_, py_ in points for v in (x + px_ * s, y + py_ * s)]
        self.create_line(*coords, smooth=True, splinesteps=24, width=width, fill=self.app.c["ink"],
                         capstyle="round", joinstyle="round", **kw)

    def treble_clef(self, x, y):
        """A G clef curling around the G line at (x, y)."""
        s = self.s
        self.curve([(0.15, 0.35), (-0.35, 0.1), (-0.1, -0.45), (0.55, -0.35), (0.75, 0.35), (0.05, 0.95),
                    (-0.75, 0.55), (-0.75, -0.35), (0.25, -1.6), (0.6, -2.9), (0.3, -3.7), (-0.1, -3.2),
                    (-0.05, -1.9), (0.3, 1.5), (0.2, 2.15), (-0.3, 2.1), (-0.35, 1.7)], x, y, max(2, 0.2 * s))
        r = 0.2 * s
        self.create_oval(x - 0.35 * s - r, y + 1.7 * s - r, x - 0.35 * s + r, y + 1.7 * s + r,
                         fill=self.app.c["ink"], width=0)

    def bass_clef(self, x, y):
        """An F clef: a dot on the F line at (x, y), an arc and two dots around the line."""
        s, ink = self.s, self.app.c["ink"]
        r = 0.34 * s
        self.create_oval(x - r, y - r, x + r, y + r, fill=ink, width=0)
        self.curve([(-0.1, -0.1), (0.2, -0.85), (0.95, -0.85), (1.3, -0.1), (1.0, 1.0), (-0.2, 2.4)],
                   x, y, max(2, 0.24 * s))
        r = 0.13 * s
        for dy in (-0.5, 0.5):
            self.create_oval(x + 1.8 * s - r, y + dy * s - r, x + 1.8 * s + r, y + dy * s + r, fill=ink, width=0)

    def sharp(self, x, y):
        s, ink = self.s, self.app.c["ink"]
        for dx in (-0.18, 0.18):
            self.create_line(x + dx * s, y - 1.05 * s - dx * 0.3 * s, x + dx * s, y + 1.05 * s - dx * 0.3 * s,
                             fill=ink, width=max(1, 0.1 * s))
        for dy in (-0.33, 0.33):
            self.create_line(x - 0.42 * s, y + (dy + 0.12) * s, x + 0.42 * s, y + (dy - 0.12) * s,
                             fill=ink, width=max(2, 0.22 * s))

    def flat(self, x, y):
        s, ink = self.s, self.app.c["ink"]
        self.create_line(x - 0.25 * s, y - 1.6 * s, x - 0.25 * s, y + 0.5 * s, fill=ink, width=max(1, 0.12 * s))
        self.curve([(-0.25, 0.5), (0.3, 0.0), (0.35, -0.35), (0.05, -0.45), (-0.25, -0.15)], x, y,
                   max(2, 0.16 * s))


class PianoView(tk.Canvas):
    """A piano keyboard. Keys can be marked ("ok", "bad", "target") and named underneath."""

    def __init__(self, master, app, on_click=None):
        self.key_h, self.label_h = app.px(124), app.px(24)
        super().__init__(master, highlightthickness=0, background=app.c["card"], width=1,
                         height=self.key_h + self.label_h)
        self.app, self.on_click = app, on_click
        self.whites, self.marks, self.labels = [], {}, {}
        self.clickable, self.hover, self.pressed = False, None, None
        self.bind("<Configure>", lambda e: self.draw())
        self.bind("<Motion>", lambda e: self.set_hover(self.key_at(e.x, e.y)))
        self.bind("<Leave>", lambda e: self.set_hover(None))
        self.bind("<ButtonPress-1>", self.press)
        self.bind("<ButtonRelease-1>", self.release)

    def set_range(self, lo, hi):
        self.whites = [m for m in range(lo, hi + 1) if notes.is_white(m)]
        self.draw()

    def set_marks(self, marks=None, labels=None, clickable=False):
        self.marks, self.labels, self.clickable = marks or {}, labels or {}, clickable
        self.hover = self.pressed = None
        self.configure(cursor="hand2" if clickable else "")
        self.draw()

    def geometry(self):
        """{midi: (x1, x2, is_black)} for every key."""
        w = self.winfo_width()
        ww = (w - 1) / max(1, len(self.whites))
        bw = ww * 0.58
        keys = {}
        for i, m in enumerate(self.whites):
            keys[m] = (i * ww, (i + 1) * ww, False)
            if i and not notes.is_white(m - 1):
                keys[m - 1] = (i * ww - bw / 2, i * ww + bw / 2, True)
        return keys

    def key_at(self, x, y):
        if not self.clickable or not 0 <= y < self.key_h:
            return None
        keys = self.geometry()
        black_h = self.key_h * 0.62
        for m, (x1, x2, black) in keys.items():
            if black and x1 <= x < x2 and y < black_h:
                return m
        return next((m for m, (x1, x2, black) in keys.items() if not black and x1 <= x < x2), None)

    def set_hover(self, m):
        if m != self.hover:
            self.hover = m
            self.draw()

    def press(self, event):
        self.pressed = self.key_at(event.x, event.y)
        self.draw()

    def release(self, event):
        m, self.pressed = self.pressed, None
        if m is not None and m == self.key_at(event.x, event.y) and self.on_click:
            self.on_click(m)
        self.draw()

    def draw(self):
        self.delete("all")
        if not self.whites or self.winfo_width() < 4 * len(self.whites):
            return
        c, px, rounder = self.app.c, self.app.px, self.app.rounder
        keys = self.geometry()
        edge = mix(WHITE_KEY, "#000000", 0.28)
        for black in (False, True):
            for m, (x1, x2, is_black) in keys.items():
                if is_black != black:
                    continue
                base = BLACK_KEY if black else WHITE_KEY
                fill = base
                kind = self.marks.get(m)
                if kind:
                    fill = mix(base, c["accent_fill"] if kind == "target" else c[kind], 0.8 if black else 0.5)
                elif m == self.pressed:
                    fill = mix(base, c["accent_fill"], 0.4 if black else 0.3)
                elif m == self.hover:
                    fill = mix(base, c["accent_fill"], 0.3 if black else 0.14)
                # Start above the canvas so only the bottom corners show as rounded.
                y2 = self.key_h * (0.62 if black else 1)
                r = px(3) if black else px(5)
                rounder.draw(self, x1, -2 * r - 2, x2 + (0 if black else 1), y2, r, fill, c["card"],
                             None if black else edge, max(1, px(1)))
                if m == 60 and not kind:  # middle C
                    d = px(3)
                    cx = (x1 + x2) / 2
                    self.create_oval(cx - d, y2 - px(14) - d, cx + d, y2 - px(14) + d, fill=c["muted"], width=0)
        for m, text in self.labels.items():
            x1, x2, _ = keys[m]
            kind = self.marks.get(m)
            color = c["accent"] if kind == "target" else c[kind] if kind else c["ink"]
            self.create_text((x1 + x2) / 2, self.key_h + self.label_h / 2 + px(2), text=text, fill=color,
                             font=self.app.fonts["body_semibold"])


class SegmentedButtons(ttk.Frame):
    """A row of buttons where exactly one is chosen."""

    def __init__(self, master, app, options, on_change):
        super().__init__(master)
        self.on_change, self.buttons, self.value = on_change, {}, None
        for i, (value, text) in enumerate(options):
            b = ttk.Button(self, text=text, command=lambda v=value: self.set(v))
            b.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else app.px(8), 0))
            self.columnconfigure(i, weight=1, uniform="seg")
            self.buttons[value] = b

    def set(self, value, notify=True):
        self.value = value
        for v, b in self.buttons.items():
            b.configure(style="Accent.TButton" if v == value else "Tinted.TButton")
        if notify:
            self.on_change()


def key_title(fifths):
    return f"{notes.key_name(fifths)} · {notes.signature_text(fifths)}"


def key_help(fifths):
    if fifths == 0:
        return "Inga ♯ eller ♭: alla toner spelas på de vita tangenterna."
    changed = ", ".join(f"{letter.replace('B', 'H')} blir {notes.note_name(letter, alt)}"
                        for letter, alt in notes.alterations(fifths).items())
    return f"Förtecknen gäller alla oktaver: {changed}."


# ---------- Screens ----------
class HomeScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        px = app.px
        self.heading("Noter", "Läs noter och hitta rätt tangent på pianot.")
        ttk.Label(self, text="TONART", style="Caption.TLabel").pack(anchor="w")
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(px(6), 0))
        ttk.Button(row, text="◀", style="Icon.TButton", width=3, command=lambda: self.step_key(-1)).pack(side="left")
        ttk.Button(row, text="▶", style="Icon.TButton", width=3, command=lambda: self.step_key(1)).pack(side="right")
        self.key_label = ttk.Label(row, style="H2.TLabel", anchor="center")
        self.key_label.pack(fill="x", expand=True)
        self.staff = StaffView(self, app)
        self.staff.pack(fill="x", pady=(px(10), px(4)))
        self.help = ttk.Label(self, style="Muted.TLabel", anchor="center", justify="center")
        self.help.pack(fill="x")
        ttk.Label(self, text="NOTSYSTEM", style="Caption.TLabel").pack(anchor="w", pady=(px(18), 0))
        self.clef = SegmentedButtons(self, app, [("treble", "Diskantklav"), ("bass", "Basklav"),
                                                 ("both", "Båda")], self.refresh)
        self.clef.pack(fill="x", pady=(px(6), 0))
        ttk.Label(self, text="VAD VILL DU ÖVA?", style="Caption.TLabel").pack(anchor="w", pady=(px(18), 0))
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(px(6), 0))
        row.columnconfigure((0, 1), weight=1, uniform="b")
        ttk.Button(row, text="Not → tangent", style="Accent.TButton",
                   command=lambda: self.start("staff-key")).grid(row=0, column=0, sticky="ew")
        ttk.Button(row, text="Tangent → not", style="Accent.TButton",
                   command=lambda: self.start("key-staff")).grid(row=0, column=1, sticky="ew", padx=(px(8), 0))
        self.bind("<Configure>", lambda e: self.help.configure(wraplength=e.width))
        self.fifths = 0
        self.clef.set("treble", notify=False)
        self.refresh()

    def step_key(self, step):
        self.fifths = max(notes.KEYS[0], min(notes.KEYS[-1], self.fifths + step))
        self.refresh()

    def refresh(self):
        self.key_label.configure(text=key_title(self.fifths))
        self.help.configure(text=key_help(self.fifths))
        self.staff.setup(self.clef.value, self.fifths)
        if getattr(self.app, "current", None) is self:
            self.app.layout()

    def start(self, direction):
        self.app.show("quiz", self.clef.value, self.fifths, direction)


class QuizScreen(Screen):
    depth = 1

    def __init__(self, app):
        super().__init__(app)
        px = app.px
        self.progress = ProgressBar(self, app)
        self.progress.pack(fill="x")
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(px(6), px(14)))
        self.progress_text = ttk.Label(top, style="Small.TLabel")
        self.progress_text.pack(side="left")
        ttk.Button(top, text="Avsluta", style="Link.TButton", takefocus=0,
                   command=lambda: app.show("home")).pack(side="right")
        self.prompt = ttk.Label(self, style="Muted.TLabel", anchor="center")
        self.prompt.pack(fill="x")
        self.staff = StaffView(self, app, on_click=self.staff_clicked)
        self.staff.pack(fill="x", pady=(px(6), px(10)))
        self.piano = PianoView(self, app, on_click=self.key_clicked)
        self.piano.pack(fill="x")
        self.feedback = Feedback(self, app)
        self.feedback.pack(fill="x", pady=px(12))
        row = ttk.Frame(self)
        row.pack(fill="x")
        self.btn_reveal = ttk.Button(row, text="Visa svar", style="Tinted.TButton", command=self.reveal)
        self.btn_next = ttk.Button(row, text="Nästa →", style="Accent.TButton", command=self.next_note)
        for key in ("<Return>", "<KP_Enter>"):
            self.btn_next.bind(key, lambda e: self.next_note())
        self.session, self.answered, self.settings = None, False, None

    def on_show(self, choice, fifths, direction, items=None):
        self.settings = (choice, fifths, direction)
        self.session = notes.Session(items or notes.make_notes(choice, fifths, direction), direction, fifths)
        self.staff.setup(choice, fifths)
        self.piano.set_range(*notes.piano_range(choice, fifths))
        self.progress.set(0, animate=False)
        self.next_note()

    @property
    def to_key(self):
        return self.session.direction == "staff-key"

    def next_note(self):
        s = self.session
        if s.current is None:
            self.app.show("summary", s, self.settings)
            return
        self.answered = False
        note = s.current.word
        if self.to_key:
            self.prompt.configure(text="Vilken tangent är det här? Klicka på pianot.")
            self.staff.set_notes([(note["clef"], note["step"], None)])
            self.piano.set_marks(clickable=True)
        else:
            self.prompt.configure(text="Var står den här tonen? Klicka i notsystemet.")
            self.staff.set_notes([], clickable=True)
            self.piano.set_marks({note["midi"]: "target"})
        self.feedback.show()
        self.btn_next.pack_forget()
        self.btn_reveal.pack(fill="x", expand=True)
        self.update_progress()
        self.focus_set()

    def update_progress(self):
        s = self.session
        self.progress.set(s.mastered / s.total)
        key = notes.key_name(s.fifths)
        self.progress_text.configure(text=f"{s.mastered} av {s.total} toner klara · {key}")

    def key_clicked(self, midi):
        if self.answered or not self.to_key:
            return
        note = self.session.current.word
        ok, _ = self.session.check(midi)
        marks, labels = {note["midi"]: "ok"}, {note["midi"]: note["name"]}
        if not ok:
            marks[midi], labels[midi] = "bad", notes.name_of_key(midi, self.session.fifths)
        self.piano.set_marks(marks, labels)
        self.staff.set_notes([(note["clef"], note["step"], "ok" if ok else None)])
        self.after_answer(ok, f"Rätt tangent: {note['name']}")

    def staff_clicked(self, clef, step):
        if self.answered or self.to_key:
            return
        note = self.session.current.word
        clicked = notes.note_at(step, self.session.fifths)
        ok, _ = self.session.check(clicked["midi"])
        shown = [(clef, step, "ok")] if ok else [(note["clef"], note["step"], "ok"), (clef, step, "bad")]
        self.staff.set_notes(shown)
        marks = {note["midi"]: "ok"}
        labels = {note["midi"]: note["name"]}
        if not ok:
            marks[clicked["midi"]], labels[clicked["midi"]] = "bad", clicked["name"]
        self.piano.set_marks(marks, labels)
        self.after_answer(ok, f"Tonen {note['name']} står här")

    def reveal(self):
        if self.answered:
            return
        note = self.session.current.word
        self.session.reveal()
        self.staff.set_notes([(note["clef"], note["step"], "ok")])
        self.piano.set_marks({note["midi"]: "ok"}, {note["midi"]: note["name"]})
        self.answered = True
        self.show_result("bad", plain(random.choice(quiz.REVEAL_MSGS)), f"Det är {note['name']}")

    def after_answer(self, ok, answer):
        self.answered = True
        if ok:
            self.show_result("ok", plain(random.choice(quiz.CORRECT_MSGS)), answer if self.to_key else "")
        else:
            self.show_result("bad", plain(random.choice(quiz.WRONG_MSGS)), answer)

    def show_result(self, kind, message, answer):
        self.feedback.show(kind, message, answer)
        self.btn_reveal.pack_forget()
        self.btn_next.pack(fill="x", expand=True)
        self.btn_next.focus_set()
        self.update_progress()


class NoteResultList(CanvasList):
    """Summary rows: ✓/✗, the note name and where it was written."""

    def __init__(self, master, app):
        super().__init__(master, app, row_h=app.px(40), gap=0)

    def draw(self):
        self.delete("all")
        c, px, fonts = self.app.c, self.app.px, self.app.fonts
        w = self.winfo_width()
        self.app.rounder.draw(self, 0, 0, w, self.content_height(), px(14), c["fill"], c["card"])
        for i, (ok, name, where) in enumerate(self.rows):
            y = i * self.row_h
            mid = y + self.row_h / 2
            if i:
                self.create_line(px(44), y, w - px(14), y, fill=c["line"])
            self.create_text(px(18), mid, text="✓" if ok else "✗", anchor="w",
                             fill=c["ok"] if ok else c["bad"], font=fonts["body_semibold"])
            self.create_text(px(44), mid, text=name, anchor="w", fill=c["ink"],
                             font=fonts["body"] if ok else fonts["body_semibold"])
            self.create_text(w - px(16), mid, text=elide(where, fonts["small"], w / 2), anchor="e",
                             fill=c["muted"], font=fonts["small"])


class SummaryScreen(Screen):
    depth = 2

    def __init__(self, app):
        super().__init__(app)
        px = app.px
        self.heading("Bra jobbat!", center=True)
        self.score = ttk.Label(self, style="Score.TLabel", anchor="center")
        self.score.pack(fill="x", pady=(px(6), 0))
        ttk.Label(self, text="rätt på första försöket", style="Muted.TLabel", anchor="center").pack(fill="x")
        self.scroller = self.results = NoteResultList(self, app)
        self.results.pack(fill="x", pady=(px(20), 0))
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(px(18), 0))
        row.columnconfigure((0, 1), weight=1, uniform="b")
        self.btn_retry = ttk.Button(row, text="Öva på missade toner", style="Accent.TButton",
                                    command=lambda: app.show("quiz", *self.settings, self.session.missed,
                                                             direction="back"))
        self.btn_again = ttk.Button(row, text="Öva igen", style="Tinted.TButton",
                                    command=lambda: app.show("quiz", *self.settings, direction="back"))
        back = self.button_row(10)
        ttk.Button(back, text="Tillbaka till start", style="Tinted.TButton",
                   command=lambda: app.show("home")).pack(side="left")
        self.session, self.settings = None, None

    def on_show(self, session, settings):
        self.session = s = session
        self.settings = settings
        self.score.configure(text=f"{s.hits} av {s.total}")
        rows = []
        for item in sorted(s.all, key=lambda i: (i.word["midi"], i.word["clef"])):
            n = item.word
            name = n["name"] + (" (mitt-C)" if n["step"] == notes.MIDDLE_C else "")
            rows.append((bool(item.first_try), name, notes.CLEF_NAMES[n["clef"]]))
        self.results.set_rows(rows)
        if s.missed:
            self.btn_retry.grid(row=0, column=0, sticky="ew")
            self.btn_again.grid(row=0, column=1, sticky="ew", padx=(self.app.px(8), 0))
            self.btn_retry.focus_set()
        else:
            self.btn_retry.grid_forget()
            self.btn_again.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0)
            self.btn_again.focus_set()


class NoterApp(GlosorApp):
    app_name, size, min_size, card_width = "Noter", (820, 760), (600, 640), 760

    def make_screens(self):
        return {"home": HomeScreen(self), "quiz": QuizScreen(self), "summary": SummaryScreen(self)}


if __name__ == "__main__":
    NoterApp().mainloop()
