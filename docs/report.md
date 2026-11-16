---
title: "NC Pre-flight: cycle-time and drive-energy ranges for CNC programs"
subtitle: "Technical report, version 0.1 (prototype on simulated data)"
date: "16 November 2026"
---

## Abstract

A CAM system reports the cycle time of an NC program as path length divided by programmed feed, and reports no energy figure at all. Both numbers matter for quoting and scheduling in a small machine shop, and neither comes with an indication of how far it can be trusted. NC Pre-flight parses a 3-axis NC program, estimates cycle time and drive energy with a physics-based model, corrects the estimate with a model learned from logged runs, and reports a range built with conformal prediction. It also runs rule-based checks on the program.

This version is a **prototype evaluated on simulated machines only**. On simulated part families the model had not seen, the learned correction reduced time error from 17.8 % to 6.6 % and energy error from 30.5 % to 7.7 %. The ranges did not reach their 90 % target on unseen families (86 %), and a simple offset did not make ranges valid on a second simulated machine. A range check that flags programs unlike the calibration jobs separated reliable results (94–98 % coverage) from unreliable ones (76–80 %). None of these figures is evidence about a real machine. A study on open measured data from two real machines is the next step.

## 1. Problem background

In a job shop, a program is written in CAM, set up on the machine, proved out, and then run. The time estimate used for the quote and the schedule comes from CAM. That estimate ignores acceleration limits, so it is too low wherever the path has short blocks or corners. The energy used per part is normally not estimated. The programmer finds program faults during prove-out, with the machine idle.

The user this project addresses is the programmer or estimator of a small shop. The assumed buyer is the shop owner. These are assumptions: no interviews were held (see §8).

## 2. Literature review and research gap

The full search log and a 42-row literature matrix are in `docs/research/`. The review used Scopus through an institutional session plus open sources. Seventeen matrix rows are Scopus records whose full text has not been read, so the review is partly verified.

What the reviewed work establishes:

- Energy and power can be predicted from G-code on a single machine (matrix rows 1–7).
- Cycle time can be corrected with learned feed-rate behaviour (rows 8–10).
- One group (KIT wbk) predicts axis signals from NC code, has published open datasets with the executed NC programs and measured controller signals from two machines, and reports that generalising to unseen parts is not yet solved (rows 4 and 12).

The gap, within the reviewed scope:

- The models reviewed give point values. A Scopus query for conformal prediction with any machining term returned four records, none about machining time or energy. That is one query and is not proof of absence.
- Evaluation is mostly on parts similar to the training parts and on one machine.

## 3. Objectives, hypotheses and claimed contribution

**Objective.** Give a cycle-time and drive-energy estimate with a range whose reliability is measured on kinds of parts the model has not seen.

| | Hypothesis | Result on simulated data |
|---|---|---|
| H1 | A learned correction on top of the physics model reduces error on unseen part families | Supported (§7.1) |
| H2 | Grouped conformal ranges reach nominal coverage on unseen families where split conformal ranges and a fixed margin do not | Partly: closer than both, but below target (§7.2) |
| H3 | Fewer than ten runs on a second machine restore valid coverage | Not supported with a constant offset (§7.4) |

**Claimed contribution, bounded.** A working pipeline and an evaluation protocol (hold out whole part families; compare coverage, not only error; test a second machine). The contribution is the method and protocol. There is no claim of accuracy on real machines, of being first, or of publishability, until the measured-data study is done.

## 4. Requirements and architecture

Requirements, the architecture diagram, the data model and the trace from requirement to module to test are in `docs/blueprint.md`. In brief:

```
NC text → parser → segments → planner (time) and energy model
                            → features → learned correction → range
                            → rule checks
        → service → HTTP API → web interface
```

The software has no connection to a machine controller. Its only machine-side interface is a CSV file of logged runs.

## 5. Implementation and key decisions

- **Parser** (`gcode.py`). Covers linear and circular moves in all three planes, helical arcs, inch and millimetre units, absolute and incremental modes. Anything it does not support is reported and left out. A block that sets an offset (G92, G10, G52) or returns to reference (G28) is skipped, because treating its axis words as a target would invent a move.
- **Planner** (`planner.py`). A look-ahead planner with constant acceleration. Corner speed follows the junction-deviation model; arc speed is limited by centripetal acceleration. It was checked against closed-form results: a 600 mm line at 6,000 mm/min takes length ÷ speed plus speed ÷ acceleration; a 1 mm move follows a triangular profile.
- **Energy** (`energy.py`). Idle, no-load spindle, axis motion and cutting power, integrated over the planned times. Cutting power uses handbook specific cutting energies and an assumed radial engagement of half the tool diameter.
- **Correction** (`calibration.py`). The target is log(measured ÷ baseline), so the correction is a ratio and ranges stay positive. Two models are supported: ridge regression and gradient-boosted trees. The trees are the default: their energy ranges were half as wide (32 % against 64 % of the estimate) at lower coverage (86 % against 92 %), and they failed less badly on the hardest family (65 % against 0 % coverage).
- **Ranges.** Residuals are collected by leaving out one part family at a time, so each residual is an error on an unseen kind of part. The range is the estimate times exp(±q), where q is the conformal quantile of those residuals. With few families this has no coverage guarantee; §7 measures what it gives.
- **Range check.** A program is flagged when any feature lies more than 10 % outside the range of the calibration jobs.
- **No binary model files.** The model is rebuilt at start-up from the calibration CSV in about 2.5 s.
- **Interface.** One screen. The data source is shown at all times. Uncalibrated machines show no range.

