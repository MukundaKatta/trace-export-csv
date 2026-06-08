"""Tests for trace-export-csv (standard-library unittest only).

Run with:

    python3 -m unittest discover -s tests
"""

import csv
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from trace_export_csv import (  # noqa: E402
    ExportResult,
    TraceExportError,
    export_csv,
    export_file,
)


def parse_csv(text: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(text)))


class BasicExportTests(unittest.TestCase):
    def test_empty_events(self):
        result = export_csv([])
        self.assertEqual(result.row_count, 0)
        self.assertEqual(parse_csv(result.csv_text), [])

    def test_default_columns_present(self):
        result = export_csv([{"kind": "llm_call"}])
        self.assertIn("kind", result.columns)
        self.assertIn("cost_usd", result.columns)
        self.assertIn("tokens_in", result.columns)

    def test_row_count(self):
        events = [{"kind": "a"}, {"kind": "b"}, {"kind": "c"}]
        result = export_csv(events)
        self.assertEqual(result.row_count, 3)

    def test_csv_text_has_rows(self):
        events = [{"kind": "llm_call", "cost_usd": 0.01}]
        result = export_csv(events)
        rows = parse_csv(result.csv_text)
        self.assertEqual(len(rows), 1)

    def test_returns_export_result(self):
        result = export_csv([{"kind": "a"}])
        self.assertIsInstance(result, ExportResult)

    def test_default_column_order(self):
        result = export_csv([{"kind": "a"}])
        self.assertEqual(
            result.columns,
            [
                "timestamp",
                "kind",
                "name",
                "lane",
                "model",
                "tokens_in",
                "tokens_out",
                "cost_usd",
                "duration_ms",
                "error",
            ],
        )

    def test_header_row_written_for_empty(self):
        # Even with no events, the header line must be present.
        result = export_csv([])
        self.assertTrue(result.csv_text.startswith("timestamp,kind,name"))


class FieldMappingTests(unittest.TestCase):
    def test_cost_usd_field(self):
        rows = parse_csv(export_csv([{"cost_usd": 0.05}]).csv_text)
        self.assertEqual(rows[0]["cost_usd"], "0.05")

    def test_cost_fallback_key(self):
        rows = parse_csv(export_csv([{"cost": 0.03}]).csv_text)
        self.assertEqual(rows[0]["cost_usd"], "0.03")

    def test_tokens_in_field(self):
        rows = parse_csv(export_csv([{"input_tokens": 100}]).csv_text)
        self.assertEqual(rows[0]["tokens_in"], "100")

    def test_tokens_out_field(self):
        rows = parse_csv(export_csv([{"output_tokens": 50}]).csv_text)
        self.assertEqual(rows[0]["tokens_out"], "50")

    def test_kind_field(self):
        rows = parse_csv(export_csv([{"kind": "tool_call"}]).csv_text)
        self.assertEqual(rows[0]["kind"], "tool_call")

    def test_type_fallback_for_kind(self):
        rows = parse_csv(export_csv([{"type": "llm_call"}]).csv_text)
        self.assertEqual(rows[0]["kind"], "llm_call")

    def test_missing_field_empty_string(self):
        rows = parse_csv(export_csv([{"kind": "a"}]).csv_text)
        self.assertEqual(rows[0]["cost_usd"], "")
        self.assertEqual(rows[0]["tokens_in"], "")

    def test_error_field(self):
        rows = parse_csv(export_csv([{"error": "timeout"}]).csv_text)
        self.assertEqual(rows[0]["error"], "timeout")

    def test_lane_field(self):
        rows = parse_csv(export_csv([{"lane": "worker-1"}]).csv_text)
        self.assertEqual(rows[0]["lane"], "worker-1")

    def test_model_field(self):
        rows = parse_csv(export_csv([{"model": "claude-sonnet"}]).csv_text)
        self.assertEqual(rows[0]["model"], "claude-sonnet")

    def test_timestamp_field(self):
        rows = parse_csv(export_csv([{"timestamp": 1000.5}]).csv_text)
        self.assertEqual(rows[0]["timestamp"], "1000.5")

    def test_name_field(self):
        rows = parse_csv(export_csv([{"name": "web_search"}]).csv_text)
        self.assertEqual(rows[0]["name"], "web_search")

    def test_first_matching_key_wins(self):
        # tokens_in is preferred over input_tokens / prompt_tokens.
        rows = parse_csv(
            export_csv([{"tokens_in": 1, "input_tokens": 2}]).csv_text
        )
        self.assertEqual(rows[0]["tokens_in"], "1")

    def test_zero_is_not_treated_as_missing(self):
        # 0 is a real value and must not fall through to the next key.
        rows = parse_csv(export_csv([{"cost_usd": 0}]).csv_text)
        self.assertEqual(rows[0]["cost_usd"], "0")

    def test_value_with_comma_is_quoted(self):
        rows = parse_csv(export_csv([{"name": "a,b"}]).csv_text)
        self.assertEqual(rows[0]["name"], "a,b")


class ExtraFieldsTests(unittest.TestCase):
    def test_extra_fields_included(self):
        rows = parse_csv(
            export_csv(
                [{"kind": "a", "custom_key": "hello"}], extra_fields=["custom_key"]
            ).csv_text
        )
        self.assertEqual(rows[0]["custom_key"], "hello")

    def test_extra_fields_missing_is_empty(self):
        rows = parse_csv(
            export_csv([{"kind": "a"}], extra_fields=["nonexistent"]).csv_text
        )
        self.assertEqual(rows[0]["nonexistent"], "")

    def test_extra_fields_appended_after_defaults(self):
        result = export_csv([{"kind": "a", "x": 1}], extra_fields=["x"])
        self.assertEqual(result.columns[-1], "x")


