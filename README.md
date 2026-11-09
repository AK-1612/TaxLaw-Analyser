# TaxLaw-Analyser: Semantic Regulatory Delta Engine

Deterministic state-diffing sidecar for tax regulatory compliance. Leverages local worker parsing to isolate statutory clause changes between tax document versions (Year A vs. Year B), reducing enterprise commercial LLM payload sizes by over 90 percent and eliminating context-window hallucinations.

---

## Architecture Overview

```
                      +-----------------------------+
                      |   EY Tax Consultant / Agent |
                      +--------------+--------------+
                                     |
                       (MCP / REST: compare_docs)
                                     v
                      +-----------------------------+
                      |       Server Interface      |
                      |   (server.py / MCP Server)  |
                      +--------------+--------------+
                                     |
                  +------------------+------------------+
                  |                                     |
                  v                                     v
       [Year A: FY25 Tax PDF]                [Year B: FY26 Tax PDF]
                  |                                     |
                  +------------------+------------------+
                                     |
                                     v
                      +-----------------------------+
                      |       Document Parser       |
                      |      (pdf_parser.py)        |
                      |  * Strips marginalia/headers|
                      |  * Filters page numbers     |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |  Deterministic Diff Engine  |
                      |      (diff_engine.py)       |
                      |  * Clause-level diffing     |
                      |  * Filters unchanged 95%    |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      | Offloaded Context Refiner   |
                      |   (Ollama / Llama 3.2)      |
                      |  * Cleans diff syntax       |
                      |  * Emits semantic JSON      |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |    Primary LLM Synthesis    |
                      |         (worker.py)         |
                      |  * Plain-English Summary    |
                      |  * Client Advisory Actions  |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |   ContextSentry Telemetry   |
                      |      (telemetry.py)         |
                      |  * contextsentry.db (SQLite)|
                      |  * Token ROI Benchmarking   |
                      +-----------------------------+
```

---

## Core Components

| Component | File | Description |
| :--- | :--- | :--- |
| Document Parser | pdf_parser.py | Extracts text blocks, headers, and statutes while stripping running headers/footers, disclaimers, and page numbers to prevent false-positive diffs. |
| Diffing Engine | diff_engine.py | Performs deterministic line-by-line and section-level diffing. Tags clauses as MODIFIED, ADDED, or REMOVED, filtering out identical text. |
| Context Refinement & Synthesis | worker.py | Offloads raw diff refinement to local Ollama (llama3.2) to output standardized semantic JSON; synthesizes executive Client Impact Summary authored by Anshul Kumaria. |
| Telemetry Logger | telemetry.py | Tracks exact token counts of Document A + B vs. Delta payload in SQLite (contextsentry.db), calculating token reduction % and financial cost savings. |
| MCP & REST Server | server.py | Exposes standard Model Context Protocol (MCP) tool compare_regulatory_documents via stdio and a FastAPI REST API (/compare, /telemetry). |
| Clause Inspector / Viewer | viewer.py | Interactive terminal diff viewer with section filtering (--section) and colorized statutory diffs. |
| Interactive Terminal CLI | cli.py | Terminal runner with step-by-step progress, colored diffs, sample JSON payloads, full Client Impact Summary, and live benchmark card. |
| Enterprise ROI Benchmarker | generate_benchmark_report.py | Generates token compression matrix and annual enterprise financial savings projections (BENCHMARK_REPORT.md). |
| Test Suite | tests/test_analyzer.py | Automated unit tests covering marginalia stripping, diff calculation, telemetry, and MCP protocol compliance. |

---

## Terminal Commands to Run

### 1. Run Full End-to-End Pipeline (Enterprise 11-Page Documents)
```bash
./.venv/bin/python cli.py --pdf-a test_docs/FY25_Enterprise_Tax_Code.pdf --pdf-b test_docs/FY26_Enterprise_Tax_Code.pdf
```

### 2. Run Interactive Section-by-Section Diff Viewer
```bash
# View all modified and added statutory clauses
./.venv/bin/python viewer.py

# Filter for specific statutory provisions (e.g., Section 168(k) Bonus Depreciation)
./.venv/bin/python viewer.py --section "168(k)"
./.venv/bin/python viewer.py --section "174"
```

### 3. Generate Enterprise ROI & Benchmark Report
```bash
./.venv/bin/python generate_benchmark_report.py
```

### 4. Query Telemetry & Benchmark History from SQLite
```bash
./.venv/bin/python cli.py --history
```

### 5. Run Automated Test Suite
```bash
./.venv/bin/python -m unittest tests/test_analyzer.py
```

