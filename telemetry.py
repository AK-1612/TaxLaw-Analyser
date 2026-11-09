"""
Telemetry Logger (contextsentry.db)
Tracks exact token sizes of Document A + Document B versus the offloaded delta,
calculating token compression percentages and enterprise cost savings for executive benchmarking.
"""
import sqlite3
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contextsentry.db")

# Commercial Enterprise LLM baseline pricing (per 1,000,000 tokens)
# e.g., GPT-4o / Claude 3.5 Sonnet / Gemini 1.5 Pro blend: ~$5.00 per 1M input tokens
COMMERCIAL_LLM_INPUT_RATE_PER_1M = 5.00

def init_db(db_path: str = DB_PATH) -> None:
    """Initializes the telemetry SQLite database schema."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT UNIQUE NOT NULL,
                timestamp TEXT NOT NULL,
                doc_a_name TEXT NOT NULL,
                doc_b_name TEXT NOT NULL,
                doc_a_tokens INTEGER NOT NULL,
                doc_b_tokens INTEGER NOT NULL,
                total_input_tokens INTEGER NOT NULL,
                raw_delta_tokens INTEGER NOT NULL,
                refined_delta_tokens INTEGER NOT NULL,
                tokens_saved INTEGER NOT NULL,
                token_reduction_pct REAL NOT NULL,
                cost_original_usd REAL NOT NULL,
                cost_optimized_usd REAL NOT NULL,
                cost_savings_usd REAL NOT NULL,
                latency_ms REAL NOT NULL
            );
        """)
        conn.commit()

def estimate_tokens(text: str) -> int:
    """
    Standard LLM token estimation heuristic:
    1 token ~ 4 characters in English, or ~0.75 words.
    Takes max of char/4 and words*1.3 for conservative accuracy.
    """
    if not text:
        return 0
    words = len(text.split())
    chars = len(text)
    return max(int(chars / 3.8), int(words * 1.35))

def log_run(
    doc_a_name: str,
    doc_b_name: str,
    text_a: str,
    text_b: str,
    raw_delta: str,
    refined_delta: str,
    latency_ms: float,
    db_path: str = DB_PATH
) -> Dict[str, Any]:
    """Logs a diffing run to contextsentry.db and calculates financial ROI metrics."""
    init_db(db_path)

    run_id = f"RUN-{uuid.uuid4().hex[:8].upper()}"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    tokens_a = estimate_tokens(text_a)
    tokens_b = estimate_tokens(text_b)
    total_input = tokens_a + tokens_b
    raw_delta_tokens = estimate_tokens(raw_delta)
    refined_tokens = estimate_tokens(refined_delta)

    # Tokens saved = original combined size vs. final payload sent to primary LLM
    final_payload_tokens = refined_tokens if refined_tokens > 0 else raw_delta_tokens
    tokens_saved = max(0, total_input - final_payload_tokens)
    reduction_pct = (tokens_saved / total_input * 100.0) if total_input > 0 else 0.0

    cost_original = (total_input / 1_000_000.0) * COMMERCIAL_LLM_INPUT_RATE_PER_1M
    cost_optimized = (final_payload_tokens / 1_000_000.0) * COMMERCIAL_LLM_INPUT_RATE_PER_1M
    cost_savings = cost_original - cost_optimized

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO telemetry_logs (
                run_id, timestamp, doc_a_name, doc_b_name,
                doc_a_tokens, doc_b_tokens, total_input_tokens,
                raw_delta_tokens, refined_delta_tokens,
                tokens_saved, token_reduction_pct,
                cost_original_usd, cost_optimized_usd, cost_savings_usd,
                latency_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id, timestamp, os.path.basename(doc_a_name), os.path.basename(doc_b_name),
            tokens_a, tokens_b, total_input,
            raw_delta_tokens, refined_tokens,
            tokens_saved, round(reduction_pct, 2),
            round(cost_original, 6), round(cost_optimized, 6), round(cost_savings, 6),
            round(latency_ms, 2)
        ))
        conn.commit()

    return {
        "run_id": run_id,
        "timestamp": timestamp,
        "doc_a_tokens": tokens_a,
        "doc_b_tokens": tokens_b,
        "total_input_tokens": total_input,
        "raw_delta_tokens": raw_delta_tokens,
        "refined_delta_tokens": refined_tokens,
        "tokens_saved": tokens_saved,
        "token_reduction_pct": round(reduction_pct, 2),
        "cost_original_usd": round(cost_original, 6),
        "cost_optimized_usd": round(cost_optimized, 6),
        "cost_savings_usd": round(cost_savings, 6),
        "latency_ms": round(latency_ms, 2)
    }

def get_telemetry_history(limit: int = 10, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """Retrieves recent telemetry runs from contextsentry.db."""
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM telemetry_logs ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(row) for row in cursor.fetchall()]

def format_benchmark_card(entry: Dict[str, Any]) -> str:
    """Formats an executive terminal banner detailing token compression and ROI."""
    card = f"""
+===========================================================================+
|           CONTEXTSENTRY TELEMETRY & TOKEN OPTIMIZATION BENCHMARK           |
+===========================================================================+
  Run ID:                {entry['run_id']}
  Timestamp:             {entry.get('timestamp', 'N/A')}
  Documents:             {entry.get('doc_a_name', 'Doc A')} vs. {entry.get('doc_b_name', 'Doc B')}
-----------------------------------------------------------------------------
  Combined Input Tokens: {entry['total_input_tokens']:,} tokens (Doc A: {entry['doc_a_tokens']:,} + Doc B: {entry['doc_b_tokens']:,})
  Offloaded Delta Size:  {entry['refined_delta_tokens']:,} tokens (Raw diff: {entry['raw_delta_tokens']:,} tokens)
  Net Tokens Saved:      {entry['tokens_saved']:,} tokens
  TOKEN REDUCTION:       {entry['token_reduction_pct']:.1f}% SAVINGS
-----------------------------------------------------------------------------
  Baseline Cloud Cost:   ${entry['cost_original_usd']:.5f} USD
  Optimized Delta Cost:  ${entry['cost_optimized_usd']:.5f} USD
  Estimated Savings/Tx:  ${entry['cost_savings_usd']:.5f} USD
  Engine Pipeline Time:  {entry['latency_ms']:.1f} ms
+===========================================================================+
"""
    return card.strip()