## 6. Experimental setup

**All data is simulated.**

- **Programs.** Six generated part families (pocket, contour, peck drilling, 3D surface, trochoidal slot, engraving), 40 programs each, with random size, feed, spindle speed, material, tool and depth.
- **Simulated machines.** Two machines, A and B. Each is the planner run with hidden parameters (lower usable acceleration, tighter corner tolerance) plus effects the estimator does not model: jerk limiting, block processing time, exact stops between rapid and feed, spindle ramps, axis and spindle inertia, a different cutting engagement per job, and noise.
- **Baselines.** Length ÷ feed; the physics model; a fixed ±10 % margin; split conformal.
- **Protocol.** Leave one family out; 3 data seeds; mean ± standard deviation over seeds.
- **Metrics.** Mean absolute percentage error (MAPE); share of held-out jobs inside the range at 80 % and 90 %; range width.

**Circularity.** The simulated machine and the estimator share the planner code. The correction therefore learns a gap that is easier than the real one. The error figures below are optimistic for that reason.

## 7. Results (simulated)

Full tables for both models are in `results/sim_results.md`. Figures here are for the default model.

### 7.1 Point error on an unseen family

| Quantity | Length ÷ feed | Physics model | Corrected |
|---|---|---|---|
| Time, MAPE | 22.0 % | 17.8 % | 6.6 ± 4.4 % |
| Energy, MAPE | n/a | 30.5 % | 7.7 ± 2.3 % |

### 7.2 Coverage on an unseen family, 90 % target

| Method | Time | Energy | Width (time) |
|---|---|---|---|
| Fixed ±10 % margin | 87.9 % | 76.0 % | 20 % |
| Split conformal | 67.2 % | 81.1 % | 11 % |
| Grouped conformal | 86.2 ± 6.8 % | 86.4 ± 2.3 % | 28 % |

Grouped conformal came closest to the target on both quantities and still fell short. The fixed margin did as well for time, which means that for time the grouped method bought no coverage over a plain ±10 % here and cost wider ranges.

### 7.3 Failure cases

- Coverage by family (seed 0, time): pocket 100 %, contour 100 %, engraving 95 %, surface 80 %, trochoid 78 %, drilling 65 %. With the ridge model, drilling fell to 0 %.
- Drilling is dominated by rapid moves and short plunges, which no other family contains. The model extrapolates.
- The range check flagged 52 % of held-out jobs: all drilling, surface and trochoid jobs. Coverage was 98.0 % (time) and 94.0 % (energy) for jobs not flagged, and 75.6 % and 79.5 % for flagged jobs.
- One hard family sets the pooled range width, so easy families get ranges wider than they need.

### 7.4 Second machine

The model is trained on machine A without one family, then tested on that family on machine B. A constant offset is fitted from k runs of other families on machine B.

| | k = 0 | k = 3 | k = 5 | k = 10 |
|---|---|---|---|---|
| Time coverage | 71.8 % | 71.2 % | 71.8 % | 69.5 % |
| Energy coverage | 14.6 % | 77.8 % | 77.1 % | 77.9 % |

A constant offset fixes most of the energy bias and does nothing for time. Neither reaches 90 %. H3 is not supported. The next thing to try is refitting the residual scores, or the model, on the second machine's runs.

### 7.5 Limitations

- Simulated data only, with the circularity described in §6.
- Six families. The ± values are spread across seeds with the same families and understate the uncertainty about a new family.
- No coverage guarantee for the grouped method.
- 3-axis milling; canned cycles and cutter compensation are not simulated.
- Stock top is assumed at Z0 for the checks and for cutting power.
- The checks are rules and catch what their author anticipated.

## 8. Verification, review and commercial assessment

**Tests.** 79 automated tests: parser geometry, planner against closed-form cases, each check rule, the conformal quantile, the API, and regression tests for review findings. The interface was driven in a browser through its empty, loading, result, stale, fault, uncalibrated, out-of-range, empty-input and disconnected states; screenshots are in `docs/screenshots/`.