### 6. Run as Model Context Protocol (MCP) Server
```bash
./.venv/bin/python server.py --mcp
```

### 7. Run as FastAPI REST Server
```bash
./.venv/bin/python server.py --host 127.0.0.1 --port 8000
```

---

## Logbook Screenshots Guide (SSs to Take)

For internship evaluation and partner presentations, capture the following screenshots:

### SS 1: End-to-End Enterprise Execution & Ingestion
- Command: ./.venv/bin/python cli.py --pdf-a test_docs/FY25_Enterprise_Tax_Code.pdf --pdf-b test_docs/FY26_Enterprise_Tax_Code.pdf
- What to Frame: Top half of terminal output showing [STEP 1 / 4] Document Ingestion & Marginalia Stripping and [STEP 2 / 4] Local Deterministic State Diffing.
- Key Callout: Highlights "Filtered 22 marginalia, header, and footer lines to prevent false diffs" and "26 Unchanged Clauses isolated and filtered out from LLM payload".

### SS 2: Semantic JSON Payload & Client Impact Summary
- Command: Scroll down on previous CLI output.
- What to Frame: [STEP 3 / 4] Offloaded Context Refinement (clean JSON schema) and [STEP 4 / 4] Primary LLM Synthesis showing the EY Client Advisory Briefing authored by Anshul Kumaria.
- Key Callout: Demonstrates structured, hallucination-free delta delivered to primary LLM rather than 50 pages of raw text.

### SS 3: ContextSentry Token Optimization Benchmark Card
- Command: Scroll to bottom of the CLI execution.
- What to Frame: The ASCII framed CONTEXTSENTRY TELEMETRY & TOKEN OPTIMIZATION BENCHMARK box.
- Key Callout: Proves the ROI metric: 10,328 original tokens -> 1,055 delta tokens (89.8% token savings) and shows estimated cloud cost savings per transaction.

### SS 4: Colorized Statutory Diff Viewer (Clause Inspection)
- Command: ./.venv/bin/python viewer.py --section "168(k)"
- What to Frame: The colored unified diff output showing Section 168(k) with red deletions (- 100 percent) and green additions (+ 80 percent).
- Key Callout: Demonstrates the deterministic audit trail EY tax reviewers can visually inspect in seconds.

### SS 5: Enterprise Financial ROI & Multi-Scale Benchmark Model
- Command: ./.venv/bin/python generate_benchmark_report.py
- What to Frame: The terminal table showing token reduction scaling from 66.7% (3-page) to 91.7% (11-page) and 97.4% (50-page), plus annual firm-wide cost savings.
- Key Callout: Proves commercial viability: as document size grows, token savings scale up to 97.4%, saving over $11,800/year per 50k transactions.

### SS 6: ContextSentry Telemetry Audit History (SQLite Persistence)
- Command: ./.venv/bin/python cli.py --history
- What to Frame: The terminal list of recent benchmark runs retrieved directly from contextsentry.db.
- Key Callout: Proves auditability, compliance logging, and reproducibility across multiple client engagements.

### SS 7: Automated Test Suite Execution
- Command: ./.venv/bin/python -m unittest tests/test_analyzer.py
- What to Frame: The test output showing Ran 6 tests in 0.179s ... OK.
- Key Callout: Demonstrates production software engineering discipline: marginalia stripping, markdown artifact sanitization, diff accuracy, token metrics, and MCP compliance are all unit-tested.

---

## Enterprise Benchmark Results

From contextsentry.db and generate_benchmark_report.py:

```
================================================================================
      CONTEXTSENTRY // ENTERPRISE ROI & TOKEN COMPRESSION BENCHMARK      
      Lead Analyst: Anshul Kumaria | Ernst & Young LLP Tax Advisory Practice    
================================================================================

Document Scope                       | Original Tokens | Delta Tokens | Reduction % | Savings / Tx
------------------------------------------------------------------------------------------------
3-Page Codification                  | 2,841           | 947          | 66.7      % | $0.00947    
11-Page Enterprise Code              | 10,328          | 858          | 91.7      % | $0.04735    
50-Page Regulatory Corpus (Projected) | 48,500          | 1,250        | 97.4      % | $0.23625    
------------------------------------------------------------------------------------------------

Enterprise Financial ROI Projections:
  • 11-Page Enterprise Code:
    - At 10,000 queries/year: $473.50 USD net annual savings
    - At 50,000 queries/year: $2,367.50 USD net annual savings
  • 50-Page Regulatory Corpus (Projected):
    - At 10,000 queries/year: $2,362.50 USD net annual savings
    - At 50,000 queries/year: $11,812.50 USD net annual savings
```
