#!/usr/bin/env python3
"""
Format o11y_search_alerts_or_incidents MCP JSON as a markdown table.

  python parse_alerts_response.py [options] [path/to/response.json]
  python parse_alerts_response.py [options] < response.json

Options:
  --top N        After sort, emit only the first N rows (e.g. "last N alerts").
  --with-ids     Add incidentId, eventId, detectorId columns.
  --truncate M   Max length for Description (Context) column.
  --no-sort      Keep JSON array order (default: newest state update first).
"""

import argparse
import json
import sys
from datetime import datetime

DESCRIPTION_KEYS = ["host.name", "k8s.pod.name", "k8s.container.name", "state"]


def _effective_state_update_ms(a):
    m = a.get("anomalyStateUpdateTimestampMs")
    if isinstance(m, (int, float)):
        return int(m)
    s = a.get("anomaly_state_update_iso_8601_date_time")
    if not s:
        return 0
    try:
        t = s.replace("Z", "+00:00") if isinstance(s, str) and s.endswith("Z") else s
        return int(datetime.fromisoformat(t).timestamp() * 1000)
    except (ValueError, TypeError, OSError):
        return 0


def sort_alerts_newest_first(alerts):
    return sorted(alerts, key=_effective_state_update_ms, reverse=True)


def build_description(a, truncate=None):
    parts = []
    if a.get("eventCategory"):
        parts.append(a["eventCategory"])
    if a.get("originatingMetric"):
        parts.append("metric: " + a["originatingMetric"])
    cp = a.get("customProperties") or {}
    for k in DESCRIPTION_KEYS:
        if cp.get(k):
            parts.append(f"{k}={cp[k]}")
    out = "; ".join(parts) if parts else (a.get("link") or {}).get("text") or "-"
    if truncate and len(out) > truncate:
        out = out[: truncate - 3].rstrip() + "..."
    return out


def parse_alerts_to_rows(data, truncate=None, sort_newest_first=True, top_n=None, with_ids=False):
    alerts = list(data.get("alerts", []))
    total_before_top = len(alerts)
    if sort_newest_first:
        alerts = sort_alerts_newest_first(alerts)
    if top_n is not None and top_n > 0:
        alerts = alerts[:top_n]

    rows = []
    for a in alerts:
        ts = a.get("anomaly_state_update_iso_8601_date_time", "")
        name = a.get("detectLabel") or a.get("detector", "")
        status = "Active" if a.get("active") else "Inactive"
        if a.get("anomalyState"):
            status = f"{status} ({a['anomalyState']})"
        sev = a.get("severity", "")
        ctx = build_description(a, truncate=truncate)
        row = [ts, name, status, sev, ctx]
        if with_ids:
            row.extend(
                [
                    a.get("incidentId", ""),
                    a.get("eventId", ""),
                    a.get("detectorId", ""),
                ]
            )
        rows.append(tuple(row))
    return rows, total_before_top


def main():
    parser = argparse.ArgumentParser(description="Format o11y_search_alerts_or_incidents JSON as markdown")
    parser.add_argument("--top", type=int, default=None, metavar="N", help="Emit only N rows after sort")
    parser.add_argument("--truncate", type=int, default=None, metavar="M", help="Truncate Description column")
    parser.add_argument("--with-ids", action="store_true", help="Add incidentId, eventId, detectorId columns")
    parser.add_argument("--no-sort", action="store_true", help="Keep JSON order")
    parser.add_argument("file", nargs="?", default=None, help="JSON file (default: stdin)")
    args = parser.parse_args()

    if args.file:
        with open(args.file) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    rows, total_in_response = parse_alerts_to_rows(
        data,
        truncate=args.truncate,
        sort_newest_first=not args.no_sort,
        top_n=args.top,
        with_ids=args.with_ids,
    )

    if args.with_ids:
        header = "| timestamp | detector name | status | Severity | Description (Context) | incidentId | eventId | detectorId |"
        sep = "|-----------|---------------|--------|----------|------------------------|------------|---------|------------|"
    else:
        header = "| timestamp | detector name | status | Severity | Description (Context) |"
        sep = "|-----------|---------------|--------|----------|------------------------|"

    print(header)
    print(sep)
    for r in rows:
        cells = [str(x).replace("|", "\\|") for x in r]
        print("| " + " | ".join(cells) + " |")

    print(f"\nRows shown: {len(rows)} | Alerts in response: {total_in_response}")
    if args.top and total_in_response > args.top:
        print(f"(Sliced to --top {args.top} after sort.)")


if __name__ == "__main__":
    main()
