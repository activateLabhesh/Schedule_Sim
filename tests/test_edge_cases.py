import random

from osscheduler.engine import simulate
from osscheduler.models import Process


def test_idle_gap_and_pid_ties_are_explicit_and_deterministic():
    result = simulate([Process("P2", 5, 1), Process("P1", 5, 1)], "fcfs")
    assert result.gantt[0].state == "idle"
    assert result.gantt[0].start == 0 and result.gantt[0].end == 5
    assert result.gantt[1].pid == "P1"
    assert "PID order" in result.trace[5].decisions[0]


def test_seeded_workloads_preserve_invariants_for_every_policy():
    rng = random.Random(13)
    for case in range(20):
        workload = tuple(Process(f"P{i}", rng.randrange(5), rng.randrange(1, 7), rng.randrange(4))
                         for i in range(1, 6))
        for algorithm in ("fcfs", "sjf", "srtf", "priority", "preemptive_priority", "rr", "mlq"):
            result = simulate(workload, algorithm, cores=2, quantum=1 + case % 3)
            assert all(p.turnaround_time == p.waiting_time + p.burst_time for p in result.processes)
            assert 0 < result.cpu_utilization <= 1
            for frame in result.trace:
                busy = [pid for pid, state in zip(frame.running, frame.core_states)
                        if pid is not None and state == "running"]
                assert len(busy) == len(set(busy))
            for process in workload:
                total = sum(b.end - b.start for b in result.gantt
                            if b.pid == process.pid and b.state == "running")
                assert total == process.burst_time
