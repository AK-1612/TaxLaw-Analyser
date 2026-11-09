#!/usr/bin/env python3
"""
Tax Law Delta Viewer (viewer.py)
Author: Anshul Kumaria
Specialized terminal diff viewer for EY tax professionals to inspect clause-by-clause
regulatory amendments with colorized diffs, section tagging, and marginalia audits.
"""
import sys
import os
import argparse
from pdf_parser import extract_document_data
from diff_engine import extract_semantic_delta
from worker import clean_markdown_artifacts

# Terminal colors
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
DIM = "\033[2m"
RESET = "\033[0m"

def render_diff_viewer(doc_a_path: str, doc_b_path: str, section_filter: str = None, author: str = "Anshul Kumaria"):
    print(f"\n{BOLD}{CYAN}" + "=" * 80)
    print("           EY TAX LAW DELTA VIEWER // DETERMINISTIC CLAUSE INSPECTOR           ")
    print(f"        Lead Analyst: {author} | Ernst & Young LLP Tax Advisory Practice        ")
    print("=" * 80 + f"{RESET}\n")

    print(f"{BOLD}Baseline Regulatory Document (Year A):{RESET} {doc_a_path}")
    print(f"{BOLD}Updated Regulatory Document (Year B): {RESET} {doc_b_path}\n")

    # Ingestion
    doc_a = extract_document_data(doc_a_path, strip_marginalia=True)
    doc_b = extract_document_data(doc_b_path, strip_marginalia=True)

    print(f"{DIM}[Audit] Stripped {doc_a['marginalia_lines_filtered']} lines of marginalia from Doc A and {doc_b['marginalia_lines_filtered']} lines from Doc B.{RESET}\n")

    # Diffing
    delta_res = extract_semantic_delta(doc_a["clean_text"], doc_b["clean_text"])
    changes = delta_res["structured_changes"]
    stats = delta_res["stats"]

    print(f"{BOLD}Summary of Regulatory Changes:{RESET}")
    print(f"  • Total Sections Compared: {stats['sections_doc_b']}")
    print(f"  • Unchanged (Bypassed):   {stats['unchanged_sections']}")
    print(f"  • Modified Provisions:    {stats['modified_sections']}")
    print(f"  • Enacted New Sections:   {stats['added_sections']}")
    print(f"  • Sunset or Repealed:     {stats['removed_sections']}")
    print("-" * 80 + "\n")

    matched_count = 0
    for idx, chg in enumerate(changes, 1):
        section_name = clean_markdown_artifacts(chg["section"])
        if section_filter and section_filter.lower() not in section_name.lower():
            continue

        matched_count += 1
        chg_type = chg["change_type"]
        tag_color = YELLOW if chg_type == "MODIFIED" else (GREEN if chg_type == "ADDED" else RED)
        
        print(f"{BOLD}{tag_color}[{idx}] {chg_type}: {section_name}{RESET}")
        
        diff_lines = chg.get("diff_lines", [])
        if diff_lines:
            for line in diff_lines:
                clean_l = clean_markdown_artifacts(line)
                if line.startswith("+") and not line.startswith("+++"):
                    print(f"  {GREEN}{clean_l}{RESET}")
                elif line.startswith("-") and not line.startswith("---"):
                    print(f"  {RED}{clean_l}{RESET}")
                elif line.startswith("@@"):
                    print(f"  {CYAN}{clean_l}{RESET}")
        else:
            if chg_type == "ADDED":
                for l in chg["text_updated"].splitlines():
                    print(f"  {GREEN}+ {clean_markdown_artifacts(l)}{RESET}")
            elif chg_type == "REMOVED":
                for l in chg["text_prior"].splitlines():
                    print(f"  {RED}- {clean_markdown_artifacts(l)}{RESET}")

        print("")

    if matched_count == 0:
        print(f"{YELLOW}No sections matched filter '{section_filter}'.{RESET}\n")

    print(f"{CYAN}" + "=" * 80 + f"{RESET}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EY Tax Law Delta Terminal Viewer - Anshul Kumaria")
    parser.add_argument("--doc-a", default="test_docs/FY25_Enterprise_Tax_Code.pdf", help="Path to Year A PDF")
    parser.add_argument("--doc-b", default="test_docs/FY26_Enterprise_Tax_Code.pdf", help="Path to Year B PDF")
    parser.add_argument("--section", help="Filter for specific section (e.g. '168(k)', '174', '163(j)')")
    parser.add_argument("--author", default="Anshul Kumaria", help="Author name")
    args = parser.parse_args()

    render_diff_viewer(args.doc_a, args.doc_b, section_filter=args.section, author=args.author)
