# Blueprint

## 1. Problem and scope

A programmer or estimator in a small machine shop has an NC program and wants to know, before the machine runs it, how long it will take, how much energy it will use, how sure that figure is, and whether the program has an obvious fault.

**In scope:** 3-axis milling programs in ISO G-code; cycle time and drive energy with calibrated ranges; rule-based checks; a web interface; a reproducible evaluation.

**Out of scope:** machine actuation or any write access to a controller; collision checking against stock, fixtures or machine geometry; 4- and 5-axis kinematics; turning; tool wear; wall-plug energy.

## 2. User workflows and acceptance criteria

| Workflow | Accepted when |
|---|---|
| Check a program | Pasting or opening a program and selecting "Check program" returns time, energy, issues and hot-spots in under 2 s for a 5,000-block program |
| Find the faulty block | Selecting an issue or a hot-spot row selects that line in the editor |
| Judge how far to trust the range | The data source (simulated, historical) is visible at all times; an uncalibrated machine shows no range; a program unlike the calibration jobs shows a warning |
| Recover from a failure | An empty program, a rejected request and an unreachable service each show a specific message and keep the program text |
| Know the result is out of date | Editing the program after a check shows a stale-result notice |

## 3. Research questions

- **RQ1** On part families not seen in training, how much does a learned correction reduce time and energy error compared with length ÷ feed and with the physics baseline?
- **RQ2** On unseen part families, do grouped conformal intervals reach their nominal coverage where split conformal intervals and a fixed ±10 % margin do not?
- **RQ3** How many logged runs does a second machine need before intervals trained on the first machine are valid on it?

Hypotheses and success metrics are in `research/research-brief.md` §5–6.

## 4. Requirements

**Functional**

| ID | Requirement | Implemented in | Test |
|---|---|---|---|
| F1 | Parse G0/G1/G2/G3 (IJK and R), G4, G17–19, G20/21, G90/91, F, S, T, M3/4/5/6/8/9/2/30 | `gcode.py` | `test_core.py` parser tests |
| F2 | Report unsupported or unknown codes without guessing | `gcode.py`, `checks.py` | `test_unsupported_and_unknown_codes_are_reported_not_guessed` |
| F3 | Planned time with acceleration and corner limits | `planner.py` | planner tests against closed-form cases |
| F4 | Physics energy baseline | `energy.py` | `test_energy_is_at_least_idle_energy...` |
| F5 | 15 program checks and 7 parser notes with severity, line, explanation and action | `checks.py` | `test_each_rule_fires`, `test_clean_program_has_no_issues` |
| F6 | Calibrated estimate and interval at 80/90/95 % | `calibration.py` | conformal tests, `test_higher_confidence_gives_a_wider_range` |
| F7 | Out-of-range flag | `calibration.py`, `service.py` | `test_program_unlike_calibration_jobs_is_flagged` |
| F8 | No range without calibration data | `service.py` | `test_uncalibrated_machine_returns_no_range` |
| F9 | HTTP API with validation | `api.py` | `test_bad_requests_are_rejected_with_a_reason` |
| F10 | Web interface with all states | `web/` | browser run, screenshots in `docs/screenshots/` |

**Non-functional:** no machine interaction; runs offline on a laptop; data source labelled on every result; inputs limited to 5 MB; no binary model artefacts in the repository; experiment reproducible from one command with fixed seeds.

## 5. Architecture

```
NC text ─▶ gcode.parse ─▶ Program(segments, notes, meta)
                              │
              ┌───────────────┼────────────────┐
              ▼               ▼                ▼
        checks.run_checks  planner.plan   energy.segment_energy
              │               │                │
              │               └──── calibration.features ────┐
              ▼                                              ▼
           issues                          Calibration.predict (ratio, low, high)
              └──────────────── service.Estimator.analyze ───┘
                                       │
                                  api.py (FastAPI)  ◀──▶  web/ (static HTML, CSS, JS)
```

- Each module has one job and depends only on the ones above it. `simulate.py` is used by the experiment and tests, never by the service.
- **Data model:** `Segment` (one block of motion or an event), `Program`, `MachineProfile` (data-sheet values), `Job` (material, tool, depth), `Plan` (per-segment times), `Calibration` (two `Target`s and an `Envelope`).
- **Machine/data interface:** a calibration CSV with one row per logged job. A read-only logger on a real controller would produce the same rows. There is no path from this software to a controller.
- **API:** `GET /api/health`, `GET /api/config`, `GET /api/samples/{id}`, `POST /api/analyze`.

## 6. Technology choices

| Choice | Reason |
|---|---|
| Python, NumPy, scikit-learn | Small, standard, readable; the models are a ridge regression and gradient-boosted trees |
| FastAPI | Typed request validation with little code |
| Static HTML/CSS/JS, no framework | One screen; nothing to build or keep up to date |
| CSV for calibration data | Human-readable, diffable, the same format for simulated and real runs |
| No database | Nothing is stored between requests |

## 7. Evaluation protocol

- **Split by part family**, never by job, so the test family's geometry is unseen (prevents leakage across workpieces).
- **Baselines fixed before building:** length ÷ feed; the physics planner; a fixed ±10 % margin; split conformal.
- **Reported:** MAPE; empirical coverage at 80 % and 90 %; interval width; per-family coverage; bootstrap interval on coverage; mean ± standard deviation over 3 seeds; both model types.
- **Failure analysis:** coverage by family and for flagged versus unflagged jobs.
- **Second machine:** train on machine A, test on machine B after 0, 3, 5 and 10 runs.
- Results are labelled simulated, historical-data, laboratory-machine or live.

## 8. Milestones

| # | Milestone | State |
|---|---|---|
| 1 | Parser, planner, energy, checks, tests | Done |
| 2 | Calibration, simulated machines, experiment | Done |
| 3 | API and interface | Done |
| 4 | Independent review and fixes | See report §8 |
| 5 | Real-data study on the KIT datasets | Not started; needs the data download |

## 9. Definition of done for the real-data study

Extraction script for the KIT archives; the same three experiments on measured time and drive energy; coverage with bootstrap intervals; a section in the report that states plainly whether each hypothesis held.
