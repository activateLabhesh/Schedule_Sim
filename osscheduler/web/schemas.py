from __future__ import annotations

from pydantic import BaseModel, Field


class ProcessInput(BaseModel):
    pid: str = Field(min_length=1)
    arrival_time: int = Field(ge=0)
    burst_time: int = Field(gt=0)
    priority: int = Field(default=0, ge=0)


class SimulationRequest(BaseModel):
    processes: list[ProcessInput] = Field(min_length=1)
    algorithm: str = "fcfs"
    cores: int = Field(default=1, ge=1, le=64)
    quantum: int = Field(default=2, ge=1)
    aging: bool = False
    aging_interval: int = Field(default=5, ge=1)
    aging_step: int = Field(default=1, ge=1)
    context_switch_cost: int = Field(default=0, ge=0)
    starvation_threshold: int = Field(default=20, ge=0)


class MonteCarloRequest(BaseModel):
    runs: int = Field(default=100, ge=1, le=10000)
    process_count: int = Field(default=8, ge=1, le=100)
    seed: int = 0
    cores: int = Field(default=1, ge=1, le=64)
    arrival_min: int = Field(default=0, ge=0)
    arrival_max: int = Field(default=10, ge=0)
    burst_min: int = Field(default=1, ge=1)
    burst_max: int = Field(default=12, ge=1)
    priority_min: int = 0
    priority_max: int = Field(default=9, ge=0)


class SweepRequest(BaseModel):
    processes: list[ProcessInput] = Field(min_length=1)
    max_quantum: int = Field(default=10, ge=1, le=100)
    cores: int = Field(default=1, ge=1, le=64)


class ExportRequest(SimulationRequest):
    format: str = "json"
