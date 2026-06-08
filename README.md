# trace-export-csv

[![CI](https://github.com/MukundaKatta/trace-export-csv/actions/workflows/ci.yml/badge.svg)](https://github.com/MukundaKatta/trace-export-csv/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Export JSONL agent traces to CSV for spreadsheet and BI analysis.

LLM-agent runs are typically logged as [JSON Lines](https://jsonlines.org/) —
one JSON object per line, one event per step. `trace-export-csv` flattens that
stream into a tidy CSV with stable columns (timestamp, kind, tokens, cost, …)
so you can pivot, chart, and total it up in Excel, Google Sheets, or any BI
tool — without writing a parser.

Zero dependencies. Python 3.10+. MIT.

## Install

```bash
pip install trace-export-csv
```

## Quick start

Given a trace file `run.jsonl`:

```jsonl
{"ts": 1712000000, "type": "llm_call", "model": "claude-sonnet", "prompt_tokens": 1200, "completion_tokens": 340, "cost": 0.012}
{"ts": 1712000003, "type": "tool_call", "tool": "web_search", "duration_ms": 870}
{"ts": 1712000005, "type": "llm_call", "model": "claude-sonnet", "prompt_tokens": 1800, "completion_tokens": 90, "cost": 0.009, "error": "rate_limited"}
```

Export it to CSV:

```python
from trace_export_csv import export_file

result = export_file("run.jsonl", "run.csv")
print(f"Exported {result.row_count} rows, columns: {result.columns}")
```

Produces `run.csv`:

```csv
timestamp,kind,name,lane,model,tokens_in,tokens_out,cost_usd,duration_ms,error
1712000000,llm_call,,,claude-sonnet,1200,340,0.012,,
1712000003,tool_call,web_search,,,,,,870,
1712000005,llm_call,,,claude-sonnet,1800,90,0.009,,rate_limited
```

Note how `ts`, `type`, `tool`, `prompt_tokens`, `completion_tokens`, and `cost`
were automatically mapped onto the canonical `timestamp`, `kind`, `name`,
`tokens_in`, `tokens_out`, and `cost_usd` columns (see
[Field mapping](#field-mapping)).

Open `run.csv` in Excel, Google Sheets, or any BI tool. Default columns:

`timestamp`, `kind`, `name`, `lane`, `model`, `tokens_in`, `tokens_out`, `cost_usd`, `duration_ms`, `error`

## From a list of dicts

```python
from trace_export_csv import export_csv

result = export_csv(events, "out.csv")
```

## Get CSV as a string (no file)

```python
result = export_csv(events)
print(result.csv_text)
```

## Include all fields

```python
result = export_file("run.jsonl", "out.csv", include_all=True)
```

Adds every key found across all events (union) as additional columns.

## Extra specific fields

```python
result = export_csv(events, "out.csv", extra_fields=["run_id", "sub_task"])
```

## CLI

```bash
trace-export-csv run.jsonl out.csv
trace-export-csv run.jsonl out.csv --all
```

## Field mapping

The default mapping recognizes common naming conventions:

| CSV column | JSONL keys tried |
|-----------|-----------------|
| `timestamp` | timestamp, ts, time, created_at, at |
| `kind` | kind, type, event_type |
| `name` | name, step, tool, tool_name |
| `tokens_in` | tokens_in, input_tokens, prompt_tokens |
| `tokens_out` | tokens_out, output_tokens, completion_tokens |
| `cost_usd` | cost_usd, cost, price_usd, usd |
| `error` | error, err, exception |

For each column, the keys are tried left to right and the **first non-`None`**
value wins (note: `0` and `""` count as present, not missing). Any key that is
not found yields an empty cell. Provide your own mapping with the `fields`
argument to override this entirely.

## API reference

### `export_csv(events, dest=None, *, fields=None, extra_fields=None, include_all=False) -> ExportResult`

Export a list of event dicts to CSV.

| Argument | Type | Description |
|----------|------|-------------|
| `events` | `list[dict]` | The events to export. |
| `dest` | `str \| Path \| None` | Output path. If `None`, the CSV is returned in `ExportResult.csv_text` instead of being written. Parent directories are created as needed. |
| `fields` | `list[tuple[str, list[str]]] \| None` | Custom `(column_name, [keys_to_try])` mapping. Replaces the default mapping when given. |
| `extra_fields` | `list[str] \| None` | Extra raw keys to append as columns after the mapped ones. |
| `include_all` | `bool` | If `True`, append every key seen across all events (sorted union) that is not already a column. |

Returns an `ExportResult`. Raises `TraceExportError` if any element of `events`
is not a dict.

### `export_file(source, dest, **kwargs) -> ExportResult`

Load a JSONL file and export it to a CSV file. `**kwargs` are forwarded to
`export_csv` (`fields`, `extra_fields`, `include_all`). Blank lines are skipped;
every non-blank line must be a JSON **object**.

Raises `TraceExportError` if the file is missing, a line is not valid JSON, or a
line is valid JSON but not an object (e.g. an array or a bare scalar). The error
message includes the file path and 1-based line number.

### `ExportResult`

A dataclass with three attributes:

| Attribute | Type | Description |
|-----------|------|-------------|
| `row_count` | `int` | Number of data rows written (header excluded). |
| `columns` | `list[str]` | The CSV column names, in order. |
| `csv_text` | `str` | The full CSV as a string. Empty when a `dest` was given. |

### `TraceExportError`

Base exception raised for all unrecoverable export failures (missing file,
malformed JSON, non-object lines, non-dict events).

## License

MIT
