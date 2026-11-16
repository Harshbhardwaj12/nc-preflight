# Simulated-machine experiment

**All numbers below come from simulated machines and generated programs.** They show how the method behaves. They are not evidence of accuracy on a real machine.

Setup: 6 part families x 40 programs = 240 jobs per seed, 3 seeds, mean ± standard deviation across seeds. Every result is for a part family the model did not see in training.

## Model: ridge

### E1 Point error on an unseen part family (MAPE, %)

| Quantity | Nominal (length / feed) | Physics baseline | Calibrated |
|---|---|---|---|
| time | 22.0 ± 0.2 | 17.8 ± 0.0 | 6.5 ± 3.9 |
| energy | n/a | 30.5 ± 0.2 | 8.9 ± 2.9 |

### E2 Interval coverage on an unseen part family (%)

| Quantity | Method | Target 80 | Target 90 | Mean width at 90 (% of estimate) |
|---|---|---|---|---|
| time | Fixed ±10 % margin | n/a | 86.1 ± 10.5 | 20 |
| time | Split conformal | 56.5 ± 7.9 | 66.5 ± 8.4 | 11 ± 5 |
| time | Grouped conformal | 82.4 ± 3.6 | 86.4 ± 7.3 | 32 ± 19 |
| energy | Fixed ±10 % margin | n/a | 74.9 ± 5.2 | 20 |
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

### E3 Second machine: coverage at the 90 % target after k calibration runs

| Quantity | k = 0 | k = 3 | k = 5 | k = 10 |
|---|---|---|---|---|
| time coverage (%) | 75.1 ± 29.6 | 77.8 ± 17.8 | 78.7 ± 19.1 | 79.5 ± 22.2 |
| time MAPE (%) | 7.2 ± 0.4 | 9.3 ± 1.9 | 8.1 ± 1.0 | 7.5 ± 1.3 |
| energy coverage (%) | 31.4 ± 42.6 | 91.5 ± 3.6 | 92.1 ± 4.3 | 93.0 ± 4.8 |
| energy MAPE (%) | 27.4 ± 0.5 | 9.2 ± 1.5 | 8.4 ± 1.2 | 7.8 ± 1.2 |

## Model: gbr

### E1 Point error on an unseen part family (MAPE, %)

| Quantity | Nominal (length / feed) | Physics baseline | Calibrated |
|---|---|---|---|
| time | 22.0 ± 0.2 | 17.8 ± 0.0 | 6.6 ± 4.4 |
| energy | n/a | 30.5 ± 0.2 | 7.7 ± 2.3 |

### E2 Interval coverage on an unseen part family (%)

| Quantity | Method | Target 80 | Target 90 | Mean width at 90 (% of estimate) |
|---|---|---|---|---|
| time | Fixed ±10 % margin | n/a | 87.9 ± 10.7 | 20 |
| time | Split conformal | 61.5 ± 3.9 | 73.9 ± 4.6 | 11 ± 2 |
| time | Grouped conformal | 78.5 ± 4.4 | 86.2 ± 6.8 | 28 ± 14 |
| energy | Fixed ±10 % margin | n/a | 76.0 ± 7.7 | 20 |
| energy | Split conformal | 69.9 ± 5.5 | 82.8 ± 4.4 | 24 ± 2 |
| energy | Grouped conformal | 77.4 ± 3.2 | 86.4 ± 2.3 | 32 ± 9 |

Coverage at the 90 % target by held-out family (seed 0):

| Family | Time: split | Time: grouped | Energy: split | Energy: grouped |
|---|---|---|---|---|
| pocket | 100 | 100 | 88 | 95 |
| contour | 100 | 100 | 95 | 95 |
| drill | 62 | 65 | 57 | 72 |
| surface | 65 | 80 | 68 | 78 |
| trochoid | 75 | 78 | 72 | 82 |
| engrave | 65 | 95 | 82 | 100 |

Out-of-range flag (a job is flagged when a feature lies outside the calibration range):

| Quantity | Jobs flagged (%) | Grouped coverage at 90, not flagged | Grouped coverage at 90, flagged | MAPE, not flagged |
|---|---|---|---|---|
| time | 51.9 ± 1.4 | 98.0 ± 1.1 | 75.6 ± 13.5 | 2.2 ± 0.0 |
| energy | 51.9 ± 1.4 | 94.0 ± 5.5 | 79.5 ± 8.6 | 4.8 ± 0.7 |

Flagged by family (seed 0, %): pocket 2, contour 0, drill 100, surface 100, trochoid 100, engrave 0

### E3 Second machine: coverage at the 90 % target after k calibration runs

| Quantity | k = 0 | k = 3 | k = 5 | k = 10 |
|---|---|---|---|---|
| time coverage (%) | 77.4 ± 18.4 | 85.4 ± 7.6 | 86.9 ± 8.4 | 82.5 ± 11.5 |
| time MAPE (%) | 7.2 ± 0.5 | 8.7 ± 2.0 | 7.3 ± 1.4 | 7.0 ± 1.3 |
| energy coverage (%) | 2.6 ± 1.7 | 88.8 ± 5.7 | 87.9 ± 6.5 | 88.5 ± 6.0 |
| energy MAPE (%) | 27.4 ± 0.4 | 8.7 ± 1.9 | 8.0 ± 1.7 | 7.6 ± 1.3 |

