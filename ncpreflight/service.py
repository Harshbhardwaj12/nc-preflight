"""Application service: one call that turns program text into the full report."""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from .calibration import FEATURES, Calibration, features, to_row
from .checks import run_checks
from .energy import MATERIALS, Job, segment_energy
from .gcode import parse, polyline
from .planner import PROFILES, MachineProfile, plan

ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"
MAX_PROGRAM_BYTES = 5_000_000
MAX_PROGRAM_LINES = 150_000
MAX_PLOT_POINTS = 6000
FEATURE_LABELS = {
    "log_nominal": "program duration", "log_planned": "program duration",
    "log_slowdown": "share of time lost to acceleration", "log_moves": "number of blocks",
    "rapid_frac": "share of rapid travel", "short_frac": "share of very short blocks",
    "log_mean_len": "typical block length", "corners_per_s": "corner density",
    "ramps_per_s": "speed-change density", "toolchanges_per_min": "tool-change rate",
    "arc_frac": "share of arc moves", "z_frac": "share of Z travel", "mean_feed": "feed rate",
    "mean_rpm": "spindle speed", "tool_d": "tool diameter", "depth": "depth of cut",
    "cut_energy_frac": "share of cutting energy", "spindle_energy_frac": "share of spindle energy",
}


def load_calibration(path: Path, kind: str = "gbr") -> Calibration | None:
    """Build a calibration from a CSV of logged runs (one row per job)."""
    if not path.exists():
        return None
    with path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) < 20:
        return None
    X = np.array([[float(r[k]) for k in FEATURES] for r in rows])
    y_t = np.array([float(r["log_time_ratio"]) for r in rows])
    y_e = np.array([float(r["log_energy_ratio"]) for r in rows])
    groups = np.array([r["group"] for r in rows])
    return Calibration.fit(X, y_t, y_e, groups, kind=kind, source=rows[0].get("source", "unknown"),
                           label=rows[0].get("label", ""))


class Estimator:
    """Holds one calibration per machine profile."""

    def __init__(self, artifacts: Path = ARTIFACTS):
        self.calibrations: dict[str, Calibration] = {}
        for pid in PROFILES:
            cal = load_calibration(artifacts / f"calibration_{pid}.csv")
            if cal is not None:
                self.calibrations[pid] = cal

    def analyze(self, text: str, machine_id: str = "generic-vmc", level: float = 0.9,
                material: str | None = None, tool_diameter: float | None = None,
                depth_of_cut: float | None = None) -> dict:
        if machine_id not in PROFILES:
            raise ValueError(f"unknown machine profile '{machine_id}'")
        if not 0.5 <= level <= 0.99:
            raise ValueError("confidence level must be between 0.5 and 0.99")
        if material is not None and material not in MATERIALS:
            raise ValueError(f"unknown material '{material}'")
        if len(text.encode("utf-8", "ignore")) > MAX_PROGRAM_BYTES:
            raise ValueError("program is larger than 5 MB")
        if text.count("\n") >= MAX_PROGRAM_LINES:
            raise ValueError(f"program has more than {MAX_PROGRAM_LINES:,} lines")
        m: MachineProfile = PROFILES[machine_id]
        prog = parse(text)
        job = Job.from_meta(prog.meta, material=material, tool_diameter=tool_diameter,
                            depth_of_cut=depth_of_cut)
        issues = run_checks(prog, m)
        if not prog.moves:
            return {"ok": False, "issues": [i.to_dict() for i in issues], "machine": m.to_dict()}

        p = plan(prog, m)
        seg_e = segment_energy(prog, p, m, job)
        f, planned, e_phys = features(prog, p, m, job)

        cal = self.calibrations.get(machine_id)
        time_out = {"nominal_s": p.nominal, "planned_s": planned}
        energy_out = {"physics_wh": e_phys / 3600.0}
        if cal is not None:
            x = to_row(f)
            r, lo, hi = cal.time.predict(x, level)
            time_out.update(estimate_s=planned * r, low_s=planned * lo, high_s=planned * hi)
            r, lo, hi = cal.energy.predict(x, level)
            energy_out.update(estimate_wh=e_phys * r / 3600, low_wh=e_phys * lo / 3600,
                              high_wh=e_phys * hi / 3600)
            outside = list(dict.fromkeys(FEATURE_LABELS.get(FEATURES[i], FEATURES[i])
                                         for i in cal.envelope.outside(x)))
            calibration = {"state": "out_of_range" if outside else "calibrated",
                           "source": cal.source, "label": cal.label, "jobs": cal.n_jobs,
                           "groups": cal.n_groups, "level": level, "outside": outside}
        else:
            time_out.update(estimate_s=planned, low_s=None, high_s=None)
            energy_out.update(estimate_wh=e_phys / 3600, low_wh=None, high_wh=None)
            calibration = {"state": "uncalibrated", "source": None, "label": "", "jobs": 0,
                           "groups": 0, "level": level, "outside": []}

        lo_b, hi_b = prog.bounds()
        return {
            "ok": True,
            "machine": m.to_dict(),
            "job": {"material": job.material, "tool_diameter": job.tool_diameter,
                    "depth_of_cut": job.depth_of_cut},
            "calibration": calibration,
            "time": time_out,
            "energy": energy_out,
            "stats": {"lines": prog.n_lines, "blocks": len(prog.segments),
                      "cut_length_mm": sum(s.length for s in prog.moves if s.is_cut),
                      "rapid_length_mm": sum(s.length for s in prog.moves if s.kind == "rapid"),
                      "tool_changes": sum(1 for s in prog.segments if s.kind == "toolchange"),
                      "bounds_min": lo_b.tolist(), "bounds_max": hi_b.tolist()},
            "issues": [i.to_dict() for i in issues],
            "hotspots": _hotspots(prog, p, seg_e),
            "path": _path(prog, p),
        }


def _hotspots(prog, p, seg_e, n_bins: int = 12) -> list[dict]:
    """Split the program into consecutive line ranges and report where time goes."""
    segs = prog.segments
    if not segs:
        return []
    edges = np.linspace(0, len(segs), min(n_bins, len(segs)) + 1).astype(int)
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        if b <= a:
            continue
        t, nom = float(p.seg_time[a:b].sum()), float(p.seg_nominal[a:b].sum())
        out.append({"line_from": segs[a].line, "line_to": segs[b - 1].line, "time_s": t,
                    "nominal_s": nom, "slowdown": t / nom if nom > 0 else 1.0,
                    "energy_wh": float(seg_e[a:b].sum()) / 3600.0,
                    "share": t / p.total if p.total > 0 else 0.0})
    return out


def _path(prog, p) -> list[dict]:
    """Polyline pieces for drawing, thinned to a bounded number of points."""
    moves = [(i, s) for i, s in enumerate(prog.segments) if s.is_move]
    stride = max(1, -(-len(moves) // MAX_PLOT_POINTS))   # ceiling division
    out = []
    for k in range(0, len(moves), stride):
        i, s = moves[k]
        end = moves[min(k + stride, len(moves)) - 1][1].end
        pts = polyline(s) if stride == 1 else np.vstack([s.start, end])
        speed = s.length / p.seg_time[i] * 60.0 if p.seg_time[i] > 0 else 0.0
        slow = int(s.is_cut and s.feed > 0 and speed < 0.7 * s.feed)   # well below programmed feed
        out.append({"k": s.kind[0], "line": s.line, "feed": round(float(speed), 1), "slow": slow,
                    "pts": np.round(pts, 3).tolist()})
    return out
