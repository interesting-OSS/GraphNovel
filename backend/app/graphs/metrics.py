"""Node execution metrics collector.

Tracks per-node timing, success/failure counts, and per-project statistics
for graph observability. In production, this could be backed by Redis or
a time-series database.
"""
import time
from collections import defaultdict
from datetime import datetime

# In-memory metrics store: project_id → list of node execution records
# Each record: {node, phase, start_time, duration_ms, success, error}
_metrics_store: dict[str, list[dict]] = defaultdict(list)
_MAX_RECORDS_PER_PROJECT = 200


def record_node_execution(
    project_id: str,
    node_name: str,
    phase: str,
    start_time: float,
    success: bool,
    error: str = "",
):
    """Record a single node execution."""
    duration_ms = round((time.time() - start_time) * 1000, 1)
    entry = {
        "node": node_name,
        "phase": phase,
        "start_time": datetime.fromtimestamp(start_time).isoformat(),
        "duration_ms": duration_ms,
        "success": success,
        "error": error,
    }

    records = _metrics_store[project_id]
    records.append(entry)

    # Trim old records
    if len(records) > _MAX_RECORDS_PER_PROJECT:
        _metrics_store[project_id] = records[-_MAX_RECORDS_PER_PROJECT:]


def get_project_metrics(project_id: str) -> dict:
    """Get aggregated metrics for a project."""
    records = _metrics_store.get(project_id, [])

    if not records:
        return {"project_id": project_id, "metrics": [], "summary": {}}

    # Per-node aggregation
    node_stats: dict[str, dict] = {}
    for r in records:
        node = r["node"]
        if node not in node_stats:
            node_stats[node] = {
                "node": node,
                "count": 0,
                "total_duration_ms": 0,
                "min_duration_ms": float("inf"),
                "max_duration_ms": 0,
                "avg_duration_ms": 0,
                "success_count": 0,
                "failure_count": 0,
                "last_phase": "",
                "last_execution": "",
            }
        ns = node_stats[node]
        ns["count"] += 1
        ns["total_duration_ms"] += r["duration_ms"]
        ns["min_duration_ms"] = min(ns["min_duration_ms"], r["duration_ms"])
        ns["max_duration_ms"] = max(ns["max_duration_ms"], r["duration_ms"])
        if r["success"]:
            ns["success_count"] += 1
        else:
            ns["failure_count"] += 1
        ns["last_phase"] = r["phase"]
        ns["last_execution"] = r["start_time"]

    for ns in node_stats.values():
        ns["avg_duration_ms"] = round(ns["total_duration_ms"] / ns["count"], 1) if ns["count"] else 0
        ns["total_duration_ms"] = round(ns["total_duration_ms"], 1)
        # Replace inf with 0 for empty nodes
        if ns["min_duration_ms"] == float("inf"):
            ns["min_duration_ms"] = 0

    metrics_list = sorted(node_stats.values(), key=lambda x: x["count"], reverse=True)

    # Overall summary
    total_calls = len(records)
    total_time = sum(r["duration_ms"] for r in records)
    failure_rate = round(
        sum(1 for r in records if not r["success"]) / total_calls * 100, 1
    ) if total_calls else 0

    # Phase timeline (ordered by time)
    phases = []
    for r in records:
        if r["phase"] not in [p["phase"] for p in phases]:
            phases.append({"phase": r["phase"], "node": r["node"],
                          "duration_ms": r["duration_ms"], "at": r["start_time"]})

    return {
        "project_id": project_id,
        "metrics": metrics_list,
        "summary": {
            "total_node_calls": total_calls,
            "total_time_ms": round(total_time, 1),
            "failure_rate_pct": failure_rate,
            "unique_nodes": len(node_stats),
        },
        "timeline": phases,
    }

