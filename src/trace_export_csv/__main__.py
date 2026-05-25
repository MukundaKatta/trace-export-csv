"""CLI: python -m trace_export_csv <source.jsonl> <dest.csv>"""
from __future__ import annotations
import sys

def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(prog="trace-export-csv", description="Export a JSONL trace to CSV.")
    parser.add_argument("source", help="Input JSONL trace file")
    parser.add_argument("dest", help="Output CSV file")
    parser.add_argument("--all", dest="include_all", action="store_true", help="Include all fields")
    args = parser.parse_args(argv)
    from . import TraceExportError, export_file
    try:
        result = export_file(args.source, args.dest, include_all=args.include_all)
        print(f"Exported {result.row_count} rows to {args.dest}")
    except TraceExportError as e:
        print(f"trace-export-csv: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
