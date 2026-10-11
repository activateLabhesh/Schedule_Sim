"""CSV, JSON, and PDF report serialization."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict

from .models import ScheduleResult
from .metrics import analyze_result


def to_json(result: ScheduleResult, *, starvation_threshold: int = 20) -> str:
    payload = asdict(result)
    payload["analysis"] = analyze_result(result, starvation_threshold=starvation_threshold)
    return json.dumps(payload, indent=2)


def to_csv(result: ScheduleResult, *, starvation_threshold: int = 20) -> str:
    stream = io.StringIO(newline="")
    analysis = analyze_result(result, starvation_threshold=starvation_threshold)
    writer = csv.DictWriter(stream, fieldnames=["pid", "arrival_time", "burst_time",
        "first_start", "completion_time", "turnaround_time", "waiting_time", "response_time",
        "response_ratio", "average_waiting_time", "average_turnaround_time",
        "average_response_time", "throughput", "cpu_utilization", "jain", "gini",
        "starved_processes", "context_switches", "switching_overhead",
        "waiting_median", "waiting_min", "waiting_max", "waiting_stdev",
        "turnaround_median", "turnaround_min", "turnaround_max", "turnaround_stdev",
        "response_median", "response_min", "response_max", "response_stdev"])
    writer.writeheader()
    for process in result.processes:
        writer.writerow({**asdict(process),
            "average_waiting_time": result.average_waiting_time,
            "average_turnaround_time": result.average_turnaround_time,
            "average_response_time": result.average_response_time,
            "throughput": result.throughput,
            "cpu_utilization": result.cpu_utilization,
            "jain": analysis["jain"], "gini": analysis["gini"],
            "starved_processes": ";".join(analysis["starved_processes"]),
            "context_switches": result.context_switches,
            "switching_overhead": result.switching_overhead,
            "waiting_median": result.metric_summary["waiting_time"]["median"],
            "waiting_min": result.metric_summary["waiting_time"]["min"],
            "waiting_max": result.metric_summary["waiting_time"]["max"],
            "waiting_stdev": result.metric_summary["waiting_time"]["stdev"],
            "turnaround_median": result.metric_summary["turnaround_time"]["median"],
            "turnaround_min": result.metric_summary["turnaround_time"]["min"],
            "turnaround_max": result.metric_summary["turnaround_time"]["max"],
            "turnaround_stdev": result.metric_summary["turnaround_time"]["stdev"],
            "response_median": result.metric_summary["response_time"]["median"],
            "response_min": result.metric_summary["response_time"]["min"],
            "response_max": result.metric_summary["response_time"]["max"],
            "response_stdev": result.metric_summary["response_time"]["stdev"]})
    return stream.getvalue()


def to_pdf(result: ScheduleResult, *, starvation_threshold: int = 20) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import landscape, letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.graphics.shapes import Drawing, Rect, String
    except ImportError as exc:
        raise RuntimeError("PDF export requires reportlab") from exc
    stream = io.BytesIO()
    doc = SimpleDocTemplate(stream, pagesize=landscape(letter))
    styles = getSampleStyleSheet()
    story = [Paragraph(f"CPU Scheduling Report — {result.algorithm.upper()}", styles["Title"]),
             Paragraph(f"Makespan {result.makespan} · {result.cores} core(s) · "
                       f"{result.context_switches} context switches · "
                       f"{result.switching_overhead} switching ticks", styles["Normal"]), Spacer(1, 14)]
    data = [["PID", "Arrival", "Burst", "Start", "Complete", "Waiting", "Turnaround", "Response", "Ratio"]]
    data.extend([[p.pid, p.arrival_time, p.burst_time, p.first_start,
                  p.completion_time, p.waiting_time, p.turnaround_time, p.response_time,
                  f"{p.response_ratio:.2f}"]
                 for p in result.processes])
    table = Table(data, repeatRows=1,
                  colWidths=[42, 48, 42, 42, 48, 46, 54, 48, 42])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#163a46")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .4, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef4f3")]),
        ("PADDING", (0, 0), (-1, -1), 5)]))
    summary = analyze_result(result, starvation_threshold=starvation_threshold)
    summary_data = [["Measure", "Mean", "Median", "Min", "Max", "Std dev"]]
    for label, key in (("Waiting", "waiting_time"), ("Turnaround", "turnaround_time"),
                       ("Response", "response_time")):
        stat = result.metric_summary[key]
        summary_data.append([label, *(f"{stat[column]:.2f}" for column in
                                     ("mean", "median", "min", "max", "stdev"))])
    summary_table = Table(summary_data, repeatRows=1)
    summary_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dce9e3")),
        ("GRID", (0, 0), (-1, -1), .4, colors.grey), ("PADDING", (0, 0), (-1, -1), 5)]))
    story.extend([table, Spacer(1, 10), summary_table, Spacer(1, 12),
                  Paragraph("CPU timeline", styles["Heading2"])])
    drawing = Drawing(648, max(36, result.cores * 26 + 8))
    left, plot_width = 66, 560
    scale = plot_width / max(result.makespan, 1)
    pid_colors = [colors.HexColor(value) for value in
                  ("#a5cb72", "#65aaa0", "#e5aa70", "#89a8ce", "#d58978", "#b4a0ca")]
    for core in range(result.cores):
        y = result.cores * 26 - (core + 1) * 26 + 8
        drawing.add(String(0, y + 4, f"CPU {core + 1}", fontSize=7))
        for block in (item for item in result.gantt if item.core == core):
            color = (colors.HexColor("#e6b77a") if block.state == "switching" else
                     colors.HexColor("#edf1ef") if block.state == "idle" else
                     pid_colors[sum(ord(char) for char in (block.pid or "P1")) % len(pid_colors)])
            x = left + block.start * scale
            width = max(1, (block.end - block.start) * scale)
            drawing.add(Rect(x, y, width, 18, fillColor=color, strokeColor=colors.white, strokeWidth=.5))
            if block.pid:
                drawing.add(String(x + 2, y + 6, block.pid, fontSize=6))
    bar_chart = Drawing(648, 84)
    stat_values = [("Waiting", result.average_waiting_time),
                   ("Turnaround", result.average_turnaround_time),
                   ("Response", result.average_response_time)]
    max_value = max((value for _, value in stat_values), default=1) or 1
    for index, (label, value) in enumerate(stat_values):
        y = 60 - index * 24
        bar_chart.add(String(0, y + 2, label, fontSize=8))
        bar_chart.add(Rect(72, y, 475 * value / max_value, 14,
                           fillColor=pid_colors[index], strokeColor=None))
        bar_chart.add(String(556, y + 2, f"{value:.2f}", fontSize=8))
    story.extend([drawing, Spacer(1, 8), Paragraph("Metric comparison", styles["Heading2"]),
        bar_chart, Spacer(1, 12), Paragraph(
        f"Average waiting {result.average_waiting_time:.2f} · "
        f"Average turnaround {result.average_turnaround_time:.2f} · "
        f"Average response {result.average_response_time:.2f} · "
        f"Throughput {result.throughput:.3f}/unit · "
        f"CPU utilization {result.cpu_utilization:.1%} · Jain fairness {summary['jain']:.3f} · "
        f"Gini {summary['gini']:.3f}", styles["Normal"]),
        Paragraph(f"Starved (wait &gt; {summary['starvation_threshold']}): "
                  f"{', '.join(summary['starved_processes']) or 'none'} · "
                  f"Little’s Law: L={summary['little_law']['L']:.3f}, "
                  f"λ={summary['little_law']['lambda']:.3f}, W={summary['little_law']['W']:.3f}, "
                  f"|L−λW|={summary['little_law']['absolute_error']:.3f}", styles["Normal"])])
    doc.build(story)
    return stream.getvalue()
