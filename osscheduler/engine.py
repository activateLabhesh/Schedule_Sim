"""Deterministic integer-tick engine shared by every scheduling policy."""

from __future__ import annotations

from collections.abc import Iterable

from .algorithms import ALGORITHMS
from .algorithms.base import Scheduler
from .algorithms.rr import RoundRobin
from .algorithms.mlq import MultiLevelQueue
from .metrics import process_metrics, summarize
from .models import DecisionEvent, GanttBlock, Process, ScheduleResult, TickSnapshot


def _coalesce(blocks: list[GanttBlock], block: GanttBlock) -> None:
    for index in range(len(blocks) - 1, -1, -1):
        previous = blocks[index]
        if previous.core == block.core:
            if previous.pid == block.pid and previous.end == block.start and previous.state == block.state:
                blocks[index] = GanttBlock(block.pid, previous.start, block.end, block.core, block.state)
            else:
                blocks.append(block)
            return
    blocks.append(block)


def _record_decision(decisions: list[str], events: list[DecisionEvent],
                     time: int, core: int, message: str) -> None:
    decisions.append(f"Core {core}: {message}")
    events.append(DecisionEvent(time, core, message))


def simulate(processes: Iterable[Process], algorithm: str | Scheduler = "fcfs", *,
             cores: int = 1, quantum: int = 2, aging: bool = False,
             aging_interval: int = 5, aging_step: int = 1,
             context_switch_cost: int = 0) -> ScheduleResult:
    """Simulate a workload and return Gantt, trace, and performance metrics.

    Lower priority numbers mean higher priority. Multi-core execution uses a
    global ready set and deterministic PID tie-breaking.
    """
    workload = tuple(processes)
    if not workload:
        raise ValueError("at least one process is required")
    if cores < 1 or quantum < 1 or context_switch_cost < 0:
        raise ValueError("cores and quantum must be positive; switch cost cannot be negative")
    if aging and aging_interval < 1:
        raise ValueError("aging_interval must be at least 1")
    if aging_step < 1:
        raise ValueError("aging_step must be at least 1")
    pids = [p.pid for p in workload]
    if len(pids) != len(set(pids)):
        raise ValueError("process PIDs must be unique")
    if isinstance(algorithm, str):
        key = algorithm.lower()
        if key not in ALGORITHMS:
            raise ValueError(f"unknown algorithm: {algorithm}")
        policy = RoundRobin(quantum) if key == "rr" else (
            MultiLevelQueue(quantum=quantum) if key == "mlq" else ALGORITHMS[key]())
    else:
        policy = algorithm
    policy.prepare(workload)

    remaining = {p.pid: p.burst_time for p in workload}
    first_start: dict[str, int] = {}
    completion: dict[str, int] = {}
    waited = {p.pid: 0 for p in workload}
    ready_order = {p.pid: (p.arrival_time, p.pid) for p in workload}
    running: list[Process | None] = [None] * cores
    last_process: list[str | None] = [None] * cores
    rr_used = [0] * cores
    switch_remaining = [0] * cores
    switch_target: list[Process | None] = [None] * cores
    gantt: list[GanttBlock] = []
    trace: list[TickSnapshot] = []
    switches = overhead = time = 0

    while len(completion) < len(workload):
        available = [p for p in workload if p.arrival_time <= time and remaining[p.pid] > 0]
        effective = {p.pid: max(0, p.priority - (waited[p.pid] // aging_interval) * aging_step)
                     if aging else p.priority for p in workload}
        selected: list[Process | None] = [None] * cores
        states = ["idle"] * cores
        decisions: list[str] = []
        events: list[DecisionEvent] = []
        claimed: set[str] = {target.pid for core, target in enumerate(switch_target)
                             if switch_remaining[core] > 0 and target is not None}
        for core in range(cores):
            current = running[core] if running[core] and remaining[running[core].pid] > 0 else None
            if switch_remaining[core] > 0:
                switch_remaining[core] -= 1
                states[core] = "switching"
                selected[core] = switch_target[core]
                if switch_remaining[core] == 0:
                    running[core] = switch_target[core]
                if selected[core]:
                    claimed.add(selected[core].pid)
                    _record_decision(decisions, events, time, core,
                                     f"completing context switch to {selected[core].pid}")
                continue

            if current is not None and current.pid in claimed:
                current = None
                running[core] = None
                rr_used[core] = 0

            active_process = current or switch_target[core]
            is_rr = policy.uses_round_robin(active_process) if active_process else False
            rr_quantum = policy.quantum if is_rr else quantum
            if is_rr and current is not None and rr_used[core] >= rr_quantum:
                ready_order[current.pid] = (time + len(workload), current.pid)
                _record_decision(decisions, events, time, core, f"{current.pid} quantum expired")
                current = None
                running[core] = None
                rr_used[core] = 0

            candidates = [p for p in available if p.pid not in claimed and p is not current]
            candidates.sort(key=lambda p: policy.ready_key(p, remaining, effective, ready_order))
            choice = policy.choose_with_priorities(candidates, remaining, current, time, effective)
            if choice is None:
                _record_decision(decisions, events, time, core,
                                 "idle; no arrived unfinished process is ready")
                selected[core] = None
                continue
            _record_decision(decisions, events, time, core,
                             policy.reason(choice, candidates, current, remaining, effective))

            previous_pid = current.pid if current is not None else last_process[core]
            if current is None or choice.pid != current.pid:
                rr_used[core] = 0
            if context_switch_cost and previous_pid is not None and choice.pid != previous_pid:
                switches += 1
                overhead += context_switch_cost
                switch_remaining[core] = context_switch_cost - 1
                switch_target[core] = choice
                selected[core] = choice
                states[core] = "switching"
                _record_decision(decisions, events, time, core,
                                 f"context switch costs {context_switch_cost} tick(s)")
                claimed.add(choice.pid)
                if switch_remaining[core] == 0:
                    running[core] = choice
                continue
            selected[core] = choice
            running[core] = choice
            states[core] = "running"
            last_process[core] = choice.pid
            claimed.add(choice.pid)

        ready_list = sorted((p for p in available if p.pid not in claimed),
                            key=lambda p: policy.ready_key(p, remaining, effective, ready_order))
        trace.append(TickSnapshot(time, tuple(p.pid if p else None for p in selected),
                                  tuple(p.pid for p in ready_list),
                                  tuple(sorted(effective.items())), tuple(decisions), tuple(states),
                                  tuple(sorted(waited.items())), tuple(events)))
        for p in available:
            if p.pid not in claimed:
                waited[p.pid] += 1
        for core, process in enumerate(selected):
            if states[core] == "switching":
                _coalesce(gantt, GanttBlock(None, time, time + 1, core, "switching"))
                continue
            if process is None:
                _coalesce(gantt, GanttBlock(None, time, time + 1, core, "idle"))
                last_process[core] = None
                continue
            first_start.setdefault(process.pid, time)
            _coalesce(gantt, GanttBlock(process.pid, time, time + 1, core, "running"))
            remaining[process.pid] -= 1
            last_process[core] = process.pid
            if policy.uses_round_robin(process):
                rr_used[core] += 1
            if remaining[process.pid] == 0:
                completion[process.pid] = time + 1
                running[core] = None
                rr_used[core] = 0
        time += 1

    rows = process_metrics(workload, first_start, completion)
    makespan = max(completion.values())
    return ScheduleResult(
        algorithm=policy.name, processes=rows, gantt=tuple(gantt), trace=tuple(trace),
        makespan=makespan,
        average_waiting_time=sum(x.waiting_time for x in rows) / len(rows),
        average_turnaround_time=sum(x.turnaround_time for x in rows) / len(rows),
        average_response_time=sum(x.response_time for x in rows) / len(rows),
        throughput=len(workload) / makespan,
        cpu_utilization=sum(p.burst_time for p in workload) / (makespan * cores),
        context_switches=switches, switching_overhead=overhead, cores=cores,
        metric_summary=summarize(rows),
    )
