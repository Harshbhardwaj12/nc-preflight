"""Unit tests for the parser, planner, checks and conformal layer."""
import math

import numpy as np
import pytest

from ncpreflight.calibration import Calibration, Envelope, conformal_quantile
from ncpreflight.checks import run_checks
from ncpreflight.energy import Job, segment_energy
from ncpreflight.gcode import parse, polyline
from ncpreflight.planner import PROFILES, junction_speed, plan
from ncpreflight.simulate import FAMILIES, MACHINE_A, generate_program, simulate_run

M = PROFILES["generic-vmc"]
HEAD = "G21 G90 G17\nS5000 M3\n"


def codes(text, m=M):
    return {i.code for i in run_checks(parse(text), m)}


# ---------------------------------------------------------------- parser
def test_line_length_and_modal_feed():
    p = parse(HEAD + "G1 X30 Y40 F600\nX60 Y80\n")
    assert [round(s.length, 6) for s in p.moves] == [50.0, 50.0]
    assert p.moves[1].feed == 600 and p.moves[1].kind == "linear"


def test_inch_units_are_converted():
    p = parse("G20 G90\nG1 X1 F10\n")
    assert p.moves[0].length == pytest.approx(25.4)
    assert p.moves[0].feed == pytest.approx(254.0)


def test_incremental_mode():
    p = parse("G21 G91\nG1 X10 F100\nX10\n")
    assert p.moves[-1].end[0] == pytest.approx(20.0)


def test_quarter_arc_ij_length_and_tangents():
    p = parse(HEAD + "G0 X10 Y0\nG3 X0 Y10 I-10 J0 F500\n")
    arc = p.moves[-1]
    assert arc.length == pytest.approx(math.pi * 10 / 2)
    assert np.allclose(arc.u_in, [0, 1, 0], atol=1e-9)
    assert np.allclose(arc.u_out, [-1, 0, 0], atol=1e-9)


def test_full_circle_and_cw_direction():
    p = parse(HEAD + "G0 X10 Y0\nG2 X10 Y0 I-10 J0 F500\n")
    arc = p.moves[-1]
    assert arc.length == pytest.approx(2 * math.pi * 10)
    assert arc.sweep == pytest.approx(-2 * math.pi)


def test_r_format_matches_ij_format():
    a = parse(HEAD + "G0 X10 Y0\nG3 X0 Y10 R10 F500\n").moves[-1]
    b = parse(HEAD + "G0 X10 Y0\nG3 X0 Y10 I-10 J0 F500\n").moves[-1]
    assert a.length == pytest.approx(b.length)
    assert np.allclose(a.center, b.center, atol=1e-9)
    big = parse(HEAD + "G0 X10 Y0\nG3 X0 Y10 R-10 F500\n").moves[-1]
    assert big.length == pytest.approx(1.5 * math.pi * 10)


def test_helical_arc_length():
    arc = parse(HEAD + "G0 X10 Y0\nG3 X10 Y0 Z-5 I-10 J0 F500\n").moves[-1]
    assert arc.length == pytest.approx(math.hypot(2 * math.pi * 10, 5))


def test_comments_line_numbers_and_metadata():
    p = parse("(MATERIAL=STEEL)\nN10 G21 G90 ; setup\nN20 G1 X5 F100 (move)\n")
    assert p.meta["MATERIAL"] == "STEEL" and len(p.moves) == 1 and not p.notes
    assert p.moves[0].line == 3


def test_unsupported_and_unknown_codes_are_reported_not_guessed():
    p = parse("G21 G90\nG83 X1 Y1 Z-5 R1 Q1 F100\nG1 X5 F100\nG77\n")
    kinds = {n.code for n in p.notes}
    assert {"UNSUPPORTED", "UNKNOWN"} <= kinds


def test_polyline_of_arc_stays_on_radius():
    arc = parse(HEAD + "G0 X10 Y0\nG3 X0 Y10 I-10 J0 F500\n").moves[-1]
    pts = polyline(arc)
    assert np.allclose(np.hypot(pts[:, 0], pts[:, 1]), 10.0)
    assert np.allclose(pts[-1], arc.end)


# ---------------------------------------------------------------- planner
def test_long_straight_move_matches_trapezoid_formula():
    p = parse(HEAD + "G1 X600 F6000\n")
    pl = plan(p, M)
    v, a = 100.0, M.accel
    assert pl.total == pytest.approx(600 / v + v / a, rel=1e-9)
    assert pl.nominal == pytest.approx(6.0)


def test_short_move_never_reaches_feed():
    pl = plan(parse(HEAD + "G1 X1 F6000\n"), M)
    assert pl.total == pytest.approx(2 * math.sqrt(1 / M.accel), rel=1e-9)   # triangle profile
    assert pl.v_peak[0] < 100.0


def test_collinear_blocks_take_the_same_time_as_one_block():
    one = plan(parse(HEAD + "G1 X100 F3000\n"), M).total
    many = plan(parse(HEAD + "G1 F3000\n" + "".join(f"X{i}\n" for i in range(1, 101))), M).total
    assert many == pytest.approx(one, rel=1e-6)


def test_corners_cost_time_and_planner_is_never_faster_than_nominal():
    zig = HEAD + "G1 F3000\n" + "".join(f"X{i} Y{i % 2}\n" for i in range(1, 101))
    pl = plan(parse(zig), M)
    assert pl.total > pl.nominal * 1.5
    for fam in FAMILIES:
        text, _ = generate_program(fam, np.random.default_rng(3))
        q = plan(parse(text), M)
        assert q.total >= q.nominal - 1e-6 and np.all(q.seg_time >= 0)


