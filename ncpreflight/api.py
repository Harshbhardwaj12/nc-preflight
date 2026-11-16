"""HTTP API and static web interface.

Run:  uvicorn ncpreflight.api:app --port 8000
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .energy import MATERIALS
from .planner import PROFILES
from .service import MAX_PROGRAM_BYTES, Estimator

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
SAMPLES = ROOT / "samples"

app = FastAPI(title="NC Pre-flight", version="0.1.0",
              description="Cycle-time and drive-energy ranges for 3-axis NC programs.")
estimator = Estimator()


class AnalyzeRequest(BaseModel):
    program: str = Field(..., max_length=MAX_PROGRAM_BYTES, description="NC program text")
    machine: str = "generic-vmc"
    level: float = Field(0.9, ge=0.5, le=0.99)
    material: str | None = None
    tool_diameter: float | None = Field(None, gt=0, le=100)
    depth_of_cut: float | None = Field(None, ge=0, le=100)


@app.get("/api/health")
def health():
    return {"status": "ok", "calibrated_machines": sorted(estimator.calibrations)}


@app.get("/api/config")
def config():
    machines = []
    for pid, m in PROFILES.items():
        cal = estimator.calibrations.get(pid)
        machines.append({**m.to_dict(), "calibrated": cal is not None,
                         "calibration_source": cal.source if cal else None,
                         "calibration_jobs": cal.n_jobs if cal else 0})
    samples = [{"id": p.name, "name": p.stem.replace("_", " ")} for p in sorted(SAMPLES.glob("*.nc"))]
    return {"machines": machines, "materials": MATERIALS, "samples": samples}


@app.get("/api/samples/{sample_id}")
def sample(sample_id: str):
    path = (SAMPLES / sample_id).resolve()
    if path.parent != SAMPLES.resolve() or path.suffix != ".nc" or not path.exists():
        raise HTTPException(404, "sample not found")
    return {"id": sample_id, "program": path.read_text()}


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    if not req.program.strip():
        raise HTTPException(422, "The program is empty.")
    try:
        return estimator.analyze(req.program, machine_id=req.machine, level=req.level,
                                 material=req.material, tool_diameter=req.tool_diameter,
                                 depth_of_cut=req.depth_of_cut)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


app.mount("/", StaticFiles(directory=WEB), name="web")
