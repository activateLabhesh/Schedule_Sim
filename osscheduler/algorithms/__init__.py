"""Built-in scheduling algorithms."""

from .fcfs import FCFS
from .sjf import SJF
from .srtf import SRTF
from .priority import Priority
from .preemptive_priority import PreemptivePriority
from .rr import RoundRobin
from .mlq import MultiLevelQueue

ALGORITHMS = {"fcfs": FCFS, "sjf": SJF, "srtf": SRTF,
              "priority": Priority, "preemptive_priority": PreemptivePriority,
              "rr": RoundRobin, "mlq": MultiLevelQueue}
ALGORITHM_METADATA = {
    name: {"name": name, "preemptive": policy.preemptive,
           "needs_quantum": name in {"rr", "mlq"},
           "supports_aging": name in {"priority", "preemptive_priority"}}
    for name, policy in ALGORITHMS.items()
}

__all__ = ["ALGORITHMS", "ALGORITHM_METADATA", "FCFS", "SJF", "SRTF", "Priority",
           "PreemptivePriority", "RoundRobin", "MultiLevelQueue"]
