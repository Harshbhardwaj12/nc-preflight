"""Calibration layer: learn the gap between the physics baseline and measured
runs, and turn it into prediction intervals.

Targets are log ratios, log(measured / baseline), so intervals are
multiplicative and stay positive. Intervals come from conformal prediction:

* split conformal      - scores from a random hold-out. Valid when the new job
                         is exchangeable with the calibration jobs.
* grouped conformal    - scores from leave-one-group-out predictions (a group
                         is a part family). Each score is the error on a kind
                         of part the model had not seen, which is the situation
                         a new job is in.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .energy import MATERIALS, Job, segment_energy
from .gcode import Program
from .planner import MachineProfile, Plan

FEATURES = ["log_nominal", "log_planned", "log_slowdown", "log_moves", "rapid_frac", "short_frac",
            "log_mean_len", "corners_per_s", "ramps_per_s", "toolchanges_per_min", "arc_frac",
            "z_frac", "mean_feed", "mean_rpm", "tool_d", "depth", "cut_energy_frac",
            "spindle_energy_frac"] + [f"mat_{m}" for m in MATERIALS]


def features(prog: Program, p: Plan, m: MachineProfile, job: Job) -> tuple[dict, float, float]:
    """Feature dict plus the two baselines (planned time in s, physics energy in J)."""
    moves = [(i, s) for i, s in enumerate(prog.segments) if s.is_move]
    total_len = sum(s.length for _, s in moves) or 1e-9
    cuts = [s for _, s in moves if s.is_cut]
    cut_len = sum(s.length for s in cuts) or 1e-9
    corners = 0
    for (_, a), (_, b) in zip(moves, moves[1:]):
        if float(np.dot(a.u_out, b.u_in)) < 0.866:           # direction change over 30 degrees
            corners += 1
    planned = max(p.total, 1e-6)
    nominal = max(p.nominal, 1e-6)
    seg_e = segment_energy(prog, p, m, job)
    e_total = max(float(seg_e.sum()), 1e-6)
    idle_e = m.idle_power * planned
    spindle_e = sum(m.spindle_w_per_rpm * s.rpm * p.seg_time[i]
                    for i, s in enumerate(prog.segments) if s.spindle_on)
    f = {
        "log_nominal": math.log(nominal), "log_planned": math.log(planned),
        "log_slowdown": math.log(planned / nominal), "log_moves": math.log(len(moves) + 1),
        "rapid_frac": sum(s.length for _, s in moves if s.kind == "rapid") / total_len,
        "short_frac": sum(1 for s in cuts if s.length < 1.0) / max(len(cuts), 1),
        "log_mean_len": math.log(total_len / max(len(moves), 1)),
        "corners_per_s": corners / planned, "ramps_per_s": p.n_accel_phases / planned,
        "toolchanges_per_min": 60.0 * sum(1 for s in prog.segments if s.kind == "toolchange") / planned,
        "arc_frac": sum(s.length for s in cuts if s.kind == "arc") / cut_len,
        "z_frac": sum(abs(s.end[2] - s.start[2]) for _, s in moves) / total_len,
        "mean_feed": sum(s.feed * s.length for s in cuts) / cut_len / 1000.0,
        "mean_rpm": sum(s.rpm * p.seg_time[i] for i, s in enumerate(prog.segments)) / planned / 1000.0,
        "tool_d": job.tool_diameter, "depth": job.depth_of_cut,
        "cut_energy_frac": max(e_total - idle_e - spindle_e, 0.0) / e_total,
        "spindle_energy_frac": spindle_e / e_total,
    }
    for mat in MATERIALS:
        f[f"mat_{mat}"] = 1.0 if job.material == mat else 0.0
    return f, planned, e_total


def conformal_quantile(scores: np.ndarray, level: float) -> float:
    """Finite-sample conformal quantile of absolute residuals. inf if too few scores."""
    n = len(scores)
    k = math.ceil((n + 1) * level)
    if n == 0 or k > n:
        return math.inf
    return float(np.sort(scores)[k - 1])


def make_model(kind: str = "ridge"):
    if kind == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    if kind == "gbr":
        return GradientBoostingRegressor(n_estimators=200, max_depth=3, learning_rate=0.05,
                                         subsample=0.8, random_state=0)
    raise ValueError(kind)


def grouped_scores(X: np.ndarray, y: np.ndarray, groups: np.ndarray, kind: str) -> np.ndarray:
    """Absolute residuals of leave-one-group-out predictions."""
    scores = np.zeros(len(y))
    for g in np.unique(groups):
        test = groups == g
        model = make_model(kind).fit(X[~test], y[~test])
        scores[test] = np.abs(y[test] - model.predict(X[test]))
    return scores


@dataclass
class Envelope:
    """Range of the calibration jobs, used to flag programs unlike any of them.

    Conformal intervals assume the new job resembles the calibration jobs. This
    check is a plain per-feature range test: a job is flagged when any feature
    lies outside the calibration range by more than `margin` of that range.
    """
    lo: np.ndarray
    hi: np.ndarray
    margin: float = 0.10

    @staticmethod
    def fit(X: np.ndarray, margin: float = 0.10) -> "Envelope":
        return Envelope(X.min(axis=0), X.max(axis=0), margin)

    def outside(self, x: np.ndarray) -> list[int]:
        """Indices of features outside the calibration range."""
        span = np.maximum(self.hi - self.lo, 1e-9)
        bad = (x < self.lo - self.margin * span) | (x > self.hi + self.margin * span)
        return [int(i) for i in np.flatnonzero(bad)]


@dataclass
class Target:
    """One calibrated quantity (time or energy)."""
    model: object
    scores: np.ndarray
    offset: float = 0.0         # bias correction after a few runs on a new machine

    def predict(self, x: np.ndarray, level: float) -> tuple[float, float, float]:
        """(ratio, low ratio, high ratio) to multiply the baseline by."""
        mu = float(self.model.predict(x.reshape(1, -1))[0]) + self.offset
        q = conformal_quantile(self.scores, level)
        return math.exp(mu), math.exp(mu - q), math.exp(mu + q)


@dataclass
class Calibration:
    time: Target
    energy: Target
    n_jobs: int
    n_groups: int
    kind: str
    source: str                 # "simulated" | "historical" | ...
    label: str = ""
    feature_names: list = field(default_factory=lambda: list(FEATURES))
    envelope: "Envelope | None" = None

    @staticmethod
    def fit(X, y_time, y_energy, groups, kind="ridge", source="simulated", label="") -> "Calibration":
        X, groups = np.asarray(X, float), np.asarray(groups)
        targets = []
        for y in (np.asarray(y_time, float), np.asarray(y_energy, float)):
            targets.append(Target(make_model(kind).fit(X, y), grouped_scores(X, y, groups, kind)))
        return Calibration(targets[0], targets[1], len(X), len(np.unique(groups)), kind, source, label,
                           envelope=Envelope.fit(X))


def to_row(f: dict) -> np.ndarray:
    return np.array([f[k] for k in FEATURES], dtype=float)
