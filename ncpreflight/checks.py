"""Rule-based program checks ("pre-flight").

Each rule is deterministic and explains itself. This is a product feature, not
a research claim: the rules catch the faults their author thought of. It does
not replace machine simulation or a dry run.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np

from .gcode import Program
from .planner import MachineProfile

ERROR, WARNING, INFO = "error", "warning", "info"


@dataclass
class Issue:
    code: str
    severity: str
    line: int          # 0 when the issue concerns the whole program
    title: str
    detail: str
    action: str        # what the programmer can do about it

    def to_dict(self) -> dict:
        return asdict(self)


def _first(issues: list[Issue], limit_per_code: int = 5) -> list[Issue]:
    """Keep the first few hits per rule and say how many were dropped."""
    out, count = [], {}
    for it in issues:
        count[it.code] = count.get(it.code, 0) + 1
        if count[it.code] <= limit_per_code:
            out.append(it)
    for code, c in count.items():
        if c > limit_per_code:
            last = next(i for i in reversed(out) if i.code == code)
            last.detail += f" ({c - limit_per_code} more blocks have the same problem.)"
    return out


def run_checks(prog: Program, m: MachineProfile) -> list[Issue]:
    issues: list[Issue] = []
    add = issues.append

    if not prog.units_declared:
        add(Issue("P001", WARNING, 0, "Units not declared",
                  "The program never sets G20 or G21, so it inherits whatever the controller was left in. Millimetres were assumed here.",
                  "Add G21 (mm) or G20 (inch) to the first block."))
    if not prog.distance_mode_declared:
        add(Issue("P002", WARNING, 0, "Absolute/incremental mode not declared",
                  "No G90 or G91 was found. Absolute positioning was assumed.",
                  "Add G90 to the first block."))
    if not prog.ended:
        add(Issue("P003", WARNING, 0, "No program end",
                  "The program does not finish with M30 or M2.",
                  "End the program with M30."))

    lo, hi = np.array(m.travel_min), np.array(m.travel_max)
    prev = None
    for s in prog.segments:
        if s.kind == "toolchange":
            if s.spindle_on:
                add(Issue("T001", WARNING, s.line, "Tool change with spindle running",
                          "M6 is called while the spindle is still commanded on.",
                          "Stop the spindle (M5) before the tool change."))
            if s.start[2] < 0:
                add(Issue("T002", ERROR, s.line, "Tool change below the work surface",
                          f"M6 is called at Z{s.start[2]:.3f}, below Z0.",
                          "Retract to a safe Z before the tool change."))
            continue
        if not s.is_move:
            continue
        if s.is_cut:
            if s.feed <= 0:
                add(Issue("F001", ERROR, s.line, "Cutting move without a feed rate",
                          "A G1/G2/G3 move runs before any F word has been set.",
                          "Program a feed rate (F) on or before this block."))
            elif s.feed > m.max_feed:
                add(Issue("F002", WARNING, s.line, "Feed above the machine limit",
                          f"F{s.feed:.0f} mm/min exceeds the profile limit of {m.max_feed:.0f}. The estimate uses the limit.",
                          "Lower the feed or check the machine profile."))
            if not s.spindle_on and min(s.start[2], s.end[2]) < 0:
                add(Issue("S001", ERROR, s.line, "Cutting move with the spindle off",
                          "The tool moves at feed below Z0 while the spindle is stopped.",
                          "Start the spindle (M3 S...) before this block."))
        if s.kind == "rapid" and s.end[2] < 0 and s.end[2] < s.start[2] - 1e-9:
            add(Issue("R001", ERROR, s.line, "Rapid move into the work",
                      f"G0 plunges to Z{s.end[2]:.3f}, below the work surface at Z0.",
                      "Rapid to a clearance height, then feed down with G1."))
        elif s.kind == "rapid" and s.start[2] < 0 and np.hypot(*(s.end[:2] - s.start[:2])) > 1e-6:
            add(Issue("R002", WARNING, s.line, "Rapid traverse below the work surface",
                      f"G0 moves sideways at Z{s.start[2]:.3f}.",
                      "Retract above Z0 before a rapid XY move, unless the path is known to be clear."))
        if s.spindle_on and s.rpm > m.max_rpm:
            if prev is None or prev.rpm != s.rpm:
                add(Issue("S002", WARNING, s.line, "Spindle speed above the machine limit",
                          f"S{s.rpm:.0f} exceeds the profile limit of {m.max_rpm:.0f} rev/min.",
                          "Lower the spindle speed or check the machine profile."))
        if s.spindle_on and s.rpm <= 0 and s.is_cut:
            add(Issue("S003", ERROR, s.line, "Spindle on with no speed",
                      "M3/M4 is active but no S word has been set.",
                      "Program a spindle speed (S)."))
        if np.any(s.end < lo - 1e-9) or np.any(s.end > hi + 1e-9):
            axis = "XYZ"[int(np.argmax((s.end < lo) | (s.end > hi)))]
            add(Issue("L001", ERROR, s.line, "Move outside the travel envelope",
                      f"The {axis} target ({s.end[0]:.1f}, {s.end[1]:.1f}, {s.end[2]:.1f}) is outside the profile's work envelope.",
                      "Check the work offset and the machine profile limits."))
        prev = s

    for n in prog.notes:
        sev = ERROR if n.code in ("ARC_RADIUS", "ARC_R_FULL", "NO_MOTION_MODE") else INFO
        if n.code == "UNSUPPORTED":
            sev = WARNING
        title = {"ARC_RADIUS": "Arc geometry does not close", "ARC_R_FULL": "Undefined arc",
                 "NO_MOTION_MODE": "Axis move without a motion code",
                 "UNSUPPORTED": "Feature not simulated", "UNKNOWN": "Unrecognised code",
                 "UNPARSED": "Text not interpreted", "HOME": "Reference return not simulated"}[n.code]
        add(Issue("N-" + n.code, sev, n.line, title, n.message.capitalize() + ".",
                  "This block is left out of the time and energy estimate; check it by hand."
                  if sev != ERROR else "Correct the block."))

    moves = prog.moves
    if moves:
        short = sum(1 for s in moves if s.is_cut and s.length < 0.5)
        cuts = sum(1 for s in moves if s.is_cut)
        if cuts and short / cuts > 0.5:
            add(Issue("Q001", INFO, 0, "Mostly very short blocks",
                      f"{short} of {cuts} cutting blocks are shorter than 0.5 mm. Real feed will stay well below the programmed value.",
                      "Expect the time range to be wider; consider arc fitting or smoothing in CAM."))
    else:
        add(Issue("P004", ERROR, 0, "No motion found", "The program contains no axis moves.",
                  "Check that the file is an NC program."))

    order = {ERROR: 0, WARNING: 1, INFO: 2}
    return sorted(_first(issues), key=lambda i: (order[i.severity], i.line))
