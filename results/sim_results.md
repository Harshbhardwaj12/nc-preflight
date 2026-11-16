# Simulated-machine experiment

**All numbers below come from simulated machines and generated programs.** They show how the method behaves. They are not evidence of accuracy on a real machine.

Setup: 6 part families x 40 programs = 240 jobs per seed, 3 seeds, mean ± standard deviation across seeds. Every result is for a part family the model did not see in training.

## Read this first

- **The simulated machine shares code with the estimator.** Its motion comes from the same planner run with hidden parameters, plus jerk, block-time, exact-stop, spindle-ramp, inertia and engagement effects the estimator does not model. The learned correction therefore has an easier job here than on a real machine, and the error figures are optimistic.
- **Grouped conformal has no coverage guarantee here.** Scores are pooled from five training families. With so few families the result is an empirical check, and it missed the 90 % target for time. One hard family sets the pooled interval width, so easy families get intervals wider than they need.
- **± is the spread over data seeds** with the same six families. It understates the uncertainty about a seventh, different family.

## Model: ridge

### E1 Point error on an unseen part family (MAPE, %)

| Quantity | Nominal (length / feed) | Physics baseline | Calibrated |
|---|---|---|---|
| time | 22.0 ± 0.2 | 17.8 ± 0.0 | 6.5 ± 3.9 |
| energy | n/a | 30.5 ± 0.2 | 8.9 ± 2.9 |

### E2 Interval coverage on an unseen part family (%)

| Quantity | Method | Target 80 | Target 90 | Mean width at 90 (% of estimate) |
|---|---|---|---|---|
| time | Fixed ±10 % margin (targets no level) | n/a | 86.1 ± 10.5 | 20 |
| time | Split conformal | 56.5 ± 7.9 | 66.5 ± 8.4 | 11 ± 5 |
| time | Grouped conformal | 82.4 ± 3.6 | 86.4 ± 7.3 | 32 ± 19 |
| energy | Fixed ±10 % margin (targets no level) | n/a | 74.9 ± 5.2 | 20 |
| energy | Split conformal | 59.6 ± 7.4 | 71.7 ± 6.5 | 21 ± 4 |
| energy | Grouped conformal | 86.8 ± 6.7 | 91.7 ± 5.8 | 64 ± 5 |

Coverage at the 90 % target by held-out family (seed 0):

| Family | Time: split | Time: grouped | Energy: split | Energy: grouped |
|---|---|---|---|---|
| pocket | 100 | 100 | 90 | 100 |
| contour | 92 | 100 | 92 | 100 |
| drill | 5 | 0 | 8 | 5 |
| surface | 35 | 82 | 42 | 100 |
| trochoid | 80 | 100 | 65 | 100 |
| engrave | 35 | 100 | 78 | 100 |

Out-of-range flag (a job is flagged when a feature lies outside the calibration range):

| Quantity | Jobs flagged (%) | Grouped coverage at 90, not flagged | Grouped coverage at 90, flagged | MAPE, not flagged |
|---|---|---|---|---|
| time | 51.9 ± 1.4 | 99.1 ± 1.2 | 74.6 ± 15.3 | 2.8 ± 0.9 |
| energy | 51.9 ± 1.4 | 98.6 ± 1.5 | 85.1 ± 12.9 | 4.8 ± 1.1 |

Flagged by family (seed 0, %): pocket 2, contour 0, drill 100, surface 100, trochoid 100, engrave 0

### E3 Second machine: held-out family, coverage at the 90 % target after k runs on that machine

The k runs on the second machine come from the other families.

| Quantity | k = 0 | k = 3 | k = 5 | k = 10 |
|---|---|---|---|---|
| time coverage (%) | 66.7 ± 14.1 | 68.7 ± 6.0 | 70.4 ± 6.5 | 69.3 ± 9.3 |
| time MAPE (%) | 10.9 ± 3.1 | 13.2 ± 4.3 | 12.3 ± 5.0 | 11.9 ± 4.6 |
| energy coverage (%) | 42.9 ± 19.6 | 86.1 ± 6.9 | 85.8 ± 4.4 | 87.6 ± 5.5 |
| energy MAPE (%) | 25.8 ± 0.5 | 13.5 ± 4.2 | 13.8 ± 4.5 | 12.6 ± 3.8 |

## Model: gbr

### E1 Point error on an unseen part family (MAPE, %)

| Quantity | Nominal (length / feed) | Physics baseline | Calibrated |
|---|---|---|---|
| time | 22.0 ± 0.2 | 17.8 ± 0.0 | 6.6 ± 4.4 |
| energy | n/a | 30.5 ± 0.2 | 7.7 ± 2.3 |

### E2 Interval coverage on an unseen part family (%)

| Quantity | Method | Target 80 | Target 90 | Mean width at 90 (% of estimate) |
|---|---|---|---|---|
| time | Fixed ±10 % margin (targets no level) | n/a | 87.9 ± 10.7 | 20 |
| time | Split conformal | 57.6 ± 1.7 | 67.2 ± 2.2 | 11 ± 3 |
| time | Grouped conformal | 78.5 ± 4.4 | 86.2 ± 6.8 | 28 ± 14 |
| energy | Fixed ±10 % margin (targets no level) | n/a | 76.0 ± 7.7 | 20 |
| energy | Split conformal | 66.8 ± 4.3 | 81.1 ± 6.2 | 25 ± 1 |
| energy | Grouped conformal | 77.4 ± 3.2 | 86.4 ± 2.3 | 32 ± 9 |

Coverage at the 90 % target by held-out family (seed 0):

| Family | Time: split | Time: grouped | Energy: split | Energy: grouped |
|---|---|---|---|---|
| pocket | 95 | 100 | 95 | 95 |
| contour | 95 | 100 | 98 | 95 |
| drill | 40 | 65 | 42 | 72 |
| surface | 62 | 80 | 78 | 78 |
| trochoid | 62 | 78 | 70 | 82 |
| engrave | 65 | 95 | 98 | 100 |

Out-of-range flag (a job is flagged when a feature lies outside the calibration range):

| Quantity | Jobs flagged (%) | Grouped coverage at 90, not flagged | Grouped coverage at 90, flagged | MAPE, not flagged |
|---|---|---|---|---|
| time | 51.9 ± 1.4 | 98.0 ± 1.1 | 75.6 ± 13.5 | 2.2 ± 0.0 |
| energy | 51.9 ± 1.4 | 94.0 ± 5.5 | 79.5 ± 8.6 | 4.8 ± 0.7 |

Flagged by family (seed 0, %): pocket 2, contour 0, drill 100, surface 100, trochoid 100, engrave 0

### E3 Second machine: held-out family, coverage at the 90 % target after k runs on that machine

The k runs on the second machine come from the other families.

| Quantity | k = 0 | k = 3 | k = 5 | k = 10 |
|---|---|---|---|---|
| time coverage (%) | 71.8 ± 4.3 | 71.2 ± 0.4 | 71.8 ± 0.5 | 69.5 ± 3.3 |
| time MAPE (%) | 10.0 ± 2.8 | 13.2 ± 3.7 | 11.9 ± 3.6 | 11.8 ± 3.6 |
| energy coverage (%) | 14.6 ± 15.5 | 77.8 ± 3.7 | 77.1 ± 4.1 | 77.9 ± 4.4 |
| energy MAPE (%) | 26.3 ± 1.4 | 12.7 ± 1.9 | 11.6 ± 1.5 | 11.0 ± 1.3 |

