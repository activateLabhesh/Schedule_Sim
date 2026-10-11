from __future__ import annotations

from collections.abc import Sequence

from .base import Scheduler
from ..models import Process


class Priority(Scheduler):
    name = "priority"

    def ready_key(self, process, remaining, priorities, order):
        return (priorities.get(process.pid, process.priority), process.pid)

    def choose_with_priorities(self, ready: Sequence[Process], remaining: dict[str, int],
                               running: Process | None, time: int,
                               priorities: dict[str, int]) -> Process | None:
        if running is not None:
            return running
        return min(ready, key=lambda p: (priorities.get(p.pid, p.priority), p.pid)) if ready else None
