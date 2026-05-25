"""Tests for trace-export-csv."""

import csv
import io
import json
import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))

import pytest
from trace_export_csv import ExportResult, TraceExportError, export_csv, export_file


def parse_csv(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


# ---------------------------------------------------------------------------
# Basic export
# ---------------------------------------------------------------------------

def test_empty_events():
    result = export_csv([])
    assert result.row_count == 0
    rows = parse_csv(result.csv_text)
    assert rows == []


def test_default_columns_present():
    result = export_csv([{"kind": "llm_call"}])
    assert "kind" in result.columns
    assert "cost_usd" in result.columns
    assert "tokens_in" in result.columns


def test_row_count():
    events = [{"kind": "a"}, {"kind": "b"}, {"kind": "c"}]
    result = export_csv(events)
    assert result.row_count == 3


def test_csv_text_has_rows():
    events = [{"kind": "llm_call", "cost_usd": 0.01}]
    result = export_csv(events)
    rows = parse_csv(result.csv_text)
    assert len(rows) == 1


# ---------------------------------------------------------------------------
# Field mapping
# ---------------------------------------------------------------------------

def test_cost_usd_field():
    events = [{"cost_usd": 0.05}]
    result = export_csv(events)
    rows = parse_csv(result.csv_text)
    assert rows[0]["cost_usd"] == "0.05"


def test_cost_fallback_key():
    events = [{"cost": 0.03}]
    result = export_csv(events)
    rows = parse_csv(result.csv_text)
    assert rows[0]["cost_usd"] == "0.03"


def test_tokens_in_field():
    events = [{"input_tokens": 100}]
    result = export_csv(events)
    rows = parse_csv(result.csv_text)
    assert rows[0]["tokens_in"] == "100"


def test_tokens_out_field():
    events = [{"output_tokens": 50}]
    result = export_csv(events)
    rows = parse_csv(result.csv_text)
    assert rows[0]["tokens_out"] == "50"


def test_kind_field():
    events = [{"kind": "tool_call"}]
    result = export_csv(events)
    rows = parse_csv(result.csv_text)
    assert rows[0]["kind"] == "tool_call"


def test_type_fallback_for_kind():
    events = [{"type": "llm_call"}]
    result = export_csv(events)
    rows = parse_csv(result.csv_text)
    assert rows[0]["kind"] == "llm_call"


def test_missing_field_empty_string():
    events = [{"kind": "a"}]
    result = export_csv(events)
    rows = parse_csv(result.csv_text)
    assert rows[0]["cost_usd"] == ""
    assert rows[0]["tokens_in"] == ""


def test_error_field():
    events = [{"error": "timeout"}]
    result = export_csv(events)
    rows = parse_csv(result.csv_text)
    assert rows[0]["error"] == "timeout"


def test_lane_field():
    events = [{"lane": "worker-1"}]
    result = export_csv(events)
    rows = parse_csv(result.csv_text)
    assert rows[0]["lane"] == "worker-1"


def test_model_field():
    events = [{"model": "claude-sonnet"}]
    result = export_csv(events)
    rows = parse_csv(result.csv_text)
    assert rows[0]["model"] == "claude-sonnet"


def test_timestamp_field():
    events = [{"timestamp": 1000.5}]
    result = export_csv(events)
    rows = parse_csv(result.csv_text)
    assert rows[0]["timestamp"] == "1000.5"


def test_name_field():
    events = [{"name": "web_search"}]
    result = export_csv(events)
    rows = parse_csv(result.csv_text)
    assert rows[0]["name"] == "web_search"


# ---------------------------------------------------------------------------
# extra_fields
# ---------------------------------------------------------------------------

def test_extra_fields_included():
    events = [{"kind": "a", "custom_key": "hello"}]
    result = export_csv(events, extra_fields=["custom_key"])
    rows = parse_csv(result.csv_text)
    assert rows[0]["custom_key"] == "hello"


def test_extra_fields_missing_is_empty():
    events = [{"kind": "a"}]
    result = export_csv(events, extra_fields=["nonexistent"])
    rows = parse_csv(result.csv_text)
    assert rows[0]["nonexistent"] == ""


# ---------------------------------------------------------------------------
# include_all
# ---------------------------------------------------------------------------

def test_include_all_adds_unknown_keys():
    events = [{"kind": "a", "my_custom": "val"}]
    result = export_csv(events, include_all=True)
    assert "my_custom" in result.columns
    rows = parse_csv(result.csv_text)
    assert rows[0]["my_custom"] == "val"


def test_include_all_union_across_events():
    events = [
        {"kind": "a", "key1": 1},
        {"kind": "b", "key2": 2},
    ]
    result = export_csv(events, include_all=True)
    assert "key1" in result.columns
    assert "key2" in result.columns


# ---------------------------------------------------------------------------
# custom fields override
# ---------------------------------------------------------------------------

def test_custom_fields():
    events = [{"x": 1, "y": 2}]
    result = export_csv(events, fields=[("col_x", ["x"]), ("col_y", ["y"])])
    assert result.columns == ["col_x", "col_y"]
    rows = parse_csv(result.csv_text)
    assert rows[0]["col_x"] == "1"
    assert rows[0]["col_y"] == "2"


# ---------------------------------------------------------------------------
# dest file
# ---------------------------------------------------------------------------

def test_dest_file_written(tmp_path):
    dest = tmp_path / "out.csv"
    events = [{"kind": "a", "cost_usd": 0.01}]
    result = export_csv(events, dest)
    assert dest.exists()
    assert result.csv_text == ""  # not returned when dest is given
    rows = parse_csv(dest.read_text())
    assert rows[0]["kind"] == "a"


def test_dest_parent_created(tmp_path):
    dest = tmp_path / "a" / "b" / "out.csv"
    export_csv([{"kind": "x"}], dest)
    assert dest.exists()


# ---------------------------------------------------------------------------
# export_file
# ---------------------------------------------------------------------------

def test_export_file(tmp_path):
    src = tmp_path / "run.jsonl"
    src.write_text(
        json.dumps({"kind": "a", "cost_usd": 0.01}) + "\n" +
        json.dumps({"kind": "b", "cost_usd": 0.02}) + "\n"
    )
    dest = tmp_path / "out.csv"
    result = export_file(src, dest)
    assert result.row_count == 2
    rows = parse_csv(dest.read_text())
    assert len(rows) == 2
    assert rows[0]["kind"] == "a"


def test_export_file_missing_raises():
    with pytest.raises(TraceExportError, match="not found"):
        export_file("/tmp/__no_trace__.jsonl", "/tmp/out.csv")


def test_export_file_invalid_json_raises(tmp_path):
    src = tmp_path / "bad.jsonl"
    src.write_text("not json\n")
    with pytest.raises(TraceExportError, match="invalid JSON"):
        export_file(src, tmp_path / "out.csv")
