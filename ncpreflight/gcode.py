"""NC program (G-code) parser for 3-axis milling.

Turns program text into a list of geometric segments with the modal state
(feed, spindle, tool) attached. Covers the ISO 6983 core used by most 3-axis
programs: G0/G1/G2/G3, G4, G17-G19, G20/G21, G90/G91, F, S, T, M3/M4/M5/M6,
M8/M9, M2/M30. Anything else is reported as a note instead of being guessed.

Lengths are millimetres, feeds mm/min, spindle speed rev/min.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

WORD_RE = re.compile(r"([A-Za-z])\s*([-+]?(?:\d+\.?\d*|\.\d+))")
PAREN_RE = re.compile(r"\([^)]*\)")
META_RE = re.compile(r"\(\s*([A-Z_]+)\s*=\s*([^)]+?)\s*\)")
INCH = 25.4

# plane -> (first axis, second axis, linear axis) as indices into XYZ
PLANES = {17: (0, 1, 2), 18: (2, 0, 1), 19: (1, 2, 0)}
IGNORED_G = {40, 43, 49, 53, 54, 55, 56, 57, 58, 59, 61, 64, 94, 98, 99, 80}
UNSUPPORTED_G = {41: "cutter radius compensation is not simulated",
                 42: "cutter radius compensation is not simulated",
                 81: "canned drilling cycle is not expanded",
                 82: "canned drilling cycle is not expanded",
                 83: "canned peck-drilling cycle is not expanded",
                 84: "tapping cycle is not expanded",
                 93: "inverse-time feed is not supported",
                 95: "feed per revolution is not supported"}
KNOWN_M = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 30}


@dataclass
class Segment:
    """One block's worth of motion, or a dwell / tool change event."""
    line: int                 # 1-based line number in the source text
    kind: str                 # rapid | linear | arc | dwell | toolchange
    start: np.ndarray
    end: np.ndarray
    length: float = 0.0       # path length in mm
    feed: float = 0.0         # programmed feed, mm/min (0 for rapids)
    rpm: float = 0.0          # spindle speed while this block runs
    spindle_on: bool = False
    tool: int = 0
    coolant: bool = False
    dwell: float = 0.0        # seconds
    radius: float = 0.0       # arc radius, mm
    u_in: Optional[np.ndarray] = None   # unit tangent at the start
    u_out: Optional[np.ndarray] = None  # unit tangent at the end
    center: Optional[np.ndarray] = None
    sweep: float = 0.0        # signed arc angle in its plane, rad
    plane: int = 17

    @property
    def is_move(self) -> bool:
        return self.kind in ("rapid", "linear", "arc")

    @property
    def is_cut(self) -> bool:
        return self.kind in ("linear", "arc")


@dataclass
class Note:
    """Something the parser could not interpret or chose to ignore."""
    line: int
    code: str
    message: str


@dataclass
class Program:
    segments: list[Segment] = field(default_factory=list)
    notes: list[Note] = field(default_factory=list)
    meta: dict[str, str] = field(default_factory=dict)
    n_lines: int = 0
    units_declared: bool = False
    distance_mode_declared: bool = False
    ended: bool = False

    @property
    def moves(self) -> list[Segment]:
        return [s for s in self.segments if s.is_move]

    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        pts = [s.start for s in self.moves] + [s.end for s in self.moves]
        if not pts:
            z = np.zeros(3)
            return z, z
        arr = np.vstack(pts)
        return arr.min(axis=0), arr.max(axis=0)


