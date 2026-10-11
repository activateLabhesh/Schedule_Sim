"""Scheduling policy interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from ..models import Process


class Scheduler(ABC):
    name = "scheduler"
    preemptive = False

    def key(self, process: Process, remaining: dict[str, int]) -> tuple[object, ...]:
        return (process.arrival_time, process.pid)

    def choose(self, ready: Sequence[Process], remaining: dict[str, int],
               running: Process | None, time: int) -> Process | None:
        return self.choose_with_priorities(ready, remaining, running, time, {})

    @abstractmethod
    def choose_with_priorities(self, ready: Sequence[Process], remaining: dict[str, int],
                               running: Process | None, time: int,
                               priorities: dict[str, int]) -> Process | None:
        raise NotImplementedError

    def uses_round_robin(self, process: Process) -> bool:
        return False

    def prepare(self, workload: Sequence[Process]) -> None:
        """Initialize policy metadata from the complete workload if needed."""

    def ready_key(self, process: Process, remaining: dict[str, int],
                  priorities: dict[str, int], order: dict[str, tuple[object, ...]]) -> tuple[object, ...]:
        return order[process.pid]

    def reason(self, selected: Process, candidates: Sequence[Process],
               running: Process | None, remaining: dict[str, int],
               priorities: dict[str, int]) -> str:
        if running is not None and selected.pid == running.pid:
            return f"{selected.pid} continues under {self.name.upper()}"
        descriptions = {
            "fcfs": "earliest arrival",
            "sjf": "shortest available burst",
            "srtf": "shortest remaining time",
            "priority": "highest priority (lower number ranks higher)",
            "preemptive_priority": "highest effective priority (lower number ranks higher)",
            "rr": "front of the ready queue",
            "mlq": "highest-priority non-empty queue",
        }
        alternatives = [p for p in candidates if p.pid != selected.pid]
        if running is not None and running.pid != selected.pid:
            alternatives.insert(0, running)
        if alternatives:
            other = alternatives[0]
            if self.name == "srtf":
                if remaining[selected.pid] == remaining[other.pid]:
                    return (f"{selected.pid} and {other.pid} both have {remaining[selected.pid]} ticks; "
                            f"PID order selects {selected.pid}")
                return (f"{selected.pid} selected over {other.pid}: remaining "
                        f"{remaining[selected.pid]} < {remaining[other.pid]}")
            if self.name == "sjf":
                if selected.burst_time == other.burst_time:
                    return (f"{selected.pid} and {other.pid} both need {selected.burst_time} ticks; "
                            "arrival time then PID breaks the tie")
                return (f"{selected.pid} selected over {other.pid}: burst "
                        f"{selected.burst_time} < {other.burst_time}")
            if self.name in {"priority", "preemptive_priority"}:
                selected_priority = priorities.get(selected.pid, selected.priority)
                other_priority = priorities.get(other.pid, other.priority)
                if selected_priority == other_priority:
                    return (f"{selected.pid} and {other.pid} both have priority {selected_priority}; "
                            f"PID order selects {selected.pid}")
                return (f"{selected.pid} priority {selected_priority} outranks {other.pid} "
                        f"priority {other_priority} (lower number is higher)")
            if self.name == "fcfs":
                if selected.arrival_time == other.arrival_time:
                    return f"arrival ties at {selected.arrival_time}; PID order selects {selected.pid}"
                return (f"{selected.pid} arrived at {selected.arrival_time} before "
                        f"{other.pid} at {other.arrival_time}")
            return f"{selected.pid} selected over {other.pid}: {descriptions.get(self.name, self.name)}"
        return f"{selected.pid} selected: {descriptions.get(self.name, self.name)}"
