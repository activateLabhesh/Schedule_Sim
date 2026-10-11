"""Schedule metric calculations."""

from __future__ import annotations

import statistics

from .models import Process, ProcessMetrics


def process_metrics(processes: tuple[Process, ...], first_start: dict[str, int],
                    completion: dict[str, int]) -> tuple[ProcessMetrics, ...]:
    rows = []
    for process in processes:
        finished = completion[process.pid]
        turnaround = finished - process.arrival_time
        waiting = turnaround - process.burst_time
        started = first_start[process.pid]
        rows.append(ProcessMetrics(
            pid=process.pid,
            arrival_time=process.arrival_time,
            burst_time=process.burst_time,
            first_start=started,
            completion_time=finished,
            turnaround_time=turnaround,
            waiting_time=waiting,
            response_time=started - process.arrival_time,
            response_ratio=turnaround / process.burst_time,
        ))
    return tuple(rows)


def summarize(rows: tuple[ProcessMetrics, ...]) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for name in ("waiting_time", "turnaround_time", "response_time"):
        values = [getattr(row, name) for row in rows]
        result[name] = {"mean": statistics.mean(values), "median": statistics.median(values),
                        "min": min(values), "max": max(values),
                        "stdev": statistics.pstdev(values)}
    return result


def fairness(values: list[float] | tuple[float, ...]) -> dict[str, float]:
    """Return Jain fairness and Gini inequality for a non-negative series."""
    data = [max(0.0, float(value)) for value in values]
    if not data:
        return {"jain": 1.0, "gini": 0.0}
    total = sum(data)
    squares = sum(x * x for x in data)
    jain = total * total / (len(data) * squares) if squares else 1.0
    ordered = sorted(data)
    n = len(ordered)
    gini = (2 * sum((i + 1) * value for i, value in enumerate(ordered)) /
            (n * total) - (n + 1) / n) if total else 0.0
    return {"jain": jain, "gini": max(0.0, gini)}


def analyze_result(result, *, starvation_threshold: int = 20) -> dict[str, object]:
    rows = result.processes
    fairness_metrics = fairness(tuple(row.waiting_time for row in rows))
    trace = result.trace
    area = sum(len(snapshot.ready) for snapshot in trace)
    l = area / result.makespan if result.makespan else 0.0
    arrival_rate = len(rows) / result.makespan if result.makespan else 0.0
    w = result.average_waiting_time
    return {
        **fairness_metrics,
        "starvation_threshold": starvation_threshold,
        "starved_processes": [row.pid for row in rows if row.waiting_time > starvation_threshold],
        "little_law": {"L": l, "lambda": arrival_rate, "W": w,
                       "lambda_W": arrival_rate * w,
                       "absolute_error": abs(l - arrival_rate * w)},
    }