def test_junction_speed_limits():
    x, y = np.array([1.0, 0, 0]), np.array([0, 1.0, 0])
    assert junction_speed(x, x, 2000, 0.02) == math.inf
    assert junction_speed(x, -x, 2000, 0.02) == 0.0
    assert 0 < junction_speed(x, y, 2000, 0.02) < 50


def test_arc_speed_is_limited_by_centripetal_acceleration():
    p = parse(HEAD + "G0 X1 Y0\nG2 X1 Y0 I-1 J0 F6000\n")
    assert plan(p, M).v_peak[-1] <= math.sqrt(M.accel * 1.0) + 1e-9


def test_dwell_and_tool_change_times_are_added():
    pl = plan(parse("G21 G90\nT1 M6\nG4 P2.5\n"), M)
    assert pl.total == pytest.approx(M.toolchange_s + 2.5)


def test_energy_is_at_least_idle_energy_and_cutting_adds_to_it():
    air = parse(HEAD + "G1 X100 Z1 F1000\n")
    cut = parse(HEAD + "G1 Z-1 F1000\nG1 X100\n")
    job = Job()
    e_air = segment_energy(air, plan(air, M), M, job).sum()
    assert e_air >= M.idle_power * plan(air, M).total
    pc = plan(cut, M)
    no_cut = Job(depth_of_cut=0.0)
    assert segment_energy(cut, pc, M, job).sum() > segment_energy(cut, pc, M, no_cut).sum()


# ---------------------------------------------------------------- checks
def test_clean_program_has_no_issues():
    text = HEAD + "G0 Z5\nG0 X0 Y0\nG1 Z-1 F200\nG1 X50 F800\nG0 Z5\nM5\nM30\n"
    assert codes(text) == set()


@pytest.mark.parametrize("text,code", [
    ("G21 G90\nM3 S5000\nG1 X10\nM30\n", "F001"),
    ("G21 G90\nG0 Z5\nG1 Z-1 F100\nM30\n", "S001"),
    (HEAD + "G0 Z-3\nM30\n", "R001"),
    (HEAD + "G1 Z-1 F100\nG0 X20\nM30\n", "R002"),
    (HEAD + "G1 X5000 F100\nM30\n", "L001"),
    (HEAD + "G1 X10 F99999\nM30\n", "F002"),
    ("G21 G90\nS99999 M3\nG1 X10 F100\nM30\n", "S002"),
    (HEAD + "G1 X10 F100\nT2 M6\nM30\n", "T001"),
    ("G90\nG1 X1 F100\nM30\n", "P001"),
    ("G21\nG1 X1 F100\nM30\n", "P002"),
    (HEAD + "G1 X1 F100\n", "P003"),
    (HEAD + "G0 X10 Y0\nG2 X20 Y0 I1 J0 F100\nM30\n", "N-ARC_RADIUS"),
    ("hello world\n", "P004"),
])
def test_each_rule_fires(text, code):
    assert code in codes(text)


def test_repeated_issue_is_summarised():
    text = "G21 G90\nM3 S100\n" + "".join(f"G1 X{i}\n" for i in range(1, 30)) + "M30\n"
    hits = [i for i in run_checks(parse(text), M) if i.code == "F001"]
    assert len(hits) == 5 and "more blocks" in hits[-1].detail


# ---------------------------------------------------------------- conformal
def test_conformal_quantile_finite_sample_rule():
    s = np.arange(1, 10, dtype=float)                 # 9 scores
    assert conformal_quantile(s, 0.8) == 8.0          # ceil(10 * 0.8) = 8th smallest
    assert conformal_quantile(s, 0.9) == 9.0
    assert conformal_quantile(s, 0.95) == math.inf    # not enough scores for this level
    assert conformal_quantile(np.array([]), 0.9) == math.inf


def test_split_conformal_covers_exchangeable_data():
    rng = np.random.default_rng(0)
    hits = []
    for _ in range(300):
        scores = np.abs(rng.normal(size=60))
        hits.append(abs(rng.normal()) <= conformal_quantile(scores, 0.9))
    assert 0.86 <= np.mean(hits) <= 0.95


def test_calibration_interval_brackets_estimate_and_widens_with_level():
    rng = np.random.default_rng(1)
    X = rng.normal(size=(120, 4))
    y = 0.1 * X[:, 0] + rng.normal(scale=0.05, size=120)
    groups = np.repeat(np.arange(6), 20)
    cal = Calibration.fit(X, y, y, groups, kind="ridge")
    r, lo, hi = cal.time.predict(X[0], 0.8)
    r2, lo2, hi2 = cal.time.predict(X[0], 0.95)
    assert lo < r < hi and lo2 <= lo and hi2 >= hi and r == r2


def test_envelope_flags_only_out_of_range_rows():
    X = np.array([[0.0, 0.0], [1.0, 10.0]])
    env = Envelope.fit(X)
    assert env.outside(np.array([0.5, 5.0])) == []
    assert env.outside(np.array([1.05, 5.0])) == []       # inside the 10 % margin
    assert env.outside(np.array([2.0, 5.0])) == [0]


# ---------------------------------------------------------------- simulator
def test_simulated_machine_is_slower_than_the_data_sheet_planner_and_reproducible():
    for fam in FAMILIES:
        text, job = generate_program(fam, np.random.default_rng(7))
        prog = parse(text)
        assert not prog.notes, fam
        t1, e1 = simulate_run(prog, M, job, MACHINE_A, np.random.default_rng(1))
        t2, e2 = simulate_run(prog, M, job, MACHINE_A, np.random.default_rng(1))
        assert (t1, e1) == (t2, e2)
        assert t1 > plan(prog, M).total * 0.97 and e1 > 0
