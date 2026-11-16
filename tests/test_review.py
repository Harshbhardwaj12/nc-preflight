"""Regression tests for defects found by the independent review."""
import math

import numpy as np
import pytest
from fastapi.testclient import TestClient

from ncpreflight.api import app
from ncpreflight.energy import Job
from ncpreflight.gcode import parse
from ncpreflight.planner import PROFILES, plan

client = TestClient(app)
HEAD = "G21 G90 G17\nS5000 M3\n"
M = PROFILES["generic-vmc"]


@pytest.mark.parametrize("block", ["G92 X0 Y0", "G10 L2 P1 X100 Y100", "G52 X10 Y10", "G28 X0 Y0 Z0"])
def test_non_motion_blocks_do_not_create_phantom_moves(block):
    p = parse(HEAD + "G0 X50 Y50\n" + block + "\nG1 X60 F500\n")
    assert [round(s.length, 3) for s in p.moves] == [round(math.hypot(50, 50), 3), 10.0]
    assert any(n.code == "SKIPPED" for n in p.notes)


def test_canned_cycle_positions_are_skipped_until_cancelled():
    p = parse(HEAD + "G0 Z5\nG81 X10 Y10 Z-5 R1 F100\nX20\nX30\nG80\nG0 X40 Y0\n")
    assert all(s.end[2] >= 0 for s in p.moves)            # no plunge to Z-5 was invented
    assert len(p.moves) == 2 and p.moves[-1].kind == "rapid"
    codes = {i["code"] for i in client.post("/api/analyze", json={"program": HEAD + "G0 Z5\nG81 X10 Y10 Z-5 R1 F100\nG80\nG0 X5\nM30\n"}).json()["issues"]}
    assert "R001" not in codes and "N-UNSUPPORTED" in codes


def test_dwell_p_integer_is_read_as_milliseconds_and_reported():
    p = parse("G21 G90\nG4 P1000\nG4 P2.5\nG4 X3\n")
    assert [s.dwell for s in p.segments] == [1.0, 2.5, 3.0]
    assert sum(n.code == "DWELL" for n in p.notes) == 2


def test_mismatched_arc_is_left_out_of_the_estimate():
    p = parse(HEAD + "G0 X0 Y0\nG2 X10 Y0 I1 J0 F100\n")
    assert not [s for s in p.moves if s.kind == "arc"]


def test_unknown_address_letter_is_reported():
    assert any("letter E" in n.message for n in parse("G21 G90\nG1 X1e5 F100\n").notes)


@pytest.mark.parametrize("meta", ["(TOOL_D=-5)(AP=nan)", "(TOOL_D=1e400)", "(AP=inf)", "(TOOL_D=abc)"])
def test_implausible_comment_metadata_falls_back_to_defaults(meta):
    job = Job.from_meta(parse(meta + "\nG21\n").meta)
    assert job.tool_diameter == 10.0 or job.depth_of_cut == 2.0
    assert math.isfinite(job.tool_diameter) and math.isfinite(job.depth_of_cut)
    r = client.post("/api/analyze", json={"program": meta + "\n" + HEAD + "G1 Z-1 F100\nG1 X20\nM30\n"})
    assert r.status_code == 200 and r.json()["ok"]


@pytest.mark.parametrize("word", ["T" + "9" * 400, "M" + "9" * 400, "X" + "9" * 400, "G4 P" + "9" * 400])
@pytest.mark.parametrize("machine", ["generic-vmc", "light-router"])
def test_huge_numbers_are_rejected_block_by_block(word, machine):
    r = client.post("/api/analyze", json={"program": HEAD + "G1 X10 F100\n" + word + "\nG1 X20\nM30\n", "machine": machine})
    assert r.status_code == 200
    body = r.json()
    assert math.isfinite(body["time"]["estimate_s"]) and any(i["code"] == "N-BAD_NUMBER" for i in body["issues"])


def test_too_many_lines_is_rejected_with_a_reason():
    r = client.post("/api/analyze", json={"program": "G1 X1 F100\n" * 150_001})
    assert r.status_code == 422 and "lines" in r.json()["detail"]


def test_traversal_to_another_nc_file_is_blocked():
    assert client.get("/api/samples/..%2Fsamples%2F..%2Fx.nc").status_code == 404
    assert client.get("/api/samples/%2Fetc%2Fpasswd.nc").status_code == 404


def test_every_sample_program_analyses():
    for s in client.get("/api/config").json()["samples"]:
        text = client.get("/api/samples/" + s["id"]).json()["program"]
        assert client.post("/api/analyze", json={"program": text}).json()["ok"], s["id"]


def test_out_of_range_labels_are_not_repeated():
    out = client.post("/api/analyze", json={"program": HEAD + "G1 X1 F100\nM30\n"}).json()["calibration"]["outside"]
    assert len(out) == len(set(out))


def test_slow_flag_compares_with_the_programmed_feed():
    r = client.post("/api/analyze", json={"program": HEAD + "G1 X300 F300\nG1 Y1 F9000\nM30\n"}).json()
    slow = {p["line"]: p["slow"] for p in r["path"]}
    assert slow[3] == 0 and slow[4] == 1       # slow feed held; fast feed never reached on 1 mm
