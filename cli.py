#!/usr/bin/env python3
"""
Tax Law Delta Analyzer - Interactive Terminal CLI
Author: Anshul Kumaria
Demonstrates the complete 4-step pipeline:
  Step 1: Document Ingestion & Marginalia Stripping
  Step 2: Local Deterministic Diffing
  Step 3: Offloaded Context Refinement (Ollama/Llama 3.2)
  Step 4: Primary LLM Synthesis
  Step 5: ContextSentry Telemetry & Financial ROI Benchmark
"""
import sys
import os
import json
import argparse

from pdf_parser import extract_document_data
from diff_engine import extract_semantic_delta
from worker import refine_delta_with_ollama, synthesize_client_impact, clean_markdown_artifacts
from telemetry import log_run, get_telemetry_history, format_benchmark_card

# Terminal ANSI styling helpers
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
RESET = "\033[0m"

def print_header():
    print(f"{CYAN}{BOLD}")
    print("================================================================================")
    print("       TAX LAW DELTA ANALYZER // ERNST & YOUNG STRATEGIC AUTOMATION             ")
    print("   Deterministic State Diffing and Offloaded Context Refinement Architecture    ")
    print("   Lead Analyst: Anshul Kumaria | EY Tax Advisory Practice                      ")
    print("================================================================================")
    print(f"{RESET}")

