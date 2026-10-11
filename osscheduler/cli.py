"""Command line tools for simulation, comparison, sweeps, and export."""

from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import analytics, export
from .algorithms import ALGORITHMS
from .engine import simulate
from .models import Process
from .workloads import PRESETS, get_preset

console = Console()


def _add_workload(parser: argparse.ArgumentParser, *, default: str = "mixed") -> None:
    parser.add_argument("--preset", choices=sorted(PRESETS), default=default)
    parser.add_argument("--process", action="append", metavar="PID,ARRIVAL,BURST[,PRIORITY]",
                        help="custom process; repeat to supply a workload (overrides preset)")
    parser.add_argument("--cores", type=int, default=1)
    parser.add_argument("--quantum", type=int, default=2)
    parser.add_argument("--switch-cost", type=int, default=0)
    parser.add_argument("--aging", action="store_true")
    parser.add_argument("--aging-interval", type=int, default=5)
    parser.add_argument("--aging-step", type=int, default=1)


def _workload(args) -> tuple[Process, ...]:
    if not args.process:
        return get_preset(args.preset)
    result = []
    for item in args.process:
        fields = item.split(",")
        if len(fields) not in (3, 4):
            raise ValueError(f"invalid process {item!r}; expected PID,ARRIVAL,BURST[,PRIORITY]")
        pid, arrival, burst, *priority = fields
        result.append(Process(pid, int(arrival), int(burst), int(priority[0]) if priority else 0))
    return tuple(result)


def _run(args, workload):
    return simulate(workload, args.algorithm, cores=args.cores, quantum=args.quantum,
                    aging=args.aging, aging_interval=args.aging_interval,
                    aging_step=args.aging_step, context_switch_cost=args.switch_cost)


def _print_result(result) -> None:
    console.print(Panel.fit(f"[bold]{result.algorithm.upper()}[/bold] · makespan {result.makespan} · {result.cores} core(s)",
                            border_style="cyan"))
    gantt_table = Table(title="CPU schedule", show_header=True, header_style="bold green")
    gantt_table.add_column("Core")
    gantt_table.add_column("Timeline")
    for core in range(result.cores):
        line = [b for b in result.gantt if b.core == core]
        gantt_table.add_row(str(core + 1), "  │  ".join(
            f"{b.start}–{b.end} {b.pid or b.state}" for b in line))
    console.print(gantt_table)
    metrics = Table(show_header=False, box=None, padding=(0, 2))
    metrics.add_column(style="dim")
    metrics.add_column(style="bold")
    metrics.add_row("Average waiting", f"{result.average_waiting_time:.2f}")
    metrics.add_row("Average turnaround", f"{result.average_turnaround_time:.2f}")
    metrics.add_row("Average response", f"{result.average_response_time:.2f}")
    metrics.add_row("Throughput", f"{result.throughput:.3f} processes/unit")
    metrics.add_row("CPU utilization", f"{result.cpu_utilization:.1%}")
    metrics.add_row("Context switches", f"{result.context_switches} ({result.switching_overhead} ticks overhead)")
    console.print(metrics)


def main() -> None:
    parser = argparse.ArgumentParser(description="CPU Scheduling Simulator")
    commands = parser.add_subparsers(dest="command", required=True)

    run_parser = commands.add_parser("run", help="run one scheduler")
    _add_workload(run_parser)
    run_parser.add_argument("--algorithm", choices=sorted(ALGORITHMS), default="fcfs")

    compare_parser = commands.add_parser("compare", help="compare all scheduling policies")
    _add_workload(compare_parser)

    sweep_parser = commands.add_parser("sweep", help="sweep RR quantum values")
    _add_workload(sweep_parser)
    sweep_parser.add_argument("--max-quantum", type=int, default=10)

    aging_parser = commands.add_parser("demo-aging", help="compare priority scheduling with and without aging")
    _add_workload(aging_parser, default="starvation")
    aging_parser.set_defaults(aging_interval=3, aging_step=2)

    export_parser = commands.add_parser("export", help="export one scheduling report")
    _add_workload(export_parser)
    export_parser.add_argument("--algorithm", choices=sorted(ALGORITHMS), default="fcfs")
    export_parser.add_argument("--format", choices=("csv", "json", "pdf"), default="json")
    export_parser.add_argument("--output", type=Path)

    args = parser.parse_args()
    try:
        workload = _workload(args)
        if args.command == "run":
            _print_result(_run(args, workload))
        elif args.command == "compare":
            table = Table(title="Algorithm comparison", header_style="bold green")
            for column in ("Policy", "Wait", "Turnaround", "Response", "Utilization"):
                table.add_column(column, justify="right" if column != "Policy" else "left")
            for name, result in analytics.compare_all(workload, cores=args.cores,
                    quantum=args.quantum, aging=args.aging,
                    aging_interval=args.aging_interval, aging_step=args.aging_step,
                    context_switch_cost=args.switch_cost).items():
                table.add_row(name.upper(), f"{result.average_waiting_time:.2f}",
                              f"{result.average_turnaround_time:.2f}",
                              f"{result.average_response_time:.2f}",
                              f"{result.cpu_utilization:.1%}")
            console.print(table)
        elif args.command == "sweep":
            result = analytics.quantum_sweep(workload, max_quantum=args.max_quantum,
                    cores=args.cores, context_switch_cost=args.switch_cost)
            for point in result["points"]:
                console.print(f"q={point['quantum']:>3}: wait={point['average_waiting_time']:.2f}, "
                              f"turnaround={point['average_turnaround_time']:.2f}")
            console.print(f"Optimum waiting-time quantum: [bold green]{result['optimum_quantum']}[/bold green]")
        elif args.command == "demo-aging":
            result = analytics.aging_demo(workload, aging_interval=args.aging_interval,
                                          aging_step=args.aging_step)
            for label, key in (("Without aging", "without_aging"), ("With aging", "with_aging")):
                schedule = result[key]
                _print_result(schedule)
                low = next((p for p in schedule.processes if p.pid == "P1"), schedule.processes[0])
                console.print(f"{label}: focus process {low.pid} first runs at {low.first_start} "
                              f"(wait {low.waiting_time})")
        elif args.command == "export":
            result = _run(args, workload)
            payload = {"csv": export.to_csv, "json": export.to_json,
                       "pdf": export.to_pdf}[args.format](result)
            output = args.output or Path(f"schedule.{args.format}")
            if isinstance(payload, bytes):
                output.write_bytes(payload)
            else:
                output.write_text(payload, encoding="utf-8")
            console.print(f"Wrote [bold green]{output}[/bold green]")
    except (ValueError, KeyError, RuntimeError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