def _arc(start, end, plane, cw, offsets, r_word, line, notes):
    """Return (length, radius, u_in, u_out, center, sweep) or None if invalid."""
    a, b, c = PLANES[plane]
    sa, sb = start[a], start[b]
    ea, eb = end[a], end[b]
    if r_word is not None:
        d = math.hypot(ea - sa, eb - sb)
        r = abs(r_word)
        if d < 1e-9:
            notes.append(Note(line, "ARC_R_FULL", "R-format arc with identical start and end is undefined"))
            return None
        if d > 2 * r + 1e-6:
            notes.append(Note(line, "ARC_RADIUS", f"arc radius {r:g} is too small for a chord of {d:.3f} mm"))
            return None
        h = math.sqrt(max(r * r - d * d / 4, 0.0))
        dx, dy = (ea - sa) / d, (eb - sb) / d
        side = 1.0 if cw else -1.0
        if r_word < 0:
            side = -side
        ca = (sa + ea) / 2 + side * h * dy
        cb = (sb + eb) / 2 - side * h * dx
    else:
        ca, cb = sa + offsets[a], sb + offsets[b]
        r = math.hypot(sa - ca, sb - cb)
        r_end = math.hypot(ea - ca, eb - cb)
        if r < 1e-9:
            notes.append(Note(line, "ARC_RADIUS", "arc has zero radius"))
            return None
        if abs(r - r_end) > max(0.01, 0.001 * r):
            notes.append(Note(line, "ARC_RADIUS",
                              f"arc start radius {r:.4f} and end radius {r_end:.4f} differ"))
    t1 = math.atan2(sb - cb, sa - ca)
    t2 = math.atan2(eb - cb, ea - ca)
    sweep = t2 - t1
    full = math.hypot(ea - sa, eb - sb) < 1e-9
    if cw:
        if sweep >= -1e-12 or full:
            sweep -= 2 * math.pi
        if full:
            sweep = -2 * math.pi
    else:
        if sweep <= 1e-12 or full:
            sweep += 2 * math.pi
        if full:
            sweep = 2 * math.pi
    arc_len = abs(sweep) * r
    dc = end[c] - start[c]
    length = math.hypot(arc_len, dc)
    sign = -1.0 if cw else 1.0

    def tangent(theta):
        t = np.zeros(3)
        t[a] = -math.sin(theta) * sign * arc_len
        t[b] = math.cos(theta) * sign * arc_len
        t[c] = dc
        n = np.linalg.norm(t)
        return t / n if n > 0 else t

    center = np.array(start, dtype=float)
    center[a], center[b] = ca, cb
    return length, r, tangent(t1), tangent(t2), center, sweep