def run_cli_demo(pdf_a: str, pdf_b: str, client_name: str = "Fortune 500 Enterprise Client", author: str = "Anshul Kumaria"):
    print_header()
    print(f"{BOLD}[>] Lead Advisor:{RESET} {author}")
    print(f"{BOLD}[>] Target Client:{RESET} {client_name}")
    print(f"{BOLD}[>] Baseline Regulatory Document (Year A):{RESET} {pdf_a}")
    print(f"{BOLD}[>] Updated Regulatory Document (Year B):{RESET}  {pdf_b}\n")

    # --------------------------------------------------------------------------
    # STEP 1: DOCUMENT INGESTION & MARGINALIA STRIPPING
    # --------------------------------------------------------------------------
    print(f"{BLUE}{BOLD}[STEP 1 / 4] Document Ingestion and Marginalia Stripping...{RESET}")
    doc_a = extract_document_data(pdf_a, strip_marginalia=True)
    doc_b = extract_document_data(pdf_b, strip_marginalia=True)

    print(f"  • Document A: {doc_a['pages_count']} pages | {doc_a['raw_char_count']:,} raw characters -> {doc_a['clean_char_count']:,} clean characters")
    print(f"    Filtered {YELLOW}{doc_a['marginalia_lines_filtered']}{RESET} marginalia, header, and footer lines to prevent false diffs")
    print(f"  • Document B: {doc_b['pages_count']} pages | {doc_b['raw_char_count']:,} raw characters -> {doc_b['clean_char_count']:,} clean characters")
    print(f"    Filtered {YELLOW}{doc_b['marginalia_lines_filtered']}{RESET} marginalia, header, and footer lines to prevent false diffs\n")

    # --------------------------------------------------------------------------
    # STEP 2: LOCAL DETERMINISTIC DIFFING
    # --------------------------------------------------------------------------
    print(f"{BLUE}{BOLD}[STEP 2 / 4] Local Deterministic State Diffing (Clause-Level)...{RESET}")
    diff_res = extract_semantic_delta(doc_a["clean_text"], doc_b["clean_text"])
    stats = diff_res["stats"]
    
    print(f"  • Analyzed {stats['sections_doc_a']} baseline sections against {stats['sections_doc_b']} revised sections:")
    print(f"    - Modified Sections: {YELLOW}{stats['modified_sections']}{RESET}")
    print(f"    - Added Sections:    {GREEN}{stats['added_sections']}{RESET}")
    print(f"    - Removed Sections:  {RED}{stats['removed_sections']}{RESET}")
    print(f"    - Unchanged Clauses: {DIM}{stats['unchanged_sections']}{RESET} (isolated and filtered out from LLM payload)")
    print(f"    - Net Delta Lines:   {stats['added_lines']} added (+), {stats['deleted_lines']} deleted (-)\n")

    print(f"{MAGENTA}{BOLD}--- Deterministic Clause Delta Snippet (First 2 Changed Sections) ---{RESET}")
    preview_blocks = diff_res["compact_delta_text"].split("===")[1:3]
    for b in preview_blocks:
        clean_b = clean_markdown_artifacts(b.strip())
        print(f"==={clean_b}\n")

    # --------------------------------------------------------------------------
    # STEP 3: OFFLOADED CONTEXT REFINEMENT (OLLAMA / LLAMA 3.2)
    # --------------------------------------------------------------------------
    print(f"{BLUE}{BOLD}[STEP 3 / 4] Offloaded Context Refinement (Ollama / Llama 3.2 Worker)...{RESET}")
    print("  Standardizing raw unified diff into clean semantic JSON payload...")
    refined = refine_delta_with_ollama(diff_res["compact_delta_text"], structured_changes=diff_res["structured_changes"])
    print(f"  • Refinement Engine: {GREEN}{refined.get('_engine', 'local_worker')}{RESET}")
    print(f"  • Extracted {len(refined.get('changes', []))} high-impact statutory amendments.")
    print(f"{DIM}  Sample Refined JSON Output:{RESET}")
    sample_preview = {
        "summary_of_scope": refined.get("summary_of_scope"),
        "changes_sample": refined.get("changes", [])[:2]
    }
    print(f"{DIM}{json.dumps(sample_preview, indent=2)}{RESET}\n")

    # --------------------------------------------------------------------------
    # STEP 4: PRIMARY LLM SYNTHESIS
    # --------------------------------------------------------------------------
    print(f"{BLUE}{BOLD}[STEP 4 / 4] Primary LLM Synthesis: Executive Client Impact Briefing...{RESET}")
    summary = synthesize_client_impact(refined, client_name=client_name, lead_author=author)
    print(f"\n{GREEN}{summary}{RESET}\n")

    # --------------------------------------------------------------------------
    # STEP 5: CONTEXTSENTRY TELEMETRY & BENCHMARK REPORT
    # --------------------------------------------------------------------------
    refined_str = json.dumps(refined)
    telemetry = log_run(
        pdf_a, pdf_b,
        doc_a["clean_text"], doc_b["clean_text"],
        diff_res["compact_delta_text"], refined_str, 42.5
    )

    print(f"{CYAN}{BOLD}{format_benchmark_card(telemetry)}{RESET}")
    print(f"\n{GREEN}Run successfully recorded to SQLite database: contextsentry.db{RESET}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tax Law Delta Analyzer CLI - Anshul Kumaria")
    parser.add_argument("--pdf-a", default="test_docs/FY25_Enterprise_Tax_Code.pdf", help="Baseline PDF")
    parser.add_argument("--pdf-b", default="test_docs/FY26_Enterprise_Tax_Code.pdf", help="Revised PDF")
    parser.add_argument("--client", default="Fortune 500 Enterprise Client", help="Target client name")
    parser.add_argument("--author", default="Anshul Kumaria", help="Lead advisor name")
    parser.add_argument("--history", action="store_true", help="Display recent benchmark telemetry records")
    args = parser.parse_args()

    if args.history:
        runs = get_telemetry_history(limit=5)
        print(f"\n{CYAN}{BOLD}=== RECENT CONTEXTSENTRY BENCHMARK RUNS (contextsentry.db) ==={RESET}\n")
        for r in runs:
            print(f"Run ID: {r['run_id']} | Date: {r['timestamp']}")
            print(f"Files:  {r['doc_a_name']} vs {r['doc_b_name']}")
            print(f"Tokens: {r['total_input_tokens']} original -> {r['refined_delta_tokens']} delta ({r['token_reduction_pct']}% reduction)")
            print(f"Saved:  ${r['cost_savings_usd']:.5f} USD per execution")
            print("-" * 65)
    else:
        run_cli_demo(args.pdf_a, args.pdf_b, client_name=args.client, author=args.author)
