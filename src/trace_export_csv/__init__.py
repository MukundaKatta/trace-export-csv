"""trace-export-csv: export JSONL agent traces to CSV for spreadsheet analysis.

Public API:
    export_csv(events, dest=None, ...) -> ExportResult
    export_file(source, dest, ...) -> ExportResult
    ExportResult    — row_count, columns, csv_text
    TraceExportError — base exception
"""

from .core import ExportResult, TraceExportError, export_csv, export_file

__all__ = ["export_csv", "export_file", "ExportResult", "TraceExportError"]
__version__ = "0.1.0"