**Independent review.** A separate reviewer agent that had not seen the code being written reviewed it. It found no blockers and nine major issues. All nine were fixed:

| Finding | Fix |
|---|---|
| The second-machine experiment tested on programs the model had trained on | Family is now held out; coverage fell from about 85 % to about 72 % |
| Grouped conformal described as if it guaranteed coverage | Described as a heuristic; shortfall reported |
| Shared planner code between simulator and estimator not disclosed in results | Disclosed in the results file and here |
| Offset and reference-return blocks created phantom moves; canned-cycle positions ran as moves | Such blocks are skipped and reported |
| Dwell `P` read as seconds | Integer `P` of 100 or more is read as milliseconds and reported for checking |
| Values from program comments bypassed validation | Validated, with defaults on failure |
| Very large numbers crashed the service | Rejected per block |
| A stale-result notice replaced the unreliable-range warning | Both are shown |

Minor findings fixed: block limit, mismatched arcs left out of the estimate, unknown address letters reported, path colouring relative to programmed feed, duplicate labels, missing tests. Not fixed: analysis is synchronous, so a 150,000-line program blocks one worker for several seconds.

The first review attempt stopped at a usage limit and was restarted on a different model.

**Commercial assessment.** Evidence is thin and stated as such.

- Sourced: machine monitoring is sold per machine per month (one vendor publishes £72–180 plus a £200 device); an independent US survey of 335 manufacturers names lack of expertise (61 %) and cost (54 %) as the main barriers to adoption.
- Not found: India-specific adoption figures; independent figures for the cost of wrong time estimates.
- Hypotheses: an estimator would pay a low monthly per-seat price for time ranges that hold; the need for logged runs from each machine is the main adoption barrier.
- Route to a pilot: the measured-data study, then read-only logging on one real machine with the shop's permission and a qualified person on site.

**Readiness: prototype.** The software works end to end and is tested. Its accuracy is unknown, because no measured data has been used. It is not a validated demonstrator and not ready for a pilot.

## 9. Conclusions and future work

The pipeline works, and the evaluation protocol exposed two things a simpler evaluation would have hidden: ranges calibrated on a random split are badly over-confident on new kinds of parts, and a range check is needed to tell the user when not to trust the range.

Next, in order:

1. **Measured data.** Two open datasets from KIT (CC BY 4.0; DOIs 10.35097/hvvwn1kfwf7qt48z and 10.35097/vnnu3n9z7ndsnhfd) contain 87 experiments on two machines with the executed NC programs and 500 Hz controller signals. They are 44.6 GB and 55.2 GB and have not been downloaded. Repeat §7 on them.
2. Refit residual scores on the second machine instead of a constant offset.
3. Scale ranges per job so easy programs get narrow ranges.
4. A simulator that does not share the planner.

## 10. Reproduction

```bash
pip install -r requirements.txt
python -m pytest -q
python scripts/run_experiment.py --jobs 40 --seeds 3
uvicorn ncpreflight.api:app --port 8000
```

## 11. Explaining the project in two minutes

> CAM software tells you how long a CNC program will take by dividing path length by feed rate. That ignores acceleration, so it is wrong wherever the path has corners or short moves, and it gives you one number with no idea how wrong it might be. I built a tool that reads the program, simulates how a machine would accelerate through it, learns the remaining gap from logged runs, and gives the answer as a range.
>
> The part I would defend is the evaluation. I held out whole kinds of parts, not random jobs, and measured how often the true value fell inside the range. The standard way of building ranges looked fine on a random split and covered only about 67 % at a 90 % target on new kinds of parts. Calibrating on held-out part families brought that to about 86 %, which is better and still short. So I added a check that tells the user when a program is unlike anything the tool has seen, and on the remaining programs coverage was 94 to 98 %.
>
> All of that is on a simulated machine that shares code with my estimator, so the numbers are optimistic. The next step is measured data from two real machines published by KIT. Until then it is a prototype.

Likely questions:

- *Why not a neural network?* About 240 jobs. A small tree model on physics features is enough, and the simplest model that supports the claim is easier to defend.
- *Why conformal prediction?* It makes no assumption about the error distribution and it is checkable: you count how often the truth is inside the range.
- *Why does it miss the target?* The guarantee needs new jobs to resemble calibration jobs. A new part family breaks that, and six families are too few to calibrate at family level.
- *What is new compared with the KIT work?* They predict signals from NC code. This adds ranges with measured coverage on unseen parts and a second machine. That difference is unproven until it is run on their data.

## References

See `docs/research/literature-matrix.md` (42 entries with DOI or locator, Scopus status and read depth) and `docs/research/research-brief.md` §8.
