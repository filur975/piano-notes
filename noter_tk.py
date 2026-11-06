"""Noter: practise reading notes and finding them on the piano, as a desktop app (Tkinter)."""
import math
import random
import sys
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

import notes

# Apple-style palette: grouped background, solid cards, one accent.
LIGHT = dict(bg="#f2f2f7", card="#ffffff", fill="#f2f2f7", ink="#1c1c1e", muted="#6e6e73", line="#e5e5ea",
             accent="#5856d6", accent_fill="#5856d6", on_accent="#ffffff",
             ok="#248a3d", ok_bg="#e3f6e8", bad="#c93400", bad_bg="#fff0e5")
DARK = dict(bg="#000000", card="#1c1c1e", fill="#2c2c2e", ink="#f5f5f7", muted="#98989d", line="#38383a",
            accent="#a5a3ff", accent_fill="#5e5ce6", on_accent="#ffffff",
            ok="#30d158", ok_bg="#0f2e1a", bad="#ff9f0a", bad_bg="#33240a")



# ---------- Platform ----------
def enable_dpi_awareness():
    """Sharp text on scaled Windows displays (otherwise Windows blurs the whole window)."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass


def system_dark():
    if sys.platform != "win32":
        return False
    try:
        import winreg
        path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            return winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 0
    except OSError:
        return False


def reduced_motion():
    """True when Windows "Animation effects" is turned off."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        enabled = ctypes.c_bool(True)
        ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(enabled), 0)  # SPI_GETCLIENTAREAANIMATION
        return not enabled.value
    except (AttributeError, OSError):
        return False


# ---------- Drawing helpers ----------
def mix(a, b, t):
    """Blend two #rrggbb colors; t=0 gives a, t=1 gives b."""
    a = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def palette(dark):
    c = dict(DARK if dark else LIGHT)
    c["tint"] = mix(c["card"], c["accent_fill"], 0.22 if dark else 0.12)
    c["row_sel"] = mix(c["fill"], c["accent_fill"], 0.22 if dark else 0.14)
    return c


def rounded_image(master, r, fill, bg, border=None, bw=1, width=None, height=None):
    """An anti-aliased rounded rectangle. Flat areas are filled in one go; only the corners are
    computed pixel by pixel."""
    w, h = width or 2 * r + 2, height or 2 * r + 2
    bw = round(bw)
    img = tk.PhotoImage(master=master, width=w, height=h)
    img.put(border or fill, to=(0, 0, w, h))
    if border:
        img.put(fill, to=(bw, bw, w - bw, h - bw))

    def distance(x, y, inset):
        radius = max(r - inset, 0)
        qx = abs(x - w / 2) - (w / 2 - inset - radius)
        qy = abs(y - h / 2) - (h / 2 - inset - radius)
        return math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - radius

    k = r + 1  # corner squares
    for x0 in (0, w - k):
        for y in list(range(k)) + list(range(h - k, h)):
            row = []
            for x in range(x0, x0 + k):
                outer = min(max(0.5 - distance(x + 0.5, y + 0.5, 0), 0), 1)
                if border:
                    inner = min(max(0.5 - distance(x + 0.5, y + 0.5, bw), 0), 1)
                    row.append(mix(mix(bg, border, outer), fill, inner))
                else:
                    row.append(mix(bg, fill, outer))
            img.put("{" + " ".join(row) + "}", to=(x0, y))
    return img


