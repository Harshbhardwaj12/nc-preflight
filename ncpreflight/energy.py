"""Physics-based drive-energy baseline.

Energy = idle power + no-load spindle power + axis motion power + cutting power,
each integrated over the planner's segment times. The coefficients come from
the machine profile and from textbook specific cutting energies, so the result
is an order-of-magnitude baseline that the calibration layer corrects.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .gcode import Program
from .planner import MachineProfile, Plan

# Specific cutting energy, N/mm^2. Typical handbook magnitudes, not measured values.
SPECIFIC_CUTTING_ENERGY = {"aluminium": 700.0, "steel": 2000.0, "plastic": 150.0}
MATERIALS = list(SPECIFIC_CUTTING_ENERGY)


@dataclass(frozen=True)
class Job:
    """What the user tells us about the job that the NC program does not contain."""
    material: str = "aluminium"
    tool_diameter: float = 10.0   # mm
    depth_of_cut: float = 2.0     # mm, axial
    width_ratio: float = 0.5      # radial engagement / tool diameter (assumed)

    @staticmethod
    def from_meta(meta: dict, **overrides) -> "Job":
        mat = meta.get("MATERIAL", "aluminium").lower()
        kw = dict(material=mat if mat in SPECIFIC_CUTTING_ENERGY else "aluminium",
                  tool_diameter=_num(meta.get("TOOL_D"), 10.0),
                  depth_of_cut=_num(meta.get("AP"), 2.0))
        kw.update({k: v for k, v in overrides.items() if v is not None})
        return Job(**kw)


def _num(v, default):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def segment_energy(prog: Program, plan: Plan, m: MachineProfile, job: Job) -> np.ndarray:
    """Joules per segment."""
    kc = SPECIFIC_CUTTING_ENERGY[job.material]
    out = np.zeros(len(prog.segments))
    for i, s in enumerate(prog.segments):
        t = plan.seg_time[i]
        p = m.idle_power
        if s.spindle_on:
            p += m.spindle_w_per_rpm * s.rpm
        if s.is_move and t > 0:
            v = s.length / t                       # mean speed, mm/s
            p += m.axis_w_per_mm_min * v * 60.0
            if s.is_cut and s.spindle_on and min(s.start[2], s.end[2]) < 0:
                mrr = job.depth_of_cut * job.width_ratio * job.tool_diameter * v   # mm^3/s
                p += kc * mrr / 1000.0
        out[i] = p * t
    return out
