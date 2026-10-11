from __future__ import annotations

from collections.abc import Sequence

from .base import Scheduler
from ..models import Process


class SJF(Scheduler):
    name = "sjf"

    def ready_key(self, process, remaining, priorities, order):
        return (process.burst_time, process.arrival_time, process.pid)

    def choose_with_priorities(self, ready: Sequence[Process], remaining: dict[str, int],
                               running: Process | None, time: int,
                               priorities: dict[str, int]) -> Process | None:
        if running is not None:
            return running
        return min(ready, key=lambda p: (p.burst_time, p.arrival_time, p.pid)) if ready else None
