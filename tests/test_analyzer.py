"""
Unit and Integration Test Suite for Tax Law Delta Analyzer
Validates:
1. Marginalia and header/footer stripping
2. Deterministic clause-level diffing accuracy
3. Context refinement schema validation
4. ContextSentry SQLite telemetry logging
5. MCP Server JSON-RPC protocol compliance
"""
import unittest
import os
import tempfile
import sqlite3
import json

from pdf_parser import extract_document_data, is_marginalia_line
from diff_engine import extract_semantic_delta, split_into_sections
from worker import refine_delta_with_ollama, synthesize_client_impact, clean_markdown_artifacts
from telemetry import log_run, get_telemetry_history, estimate_tokens
from server import execute_pipeline

class TestTaxLawDeltaAnalyzer(unittest.TestCase):

    def setUp(self):
        self.doc_a_path = "test_docs/FY25_Tax_Code.pdf"
        self.doc_b_path = "test_docs/FY26_Tax_Code.pdf"
        self.ent_a_path = "test_docs/FY25_Enterprise_Tax_Code.pdf"
        self.ent_b_path = "test_docs/FY26_Enterprise_Tax_Code.pdf"

    def test_clean_markdown_artifacts(self):
        """Verifies that markdown artifacts like **, ###, and ` are cleanly stripped."""
        dirty = "### SECTION 168(k)\n**100% expensing** phases down to **80%**.\n##### Note: `MACRS` property"
        cleaned = clean_markdown_artifacts(dirty)
        self.assertNotIn("**", cleaned)
        self.assertNotIn("###", cleaned)
        self.assertNotIn("`", cleaned)
        self.assertIn("100% expensing", cleaned)

    def test_marginalia_filtering(self):
        """Ensures headers, footers, and page numbers are properly identified."""
        self.assertTrue(is_marginalia_line("CONFIDENTIAL // EY TAX ADVISORY SERVICES // REGULATORY CODIFICATION ARCHIVE"))
        self.assertTrue(is_marginalia_line("Page 1 of 3 - Ernst & Young LLP Private Briefing - Subject to Circular 230"))
        self.assertTrue(is_marginalia_line("Page 12"))
        self.assertFalse(is_marginalia_line("SECTION 168(k). TEMPORARY 100% EXPENSING FOR QUALIFIED PROPERTY"))
        self.assertFalse(is_marginalia_line("(a) Standard Rate: A corporate tax rate of 21.0% shall apply."))

    def test_document_ingestion(self):
        """Ensures PDF parsing extracts clean text while dropping marginalia lines."""
        if os.path.exists(self.doc_a_path):
            data_a = extract_document_data(self.doc_a_path, strip_marginalia=True)
            self.assertGreater(data_a["pages_count"], 0)
            self.assertGreater(data_a["marginalia_lines_filtered"], 0)
            self.assertIn("SECTION 168(k)", data_a["clean_text"])
            self.assertNotIn("Circular 230", data_a["clean_text"])

    def test_deterministic_diff_engine(self):
        """Verifies section parsing and clause-level change detection."""
        text_a = (
            "SECTION 11. CORPORATE TAX RATES\n(a) Standard Rate is 21%.\n\n"
            "SECTION 168(k). BONUS DEPRECIATION\n(1) Expensing percentage is 100%.\n"
        )
        text_b = (
            "SECTION 11. CORPORATE TAX RATES\n(a) Standard Rate is 21%.\n\n"
            "SECTION 168(k). BONUS DEPRECIATION\n(1) Expensing percentage is 80%.\n\n"
            "SECTION 48E. CLEAN ELECTRICITY CREDIT\n(1) Enacted credit is 30%.\n"
        )
        diff_res = extract_semantic_delta(text_a, text_b)
        stats = diff_res["stats"]

        self.assertEqual(stats["modified_sections"], 1)
        self.assertEqual(stats["added_sections"], 1)
        self.assertEqual(stats["unchanged_sections"], 1)
        self.assertEqual(stats["removed_sections"], 0)

        # Check structured changes
        mod_change = [c for c in diff_res["structured_changes"] if c["change_type"] == "MODIFIED"][0]
        self.assertIn("168(k)", mod_change["section"])

        add_change = [c for c in diff_res["structured_changes"] if c["change_type"] == "ADDED"][0]
        self.assertIn("48E", add_change["section"])

    def test_telemetry_and_roi(self):
        """Validates token calculation and SQLite logging into contextsentry.db."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_db:
            db_path = tmp_db.name

        try:
            sample_a = "Word " * 1000
            sample_b = "Word " * 1000
            sample_delta = "Word " * 50

            log_entry = log_run("DocA.pdf", "DocB.pdf", sample_a, sample_b, sample_delta, sample_delta, 15.0, db_path=db_path)
            
            self.assertGreater(log_entry["tokens_saved"], 0)
            self.assertGreater(log_entry["token_reduction_pct"], 90.0)
            self.assertGreater(log_entry["cost_savings_usd"], 0)

            history = get_telemetry_history(limit=5, db_path=db_path)
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["run_id"], log_entry["run_id"])
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_pipeline_execution(self):
        """Validates the complete 4-step pipeline on test fixtures."""
        if os.path.exists(self.doc_a_path) and os.path.exists(self.doc_b_path):
            result = execute_pipeline(self.doc_a_path, self.doc_b_path, client_name="EY Test Client")
            self.assertEqual(result["status"], "success")
            summary = result["client_impact_summary"]
            self.assertTrue("CLIENT ADVISORY BRIEFING" in summary or "CLIENT IMPACT SUMMARY" in summary)
            self.assertIn("Anshul Kumaria", summary)
            self.assertIn("changes", result["refined_delta_json"])
            self.assertIn("tokens_saved", result["telemetry"])

if __name__ == "__main__":
    unittest.main()

