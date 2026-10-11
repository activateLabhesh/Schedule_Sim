from __future__ import annotations

from collections.abc import Sequence

from .base import Scheduler
from ..models import Process


class RoundRobin(Scheduler):
    name = "rr"
    preemptive = True

    def __init__(self, quantum: int = 2):
        if quantum < 1:
            raise ValueError("quantum must be at least 1")
        self.quantum = quantum

    def choose_with_priorities(self, ready: Sequence[Process], remaining: dict[str, int],
                               running: Process | None, time: int,
                               priorities: dict[str, int]) -> Process | None:
        if running is not None:
            return running
        return ready[0] if ready else None

    def uses_round_robin(self, process: Process) -> bool:
        return True