class IncludeAllTests(unittest.TestCase):
    def test_include_all_adds_unknown_keys(self):
        result = export_csv([{"kind": "a", "my_custom": "val"}], include_all=True)
        self.assertIn("my_custom", result.columns)
        rows = parse_csv(result.csv_text)
        self.assertEqual(rows[0]["my_custom"], "val")

    def test_include_all_union_across_events(self):
        events = [{"kind": "a", "key1": 1}, {"kind": "b", "key2": 2}]
        result = export_csv(events, include_all=True)
        self.assertIn("key1", result.columns)
        self.assertIn("key2", result.columns)

    def test_include_all_does_not_duplicate_mapped_keys(self):
        # 'kind' is already a mapped column and must not be added again.
        result = export_csv([{"kind": "a"}], include_all=True)
        self.assertEqual(result.columns.count("kind"), 1)

    def test_include_all_extra_keys_sorted(self):
        result = export_csv([{"zeta": 1, "alpha": 2}], include_all=True)
        extra = [c for c in result.columns if c in ("alpha", "zeta")]
        self.assertEqual(extra, ["alpha", "zeta"])


class CustomFieldsTests(unittest.TestCase):
    def test_custom_fields(self):
        result = export_csv(
            [{"x": 1, "y": 2}], fields=[("col_x", ["x"]), ("col_y", ["y"])]
        )
        self.assertEqual(result.columns, ["col_x", "col_y"])
        rows = parse_csv(result.csv_text)
        self.assertEqual(rows[0]["col_x"], "1")
        self.assertEqual(rows[0]["col_y"], "2")


class DestFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_dest_file_written(self):
        dest = self.tmp_path / "out.csv"
        result = export_csv([{"kind": "a", "cost_usd": 0.01}], dest)
        self.assertTrue(dest.exists())
        self.assertEqual(result.csv_text, "")  # not returned when dest given
        rows = parse_csv(dest.read_text())
        self.assertEqual(rows[0]["kind"], "a")

    def test_dest_parent_created(self):
        dest = self.tmp_path / "a" / "b" / "out.csv"
        export_csv([{"kind": "x"}], dest)
        self.assertTrue(dest.exists())

    def test_dest_accepts_string_path(self):
        dest = str(self.tmp_path / "out.csv")
        export_csv([{"kind": "a"}], dest)
        self.assertTrue(Path(dest).exists())


class ExportFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_export_file(self):
        src = self.tmp_path / "run.jsonl"
        src.write_text(
            json.dumps({"kind": "a", "cost_usd": 0.01})
            + "\n"
            + json.dumps({"kind": "b", "cost_usd": 0.02})
            + "\n"
        )
        dest = self.tmp_path / "out.csv"
        result = export_file(src, dest)
        self.assertEqual(result.row_count, 2)
        rows = parse_csv(dest.read_text())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["kind"], "a")

    def test_export_file_skips_blank_lines(self):
        src = self.tmp_path / "run.jsonl"
        src.write_text(
            json.dumps({"kind": "a"}) + "\n\n   \n" + json.dumps({"kind": "b"}) + "\n"
        )
        result = export_file(src, self.tmp_path / "out.csv")
        self.assertEqual(result.row_count, 2)

    def test_export_file_missing_raises(self):
        with self.assertRaisesRegex(TraceExportError, "not found"):
            export_file(
                self.tmp_path / "__no_trace__.jsonl", self.tmp_path / "out.csv"
            )

    def test_export_file_invalid_json_raises(self):
        src = self.tmp_path / "bad.jsonl"
        src.write_text("not json\n")
        with self.assertRaisesRegex(TraceExportError, "invalid JSON"):
            export_file(src, self.tmp_path / "out.csv")

    def test_export_file_reports_line_number(self):
        src = self.tmp_path / "bad.jsonl"
        src.write_text(
            json.dumps({"kind": "a"}) + "\n" + "{not valid}\n"
        )
        with self.assertRaisesRegex(TraceExportError, ":2:"):
            export_file(src, self.tmp_path / "out.csv")

    def test_export_file_non_object_line_raises(self):
        # A line that is valid JSON but not an object (e.g. an array) must
        # produce a clean TraceExportError, not a raw AttributeError.
        src = self.tmp_path / "arr.jsonl"
        src.write_text(json.dumps(["a", "b", "c"]) + "\n")
        with self.assertRaisesRegex(TraceExportError, "expected a JSON object"):
            export_file(src, self.tmp_path / "out.csv")

    def test_export_file_scalar_line_raises(self):
        src = self.tmp_path / "scalar.jsonl"
        src.write_text("42\n")
        with self.assertRaisesRegex(TraceExportError, "expected a JSON object"):
            export_file(src, self.tmp_path / "out.csv")

    def test_export_file_include_all_kwarg(self):
        src = self.tmp_path / "run.jsonl"
        src.write_text(json.dumps({"kind": "a", "custom": "z"}) + "\n")
        result = export_file(src, self.tmp_path / "out.csv", include_all=True)
        self.assertIn("custom", result.columns)


class NonDictEventTests(unittest.TestCase):
    def test_export_csv_non_dict_event_raises(self):
        with self.assertRaisesRegex(TraceExportError, "not a dict"):
            export_csv([["not", "a", "dict"]])

    def test_export_csv_non_dict_event_index_in_message(self):
        with self.assertRaisesRegex(TraceExportError, "event 1"):
            export_csv([{"kind": "a"}, 42])

    def test_export_csv_non_dict_with_include_all_raises(self):
        with self.assertRaisesRegex(TraceExportError, "not a dict"):
            export_csv([42], include_all=True)


if __name__ == "__main__":
    unittest.main()
