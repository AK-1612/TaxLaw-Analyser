"""
MCP Server & REST Interface (server.py)
Standard interface for AI agents and consultants to invoke the deterministic diffing pipeline.
Supports both Model Context Protocol (MCP) stdio tool invocation ('compare_regulatory_documents')
and FastAPI REST API endpoints, maintaining the opt-in, decoupled ContextSentry architecture.
"""
import sys
import os
import time
import json
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from pdf_parser import extract_document_data
from diff_engine import extract_semantic_delta
from worker import refine_delta_with_ollama, synthesize_client_impact
from telemetry import log_run, get_telemetry_history, format_benchmark_card

# ==============================================================================
# Pipeline Execution Engine
# ==============================================================================
def execute_pipeline(
    pdf_path_a: str,
    pdf_path_b: str,
    client_name: str = "Fortune 500 Enterprise Client",
    author: str = "Anshul Kumaria",
    strip_marginalia: bool = True
) -> Dict[str, Any]:
    """
    Executes the 4-step Tax Law Delta Analyzer workflow:
    1. Document Ingestion & Marginalia Stripping
    2. Local Deterministic Diffing
    3. Offloaded Context Refinement (Ollama/Llama 3.2 or deterministic fallback)
    4. Primary LLM Synthesis & Telemetry Logging
    """
    if not os.path.exists(pdf_path_a):
        raise FileNotFoundError(f"Document A not found: {pdf_path_a}")
    if not os.path.exists(pdf_path_b):
        raise FileNotFoundError(f"Document B not found: {pdf_path_b}")

    start_time = time.perf_counter()

    # Step 1: Ingestion & Marginalia Stripping
    doc_a_data = extract_document_data(pdf_path_a, strip_marginalia=strip_marginalia)
    doc_b_data = extract_document_data(pdf_path_b, strip_marginalia=strip_marginalia)

    # Step 2: Local Deterministic Diffing
    diff_results = extract_semantic_delta(doc_a_data["clean_text"], doc_b_data["clean_text"])
    raw_delta = diff_results["compact_delta_text"]
    structured_changes = diff_results["structured_changes"]

    if not raw_delta.strip() and not structured_changes:
        end_time = time.perf_counter()
        telemetry = log_run(
            pdf_path_a, pdf_path_b,
            doc_a_data["clean_text"], doc_b_data["clean_text"],
            "", "", (end_time - start_time) * 1000.0
        )
        return {
            "status": "success",
            "message": "No regulatory changes detected between the provided documents.",
            "client_impact_summary": "No regulatory amendments identified.",
            "refined_delta_json": {"changes": []},
            "diff_stats": diff_results["stats"],
            "telemetry": telemetry
        }

    # Step 3: Offloaded Context Refinement (Ollama/Llama 3.2)
    refined_delta = refine_delta_with_ollama(raw_delta, structured_changes=structured_changes)

    # Step 4: Primary LLM Synthesis
    client_impact_summary = synthesize_client_impact(refined_delta, client_name=client_name, lead_author=author)

    end_time = time.perf_counter()
    latency_ms = (end_time - start_time) * 1000.0

    # Log to contextsentry.db
    refined_str = json.dumps(refined_delta)
    telemetry = log_run(
        pdf_path_a, pdf_path_b,
        doc_a_data["clean_text"], doc_b_data["clean_text"],
        raw_delta, refined_str, latency_ms
    )

    return {
        "status": "success",
        "client_name": client_name,
        "client_impact_summary": client_impact_summary,
        "refined_delta_json": refined_delta,
        "raw_delta": raw_delta,
        "diff_stats": diff_results["stats"],
        "telemetry": telemetry,
        "ingestion_metadata": {
            "doc_a": {
                "pages": doc_a_data["pages_count"],
                "marginalia_lines_filtered": doc_a_data["marginalia_lines_filtered"]
            },
            "doc_b": {
                "pages": doc_b_data["pages_count"],
                "marginalia_lines_filtered": doc_b_data["marginalia_lines_filtered"]
            }
        }
    }

# ==============================================================================
# FastAPI REST Server
# ==============================================================================
app = FastAPI(
    title="EY Tax Law Delta Analyzer",
    description="Deterministic state diffing sidecar with local Ollama refinement and token optimization telemetry.",
    version="1.0.0"
)

