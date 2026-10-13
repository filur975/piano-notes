"""Glosor: a vocabulary trainer for Swedish and English, as a desktop app (Tkinter)."""
import math
import random
import sys
import tkinter as tk
import uuid
from tkinter import font as tkfont
from tkinter import messagebox, ttk

import quiz
import store

# Apple-style palette: grouped background, solid cards, one accent.
LIGHT = dict(bg="#f2f2f7", card="#ffffff", fill="#f2f2f7", ink="#1c1c1e", muted="#6e6e73", line="#e5e5ea",
             accent="#5856d6", accent_fill="#5856d6", on_accent="#ffffff",
             ok="#248a3d", ok_bg="#e3f6e8", bad="#c93400", bad_bg="#fff0e5", danger="#d70015")
DARK = dict(bg="#000000", card="#1c1c1e", fill="#2c2c2e", ink="#f5f5f7", muted="#98989d", line="#38383a",
            accent="#a5a3ff", accent_fill="#5e5ce6", on_accent="#ffffff",
            ok="#30d158", ok_bg="#0f2e1a", bad="#ff9f0a", bad_bg="#33240a", danger="#ff453a")


# ---------- Data ----------
def load_lists():
    return store.load_data()["lists"]


def save_list(list_id, name, words):
    """Create (list_id=None) or update a list. Returns the saved list."""
    data = store.load_data()
    if list_id is None:
        lst = {"id": uuid.uuid4().hex[:12], "name": name, "words": store.clean_words(words)}
        data["lists"].append(lst)
    else:
        lst = next(l for l in data["lists"] if l["id"] == list_id)
        lst["name"] = name
        lst["words"] = store.clean_words(words, lst["words"])
    store.save_data(data)
    return lst


def delete_list(list_id):
    data = store.load_data()
    data["lists"] = [l for l in data["lists"] if l["id"] != list_id]
    store.save_data(data)


def record_result(word, correct):
    data = store.load_data()
    for lst in data["lists"]:
        if lst["id"] != word["list_id"]:
            continue
        for w in lst["words"]:
            if w["sv"] == word["sv"] and w["en"] == word["en"]:
                w["correct" if correct else "wrong"] += 1
                store.save_data(data)
                return


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


