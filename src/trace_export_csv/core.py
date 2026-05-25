"""Export a JSONL agent trace to CSV for spreadsheet analysis."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class TraceExportError(Exception):
    """Raised on unrecoverable export failures."""


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def _load_jsonl(source: str | Path) -> list[dict[str, Any]]:
    p = Path(source)
    if not p.exists():
        raise TraceExportError(f"file not found: {p}")
    events: list[dict[str, Any]] = []
    for lineno, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise TraceExportError(f"{p}:{lineno}: invalid JSON: {e}") from e
    return events


# ---------------------------------------------------------------------------
# Default fields
# ---------------------------------------------------------------------------

# Ordered list of (csv_column_name, list_of_jsonl_keys_to_try)
_DEFAULT_FIELDS: list[tuple[str, list[str]]] = [
    ("timestamp", ["timestamp", "ts", "time", "created_at", "at"]),
    ("kind", ["kind", "type", "event_type"]),
    ("name", ["name", "step", "tool", "tool_name"]),
    ("lane", ["lane"]),
    ("model", ["model", "model_id", "model_name"]),
    ("tokens_in", ["tokens_in", "input_tokens", "prompt_tokens"]),
    ("tokens_out", ["tokens_out", "output_tokens", "completion_tokens"]),
    ("cost_usd", ["cost_usd", "cost", "price_usd", "usd"]),
    ("duration_ms", ["duration_ms", "duration"]),
    ("error", ["error", "err", "exception"]),
]


def _pick(event: dict[str, Any], keys: list[str]) -> str:
    """Return the first non-None value matching any of the keys, as a string."""
    for key in keys:
        val = event.get(key)
        if val is not None:
            return str(val)
    return ""


# ---------------------------------------------------------------------------
# Export result
# ---------------------------------------------------------------------------

@dataclass
class ExportResult:
    """Result of exporting a trace to CSV.

    Attributes:
        row_count: number of data rows written.
        columns: list of column names in the CSV.
        csv_text: the CSV content as a string (if no dest was given).
    """

    row_count: int
    columns: list[str]
    csv_text: str = ""


# ---------------------------------------------------------------------------
# Main export function
# ---------------------------------------------------------------------------

def export_csv(
    events: list[dict[str, Any]],
    dest: str | Path | None = None,
    *,
    fields: list[tuple[str, list[str]]] | None = None,
    extra_fields: list[str] | None = None,
    include_all: bool = False,
) -> ExportResult:
    """Export a list of JSONL events to CSV.

    Args:
        events: list of event dicts.
        dest: output CSV path. If None, returns the CSV as a string in
            ExportResult.csv_text.
        fields: list of (column_name, [keys_to_try]) pairs. Overrides
            the default field mapping if provided.
        extra_fields: additional raw field names to include (appended after
            the default or custom fields).
        include_all: if True, include every key found across all events
            (union of all keys, appended after mapped fields).

    Returns:
        ExportResult with row_count, columns, and csv_text (if no dest).
    """
    mapped_fields = fields if fields is not None else _DEFAULT_FIELDS

    # Collect extra columns
    extra_cols: list[str] = list(extra_fields or [])
    if include_all:
        all_keys: set[str] = set()
        for event in events:
            all_keys.update(event.keys())
        mapped_names = {col for col, _ in mapped_fields}
        for key in sorted(all_keys):
            if key not in mapped_names and key not in extra_cols:
                extra_cols.append(key)

    columns = [col for col, _ in mapped_fields] + extra_cols

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(columns)

    for event in events:
        row: list[str] = []
        for col, keys in mapped_fields:
            row.append(_pick(event, keys))
        for key in extra_cols:
            val = event.get(key)
            row.append("" if val is None else str(val))
        writer.writerow(row)

    csv_text = output.getvalue()

    if dest is not None:
        p = Path(dest)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(csv_text, encoding="utf-8")
        return ExportResult(row_count=len(events), columns=columns)

    return ExportResult(row_count=len(events), columns=columns, csv_text=csv_text)


def export_file(
    source: str | Path,
    dest: str | Path,
    **kwargs: Any,
) -> ExportResult:
    """Load a JSONL file and export it to a CSV file."""
    events = _load_jsonl(source)
    return export_csv(events, dest, **kwargs)
