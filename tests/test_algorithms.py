from osscheduler.engine import simulate
from osscheduler.models import Process
import pytest


@pytest.mark.parametrize("kwargs", [
    {"pid": "", "arrival_time": 0, "burst_time": 1},
    {"pid": "P1", "arrival_time": -1, "burst_time": 1},
    {"pid": "P1", "arrival_time": 0, "burst_time": 0},
    {"pid": "P1", "arrival_time": 0.5, "burst_time": 1},
    {"pid": "P1", "arrival_time": 0, "burst_time": 1, "priority": -1},
])
def test_process_rejects_invalid_tick_data(kwargs):
    with pytest.raises(ValueError):
        Process(**kwargs)


def test_fcfs_hand_computed_waiting_times():
    result = simulate([Process("P1", 0, 5), Process("P2", 2, 3), Process("P3", 4, 1)], "fcfs")
    assert [p.waiting_time for p in result.processes] == [0, 3, 4]
    assert result.average_waiting_time == 7 / 3
    assert result.trace[0].events[0].time == 0
    assert result.trace[0].events[0].core == 0
    assert "selected" in result.trace[0].events[0].message


def test_sjf_orders_shortest_available_job_first():
    result = simulate([Process("P1", 0, 6), Process("P2", 0, 8),
                       Process("P3", 0, 7), Process("P4", 0, 3)], "sjf")
    assert [block.pid for block in result.gantt] == ["P4", "P1", "P3", "P2"]
    assert result.average_waiting_time == 7


def test_srtf_preempts_for_shorter_remaining_job():
    result = simulate([Process("P1", 0, 8), Process("P2", 1, 4), Process("P3", 2, 2)], "srtf")
    assert [(b.pid, b.start, b.end) for b in result.gantt] == [
        ("P1", 0, 1), ("P2", 1, 2), ("P3", 2, 4), ("P2", 4, 7), ("P1", 7, 14)]
    assert [p.waiting_time for p in result.processes] == [6, 2, 0]


def test_all_policies_return_valid_schedules():
    workload = [Process("P1", 0, 4, 2), Process("P2", 1, 2, 0), Process("P3", 2, 3, 1)]
    for name in ("fcfs", "sjf", "srtf", "priority", "preemptive_priority", "rr", "mlq"):
        result = simulate(workload, name, quantum=2)
        assert sum(p.burst_time for p in workload) == sum(
            b.end - b.start for b in result.gantt if b.state == "running")
        assert all(p.turnaround_time == p.waiting_time + p.burst_time for p in result.processes)
        assert 0 <= result.cpu_utilization <= 1


def test_priority_lower_number_is_higher_priority():
    result = simulate([Process("P1", 0, 3, 5), Process("P2", 0, 2, 1)], "priority")
    assert result.gantt[0].pid == "P2"


def test_priority_example_schedules_by_textbook_priority_order():
    workload = [Process("P1", 0, 10, 3), Process("P2", 0, 1, 1),
                Process("P3", 0, 2, 4), Process("P4", 0, 1, 5),
                Process("P5", 0, 5, 2)]
    result = simulate(workload, "priority")
    assert [block.pid for block in result.gantt] == ["P2", "P5", "P1", "P3", "P4"]
    assert result.average_waiting_time == 8.2


def test_preemptive_priority_example_interrupts_lower_priority_process():
    result = simulate([Process("P1", 0, 7, 2), Process("P2", 2, 4, 1)], "preemptive_priority")
    assert [(b.pid, b.start, b.end) for b in result.gantt] == [
        ("P1", 0, 2), ("P2", 2, 6), ("P1", 6, 11)]


def test_quantum_one_rotates_ready_processes_and_large_quantum_is_fcfs():
    workload = [Process("P1", 0, 3), Process("P2", 0, 2), Process("P3", 0, 1)]
    rr = simulate(workload, "rr", quantum=1)
    assert [x.running[0] for x in rr.trace[:4]] == ["P1", "P2", "P3", "P1"]
    rr_large = simulate(workload, "rr", quantum=10)
    fcfs = simulate(workload, "fcfs")
    assert [(b.pid, b.start, b.end) for b in rr_large.gantt] == [
        (b.pid, b.start, b.end) for b in fcfs.gantt]


def test_round_robin_textbook_workload_rotates_until_completion():
    result = simulate([Process("P1", 0, 24), Process("P2", 0, 3),
                       Process("P3", 0, 3)], "rr", quantum=4)
    assert [(b.pid, b.start, b.end) for b in result.gantt] == [
        ("P1", 0, 4), ("P2", 4, 7), ("P3", 7, 10),
        ("P1", 10, 30)]
    assert [event for frame in result.trace for event in frame.decisions
            if "quantum expired" in event]