def parse(text: str) -> Program:
    """Parse NC program text into a Program."""
    prog = Program()
    pos = np.zeros(3)
    motion = None            # modal motion group: 0, 1, 2, 3
    plane = 17
    scale = 1.0              # 1 for mm, 25.4 for inch
    absolute = True
    feed = 0.0
    rpm = 0.0
    spindle_on = False
    coolant = False
    tool = 0
    pending_tool = 0

    lines = text.splitlines()
    prog.n_lines = len(lines)
    for ln, raw in enumerate(lines, start=1):
        for key, val in META_RE.findall(raw.upper()):
            prog.meta.setdefault(key, val.strip())
        body = PAREN_RE.sub(" ", raw)
        body = body.split(";", 1)[0].strip()
        if not body or body.startswith("%"):
            continue
        if body.startswith("/"):          # block delete: treat as active
            body = body[1:]
        words = [(w.upper(), float(v)) for w, v in WORD_RE.findall(body)]
        leftover = WORD_RE.sub("", body).strip()
        if leftover:
            prog.notes.append(Note(ln, "UNPARSED", f"could not interpret '{leftover[:40]}'"))
        if not words:
            continue
        if words[0][0] == "O":            # program number
            continue

        vals: dict[str, float] = {}
        gcodes: list[float] = []
        mcodes: list[int] = []
        for w, v in words:
            if w == "G":
                gcodes.append(v)
            elif w == "M":
                mcodes.append(int(v))
            elif w == "N":
                continue
            else:
                vals[w] = v

        dwell_block = False
        home_block = False
        for g in gcodes:
            gi = int(g)
            if g != gi:
                prog.notes.append(Note(ln, "UNSUPPORTED", f"G{g:g} is not supported"))
            elif gi in (0, 1, 2, 3):
                motion = gi
            elif gi == 4:
                dwell_block = True
            elif gi in PLANES:
                plane = gi
            elif gi == 20:
                scale, prog.units_declared = INCH, True
            elif gi == 21:
                scale, prog.units_declared = 1.0, True
            elif gi == 90:
                absolute, prog.distance_mode_declared = True, True
            elif gi == 91:
                absolute, prog.distance_mode_declared = False, True
            elif gi == 28:
                home_block = True
            elif gi in UNSUPPORTED_G:
                prog.notes.append(Note(ln, "UNSUPPORTED", f"G{gi}: {UNSUPPORTED_G[gi]}"))
            elif gi not in IGNORED_G:
                prog.notes.append(Note(ln, "UNKNOWN", f"G{gi} is not recognised"))

        if "F" in vals:
            feed = vals["F"] * scale
        if "S" in vals:
            rpm = vals["S"]
        if "T" in vals:
            pending_tool = int(vals["T"])

        def base(kind, **kw):
            return Segment(line=ln, kind=kind, start=pos.copy(), end=pos.copy(), rpm=rpm,
                           spindle_on=spindle_on, tool=tool, coolant=coolant, **kw)

        for m in mcodes:
            if m in (3, 4):
                spindle_on = True
            elif m == 5:
                spindle_on = False
            elif m == 6:
                tool = pending_tool
                prog.segments.append(base("toolchange"))
            elif m in (7, 8):
                coolant = True
            elif m == 9:
                coolant = False
            elif m in (2, 30):
                prog.ended = True
            elif m not in KNOWN_M:
                prog.notes.append(Note(ln, "UNKNOWN", f"M{m} is not recognised"))

        if dwell_block:
            secs = vals.get("P", vals.get("X", vals.get("U", 0.0)))
            prog.segments.append(base("dwell", dwell=max(secs, 0.0)))
            continue
        if home_block:
            prog.notes.append(Note(ln, "HOME", "G28 reference return is not simulated"))
            continue

        has_axis = any(k in vals for k in "XYZ")
        if not has_axis:
            continue
        if motion is None:
            prog.notes.append(Note(ln, "NO_MOTION_MODE", "axis words before any G0/G1/G2/G3"))
            continue

        target = pos.copy()
        for i, ax in enumerate("XYZ"):
            if ax in vals:
                target[i] = vals[ax] * scale if absolute else pos[i] + vals[ax] * scale

        seg = base("rapid" if motion == 0 else "linear" if motion == 1 else "arc")
        seg.end = target.copy()
        seg.plane = plane
        if motion in (0, 1):
            d = target - pos
            seg.length = float(np.linalg.norm(d))
            if seg.length > 0:
                seg.u_in = seg.u_out = d / seg.length
            seg.feed = feed if motion == 1 else 0.0
        else:
            offsets = np.array([vals.get("I", 0.0), vals.get("J", 0.0), vals.get("K", 0.0)]) * scale
            r_word = vals["R"] * scale if "R" in vals else None
            res = _arc(pos, target, plane, motion == 2, offsets, r_word, ln, prog.notes)
            if res is None:
                pos = target
                continue
            seg.length, seg.radius, seg.u_in, seg.u_out, seg.center, seg.sweep = res
            seg.feed = feed
        if seg.length > 0:
            prog.segments.append(seg)
        pos = target
    return prog


def polyline(seg: Segment, max_step_deg: float = 6.0) -> np.ndarray:
    """Points along a segment, for drawing. Arcs are sampled; lines give two points."""
    if seg.kind != "arc" or seg.center is None:
        return np.vstack([seg.start, seg.end])
    a, b, c = PLANES[seg.plane]
    n = max(2, int(abs(math.degrees(seg.sweep)) / max_step_deg) + 1)
    t0 = math.atan2(seg.start[b] - seg.center[b], seg.start[a] - seg.center[a])
    ts = t0 + np.linspace(0.0, seg.sweep, n)
    pts = np.zeros((n, 3))
    pts[:, a] = seg.center[a] + seg.radius * np.cos(ts)
    pts[:, b] = seg.center[b] + seg.radius * np.sin(ts)
    pts[:, c] = np.linspace(seg.start[c], seg.end[c], n)
    return pts
