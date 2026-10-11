"""FastAPI application and JSON API."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .. import analytics, export
from ..algorithms import ALGORITHMS, ALGORITHM_METADATA
from ..engine import simulate
from ..metrics import analyze_result
from ..models import Process
from ..workloads import PRESETS, get_preset
from .schemas import ExportRequest, MonteCarloRequest, SimulationRequest, SweepRequest

app = FastAPI(title="OS Scheduler Lab", version="0.1.0")
STATIC = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC), name="static")


def _processes(items) -> tuple[Process, ...]:
    return tuple(Process(**item.model_dump()) for item in items)


def _json_result(result, starvation_threshold: int = 20):
    value = asdict(result)
    value["analysis"] = analyze_result(result, starvation_threshold=starvation_threshold)
    return value


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/presets")
def presets():
    return {name: [asdict(process) for process in processes]
            for name, processes in PRESETS.items()}


@app.get("/api/algorithms")
def algorithms():
    return ALGORITHM_METADATA


@app.post("/api/simulate")
def run_simulation(request: SimulationRequest):
    try:
        result = simulate(_processes(request.processes), request.algorithm,
                          cores=request.cores, quantum=request.quantum,
                          aging=request.aging, aging_interval=request.aging_interval,
                          aging_step=request.aging_step,
                          context_switch_cost=request.context_switch_cost)
    except (ValueError, KeyError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return _json_result(result, request.starvation_threshold)


@app.post("/api/compare")
def compare(request: SimulationRequest):
    try:
        results = analytics.compare_all(_processes(request.processes), cores=request.cores,
            quantum=request.quantum, aging=request.aging,
            aging_interval=request.aging_interval, aging_step=request.aging_step,
            context_switch_cost=request.context_switch_cost)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {name: _json_result(result, request.starvation_threshold) for name, result in results.items()}


@app.post("/api/montecarlo")
def monte_carlo(request: MonteCarloRequest):
    try:
        if request.arrival_max < request.arrival_min or request.burst_max < request.burst_min or request.priority_max < request.priority_min:
            raise ValueError("each range maximum must be at least its minimum")
        return analytics.monte_carlo(runs=request.runs,
                                     process_count=request.process_count,
                                     seed=request.seed, cores=request.cores,
                                     arrival_range=(request.arrival_min, request.arrival_max),
                                     burst_range=(request.burst_min, request.burst_max),
                                     priority_range=(request.priority_min, request.priority_max))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/quantum-sweep")
def sweep(request: SweepRequest):
    try:
        return analytics.quantum_sweep(_processes(request.processes),
                                       max_quantum=request.max_quantum,
                                       cores=request.cores)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/aging-demo")
def aging_lab(request: SimulationRequest):
    try:
        result = analytics.aging_demo(_processes(request.processes),
                                      aging_interval=request.aging_interval,
                                      aging_step=request.aging_step,
                                      starvation_threshold=request.starvation_threshold)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"without_aging": _json_result(result["without_aging"]),
            "with_aging": _json_result(result["with_aging"]),
            "before": result["before"], "after": result["after"],
            "priority_history": result["priority_history"],
            "waiting_history": result["waiting_history"]}


@app.post("/api/export")
def export_report(request: ExportRequest):
    try:
        result = simulate(_processes(request.processes), request.algorithm,
                          cores=request.cores, quantum=request.quantum,
                          aging=request.aging, aging_interval=request.aging_interval,
                          aging_step=request.aging_step,
                          context_switch_cost=request.context_switch_cost)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    fmt = request.format.lower()
    if fmt == "json":
        return Response(export.to_json(result, starvation_threshold=request.starvation_threshold), media_type="application/json",
                        headers={"Content-Disposition": "attachment; filename=schedule.json"})
    if fmt == "csv":
        return Response(export.to_csv(result, starvation_threshold=request.starvation_threshold), media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=schedule.csv"})
    if fmt == "pdf":
        try:
            payload = export.to_pdf(result, starvation_threshold=request.starvation_threshold)
        except RuntimeError as exc:
            raise HTTPException(500, str(exc)) from exc
        return Response(payload, media_type="application/pdf",
                        headers={"Content-Disposition": "attachment; filename=schedule.pdf"})
    raise HTTPException(422, "format must be csv, json, or pdf")