class ChoiceList(CanvasList):
    """Selectable word lists: rounded rows with a checkbox, like a macOS sidebar selection."""

    def __init__(self, master, app, on_change, on_activate):
        super().__init__(master, app, row_h=app.px(50), gap=app.px(6))
        self.on_change, self.on_activate = on_change, on_activate
        self.selected, self.pressed, self.press_idx, self.focus_idx = set(), None, None, 0
        self.configure(takefocus=1)
        self.bind("<ButtonPress-1>", self.press)
        self.bind("<B1-Motion>", self.motion)
        self.bind("<ButtonRelease-1>", self.release)
        self.bind("<space>", lambda e: self.toggle(self.focus_idx))
        self.bind("<Return>", lambda e: self.on_activate())
        self.bind("<Up>", lambda e: self.move_focus(-1))
        self.bind("<Down>", lambda e: self.move_focus(1))
        self.bind("<FocusIn>", lambda e: self.draw())
        self.bind("<FocusOut>", lambda e: self.draw())

    def index_at(self, event):
        y = self.canvasy(event.y)
        i = int(y // (self.row_h + self.gap))
        inside = y - i * (self.row_h + self.gap) < self.row_h
        return i if inside and 0 <= i < len(self.rows) else None

    def press(self, event):
        # Highlight immediately on press; commit on release.
        self.focus_set()
        self.press_idx = self.pressed = self.index_at(event)
        if self.press_idx is not None:
            self.focus_idx = self.press_idx
        self.draw()

    def motion(self, event):
        # Dragging off the row cancels; dragging back re-arms.
        pressed = self.press_idx if self.index_at(event) == self.press_idx else None
        if pressed != self.pressed:
            self.pressed = pressed
            self.draw()

    def release(self, event):
        if self.press_idx is not None and self.index_at(event) == self.press_idx:
            self.toggle(self.press_idx)
        self.press_idx = self.pressed = None
        self.draw()

    def toggle(self, i):
        if not self.rows:
            return
        list_id = self.rows[i]["id"]
        self.selected ^= {list_id}
        self.on_change()
        self.draw()

    def move_focus(self, step):
        if not self.rows:
            return
        self.focus_idx = max(0, min(len(self.rows) - 1, self.focus_idx + step))
        top = self.focus_idx * (self.row_h + self.gap)
        total = self.content_height()
        view_top, view_bottom = (f * total for f in self.yview())
        if top < view_top or top + self.row_h > view_bottom:
            self.yview_moveto(max(0, top - self.gap) / total)
        self.draw()

    def draw(self):
        self.delete("all")
        c, px, fonts = self.app.c, self.app.px, self.app.fonts
        w = self.winfo_width()
        if not self.rows:
            self.create_text(w / 2, self.row_h / 2, text="Inga listor än – skapa en med ”Ny lista”.",
                             fill=c["muted"], font=fonts["body"])
            return
        focused = self.focus_get() is self
        for i, lst in enumerate(self.rows):
            y = i * (self.row_h + self.gap)
            mid = y + self.row_h / 2
            on = lst["id"] in self.selected
            bg = c["row_sel"] if on else c["fill"]
            if i == self.pressed:
                bg = mix(bg, c["ink"], 0.07)
            ring = c["accent_fill"] if focused and i == self.focus_idx else None
            self.app.rounder.draw(self, 0, y, w, y + self.row_h, px(12), bg, c["card"], ring, max(2, px(2)))
            s = px(22)
            x0, y0 = px(14), round(mid - s / 2)
            box = c["accent_fill"] if on else c["card"]
            self.app.rounder.draw(self, x0, y0, x0 + s, y0 + s, s * 0.28, box, bg,
                                  c["accent_fill"] if on else c["muted"], max(1, px(1.5)))
            if on:
                self.create_line(x0 + s * .27, y0 + s * .52, x0 + s * .44, y0 + s * .69, x0 + s * .75, y0 + s * .33,
                                 fill=c["on_accent"], width=max(2, px(2.5)), capstyle="round", joinstyle="round")
            count = f"{len(lst['words'])} ord"
            count_w = fonts["small"].measure(count)
            self.create_text(w - px(16), mid, text=count, anchor="e", fill=c["muted"], font=fonts["small"])
            name = elide(lst["name"], fonts["body"], w - px(52) - count_w - px(32))
            self.create_text(px(50), mid, text=name, anchor="w", fill=c["ink"], font=fonts["body"])


class ResultList(CanvasList):
    """Summary rows: ✓/✗, the question and the answer, on one rounded grouped surface."""

    def __init__(self, master, app):
        super().__init__(master, app, row_h=app.px(44), gap=0)

    def draw(self):
        self.delete("all")
        c, px, fonts = self.app.c, self.app.px, self.app.fonts
        w = self.winfo_width()
        self.app.rounder.draw(self, 0, 0, w, self.content_height(), px(14), c["fill"], c["card"])
        for i, (ok, question, answer) in enumerate(self.rows):
            y = i * self.row_h
            mid = y + self.row_h / 2
            if i:
                self.create_line(px(44), y, w - px(14), y, fill=c["line"])
            self.create_text(px(18), mid, text="✓" if ok else "✗", anchor="w",
                             fill=c["ok"] if ok else c["bad"], font=fonts["body_semibold"])
            lead = f"{question} – "
            self.create_text(px(44), mid, text=lead, anchor="w", fill=c["ink"], font=fonts["body"])
            x = px(44) + fonts["body"].measure(lead)
            font = fonts["body"] if ok else fonts["body_semibold"]
            text = answer if ok else f"rätt svar: {answer}"
            self.create_text(x, mid, text=elide(text, font, w - x - px(14)), anchor="w", fill=c["ink"], font=font)


class ScrollFrame(ttk.Frame):
    """Widgets in a scrolling area that is as tall as its content, up to a maximum."""

    def __init__(self, master, app):
        super().__init__(master)
        self.app, self.max_h, self.bar_shown = app, None, False
        self.canvas = tk.Canvas(self, highlightthickness=0, background=app.c["card"], height=1, width=1,
                                yscrollincrement=app.px(16))
        self.bar = ttk.Scrollbar(self, orient="vertical", style="Thin.Vertical.TScrollbar",
                                 command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.content = ttk.Frame(self.canvas)
        win = self.canvas.create_window(0, 0, window=self.content, anchor="nw")
        self.content.bind("<Configure>", lambda e: self.fit())
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(win, width=e.width))

    def set_max(self, h):
        self.max_h = max(self.app.px(140), h)
        self.fit()

    def fit(self):
        content = self.content.winfo_reqheight()
        h = min(content, self.max_h) if self.max_h else content
        if int(self.canvas["height"]) != h:
            self.canvas.configure(height=h)
        self.canvas.configure(scrollregion=(0, 0, 1, content))
        need = content > h
        if need != self.bar_shown:
            self.bar_shown = need
            if need:
                self.bar.pack(side="right", fill="y", padx=(self.app.px(6), 0))
            else:
                self.bar.pack_forget()

    def wheel(self, event):
        if self.bar_shown:
            self.canvas.yview_scroll(3 * wheel_step(event), "units")

    def scroll_to_end(self):
        self.update_idletasks()
        self.canvas.yview_moveto(1)


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


# ---------- Screens ----------
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


class HomeScreen(Screen):
    def __init__(self, app):
        super().__init__(app)
        px = app.px
        self.heading("Gloslistor", "Bocka i en eller flera listor att öva på.")
        self.scroller = self.choices = ChoiceList(self, app, self.update_buttons, self.practice)
        self.choices.pack(fill="x")
        row = self.button_row()
        self.btn_practice = ttk.Button(row, text="Öva", style="Accent.TButton", command=self.practice)
        self.btn_practice.pack(side="left")
        self.btn_edit = ttk.Button(row, text="Redigera", style="Tinted.TButton", command=self.edit)
        self.btn_edit.pack(side="left", padx=px(8))
        ttk.Button(row, text="+ Ny lista", style="Tinted.TButton",
                   command=lambda: app.show("edit", None)).pack(side="right")
        self.lists = []

    def on_show(self, select_id=None):
        prev = {select_id} if select_id else set(self.choices.selected)
        self.lists = load_lists()
        ids = {l["id"] for l in self.lists}
        prev &= ids
        if not prev and self.lists:
            prev = {self.lists[0]["id"]}
        self.choices.selected = prev
        self.choices.set_rows(self.lists)
        self.update_buttons()
        self.choices.focus_set()

    def checked(self):
        return [l for l in self.lists if l["id"] in self.choices.selected]

    def update_buttons(self):
        n = len(self.checked())
        self.btn_practice.state(["!disabled"] if n >= 1 else ["disabled"])
        self.btn_edit.state(["!disabled"] if n == 1 else ["disabled"])

    def edit(self):
        if len(self.checked()) == 1:
            self.app.show("edit", self.checked()[0])

    def practice(self):
        chosen = self.checked()
        words = quiz.combine(chosen)
        if words:
            self.app.show("mode", words)
        elif len(chosen) == 1:
            self.app.show("edit", chosen[0])


class EditScreen(Screen):
    depth = 1

    def __init__(self, app):
        super().__init__(app)
        px = app.px
        self.title = self.heading("Redigera lista", "Tomma rader hoppas över när du sparar.")
        ttk.Label(self, text="Namn på listan", style="Caption.TLabel").pack(anchor="w")
        name_box = ttk.Frame(self)
        name_box.pack(fill="x", pady=(px(6), px(18)))
        self.name = ttk.Entry(name_box, style="Field.TEntry", font=app.fonts["body"])
        self.name.pack(fill="x")
        self.name.bind("<Key>", lambda e: self.set_name_error(False))
        self.name_error = ttk.Label(name_box, text="Ge listan ett namn.", style="Error.TLabel")

        self.scroller = ScrollFrame(self, app)
        self.scroller.pack(fill="x")
        rows = self.rows_frame = self.scroller.content
        rows.columnconfigure((0, 1), weight=1, uniform="col")
        ttk.Label(rows, text="SVENSKA", style="Caption.TLabel").grid(row=0, column=0, sticky="w", pady=(0, px(6)))
        ttk.Label(rows, text="ENGELSKA", style="Caption.TLabel").grid(row=0, column=1, sticky="w", padx=px(8),
                                                                       pady=(0, px(6)))

        add = ttk.Button(self, text="+ Lägg till ord", style="Tinted.TButton", command=self.add_row_focus)
        add.pack(anchor="w", pady=(px(10), 0))
        row = self.button_row(22)
        ttk.Button(row, text="Spara", style="Accent.TButton", command=self.save).pack(side="left")
        ttk.Button(row, text="Avbryt", style="Tinted.TButton",
                   command=lambda: app.show("home")).pack(side="left", padx=px(8))
        self.btn_delete = ttk.Button(row, text="Ta bort lista", style="Danger.TButton", command=self.delete)
        self.editing, self.rows, self.next_grid_row = None, [], 1

    def set_name_error(self, on):
        self.name.state(["invalid"] if on else ["!invalid"])
        if on:
            self.name_error.pack(anchor="w", pady=(self.app.px(6), 0))
        else:
            self.name_error.pack_forget()

    def on_show(self, lst):
        self.editing = lst
        self.title.configure(text="Redigera lista" if lst else "Ny lista")
        self.name.delete(0, "end")
        self.name.insert(0, lst["name"] if lst else "")
        self.set_name_error(False)
        for row in self.rows:
            for widget in row:
                widget.destroy()
        self.rows, self.next_grid_row = [], 1  # grid row 0 is the header
        for w in (lst["words"] if lst else [{}, {}, {}]):
            self.add_row(w.get("sv", ""), w.get("en", ""))
        if lst:
            self.btn_delete.pack(side="right")
        else:
            self.btn_delete.pack_forget()
        self.scroller.canvas.yview_moveto(0)
        self.name.focus_set()

    def add_row(self, sv="", en=""):
        px, r = self.app.px, self.next_grid_row
        self.next_grid_row += 1
        sv_entry = ttk.Entry(self.rows_frame, style="Field.TEntry", font=self.app.fonts["body"])
        en_entry = ttk.Entry(self.rows_frame, style="Field.TEntry", font=self.app.fonts["body"])
        sv_entry.insert(0, sv)
        en_entry.insert(0, en)
        sv_entry.grid(row=r, column=0, sticky="ew", pady=px(4))
        en_entry.grid(row=r, column=1, sticky="ew", pady=px(4), padx=px(8))
        row = [sv_entry, en_entry]
        remove = ttk.Button(self.rows_frame, text="✕", style="Icon.TButton", takefocus=0, width=2,
                            command=lambda: self.remove_row(row))
        remove.grid(row=r, column=2, pady=px(4))
        row.append(remove)
        self.rows.append(row)
        return sv_entry

    def add_row_focus(self):
        entry = self.add_row()
        self.scroller.scroll_to_end()
        entry.focus_set()

    def remove_row(self, row):
        for widget in row:
            widget.destroy()
        self.rows.remove(row)

    def save(self):
        name = self.name.get().strip()[:80]
        if not name:
            self.set_name_error(True)
            self.name.focus_set()
            return
        words = [{"sv": sv.get(), "en": en.get()} for sv, en, _ in self.rows]
        saved = save_list(self.editing["id"] if self.editing else None, name, words)
        self.app.show("home", saved["id"])

    def delete(self):
        # Deleting can't be undone, so this is the one place that asks first.
        if messagebox.askyesno("Ta bort lista", f"Vill du ta bort listan ”{self.editing['name']}”?",
                               parent=self, icon="warning"):
            delete_list(self.editing["id"])
            self.app.show("home")


class ModeScreen(Screen):
    depth = 1

    def __init__(self, app):
        super().__init__(app)
        px = app.px
        self.heading("Vad vill du öva?", "Välj åt vilket håll du vill översätta.")
        row = ttk.Frame(self)
        row.pack(fill="x")
        row.columnconfigure((0, 1), weight=1, uniform="b")
        ttk.Button(row, text="Svenska → Engelska", style="Accent.TButton",
                   command=lambda: app.show("quiz", self.words, "sv-en")).grid(row=0, column=0, sticky="ew")
        ttk.Button(row, text="Engelska → Svenska", style="Accent.TButton",
                   command=lambda: app.show("quiz", self.words, "en-sv")).grid(row=0, column=1, sticky="ew",
                                                                                padx=(px(8), 0))
        back = self.button_row(14)
        ttk.Button(back, text="Tillbaka", style="Tinted.TButton", command=lambda: app.show("home")).pack(side="left")
        self.words = []

    def on_show(self, words=None):
        if words is not None:
            self.words = words


class QuizScreen(Screen):
    depth = 2

    def __init__(self, app):
        super().__init__(app)
        px = app.px
        self.progress = ProgressBar(self, app)
        self.progress.pack(fill="x")
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(px(6), px(20)))
        self.progress_text = ttk.Label(top, style="Small.TLabel")
        self.progress_text.pack(side="left")
        ttk.Button(top, text="Avsluta", style="Link.TButton", takefocus=0,
                   command=lambda: app.show("home")).pack(side="right")
        self.prompt = ttk.Label(self, style="Muted.TLabel", anchor="center")
        self.prompt.pack(fill="x")
        self.word = ttk.Label(self, style="Word.TLabel", anchor="center", justify="center")
        self.word.pack(fill="x", pady=(px(2), px(18)))
        self.answer = ttk.Entry(self, style="Field.TEntry", font=app.fonts["big"], justify="center")
        self.answer.pack(fill="x")
        self.answer.bind("<Return>", lambda e: self.check())
        self.answer.bind("<KP_Enter>", lambda e: self.check())
        self.feedback = Feedback(self, app)
        self.feedback.pack(fill="x", pady=px(16))
        row = ttk.Frame(self)
        row.pack(fill="x")
        self.btn_check = ttk.Button(row, text="Svara", style="Accent.TButton", command=self.check)
        self.btn_reveal = ttk.Button(row, text="Visa svar", style="Tinted.TButton", command=self.reveal)
        self.btn_next = ttk.Button(row, text="Nästa →", style="Accent.TButton", command=self.next_word)
        for key in ("<Return>", "<KP_Enter>"):
            self.btn_next.bind(key, lambda e: self.next_word())
        self.bind("<Configure>", lambda e: self.word.configure(wraplength=e.width))
        self.session, self.answered, self.shake_job = None, False, None

    def on_show(self, words, direction):
        self.session = quiz.Session(words, direction)
        self.progress.set(0, animate=False)
        self.next_word()

    def next_word(self):
        s = self.session
        if s.current is None:
            self.app.show("summary", s)
            return
        self.answered = False
        self.prompt.configure(text="Vad heter detta på engelska?" if s.direction == "sv-en"
                              else "Vad heter detta på svenska?")
        self.word.configure(text=s.question(s.current.word))
        self.answer.state(["!disabled"])
        self.answer.delete(0, "end")
        self.feedback.show()
        self.btn_next.pack_forget()
        self.btn_check.pack(side="left", fill="x", expand=True)
        self.btn_reveal.pack(side="left", fill="x", expand=True, padx=(self.app.px(8), 0))
        self.update_progress()
        self.answer.focus_set()

    def update_progress(self):
        s = self.session
        self.progress.set(s.mastered / s.total)
        self.progress_text.configure(text=f"{s.mastered} av {s.total} ord klara")

    def check(self):
        if self.answered:
            self.next_word()
            return
        given = self.answer.get()
        if not given.strip():
            return
        s = self.session
        word = s.current.word
        ok, first = s.check(given)
        if first:
            record_result(word, ok)
        if ok:
            self.after_answer("ok", plain(random.choice(quiz.CORRECT_MSGS)))
        else:
            self.after_answer("bad", plain(random.choice(quiz.WRONG_MSGS)), f"Rätt stavning: {s.answer_of(word)}")
            self.shake()

    def reveal(self):
        if self.answered:
            return
        s = self.session
        word = s.current.word
        if s.reveal():
            record_result(word, False)
        self.after_answer("bad", plain(random.choice(quiz.REVEAL_MSGS)), f"Svar: {s.answer_of(word)}")

    def after_answer(self, kind, message, answer=""):
        self.answered = True
        self.feedback.show(kind, message, answer)
        self.answer.state(["disabled"])
        self.btn_check.pack_forget()
        self.btn_reveal.pack_forget()
        self.btn_next.pack(fill="x", expand=True)
        self.btn_next.focus_set()
        self.update_progress()

    def shake(self):
        """A short, damped side-to-side shake of the answer field, like a wrong password on a Mac."""
        if self.app.reduced:
            return
        offsets = [-8, 7, -5, 3, -1, 0]

        def step(i=0):
            dx = self.app.px(offsets[i])
            self.answer.pack_configure(padx=(max(0, 2 * dx), max(0, -2 * dx)))
            self.shake_job = self.after(40, step, i + 1) if i + 1 < len(offsets) else None

        if self.shake_job:
            self.after_cancel(self.shake_job)
        step()


