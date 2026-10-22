# Authors: Kahekili Spears, Jack O'Brien, Woody Churchward
# Date created: 10/20/26
# Date modified: 10/20/26
# Purpose: Reaction time game

import math
import os
import random
import subprocess
import sys
import time
import textwrap
import tkinter as tk
from dataclasses import dataclass
from typing import Any, Callable, Optional, TypeVar

if sys.platform == "win32":
    import winsound

# ============================================================
# Constants
# ============================================================
FONT = "Helvetica"
IS_MAC = sys.platform == "darwin"
HAND = "pointinghand" if IS_MAC else "hand2"
PIXEL_FONT = "Monaco" if IS_MAC else "Courier"
SLOWMO = {"Fast": 1.6, "Normal": 1.0, "Cinematic": 0.7}  # animation speed multipliers
# Bot levels: (average reaction ms, spread ms, chance it jumps the gun)
BOT_LEVELS = {"Easy": (480, 90, 0.06), "Medium": (330, 60, 0.03),
              "Hard": (240, 40, 0.012), "Brutal": (175, 22, 0.004)}
# Trainer tempos: (min wait ms, max wait ms, cool-down multiplier)
TRAINER_TEMPOS = {"Fast": (500, 1500, 1.0), "Rapid": (350, 1000, 0.7), "Blitz": (250, 700, 0.5)}
OUTFIT_HATS = ["Cowboy", "Sombrero", "Top Hat", "Cap", "Bandana"]
OUTFIT_FACES = ["None", "Mustache", "Shades", "Eyepatch"]
OUTFIT_COLORS = [("Red", "#e43b44"), ("Blue", "#41a6f6"), ("Gold", "#ffcd75"), ("Lime", "#a7f070"),
                 ("Cyan", "#73eff7"), ("Orange", "#ef7d57"), ("White", "#f4f4f4"), ("Pink", "#b55088")]
DEFAULT_OUTFITS = [dict(hat="Cowboy", color="#e43b44", face="None"),
                   dict(hat="Cowboy", color="#41a6f6", face="None")]

MIN_PLAYERS, MAX_PLAYERS = 2, 8
MIN_ROUNDS, MAX_ROUNDS = 1, 15
MIN_TOO_SLOW, MAX_TOO_SLOW = 1.0, 5.0
NAME_MAX = 12

COLLECT_WINDOW_MS = 900  # how long after the first press we wait for the others
COUNTDOWN_STEP_MS = 700  # speed of the 3-2-1 countdown

DEFAULT_KEYS = ["a", "l", "q", "p", "z", "m", "x", "n"]
RESERVED_KEYS = {"space", "escape", "return", "tab", "f11"}
ARROW_KEYS = {"up", "down", "left", "right"}

WAIT_PRESETS = {"Quick": (1000, 3000), "Normal": (1500, 5000), "Long": (3000, 8000)}

SOUND_DIR = "/System/Library/Sounds"
SOUND_FILES = {
    "tick": "Tink", "go": "Pop", "hit": "Ping", "win": "Glass",
    "buzz": "Basso", "void": "Funk", "fanfare": "Hero",
}

# Game states
IDLE = "idle"
COUNTDOWN = "countdown"
WAITING = "waiting"
GO = "go"
ROUND_OVER = "round_over"
MATCH_OVER = "match_over"
SHOWDOWN = "showdown"  # slow-mo duel animation playing (Pixel theme, 2 players)

VOID = "void"  # marker stored in the round log for a voided round

# ============================================================
# Themes:  (background, text) for each screen state
# ============================================================
THEMES: dict[str, dict[str, Any]] = {
    "Classic": {
        "idle": ("#2b2d42", "#ffffff"), "wait": ("#d90429", "#ffffff"),
        "go": ("#2dc653", "#052e16"), "result": ("#3a86ff", "#ffffff"),
        "accent": "#ffd166", "accent_text": "#2b2d42",
        "players": ["#ff6b6b", "#4dd0e1", "#ffd166", "#b388ff",
                    "#80ed99", "#ff9f1c", "#f78fb3", "#ffffff"],
    },
    "Neon": {
        "idle": ("#0b0c1e", "#f1f1f1"), "wait": ("#ff0054", "#ffffff"),
        "go": ("#00f5d4", "#00120f"), "result": ("#6a00f4", "#ffffff"),
        "accent": "#fee440", "accent_text": "#0b0c1e",
        "players": ["#ff0054", "#00f5d4", "#fee440", "#9b5de5",
                    "#00bbf9", "#f15bb5", "#8ac926", "#ff9770"],
    },
    "Dark": {
        "idle": ("#121212", "#e5e7eb"), "wait": ("#7f1d1d", "#fee2e2"),
        "go": ("#14532d", "#dcfce7"), "result": ("#1e3a8a", "#dbeafe"),
        "accent": "#fbbf24", "accent_text": "#121212",
        "players": ["#f87171", "#60a5fa", "#fbbf24", "#a78bfa",
                    "#34d399", "#fb923c", "#f472b6", "#e5e7eb"],
    },
    "Colorblind": {
        "idle": ("#222b3a", "#ffffff"), "wait": ("#e69f00", "#1a1a1a"),
        "go": ("#0072b2", "#ffffff"), "result": ("#5b6b86", "#ffffff"),
        "accent": "#f0e442", "accent_text": "#222b3a",
        "players": ["#e69f00", "#56b4e9", "#009e73", "#f0e442",
                    "#0072b2", "#d55e00", "#cc79a7", "#ffffff"],
    },
}
THEMES["Pixel"] = {
    "idle": ("#1a1c2c", "#f4f4f4"), "wait": ("#b13e53", "#f4f4f4"),
    "go": ("#38b764", "#1a1c2c"), "result": ("#29366f", "#f4f4f4"),
    "accent": "#ffcd75", "accent_text": "#1a1c2c",
    "players": ["#e43b44", "#41a6f6", "#ffcd75", "#a7f070",
                "#73eff7", "#ef7d57", "#f4f4f4", "#b55088"],
    "font": PIXEL_FONT, "square": True, "pixel": True,
    "btn": "#333c57", "btn_hover": "#566c86", "btn_edge": "#94b0c2",
}
THEME_NAMES = list(THEMES)


# ============================================================
# Small helpers
# ============================================================
def _rgb(color):
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def mix(a, b, t):
    """Blend color a toward color b by fraction t (0..1)."""
    ra, ga, ba = _rgb(a)
    rb, gb, bb = _rgb(b)
    return "#{:02x}{:02x}{:02x}".format(
        int(ra + (rb - ra) * t), int(ga + (gb - ga) * t), int(ba + (bb - ba) * t)
    )


def tint(color, t):
    return mix(color, "#ffffff", t)


def key_label(key):
    return key.upper() if len(key) == 1 else key.capitalize()


T = TypeVar("T", int, float)


def clamp(value: T, low: T, high: T) -> T:
    return max(low, min(high, value))


@dataclass
class Settings:
    num_players: int = 2
    rounds: int = 5
    too_slow: float = 2.0
    wait: str = "Normal"
    countdown: bool = True
    sound: bool = True
    shake: bool = True
    duel_anim: bool = True  # slow-mo showdown (Pixel theme, 2 players)
    slowmo: str = "Normal"  # Fast / Normal / Cinematic
    theme: str = "Pixel"
    bot_level: str = "Medium"  # Easy / Medium / Hard / Brutal
    early_clinch: bool = True  # end the match as soon as nobody can catch the leader
    arena: str = "Desert"  # Desert / Snow Town / Cave / Space Station
    trainer_tempo: str = "Fast"  # Fast / Rapid / Blitz
    fullscreen: bool = False


@dataclass
class Player:
    index: int
    name: str
    key: str
    score: int = 0
    streak: int = 0
    bot: bool = False


