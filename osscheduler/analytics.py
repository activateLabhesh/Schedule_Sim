"""Algorithm comparison, Monte Carlo analysis, and RR quantum sweeps."""

from __future__ import annotations

import statistics

from .algorithms import ALGORITHMS
from .engine import simulate
from .models import Process
from .workloads import random_workload
from .metrics import analyze_result


def compare_all(processes: tuple[Process, ...] | list[Process], **options) -> dict[str, object]:
    return {name: simulate(processes, name, **options) for name in ALGORITHMS}


def monte_carlo(*, runs: int = 100, process_count: int = 8, seed: int = 0,
                arrival_range: tuple[int, int] = (0, 10),
                burst_range: tuple[int, int] = (1, 12),
                priority_range: tuple[int, int] = (0, 9),
                **options) -> dict[str, object]:
    if runs < 1:
        raise ValueError("runs must be positive")
    names = tuple(ALGORITHMS)
    samples: dict[str, list[float]] = {name: [] for name in names}
    wins = dict.fromkeys(names, 0)
    for index in range(runs):
        workload = random_workload(process_count, seed=seed + index,
                                   arrival_range=arrival_range, burst_range=burst_range,
                                   priority_range=priority_range)
        results = {name: simulate(workload, name, **options) for name in names}
        for name, result in results.items():
            samples[name].append(result.average_waiting_time)
        winner = min(names, key=lambda name: (results[name].average_waiting_time, name))
        wins[winner] += 1
    return {name: {"mean": statistics.mean(values), "median": statistics.median(values),
                   "stdev": statistics.stdev(values) if len(values) > 1 else 0.0,
                   "min": min(values), "max": max(values), "win_rate": wins[name] / runs,
                   "samples": values}
            for name, values in samples.items()}


def quantum_sweep(processes: tuple[Process, ...] | list[Process], *,
                  max_quantum: int = 10, cores: int = 1,
                  context_switch_cost: int = 0) -> dict[str, object]:
    if max_quantum < 1:
        raise ValueError("max_quantum must be positive")
    points = []
    for quantum in range(1, max_quantum + 1):
        result = simulate(processes, "rr", quantum=quantum, cores=cores,
                          context_switch_cost=context_switch_cost)
        points.append({"quantum": quantum,
                       "average_waiting_time": result.average_waiting_time,
                       "average_turnaround_time": result.average_turnaround_time,
                       "response_time": result.average_response_time})
    optimum = min(points, key=lambda point: point["average_waiting_time"])
    return {"points": points, "optimum_quantum": optimum["quantum"]}


def aging_demo(processes: tuple[Process, ...] | list[Process], *,
               aging_interval: int = 3, aging_step: int = 2,
               starvation_threshold: int = 20) -> dict[str, object]:
    plain = simulate(processes, "priority")
    aged = simulate(processes, "priority", aging=True,
                    aging_interval=aging_interval, aging_step=aging_step)
    history = [{"time": tick.time, **dict(tick.effective_priorities)} for tick in aged.trace]
    waiting_history = [{"time": tick.time, **dict(tick.waiting_times)} for tick in aged.trace]
    return {"without_aging": plain, "with_aging": aged,
            "before": analyze_result(plain, starvation_threshold=starvation_threshold),
            "after": analyze_result(aged, starvation_threshold=starvation_threshold),
            "priority_history": history, "waiting_history": waiting_history}