class SummaryScreen(Screen):
    depth = 3

    def __init__(self, app):
        super().__init__(app)
        px = app.px
        self.heading("Bra jobbat!", center=True)
        self.score = ttk.Label(self, style="Score.TLabel", anchor="center")
        self.score.pack(fill="x", pady=(px(6), 0))
        ttk.Label(self, text="rätt på första försöket", style="Muted.TLabel", anchor="center").pack(fill="x")
        self.scroller = self.results = ResultList(self, app)
        self.results.pack(fill="x", pady=(px(20), 0))
        row = ttk.Frame(self)
        row.pack(fill="x", pady=(px(18), 0))
        row.columnconfigure((0, 1), weight=1, uniform="b")
        self.btn_retry = ttk.Button(row, text="Öva på missade ord", style="Accent.TButton",
                                    command=lambda: app.show("quiz", self.session.missed, self.session.direction,
                                                             direction="fwd"))
        self.btn_again = ttk.Button(row, text="Öva igen", style="Tinted.TButton", command=lambda: app.show("mode"))
        back = self.button_row(10)
        ttk.Button(back, text="Tillbaka till listorna", style="Tinted.TButton",
                   command=lambda: app.show("home")).pack(side="left")
        self.session = None

    def on_show(self, session):
        self.session = s = session
        self.score.configure(text=f"{s.hits} av {s.total}")
        self.results.set_rows([(bool(i.first_try), s.question(i.word), s.answer_of(i.word)) for i in s.all])
        if s.missed:
            self.btn_retry.grid(row=0, column=0, sticky="ew")
            self.btn_again.grid(row=0, column=1, sticky="ew", padx=(self.app.px(8), 0))
            self.btn_retry.focus_set()
        else:
            self.btn_retry.grid_forget()
            self.btn_again.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0)
            self.btn_again.focus_set()


