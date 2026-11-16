"""Simulated machines and synthetic NC programs.

EVERYTHING THIS MODULE PRODUCES IS SIMULATED. It exists so the whole pipeline
(parse -> plan -> calibrate -> interval) can be exercised and tested without a
machine. A "true" machine here is the planner run with hidden parameters plus
effects the estimator does not model (jerk limiting, block processing time,
exact stops, spindle ramps, inertia, a different cutting engagement). Results
from it show that the method behaves as designed. They say nothing about
accuracy on a real machine.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .energy import Job, SPECIFIC_CUTTING_ENERGY, MATERIALS
from .gcode import Program
from .planner import MachineProfile, plan


@dataclass(frozen=True)
class HiddenMachine:
    """Behaviour of a simulated machine that its data sheet does not tell you."""
    accel_factor: float = 0.62        # usable acceleration / data-sheet value
    junction_dev: float = 0.008       # mm
    jerk: float = 40000.0             # mm/s^3
    min_block_time: float = 0.004     # s per block
    toolchange_extra: float = 2.5     # s
    spindle_ramp: float = 6000.0      # rev/min per second
    idle_power: float = 1150.0        # W
    spindle_lin: float = 0.045        # W per rev/min
    spindle_quad: float = 2.2e-6      # W per (rev/min)^2
    axis_friction: float = 0.03       # W per mm/min
    moving_mass: float = 350.0        # kg
    spindle_inertia: float = 0.012    # kg m^2
    kc_factor: tuple = (1.15, 0.9, 1.3)   # aluminium, steel, plastic
    time_noise: float = 0.01
    energy_noise: float = 0.02


MACHINE_A = HiddenMachine()
MACHINE_B = HiddenMachine(accel_factor=0.45, junction_dev=0.015, jerk=25000.0, min_block_time=0.006,
                          toolchange_extra=4.0, spindle_ramp=4000.0, idle_power=1500.0,
                          spindle_lin=0.06, spindle_quad=3.0e-6, axis_friction=0.045,
                          moving_mass=520.0, kc_factor=(1.3, 1.05, 1.2))


def simulate_run(prog: Program, m: MachineProfile, job: Job, hidden: HiddenMachine,
                 rng: np.random.Generator) -> tuple[float, float]:
    """Return the simulated measured (cycle time in s, drive energy in J)."""
    a = m.accel * hidden.accel_factor
    p = plan(prog, m, accel=a, junction_dev=hidden.junction_dev,
             min_block_time=hidden.min_block_time, exact_stop_rapid=True)
    seg_time = p.seg_time.copy()
    width = rng.uniform(0.25, 0.8)               # true radial engagement, unknown to the estimator
    kc = SPECIFIC_CUTTING_ENERGY[job.material] * hidden.kc_factor[MATERIALS.index(job.material)]
    energy = 0.0
    last_rpm = 0.0
    extra_time = 0.0
    for i, s in enumerate(prog.segments):
        if s.kind == "toolchange":
            seg_time[i] += hidden.toolchange_extra
        rpm = s.rpm if s.spindle_on else 0.0
        if rpm != last_rpm:                       # spindle speed change: ramp and inertia
            ramp = abs(rpm - last_rpm) / hidden.spindle_ramp
            extra_time += ramp
            if rpm > last_rpm:
                w1, w0 = rpm * 2 * math.pi / 60, last_rpm * 2 * math.pi / 60
                energy += 0.5 * hidden.spindle_inertia * (w1 * w1 - w0 * w0)
            energy += hidden.idle_power * ramp
            last_rpm = rpm
        power = hidden.idle_power + hidden.spindle_lin * rpm + hidden.spindle_quad * rpm * rpm
        if s.is_move and p.seg_time[i] > 0:
            v0, v1, vp = p.v_entry[i], p.v_entry[i + 1], p.v_peak[i]
            n_ramps = int(vp - v0 > 1e-6) + int(vp - v1 > 1e-6)
            seg_time[i] += n_ramps * a / hidden.jerk          # S-curve lengthens every ramp
            v = s.length / seg_time[i]
            power += hidden.axis_friction * v * 60.0
            energy += 0.5 * hidden.moving_mass * max(vp * vp - v0 * v0, 0.0) * 1e-6   # mm/s -> m/s
            if s.is_cut and s.spindle_on and min(s.start[2], s.end[2]) < 0:
                power += kc * job.depth_of_cut * width * job.tool_diameter * v / 1000.0
        energy += power * seg_time[i]
    total = (seg_time.sum() + extra_time) * math.exp(rng.normal(0.0, hidden.time_noise))
    return float(total), float(energy * math.exp(rng.normal(0.0, hidden.energy_noise)))


# --------------------------------------------------------------------------
# Synthetic NC programs. Six geometry families with different block statistics.
# --------------------------------------------------------------------------

FAMILIES = ("pocket", "contour", "drill", "surface", "trochoid", "engrave")


def _header(family, material, tool_d, ap, rpm):
    return [f"(FAMILY={family.upper()})", f"(MATERIAL={material.upper()})", f"(TOOL_D={tool_d:g})",
            f"(AP={ap:g})", "(SIMULATED PROGRAM - GENERATED, NOT FROM A REAL JOB)",
            "G21 G90 G17", "T1 M6", f"S{rpm:.0f} M3", "G0 Z5.000"]


def _footer():
    return ["G0 Z20.000", "M5", "M30"]


def _pocket(r, f, ap, d):
    w, h = r.uniform(30, 120), r.uniform(20, 80)
    step = d * r.uniform(0.3, 0.7)
    out = []
    for lvl in range(1, int(r.integers(1, 5)) + 1):
        z = -ap * lvl
        out += [f"G0 X0.000 Y0.000", f"G1 Z{z:.3f} F{f * 0.3:.0f}", f"F{f:.0f}"]
        y, right = 0.0, True
        while y <= h:
            out.append(f"G1 X{w if right else 0:.3f} Y{y:.3f}")
            y += step
            if y <= h:
                out.append(f"G1 Y{y:.3f}")
            right = not right
        out += [f"G1 X0.000 Y{h:.3f}", "G1 Y0.000", f"G1 X{w:.3f}", f"G1 Y{h:.3f}", "G0 Z5.000"]
    return out


def _contour(r, f, ap, d):
    w, h, c = r.uniform(40, 150), r.uniform(30, 100), r.uniform(3, 12)
    out = [f"G0 X{c:.3f} Y0.000"]
    for lvl in range(1, int(r.integers(2, 8)) + 1):
        out += [f"G1 Z{-ap * lvl:.3f} F{f * 0.3:.0f}", f"G1 X{w - c:.3f} F{f:.0f}",
                f"G3 X{w:.3f} Y{c:.3f} I0 J{c:.3f}", f"G1 Y{h - c:.3f}",
                f"G3 X{w - c:.3f} Y{h:.3f} I{-c:.3f} J0", f"G1 X{c:.3f}",
                f"G3 X0.000 Y{h - c:.3f} I0 J{-c:.3f}", f"G1 Y{c:.3f}",
                f"G3 X{c:.3f} Y0.000 I{c:.3f} J0"]
    return out + ["G0 Z5.000"]


def _drill(r, f, ap, d):
    nx, ny, pitch = int(r.integers(3, 10)), int(r.integers(2, 8)), r.uniform(8, 25)
    depth, peck = r.uniform(5, 25), max(ap, 1.0)
    out = []
    for i in range(nx):
        for j in (range(ny) if i % 2 == 0 else range(ny - 1, -1, -1)):
            out += [f"G0 X{i * pitch:.3f} Y{j * pitch:.3f}", "G0 Z1.000"]
            z = 0.0
            while z > -depth:
                z = max(z - peck, -depth)
                out += [f"G1 Z{z:.3f} F{f * 0.25:.0f}", "G0 Z1.000"]
            out.append("G0 Z5.000")
    return out


def _surface(r, f, ap, d):
    w, h = r.uniform(25, 70), r.uniform(15, 40)
    step, pitch = r.uniform(0.2, 0.9), r.uniform(0.4, 1.5)
    amp, wave = min(ap, 3.0), r.uniform(8, 30)
    out = ["G0 X0.000 Y0.000", f"G1 Z{-amp:.3f} F{f * 0.3:.0f}", f"F{f:.0f}"]
    y, fwd = 0.0, True
    xs = np.arange(0.0, w + step, step)
    while y <= h:
        for x in (xs if fwd else xs[::-1]):
            z = -amp * (1.05 + math.sin(2 * math.pi * x / wave) * math.cos(2 * math.pi * y / wave)) / 2
            out.append(f"G1 X{x:.3f} Y{y:.3f} Z{z:.3f}")
        y += pitch
        fwd = not fwd
    return out + ["G0 Z5.000"]


def _trochoid(r, f, ap, d):
    length, rad, adv = r.uniform(30, 120), d * r.uniform(0.3, 0.8), d * r.uniform(0.08, 0.25)
    out = ["G0 X0.000 Y0.000", f"G1 Z{-ap:.3f} F{f * 0.3:.0f}", f"F{f:.0f}"]
    x = 0.0
    while x < length:
        out += [f"G2 X{x:.3f} Y0.000 I0 J{rad:.3f}", f"G1 X{x + adv:.3f}"]
        x += adv
    return out + ["G0 Z5.000"]


def _engrave(r, f, ap, d):
    out = []
    for _ in range(int(r.integers(6, 30))):
        x, y = r.uniform(0, 100), r.uniform(0, 60)
        out += [f"G0 X{x:.3f} Y{y:.3f}", f"G1 Z{-min(ap, 0.5):.3f} F{f * 0.3:.0f}", f"F{f:.0f}"]
        for _ in range(int(r.integers(4, 25))):
            x, y = x + r.uniform(-6, 6), y + r.uniform(-6, 6)
            out.append(f"G1 X{x:.3f} Y{y:.3f}")
        out.append("G0 Z2.000")
    return out


_BUILDERS = dict(pocket=_pocket, contour=_contour, drill=_drill, surface=_surface,
                 trochoid=_trochoid, engrave=_engrave)


def generate_program(family: str, rng: np.random.Generator) -> tuple[str, Job]:
    """A random NC program of the given family and the job data that goes with it."""
    material = str(rng.choice(MATERIALS))
    tool_d = float(rng.choice([3, 4, 6, 8, 10, 12, 16]))
    ap = round(float(rng.uniform(0.5, 4.0)), 2)
    rpm = float(rng.integers(3, 13)) * 1000.0
    feed = float(rng.uniform(300, 4000))
    body = _BUILDERS[family](rng, feed, ap, tool_d)
    text = "\n".join(_header(family, material, tool_d, ap, rpm) + body + _footer()) + "\n"
    return text, Job(material=material, tool_diameter=tool_d, depth_of_cut=ap)
