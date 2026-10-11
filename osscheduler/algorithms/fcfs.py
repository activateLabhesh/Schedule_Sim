from __future__ import annotations

from collections.abc import Sequence

from .base import Scheduler
from ..models import Process


class FCFS(Scheduler):
    name = "fcfs"

    def choose_with_priorities(self, ready: Sequence[Process], remaining: dict[str, int],
                               running: Process | None, time: int,
                               priorities: dict[str, int]) -> Process | None:
        if running is not None:
            return running
        return min(ready, key=lambda p: self.key(p, remaining)) if ready else None