# ---------- App ----------
class GlosorApp(tk.Tk):
    app_name, size, min_size, card_width = "Glosor", (600, 660), (440, 480), 560

    def __init__(self):
        enable_dpi_awareness()
        super().__init__()
        self.dark, self.reduced = system_dark(), reduced_motion()
        self.c = c = palette(self.dark)
        self.scale = self.winfo_fpixels("1i") / 96
        self.title(self.app_name)
        self.geometry(f"{self.px(self.size[0])}x{self.px(self.size[1])}")
        self.minsize(self.px(self.min_size[0]), self.px(self.min_size[1]))
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

        self.screens = self.make_screens()
        self.current = None
        self.show("home")
        self.dark_title_bar()

    def make_screens(self):
        return {
            "home": HomeScreen(self), "edit": EditScreen(self), "mode": ModeScreen(self),
            "quiz": QuizScreen(self), "summary": SummaryScreen(self),
        }

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
            "big": make(text, 16),
            "big_bold": make(display, 14, "bold"),
            "h2": make(display, 20, "bold"),
            "word": make(display, 30, "bold"),
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
        st.configure("Error.TLabel", foreground=c["danger"], font=self.fonts["small"])
        st.configure("Word.TLabel", font=self.fonts["word"])
        st.configure("Score.TLabel", font=self.fonts["score"])

        # Rounded buttons and fields, drawn from small anti-aliased images (one per state).
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
        button("Danger.TButton", card, c["danger"], mix(card, c["danger"], 0.12), mix(card, c["danger"], 0.06),
               card, c["muted"])
        button("Link.TButton", card, c["muted"], card, card, card, c["muted"], padding=(0, 2), font="small")
        st.configure("Link.TButton", width=-1)
        st.map("Link.TButton", foreground=[("pressed", c["ink"]), ("active", c["ink"])])
        button("Icon.TButton", c["fill"], c["muted"], mix(c["fill"], c["ink"], 0.12), mix(c["fill"], c["ink"], 0.05),
               c["fill"], c["muted"], padding=(8, 6), font="small", radius=8)

        r, f = px(10), c["fill"]
        st.element_create("Field.bg", "image", image(r, f, c["line"]),
                          ("invalid", image(r, f, c["danger"], px(2))), ("focus", image(r, f, c["accent_fill"], px(2))),
                          border=r, sticky="nsew", width=2 * r, height=2 * r)
        st.layout("Field.TEntry", [("Field.bg", {"sticky": "nsew", "children": [
            ("Entry.padding", {"sticky": "nsew", "children": [("Entry.textarea", {"sticky": "nsew"})]})]})])
        st.configure("Field.TEntry", fieldbackground=f, background=f, foreground=c["ink"], insertcolor=c["ink"],
                     selectbackground=c["accent_fill"], selectforeground=c["on_accent"], padding=(px(12), px(9)))
        st.map("Field.TEntry", foreground=[("disabled", c["ink"])])

        st.layout("Thin.Vertical.TScrollbar", [("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
            ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
        st.configure("Thin.Vertical.TScrollbar", troughcolor=c["card"], background=c["line"], bordercolor=c["card"],
                     lightcolor=c["line"], darkcolor=c["line"], gripcount=0, arrowsize=px(6))
        st.map("Thin.Vertical.TScrollbar", background=[("active", c["muted"])])

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
        w = min(W - 2 * margin, px(self.card_width))
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
    GlosorApp().mainloop()
