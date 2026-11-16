"""Cycle-time model: a look-ahead trapezoidal velocity planner.

Two estimates are produced for every program:

* nominal  - path length divided by programmed feed. This is what a CAM
             system reports and is the weak baseline.
* planned  - a constant-acceleration planner with corner slow-down, the
             physics-based baseline.

The planner is deliberately simple (one acceleration for all axes, no jerk
limit). The calibration layer learns what it leaves out.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict

import numpy as np

from .gcode import Program, Segment


@dataclass(frozen=True)
class MachineProfile:
    """Data-sheet level description of a 3-axis machine."""
    id: str
    name: str
    max_feed: float = 10000.0        # mm/min
    rapid: float = 24000.0           # mm/min
    accel: float = 2000.0            # mm/s^2
    junction_dev: float = 0.02       # mm, corner tolerance
    max_rpm: float = 12000.0
    toolchange_s: float = 5.0
    travel_min: tuple = (-300.0, -200.0, -300.0)   # work-coordinate envelope, mm
    travel_max: tuple = (300.0, 200.0, 150.0)
    idle_power: float = 900.0        # W, machine on, nothing moving
    spindle_w_per_rpm: float = 0.06  # W per rev/min, no-load spindle
    axis_w_per_mm_min: float = 0.02  # W per mm/min of feed motion

    def to_dict(self) -> dict:
        return asdict(self)


PROFILES = {
    "generic-vmc": MachineProfile(id="generic-vmc", name="Generic 3-axis VMC"),
    "light-router": MachineProfile(id="light-router", name="Light CNC router", max_feed=6000.0,
                                   rapid=10000.0, accel=800.0, junction_dev=0.05, max_rpm=24000.0,
                                   toolchange_s=0.0, idle_power=250.0, spindle_w_per_rpm=0.012,
                                   axis_w_per_mm_min=0.008),
}


@dataclass
class Plan:
    """Per-segment timing for one program on one machine."""
    seg_time: np.ndarray       # seconds per segment, planner
    seg_nominal: np.ndarray    # seconds per segment, length / feed
    v_peak: np.ndarray         # mm/s reached in each segment
    v_entry: np.ndarray        # mm/s at the start of each segment (length n + 1)
    n_accel_phases: int        # speed ramps that are not flat
    total: float
    nominal: float


def _limit_speed(seg: Segment, m: MachineProfile, accel: float) -> float:
    """Highest speed this segment may run at, mm/s."""
    if seg.kind == "rapid":
        return m.rapid / 60.0
    v = min(seg.feed, m.max_feed) / 60.0
    if seg.kind == "arc" and seg.radius > 0:
        v = min(v, math.sqrt(accel * seg.radius))
    return v


def junction_speed(u_out: np.ndarray, u_in: np.ndarray, accel: float, dev: float) -> float:
    """Speed allowed through a corner (centripetal junction-deviation model)."""
    cos_t = -float(np.dot(u_out, u_in))
    if cos_t < -0.999999:
        return math.inf           # straight on
    if cos_t > 0.999999:
        return 0.0                # full reversal
    s = math.sqrt(0.5 * (1.0 - cos_t))
    return math.sqrt(accel * dev * s / (1.0 - s))


def plan(prog: Program, m: MachineProfile, accel: float | None = None,
         junction_dev: float | None = None, min_block_time: float = 0.0,
         exact_stop_rapid: bool = False) -> Plan:
    """Time every segment. The optional arguments let a simulator override the data sheet."""
    a = accel if accel is not None else m.accel
    dev = junction_dev if junction_dev is not None else m.junction_dev
    segs = prog.segments
    n = len(segs)
    seg_time = np.zeros(n)
    seg_nom = np.zeros(n)
    v_peak = np.zeros(n)
    vmax = np.zeros(n)
    for i, s in enumerate(segs):
        if s.kind == "dwell":
            seg_time[i] = seg_nom[i] = s.dwell
        elif s.kind == "toolchange":
            seg_time[i] = seg_nom[i] = m.toolchange_s
        else:
            vmax[i] = _limit_speed(s, m, a)
            if min_block_time > 0:
                vmax[i] = min(vmax[i], s.length / min_block_time)
            seg_nom[i] = s.length / vmax[i] if vmax[i] > 0 else 0.0
            if s.kind != "rapid" and s.feed > 0:
                seg_nom[i] = s.length / (s.feed / 60.0)

    # entry speed limit for each segment (v_entry[n] is the final stop)
    v_entry = np.zeros(n + 1)
    for i in range(1, n):
        p, c = segs[i - 1], segs[i]
        if not (p.is_move and c.is_move) or vmax[i] <= 0 or vmax[i - 1] <= 0:
            continue
        if p.spindle_on != c.spindle_on or p.rpm != c.rpm:
            continue                                  # spindle change: stop
        if exact_stop_rapid and (p.kind == "rapid") != (c.kind == "rapid"):
            continue
        v_entry[i] = min(junction_speed(p.u_out, c.u_in, a, dev), vmax[i - 1], vmax[i])

    for i in range(n - 1, -1, -1):                    # backward pass: can we brake in time?
        if segs[i].is_move:
            v_entry[i] = min(v_entry[i], math.sqrt(v_entry[i + 1] ** 2 + 2 * a * segs[i].length))
    ramps = 0
    for i in range(n):                                # forward pass: can we get up to speed?
        s = segs[i]
        if not s.is_move or vmax[i] <= 0:
            continue
        v0 = v_entry[i]
        v1 = min(v_entry[i + 1], math.sqrt(v0 * v0 + 2 * a * s.length))
        v_entry[i + 1] = v1
        vp = min(vmax[i], math.sqrt((2 * a * s.length + v0 * v0 + v1 * v1) / 2))
        vp = max(vp, v0, v1, 1e-9)
        d_ramp = (vp * vp - v0 * v0) / (2 * a) + (vp * vp - v1 * v1) / (2 * a)
        cruise = max(s.length - d_ramp, 0.0)
        seg_time[i] = (vp - v0) / a + (vp - v1) / a + cruise / vp
        v_peak[i] = vp
        ramps += int(vp - v0 > 1e-6) + int(vp - v1 > 1e-6)
    return Plan(seg_time, seg_nom, v_peak, v_entry, ramps, float(seg_time.sum()), float(seg_nom.sum()))
