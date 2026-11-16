"""Integration tests: the HTTP API and the full analysis path."""
import numpy as np
import pytest
from fastapi.testclient import TestClient

from ncpreflight.api import app
from ncpreflight.simulate import FAMILIES, generate_program

client = TestClient(app)
GOOD = "G21 G90 G17\nS5000 M3\nG0 Z5\nG1 Z-1 F200\nG1 X50 F800\nG0 Z5\nM5\nM30\n"


def test_health_and_config():
    assert client.get("/api/health").json()["status"] == "ok"
    cfg = client.get("/api/config").json()
    by_id = {m["id"]: m for m in cfg["machines"]}
    assert by_id["generic-vmc"]["calibrated"] and by_id["generic-vmc"]["calibration_source"] == "simulated"
    assert not by_id["light-router"]["calibrated"]
    assert cfg["samples"] and "steel" in cfg["materials"]


def test_calibrated_result_is_ordered_and_labelled():
    r = client.post("/api/analyze", json={"program": GOOD}).json()
    t, e = r["time"], r["energy"]
    assert r["ok"] and r["calibration"]["source"] == "simulated"
    assert t["low_s"] < t["estimate_s"] < t["high_s"]
    assert e["low_wh"] < e["estimate_wh"] < e["high_wh"]
    assert t["planned_s"] >= t["nominal_s"] > 0
    assert abs(sum(h["share"] for h in r["hotspots"]) - 1) < 1e-6


def test_higher_confidence_gives_a_wider_range():
    a = client.post("/api/analyze", json={"program": GOOD, "level": 0.8}).json()["time"]
    b = client.post("/api/analyze", json={"program": GOOD, "level": 0.95}).json()["time"]
    assert b["high_s"] - b["low_s"] > a["high_s"] - a["low_s"]
    assert a["estimate_s"] == pytest.approx(b["estimate_s"])


def test_uncalibrated_machine_returns_no_range():
    r = client.post("/api/analyze", json={"program": GOOD, "machine": "light-router"}).json()
    assert r["calibration"]["state"] == "uncalibrated"
    assert r["time"]["low_s"] is None and r["time"]["estimate_s"] == r["time"]["planned_s"]


def test_program_unlike_calibration_jobs_is_flagged():
    r = client.post("/api/analyze", json={"program": GOOD}).json()
    assert r["calibration"]["state"] == "out_of_range" and r["calibration"]["outside"]
    text, _ = generate_program("contour", np.random.default_rng(11))
    assert client.post("/api/analyze", json={"program": text}).json()["calibration"]["state"] == "calibrated"


def test_job_overrides_change_energy_not_time():
    a = client.post("/api/analyze", json={"program": GOOD, "material": "plastic"}).json()
    b = client.post("/api/analyze", json={"program": GOOD, "material": "steel", "depth_of_cut": 4}).json()
    assert b["energy"]["physics_wh"] > a["energy"]["physics_wh"]
    assert a["time"]["planned_s"] == b["time"]["planned_s"]


@pytest.mark.parametrize("body,status", [
    ({"program": "   "}, 422), ({"program": GOOD, "machine": "nope"}, 422),
    ({"program": GOOD, "level": 1.5}, 422), ({"program": GOOD, "material": "wood"}, 422),
    ({"program": GOOD, "tool_diameter": -1}, 422), ({}, 422),
])
def test_bad_requests_are_rejected_with_a_reason(body, status):
    res = client.post("/api/analyze", json=body)
    assert res.status_code == status and res.json()["detail"]


def test_program_without_motion_reports_instead_of_failing():
    r = client.post("/api/analyze", json={"program": "this is not g-code"}).json()
    assert r["ok"] is False and any(i["code"] == "P004" for i in r["issues"])


def test_samples_are_served_and_path_traversal_is_blocked():
    sid = client.get("/api/config").json()["samples"][0]["id"]
    assert "G1" in client.get(f"/api/samples/{sid}").json()["program"]
    assert client.get("/api/samples/..%2Fpyproject.toml").status_code == 404
    assert client.get("/api/samples/missing.nc").status_code == 404


def test_every_family_and_sample_analyses_cleanly():
    for fam in FAMILIES:
        text, _ = generate_program(fam, np.random.default_rng(21))
        r = client.post("/api/analyze", json={"program": text}).json()
        assert r["ok"] and not [i for i in r["issues"] if i["severity"] == "error"], fam
        assert len(r["path"]) <= 6000


def test_static_interface_is_served():
    assert "NC Pre-flight" in client.get("/").text
    assert client.get("/app.js").status_code == 200
