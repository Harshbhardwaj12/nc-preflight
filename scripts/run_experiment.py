"""Simulated-machine experiment (SIMULATED DATA ONLY).

Checks that the pipeline behaves as designed before any real data is used:

E1  point error on a held-out part family: nominal vs planner vs calibrated
E2  interval coverage on a held-out family: fixed margin vs split conformal
    vs grouped conformal
E3  a second machine: coverage after 0, 3, 5, 10 calibration runs

Usage:  python scripts/run_experiment.py [--jobs 40] [--seeds 3]
Writes results/sim_results.json, results/sim_results.md and
artifacts/calibration_generic-vmc.csv (seed 0, machine A).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ncpreflight.calibration import (FEATURES, Envelope, conformal_quantile, features, grouped_scores,  # noqa: E402
                                     make_model, to_row)
from ncpreflight.gcode import parse  # noqa: E402
from ncpreflight.planner import PROFILES, plan  # noqa: E402
from ncpreflight.simulate import FAMILIES, MACHINE_A, MACHINE_B, generate_program, simulate_run  # noqa: E402

LEVELS = (0.8, 0.9)
PROFILE = PROFILES["generic-vmc"]


def build(n_per_family: int, seed: int) -> dict:
    """Generate programs and simulate each on machines A and B."""
    rng = np.random.default_rng(seed)
    X, fam, nominal, planned, phys = [], [], [], [], []
    truth = {"A": [], "B": []}
    for family in FAMILIES:
        for _ in range(n_per_family):
            text, job = generate_program(family, rng)
            prog = parse(text)
            p = plan(prog, PROFILE)
            f, t_plan, e_phys = features(prog, p, PROFILE, job)
            X.append(to_row(f)); fam.append(family)
            nominal.append(p.nominal); planned.append(t_plan); phys.append(e_phys)
            truth["A"].append(simulate_run(prog, PROFILE, job, MACHINE_A, rng))
            truth["B"].append(simulate_run(prog, PROFILE, job, MACHINE_B, rng))
    d = dict(X=np.array(X), fam=np.array(fam), nominal=np.array(nominal),
             planned=np.array(planned), phys=np.array(phys))
    for k, v in truth.items():
        v = np.array(v)
        d[f"t_{k}"], d[f"e_{k}"] = v[:, 0], v[:, 1]
    return d


def mape(pred, true):
    return float(np.mean(np.abs(pred - true) / true) * 100)


def e1_e2(d: dict, kind: str, rng) -> dict:
    """Leave-one-family-out point error and coverage."""
    out = {"time": {}, "energy": {}}
    for name, base, true in (("time", d["planned"], d["t_A"]), ("energy", d["phys"], d["e_A"])):
        y = np.log(true / base)
        pred = np.zeros(len(y))
        cov = {m: {lv: np.zeros(len(y), bool) for lv in LEVELS} for m in ("fixed10", "split", "grouped")}
        width = {m: {lv: np.zeros(len(y)) for lv in LEVELS} for m in ("split", "grouped")}
        flagged = np.zeros(len(y), bool)
        for family in FAMILIES:
            te = d["fam"] == family
            Xtr, ytr, gtr = d["X"][~te], y[~te], d["fam"][~te]
            model = make_model(kind).fit(Xtr, ytr)
            mu = model.predict(d["X"][te])
            pred[te] = mu
            env = Envelope.fit(Xtr)
            flagged[te] = [bool(env.outside(x)) for x in d["X"][te]]
            # split conformal: random half of the training jobs as calibration set
            idx = rng.permutation(len(ytr))
            fit_i, cal_i = idx[: len(idx) // 2], idx[len(idx) // 2:]
            m_split = make_model(kind).fit(Xtr[fit_i], ytr[fit_i])
            s_split = np.abs(ytr[cal_i] - m_split.predict(Xtr[cal_i]))
            mu_split = m_split.predict(d["X"][te])
            s_group = grouped_scores(Xtr, ytr, gtr, kind)
            for lv in LEVELS:
                q = conformal_quantile(s_split, lv)
                cov["split"][lv][te] = np.abs(y[te] - mu_split) <= q
                width["split"][lv][te] = 2 * math.sinh(q) * 100 if math.isfinite(q) else np.nan
                q = conformal_quantile(s_group, lv)
                cov["grouped"][lv][te] = np.abs(y[te] - mu) <= q
                width["grouped"][lv][te] = 2 * math.sinh(q) * 100 if math.isfinite(q) else np.nan
                cov["fixed10"][lv][te] = np.abs(np.exp(mu) - np.exp(y[te])) / np.exp(y[te]) <= 0.10
        res = {"mape_baseline": mape(base, true), "mape_calibrated": mape(base * np.exp(pred), true),
               "coverage": {}, "width_pct": {}, "coverage_by_family": {}}
        if name == "time":
            res["mape_nominal"] = mape(d["nominal"], true)
        for m in cov:
            res["coverage"][m] = {str(lv): float(cov[m][lv].mean() * 100) for lv in LEVELS}
        for m in width:
            res["width_pct"][m] = {str(lv): float(np.nanmean(width[m][lv])) for lv in LEVELS}
        for family in FAMILIES:
            te = d["fam"] == family
            res["coverage_by_family"][family] = {
                m: float(cov[m][0.9][te].mean() * 100) for m in ("split", "grouped")}
        res["flagged_pct"] = float(flagged.mean() * 100)
        res["flagged_by_family"] = {f: float(flagged[d["fam"] == f].mean() * 100) for f in FAMILIES}
        keep = ~flagged
        res["grouped90_unflagged"] = float(cov["grouped"][0.9][keep].mean() * 100) if keep.any() else float("nan")
        res["grouped90_flagged"] = float(cov["grouped"][0.9][flagged].mean() * 100) if flagged.any() else float("nan")
        res["mape_unflagged"] = mape((base * np.exp(pred))[keep], true[keep]) if keep.any() else float("nan")
        # bootstrap over jobs for the grouped 90 % coverage
        hits = cov["grouped"][0.9]
        boots = [hits[rng.integers(0, len(hits), len(hits))].mean() * 100 for _ in range(2000)]
        res["grouped90_ci95"] = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
        out[name] = res
    return out


def e3(d: dict, kind: str, rng, ks=(0, 3, 5, 10), repeats: int = 200) -> dict:
    """Train on machine A, deploy on machine B with k calibration runs."""
    out = {}
    for name, base, ya, yb in (("time", d["planned"], d["t_A"], d["t_B"]),
                               ("energy", d["phys"], d["e_A"], d["e_B"])):
        y_a, y_b = np.log(ya / base), np.log(yb / base)
        model = make_model(kind).fit(d["X"], y_a)
        scores = grouped_scores(d["X"], y_a, d["fam"], kind)
        q = conformal_quantile(scores, 0.9)
        mu = model.predict(d["X"])
        res = {}
        for k in ks:
            covs, errs = [], []
            for _ in range(repeats if k else 1):
                cal = rng.choice(len(y_b), size=k, replace=False) if k else np.array([], int)
                rest = np.setdiff1d(np.arange(len(y_b)), cal)
                offset = float(np.mean(y_b[cal] - mu[cal])) if k else 0.0
                covs.append(np.mean(np.abs(y_b[rest] - mu[rest] - offset) <= q) * 100)
                errs.append(mape(base[rest] * np.exp(mu[rest] + offset), np.exp(y_b[rest]) * base[rest]))
            res[str(k)] = {"coverage90": float(np.mean(covs)), "coverage90_sd": float(np.std(covs)),
                           "mape": float(np.mean(errs))}
        out[name] = res
    return out


def write_calibration_csv(d: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["source", "label", "group"] + FEATURES + ["log_time_ratio", "log_energy_ratio"])
        for i in range(len(d["fam"])):
            w.writerow(["simulated", "Simulated machine A, 6 synthetic part families", d["fam"][i]]
                       + [f"{v:.6g}" for v in d["X"][i]]
                       + [f"{math.log(d['t_A'][i] / d['planned'][i]):.6g}",
                          f"{math.log(d['e_A'][i] / d['phys'][i]):.6g}"])


def agg(runs: list, path: list):
    vals = []
    for r in runs:
        for key in path:
            r = r[key]
        vals.append(r)
    return float(np.mean(vals)), float(np.std(vals))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", type=int, default=40, help="programs per family")
    ap.add_argument("--seeds", type=int, default=3)
    args = ap.parse_args()
    t0 = time.time()
    results = {"config": {"jobs_per_family": args.jobs, "families": list(FAMILIES),
                          "seeds": args.seeds, "levels": LEVELS, "data": "SIMULATED"},
               "runs": []}
    for seed in range(args.seeds):
        d = build(args.jobs, seed)
        if seed == 0:
            write_calibration_csv(d, ROOT / "artifacts" / "calibration_generic-vmc.csv")
        rng = np.random.default_rng(1000 + seed)
        run = {"seed": seed}
        for kind in ("ridge", "gbr"):
            run[kind] = {"loo_family": e1_e2(d, kind, rng), "new_machine": e3(d, kind, rng)}
        results["runs"].append(run)
        print(f"seed {seed} done in {time.time() - t0:.0f}s", flush=True)

    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "sim_results.json").write_text(json.dumps(results, indent=1))

    R = results["runs"]
    n = args.jobs * len(FAMILIES)
    L = ["# Simulated-machine experiment", "",
         "**All numbers below come from simulated machines and generated programs.** They show how the "
         "method behaves. They are not evidence of accuracy on a real machine.", "",
         f"Setup: {len(FAMILIES)} part families x {args.jobs} programs = {n} jobs per seed, "
         f"{args.seeds} seeds, mean ± standard deviation across seeds. "
         "Every result is for a part family the model did not see in training.", ""]
    for kind in ("ridge", "gbr"):
        L += [f"## Model: {kind}", "", "### E1 Point error on an unseen part family (MAPE, %)", "",
              "| Quantity | Nominal (length / feed) | Physics baseline | Calibrated |", "|---|---|---|---|"]
        for q in ("time", "energy"):
            nom = "%.1f ± %.1f" % agg(R, [kind, "loo_family", q, "mape_nominal"]) if q == "time" else "n/a"
            L.append("| %s | %s | %.1f ± %.1f | %.1f ± %.1f |" % (
                (q, nom) + agg(R, [kind, "loo_family", q, "mape_baseline"])
                + agg(R, [kind, "loo_family", q, "mape_calibrated"])))
        L += ["", "### E2 Interval coverage on an unseen part family (%)", "",
              "| Quantity | Method | Target 80 | Target 90 | Mean width at 90 (% of estimate) |",
              "|---|---|---|---|---|"]
        for q in ("time", "energy"):
            for m, label in (("fixed10", "Fixed ±10 % margin"), ("split", "Split conformal"),
                             ("grouped", "Grouped conformal")):
                c80 = "%.1f ± %.1f" % agg(R, [kind, "loo_family", q, "coverage", m, "0.8"])
                c90 = "%.1f ± %.1f" % agg(R, [kind, "loo_family", q, "coverage", m, "0.9"])
                if m == "fixed10":
                    c80, wd = "n/a", "20"
                else:
                    wd = "%.0f ± %.0f" % agg(R, [kind, "loo_family", q, "width_pct", m, "0.9"])
                L.append(f"| {q} | {label} | {c80} | {c90} | {wd} |")
        L += ["", "Coverage at the 90 % target by held-out family (seed 0):", "",
              "| Family | Time: split | Time: grouped | Energy: split | Energy: grouped |", "|---|---|---|---|---|"]
        for fam in FAMILIES:
            t = R[0][kind]["loo_family"]["time"]["coverage_by_family"][fam]
            e = R[0][kind]["loo_family"]["energy"]["coverage_by_family"][fam]
            L.append(f"| {fam} | {t['split']:.0f} | {t['grouped']:.0f} | {e['split']:.0f} | {e['grouped']:.0f} |")
        L += ["", "Out-of-range flag (a job is flagged when a feature lies outside the calibration range):", "",
              "| Quantity | Jobs flagged (%) | Grouped coverage at 90, not flagged | Grouped coverage at 90, flagged | MAPE, not flagged |",
              "|---|---|---|---|---|"]
        for q in ("time", "energy"):
            L.append("| %s | %.1f ± %.1f | %.1f ± %.1f | %.1f ± %.1f | %.1f ± %.1f |" % (
                (q,) + agg(R, [kind, "loo_family", q, "flagged_pct"])
                + agg(R, [kind, "loo_family", q, "grouped90_unflagged"])
                + agg(R, [kind, "loo_family", q, "grouped90_flagged"])
                + agg(R, [kind, "loo_family", q, "mape_unflagged"])))
        fb = R[0][kind]["loo_family"]["time"]["flagged_by_family"]
        L += ["", "Flagged by family (seed 0, %): " + ", ".join(f"{f} {v:.0f}" for f, v in fb.items())]
        L += ["", "### E3 Second machine: coverage at the 90 % target after k calibration runs", "",
              "| Quantity | k = 0 | k = 3 | k = 5 | k = 10 |", "|---|---|---|---|---|"]
        for q in ("time", "energy"):
            L.append(f"| {q} coverage (%) | " + " | ".join(
                "%.1f ± %.1f" % agg(R, [kind, "new_machine", q, k, "coverage90"]) for k in ("0", "3", "5", "10")) + " |")
            L.append(f"| {q} MAPE (%) | " + " | ".join(
                "%.1f ± %.1f" % agg(R, [kind, "new_machine", q, k, "mape"]) for k in ("0", "3", "5", "10")) + " |")
        L.append("")
    (ROOT / "results" / "sim_results.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
