from __future__ import annotations

from collections.abc import Sequence

from .base import Scheduler
from ..models import Process


class MultiLevelQueue(Scheduler):
    """Priority classes, each using FCFS, SJF, or RR within its class."""
    name = "mlq"
    preemptive = True

    def __init__(self, class_algorithms: tuple[str, ...] = ("fcfs", "sjf", "rr"), quantum: int = 2):
        if not class_algorithms or any(name not in {"fcfs", "sjf", "rr"} for name in class_algorithms):
            raise ValueError("MLQ classes must use fcfs, sjf, or rr")
        if quantum < 1:
            raise ValueError("quantum must be at least 1")
        self.class_algorithms = class_algorithms
        self.quantum = quantum
        self.level_for_priority: dict[int, int] = {}

    def _class(self, priority: int) -> int:
        if priority not in self.level_for_priority:
            values = sorted(set(self.level_for_priority) | {priority})
            self.level_for_priority = {value: min(i, len(self.class_algorithms) - 1)
                                       for i, value in enumerate(values)}
        return self.level_for_priority[priority]

    def prepare(self, workload: Sequence[Process]) -> None:
        priorities = sorted({process.priority for process in workload})
        self.level_for_priority = {value: min(index, len(self.class_algorithms) - 1)
                                   for index, value in enumerate(priorities)}

    def uses_round_robin(self, process: Process) -> bool:
        return self.class_algorithms[self._class(process.priority)] == "rr"

    def choose_with_priorities(self, ready: Sequence[Process], remaining: dict[str, int],
                               running: Process | None, time: int,
                               priorities: dict[str, int]) -> Process | None:
        candidates = list(ready)
        if running is not None:
            candidates.append(running)
        if not candidates:
            return None
        level = self.level_for_priority
        best_class = min(level[p.priority] for p in candidates)
        group = [p for p in candidates if level[p.priority] == best_class]
        mode = self.class_algorithms[best_class]
        if running in group and mode != "rr":
            return running
        if mode == "sjf":
            return min(group, key=lambda p: (remaining[p.pid], p.arrival_time, p.pid))
        if mode == "rr":
            return group[0]
        return min(group, key=lambda p: (p.arrival_time, p.pid))