# ============================================================
# A label that behaves like a button (native Mac buttons ignore colors)
# ============================================================
class FlatButton(tk.Label):
    def __init__(self, parent, text, command, theme, bg, fg,
                 style="secondary", size=14, padx=20, pady=9, width=0):
        super().__init__(parent, bd=0, cursor=HAND)
        self.command = command
        self.theme = theme
        self.style = style
        self.screen_bg = bg
        self.screen_fg = fg
        self.font_size = size  # (not 'size': tk.Label already has a size() method)
        self.text_value = text
        self.width_chars = width
        self.pixel = bool(theme.get("pixel"))
        self.hovering = False
        self._img: Optional[tk.PhotoImage] = None
        if self.pixel:  # chunky bordered pixel button, label text drawn with the bitmap font
            self.px = max(8, padx // 2 + 2)  # padding is baked into the pixel size below
            self.py = max(6, pady // 2 + 2)
            self.configure(padx=0, pady=0, highlightthickness=3)
        else:
            self.configure(padx=padx, pady=pady)
            if width:
                self.configure(width=width)
        self.paint()
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<ButtonRelease-1>", self._release)

    def colors(self):
        """(background, text, hover background, border or None)"""
        th = self.theme
        if self.pixel:
            if self.style == "primary":
                base = th["accent"]
                return base, th["accent_text"], tint(base, 0.28), tint(base, 0.55)
            return th["btn"], PANEL_FG, th["btn_hover"], th["btn_edge"]
        if self.style == "primary":
            base = th["accent"]
            return base, th["accent_text"], tint(base, 0.28), None
        base = mix(self.screen_bg, self.screen_fg, 0.16)
        return base, self.screen_fg, mix(self.screen_bg, self.screen_fg, 0.32), None

    def paint(self):
        base, text, hover, edge = self.colors()
        bg = hover if self.hovering else base
        if self.pixel:
            scale = pixel_scale(self.font_size)
            img = bitmap_text_image(self.text_value, scale, text, bg, "center")
            self._img = img
            width = img.width()
            if self.width_chars:
                width = max(width, self.width_chars * 6 * scale)
            self.configure(image=img, text="", bg=bg, width=width + 2 * self.px,
                           height=img.height() + 2 * self.py,
                           highlightbackground=edge, highlightcolor=edge)
        else:
            self.configure(text=self.text_value, bg=bg, fg=text,
                           font=(FONT, self.font_size, "bold"))

    def set_text(self, text):
        self.text_value = text
        self.paint()

    def set_screen(self, bg, fg):
        self.screen_bg, self.screen_fg = bg, fg
        self.paint()

    def _enter(self, _event):
        self.hovering = True
        self.paint()

    def _leave(self, _event):
        self.hovering = False
        self.paint()

    def _release(self, event):
        inside = 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height()
        if inside and self.command:
            self.command()  # may destroy this widget; don't touch self afterward


# ============================================================
# Pixel-art duel scene (Pixel theme + exactly 2 players)
# ============================================================
PX_DARK = "#1a1c2c"
PX_WHITE = "#f4f4f4"
PX_YELLOW = "#ffcd75"
PX_ORANGE = "#ef7d57"
PX_RED = "#b13e53"
PX_PURPLE = "#5d275d"
PX_BLUE = "#3b5dc9"
PX_NAVY = "#29366f"
PX_GREY = "#94b0c2"
PX_SLATE = "#566c86"
PX_GREEN = "#38b764"
PX_LIME = "#a7f070"
SKIN = "#f2c28b"
BOOT = "#4a2f20"
HOLSTER = "#7a4a2b"

# 5x7 bitmap font for the big in-scene callouts ("GO!", "HIT!", ...)
_GLYPH_SRC = {
    "A": ".###./#...#/#...#/#####/#...#/#...#/#...#",
    "B": "####./#...#/#...#/####./#...#/#...#/####.",
    "C": ".####/#..../#..../#..../#..../#..../.####",
    "D": "####./#...#/#...#/#...#/#...#/#...#/####.",
    "E": "#####/#..../#..../####./#..../#..../#####",
    "F": "#####/#..../#..../####./#..../#..../#....",
    "G": ".####/#..../#..../#.###/#...#/#...#/.####",
    "H": "#...#/#...#/#...#/#####/#...#/#...#/#...#",
    "I": "#####/..#../..#../..#../..#../..#../#####",
    "J": "..###/...#./...#./...#./...#./#..#./.##..",
    "K": "#...#/#..#./#.#../##.../#.#../#..#./#...#",
    "L": "#..../#..../#..../#..../#..../#..../#####",
    "M": "#...#/##.##/#.#.#/#.#.#/#...#/#...#/#...#",
    "N": "#...#/##..#/#.#.#/#..##/#...#/#...#/#...#",
    "O": ".###./#...#/#...#/#...#/#...#/#...#/.###.",
    "P": "####./#...#/#...#/####./#..../#..../#....",
    "Q": ".###./#...#/#...#/#...#/#.#.#/#..#./.##.#",
    "R": "####./#...#/#...#/####./#.#../#..#./#...#",
    "S": ".####/#..../#..../.###./....#/....#/####.",
    "T": "#####/..#../..#../..#../..#../..#../..#..",
    "U": "#...#/#...#/#...#/#...#/#...#/#...#/.###.",
    "V": "#...#/#...#/#...#/#...#/#...#/.#.#./..#..",
    "W": "#...#/#...#/#...#/#.#.#/#.#.#/##.##/#...#",
    "X": "#...#/#...#/.#.#./..#../.#.#./#...#/#...#",
    "Y": "#...#/#...#/.#.#./..#../..#../..#../..#..",
    "Z": "#####/....#/...#./..#../.#.../#..../#####",
    "0": ".###./#...#/#..##/#.#.#/##..#/#...#/.###.",
    "1": "..#../.##../..#../..#../..#../..#../.###.",
    "2": ".###./#...#/....#/...#./..#../.#.../#####",
    "3": "####./....#/....#/.###./....#/....#/####.",
    "4": "...#./..##./.#.#./#..#./#####/...#./...#.",
    "5": "#####/#..../####./....#/....#/#...#/.###.",
    "6": ".###./#..../#..../####./#...#/#...#/.###.",
    "7": "#####/....#/...#./..#../.#.../.#.../.#...",
    "8": ".###./#...#/#...#/.###./#...#/#...#/.###.",
    "9": ".###./#...#/#...#/.####/....#/....#/.###.",
    "!": "..#../..#../..#../..#../..#../...../..#..",
    "-": "...../...../...../#####/...../...../.....",
    ".": "...../...../...../...../...../.##../.##..",
    "?": ".###./#...#/....#/...#./..#../...../..#..",
    ":": "...../.##../.##../...../.##../.##../.....",
    "'": "..#../..#../.#.../...../...../...../.....",
    ",": "...../...../...../...../.##../..#../.#...",
    "(": "...#./..#../.#.../.#.../.#.../..#../...#.",
    ")": ".#.../..#../...#./...#./...#./..#../.#...",
    "[": ".###./.#.../.#.../.#.../.#.../.#.../.###.",
    "]": ".###./...#./...#./...#./...#./...#./.###.",
    "+": "...../..#../..#../#####/..#../..#../.....",
    "/": "....#/....#/...#./..#../.#.../#..../#....",
    "|": "..#../..#../..#../..#../..#../..#../..#..",
    "*": "...../#.#.#/.###./#####/.###./#.#.#/.....",
    "=": "...../...../#####/...../#####/...../.....",
    "_": "...../...../...../...../...../...../#####",
    "%": "##..#/##.#./...#./..#../.#.../.#.##/#..##",
    "&": ".##../#..#./#..#./.##../#.#.#/#..#./.##.#",
    "<": "...#./..#../.#.../#..../.#.../..#../...#.",
    ">": ".#.../..#../...#./....#/...#./..#../.#...",
    '"': ".#.#./.#.#./...../...../...../...../.....",
    "#": ".#.#./#####/.#.#./.#.#./.#.#./#####/.#.#.",
    "\u2605": "..#../..#../#####/.###./.#.#./#...#/.....",
}
GLYPHS = {ch: src.split("/") for ch, src in _GLYPH_SRC.items()}
GLYPHS[" "] = ["....."] * 7

# ---------- Pixel UI kit: bitmap text, chunky panels, full-window scenery ----------
PANEL_BG = "#1a1c2c"
PANEL_FG = "#f4f4f4"
PX_ALERT = "#e43b44"
PX_BOTTOM_W, PX_BOTTOM_H = 860, 244  # fixed size of the bottom info panel (2 players)

_IMG_CACHE: dict[tuple, tk.PhotoImage] = {}


def pixel_scale(size):
    """Map a normal font size (points) to a whole-number bitmap-font scale."""
    if size <= 10:
        return 1
    if size <= 20:
        return 2
    return max(2, round(size / 9))


def wrap_text(text, cols):
    out = []
    for para in text.split("\n"):
        out.extend(textwrap.wrap(para, cols) or [""])
    return "\n".join(out)


def bitmap_text_image(text: str, scale: int, fg: str, bg: str, justify: str = "center") -> tk.PhotoImage:
    """Render text with the 5x7 pixel font into a (cached) PhotoImage."""
    key = (text, scale, fg, bg, justify)
    img = _IMG_CACHE.get(key)
    if img is not None:
        return img
    lines = text.split("\n")
    max_chars = max(len(line) for line in lines)
    cw = max(1, max_chars * 6 - 1)
    ch = len(lines) * 9 + 1  # 1 blank margin row above/below, 2 between lines
    rows = [[bg] * cw for _ in range(ch)]
    for li, line in enumerate(lines):
        if justify == "left":
            off = 0
        elif justify == "right":
            off = (max_chars - len(line)) * 6
        else:
            off = (max_chars - len(line)) * 3
        for ci, char in enumerate(line):
            glyph = GLYPHS.get(char.upper(), GLYPHS[" "])
            for r, grow in enumerate(glyph):
                for c, cell in enumerate(grow):
                    if cell == "#":
                        rows[1 + li * 9 + r][off + ci * 6 + c] = fg
    small = tk.PhotoImage(width=cw, height=ch)
    small.put(" ".join("{" + " ".join(r) + "}" for r in rows))
    img = small.zoom(scale, scale) if scale > 1 else small
    if len(_IMG_CACHE) > 800:
        _IMG_CACHE.clear()
    _IMG_CACHE[key] = img
    return img


class TextLabel(tk.Label):
    """A label that draws with the bitmap pixel font in the Pixel theme (normal font otherwise).

    Always update it with .set(...) so both modes stay in sync.
    """

    def __init__(self, parent, text="", size=14, bold=False, fg="#ffffff", bg="#000000",
                 pixel=False, width=0, wraplength=0, justify="center", anchor="center", **kw):
        super().__init__(parent, bd=0, highlightthickness=0, padx=0, pady=0, anchor=anchor, **kw)
        self.pixel = pixel
        self._img: Optional[tk.PhotoImage] = None
        self.opts: dict[str, Any] = dict(text=text, size=size, bold=bold, fg=fg, bg=bg,
                                         width=width, wrap=wraplength, justify=justify)
        self.refresh()

    def set(self, text=None, fg=None, bg=None, size=None, bold=None):
        o = self.opts
        for key, value in (("text", text), ("fg", fg), ("bg", bg), ("size", size), ("bold", bold)):
            if value is not None:
                o[key] = value
        self.refresh()

    def refresh(self):
        o = self.opts
        if self.pixel:
            scale = pixel_scale(o["size"])
            text = o["text"]
            if o["wrap"]:
                text = wrap_text(text, max(4, o["wrap"] // (6 * scale)))
            img = bitmap_text_image(text, scale, o["fg"], o["bg"], o["justify"])
            self._img = img
            width = max(img.width(), o["width"] * 6 * scale) if o["width"] else img.width()
            self.configure(image=img, text="", bg=o["bg"], width=width, height=img.height())
        else:
            self.configure(text=o["text"], bg=o["bg"], fg=o["fg"],
                           font=(FONT, o["size"], "bold" if o["bold"] else "normal"),
                           justify=o["justify"], width=o["width"], wraplength=o["wrap"])


class PixelPanel(tk.Frame):
    """A chunky bordered panel: dark outline, colored edge, content goes in .body"""

    def __init__(self, parent, bg=PANEL_BG, edge=PX_SLATE, outline=PX_DARK, thick=4, inset=3):
        super().__init__(parent, bg=outline)
        self.inner = tk.Frame(self, bg=edge)
        self.inner.pack(fill="both", expand=True, padx=thick, pady=thick)
        self.body = tk.Frame(self.inner, bg=bg)
        self.body.pack(fill="both", expand=True, padx=inset, pady=inset)

    def set_edge(self, color):
        self.inner.configure(bg=color)


ARENA_NAMES = ["Desert", "Snow Town", "Cave", "Space Station"]


def _tone(colors, target, amount):
    return [mix(c, target, amount) for c in colors]


def _style(kind, sky, orb, ground, bits, orb_kind, orb_pos, star="#f4f4f4", stars=0, cloud=None,
           wait_sky=None, go_sky=None, wait_orb=None, go_orb=None) -> dict[str, Any]:
    """Describe one arena. WAIT/GO palettes are derived from the idle one unless given."""
    return dict(
        kind=kind, orb_kind=orb_kind, orb_pos=orb_pos, ground=ground, bits=bits,
        star=star, stars=stars, cloud=cloud,
        sky={"idle": sky,
             "wait": wait_sky or _tone(sky, "#b01f3a", 0.55),
             "go": go_sky or _tone(sky, "#1f9a55", 0.60)},
        orb={"idle": orb,
             "wait": wait_orb or mix(orb, "#e43b44", 0.5),
             "go": go_orb or mix(orb, "#a7f070", 0.5)},
    )


ARENA_STYLES: dict[str, dict[str, Any]] = {
    "Desert": _style(
        "desert", ["#29366f", "#3b5dc9", "#5d275d", "#b13e53", "#ef7d57"], "#ffcd75",
        ("#ffcd75", "#ef7d57", "#b13e53", "#5d275d"), ("#5d275d", "#b13e53", "#ef7d57"),
        "sun", (0.5, "ground", -27), stars=36, cloud=("#ef7d57", "#ffcd75"),
        wait_sky=["#1a1c2c", "#4a1942", "#7a1f3d", "#b13e53", "#e43b44"],
        go_sky=["#0b3d2e", "#115c3b", "#17774a", "#1f8a4c", "#2da158"],
        wait_orb="#ef7d57", go_orb="#f4f4f4"),
    "Snow Town": _style(
        "snow", ["#0b1030", "#16225a", "#2a3a8a", "#4b6cc1", "#9ad0f5"], "#f4f4f4",
        ("#f4f4f4", "#cfe3f5", "#9ac1e5", "#3a4a7a"), ("#9ac1e5", "#566c86", "#f4f4f4"),
        "moon", (0.84, "frac", 0.56), stars=30, cloud=("#3a4a7a", "#566c86")),
    "Cave": _style(
        "cave", ["#0e0f1a", "#161827", "#1f2238", "#2b2f4d", "#3d4570"], "#73eff7",
        ("#94b0c2", "#566c86", "#333c57", "#1a1c2c"), ("#333c57", "#566c86", "#ffcd75"),
        "crystal", (0.5, "ground", 0), star="#566c86", stars=0),
    "Space Station": _style(
        "space", ["#05060f", "#0b0d2a", "#14173f", "#1d2260", "#2a3182"], "#ef7d57",
        ("#94b0c2", "#566c86", "#333c57", "#1a1c2c"), ("#1a1c2c", "#333c57", "#94b0c2"),
        "planet", (0.16, "frac", 0.56), stars=12),
}


class PixelBackdrop:
    """The whole window as a pixel-art scene: sky, sun/moon, scenery, ground and ambient life.

    It is a Canvas; screens pack their panels on top of it, and the duel figures are
    drawn onto it too. The sky palette swaps with the game state (WAIT = red, GO = green),
    and the scenery is chosen with set_arena().
    """

    U = 5

    def __init__(self, parent, arena="Desert"):
        self.canvas = tk.Canvas(parent, highlightthickness=0, bd=0, bg=PX_DARK)
        self.canvas.pack_propagate(False)
        self.width = self.height = 1
        self.ground_fn = lambda width, height: int(height * 0.70)
        self.ground = 300
        self.arena_name = arena if arena in ARENA_STYLES else "Desert"
        self.style = ARENA_STYLES[self.arena_name]
        self.palette = "idle"
        self.cloud_off = 0.0
        self.t0 = time.perf_counter()
        self.anchors: dict[str, list] = {}
        self.pts: dict[str, list] = {}
        self.on_change: Optional[Callable[[], None]] = None
        self.stopped = False
        self.canvas.bind("<Configure>", self._on_configure)
        self.job: Optional[str] = self.canvas.after(60, self.loop)

    # ---------- layout ----------
    def _on_configure(self, event):
        self.width, self.height = event.width, event.height
        self.apply()

    def apply(self):
        """Recompute the ground line from the layout rule and repaint the scenery."""
        if self.width < 100 or self.height < 100:
            return
        self.ground = max(self.U * 10, int(self.ground_fn(self.width, self.height)) // self.U * self.U)
        self.redraw_bg()
        self.draw_clouds()
        self.draw_ambient(time.perf_counter() - self.t0)
        callback = self.on_change
        if callback is not None:
            callback()

    def set_palette(self, name):
        if name != self.palette:
            self.palette = name
            self.redraw_bg()
            self.draw_clouds()

    def set_arena(self, name):
        if name in ARENA_STYLES and name != self.arena_name:
            self.arena_name = name
            self.style = ARENA_STYLES[name]
            self.apply()

    def pal(self) -> dict[str, Any]:
        st, p = self.style, self.palette
        return dict(sky=st["sky"][p], orb=st["orb"][p], star=st["star"], cloud=st["cloud"],
                    ground=st["ground"], bits=st["bits"])

    # ---------- static scenery ----------
    def redraw_bg(self):
        c, unit, width, height, ground = self.canvas, self.U, self.width, self.height, self.ground
        if width < 100 or height < 100:
            return
        pal = self.pal()
        c.delete("bg")

        def b(x, y, w, h, color):
            if w > 0 and h > 0:
                c.create_rectangle(int(x), int(y), int(x + w), int(y + h),
                                   fill=color, outline="", tags="bg")

        fractions = (0.0, 0.22, 0.44, 0.60, 0.78)
        ys = [int(ground * f) // unit * unit for f in fractions] + [ground]
        for k, col in enumerate(pal["sky"]):
            b(0, ys[k], width, ys[k + 1] - ys[k], col)

        rnd = random.Random(11)
        count = self.style["stars"]
        for _ in range(max(0, width // count) if count else 0):  # fixed stars
            b(rnd.randrange(0, width) // unit * unit, rnd.randrange(0, max(unit, ys[3])) // unit * unit, unit, unit,
              pal["star"])
        # points the ambient animation uses (twinkle, snow, fireflies)
        self.pts["twinkle"] = [
            (rnd.randrange(0, width) // unit * unit, rnd.randrange(unit, max(2 * unit, ys[3])) // unit * unit)
            for _ in range(18)]
        self.pts["snow"] = [(rnd.uniform(0, width), rnd.uniform(0, ground), rnd.uniform(25, 70),
                             rnd.uniform(6, 16), rnd.choice((3, 3, 5))) for _ in range(70)]
        self.pts["fly"] = [(rnd.uniform(0.05, 0.95) * width, rnd.uniform(0.35, 0.9) * ground) for _ in range(14)]
        self.anchors = {}

        self.draw_orb(b, pal)
        getattr(self, "_scenery_" + self.style["kind"])(b, pal, rnd)

        edge, b1, b2, deep = pal["ground"]  # ground
        b(0, ground, width, 2 * unit, edge)
        b(0, ground + 2 * unit, width, 3 * unit, b1)
        b(0, ground + 5 * unit, width, 8 * unit, b2)
        b(0, ground + 13 * unit, width, height - ground - 13 * unit, deep)
        bits = pal["bits"]
        for _ in range(max(10, width * max(0, height - ground) // 22000)):  # pebbles / ice / ore bits
            px = rnd.randrange(0, max(1, width - 2 * unit)) // unit * unit
            py = rnd.randrange(ground + 3 * unit, max(ground + 4 * unit, height - unit)) // unit * unit
            b(px, py, 2 * unit, unit, bits[0] if py < ground + 13 * unit else bits[1])
            b(px + unit, py - unit, unit, unit, bits[2])
        c.tag_lower("bg")

    def draw_orb(self, b, pal):
        unit, width, ground = self.U, self.width, self.ground
        kind = self.style["orb_kind"]
        fx, mode, val = self.style["orb_pos"]
        ox = int(width * fx)
        oy = ground + val if mode == "ground" else int(ground * val)
        col = pal["orb"]
        if kind in ("sun", "moon", "planet"):
            r = {"sun": 50, "moon": 36, "planet": 42}[kind]
            for dy in range(-r, r, unit):
                span = r * r - (dy + unit / 2) ** 2
                half = int(span ** 0.5 // unit * unit) if span > 0 else 0
                if half > 0 and oy + dy + unit <= ground:
                    b(ox - half, oy + dy, half * 2, unit, col)
            if kind == "moon":  # craters
                dark = mix(col, "#000000", 0.18)
                b(ox - 15, oy - 10, 10, 10, dark)
                b(ox + 5, oy + 5, 10, 10, dark)
                b(ox - 5, oy + 15, 5, 5, dark)
            if kind == "planet":  # ring + stripes
                ring = mix(col, "#f4f4f4", 0.45)
                b(ox - r - 30, oy + unit, 2 * r + 60, unit, ring)
                b(ox - r - 20, oy + 2 * unit, 2 * r + 40, unit, mix(ring, "#000000", 0.2))
                b(ox - 20, oy - 15, 40, unit, mix(col, "#000000", 0.2))
        elif kind == "crystal":  # glowing crystal cluster
            def crystal(cx, k):
                rows = 2 * k + 1
                for i in range(rows):
                    w = (min(i, rows - 1 - i) + 1) * unit
                    b(cx - w // 2, ground - (rows - i) * unit, w, unit, col)
                b(cx - unit, ground - (rows - 1) * unit + unit, unit, unit, "#f4f4f4")

            crystal(ox, 5)
            crystal(ox - 7 * unit, 3)
            crystal(ox + 8 * unit, 4)

    def _scenery_desert(self, b, _pal, _rnd):
        unit, width, ground = self.U, self.width, self.ground

        def mesa(cx, tiers, color):
            y = ground
            for w, h in tiers:
                b(cx - w // 2, y - h, w, h, color)
                y -= h

        mesa(int(width * 0.13), [(130, 24), (90, 24)], "#333c57")
        mesa(int(width * 0.87), [(150, 24), (100, 20), (60, 18)], "#333c57")
        mesa(width // 2, [(110, 15)], PX_PURPLE)

        def cactus(x, h):
            b(x - unit, ground - h * unit, 2 * unit, h * unit, PX_GREEN)
            b(x - unit, ground - h * unit, 2 * unit, unit, PX_LIME)
            ay = ground - (h - 6) * unit
            b(x - 3 * unit, ay - 3 * unit, 2 * unit, 4 * unit, PX_GREEN)
            b(x + unit, ay - 5 * unit, 2 * unit, 5 * unit, PX_GREEN)

        cactus(int(width * 0.045), 11)
        cactus(int(width * 0.955), 9)

    def _scenery_snow(self, b, pal, rnd):
        unit, width, ground = self.U, self.width, self.ground
        hill = mix(pal["sky"][4], "#f4f4f4", 0.35)
        x = 0
        while x < width:  # snowy hills
            w, h = rnd.randrange(8, 16) * unit, rnd.randrange(3, 8) * unit
            b(x, ground - h, w, h, hill)
            b(x + unit, ground - h - unit, w - 2 * unit, unit, hill)
            x += w - unit

        def pine(x, tiers):
            b(x - unit, ground - 2 * unit, 2 * unit, 2 * unit, HOLSTER)
            for i in range(tiers):
                w = (9 - 2 * i) * unit
                y = ground - 2 * unit - (i + 1) * 3 * unit
                b(x - w // 2, y, w, 3 * unit, "#14523a" if i % 2 else "#1f8a4c")
                b(x - w // 2 + unit, y, w - 2 * unit, unit, "#f4f4f4")

        for fx, tiers in ((0.04, 4), (0.09, 3), (0.30, 3), (0.70, 3), (0.93, 3), (0.97, 4)):
            pine(int(width * fx), tiers)

        def cabin(x):
            b(x - 8 * unit, ground - 9 * unit, 16 * unit, 9 * unit, HOLSTER)
            b(x - 10 * unit, ground - 10 * unit, 20 * unit, unit, PX_PURPLE)
            for k, w in enumerate((20, 16, 12)):
                b(x - w * unit // 2, ground - (11 + k) * unit, w * unit, unit, "#f4f4f4")
            b(x - unit, ground - 5 * unit, 2 * unit, 5 * unit, "#3b2a1a")
            b(x + 3 * unit, ground - 7 * unit, 3 * unit, 3 * unit, PX_YELLOW)
            b(x + 4 * unit, ground - 14 * unit, 2 * unit, 3 * unit, PX_SLATE)

        self.anchors["cabins"] = [int(width * 0.15), int(width * 0.86)]
        for cx in self.anchors["cabins"]:
            cabin(cx)

    def _scenery_cave(self, b, pal, rnd):
        unit, width, ground = self.U, self.width, self.ground
        stone = mix(pal["sky"][2], "#ffffff", 0.07)
        for _ in range(140):  # rock texture
            b(rnd.randrange(0, width) // unit * unit, rnd.randrange(0, max(unit, ground - 6 * unit)) // unit * unit,
              rnd.choice((2, 3, 4)) * unit, unit, stone)
        for _ in range(16):  # ores in the wall
            ox = rnd.randrange(0, width) // unit * unit
            oy = rnd.randrange(int(ground * 0.3), max(int(ground * 0.3) + unit, ground - 8 * unit)) // unit * unit
            col = rnd.choice((PX_YELLOW, "#73eff7", "#e43b44"))
            b(ox, oy, 2 * unit, 2 * unit, col)
            b(ox + unit, oy + unit, unit, unit, mix(col, "#ffffff", 0.5))
        for _ in range(12):  # stalactites
            sx = rnd.randrange(0, width) // unit * unit
            for i in range(rnd.randrange(3, 7)):
                w = max(1, 8 - 2 * i) * unit
                b(sx - w // 2, i * 2 * unit, w, 2 * unit, mix(pal["sky"][3], "#ffffff", 0.05))
        for fx in (0.05, 0.12, 0.88, 0.95):  # stalagmites
            sx = int(width * fx)
            for i in range(rnd.randrange(3, 5)):
                w = max(1, 7 - 2 * i) * unit
                b(sx - w // 2, ground - (i + 1) * 2 * unit, w, 2 * unit, mix(pal["sky"][4], "#ffffff", 0.08))
        self.anchors["torches"] = [(int(width * 0.10), ground - 18 * unit), (int(width * 0.90), ground - 18 * unit)]
        for tx, ty in self.anchors["torches"]:  # torch holders
            b(tx - unit, ty, 2 * unit, 6 * unit, HOLSTER)
            b(tx - 2 * unit, ty + 4 * unit, 4 * unit, unit, PX_SLATE)

    def _scenery_space(self, b, _pal, rnd):
        unit, width, ground = self.U, self.width, self.ground

        def dome(cx, r):
            for i in range(r):
                w = int((r * r - (r - 1 - i) ** 2) ** 0.5 * 2) * unit // 2
                b(cx - w, ground - (r - i) * unit, w * 2, unit, "#333c57")
            for _ in range(5):
                b(cx + rnd.randrange(-r * unit // 2, r * unit // 2) // unit * unit, ground - rnd.randrange(1, r) * unit,
                  unit, unit, PX_YELLOW)

        dome(int(width * 0.12), 9)
        dome(int(width * 0.90), 7)

        def mast(x, h):
            b(x - unit // 2, ground - h * unit, unit, h * unit, PX_SLATE)
            b(x - 3 * unit, ground - h * unit + 2 * unit, 6 * unit, unit, PX_GREY)

        mast(int(width * 0.33), 12)
        mast(int(width * 0.70), 10)
        self.anchors["masts"] = [(int(width * 0.33), ground - 12 * unit), (int(width * 0.70), ground - 10 * unit)]
        for fx in (0.45, 0.58):  # solar panels
            x = int(width * fx)
            b(x, ground - 5 * unit, 10 * unit, 3 * unit, PX_BLUE)
            for k in range(1, 5):
                b(x + k * 2 * unit, ground - 5 * unit, unit // 2 + 1, 3 * unit, PX_DARK)

    # ---------- clouds + ambient life ----------
    def draw_clouds(self):
        c, unit = self.canvas, self.U
        if self.width < 100:
            return
        c.delete("cloud")
        cl = self.style["cloud"]
        if cl:
            if self.palette == "wait":
                cl = (mix(cl[0], "#b01f3a", 0.5), mix(cl[1], "#b01f3a", 0.5))
            elif self.palette == "go":
                cl = (mix(cl[0], "#1f9a55", 0.5), mix(cl[1], "#a7f070", 0.4))
            for fx, fy, sc in ((0.10, 0.52, 1.0), (0.55, 0.60, 1.3), (0.88, 0.46, 0.9)):
                x = (fx * self.width + self.cloud_off) % (self.width + 160) - 80
                y = int(self.ground * fy) // unit * unit
                w = int(unit * 8 * sc)
                for rx, ry, rw, col in ((0, unit, w, cl[0]), (unit, 0, w - 2 * unit, cl[0]),
                                        (2 * unit, -unit, w // 2, cl[1])):
                    c.create_rectangle(int(x + rx), int(y + ry), int(x + rx + rw), int(y + ry + unit),
                                       fill=col, outline="", tags="cloud")
        c.tag_lower("cloud")
        c.tag_lower("bg")

    def draw_ambient(self, t):
        c = self.canvas
        c.delete("amb")
        if self.width < 100 or not self.pts:
            return
        pal = self.pal()

        def r(x, y, w, h, col):
            c.create_rectangle(int(x), int(y), int(x + w), int(y + h), fill=col,
                               outline="", tags="amb")

        for k, (x, y) in enumerate(self.pts["twinkle"]):  # twinkling stars (all arenas)
            if self.style["kind"] != "cave" and math.sin(t * 1.7 + k * 1.3) > 0.55:
                r(x, y, self.U, self.U, "#ffffff")
        getattr(self, "_amb_" + self.style["kind"])(t, r, pal)
        c.tag_lower("amb")
        c.tag_lower("cloud")
        c.tag_lower("bg")

    @staticmethod
    def _bird(r, x, y, frame, col, s=3):
        """A flapping silhouette bird (vulture / bat), two animation frames."""
        up = ((-3, -1), (-2, 0), (-1, 1), (0, 1), (1, 1), (2, 0), (3, -1))
        down = ((-3, 1), (-2, 0), (-1, -1), (0, -1), (1, -1), (2, 0), (3, 1))
        for dx, dy in (up if frame == 0 else down):
            r(x + dx * s, y + dy * s, s, s, col)

    def _amb_desert(self, t, r, _pal):
        width, ground = self.width, self.ground
        for i in range(3):  # circling vultures
            direction = 1 if i % 2 == 0 else -1
            x = (i * 410 + direction * (16 + 7 * i) * t) % (width + 200) - 100
            y = ground * (0.50 + 0.06 * i) + 14 * math.sin(t * 0.8 + i * 2)
            self._bird(r, x, y, int(t * 3 + i) % 2, "#1a1c2c", 4)
        ph = (t % 26) / 9.0  # tumbleweed rolls by
        if ph < 1:
            x = -40 + (width + 80) * ph
            y = ground - 14 - abs(math.sin(t * 7)) * 12
            for dy in range(-4, 5):
                half = int(math.sqrt(16 - dy * dy))
                if half:
                    r(x - half * 3, y + dy * 3, half * 6, 3, "#c9a060")
            if int(t * 7) % 2 == 0:
                r(x - 12, y - 1, 24, 3, HOLSTER)
            else:
                r(x - 1, y - 12, 3, 24, HOLSTER)

    def _amb_snow(self, t, r, pal):
        unit, width, ground = self.U, self.width, self.ground
        for k, (x0, y0, sp, amp, sz) in enumerate(self.pts["snow"]):  # snowfall
            r((x0 + amp * math.sin(t * 0.9 + k)) % width, (y0 + sp * t) % ground, sz, sz, "#f4f4f4")
        for k in range(2):  # northern lights
            colr = ("#73eff7", "#a7f070")[k]
            for x in range(0, width, 16):
                y = ground * 0.12 + 16 * math.sin(x * 0.010 + t * 0.5 + k * 2.1) + k * 22
                r(x, y, 16, 3 * unit + 4 * math.sin(x * 0.02 + t), colr)
        for idx, cx in enumerate(self.anchors.get("cabins", [])):  # smoke + glowing windows
            r(cx + 3 * unit, ground - 7 * unit, 3 * unit, 3 * unit, PX_YELLOW if int(t * 2 + idx) % 3 else PX_ORANGE)
            for j in range(4):
                age = (t * 0.5 + j * 0.25 + idx * 0.13) % 1
                r(cx + 5 * unit + math.sin(age * 6 + j) * 6 + age * 14, ground - 14 * unit - age * 70,
                  unit * (1 + age), unit * (1 + age), mix("#f4f4f4", pal["sky"][4], age * 0.7))

    def _amb_cave(self, t, r, _pal):
        unit, width, ground = self.U, self.width, self.ground
        for tx, ty in self.anchors.get("torches", []):  # flickering torches + embers
            flick = int(1.5 + 1.5 * math.sin(t * 11 + tx))
            r(tx - 2 * unit, ty - (5 + flick) * unit, 4 * unit, (5 + flick) * unit, PX_ORANGE)
            r(tx - unit, ty - (4 + flick) * unit, 2 * unit, (4 + flick) * unit, PX_YELLOW)
            r(tx - unit // 2, ty - 2 * unit, unit, unit, "#ffffff")
            for j in range(4):
                age = (t * 0.8 + j * 0.27) % 1
                r(tx + math.sin(j * 3 + age * 5) * 12, ty - (6 + age * 14) * unit,
                  unit // 2 * 2, unit // 2 * 2, PX_YELLOW if age < 0.5 else PX_ORANGE)
        for i in range(3):  # bats
            direction = 1 if i % 2 == 0 else -1
            x = (i * 380 + direction * 45 * t) % (width + 160) - 80
            y = ground * 0.50 + 40 * math.sin(t * 1.6 + i * 2)
            self._bird(r, x, y, int(t * 6 + i) % 2, "#0e0f1a", 3)
            r(x - 3, y + 1, 3, 3, "#e43b44")
        for k, (x, y) in enumerate(self.pts["fly"]):  # glow-worms
            if math.sin(t * 1.5 + k * 2) > -0.2:
                r(x + 30 * math.sin(t * 0.5 + k), y + 20 * math.cos(t * 0.7 + k * 1.3), 4, 4,
                  "#a7f070" if k % 2 else "#73eff7")

    def _amb_space(self, t, r, pal):
        unit, width, ground = self.U, self.width, self.ground
        ph = (t % 7.5) / 0.9  # shooting star
        if ph < 1:
            hx, hy = width * 0.92 - ph * width * 0.45, ground * 0.22 + ph * ground * 0.28
            for k in range(8):
                r(hx + k * 11, hy - k * 5.5, unit - k // 2, unit - k // 2,
                  mix("#ffffff", pal["sky"][3], k / 8.0))
        ph = (t % 30) / 16.0  # a UFO drifts by
        if ph < 1:
            x = -60 + (width + 120) * ph
            y = ground * 0.46 + 12 * math.sin(t * 2)
            r(x - 2 * unit, y - 3 * unit, 4 * unit, unit, "#73eff7")
            r(x - 5 * unit, y - 2 * unit, 10 * unit, 2 * unit, PX_GREY)
            r(x - 3 * unit, y, 6 * unit, unit, PX_SLATE)
            for i in range(3):
                if (int(t * 4) + i) % 3:
                    r(x - 4 * unit + i * 4 * unit, y - 2 * unit + unit // 2, unit, unit, PX_YELLOW)
        for i in range(int(width // (14 * unit)) + 1):  # blinking deck lights
            if (i + int(t * 2)) % 3 == 0:
                r(i * 14 * unit + 3 * unit, ground - unit, unit, unit, PX_YELLOW)
        for mx, my in self.anchors.get("masts", []):
            if int(t * 1.5) % 2 == 0:
                r(mx - unit // 2, my - 2 * unit, unit, unit, "#e43b44")

    def loop(self):
        self.job = None
        if self.stopped:
            return
        self.cloud_off += 0.6
        try:
            self.draw_clouds()
            self.draw_ambient(time.perf_counter() - self.t0)
            self.job = self.canvas.after(60, self.loop)
        except tk.TclError:
            self.job = None

    def stop(self):
        self.stopped = True
        if self.job is not None:
            try:
                self.canvas.after_cancel(self.job)
            except tk.TclError:
                pass
            self.job = None


def ease(x):
    """Ease-out curve: fast start, soft landing (0..1 in, 0..1 out)."""
    x = clamp(x, 0.0, 1.0)
    return 1 - (1 - x) ** 3


class DuelArena:
    """A little western duel painted entirely out of rectangles.

    Everything is a pure function of 'animation time' t, so the showdown can be
    slowed down, frozen for hit-stop, or skipped without any special cases.
    """

    U = 5  # the size of one "pixel"
    GROUND = 0  # the scene uses LOCAL coordinates: (0, 0) is the point
    FIG_X = (-230, 230)  # on the ground under the middle of the window
    FACING = (1, -1)  # +1 = faces right, -1 = faces left
    MUZZLE = (14, -15)  # gun muzzle offset in pixels (x forward, y up)
    TORSO_FRONT = 5  # how far in front of center bullets hit
    BULLET_V = 0.30  # px per animation-ms (the "slow-mo" speed)
    KNOCK = 30  # px the loser is knocked back
    FREEZE_MS = 190  # hit-stop length

    def __init__(self, backdrop, outfits, sfx=None, shake=None):
        self.bd = backdrop  # the full-window PixelBackdrop we draw onto
        self.canvas = backdrop.canvas
        self.outfits = outfits  # [{hat, color, face}, {hat, color, face}]
        self.sfx = sfx or (lambda name: None)
        self.shake = shake or (lambda strength, steps: None)
        self.mode = "static"  # static | duel | void | stopped
        self.plan: dict[str, Any] = {}
        self.plan_key = None
        self.text = None  # (text, color, scale, top)
        self.banner = None  # e.g. "MATCH POINT!" (flashes above the scene)
        self.tr: dict[str, Any] = {}  # trainer-scene state
        self.t = 0.0
        self.speed = 1.0
        self.freeze = 0.0
        self.flash_left = 0.0
        self.hit_done = False
        self.ev_i = 0
        self.done_cb: Optional[Callable[[], None]] = None
        self.last = time.perf_counter()
        self.job: Optional[str] = None
        backdrop.on_change = self.redraw
        self.redraw()
        self.job = self.canvas.after(100, self.loop)

    @property
    def cx(self):
        return self.bd.width // 2

    @property
    def gy(self):
        return self.bd.ground

    # ---------- low-level drawing ----------
    def rect(self, x, y, w, h, color):
        """Draw a rectangle given in scene-local coordinates."""
        ox, oy = self.cx, self.gy
        self.canvas.create_rectangle(int(ox + x), int(oy + y), int(ox + x + w), int(oy + y + h),
                                     fill=color, outline="", tags="dyn")

    def draw_text(self, text, cx, cy, scale, color, shadow=True):
        total = len(text) * 6 * scale - scale
        left = int(cx - total / 2)
        top = int(cy - 7 * scale / 2)
        passes = ((scale, scale, PX_DARK), (0, 0, color)) if shadow else ((0, 0, color),)
        for dx, dy, col in passes:
            x = left
            for ch in text.upper():
                glyph = GLYPHS.get(ch, GLYPHS[" "])
                for r, row in enumerate(glyph):
                    start = None
                    for k, cell in enumerate(row + "."):
                        if cell == "#" and start is None:
                            start = k
                        elif cell != "#" and start is not None:
                            self.rect(x + start * scale + dx, top + r * scale + dy,
                                      (k - start) * scale, scale, col)
                            start = None
                x += 6 * scale

    # ---------- sprites ----------
    def parts_for(self, idx, pose, hat_on=True, closed_eyes=False):
        """Rectangles (x, y_top, w, h, color) in pixel units; feet at (0, 0), facing +x."""
        o = self.outfits[idx]
        col, hat_style, face = o["color"], o.get("hat", "Cowboy"), o.get("face", "None")
        vest = mix(col, PX_DARK, 0.30)
        parts = []
        add = lambda x, y, w, h, c: parts.append((x, y, w, h, c))

        if pose == "hit":  # arms flung up
            add(-6, -21, 2, 6, vest);
            add(-6, -23, 2, 2, SKIN)
        else:
            add(-6, -15, 2, 6, vest);
            add(-6, -9, 2, 2, SKIN)
        add(-3, -9, 3, 7, PX_BLUE);
        add(1, -9, 3, 7, PX_BLUE)  # legs
        add(-4, -2, 4, 2, BOOT);
        add(1, -2, 5, 2, BOOT)  # boots
        add(-4, -16, 8, 7, vest);
        add(-1, -16, 2, 7, PX_WHITE)  # torso + shirt
        add(-4, -10, 8, 1, BOOT);
        add(0, -10, 1, 1, PX_YELLOW)  # belt + buckle
        if pose in ("ready", "aim", "aim_up"):
            add(2, -10, 3, 3, HOLSTER)
            if pose == "ready":
                add(3, -11, 2, 1, PX_GREY)
        add(-3, -20, 6, 3, SKIN)  # head
        if closed_eyes:
            add(0, -19, 3, 1, PX_DARK)
        else:
            add(1, -19, 1, 1, PX_DARK)
        if face == "Mustache":
            add(0, -18, 3, 1, BOOT)
        elif face == "Shades":
            add(-1, -19, 4, 1, PX_DARK)
        elif face == "Eyepatch":
            add(0, -19, 2, 2, PX_DARK);
            add(-3, -20, 3, 1, PX_DARK)
        add(-3, -17, 6, 1, PX_RED)  # neckerchief
        if hat_style == "Bandana" or hat_on:  # a bandana never flies off
            for part in self.hat_parts(hat_style, col):
                add(*part)

        if pose == "ready":
            add(4, -15, 2, 5, vest);
            add(4, -10, 2, 2, SKIN)
        elif pose == "aim":
            add(4, -15, 3, 2, vest);
            add(7, -15, 2, 2, SKIN)
            add(9, -16, 5, 2, PX_GREY);
            add(9, -14, 2, 2, PX_SLATE)
        elif pose == "aim_up":
            add(5, -21, 2, 6, vest);
            add(5, -23, 2, 2, SKIN)
            add(5, -28, 2, 5, PX_GREY);
            add(7, -25, 2, 2, PX_SLATE)
        elif pose == "hit":
            add(4, -21, 2, 6, vest);
            add(4, -23, 2, 2, SKIN)
        return parts

    @staticmethod
    def hat_parts(style, col):
        """Hat rectangles in the figure's own coordinates (the head top is at y = -20)."""
        hat_d = mix(col, PX_DARK, 0.45)
        if style == "Sombrero":
            return [(-9, -21, 18, 1, hat_d), (-7, -22, 14, 1, col), (-3, -25, 6, 3, col),
                    (-1, -26, 2, 1, col), (-3, -22, 6, 1, PX_YELLOW)]
        if style == "Top Hat":
            dark = mix(col, PX_DARK, 0.75)
            return [(-5, -21, 10, 1, dark), (-3, -28, 6, 7, dark), (-3, -23, 6, 1, col)]
        if style == "Cap":
            return [(-3, -23, 6, 3, col), (2, -21, 6, 1, hat_d)]
        if style == "Bandana":
            return [(-3, -20, 6, 1, col), (-5, -20, 2, 3, col)]
        return [(-6, -21, 12, 1, hat_d), (-3, -24, 6, 3, col), (-3, -22, 6, 1, hat_d)]  # Cowboy

    def hat_sprite(self, idx):
        """The hat alone, with its bottom edge at y = 0 (used when it flies off)."""
        o = self.outfits[idx]
        if o.get("hat") == "Bandana":
            return []
        parts = self.hat_parts(o.get("hat", "Cowboy"), o["color"])
        bottom = max(y + h for _x, y, _w, h, _c in parts)
        return [(x, y - bottom, w, h, c) for x, y, w, h, c in parts]

    @staticmethod
    def apply_lean(parts, lean):
        """Shear the figure backwards: the higher the part, the further it leans."""
        out = []
        for x, y, w, h, c in parts:
            height = -(y + h / 2.0)
            out.append((x + round(lean * height / 24.0), y, w, h, c))
        return out

    @staticmethod
    def rotate_down(parts):
        """Lay the figure flat, head pointing backwards (-x), feet on the ground."""
        out = [(y, -(x + w), h, w, c) for x, y, w, h, c in parts]
        bottom = max(py + ph for _x, py, _w, ph, _c in out)
        return [(px, py - bottom, pw, ph, c) for px, py, pw, ph, c in out]

    def draw_figure(self, parts, ox, oy, facing, flash=False):
        unit = self.U

        def pr(x, y, w, h, color):
            if facing < 0:
                x = -(x + w)
            self.rect(ox + x * unit, oy + y * unit, w * unit, h * unit, color)

        for x, y, w, h, _c in parts:
            pr(x - 1, y - 1, w + 2, h + 2, PX_DARK)
        for x, y, w, h, c in parts:
            pr(x, y, w, h, "#ffffff" if flash else c)

    # ---------- effects ----------
    def draw_star(self, cx, cy, r):
        unit = self.U
        r = max(unit, int(r))
        self.rect(cx - 2 * r, cy - unit / 2, 4 * r, unit, PX_YELLOW)
        self.rect(cx - unit / 2, cy - 2 * r, unit, 4 * r, PX_YELLOW)
        d = int(r * 1.3)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.rect(cx + sx * d - unit * 0.75, cy + sy * d - unit * 0.75, unit * 1.5, unit * 1.5, PX_ORANGE)
        self.rect(cx - r, cy - r, 2 * r, 2 * r, PX_WHITE)

    def draw_bullet(self, bx, by, f, vertical=False):
        unit = self.U
        if vertical:
            for k, col in enumerate((PX_YELLOW, PX_ORANGE, PX_RED)):
                self.rect(bx - (unit - 1 - k) / 2, by + 1.5 * unit + k * 3 * unit, unit - 1 - k, 3 * unit, col)
            self.rect(bx - unit / 2, by - 1.5 * unit, unit, 3 * unit, PX_WHITE)
            return
        for k, col in enumerate((PX_YELLOW, PX_ORANGE, PX_RED)):
            h = unit - 1 - k
            if f > 0:
                x0 = bx - 1.5 * unit - (k + 1) * 3 * unit
            else:
                x0 = bx + 1.5 * unit + k * 3 * unit
            self.rect(x0, by - h / 2, 3 * unit, h, col)
        self.rect(bx - 1.5 * unit, by - unit / 2, 3 * unit, unit, PX_WHITE)

    def draw_tumbleweed(self, t):
        s = 3
        cx = -self.cx - 40 + (self.bd.width + 80) * (t / 2800.0)
        cy = self.GROUND - 22 - abs(math.sin(t / 160.0)) * 14
        for dy in range(-6, 7):
            half = int(math.sqrt(36 - dy * dy))
            if half:
                self.rect(cx - half * s, cy + dy * s, half * 2 * s, s, "#c9a060")
        dark = HOLSTER
        if int(t / 140) % 2 == 0:
            self.rect(cx - 6 * s, cy - s / 2, 12 * s, s, dark)
            self.rect(cx - s / 2, cy - 6 * s, s, 12 * s, dark)
        else:
            for k in (-4, -2, 0, 2, 4):
                self.rect(cx + k * s - s / 2, cy + k * s - s / 2, s, s, dark)
                self.rect(cx + k * s - s / 2, cy - k * s - s / 2, s, s, dark)

    # ---------- the showdown "script" ----------
    def make_plan(self, winner, loser, delta_ms, early):
        """Plan a duel in animation-ms. W = winner, L = loser."""
        unit, ground = self.U, self.GROUND
        mx = [self.FIG_X[i] + self.FACING[i] * self.MUZZLE[0] * unit for i in (0, 1)]
        my = ground + self.MUZZLE[1] * unit
        hit_x = self.FIG_X[loser] + self.FACING[loser] * self.TORSO_FRONT * unit
        flight = abs(hit_x - mx[winner]) / self.BULLET_V
        fire = {winner: 1500.0 if early else 500.0}
        up = None
        if early:  # false starter fires at the sky
            up = {"i": loser, "t": 350.0}
        elif delta_ms is not None:  # loser pulled the trigger too, just later
            gap = clamp(250.0 + delta_ms * 5.0, 250.0, 0.85 * flight)
            fire[loser] = fire[winner] + gap
        hit_t = fire[winner] + flight
        events = [(ft, "go") for ft in fire.values()]
        if up:
            events.append((up["t"], "go"))
        plan = dict(W=winner, L=loser, fire=fire, up=up, mx=mx, my=my, hit_x=hit_x,
                    flight=flight, hit_t=hit_t, end_t=hit_t + 1700.0,
                    events=sorted(events))
        plan["particles"] = self.build_particles(plan)
        return plan

    def up_muzzle(self, plan):
        i = plan["up"]["i"]
        return (self.FIG_X[i] + self.FACING[i] * 6 * self.U, self.GROUND - 28 * self.U)

    def build_particles(self, plan):
        unit, ground = self.U, self.GROUND
        winner, loser = plan["W"], plan["L"]
        rnd = random.random
        particles = []

        def smoke(x, y, t0, f):
            for k in range(6):
                particles.append(dict(t0=t0 + k * 70, x=x, y=y, vx=f * (0.005 + rnd() * 0.025),
                                      vy=-(0.02 + rnd() * 0.03), g=0.0, life=1800.0, s0=unit * 1.2,
                                      s1=unit * 3.0, color=random.choice((PX_GREY, PX_WHITE, PX_SLATE)),
                                      kind="smoke"))

        for i, ft in plan["fire"].items():
            smoke(plan["mx"][i], plan["my"], ft, self.FACING[i])
        if plan["up"]:
            ux, uy = self.up_muzzle(plan)
            smoke(ux, uy, plan["up"]["t"], 0)

        d = self.FACING[winner]
        for _ in range(24):  # impact sparks
            back = -d if rnd() < 0.8 else d
            particles.append(dict(t0=plan["hit_t"], x=plan["hit_x"], y=plan["my"],
                                  vx=back * (0.1 + rnd() * 0.7), vy=-(0.1 + rnd() * 0.7), g=0.0016,
                                  life=600 + rnd() * 300,
                                  s0=random.choice((unit, unit, unit * 0.6, unit * 1.4)), s1=unit * 0.4,
                                  color=random.choice((PX_YELLOW, PX_WHITE, PX_ORANGE, PX_YELLOW)),
                                  kind="spark"))
        if loser in plan["fire"]:  # the loser's bullet fizzles out
            bx = plan["mx"][loser] + self.FACING[loser] * self.BULLET_V * (plan["hit_t"] - plan["fire"][loser])
            for _ in range(8):
                particles.append(dict(t0=plan["hit_t"], x=bx, y=plan["my"], vx=(rnd() - 0.5) * 0.4,
                                      vy=-rnd() * 0.3, g=0.001, life=420, s0=unit * 0.8, s1=unit * 0.3,
                                      color=random.choice((PX_YELLOW, PX_GREY)), kind="spark"))
        origin = self.FIG_X[loser] - self.FACING[loser] * self.KNOCK
        for _ in range(12):  # dust when the loser hits the ground
            particles.append(dict(t0=plan["hit_t"] + 320, x=origin - self.FACING[loser] * rnd() * 70,
                                  y=ground - unit, vx=(rnd() - 0.5) * 0.35, vy=-(0.03 + rnd() * 0.09),
                                  g=0.0003, life=520, s0=unit * 1.6, s1=unit * 0.5,
                                  color=random.choice((PX_YELLOW, PX_ORANGE)), kind="dust"))
        return particles

    def hat_state(self, loser, age):
        """Where the loser's flying hat is, `age` ms after the hit."""
        if age < 0:
            return None
        unit, ground = self.U, self.GROUND
        f = self.FACING[loser]
        x0, y0 = self.FIG_X[loser] - f * 3 * unit, ground - 20 * unit
        vx, vy, g = -f * 0.13, -0.50, 0.0016
        a1 = (-vy + math.sqrt(vy * vy - 2 * g * (y0 - ground))) / g  # first landing
        vb = -0.30 * (vy + g * a1)  # one small bounce
        a2 = 2 * abs(vb) / g
        if age <= a1:
            return x0 + vx * age, y0 + vy * age + 0.5 * g * age * age
        if age <= a1 + a2:
            b = age - a1
            return x0 + vx * age, ground + vb * b + 0.5 * g * b * b
        return x0 + vx * (a1 + a2), ground

    def draw_plan(self, t, animated):
        p = self.plan
        unit, ground = self.U, self.GROUND
        winner, loser = p["W"], p["L"]
        post = t - p["hit_t"]

        for i in (0, 1):
            f, fx = self.FACING[i], self.FIG_X[i]
            ox: float = fx
            oy: float = ground
            pose, hat_on, flash, lean, lying = "ready", True, False, 0, False
            ft = p["fire"].get(i)
            up = p["up"]
            if i == loser and post >= 0:
                hat_on = False
                lean = -2 - 6 * ease(min(post, 300.0) / 300.0)
                ox = fx - f * self.KNOCK * ease(min(post, 500.0) / 500.0)
                flash = post < 140
                if post < 320:
                    pose = "hit"
                else:
                    lying = True
                    b = post - 320
                    if b < 300:
                        oy = ground - unit * 2 * abs(math.sin(math.pi * b / 300.0))
            else:
                if up and up["i"] == i and t >= up["t"] - 150:
                    pose = "aim_up"
                elif ft is not None and t >= ft - 150:
                    pose = "aim"
                if ft is not None and 0 <= t - ft < 160:  # recoil kick
                    ox = fx - f * 2 * unit * (1 - (t - ft) / 160.0)
                if i == winner and 650 <= post < 1100:  # victory hop
                    oy = ground - 3 * unit * math.sin(math.pi * (post - 650) / 450.0)
            parts = self.parts_for(i, pose, hat_on, closed_eyes=(i == loser and post >= 0))
            if lying:
                parts = self.rotate_down(parts)
            elif lean:
                parts = self.apply_lean(parts, lean)
            if not lying:
                self.rect(ox - 6 * unit, ground, 12 * unit, unit, PX_PURPLE)  # shadow
            self.draw_figure(parts, ox, oy, f, flash)

        if post >= 0:  # the flying hat
            pos = self.hat_state(loser, post)
            sprite = self.hat_sprite(loser)
            if sprite and pos is not None:
                self.draw_figure(sprite, pos[0], pos[1], 1)

        if not animated:
            return

        for q in p["particles"]:  # sparks, smoke, dust
            age = t - q["t0"]
            if 0 <= age < q["life"]:
                k = age / q["life"]
                size = q["s0"] + (q["s1"] - q["s0"]) * k
                x = q["x"] + q["vx"] * age
                y = q["y"] + q["vy"] * age + 0.5 * q["g"] * age * age
                if q["kind"] == "spark":
                    y = min(y, ground - size)
                self.rect(x - size / 2, y - size / 2, size, size, q["color"])

        my = p["my"]
        for i, ft in p["fire"].items():  # bullets + muzzle flash
            f = self.FACING[i]
            if ft <= t < p["hit_t"]:
                self.draw_bullet(p["mx"][i] + f * self.BULLET_V * (t - ft), my, f)
            if 0 <= t - ft < 110:
                self.draw_star(p["mx"][i] + f * 2 * unit, my, unit * (1.2 + 0.8 * (1 - (t - ft) / 110.0)))
        if p["up"]:
            ux, uy = self.up_muzzle(p)
            ut = p["up"]["t"]
            if ut <= t < p["hit_t"]:
                self.draw_bullet(ux, uy - 0.4 * (t - ut), 0, vertical=True)
            if 0 <= t - ut < 110:
                self.draw_star(ux, uy - 2 * unit, unit * 1.4)

        if 0 <= post < 240:  # impact star
            self.draw_star(p["hit_x"], my, unit * (2 + 4 * ease(post / 240.0)))

        cx = 0
        if post < 0:
            if p["up"] and p["up"]["t"] <= t < p["fire"][winner]:
                self.draw_text("FOUL!", cx, -140, 7, PX_ORANGE)
            elif t > 200:
                self.draw_text("SLOW-MO", cx, -140, 6, PX_WHITE)
        else:
            if post < 900:  # floating "HIT!"
                self.draw_text("HIT!", self.FIG_X[loser], ground - 31 * unit - 0.03 * post, 5, PX_YELLOW)
            if post >= 400:
                self.draw_text("KO!", cx, -140, 8, PX_YELLOW)

    def draw_ready(self):
        for i in (0, 1):
            self.rect(self.FIG_X[i] - 6 * self.U, self.GROUND, 12 * self.U, self.U, PX_PURPLE)
            self.draw_figure(self.parts_for(i, "ready"), self.FIG_X[i], self.GROUND, self.FACING[i])

    def redraw(self):
        self.canvas.delete("dyn")
        if self.flash_left > 0:
            self.canvas.create_rectangle(0, 0, self.bd.width, self.gy, fill="#ffffff",
                                         outline="", tags="dyn")
        if self.mode == "trainer":
            self.draw_trainer()
        elif self.plan:
            self.draw_plan(self.t if self.mode == "duel" else 1e9, self.mode == "duel")
        else:
            self.draw_ready()
        if self.mode == "void":
            self.draw_tumbleweed(self.t)
            if self.t > 400:
                self.draw_text("TOO SLOW!", 0, -140, 7, PX_WHITE)
        if self.text:
            txt, color, scale, top = self.text
            self.draw_text(txt, 0, (top - self.gy) if top is not None else -140, scale, color)
        if self.banner and self.mode == "static":  # flashing MATCH POINT!
            flash = PX_YELLOW if int(time.perf_counter() * 2.5) % 2 == 0 else PX_ORANGE
            self.draw_text(self.banner, 0, -205, 4, flash)

    # ---------- trainer scene: one gunslinger and a pop-up target ----------
    TARGET_X = 210
    TRAIN_BULLET_V = 1.6  # px per ms (real time: drills are fast, no slow-mo)

    @staticmethod
    def _now():
        return time.perf_counter() * 1000.0

    def trainer_begin(self):
        self.mode = "trainer"
        self.plan, self.plan_key, self.text, self.banner = {}, None, None, None
        self.tr = dict(target="hidden", t0=0.0, shot=None, parts=[])
        self.redraw()

    def trainer_arm(self):
        self.tr.update(target="hidden", shot=None, parts=[])

    def trainer_signal(self):
        self.tr.update(target="up", t0=self._now(), shot=None, parts=[])

    def trainer_shoot(self, hit):
        """Fire at the target (hit=True) or into the sky because it was too early."""
        play_sound_effect("gunshot")
        unit = self.U
        now = self._now()
        if hit:
            mx = self.FIG_X[0] + self.MUZZLE[0] * unit
            t_hit = now + ((self.TARGET_X - 6 * unit) - mx) / self.TRAIN_BULLET_V
            parts = []
            for _ in range(20):  # wood chips + sparks
                parts.append(dict(t0=t_hit, x=self.TARGET_X - 6 * unit, y=self.MUZZLE[1] * unit,
                                  vx=-(0.05 + random.random() * 0.5), vy=-(0.1 + random.random() * 0.6),
                                  g=0.0016, life=500 + random.random() * 300,
                                  s0=random.choice((unit, unit * 0.6, unit * 1.2)), s1=unit * 0.4,
                                  color=random.choice(("#d9a066", HOLSTER, PX_WHITE, PX_YELLOW, PX_RED)),
                                  kind="spark"))
            self.tr.update(shot=dict(t0=now, hit=True, t_hit=t_hit), parts=parts)
        else:
            self.tr.update(shot=dict(t0=now, hit=False), parts=[])

    def trainer_miss(self):
        self.tr.update(target="sinking", t0=self._now(), shot=None, parts=[])

    def trainer_text(self, text, color=PX_WHITE, scale=7):
        self.text = (text, color, scale, None) if text else None

    def clipped_rect(self, x, y, w, h, color):
        """Rectangle clipped at the ground line (so the target emerges from the ground)."""
        if y >= 0:
            return
        if y + h > 0:
            h = -y
        self.rect(x, y, w, h, color)

    def draw_trainer(self):
        unit = self.U
        tr = self.tr or {}
        now = self._now()
        shot = tr.get("shot")
        pose, ox = "ready", self.FIG_X[0]
        if shot:
            age = now - shot["t0"]
            if age < 700:
                pose = "aim" if shot["hit"] else "aim_up"
            if age < 160:
                ox -= 2 * unit * (1 - age / 160.0)
        self.rect(ox - 6 * unit, 0, 12 * unit, unit, PX_PURPLE)
        self.draw_figure(self.parts_for(0, pose), ox, 0, 1)

        state = tr.get("target", "hidden")  # the target
        drop = None
        if state == "up":
            drop = 22 * unit * (1 - ease((now - tr["t0"]) / 140.0))
        elif state == "sinking":
            drop = 22 * unit * ease((now - tr["t0"]) / 260.0)
        if drop is not None and drop < 22 * unit:
            wob, flash = 0.0, False
            if shot and shot.get("hit") and now >= shot["t_hit"]:
                a = now - shot["t_hit"]
                wob = math.sin(a / 38.0) * max(0.0, 1 - a / 420.0) * unit * 1.5
                flash = a < 110
            tx = self.TARGET_X + wob
            for x, y, w, h in ((-7, -22, 14, 14), (-2, -10, 4, 10)):  # outline
                self.clipped_rect(tx + x * unit, y * unit + drop, w * unit, h * unit, PX_DARK)
            for x, y, w, h, c in ((-6, -21, 12, 12, HOLSTER), (-1, -9, 2, 9, HOLSTER),
                                  (-5, -20, 10, 10, PX_WHITE), (-4, -19, 8, 8, "#e43b44"),
                                  (-3, -18, 6, 6, PX_WHITE), (-2, -17, 4, 4, "#e43b44"),
                                  (-1, -16, 2, 2, PX_WHITE)):
                self.clipped_rect(tx + x * unit, y * unit + drop, w * unit, h * unit, "#ffffff" if flash else c)

        my = self.MUZZLE[1] * unit
        if shot:
            age = now - shot["t0"]
            if shot["hit"]:
                mx = self.FIG_X[0] + self.MUZZLE[0] * unit
                if now < shot["t_hit"]:
                    self.draw_bullet(mx + self.TRAIN_BULLET_V * age, my, 1)
                if 0 <= age < 110:
                    self.draw_star(mx + 2 * unit, my, unit * (1.2 + 0.8 * (1 - age / 110.0)))
                a = now - shot["t_hit"]
                if 0 <= a < 240:
                    self.draw_star(self.TARGET_X - 6 * unit, my, unit * (2 + 4 * ease(a / 240.0)))
            else:
                ux, uy = self.FIG_X[0] + 6 * unit, -28 * unit
                if uy - 0.8 * age > -420:
                    self.draw_bullet(ux, uy - 0.8 * age, 0, vertical=True)
                if 0 <= age < 110:
                    self.draw_star(ux, uy - 2 * unit, unit * 1.4)
        for q in tr.get("parts", []):  # sparks
            age = now - q["t0"]
            if 0 <= age < q["life"]:
                k = age / q["life"]
                size = q["s0"] + (q["s1"] - q["s0"]) * k
                x = q["x"] + q["vx"] * age
                y = min(q["y"] + q["vy"] * age + 0.5 * q["g"] * age * age, -size)
                self.rect(x - size / 2, y - size / 2, size, size, q["color"])

    # ---------- main loop ----------

    def loop(self):
        self.job = None
        if self.mode == "stopped":
            return
        now = time.perf_counter()
        real_dt = min(60.0, (now - self.last) * 1000.0)
        self.last = now
        if self.flash_left > 0:
            self.flash_left -= real_dt
        if self.mode in ("duel", "void"):
            self.advance(real_dt)
        try:
            if self.mode == "stopped":
                return
            self.redraw()
            delay = 20 if self.mode in ("duel", "void", "trainer") else 100
            self.job = self.canvas.after(delay, self.loop)
        except tk.TclError:
            self.job = None

    def advance(self, real_dt):
        if self.mode == "void":
            self.t += real_dt * self.speed
            if self.t >= 3000:
                self.finish()
            return
        p = self.plan
        if self.freeze > 0:  # hit-stop: time stands still
            self.freeze -= real_dt
            return
        nt = self.t + real_dt * self.speed
        if not self.hit_done and nt >= p["hit_t"]:
            nt = p["hit_t"]
            self.hit_done = True
            self.freeze = self.FREEZE_MS
            self.flash_left = 80
            self.sfx("buzz")
            play_sound_effect("bullet hit")
            self.shake(10, 10)
        self.t = nt
        while self.ev_i < len(p["events"]) and p["events"][self.ev_i][0] <= self.t:
            self.sfx(p["events"][self.ev_i][1])
            play_sound_effect("gunshot")
            self.ev_i += 1
        if self.t >= p["end_t"]:
            self.finish()

    # ---------- public API ----------
    def play_duel(self, winner, loser, delta_ms, early, on_done, speed=1.0):
        self.plan = self.make_plan(winner, loser, delta_ms, early)
        self.plan_key = None
        self.mode, self.t, self.speed = "duel", 0.0, speed
        self.freeze, self.flash_left, self.hit_done, self.ev_i = 0.0, 0.0, False, 0
        self.done_cb, self.text = on_done, None
        self.last = time.perf_counter()
        self.redraw()

    def play_void(self, on_done, speed=1.0):
        self.plan, self.plan_key = {}, None
        self.mode, self.t, self.speed = "void", 0.0, speed
        self.done_cb, self.text = on_done, None
        self.last = time.perf_counter()
        self.sfx("void")
        self.redraw()

    def show_ready(self, text=None, color=PX_WHITE, scale=6, top=None):
        self.mode, self.plan, self.plan_key = "static", {}, None
        self.text = (text, color, scale, top) if text else None
        self.redraw()

    def show_final(self, winner, loser, text=None, color=PX_YELLOW, scale=7):
        key = (winner, loser)
        if self.plan_key != key or not self.plan:
            self.plan = self.make_plan(winner, loser, None, False)
            self.plan_key = key
        self.mode = "static"
        self.text = (text, color, scale, None) if text else None
        self.redraw()

    def skip(self):
        if self.mode in ("duel", "void"):
            self.finish()

    def finish(self):
        cb = self.done_cb
        self.done_cb = None
        if self.mode == "duel":
            self.show_final(self.plan["W"], self.plan["L"], "KO!")
        else:
            self.show_ready("TOO SLOW!")
        if cb is not None:
            cb()

    def stop(self):
        self.mode = "stopped"
        self.done_cb = None
        if self.bd.on_change == self.redraw:
            self.bd.on_change = None
        if self.job is not None:
            try:
                self.canvas.after_cancel(self.job)
            except tk.TclError:
                pass
            self.job = None


# ============================================================
# The game
# ============================================================
class ReactionDuel:
    # Attributes that are assigned in reset_game_data(), build_*() and show_*() are declared
    # here, so every attribute of the app is documented in one place.
    state: str
    players: list[Player]
    total_slots: int
    round_log: list[Any]
    sudden_death: bool
    sd_players: set[int]
    round_players: set[int]
    locked_out: set[int]
    presses: dict[int, float]
    collecting: bool
    go_time: float
    countdown_value: int
    report: dict[str, Any]
    notice: str
    paused_state: Optional[str]
    match_winner: Optional[int]
    bar: tk.Frame
    btn_row: tk.Frame
    chip_row: tk.Frame
    round_lbl: TextLabel
    dots: tk.Canvas
    main_lbl: TextLabel
    sub_lbl: TextLabel
    table: tk.Frame
    btn_primary: FlatButton
    btn_pause: FlatButton
    btn_menu: FlatButton
    tr_stat: dict[str, TextLabel]
    tr_box: tk.Frame
    tr_box_lbl: TextLabel
    tr_rows: list[TextLabel]
    tr_strip: tk.Canvas
    tr_rating: TextLabel
    tr_coach: TextLabel
    tr_btn_pause: FlatButton
    tr_btn_tempo: FlatButton

    def __init__(self, root):
        self.root = root
        root.title("Reaction Duel")
        root.geometry("1060x780")
        root.minsize(960, 720)

        self.settings = Settings()
        self.names = [f"Player {i + 1}" for i in range(MAX_PLAYERS)]
        self.keys = list(DEFAULT_KEYS)

        self.screen = "menu"
        self.cur_bg, self.cur_fg = THEMES["Classic"]["idle"]
        self.rebind_target = None
        self.settings_msg = ""
        self.down: set[str] = set()  # keys currently held (ignores auto-repeat)
        self.jobs = {}  # named after() callbacks
        self.shake_job = None
        self.confetti = []
        self.confetti_job = None
        self.overlay = None
        self.gf = None
        self.arena: Optional[DuelArena] = None  # pixel duel scene in the game screen
        self.menu_arena: Optional[DuelArena] = None  # decorative duel figures on the menu
        self.backdrop: Optional[PixelBackdrop] = None  # full-window pixel scenery (Pixel theme)
        self.bottom: Optional[PixelPanel] = None  # bottom info panel (Pixel game screen)
        self.showdown_then = None
        self.outfits = [dict(o) for o in DEFAULT_OUTFITS]  # what the duel fighters wear
        self.mode = "duel"  # duel | solo
        self.pick_vals, self.pick_swatch, self.pick_edges = {}, {}, {}
        self.tr_trials, self.tr_state, self.tr_paused, self.tr_t0 = [], "intro", False, 0.0
        self.reset_game_data()

        # All screens live inside "stage" so we can shake it
        self.stage = tk.Frame(root)
        self.stage.place(x=0, y=0, relwidth=1, relheight=1)

        root.bind("<KeyPress>", self.on_key_press)
        root.bind("<KeyRelease>", self.on_key_release)
        root.bind("<FocusOut>", lambda _e: self.down.clear())
        root.bind("<F11>", lambda _e: self.toggle_fullscreen())

        self.show_menu()

    # ---------- theme ----------
    @property
    def theme(self):
        return THEMES[self.settings.theme]

    @property
    def bd(self) -> PixelBackdrop:
        """The scenery of the current Pixel screen (only valid while one is showing)."""
        if self.backdrop is None:
            raise RuntimeError("this screen has no pixel backdrop")
        return self.backdrop

    def need_arena(self) -> DuelArena:
        if self.arena is None:
            raise RuntimeError("this screen has no duel arena")
        return self.arena

    @property
    def pixel(self):
        return bool(self.theme.get("pixel"))

    def player_color(self, idx):
        if self.pixel and idx < 2:  # the two duel fighters wear their chosen color
            return self.outfits[idx]["color"]
        colors = self.theme["players"]
        return colors[idx % len(colors)]

    def sync_font(self):
        """Pixel theme uses a chunky monospace font everywhere."""
        global FONT
        FONT = self.theme.get("font", "Helvetica")

    def swatch_widget(self, parent, color, size=14, bg=None):
        """A little colored marker for a player: a solid square (Pixel) or a dot."""
        if self.pixel:
            return tk.Frame(parent, width=12, height=12, bg=color)
        return tk.Label(parent, text="\u25cf", font=(FONT, size + 6), fg=color,
                        bg=bg or self.cur_bg)

    def play(self, name):
        if not self.settings.sound or not IS_MAC:
            return
        path = os.path.join(SOUND_DIR, SOUND_FILES[name] + ".aiff")
        if os.path.exists(path):
            try:
                subprocess.Popen(["afplay", path],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except OSError:
                pass

    # ---------- scheduling ----------
    def schedule(self, name, ms, fn):
        self.cancel(name)

        def run():
            self.jobs.pop(name, None)
            fn()

        self.jobs[name] = self.root.after(ms, run)

    def cancel(self, name):
        job = self.jobs.pop(name, None)
        if job is not None:
            self.root.after_cancel(job)

    def cancel_jobs(self):
        for name in list(self.jobs):
            self.cancel(name)

    # ---------- fullscreen ----------
    def apply_fullscreen(self):
        self.root.attributes("-fullscreen", self.settings.fullscreen)

    def toggle_fullscreen(self):
        self.settings.fullscreen = not self.settings.fullscreen
        self.apply_fullscreen()
        # Mid-round / mid-drill we leave the screen alone so nothing glitches
        if self.screen not in ("game", "trainer") or self.overlay is not None:
            self.refresh_screen()

    def refresh_screen(self):
        if self.screen == "menu":
            self.show_menu()
        elif self.screen == "more":
            self.show_more()
        elif self.screen == "settings":
            self.show_settings()
        elif self.screen == "howto":
            self.show_howto()
        elif self.screen == "picker":
            self.show_picker()
        elif self.screen == "game":
            self.refresh_game_ui()

    def stop_arenas(self):
        for arena in (self.arena, self.menu_arena):
            if arena is not None:
                arena.stop()
        if self.backdrop is not None:
            self.backdrop.stop()
        self.arena = None
        self.menu_arena = None
        self.backdrop = None

    def clear_stage(self):
        self.stop_confetti()
        self.stop_arenas()
        self.overlay = None
        for widget in self.stage.winfo_children():
            widget.destroy()
        self.stage.place_configure(x=0, y=0)

    def make_root(self, boxed=False):
        """Create the root widget of a screen and return the frame to fill with content.

        Pixel theme: a full-window scenic canvas (optionally with one centered panel on it).
        Other themes: a plain colored frame.
        """
        if self.pixel:
            self.backdrop = PixelBackdrop(self.stage, self.settings.arena)
            self.backdrop.canvas.pack(fill="both", expand=True)
            self.cur_bg, self.cur_fg = PANEL_BG, PANEL_FG
            if boxed:
                panel = PixelPanel(self.backdrop.canvas, bg=PANEL_BG, edge=PX_SLATE)
                panel.pack(expand=True, padx=16, pady=16)
                return panel.body
            return self.backdrop.canvas
        frame = tk.Frame(self.stage, bg=self.cur_bg)
        frame.pack(fill="both", expand=True)
        return frame

    def begin_screen(self, name, state_key="idle", boxed=False):
        self.screen = name
        self.sync_font()
        self.cancel_jobs()
        self.clear_stage()
        self.cur_bg, self.cur_fg = self.theme[state_key]
        self.root.configure(bg=self.cur_bg)
        frame = self.make_root(boxed)
        self.root.focus_set()
        return frame

    def btn(self, parent, text, command, style="secondary", size=14,
            padx=20, pady=9, width=0):
        return FlatButton(parent, text, command, self.theme, self.cur_bg,
                          self.cur_fg, style, size, padx, pady, width)

    def label(self, parent, text, size=14, bold=False, color=None, **kw):
        return TextLabel(parent, text, size, bold, color or self.cur_fg, self.cur_bg,
                         self.pixel, **kw)

    # ============================================================
    # Menu
    # ============================================================
    def show_menu(self):
        f = self.begin_screen("menu")
        s = self.settings
        summary = f"{s.rounds} rounds   |   {s.theme} theme"
        if self.pixel:
            self.show_menu_pixel(f, summary)
            return
        self.label(f, "REACTION", 64, True).pack(pady=(50, 0))
        self.label(f, "DUEL", 64, True, self.theme["accent"]).pack()
        self.label(f, summary, 15).pack(pady=(6, 24))
        self.btn(f, "Duel", self.start_duel, "primary", 22, width=14, pady=12).pack(pady=6)
        self.btn(f, "Solo", self.start_solo, "primary", 22, width=14, pady=12).pack(pady=6)
        self.btn(f, "More", self.show_more, "secondary", 18, width=16, pady=10).pack(pady=6)

    def show_menu_pixel(self, f, summary):
        """Pixel menu: the two gunslingers face off in the arena, buttons on a panel below."""
        panel = PixelPanel(f, bg=PANEL_BG, edge=PX_SLATE)
        panel.pack(side="bottom", pady=(0, 16))
        body = panel.body
        self.label(body, summary, 14).pack(pady=(12, 6), padx=20)
        row = tk.Frame(body, bg=PANEL_BG)
        row.pack(pady=(0, 4), padx=16)
        self.btn(row, "Duel", self.start_duel, "primary", 26, padx=30, pady=12,
                 width=9).pack(side="left", padx=6)
        self.btn(row, "Solo", self.start_solo, "primary", 26, padx=30, pady=12,
                 width=9).pack(side="left", padx=6)
        self.label(body, "DUEL: 2+ PLAYERS   |   SOLO: YOU VS A BOT", 11,
                   color=mix(PANEL_BG, PANEL_FG, 0.6)).pack(pady=(0, 6), padx=22)
        self.btn(body, "More", self.show_more, "secondary", 18, padx=24, pady=8,
                 width=12).pack(pady=(0, 12))
        self.root.update_idletasks()
        panel_h = panel.winfo_reqheight()
        bd = self.bd
        bd.ground_fn = lambda width, height: height - panel_h - 16 - 80
        self.menu_arena = DuelArena(bd, self.outfits)
        self.menu_arena.show_ready("REACTION DUEL", self.theme["accent"], 9, top=84)
        bd.apply()

    # ============================================================
    # Settings
    # ============================================================
    def set_option(self, attr, value):
        setattr(self.settings, attr, value)
        self.rebind_target = None
        self.settings_msg = ""
        if attr == "fullscreen":
            self.apply_fullscreen()
        self.show_settings()

    def reset_defaults(self):
        self.settings = Settings()
        self.names = [f"Player {i + 1}" for i in range(MAX_PLAYERS)]
        self.keys = list(DEFAULT_KEYS)
        self.rebind_target = None
        self.settings_msg = "Everything reset to defaults."
        self.apply_fullscreen()
        self.show_settings()

    def settings_back(self):
        self.rebind_target = None
        self.settings_msg = ""
        self.show_more()

    def stepper_row(self, parent, row, title, value_text, on_minus, on_plus):
        self.label(parent, title, 14, anchor="w").grid(row=row, column=0, sticky="w",
                                                       pady=6, padx=(0, 18))
        ctl = tk.Frame(parent, bg=self.cur_bg)
        ctl.grid(row=row, column=1, sticky="w")
        self.btn(ctl, "-", on_minus, size=14, padx=14, pady=4).pack(side="left")
        self.label(ctl, value_text, 15, True, width=7).pack(side="left", padx=6)
        self.btn(ctl, "+", on_plus, size=14, padx=14, pady=4).pack(side="left")

    def toggle_row(self, parent, row, title, attr):
        value = getattr(self.settings, attr)
        self.label(parent, title, 14, anchor="w").grid(row=row, column=0, sticky="w",
                                                       pady=6, padx=(0, 18))
        ctl = tk.Frame(parent, bg=self.cur_bg)
        ctl.grid(row=row, column=1, sticky="w")
        self.btn(ctl, "On" if value else "Off",
                 lambda: self.set_option(attr, not value),
                 "primary" if value else "secondary", 14, padx=22, pady=4).pack(side="left")

    def choice_row(self, parent, row, title, attr, options):
        current = getattr(self.settings, attr)
        self.label(parent, title, 14, anchor="w").grid(row=row, column=0, sticky="w",
                                                       pady=6, padx=(0, 18))
        ctl = tk.Frame(parent, bg=self.cur_bg)
        ctl.grid(row=row, column=1, sticky="w")
        for option in options:
            self.btn(ctl, option, lambda o=option: self.set_option(attr, o),
                     "primary" if option == current else "secondary",
                     11, padx=7, pady=4).pack(side="left", padx=2)

    def show_settings(self):
        f = self.begin_screen("settings", boxed=True)
        s = self.settings
        self.label(f, "SETTINGS", 34 if self.pixel else 30, True).pack(pady=(10, 0))

        # Footer / theme row are packed first (bottom) so they never get pushed off-screen
        foot = tk.Frame(f, bg=self.cur_bg)
        foot.pack(side="bottom", pady=(8, 8))
        self.btn(foot, "Back", self.settings_back, "primary").pack(side="left", padx=8)
        self.btn(foot, "Reset to Defaults", self.reset_defaults).pack(side="left", padx=8)
        self.label(f, self.settings_msg, 14, True, self.theme["accent"]).pack(side="bottom")
        if s.theme == "Pixel":
            note = ("Pixel duel scene: Solo, or Duel with exactly 2 players" if s.num_players == 2
                    else "Duel scene needs exactly 2 players (Solo always has it)")
            self.label(f, note, 11, color=mix(self.cur_bg, self.cur_fg, 0.6)).pack(
                side="bottom", pady=(2, 0))
        trow = tk.Frame(f, bg=self.cur_bg)
        trow.pack(side="bottom", pady=(4, 0))
        self.choice_row(trow, 0, "Theme", "theme", THEME_NAMES)

        body = tk.Frame(f, bg=self.cur_bg)
        body.pack(expand=True, pady=(4, 0))
        left = tk.Frame(body, bg=self.cur_bg)
        left.grid(row=0, column=0, padx=22, sticky="n")
        right = tk.Frame(body, bg=self.cur_bg)
        right.grid(row=0, column=1, padx=22, sticky="n")

        # ----- left column: game options -----
        self.stepper_row(left, 0, "Duel players", str(s.num_players),
                         lambda: self.set_option("num_players", clamp(s.num_players - 1, MIN_PLAYERS, MAX_PLAYERS)),
                         lambda: self.set_option("num_players", clamp(s.num_players + 1, MIN_PLAYERS, MAX_PLAYERS)))
        self.stepper_row(left, 1, "Rounds", str(s.rounds),
                         lambda: self.set_option("rounds", clamp(s.rounds - 1, MIN_ROUNDS, MAX_ROUNDS)),
                         lambda: self.set_option("rounds", clamp(s.rounds + 1, MIN_ROUNDS, MAX_ROUNDS)))
        self.stepper_row(left, 2, "Too-slow limit", f"{s.too_slow:.1f} s",
                         lambda: self.set_option("too_slow",
                                                 round(clamp(s.too_slow - 0.5, MIN_TOO_SLOW, MAX_TOO_SLOW), 1)),
                         lambda: self.set_option("too_slow",
                                                 round(clamp(s.too_slow + 0.5, MIN_TOO_SLOW, MAX_TOO_SLOW), 1)))
        self.choice_row(left, 3, "Wait time", "wait", list(WAIT_PRESETS))
        self.toggle_row(left, 4, "3-2-1 countdown", "countdown")
        self.toggle_row(left, 5, "Sound" if IS_MAC else "Sound (Mac only)", "sound")
        self.toggle_row(left, 6, "Screen shake", "shake")
        self.toggle_row(left, 7, "Fullscreen", "fullscreen")
        self.toggle_row(left, 8, "Duel animation", "duel_anim")
        self.choice_row(left, 9, "Slow-mo speed", "slowmo", list(SLOWMO))
        self.choice_row(left, 10, "Bot level", "bot_level", list(BOT_LEVELS))
        self.toggle_row(left, 11, "Early clinch", "early_clinch")

        # ----- right column: names + keys -----
        self.label(right, "Players", 18, True).grid(row=0, column=0, columnspan=3, pady=(6, 2))
        self.label(right, "click Key to rebind", 11,
                   color=mix(self.cur_bg, self.cur_fg, 0.6)).grid(row=1, column=0, columnspan=3, pady=(0, 8))
        for i in range(s.num_players):
            row = i + 2
            self.swatch_widget(right, self.player_color(i), 14).grid(row=row, column=0,
                                                                     padx=(0, 6), pady=2)
            var = tk.StringVar(value=self.names[i])
            var.trace_add("write", lambda *_a, idx=i, v=var: self.set_name(idx, v))
            entry = tk.Entry(right, textvariable=var, width=11, font=(FONT, 13),
                             bg="#ffffff", fg="#111111", insertbackground="#111111",
                             relief="flat", highlightthickness=2,
                             highlightbackground=mix(self.cur_bg, self.cur_fg, 0.35),
                             highlightcolor=self.theme["accent"])
            entry.grid(row=row, column=1, padx=6, pady=2, ipady=2)
            entry.bind("<Return>", lambda _e: self.root.focus_set())
            waiting = self.rebind_target == i
            self.btn(right, "Press key..." if waiting else f"Key: {key_label(self.keys[i])}",
                     lambda idx=i: self.start_rebind(idx),
                     "primary" if waiting else "secondary", 11, padx=8, pady=4,
                     width=12).grid(row=row, column=2, padx=6, pady=2)

    def set_name(self, idx, var):
        value = var.get()
        if len(value) > NAME_MAX:
            value = value[:NAME_MAX]
            var.set(value)
        self.names[idx] = value

    def start_rebind(self, idx):
        self.root.focus_set()
        self.rebind_target = idx
        self.settings_msg = f"Press a key for {self.names[idx] or 'this player'}  (Esc to cancel)"
        self.show_settings()

    def handle_rebind(self, key):
        idx = self.rebind_target
        if idx is None:
            return
        if key == "escape":
            self.rebind_target = None
            self.settings_msg = "Rebind cancelled."
        elif key in RESERVED_KEYS:
            self.settings_msg = f"{key_label(key)} is reserved - try another key."
        elif not (len(key) == 1 or key in ARROW_KEYS):
            self.settings_msg = "That key can't be used - try a letter, number, or arrow."
        else:
            clash = next((j for j, k in enumerate(self.keys) if k == key and j != idx), None)
            if clash is not None:
                who = self.names[clash] or f"Player {clash + 1}"
                if clash >= self.settings.num_players:
                    who += " (not playing)"
                self.settings_msg = f"{key_label(key)} is already used by {who}."
            else:
                self.keys[idx] = key
                self.rebind_target = None
                self.settings_msg = f"{self.names[idx] or 'Player'} now uses {key_label(key)}."
        self.show_settings()

    # ============================================================
    # How to play
    # ============================================================
    def show_howto(self):
        f = self.begin_screen("howto", boxed=True)
        self.label(f, "HOW TO PLAY", 34, True).pack(pady=(10, 8))
        rules = [
            "1.  DUEL = 2+ players on one keyboard.  SOLO = you vs a bot.",
            "2.  Press Start Round. The WAIT sky is red: do NOT press yet!",
            "3.  The moment the screen flips to GO (green), hit your key.",
            "4.  Jump the gun and you're locked out of that round. If everyone",
            "     else jumps too, the last player standing wins by default.",
            "5.  Nobody presses in time? The round is voided and an extra",
            "     round is added to the end of the match.",
            "6.  Most round wins takes the match. MATCH POINT! flashes when the",
            "     next win would end it. Tied at the end? Sudden death.",
            "7.  Pixel theme + 2 players (or Solo): pick outfits and an arena,",
            "     then every round ends in a slow-motion shootout. Space skips.",
            "8.  More > Trainer: fast reaction drills with a coach and a click",
            "     feed (green = faster than your last click, red = slower).",
            "",
            "Esc = pause/back  |  Space = start/next round  |  F11 = fullscreen",
        ]
        side_pad = 24 if self.pixel else 110
        for line in rules:
            self.label(f, line, 15, anchor="w", justify="left").pack(
                anchor="w", padx=side_pad, pady=1 if self.pixel else 0)

        self.label(f, "Keys", 18, True, self.theme["accent"]).pack(pady=(10, 4))
        row = tk.Frame(f, bg=self.cur_bg)
        row.pack()
        for i in range(self.settings.num_players):
            cell = tk.Frame(row, bg=self.cur_bg)
            cell.pack(side="left", padx=10)
            self.swatch_widget(cell, self.player_color(i), 14).pack(pady=(0, 2))
            self.label(cell, self.names[i] or f"Player {i + 1}", 12).pack()
            self.label(cell, key_label(self.keys[i]), 16, True).pack()

        self.btn(f, "Back", self.show_more, "primary").pack(pady=(12, 8))

    # ============================================================
    # Game data
    # ============================================================
    def reset_game_data(self):
        self.state = IDLE
        self.players = []
        self.total_slots = 0
        self.round_log = []  # winner index or VOID, one per finished round
        self.sudden_death = False
        self.sd_players = set()
        self.round_players = set()  # who is taking part in the current round
        self.locked_out = set()
        self.presses = {}  # player index -> reaction time in ms
        self.collecting = False
        self.go_time = 0.0
        self.countdown_value = 0
        self.report = {}
        self.notice = ""
        self.paused_state = None
        self.match_winner = None  # who actually won the whole match

    def new_match(self):
        self.reset_game_data()
        if self.mode == "solo":  # you vs a bot
            self.players = [
                Player(0, (self.names[0].strip() or "Player 1"), self.keys[0]),
                Player(1, f"Bot {self.settings.bot_level}", "", bot=True),
            ]
        else:
            n = self.settings.num_players
            self.players = [
                Player(i, (self.names[i].strip() or f"Player {i + 1}"), self.keys[i])
                for i in range(n)
            ]
        self.total_slots = self.settings.rounds

    def show_game(self, new=True):
        self.gf = self.begin_screen("game")
        if new:
            self.new_match()
        self.build_game_widgets()
        self.render()

    def refresh_game_ui(self):
        had_overlay = self.overlay is not None
        if had_overlay:
            self.close_overlay()
        self.sync_font()
        self.stop_arenas()
        if self.gf is not None:
            self.gf.destroy()
        self.cur_bg, self.cur_fg = self.theme["idle"]
        self.root.configure(bg=self.cur_bg)
        self.gf = self.make_root()
        self.build_game_widgets()
        self.render()
        if had_overlay:
            self.build_overlay()

    def build_game_widgets(self):
        if self.pixel:
            self.build_game_widgets_pixel()
        else:
            self.build_game_widgets_classic()

    def build_game_widgets_classic(self):
        gf = self.gf
        bg, fg = self.cur_bg, self.cur_fg
        self.bar = tk.Frame(gf, bg=bg, height=84)
        self.bar.pack(side="bottom", fill="x")
        self.bar.pack_propagate(False)
        self.btn_row = tk.Frame(self.bar, bg=bg)
        self.btn_row.place(relx=0.5, rely=0.5, anchor="center")

        self.chip_row = tk.Frame(gf, bg=bg)
        self.chip_row.pack(side="top", fill="x", padx=14, pady=(14, 4))
        self.round_lbl = TextLabel(gf, "", 16, True, fg, bg, False)
        self.round_lbl.pack(pady=(4, 0))
        self.dots = tk.Canvas(gf, height=34, highlightthickness=0, bg=bg)
        self.dots.pack()
        self.main_lbl = TextLabel(gf, "", 56, True, fg, bg, False, wraplength=860)
        self.main_lbl.pack(expand=True)
        self.sub_lbl = TextLabel(gf, "", 17, False, fg, bg, False, wraplength=860,
                                 justify="center")
        self.sub_lbl.pack()
        self.table = tk.Frame(gf, bg=bg)
        self.table.pack(pady=(6, 8))

        self.btn_primary = FlatButton(self.btn_row, "", self.primary_action, self.theme,
                                      bg, fg, "primary", 15)
        self.btn_pause = FlatButton(self.btn_row, "Pause", self.open_pause, self.theme,
                                    bg, fg, "secondary", 15)
        self.btn_menu = FlatButton(self.btn_row, "Main Menu", self.show_menu, self.theme,
                                   bg, fg, "secondary", 15)

    def build_game_widgets_pixel(self):
        """Pixel layout: HUD panel on top, the desert scene in the middle, info panel below."""
        root = self.gf  # the full-window backdrop canvas
        bg, fg = PANEL_BG, PANEL_FG
        two = len(self.players) == 2

        hud = PixelPanel(root, bg=bg, edge=PX_SLATE)
        hud.pack(side="top", fill="x", padx=12, pady=(12, 0))
        self.chip_row = tk.Frame(hud.body, bg=bg)
        self.chip_row.pack(fill="x", padx=6, pady=(6, 2))
        self.round_lbl = TextLabel(hud.body, "", 16, True, fg, bg, True)
        self.round_lbl.pack(pady=(2, 0))
        self.dots = tk.Canvas(hud.body, height=34, highlightthickness=0, bg=bg)
        self.dots.pack(pady=(0, 4))

        self.bottom = PixelPanel(root, bg=bg, edge=PX_SLATE)
        if two:  # fixed size so the scene above never jumps around
            self.bottom.configure(width=PX_BOTTOM_W, height=PX_BOTTOM_H)
            self.bottom.pack_propagate(False)
            self.bottom.pack(side="bottom", pady=(0, 12))
        else:
            self.bottom.pack(side="bottom", padx=12, pady=(0, 12))
        body = self.bottom.body
        self.bar = tk.Frame(body, bg=bg)
        self.bar.pack(side="bottom", pady=(0, 6))
        self.btn_row = self.bar
        mid = tk.Frame(body, bg=bg)
        mid.pack(expand=True, padx=16, pady=(6, 8))
        self.main_lbl = TextLabel(mid, "", 40, True, fg, bg, True, wraplength=PX_BOTTOM_W - 80)
        self.main_lbl.pack(pady=(2, 2))
        self.sub_lbl = TextLabel(mid, "", 17, False, fg, bg, True, wraplength=PX_BOTTOM_W - 80,
                                 justify="center")
        self.sub_lbl.pack()
        self.table = tk.Frame(mid, bg=bg)
        self.table.pack(pady=(4, 0))

        self.btn_primary = FlatButton(self.btn_row, "", self.primary_action, self.theme,
                                      bg, fg, "primary", 15)
        self.btn_pause = FlatButton(self.btn_row, "Pause", self.open_pause, self.theme,
                                    bg, fg, "secondary", 15)
        self.btn_menu = FlatButton(self.btn_row, "Main Menu", self.show_menu, self.theme,
                                   bg, fg, "secondary", 15)

        bd = self.bd
        if two:
            self.arena = DuelArena(bd, self.outfits, sfx=self.play, shake=self.shake)
            bd.ground_fn = lambda width, height: height - PX_BOTTOM_H - 12 - 70
        else:
            bd.ground_fn = lambda width, height: int(height * 0.70)
        bd.apply()

    # ============================================================
    # Rendering
    # ============================================================
    def state_colors(self):
        key = {IDLE: "idle", COUNTDOWN: "idle", WAITING: "wait", GO: "go",
               SHOWDOWN: "idle", ROUND_OVER: "result", MATCH_OVER: "result"}[self.state]
        return self.theme[key]

    def render(self):
        if self.screen != "game" or self.gf is None or not self.gf.winfo_exists():
            return
        if self.pixel:
            bg, fg = PANEL_BG, PANEL_FG
            self.bd.set_palette({WAITING: "wait", GO: "go"}.get(self.state, "idle"))
            if self.bottom is not None:
                self.bottom.set_edge({WAITING: PX_ALERT, GO: PX_GREEN}.get(self.state, PX_SLATE))
        else:
            bg, fg = self.state_colors()
            self.root.configure(bg=bg)
            for w in (self.gf, self.bar, self.btn_row, self.chip_row, self.table, self.dots):
                w.configure(bg=bg)
            for w in (self.round_lbl, self.main_lbl, self.sub_lbl):
                w.set(bg=bg, fg=fg)
        self.render_chips(bg, fg)
        self.render_dots(bg, fg)
        self.render_texts(bg, fg)
        self.render_table(bg, fg)
        self.render_buttons(bg, fg)
        self.render_arena()

    def render_arena(self):
        """Keep the pixel duel scene in sync with the game state (not while it is animating)."""
        a = self.arena
        if a is None or self.state == SHOWDOWN:
            return
        s = self.state
        accent = self.theme["accent"]
        mp = s in (IDLE, COUNTDOWN, WAITING, GO, ROUND_OVER) and bool(self.match_point_players())
        a.banner = "MATCH POINT!" if mp else None
        if s in (ROUND_OVER, MATCH_OVER) and self.report:
            winner = self.report.get("winner")
            if s == MATCH_OVER and self.match_winner is not None:
                winner = self.match_winner  # the match winner stands, whoever took the last round
            if winner is not None:
                a.show_final(winner, 1 - winner, "WINNER!" if s == MATCH_OVER else "KO!", accent)
            else:
                a.show_ready("TOO SLOW!", PX_WHITE)
        elif s == COUNTDOWN:
            a.show_ready(str(self.countdown_value), PX_WHITE, 8)
        elif s == WAITING:
            a.show_ready("WAIT...", PX_WHITE, 7)
        elif s == GO:
            a.show_ready("GO!", accent, 9)
        else:
            a.show_ready("READY?", PX_WHITE, 7)

    def round_text(self):
        if self.state == MATCH_OVER:
            return "Match complete"
        if self.sudden_death:
            names = ", ".join(self.players[i].name for i in sorted(self.sd_players))
            return f"SUDDEN DEATH  -  {names}"
        done = len(self.round_log)
        number = done if self.state == ROUND_OVER else done + 1
        text = f"Round {max(1, number)} of {self.total_slots}"
        if self.match_point_players():
            text += "  -  MATCH POINT!"
        return text

    def render_chips(self, bg, fg):
        for w in self.chip_row.winfo_children():
            w.destroy()
        pix = self.pixel
        n = len(self.players)
        cols = 4 if (pix and n > 4) else n
        for c in range(MAX_PLAYERS):
            self.chip_row.grid_columnconfigure(c, weight=1 if c < cols else 0,
                                               uniform="chip" if c < cols else "")
        big = n <= 4 if pix else n <= 5
        chip_bg = mix(bg, fg, 0.08 if pix else 0.12)
        muted = mix(bg, fg, 0.45)
        winner_idx = self.report.get("winner") if self.report else None
        show_winner = self.state in (ROUND_OVER, MATCH_OVER)

        for p in self.players:
            out = p.index in self.locked_out
            sitting = self.sudden_death and p.index not in self.sd_players
            dim = out or sitting
            won = show_winner and winner_idx == p.index
            border = self.theme["accent"] if won else (muted if dim else self.player_color(p.index))
            chip: tk.Frame
            host: tk.Frame
            if pix:
                chip_panel = PixelPanel(self.chip_row, bg=chip_bg, edge=border, thick=3, inset=2)
                chip, host = chip_panel, chip_panel.body
            else:
                chip = tk.Frame(self.chip_row, bg=chip_bg, highlightthickness=4,
                                highlightbackground=border, highlightcolor=border)
                host = chip
            chip.grid(row=p.index // cols, column=p.index % cols, sticky="nsew",
                      padx=4, pady=3 if pix else 0)
            text_color = muted if dim else fg
            TextLabel(host, ("\u2605 " if won else "") + p.name, 13 if big else 11, True,
                      text_color, chip_bg, pix).pack(pady=(6, 0))
            TextLabel(host, str(p.score), 30 if big else 22, True, text_color, chip_bg,
                      pix).pack()
            extra = "[BOT]" if p.bot else f"[{key_label(p.key)}]"
            if out:
                extra += "  OUT"
            elif sitting:
                extra += "  sitting out"
            elif p.streak >= 2:
                extra += f"  streak x{p.streak}"
            TextLabel(host, extra, 11, False, text_color, chip_bg, pix).pack(pady=(0, 6))

    def render_dots(self, bg, fg):
        c = self.dots
        c.delete("all")
        shape = c.create_rectangle if self.theme.get("square") else c.create_oval
        d, gap = 20, 10
        total = self.total_slots + (1 if self.sudden_death else 0)
        c.configure(width=total * (d + gap) + gap, height=d + 14)
        played = len(self.round_log)
        in_play = self.state in (COUNTDOWN, WAITING, GO, SHOWDOWN)
        muted = mix(bg, fg, 0.45)
        accent = self.theme["accent"]
        winner_idx = self.report.get("winner") if self.report else None

        for i in range(total):
            x0 = gap + i * (d + gap)
            y0 = 7
            x1, y1 = x0 + d, y0 + d
            is_sd_slot = self.sudden_death and i == total - 1
            if i < played:
                entry = self.round_log[i]
                if entry == VOID:
                    shape(x0, y0, x1, y1, outline=muted, width=2, dash=(3, 2))
                    c.create_line(x0 + 6, y0 + 6, x1 - 6, y1 - 6, fill=muted, width=2)
                    c.create_line(x0 + 6, y1 - 6, x1 - 6, y0 + 6, fill=muted, width=2)
                else:
                    color = self.player_color(entry)
                    shape(x0, y0, x1, y1, fill=color, outline=color)
            elif is_sd_slot and self.state == MATCH_OVER and winner_idx is not None:
                color = self.player_color(winner_idx)
                shape(x0, y0, x1, y1, fill=color, outline=accent, width=3)
            else:
                current = in_play and i == played
                shape(x0, y0, x1, y1, outline=fg if current else muted,
                      width=4 if current else 2)
                if is_sd_slot:
                    c.create_text((x0 + x1) / 2, (y0 + y1) / 2, text="!", fill=accent,
                                  font=(FONT, 12, "bold"))

    def render_texts(self, _bg, fg):
        s = self.state
        size = 56
        if s == IDLE:
            headline = "Ready?"
            sub = "Click Start Round or press Space.\nFingers on your keys - wait for GO!"
        elif s == COUNTDOWN:
            headline, sub, size = str(self.countdown_value), "Get ready...", 96
        elif s == WAITING:
            headline, sub, size = "WAIT...", (self.notice or "Don't press yet!"), 72
        elif s == GO:
            if self.collecting and self.presses:
                first = min(self.presses, key=lambda k: self.presses[k])
                headline = f"{self.players[first].name} hit first!"
                sub, size = "Waiting for the others...", 48
            else:
                headline, sub, size = "GO!", "", 110
        elif s == SHOWDOWN:
            headline, sub, size = "SLOW-MO!", "Press Space to skip", 40
        else:
            rep = self.report or {}
            headline, sub, size = rep.get("headline", ""), rep.get("detail", ""), 40

        if self.arena is not None:  # the scene tells the story; keep the text compact
            size = min(size, 30)
        round_color = self.theme["accent"] if self.sudden_death else fg
        self.round_lbl.set(text=self.round_text(), fg=round_color)
        self.main_lbl.set(text=headline, fg=fg, size=size)
        self.sub_lbl.set(text=sub, fg=fg)

    def render_table(self, bg, fg):
        for w in self.table.winfo_children():
            w.destroy()
        if self.state not in (ROUND_OVER, MATCH_OVER) or not self.report:
            return
        pix = self.pixel
        rows = self.report.get("rows", [])
        size = 14 if len(rows) <= 5 else 12
        muted = mix(bg, fg, 0.55)
        accent = self.theme["accent"]
        for r, row in enumerate(rows):
            p = self.players[row["idx"]]
            win = row.get("win", False)
            color = accent if win else fg
            pad = 1 if pix else 0
            TextLabel(self.table, row["rank"], size, win, color, bg, pix, width=3,
                      anchor="e").grid(row=r, column=0, pady=pad)
            self.swatch_widget(self.table, self.player_color(p.index), size, bg).grid(
                row=r, column=1, padx=(6, 8), pady=pad)
            TextLabel(self.table, p.name, size, win, color, bg, pix, width=14,
                      anchor="w").grid(row=r, column=2, pady=pad)
            TextLabel(self.table, row["time"], size, win, color, bg, pix, width=14,
                      anchor="e").grid(row=r, column=3, pady=pad)
            TextLabel(self.table, row["delta"], size, False, muted, bg, pix, width=10,
                      anchor="e").grid(row=r, column=4, pady=pad)

    def render_buttons(self, _bg, _fg):
        for b in (self.btn_primary, self.btn_pause, self.btn_menu):
            b.pack_forget()
        s = self.state
        if s == IDLE:
            self.btn_primary.set_text("Start Round  (Space)")
            shown = [self.btn_primary, self.btn_menu]
        elif s == ROUND_OVER:
            label = "Sudden Death  (Space)" if self.sudden_death else "Next Round  (Space)"
            self.btn_primary.set_text(label)
            shown = [self.btn_primary, self.btn_pause, self.btn_menu]
        elif s == MATCH_OVER:
            self.btn_primary.set_text("Rematch  (Space)")
            shown = [self.btn_primary, self.btn_menu]
        elif s == SHOWDOWN:
            self.btn_primary.set_text("Skip  (Space)")
            shown = [self.btn_primary]
        elif s in (COUNTDOWN, WAITING):
            shown = [self.btn_pause]
        else:
            shown = []
        for b in shown:
            b.pack(side="left", padx=8)

    # ============================================================
    # Round flow
    # ============================================================
    def primary_action(self):
        if self.overlay is not None:
            return
        if self.state in (IDLE, ROUND_OVER):
            self.begin_attempt()
        elif self.state == MATCH_OVER:
            self.show_game(True)
        elif self.state == SHOWDOWN:
            self.skip_showdown()

    def begin_attempt(self, notice=""):
        self.cancel_jobs()
        if self.sudden_death:
            self.round_players = set(self.sd_players)
        else:
            self.round_players = set(range(len(self.players)))
        self.locked_out = set()
        self.presses = {}
        self.collecting = False
        self.report = {}
        self.notice = notice
        if self.settings.countdown:
            self.run_countdown(3)
        else:
            self.enter_waiting()

    def run_countdown(self, n):
        self.state = COUNTDOWN
        self.countdown_value = n
        self.render()
        self.play("tick")
        nxt = (lambda: self.run_countdown(n - 1)) if n > 1 else self.enter_waiting
        self.schedule("countdown", COUNTDOWN_STEP_MS, nxt)
        self.root.update_idletasks()
        play_sound_effect("countdown")

    def enter_waiting(self):
        self.state = WAITING
        self.render()
        low, high = WAIT_PRESETS[self.settings.wait]
        delay = random.randint(low, high)
        self.schedule("wait", delay, self.enter_go)
        self.plan_bot_false_start(delay)

    def enter_go(self):
        self.state = GO
        self.collecting = False
        self.render()
        self.root.update_idletasks()
        self.go_time = time.perf_counter()
        self.schedule("timeout", int(self.settings.too_slow * 1000), self.on_timeout)
        self.plan_bot_press()
        self.root.after(1, lambda: self.play("go"))

    def on_timeout(self):
        if self.state == GO and not self.collecting:
            self.void_round("Too slow!", "Nobody pressed in time.")
            self.root.update_idletasks()
            play_sound_effect("too slow")

    # ---------- input ----------
    def player_press(self, idx):
        if idx not in self.round_players or idx in self.locked_out:
            return
        if self.state == WAITING:
            self.false_start(idx)
        elif self.state == GO:
            if idx in self.presses:
                return
            self.presses[idx] = (time.perf_counter() - self.go_time) * 1000.0
            first = not self.collecting
            if first:
                self.collecting = True
                self.cancel("timeout")
                self.schedule("collect", COLLECT_WINDOW_MS, self.finish_collect)
            if not (self.round_players - self.locked_out - set(self.presses)):
                self.finish_collect()
            elif first:
                self.play("hit")
                self.render()

    def false_start(self, idx):
        self.locked_out.add(idx)
        self.play("buzz")
        play_sound_effect("horse neigh")
        eligible = self.round_players - self.locked_out
        if not eligible:
            self.cancel("wait")
            self.void_round("Everyone false-started!", "Nobody kept their cool.")
        elif len(eligible) == 1:
            self.cancel("wait")
            self.resolve_round_win(next(iter(eligible)), by_default=True)
        else:
            names = ", ".join(self.players[i].name for i in sorted(self.locked_out))
            self.notice = f"False start!  Locked out: {names}"
            self.render()

    def finish_collect(self):
        self.cancel("collect")
        self.cancel("timeout")
        if self.presses:
            self.resolve_round_win(min(self.presses, key=lambda k: self.presses[k]))

    # ---------- results ----------
    def build_rows(self, default_winner=None):
        rows = []
        ordered = sorted(self.presses.items(), key=lambda kv: kv[1])
        best = ordered[0][1] if ordered else 0.0
        if default_winner is not None:
            rows.append(dict(idx=default_winner, rank="1", time="by default",
                             delta="", win=True))
        for rank, (idx, ms) in enumerate(ordered, 1):
            rows.append(dict(idx=idx, rank=str(rank), time=f"{ms:.0f} ms",
                             delta="" if rank == 1 else f"+{ms - best:.0f} ms",
                             win=(rank == 1)))
        for idx in sorted(self.locked_out):
            rows.append(dict(idx=idx, rank="-", time="FALSE START", delta="", win=False))
        skip = set(self.presses) | self.locked_out
        if default_winner is not None:
            skip.add(default_winner)
        for idx in sorted(self.round_players - skip):
            rows.append(dict(idx=idx, rank="-", time="too slow", delta="", win=False))
        for idx in range(len(self.players)):
            if idx not in self.round_players:
                rows.append(dict(idx=idx, rank="-", time="sitting out", delta="", win=False))
        return rows

    # ---------- slow-mo showdown (pixel duel scene) ----------
    def showdown_enabled(self):
        return self.arena is not None and self.settings.duel_anim

    def run_showdown(self, play, then):
        """Enter the SHOWDOWN state, start the animation, run `then` when it ends."""
        self.state = SHOWDOWN
        self.showdown_then = then
        self.render()
        play(self.end_showdown)

    def end_showdown(self):
        then, self.showdown_then = self.showdown_then, None
        if then:
            then()

    def skip_showdown(self):
        if self.state == SHOWDOWN and self.arena is not None:
            self.arena.skip()

    def resolve_round_win(self, winner, by_default=False):
        self.cancel_jobs()
        if self.showdown_enabled():
            loser = 1 - winner
            delta = None
            if not by_default and winner in self.presses and loser in self.presses:
                delta = self.presses[loser] - self.presses[winner]
            speed = SLOWMO[self.settings.slowmo]
            self.run_showdown(
                lambda done: self.need_arena().play_duel(winner, loser, delta, by_default, done, speed),
                lambda: self.commit_round_win(winner, by_default, quiet=True))
        else:
            self.commit_round_win(winner, by_default)

    def commit_round_win(self, winner, by_default=False, quiet=False):
        self.cancel_jobs()
        player = self.players[winner]
        player.score += 1
        for q in self.players:
            q.streak = q.streak + 1 if q is player else 0

        ordered = sorted(self.presses.items(), key=lambda kv: kv[1])
        if by_default:
            detail = "Everyone else false-started - wins by default!"
        elif len(ordered) >= 2:
            runner_up = self.players[ordered[1][0]].name
            margin = ordered[1][1] - ordered[0][1]
            detail = (f"Fastest: {ordered[0][1]:.0f} ms   |   "
                      f"Beat {runner_up} by {margin:.0f} ms")
        else:
            detail = f"Fastest: {ordered[0][1]:.0f} ms   |   Everyone else was too slow"

        report = dict(headline=f"{player.name} wins the round!", detail=detail,
                      rows=self.build_rows(winner if by_default else None), winner=winner)

        if self.sudden_death:
            self.end_match(winner, report, quiet)
            return
        self.round_log.append(winner)
        if len(self.round_log) >= self.total_slots:
            self.end_of_regulation(report, quiet)
            return
        leader = self.clinched_leader() if self.settings.early_clinch else None
        if leader is not None:
            report["detail"] += "\nMatch clinched - nobody can catch up!"
            self.end_match(leader, report, quiet)
        else:
            self.show_round_over(report, quiet)

    def clinched_leader(self):
        """Index of a player nobody can catch any more (lead bigger than rounds left), or None."""
        remaining = self.total_slots - len(self.round_log)
        ranked = sorted(self.players, key=lambda p: -p.score)
        if len(ranked) > 1 and ranked[0].score > ranked[1].score + remaining:
            return ranked[0].index
        return None

    def match_point_players(self):
        """Players who would win the whole match by winning the NEXT round."""
        if self.sudden_death or self.state == MATCH_OVER or len(self.players) < 2:
            return []
        after = self.total_slots - len(self.round_log) - 1  # rounds left after that one
        if after < 0 or (after > 0 and not self.settings.early_clinch):
            return []
        out = []
        for p in self.players:
            others = max(q.score for q in self.players if q is not p)
            if p.score + 1 > others + after:
                out.append(p.index)
        return out

    def end_of_regulation(self, report, quiet=False):
        top = max(p.score for p in self.players)
        leaders = [p.index for p in self.players if p.score == top]
        if len(leaders) == 1:
            self.end_match(leaders[0], report, quiet)
            return
        self.sudden_death = True
        self.sd_players = set(leaders)
        names = " vs ".join(self.players[i].name for i in leaders)
        report["detail"] += f"\nTied at {top}!  SUDDEN DEATH: {names}"
        self.show_round_over(report, quiet)

    def show_round_over(self, report, quiet=False):
        self.state = ROUND_OVER
        self.report = report
        self.play("win")
        self.render()
        self.root.update_idletasks()
        if self.players[report["winner"]].bot:
            play_sound_effect("oof")
        else:
            play_sound_effect("fanfare")
        if not quiet:  # the duel scene already shook the screen
            self.shake(8, 8)

    def end_match(self, winner, report, quiet=False):
        self.state = MATCH_OVER
        self.match_winner = winner
        standings = sorted(self.players, key=lambda p: -p.score)
        final = "   |   ".join(f"{p.name} {p.score}" for p in standings)
        report["headline"] = f"{self.players[winner].name} wins the match!"
        report["detail"] += f"\nFinal: {final}"
        self.report = report
        self.play("fanfare")
        self.render()
        self.root.update_idletasks()
        if self.players[winner].bot:
            play_sound_effect("womp womp")
        else:
            play_sound_effect("ultra fanfare")
        if not quiet:
            self.shake(14, 14)
        colors = self.theme["players"] + [self.theme["accent"]]
        self.launch_confetti([self.player_color(winner)] * 3 + colors)

    def void_round(self, headline, reason):
        self.cancel_jobs()
        if self.showdown_enabled():
            speed = SLOWMO[self.settings.slowmo]
            self.run_showdown(lambda done: self.need_arena().play_void(done, speed),
                              lambda: self.commit_void(headline, reason, quiet=True))
        else:
            self.commit_void(headline, reason)

    def commit_void(self, headline, reason, quiet=False):
        rows = self.build_rows()
        if self.sudden_death:
            detail = reason + "\nSudden death goes again!"
        else:
            self.round_log.append(VOID)
            self.total_slots += 1
            detail = reason + "\nThe round doesn't count - an extra round was added!"
        self.state = ROUND_OVER
        self.report = dict(headline=headline, detail=detail, rows=rows, winner=None)
        if not quiet:
            self.play("void")
        self.render()

    # ============================================================
    # Pause
    # ============================================================
    def open_pause(self):
        if self.overlay is not None or self.screen != "game":
            return
        if self.state in (GO, MATCH_OVER, SHOWDOWN):
            return
        self.cancel_jobs()
        self.paused_state = self.state
        self.build_overlay()
        self.root.update_idletasks()
        play_sound_effect("pause")

    def build_overlay(self):
        self.sync_font()
        if self.pixel:
            self.cur_bg, self.cur_fg = PANEL_BG, PANEL_FG
            panel = PixelPanel(self.stage, bg=PANEL_BG, edge=self.theme["accent"])
            panel.place(relx=0.5, rely=0.5, anchor="center")
            host = panel.body
            self.overlay = panel
        else:
            bg, fg = self.theme["idle"]
            self.cur_bg, self.cur_fg = bg, fg
            cover = tk.Frame(self.stage, bg=bg)
            cover.place(x=0, y=0, relwidth=1, relheight=1)
            host = cover
            self.overlay = cover
            self.root.configure(bg=bg)

        self.label(host, "PAUSED", 48, True).pack(pady=(30, 0), padx=60)
        self.label(host, self.round_text(), 16).pack(pady=(0, 16))
        s = self.settings
        entries = [
            ("Resume", self.resume, "primary"),
            ("Restart Match", self.restart_match, "secondary"),
            (f"Theme: {s.theme}", self.cycle_theme, "secondary"),
            (f"Sound: {'On' if s.sound else 'Off'}", self.toggle_sound, "secondary"),
            (f"Fullscreen: {'On' if s.fullscreen else 'Off'}", self.toggle_fullscreen, "secondary"),
            ("Main Menu", self.show_menu, "secondary"),
            ("Quit Game", self.root.destroy, "secondary"),
        ]
        for text, command, style in entries:
            self.btn(host, text, command, style, 15, width=18, pady=6).pack(pady=3)
        tk.Frame(host, height=18, bg=self.cur_bg).pack()

    def close_overlay(self):
        if self.overlay is not None:
            self.overlay.destroy()
            self.overlay = None

    def resume(self):
        if self.overlay is None:
            return
        self.close_overlay()
        previous = self.paused_state
        self.paused_state = None
        if previous in (COUNTDOWN, WAITING):
            self.begin_attempt("Round restarted after pause - fresh wait!")
        else:
            self.render()

    def restart_match(self):
        self.close_overlay()
        self.show_game(True)

    def cycle_theme(self):
        nxt = THEME_NAMES[(THEME_NAMES.index(self.settings.theme) + 1) % len(THEME_NAMES)]
        self.settings.theme = nxt
        self.refresh_game_ui()

    def toggle_sound(self):
        self.settings.sound = not self.settings.sound
        self.close_overlay()
        self.build_overlay()

    # ============================================================
    # Play modes: DUEL / SOLO, the More menu, outfit + arena picker
    # ============================================================
    def start_duel(self):
        self.mode = "duel"
        self.begin_play()

    def start_solo(self):
        self.mode = "solo"
        self.begin_play()

    def begin_play(self):
        two = self.mode == "solo" or self.settings.num_players == 2
        if self.pixel and two:
            self.show_picker()  # outfits + arena for one or two players
        else:
            self.show_game(True)

    def show_more(self):
        f = self.begin_screen("more", boxed=True)
        self.label(f, "MORE", 34 if self.pixel else 30, True).pack(pady=(14, 8), padx=70)
        fs = "On" if self.settings.fullscreen else "Off"
        entries = [
            ("Trainer", self.show_trainer, "primary"),
            ("Settings", self.show_settings, "secondary"),
            ("How to Play", self.show_howto, "secondary"),
            (f"Fullscreen: {fs}", self.toggle_fullscreen, "secondary"),
            ("Quit Game", self.root.destroy, "secondary"),
        ]
        for text, command, style in entries:
            self.btn(f, text, command, style, 16, width=18, pady=8).pack(pady=4)
        self.btn(f, "Back", self.show_menu, "secondary", 16, width=18, pady=8).pack(pady=(10, 14))

    # ---------- outfit + arena picker (Pixel theme) ----------
    @staticmethod
    def color_name(hex_color):
        return next((n for n, c in OUTFIT_COLORS if c == hex_color), "Custom")

    def picker_value(self, key):
        """Text shown for one picker row."""
        kind, slot = key
        if kind == "hat":
            return self.outfits[slot]["hat"]
        if kind == "face":
            return self.outfits[slot]["face"]
        if kind == "color":
            return self.color_name(self.outfits[slot]["color"])
        if kind == "arena":
            return self.settings.arena
        return self.settings.bot_level

    def picker_row(self, parent, title, key, on_step):
        row = tk.Frame(parent, bg=PANEL_BG)
        row.pack(pady=2, anchor="w")
        if title:
            self.label(row, title, 11, color=mix(PANEL_BG, PANEL_FG, 0.6), width=6,
                       anchor="w").pack(side="left")
        self.btn(row, "<", lambda: on_step(-1), "secondary", 12, padx=8, pady=4).pack(side="left")
        if key[0] == "color":
            sw = tk.Frame(row, width=12, height=12, bg=self.outfits[key[1]]["color"])
            sw.pack(side="left", padx=(6, 0))
            self.pick_swatch[key[1]] = sw
        val = self.label(row, self.picker_value(key), 13, True, width=13)
        val.pack(side="left", padx=2)
        self.pick_vals[key] = val
        self.btn(row, ">", lambda: on_step(1), "secondary", 12, padx=8, pady=4).pack(side="left")

    def picker_fighter_box(self, parent, slot, title):
        box = PixelPanel(parent, bg=PANEL_BG, edge=self.outfits[slot]["color"], thick=3, inset=10)
        self.pick_edges[slot] = box
        inner = box.body
        self.label(inner, title.upper(), 14, True).pack(pady=(0, 4))
        self.picker_row(inner, "HAT", ("hat", slot), lambda s: self.picker_step(slot, "hat", s))
        self.picker_row(inner, "COLOR", ("color", slot), lambda s: self.picker_step(slot, "color", s))
        self.picker_row(inner, "FACE", ("face", slot), lambda s: self.picker_step(slot, "face", s))
        if slot == 1 and self.mode == "solo":
            self.picker_row(inner, "LEVEL", ("bot", 1), self.picker_bot)
        return box

    def show_picker(self):
        f = self.begin_screen("picker")
        solo = self.mode == "solo"
        self.pick_vals, self.pick_swatch, self.pick_edges = {}, {}, {}
        panel = PixelPanel(f, bg=PANEL_BG, edge=PX_SLATE)
        panel.pack(side="bottom", pady=(0, 14))
        body = panel.body
        self.label(body, "CHOOSE YOUR FIGHTERS AND ARENA", 16, True,
                   self.theme["accent"]).pack(pady=(8, 6))
        cols = tk.Frame(body, bg=PANEL_BG)
        cols.pack(padx=12)
        n0 = self.names[0].strip() or "Player 1"
        n1 = "Bot" if solo else (self.names[1].strip() or "Player 2")
        self.picker_fighter_box(cols, 0, n0).grid(row=0, column=0, padx=8, sticky="n")
        mid = tk.Frame(cols, bg=PANEL_BG)
        mid.grid(row=0, column=1, padx=8, sticky="n")
        self.label(mid, "ARENA", 14, True).pack(pady=(4, 6))
        self.picker_row(mid, "", ("arena", 0), self.picker_arena)
        self.picker_fighter_box(cols, 1, n1).grid(row=0, column=2, padx=8, sticky="n")
        foot = tk.Frame(body, bg=PANEL_BG)
        foot.pack(pady=(10, 10))
        self.btn(foot, "Start", lambda: self.show_game(True), "primary", 20, padx=30,
                 pady=8, width=8).pack(side="left", padx=8)
        self.btn(foot, "Back", self.show_menu, "secondary", 16, padx=20, pady=8,
                 width=6).pack(side="left", padx=8)

        self.root.update_idletasks()
        panel_h = panel.winfo_reqheight()
        bd = self.bd
        bd.ground_fn = lambda width, height: height - panel_h - 14 - 70
        self.menu_arena = DuelArena(bd, self.outfits)
        self.menu_arena.show_ready("SOLO" if solo else "DUEL", self.theme["accent"], 10, top=70)
        bd.apply()

    def picker_step(self, slot, key, step):
        if key == "color":
            opts = [c for _n, c in OUTFIT_COLORS]
        else:
            opts = OUTFIT_HATS if key == "hat" else OUTFIT_FACES
        cur = self.outfits[slot][key]
        i = opts.index(cur) if cur in opts else 0
        for _ in range(len(opts)):
            i = (i + step) % len(opts)
            if key != "color" or opts[i] != self.outfits[1 - slot]["color"]:
                break  # never let both fighters share a color
        self.outfits[slot][key] = opts[i]
        self.picker_refresh()

    def picker_arena(self, step):
        i = (ARENA_NAMES.index(self.settings.arena) + step) % len(ARENA_NAMES)
        self.settings.arena = ARENA_NAMES[i]
        self.bd.set_arena(self.settings.arena)
        self.picker_refresh()

    def picker_bot(self, step):
        names = list(BOT_LEVELS)
        i = (names.index(self.settings.bot_level) + step) % len(names)
        self.settings.bot_level = names[i]
        self.picker_refresh()

    def picker_refresh(self):
        for key, lbl in self.pick_vals.items():
            lbl.set(text=self.picker_value(key))
        for slot, sw in self.pick_swatch.items():
            sw.configure(bg=self.outfits[slot]["color"])
        for slot, box in self.pick_edges.items():
            box.set_edge(self.outfits[slot]["color"])
        if self.menu_arena is not None:
            self.menu_arena.redraw()

    # ---------- the bot (Solo mode) ----------
    def bot_index(self):
        for p in self.players:
            if p.bot:
                return p.index
        return None

    def plan_bot_false_start(self, wait_ms):
        """Now and then the bot gets jumpy and fires early (harder bots are calmer)."""
        b = self.bot_index()
        if b is None or b not in self.round_players:
            return
        if random.random() < BOT_LEVELS[self.settings.bot_level][2]:
            self.schedule("bot_fs", int(wait_ms * random.uniform(0.35, 0.95)),
                          lambda: self.player_press(b))

    def plan_bot_press(self):
        """Schedule the bot's reaction to GO using its level's average reaction time."""
        b = self.bot_index()
        if b is None or b not in self.round_players:
            return
        mean, sd, _fs = BOT_LEVELS[self.settings.bot_level]
        self.schedule("bot", int(max(110.0, random.gauss(mean, sd))), lambda: self.player_press(b))

    # ============================================================
    # Trainer: fast reaction drills with a coach and a click feed
    # ============================================================
    def show_trainer(self):
        f = self.begin_screen("trainer")
        pix = self.pixel
        self.tr_trials = []
        self.tr_state = "intro"
        self.tr_paused = False
        self.tr_t0 = 0.0
        bg, fg = (PANEL_BG, PANEL_FG) if pix else self.theme["idle"]
        accent = self.theme["accent"]

        top_body: tk.Frame
        if pix:
            top_panel = PixelPanel(f, bg=bg, edge=PX_SLATE)
            top_panel.pack(side="top", fill="x", padx=12, pady=(12, 0))
            top_body = top_panel.body
        else:
            top_body = tk.Frame(f, bg=bg)
            top_body.pack(side="top", fill="x", padx=14, pady=(12, 0))
        TextLabel(top_body, "TRAINER", 24, True, accent, bg, pix).pack(pady=(4, 0))
        hint = f"press SPACE, {key_label(self.keys[0])} or click when it turns GREEN"
        TextLabel(top_body, hint, 12, False, mix(bg, fg, 0.6), bg, pix).pack()
        chips = tk.Frame(top_body, bg=bg)
        chips.pack(pady=(4, 6))
        self.tr_stat = {}
        for key, title in (("trials", "TRIALS"), ("best", "BEST"), ("avg", "AVERAGE"),
                           ("last5", "LAST 5"), ("trend", "TREND"), ("errors", "ERRORS")):
            chip: tk.Frame
            if pix:
                stat_panel = PixelPanel(chips, bg=mix(bg, fg, 0.08), edge=PX_SLATE, thick=3, inset=3)
                chip, host = stat_panel, stat_panel.body
            else:
                chip = tk.Frame(chips, bg=mix(bg, fg, 0.12), highlightthickness=2,
                                highlightbackground=PX_SLATE)
                host = chip
            chip.pack(side="left", padx=4)
            chip_bg = mix(bg, fg, 0.08 if pix else 0.12)
            TextLabel(host, title, 10, False, mix(bg, fg, 0.6), chip_bg, pix).pack(padx=8, pady=(3, 0))
            val = TextLabel(host, "--", 20, True, fg, chip_bg, pix, width=8)
            val.pack(padx=8, pady=(0, 3))
            self.tr_stat[key] = val

        bottom_h = 236
        bottom_host: tk.Frame
        if pix:
            bottom_panel = PixelPanel(f, bg=bg, edge=PX_SLATE)
            bottom_panel.configure(width=940, height=bottom_h)
            bottom_panel.pack_propagate(False)
            bottom_panel.pack(side="bottom", pady=(0, 12))
            bottom_host = bottom_panel.body
        else:
            bottom_frame = tk.Frame(f, bg=bg, height=bottom_h)
            bottom_frame.pack_propagate(False)
            bottom_frame.pack(side="bottom", fill="x", padx=14, pady=(0, 12))
            bottom_host = bottom_frame
        self.trainer_build_bottom(bottom_host, bg, fg, pix)

        if pix:
            bd = self.bd
            trainer_arena = DuelArena(bd, self.outfits, sfx=self.play, shake=self.shake)
            self.arena = trainer_arena
            trainer_arena.trainer_begin()
            bd.ground_fn = lambda width, height: height - bottom_h - 12 - 70
            bd.canvas.bind("<Button-1>", lambda _e: self.trainer_press())
            bd.apply()
        else:
            self.tr_box = tk.Frame(f, bg=self.theme["idle"][0], cursor=HAND)
            self.tr_box.pack(fill="both", expand=True, padx=14, pady=10)
            self.tr_box_lbl = TextLabel(self.tr_box, "GET READY", 64, True, self.theme["idle"][1],
                                        self.theme["idle"][0], False)
            self.tr_box_lbl.pack(expand=True)
            for w in (self.tr_box, self.tr_box_lbl):
                w.bind("<Button-1>", lambda _e: self.trainer_press())
        self.trainer_refresh()
        self.trainer_start()

    def trainer_build_bottom(self, parent, bg, fg, pix):
        accent = self.theme["accent"]
        wrap = tk.Frame(parent, bg=bg)
        wrap.pack(fill="both", expand=True, padx=10, pady=6)
        left = tk.Frame(wrap, bg=bg)
        left.pack(side="left", fill="both", expand=True)
        right = tk.Frame(wrap, bg=bg)
        right.pack(side="left", fill="both", expand=True, padx=(14, 0))

        TextLabel(left, "CLICK FEED", 14, True, accent, bg, pix).pack(anchor="w")
        self.tr_rows = []
        for _ in range(5):
            lbl = TextLabel(left, "", 14, False, fg, bg, pix, width=30, anchor="w")
            lbl.pack(anchor="w")
            self.tr_rows.append(lbl)
        self.tr_strip = tk.Canvas(left, height=48, width=420, highlightthickness=0, bg=bg)
        self.tr_strip.pack(anchor="w", pady=(6, 0))

        TextLabel(right, "COACH", 14, True, accent, bg, pix).pack(anchor="w")
        self.tr_rating = TextLabel(right, "", 14, True, fg, bg, pix, anchor="w")
        self.tr_rating.pack(anchor="w")
        self.tr_coach = TextLabel(right, "", 14, False, fg, bg, pix, wraplength=390,
                                  justify="left", anchor="w")
        self.tr_coach.pack(anchor="w", pady=(2, 4))
        button_row = tk.Frame(right, bg=bg)
        button_row.pack(side="bottom", anchor="w")
        self.tr_btn_pause = self.btn(button_row, "Pause", self.trainer_toggle_pause, "secondary", 11,
                                     padx=12, pady=6)
        self.tr_btn_pause.pack(side="left", padx=2)
        self.btn(button_row, "Reset", self.trainer_reset, "secondary", 11, padx=12,
                 pady=6).pack(side="left", padx=2)
        self.tr_btn_tempo = self.btn(button_row, f"Tempo: {self.settings.trainer_tempo}",
                                     self.trainer_cycle_tempo, "secondary", 11, padx=12, pady=6)
        self.tr_btn_tempo.pack(side="left", padx=2)
        self.btn(button_row, "Back", self.show_more, "primary", 11, padx=12, pady=6).pack(side="left", padx=2)

    # ---------- the drill loop ----------
    def trainer_tempo(self):
        return TRAINER_TEMPOS[self.settings.trainer_tempo]

    def trainer_start(self):
        self.tr_state = "intro"
        self.trainer_visual("intro")
        self.schedule("tr_next", 900, self.trainer_arm)

    def trainer_arm(self):
        self.tr_state = "arm"
        low, high, _cool = self.trainer_tempo()
        self.trainer_visual("arm")
        self.schedule("tr_signal", random.randint(low, high), self.trainer_signal)

    def trainer_signal(self):
        self.tr_state = "signal"
        self.trainer_visual("signal")
        self.root.update_idletasks()
        self.tr_t0 = time.perf_counter()
        self.schedule("tr_timeout", 1300, self.trainer_timeout)
        self.root.after(1, lambda: self.play("go"))

    def trainer_press(self):
        if self.screen != "trainer":
            return
        if self.tr_state == "arm":
            self.cancel("tr_signal")
            self.trainer_record("early", None)
        elif self.tr_state == "signal":
            ms = (time.perf_counter() - self.tr_t0) * 1000.0
            self.cancel("tr_timeout")
            self.trainer_record("hit", ms)

    def trainer_timeout(self):
        if self.tr_state == "signal":
            self.trainer_record("miss", None)

    def trainer_record(self, kind, ms):
        prev = next((t["ms"] for t in reversed(self.tr_trials) if t["kind"] == "hit"), None)
        delta = ms - prev if (ms is not None and prev is not None) else None
        trial = dict(kind=kind, ms=ms, delta=delta)
        self.tr_trials.append(trial)
        self.tr_state = "cool"
        self.trainer_visual(kind, trial)
        self.trainer_refresh()
        cool = {"hit": 700, "early": 1000, "miss": 900}[kind] * self.trainer_tempo()[2]
        self.schedule("tr_next", int(cool), self.trainer_arm)

    def trainer_key(self, key):
        if key in ("space", "return", self.keys[0]):
            self.trainer_press()
        elif key == "p":
            self.trainer_toggle_pause()
        elif key == "escape":
            self.show_more()

    def trainer_toggle_pause(self):
        if self.screen != "trainer":
            return
        if self.tr_paused:
            self.tr_paused = False
            self.tr_btn_pause.set_text("Pause")
            self.trainer_start()
        else:
            self.tr_paused = True
            for name in ("tr_next", "tr_signal", "tr_timeout"):
                self.cancel(name)
            self.tr_state = "paused"
            self.tr_btn_pause.set_text("Resume")
            self.trainer_visual("paused")

    def trainer_reset(self):
        self.tr_trials = []
        self.tr_paused = False
        self.tr_btn_pause.set_text("Pause")
        for name in ("tr_next", "tr_signal", "tr_timeout"):
            self.cancel(name)
        self.trainer_refresh()
        self.trainer_start()

    def trainer_cycle_tempo(self):
        names = list(TRAINER_TEMPOS)
        self.settings.trainer_tempo = names[(names.index(self.settings.trainer_tempo) + 1) % len(names)]
        self.tr_btn_tempo.set_text(f"Tempo: {self.settings.trainer_tempo}")

    # ---------- visuals ----------
    GOOD_COLOR = "#5de07b"  # faster than the last click
    BAD_COLOR = "#ff5a5f"  # slower / early / missed

    def trainer_visual(self, kind, trial=None):
        accent = self.theme["accent"]
        text, color, scale = "", PX_WHITE, 7
        palette = "idle"
        if kind == "intro":
            text, scale = "GET READY", 7
        elif kind == "paused":
            text, scale = "PAUSED", 8
        elif kind == "arm":
            text, palette = "WAIT...", "wait"
        elif kind == "signal":
            text, color, scale, palette = "GO!", accent, 9, "go"
        elif kind == "hit":
            ms = trial["ms"]
            text, scale = f"{ms:.0f} MS", 8
            color = (self.GOOD_COLOR if trial["delta"] < 0 else self.BAD_COLOR) if trial[
                                                                                       "delta"] is not None else accent
        elif kind == "early":
            text, color = "TOO EARLY!", self.BAD_COLOR
        elif kind == "miss":
            text, color = "TOO SLOW!", self.BAD_COLOR
        if self.pixel:
            self.bd.set_palette(palette)
            a = self.need_arena()
            if kind == "arm" or kind == "intro":
                a.trainer_arm()
            elif kind == "signal":
                a.trainer_signal()
            elif kind == "hit":
                a.trainer_shoot(True)
                self.play("hit")
            elif kind == "early":
                a.trainer_shoot(False)
                self.play("buzz")
            elif kind == "miss":
                a.trainer_miss()
                self.play("buzz")
            a.trainer_text(text, color, scale)
        else:
            key = {"wait": "wait", "go": "go"}.get(palette, "idle")
            box_bg, box_fg = self.theme[key]
            if kind in ("hit", "early", "miss"):
                box_bg, box_fg = self.theme["result"]
            self.tr_box.configure(bg=box_bg)
            self.tr_box_lbl.set(text=text, bg=box_bg, fg=color if kind in ("hit", "early", "miss") else box_fg,
                                size=64)
            if kind == "signal":
                pass
            elif kind in ("early", "miss"):
                self.play("buzz")
            elif kind == "hit":
                self.play("hit")

    def trainer_stats(self) -> dict[str, Any]:
        hits = [t["ms"] for t in self.tr_trials if t["kind"] == "hit"]
        return {
            "trials": len(self.tr_trials),
            "hits": hits,
            "errors": sum(1 for t in self.tr_trials if t["kind"] != "hit"),
            "best": min(hits) if hits else None,
            "avg": sum(hits) / len(hits) if hits else None,
            "last5": sum(hits[-5:]) / len(hits[-5:]) if hits else None,
            "trend": (sum(hits[-5:]) / 5 - sum(hits[-10:-5]) / 5) if len(hits) >= 10 else None,
        }

    def trainer_refresh(self):
        st = self.trainer_stats()
        fg = PANEL_FG if self.pixel else self.theme["idle"][1]

        def show(key, text, color=None):
            self.tr_stat[key].set(text=text, fg=color or fg)

        show("trials", str(st["trials"]))
        show("best", f"{st['best']:.0f} ms" if st["best"] is not None else "--",
             self.GOOD_COLOR if st["best"] is not None else None)
        show("avg", f"{st['avg']:.0f} ms" if st["avg"] is not None else "--")
        show("last5", f"{st['last5']:.0f} ms" if st["last5"] is not None else "--")
        if st["trend"] is None:
            show("trend", "--")
        else:
            show("trend", f"{st['trend']:+.0f} ms", self.GOOD_COLOR if st["trend"] < 0 else self.BAD_COLOR)
        show("errors", str(st["errors"]), self.BAD_COLOR if st["errors"] else None)

        # click feed: newest first, green when faster than the previous click, red when slower
        recent = list(enumerate(self.tr_trials, 1))[-5:][::-1]
        for row_lbl, item in zip(self.tr_rows, recent + [None] * (5 - len(recent))):
            if item is None:
                row_lbl.set(text="", fg=fg)
                continue
            n, t = item
            if t["kind"] == "early":
                row_lbl.set(text=f"#{n:<3} TOO EARLY", fg=self.BAD_COLOR)
            elif t["kind"] == "miss":
                row_lbl.set(text=f"#{n:<3} MISSED", fg=self.BAD_COLOR)
            elif t["delta"] is None:
                row_lbl.set(text=f"#{n:<3} {t['ms']:>4.0f} MS      --", fg=fg)
            else:
                good = t["delta"] < 0
                row_lbl.set(text=f"#{n:<3} {t['ms']:>4.0f} MS   {t['delta']:>+5.0f} MS",
                            fg=self.GOOD_COLOR if good else self.BAD_COLOR)
        self.trainer_draw_strip()
        msg, rating = self.trainer_coach(st)
        self.tr_coach.set(text=msg)
        self.tr_rating.set(text=rating[0], fg=rating[1])

    def trainer_draw_strip(self):
        c = self.tr_strip
        c.delete("all")
        trials = self.tr_trials[-30:]
        bg = c.cget("bg")
        for i, t in enumerate(trials):
            x0 = 4 + i * 14
            if t["kind"] == "hit":
                h = 6 + clamp((t["ms"] - 120) / 480.0, 0.0, 1.0) * 38  # taller bar = slower
                color = PX_GREY if t["delta"] is None else (self.GOOD_COLOR if t["delta"] < 0 else self.BAD_COLOR)
                c.create_rectangle(x0, 46 - h, x0 + 10, 46, fill=color, outline="")
            else:
                c.create_rectangle(x0, 8, x0 + 10, 46, fill=bg, outline=self.BAD_COLOR, width=2)
                c.create_line(x0 + 2, 12, x0 + 8, 42, fill=self.BAD_COLOR, width=2)
                c.create_line(x0 + 2, 42, x0 + 8, 12, fill=self.BAD_COLOR, width=2)

    COACH_TIPS = [
        "Rest your finger lightly on the key. Don't hover high above it.",
        "Relax your shoulders and wrist. Tension makes you slower.",
        "React, don't predict. Wait for GO instead of guessing the timing.",
        "Breathe out as the target pops up. A calm hand is a fast hand.",
        "Look at the target, not around it. Soft focus catches changes faster.",
    ]

    def trainer_coach(self, st):
        """A coaching line plus a rating badge, based on the session so far."""
        hits, n = st["hits"], len(self.tr_trials)
        avg = st["last5"]
        rating = ("WARMING UP", PANEL_FG if self.pixel else self.theme["idle"][1])
        if avg is not None:
            for limit, name in ((200, "ELITE"), (250, "GREAT"), (300, "GOOD"), (400, "OKAY")):
                if avg < limit:
                    rating = (f"RATING: {name}", self.GOOD_COLOR if limit <= 250 else self.theme["accent"])
                    break
            else:
                rating = ("RATING: KEEP GOING", self.BAD_COLOR)
        if not self.tr_trials:
            return "Wait for the target to pop up, then hit it as fast as you can. I'll coach as you go!", rating
        last = self.tr_trials[-1]
        if last["kind"] == "early":
            return "TOO EARLY! Don't guess. Wait until the target actually pops up.", rating
        if last["kind"] == "miss":
            return "MISSED IT. Eyes on the target and finger ready. Reset and go again.", rating
        ms = last["ms"]
        if len(hits) >= 10 and len(hits) % 10 == 0:
            tr = st["trend"]
            word = "faster" if tr < 0 else "slower"
            return (f"CHECKPOINT: your last 5 are {abs(tr):.0f} ms {word} than the 5 before. "
                    + ("Great progress, keep it up!" if tr < 0 else "Breathe, relax, reset your focus."), rating)
        if ms <= st["best"] and len(hits) > 1:
            return f"NEW BEST! {ms:.0f} ms. Lock that feeling in.", rating
        up = 0
        for t in reversed(self.tr_trials):
            if t["kind"] == "hit" and t["delta"] is not None and t["delta"] < 0:
                up += 1
            else:
                break
        down = 0
        for t in reversed(self.tr_trials):
            if t["kind"] == "hit" and t["delta"] is not None and t["delta"] > 0:
                down += 1
            else:
                break
        if up >= 3:
            return f"{up} FASTER IN A ROW! Keep that rhythm.", rating
        if down >= 3:
            return "You're slipping. Breathe out, shake out your hand, then reset.", rating
        if st["avg"] is not None and len(hits) >= 3:
            if ms < st["avg"] - 30:
                return f"NICE! {st['avg'] - ms:.0f} ms faster than your average.", rating
            if ms > st["avg"] + 80:
                return "SLOW ONE. Stay locked on the target. Don't wait for it.", rating
        return self.COACH_TIPS[n % len(self.COACH_TIPS)], rating

    # ============================================================
    # Keyboard
    # ============================================================
    def on_key_release(self, event):
        self.down.discard(event.keysym.lower())

    def on_key_press(self, event):
        key = event.keysym.lower()
        try:
            focused = self.root.focus_get()
        except KeyError:
            focused = None
        if isinstance(focused, tk.Entry):
            if key in ("return", "escape"):
                self.root.focus_set()
            return
        if key in self.down:  # auto-repeat from a held key
            return
        self.down.add(key)

        if self.rebind_target is not None:
            self.handle_rebind(key)
        elif self.screen == "game":
            self.game_key(key)
        elif self.screen == "trainer":
            self.trainer_key(key)
        elif key == "escape" and self.screen in ("settings", "howto"):
            self.show_more()
        elif key == "escape" and self.screen in ("more", "picker"):
            self.show_menu()

    def game_key(self, key):
        if self.overlay is not None:
            if key in ("escape", "space"):
                self.resume()
            return
        if key == "escape":
            self.open_pause()
        elif key == "space":
            self.primary_action()
        else:
            for p in self.players:
                if p.key == key:
                    self.player_press(p.index)
                    break

    # ============================================================
    # Effects: screen shake + confetti
    # ============================================================
    def shake(self, strength, steps):
        if not self.settings.shake:
            return
        if self.shake_job is not None:
            self.root.after_cancel(self.shake_job)
            self.shake_job = None

        def step(i):
            if i >= steps:
                self.stage.place_configure(x=0, y=0)
                self.shake_job = None
                return
            amp = max(1, int(strength * (1 - i / steps)))
            self.stage.place_configure(x=random.randint(-amp, amp),
                                       y=random.randint(-amp, amp))
            self.shake_job = self.root.after(28, lambda: step(i + 1))

        step(0)

    def launch_confetti(self, colors, count=70):
        self.stop_confetti()
        self.root.update_idletasks()
        width = max(200, self.stage.winfo_width())
        for _ in range(count):
            size = random.randint(6, 12)
            x = random.uniform(0, width - size)
            y = random.uniform(-350, -10)
            vx = random.uniform(-1.5, 1.5)
            vy = random.uniform(3.0, 7.0)
            piece = tk.Frame(self.stage, bg=random.choice(colors))
            piece.place(x=int(x), y=int(y), width=size, height=size)
            self.confetti.append([piece, x, y, vx, vy])
        self.animate_confetti()

    def animate_confetti(self):
        height = self.stage.winfo_height()
        alive = []
        for piece in self.confetti:
            widget, x, y, vx, vy = piece
            x += vx
            y += vy
            if y > height:
                widget.destroy()
                continue
            widget.place_configure(x=int(x), y=int(y))
            piece[1], piece[2] = x, y
            alive.append(piece)
        self.confetti = alive
        self.confetti_job = self.root.after(30, self.animate_confetti) if alive else None

    def stop_confetti(self):
        if self.confetti_job is not None:
            self.root.after_cancel(self.confetti_job)
            self.confetti_job = None
        self.confetti = []


def main():
    root = tk.Tk()
    ReactionDuel(root)
    # Make sure the window comes to the front when launched from a terminal
    root.lift()
    root.attributes("-topmost", True)
    root.after(300, lambda: root.attributes("-topmost", False))
    root.focus_force()
    root.mainloop()


#Woody's PPR
def play_sound_effect(effect):

    if sys.platform != "win32":
        return

    if effect == "fanfare":
        notes = [523, 659, 784, 1047]
        note_ms = 100
    elif effect == "oof":
        notes = [247,196]
        note_ms = 90 
    elif effect == "ultra fanfare":
        notes = [523, 659, 784, 1047, 784, 1047, 1319]
        note_ms = 120
    elif effect == "womp womp":
        notes = [247, 196]
        note_ms = 400
    elif effect == "horse neigh":
        notes = [1760, 1568, 1760, 1568, 1319, 1568, 1319,1047 ]
        note_ms = 50
    elif effect == "gunshot":
        notes = [2500, 1800, 1200 ]
        note_ms = 20
    elif effect == "countdown":
        notes = [880]
        note_ms = 150
    elif effect == "too slow":
        notes = [880,784,659,587]
        note_ms = 200
    elif effect == "pause":
        notes = [784,523]
        note_ms = 80
    elif effect == "bullet hit":
        notes = [1800,400,200]
        note_ms = 20
    else:
        notes = []
        note_ms = 0
    for note in notes:
        winsound.Beep(note, note_ms)
        


if __name__ == "__main__":
    main()