"""Shared immutable input and output types for the simulator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class Process:
    pid: str
    arrival_time: int
    burst_time: int
    priority: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.pid, str) or not self.pid:
            raise ValueError("pid must not be empty")
        if any(type(value) is not int for value in
               (self.arrival_time, self.burst_time, self.priority)):
            raise ValueError("arrival_time, burst_time, and priority must be integers")
        if self.arrival_time < 0:
            raise ValueError("arrival_time must be non-negative")
        if self.burst_time <= 0:
            raise ValueError("burst_time must be positive")
        if self.priority < 0:
            raise ValueError("priority must be non-negative")


@dataclass(frozen=True, slots=True)
class GanttBlock:
    pid: str | None
    start: int
    end: int
    core: int = 0
    state: Literal["running", "idle", "switching"] = "running"


@dataclass(frozen=True, slots=True)
class DecisionEvent:
    time: int
    core: int
    message: str


@dataclass(frozen=True, slots=True)
class TickSnapshot:
    time: int
    running: tuple[str | None, ...]
    ready: tuple[str, ...]
    effective_priorities: tuple[tuple[str, int], ...] = ()
    decisions: tuple[str, ...] = ()
    core_states: tuple[str, ...] = ()
    waiting_times: tuple[tuple[str, int], ...] = ()
    events: tuple[DecisionEvent, ...] = ()


@dataclass(frozen=True, slots=True)
class ProcessMetrics:
    pid: str
    arrival_time: int
    burst_time: int
    first_start: int
    completion_time: int
    turnaround_time: int
    waiting_time: int
    response_time: int
    response_ratio: float


@dataclass(frozen=True, slots=True)
class ScheduleResult:
    algorithm: str
    processes: tuple[ProcessMetrics, ...]
    gantt: tuple[GanttBlock, ...]
    trace: tuple[TickSnapshot, ...]
    makespan: int
    average_waiting_time: float
    average_turnaround_time: float
    average_response_time: float
    throughput: float
    cpu_utilization: float
    context_switches: int = 0
    switching_overhead: int = 0
    cores: int = 1
    metric_summary: dict[str, dict[str, float]] | None = None
