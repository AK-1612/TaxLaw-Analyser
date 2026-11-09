#!/usr/bin/env bash
# Tax Law Delta Analyzer - Complete Demonstration Runner
# Author: Anshul Kumaria

set -e
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$BASE_DIR"

echo "================================================================================"
echo "          TAX LAW DELTA ANALYZER // FULL DEMONSTRATION SUITE                    "
echo "          Lead Analyst: Anshul Kumaria | Ernst & Young LLP                      "
echo "================================================================================"
echo ""

echo ">>> [1/4] Running Automated Test Suite..."
./.venv/bin/python -m unittest tests/test_analyzer.py
echo ""

echo ">>> [2/4] Generating Multi-Scale Enterprise ROI Benchmarks..."
./.venv/bin/python generate_benchmark_report.py
echo ""

echo ">>> [3/4] Inspecting Section 168(k) Bonus Depreciation Diff in Terminal..."
./.venv/bin/python viewer.py --section "168(k)"
echo ""

echo ">>> [4/4] Executing End-to-End Enterprise Tax Code Analysis..."
./.venv/bin/python cli.py --pdf-a test_docs/FY25_Enterprise_Tax_Code.pdf --pdf-b test_docs/FY26_Enterprise_Tax_Code.pdf
echo ""

echo "================================================================================"
echo "          DEMONSTRATION COMPLETE - ALL ARTIFACTS RECORDED IN contextsentry.db   "
echo "================================================================================"

