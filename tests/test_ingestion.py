"""Unit tests for CSV ingestion module (Section 7.1, Section 16)."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from ads.config import load_config
from ads.ingestion import compute_sha256, load_csv


class TestIngestion(unittest.TestCase):
    def test_standard_csv_preserves_raw_strings(self) -> None:
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "sample.csv"
            p.write_text(
                "id,amount,status\n"
                "001, 12.50 ,N/A\n"
                "002,100.00,\n"
                "003,?,Active\n",
                encoding="utf-8",
            )
            res = load_csv(p)
            self.assertEqual(res.metadata.n_rows, 3)
            self.assertEqual(res.metadata.n_cols, 3)
            self.assertEqual(res.metadata.encoding, "utf-8")
            self.assertFalse(res.metadata.encoding_fallback_used)
            self.assertEqual(res.metadata.delimiter, ",")
            self.assertEqual(res.metadata.sha256, compute_sha256(p))

            # df_raw_str must preserve leading zeros, spaces, and placeholder tokens
            self.assertEqual(res.df_raw_str.loc[0, "id"], "001")
            self.assertEqual(res.df_raw_str.loc[0, "amount"], " 12.50 ")
            self.assertEqual(res.df_raw_str.loc[0, "status"], "N/A")
            self.assertEqual(res.df_raw_str.loc[1, "status"], "")

            # df_naive should have parsed id as int64
            self.assertTrue(str(res.df_naive["id"].dtype).startswith("int"))

    def test_bom_and_semicolon_delimiter(self) -> None:
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "semicolon_bom.csv"
            raw_bytes = b"\xef\xbb\xbfage;job;balance\n30;admin;1787\n33;services;4789\n"
            p.write_bytes(raw_bytes)

            res = load_csv(p)
            self.assertEqual(res.metadata.encoding, "utf-8-sig")
            self.assertFalse(res.metadata.encoding_fallback_used)
            self.assertEqual(res.metadata.delimiter, ";")
            self.assertEqual(list(res.df_raw_str.columns), ["age", "job", "balance"])
            self.assertEqual(res.df_raw_str.loc[0, "job"], "admin")

    def test_latin1_fallback_encoding(self) -> None:
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "latin1.csv"
            content = "city,note\nMontréal,café résumé\nZürich,naïve\n"
            p.write_bytes(content.encode("latin-1"))

            res = load_csv(p)
            self.assertEqual(res.metadata.encoding, "latin-1")
            self.assertTrue(res.metadata.encoding_fallback_used)
            self.assertEqual(res.df_raw_str.loc[0, "city"], "Montréal")
            self.assertTrue(
                any("encoding fallback" in w for w in res.metadata.warnings)
            )

    def test_duplicate_and_empty_column_names(self) -> None:
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "headers.csv"
            p.write_text(
                "Unnamed: 0, Region ,Region,,Region\n"
                "0,North,South,X,East\n",
                encoding="utf-8",
            )
            res = load_csv(p)
            self.assertEqual(
                list(res.df_raw_str.columns),
                ["Unnamed: 0", "Region", "Region.1", "unnamed_3", "Region.2"],
            )
            self.assertIn(" Region ", res.metadata.column_name_changes)
            self.assertIn("<empty_3>", res.metadata.column_name_changes)

    def test_quoted_fields_embedded_newlines_and_ragged_rows(self) -> None:
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "ragged.csv"
            p.write_text(
                'id,comment,score\n'
                '1,"hello, world\nsecond line",95\n'
                '2,too,many,fields,here,100\n'
                '3,"clean",88\n',
                encoding="utf-8",
            )
            res = load_csv(p)
            self.assertEqual(res.metadata.n_rows, 2)
            self.assertEqual(res.metadata.n_bad_lines, 1)
            self.assertEqual(res.df_raw_str.loc[0, "comment"], "hello, world\nsecond line")
            self.assertEqual(res.df_raw_str.loc[1, "id"], "3")

    def test_trailing_delimiters(self) -> None:
        with TemporaryDirectory() as tmp:
            p = Path(tmp) / "trailing.csv"
            p.write_text("col1,col2\n10,20,\n30,40,\n", encoding="utf-8")
            res = load_csv(p)
            self.assertEqual(res.metadata.n_rows, 2)
            self.assertEqual(res.metadata.n_bad_lines, 0)
            self.assertEqual(res.df_raw_str.loc[0, "col1"], "10")
            self.assertEqual(res.df_raw_str.loc[0, "col2"], "20")

    def test_header_only_and_single_column_csv(self) -> None:
        with TemporaryDirectory() as tmp:
            p_header = Path(tmp) / "header_only.csv"
            p_header.write_text("a,b,c\n", encoding="utf-8")
            res_h = load_csv(p_header)
            self.assertEqual(res_h.metadata.n_rows, 0)
            self.assertEqual(res_h.metadata.n_cols, 3)

            p_single = Path(tmp) / "single_col.csv"
            p_single.write_text("only_col\nval1\nval2\n", encoding="utf-8")
            res_s = load_csv(p_single)
            self.assertEqual(res_s.metadata.n_rows, 2)
            self.assertEqual(res_s.metadata.n_cols, 1)

    def test_guardrails_missing_empty_and_oversized(self) -> None:
        with TemporaryDirectory() as tmp:
            missing_path = Path(tmp) / "does_not_exist.csv"
            with self.assertRaises(FileNotFoundError):
                load_csv(missing_path)

            empty_path = Path(tmp) / "empty.csv"
            empty_path.write_bytes(b"")
            with self.assertRaises(ValueError):
                load_csv(empty_path)

            ws_path = Path(tmp) / "ws.csv"
            ws_path.write_text("   \n\t  \n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_csv(ws_path)

            big_path = Path(tmp) / "big.csv"
            big_path.write_text("a,b\n" + "1,2\n" * 500, encoding="utf-8")
            small_cfg = load_config(cli_overrides={"ingestion": {"max_file_size_mb": 0.0001}})
            with self.assertRaises(ValueError):
                load_csv(big_path, config=small_cfg)


if __name__ == "__main__":
    unittest.main()

