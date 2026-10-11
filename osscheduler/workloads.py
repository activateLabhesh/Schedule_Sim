"""Named teaching workloads and deterministic random generation."""

from __future__ import annotations

import random

from .models import Process

PRESETS: dict[str, tuple[Process, ...]] = {
    "convoy": (
        Process("P1", 0, 10), Process("P2", 1, 2),
        Process("P3", 2, 1), Process("P4", 3, 2),
    ),
    "starvation": (Process("P1", 0, 2, 9),
        Process("Q2", 0, 3, 0), Process("Q3", 3, 3, 0), Process("Q4", 6, 3, 0),
        Process("Q5", 9, 3, 0), Process("Q6", 12, 3, 0), Process("Q7", 15, 3, 0),
        Process("Q8", 18, 3, 0), Process("Q9", 21, 3, 0), Process("Q10", 24, 3, 0)),
    "aging-fix": (Process("P1", 0, 2, 6),
        Process("Q2", 0, 3, 0), Process("Q3", 3, 3, 0), Process("Q4", 6, 3, 0),
        Process("Q5", 9, 3, 0), Process("Q6", 12, 3, 0), Process("Q7", 15, 3, 0),
        Process("Q8", 18, 3, 0), Process("Q9", 21, 3, 0), Process("Q10", 24, 3, 0)),
    "mixed": (
        Process("P1", 0, 5, 2), Process("P2", 1, 3, 0),
        Process("P3", 2, 7, 4), Process("P4", 4, 2, 1),
    ),
}


def get_preset(name: str) -> tuple[Process, ...]:
    try:
        return PRESETS[name.lower()]
    except KeyError as exc:
        raise ValueError(f"unknown preset: {name}") from exc


def random_workload(count: int, *, seed: int = 0,
                    arrival_range: tuple[int, int] = (0, 10),
                    burst_range: tuple[int, int] = (1, 12),
                    priority_range: tuple[int, int] = (0, 9)) -> tuple[Process, ...]:
    if count < 1:
        raise ValueError("count must be positive")
    rng = random.Random(seed)
    return tuple(Process(f"P{i + 1}", rng.randint(*arrival_range),
                         rng.randint(*burst_range), rng.randint(*priority_range))
                 for i in range(count))


PRESETS["mixed"] = random_workload(6, seed=42)