class CompareRequest(BaseModel):
    pdf_path_a: str = Field(..., description="Absolute or relative path to baseline tax document (Year A)")
    pdf_path_b: str = Field(..., description="Absolute or relative path to updated tax document (Year B)")
    client_name: Optional[str] = Field("EY Corporate Tax Client", description="Name of corporate client for summary targeting")
    strip_marginalia: Optional[bool] = Field(True, description="Whether to strip running headers/footers and page numbers")

@app.post("/compare")
def compare_documents(request: CompareRequest):
    try:
        result = execute_pipeline(
            pdf_path_a=request.pdf_path_a,
            pdf_path_b=request.pdf_path_b,
            client_name=request.client_name or "EY Corporate Tax Client",
            strip_marginalia=request.strip_marginalia if request.strip_marginalia is not None else True
        )
        return result
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

@app.get("/telemetry")
def get_telemetry(limit: int = 10):
    """Returns recent benchmarking runs and token reduction records from contextsentry.db."""
    return {
        "status": "success",
        "runs": get_telemetry_history(limit=limit)
    }

@app.get("/health")
def health_check():
    return {"status": "online", "service": "TaxLaw-DeltaAnalyzer"}

# ==============================================================================
# Model Context Protocol (MCP) Stdio Interface
# ==============================================================================
def run_mcp_server():
    """
    Runs a Model Context Protocol (MCP) standard stdio JSON-RPC server.
    Exposes tool: compare_regulatory_documents
    """
    tools_definition = [
        {
            "name": "compare_regulatory_documents",
            "description": "Deterministic tax regulation diffing tool. Ingests Year A and Year B PDFs, isolates statutory clause deltas locally, and produces a token-optimized Client Impact Summary.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "pdf_path_a": {
                        "type": "string",
                        "description": "Path to baseline regulatory PDF (e.g. FY25_Tax_Code.pdf)"
                    },
                    "pdf_path_b": {
                        "type": "string",
                        "description": "Path to updated regulatory PDF (e.g. FY26_Tax_Code.pdf)"
                    },
                    "client_name": {
                        "type": "string",
                        "description": "Optional corporate client name for tailored impact analysis"
                    }
                },
                "required": ["pdf_path_a", "pdf_path_b"]
            }
        }
    ]

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            req_id = req.get("id")
            method = req.get("method")

            if method == "initialize":
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {
                            "name": "tax-law-delta-analyzer",
                            "version": "1.0.0"
                        }
                    }
                }
            elif method == "tools/list":
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"tools": tools_definition}
                }
            elif method == "tools/call":
                params = req.get("params", {})
                tool_name = params.get("name")
                args = params.get("arguments", {})

                if tool_name == "compare_regulatory_documents":
                    pipeline_res = execute_pipeline(
                        pdf_path_a=args["pdf_path_a"],
                        pdf_path_b=args["pdf_path_b"],
                        client_name=args.get("client_name", "EY Corporate Tax Client")
                    )
                    content_text = (
                        f"{pipeline_res['client_impact_summary']}\n\n"
                        f"{format_benchmark_card(pipeline_res['telemetry'])}"
                    )
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [
                                {"type": "text", "text": content_text}
                            ],
                            "isError": False
                        }
                    }
                else:
                    res = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32601, "message": f"Tool '{tool_name}' not found."}
                    }
            else:
                res = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {}
                }

            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()

        except Exception as ex:
            err_res = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32000, "message": str(ex)}
            }
            sys.stdout.write(json.dumps(err_res) + "\n")
            sys.stdout.flush()

# ==============================================================================
# Entry Point CLI
# ==============================================================================
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tax Law Delta Analyzer Server")
    parser.add_argument("--mcp", action="store_true", help="Run as Model Context Protocol (MCP) stdio server")
    parser.add_argument("--host", default="127.0.0.1", help="REST server host")
    parser.add_argument("--port", type=int, default=8000, help="REST server port")
    parser.add_argument("--compare", nargs=2, metavar=("DOC_A", "DOC_B"), help="Run immediate comparison on two PDFs")
    args = parser.parse_args()

    if args.mcp:
        run_mcp_server()
    elif args.compare:
        doc_a, doc_b = args.compare
        res = execute_pipeline(doc_a, doc_b)
        print("\n" + res["client_impact_summary"])
        print("\n" + format_benchmark_card(res["telemetry"]))
    else:
        import uvicorn
        print(f"Starting Tax Law Delta Analyzer REST API on http://{args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)