class Rounder:
    """Anti-aliased rounded rectangles on a canvas: four corner images plus plain rectangles."""

    def __init__(self, master):
        self.master, self.cache = master, {}

    def corners(self, r, fill, bg, border, bw):
        key = (r, fill, bg, border, bw)
        if key not in self.cache:
            full = rounded_image(self.master, r, fill, bg, border, bw)
            h = r + 1
            parts = []
            for x, y in ((0, 0), (h, 0), (0, h), (h, h)):
                part = tk.PhotoImage(master=self.master, width=h, height=h)
                part.tk.call(part, "copy", full, "-from", x, y, x + h, y + h, "-to", 0, 0)
                parts.append(part)
            self.cache[key] = parts
        return self.cache[key]

    def draw(self, canvas, x1, y1, x2, y2, r, fill, bg, border=None, bw=1, tags=()):
        x1, y1, x2, y2 = round(x1), round(y1), round(x2), round(y2)
        r = int(min(r, (x2 - x1) // 2 - 1, (y2 - y1) // 2 - 1))
        h = r + 1
        tl, tr, bl, br = self.corners(r, fill, bg, border, bw)
        for img, x, y, anchor in ((tl, x1, y1, "nw"), (tr, x2, y1, "ne"), (bl, x1, y2, "sw"), (br, x2, y2, "se")):
            canvas.create_image(x, y, image=img, anchor=anchor, tags=tags)
        canvas.create_rectangle(x1 + h, y1, x2 - h, y2, fill=fill, width=0, tags=tags)
        canvas.create_rectangle(x1, y1 + h, x2, y2 - h, fill=fill, width=0, tags=tags)
        if border:
            for box in ((x1 + h, y1, x2 - h, y1 + bw), (x1 + h, y2 - bw, x2 - h, y2),
                        (x1, y1 + h, x1 + bw, y2 - h), (x2 - bw, y1 + h, x2, y2 - h)):
                canvas.create_rectangle(*box, fill=border, width=0, tags=tags)


def plain(text):
    """Tk can't draw emoji reliably, so leave them out."""
    return "".join(ch for ch in text if ord(ch) <= 0xFFFF and ch != "️").strip()


def elide(text, font, width):
    if font.measure(text) <= width:
        return text
    while text and font.measure(text + "…") > width:
        text = text[:-1]
    return text + "…"


def wheel_step(event):
    return -1 if event.num == 4 or event.delta > 0 else 1


# ---------- Widgets ----------
class CanvasList(tk.Canvas):
    """Rows drawn on a canvas: as tall as the content up to a maximum, then it scrolls."""

    def __init__(self, master, app, row_h, gap):
        super().__init__(master, highlightthickness=0, background=app.c["card"], height=row_h,
                         width=1, yscrollincrement=app.px(16))
        self.app, self.row_h, self.gap = app, row_h, gap
        self.rows, self.max_h = [], None
        self.bind("<Configure>", lambda e: self.draw())

    def content_height(self):
        n = len(self.rows)
        return n * self.row_h + (n - 1) * self.gap if n else self.row_h

    def set_rows(self, rows):
        self.rows = rows
        self.yview_moveto(0)
        self.fit()
        self.draw()

    def set_max(self, h):
        self.max_h = max(self.row_h * 2, h)
        self.fit()

    def fit(self):
        content = self.content_height()
        h = min(content, self.max_h) if self.max_h else content
        if int(self["height"]) != h:
            self.configure(height=h)
        self.configure(scrollregion=(0, 0, 1, content))

    def wheel(self, event):
        if self.content_height() > self.winfo_height():
            self.yview_scroll(3 * wheel_step(event), "units")

    def draw(self):
        pass



class ProgressBar(tk.Canvas):
    def __init__(self, master, app):
        super().__init__(master, height=app.px(6), width=1, highlightthickness=0, background=app.c["card"])
        self.app, self.value, self.target, self.job = app, 0.0, 0.0, None
        self.bind("<Configure>", lambda e: self.draw())

    def set(self, target, animate=True):
        self.target = target
        if not animate or self.app.reduced:
            self.value = target
            self.draw()
        elif self.job is None:
            self.tick()

    def tick(self):
        # Ease toward the target from the current on-screen value; never overshoots.
        self.value += (self.target - self.value) * 0.16
        if abs(self.target - self.value) < 0.002:
            self.value, self.job = self.target, None
        else:
            self.job = self.after(16, self.tick)
        self.draw()

    def draw(self):
        self.delete("all")
        w, h = self.winfo_width(), int(self["height"])
        r = h / 2
        self.create_line(r, r, w - r, r, width=h, capstyle="round", fill=self.app.c["fill"])
        if self.value > 0.001:
            self.create_line(r, r, r + (w - h) * self.value, r, width=h, capstyle="round", fill=self.app.c["ok"])


class Feedback(tk.Canvas):
    """The answer feedback: a rounded, tinted box with a message and the right answer."""

    def __init__(self, master, app):
        super().__init__(master, height=app.px(86), width=1, highlightthickness=0, background=app.c["card"])
        self.app, self.content = app, (None, "", "")
        self.bind("<Configure>", lambda e: self.draw())

    def show(self, kind=None, message="", answer=""):
        self.content = (kind, message, answer)
        self.draw()

    def draw(self):
        self.delete("all")
        kind, message, answer = self.content
        if not kind:
            return
        c, px, fonts = self.app.c, self.app.px, self.app.fonts
        w, h = self.winfo_width(), self.winfo_height()
        self.app.rounder.draw(self, 0, 0, w, h, px(14), c[kind + "_bg"], c["card"])
        self.create_text(w / 2, 0, text=message, anchor="n", justify="center", width=w - px(28),
                         fill=c[kind], font=fonts["body_semibold"] if answer else fonts["big_bold"], tags="text")
        if answer:
            top = self.bbox("text")[3] + px(2)
            self.create_text(w / 2, top, text=answer, anchor="n", justify="center", width=w - px(28),
                             fill=c[kind], font=fonts["big_bold"], tags="text")
        x1, y1, x2, y2 = self.bbox("text")
        self.move("text", 0, h / 2 - (y1 + y2) / 2)


class Screen(ttk.Frame):
    depth = 0
    scroller = None  # a widget with set_max()/wheel(), capped so the card fits the window

    def __init__(self, app):
        super().__init__(app.card)
        self.app = app

    def heading(self, title, sub=None, center=False):
        anchor = "center" if center else "w"
        label = ttk.Label(self, text=title, style="H2.TLabel", anchor=anchor)
        label.pack(fill="x")
        if sub:
            ttk.Label(self, text=sub, style="Muted.TLabel", anchor=anchor).pack(
                fill="x", pady=(self.app.px(2), self.app.px(18)))
        return label

    def button_row(self, pady_top=18):
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(self.app.px(pady_top), 0))
        return row

    def on_show(self, *args):
        pass



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
        note = s.current.note
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
        note = self.session.current.note
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
        note = self.session.current.note
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
        note = self.session.current.note
        self.session.reveal()
        self.staff.set_notes([(note["clef"], note["step"], "ok")])
        self.piano.set_marks({note["midi"]: "ok"}, {note["midi"]: note["name"]})
        self.answered = True
        self.show_result("bad", plain(random.choice(notes.REVEAL_MSGS)), f"Det är {note['name']}")

    def after_answer(self, ok, answer):
        self.answered = True
        if ok:
            self.show_result("ok", plain(random.choice(notes.CORRECT_MSGS)), answer if self.to_key else "")
        else:
            self.show_result("bad", plain(random.choice(notes.WRONG_MSGS)), answer)

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
        for item in sorted(s.all, key=lambda i: (i.note["midi"], i.note["clef"])):
            n = item.note
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


# ---------- App ----------
class NoterApp(tk.Tk):
    def __init__(self):
        enable_dpi_awareness()
        super().__init__()
        self.dark, self.reduced = system_dark(), reduced_motion()
        self.c = c = palette(self.dark)
        self.scale = self.winfo_fpixels("1i") / 96
        self.title("Noter")
        self.geometry(f"{self.px(820)}x{self.px(760)}")
        self.minsize(self.px(600), self.px(640))
        self.configure(background=c["bg"])
        self.rounder = Rounder(self)
        self.setup_fonts()
        self.setup_style()

        # The card is a rounded rectangle drawn on a canvas, with the current screen on top of it.
        self.holder = tk.Canvas(self, background=c["bg"], highlightthickness=0)
        self.holder.pack(fill="both", expand=True)
        self.card = ttk.Frame(self.holder)
        self.card_win = self.holder.create_window(0, 0, window=self.card, anchor="nw")
        self.holder.bind("<Configure>", self.layout)
        self.card.bind("<Configure>", self.layout)
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.bind_all(seq, self.on_wheel)
        self.slide_dx, self.slide_job = 0.0, None

        self.screens = {"home": HomeScreen(self), "quiz": QuizScreen(self), "summary": SummaryScreen(self)}
        self.current = None
        self.show("home")
        self.dark_title_bar()

    def px(self, n):
        return round(n * self.scale)

    def setup_fonts(self):
        families = set(tkfont.families(self))

        def first(*names):
            return next((n for n in names if n in families), tkfont.nametofont("TkDefaultFont").actual("family"))

        # Prefer the platform's own UI font (Segoe UI Variable on Windows 11 has optical sizes).
        text = first("Segoe UI Variable Text", "Segoe UI", "SF Pro Text", "Helvetica Neue", "Cantarell", "DejaVu Sans")
        display = first("Segoe UI Variable Display", "Segoe UI", "SF Pro Display", "Helvetica Neue", "Cantarell",
                        "DejaVu Sans")
        semibold = (first("Segoe UI Semibold"), "normal") if "Segoe UI Semibold" in families else (text, "bold")

        def make(family, size, weight="normal"):
            return tkfont.Font(self, family=family, size=size, weight=weight)

        self.fonts = {
            "small": make(text, 10),
            "body": make(text, 11),
            "body_semibold": make(semibold[0], 11, semibold[1]),
            "caption": make(semibold[0], 9, semibold[1]),
            "button": make(semibold[0], 11, semibold[1]),
            "big_bold": make(display, 14, "bold"),
            "h2": make(display, 20, "bold"),
            "score": make(display, 40, "bold"),
        }
        tkfont.nametofont("TkDefaultFont").configure(family=text, size=11)
        tkfont.nametofont("TkTextFont").configure(family=text, size=11)

    def setup_style(self):
        c, px = self.c, self.px
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure(".", background=c["card"], foreground=c["ink"], font=self.fonts["body"],
                     borderwidth=0, focuscolor=c["accent_fill"], troughcolor=c["fill"])
        st.configure("TFrame", background=c["card"])
        st.configure("TLabel", background=c["card"], foreground=c["ink"])
        st.configure("H2.TLabel", font=self.fonts["h2"])
        st.configure("Muted.TLabel", foreground=c["muted"])
        st.configure("Small.TLabel", foreground=c["muted"], font=self.fonts["small"])
        st.configure("Caption.TLabel", foreground=c["muted"], font=self.fonts["caption"])
        st.configure("Score.TLabel", font=self.fonts["score"])

        # Rounded buttons, drawn from small anti-aliased images (one per state).
        self.images = []

        def image(r, fill, border=None, bw=1):
            # ttk tiles the middle of the image; a 256x96 middle keeps that to a few copies per widget,
            # which matters on Windows where every copy is a slow drawing call. (The elements get a small
            # minimum size, so the image size doesn't make widgets bigger.)
            img = rounded_image(self, r, fill, card, border, bw, width=2 * r + 256, height=2 * r + 96)
            self.images.append(img)  # Tk images vanish when Python drops the last reference
            return img

        def button(name, bg, fg, press, hover, disabled_bg, disabled_fg, padding=(18, 10), font="button",
                   ring=None, radius=10):
            r = px(radius)
            focus = image(r, bg, ring or c["accent_fill"], max(2, px(2)))  # keyboard focus: a ring, not dots
            st.element_create(f"{name}.bg", "image", image(r, bg), ("disabled", image(r, disabled_bg)),
                              ("pressed", image(r, press)), ("active", image(r, hover)), ("focus", focus),
                              border=r, sticky="nsew", width=2 * r, height=2 * r)
            st.layout(name, [(f"{name}.bg", {"sticky": "nsew", "children": [
                ("Button.padding", {"sticky": "nsew", "children": [("Button.label", {"sticky": "nsew"})]})]})])
            st.configure(name, background=bg, foreground=fg, font=self.fonts[font], anchor="center",
                         padding=(px(padding[0]), px(padding[1])))
            st.map(name, foreground=[("disabled", disabled_fg)])

        a, t, card = c["accent_fill"], c["tint"], c["card"]
        button("Accent.TButton", a, c["on_accent"], mix(a, "#000000", 0.18), mix(a, "#ffffff", 0.1),
               mix(a, card, 0.6), mix(c["on_accent"], card, 0.3), ring=mix(a, "#ffffff", 0.55))
        button("Tinted.TButton", t, c["accent"], mix(t, a, 0.16), mix(t, a, 0.07), c["fill"], c["muted"])
        button("Link.TButton", card, c["muted"], card, card, card, c["muted"], padding=(0, 2), font="small")
        st.configure("Link.TButton", width=-1)
        st.map("Link.TButton", foreground=[("pressed", c["ink"]), ("active", c["ink"])])
        button("Icon.TButton", c["fill"], c["muted"], mix(c["fill"], c["ink"], 0.12), mix(c["fill"], c["ink"], 0.05),
               c["fill"], c["muted"], padding=(8, 6), font="small", radius=8)

    def dark_title_bar(self):
        if sys.platform != "win32" or not self.dark:
            return
        try:
            import ctypes
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            on = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(on), ctypes.sizeof(on))
        except (AttributeError, OSError):
            pass

    def layout(self, event=None):
        W, H = self.holder.winfo_width(), self.holder.winfo_height()
        if W < 2:
            return
        px = self.px
        margin, pad = px(24), px(28)
        w = min(W - 2 * margin, px(760))
        screen = self.current
        if screen is not None and screen.scroller is not None:
            other = self.card.winfo_reqheight() - screen.scroller.winfo_reqheight()
            screen.scroller.set_max(H - 2 * margin - 2 * pad - other)
        x = (W - w) / 2 + self.slide_dx
        self.holder.coords(self.card_win, x + pad, margin + pad)
        self.holder.itemconfigure(self.card_win, width=max(1, w - 2 * pad))
        h = self.card.winfo_reqheight() + 2 * pad
        self.holder.delete("card")
        self.rounder.draw(self.holder, x, margin, x + w, margin + h, px(22), self.c["card"], self.c["bg"],
                          None if self.dark else self.c["line"], tags="card")
        self.holder.tag_lower("card")

    def show(self, name, *args, direction=None):
        screen = self.screens[name]
        if direction is None and self.current is not None:
            direction = "fwd" if screen.depth >= self.current.depth else "back"
        if self.current is not None:
            self.current.pack_forget()
        self.current = screen
        screen.on_show(*args)
        screen.pack(fill="both", expand=True)
        if direction:
            self.slide(direction)
        else:
            self.layout()

    def slide(self, direction):
        """Screens enter along the direction you travel: deeper from the right, back from the left."""
        if self.reduced:
            self.slide_dx = 0.0
            self.layout()
            return
        self.slide_dx = float(self.px(28) * (1 if direction == "fwd" else -1))
        if self.slide_job is None:
            self.slide_step()

    def slide_step(self):
        # Ease out from wherever the card is now, with no overshoot.
        old = self.slide_dx
        self.slide_dx *= 0.72
        if abs(self.slide_dx) < 0.5:
            self.slide_dx, self.slide_job = 0.0, None
        else:
            self.slide_job = self.after(16, self.slide_step)
        # Moving is much cheaper than a full layout, especially on Windows.
        self.holder.move("card", self.slide_dx - old, 0)
        self.holder.move(self.card_win, self.slide_dx - old, 0)

    def on_wheel(self, event):
        if self.current is not None and self.current.scroller is not None:
            self.current.scroller.wheel(event)


if __name__ == "__main__":
    NoterApp().mainloop()
