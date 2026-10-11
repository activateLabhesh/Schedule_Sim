from __future__ import annotations

from collections.abc import Sequence

from .base import Scheduler
from ..models import Process


class SRTF(Scheduler):
    name = "srtf"
    preemptive = True

    def ready_key(self, process, remaining, priorities, order):
        return (remaining[process.pid], process.pid)

    def choose_with_priorities(self, ready: Sequence[Process], remaining: dict[str, int],
                               running: Process | None, time: int,
                               priorities: dict[str, int]) -> Process | None:
        candidates = list(ready)
        if running is not None:
            candidates.append(running)
        return min(candidates, key=lambda p: (remaining[p.pid], p.pid)) if candidates else None
