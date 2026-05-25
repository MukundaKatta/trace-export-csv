# trace-export-csv

Export JSONL agent traces to CSV for spreadsheet and BI analysis.

Zero dependencies. Python 3.10+. MIT.

## Install

```bash
pip install trace-export-csv
```

## Usage

```python
from trace_export_csv import export_file

result = export_file("logs/run.jsonl", "analysis/run.csv")
print(f"Exported {result.row_count} rows, columns: {result.columns}")
```

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

## License

MIT
