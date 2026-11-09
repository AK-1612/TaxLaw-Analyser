"""
Deterministic Diffing Engine
Executes line-by-line and section-level semantic comparisons between Document A
and Document B to isolate exact text blocks that were added, removed, or modified.
"""
import difflib
import re
from typing import Dict, List, Any, Tuple

# Regex to detect statutory sections, articles, or statutory parts
SECTION_HEADER_PATTERN = re.compile(
    r"^(SECTION\s+[\w\(\)\.\-]+[^\n]*|PART\s+[IVXLCDM]+[^\n]*|ARTICLE\s+[IVXLCDM]+[^\n]*)",
    re.IGNORECASE | re.MULTILINE
)

def split_into_sections(text: str) -> Dict[str, str]:
    """
    Parses a regulatory document into a dictionary of {section_title: section_body}.
    Sections without explicit statutory headers are grouped under 'PREAMBLE' or paragraph chunks.
    """
    matches = list(SECTION_HEADER_PATTERN.finditer(text))
    if not matches:
        # Fallback to paragraph-level blocks if no formal statutory headers found
        blocks = text.split("\n\n")
        return {f"Clause {i+1}": b.strip() for i, b in enumerate(blocks) if b.strip()}

    sections: Dict[str, str] = {}
    
    # Text before the first section
    if matches[0].start() > 0:
        preamble = text[:matches[0].start()].strip()
        if preamble:
            sections["PREAMBLE"] = preamble

    for i, match in enumerate(matches):
        section_title = match.group(0).strip()
        start_idx = match.end()
        end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_body = text[start_idx:end_idx].strip()
        sections[section_title] = section_body

    return sections

def normalize_clause_text(text: str) -> str:
    """Normalizes whitespace and standardizes indentation for stable diffing."""
    lines = [re.sub(r"\s+", " ", l.strip()) for l in text.splitlines()]
    return "\n".join([l for l in lines if l])

def compute_section_diff(before: str, after: str) -> Tuple[List[str], int, int]:
    """Calculates unified diff lines between two text blocks along with addition/deletion counts."""
    lines_a = [l.strip() for l in before.splitlines() if l.strip()]
    lines_b = [l.strip() for l in after.splitlines() if l.strip()]
    
    diff = list(difflib.unified_diff(lines_a, lines_b, fromfile='Doc_A', tofile='Doc_B', lineterm='', n=1))
    
    add_count = sum(1 for line in diff if line.startswith('+') and not line.startswith('+++'))
    del_count = sum(1 for line in diff if line.startswith('-') and not line.startswith('---'))
    return diff, add_count, del_count

def extract_semantic_delta(text_a: str, text_b: str) -> Dict[str, Any]:
    """
    Performs deterministic state diffing between Document A and Document B.
    Isolates modified, added, and removed regulatory blocks.
    
    Returns:
        {
            "structured_changes": [ ... ],
            "raw_unified_diff": str,
            "compact_delta_text": str,
            "stats": { ... }
        }
    """
    sections_a = split_into_sections(text_a)
    sections_b = split_into_sections(text_b)

    all_keys = list(dict.fromkeys(list(sections_a.keys()) + list(sections_b.keys())))

    structured_changes: List[Dict[str, Any]] = []
    compact_delta_lines: List[str] = []
    
    total_added_lines = 0
    total_deleted_lines = 0
    modified_count = 0
    added_count = 0
    removed_count = 0
    unchanged_count = 0

    for key in all_keys:
        in_a = key in sections_a
        in_b = key in sections_b

        if in_a and not in_b:
            # REMOVED SECTION
            removed_count += 1
            body_a = sections_a[key]
            lines_a = body_a.splitlines()
            total_deleted_lines += len(lines_a)
            
            structured_changes.append({
                "section": key,
                "change_type": "REMOVED",
                "text_prior": body_a,
                "text_updated": "",
                "diff_lines": [f"- {l}" for l in lines_a]
            })
            compact_delta_lines.append(f"--- [REMOVED] {key} ---")
            for l in lines_a:
                compact_delta_lines.append(f"- {l}")
            compact_delta_lines.append("")

        elif not in_a and in_b:
            # ADDED SECTION
            added_count += 1
            body_b = sections_b[key]
            lines_b = body_b.splitlines()
            total_added_lines += len(lines_b)

            structured_changes.append({
                "section": key,
                "change_type": "ADDED",
                "text_prior": "",
                "text_updated": body_b,
                "diff_lines": [f"+ {l}" for l in lines_b]
            })
            compact_delta_lines.append(f"+++ [ADDED] {key} +++")
            for l in lines_b:
                compact_delta_lines.append(f"+ {l}")
            compact_delta_lines.append("")

        else:
            # Section in both A and B
            body_a = sections_a[key]
            body_b = sections_b[key]
            
            norm_a = normalize_clause_text(body_a)
            norm_b = normalize_clause_text(body_b)

            if norm_a == norm_b:
                unchanged_count += 1
            else:
                # MODIFIED SECTION
                modified_count += 1
                diff_lines, adds, dels = compute_section_diff(norm_a, norm_b)
                total_added_lines += adds
                total_deleted_lines += dels

                structured_changes.append({
                    "section": key,
                    "change_type": "MODIFIED",
                    "text_prior": body_a,
                    "text_updated": body_b,
                    "diff_lines": diff_lines
                })
                compact_delta_lines.append(f"=== [MODIFIED] {key} ===")
                for dl in diff_lines:
                    if dl.startswith('+') and not dl.startswith('+++'):
                        compact_delta_lines.append(dl)
                    elif dl.startswith('-') and not dl.startswith('---'):
                        compact_delta_lines.append(dl)
                compact_delta_lines.append("")

    # Full line-by-line unified diff across entire documents
    full_lines_a = text_a.splitlines()
    full_lines_b = text_b.splitlines()
    unified_full = list(difflib.unified_diff(
        full_lines_a, full_lines_b,
        fromfile="Year_A_Regulatory_Doc",
        tofile="Year_B_Regulatory_Doc",
        lineterm=""
    ))
    raw_unified_diff = "\n".join(unified_full)
    compact_delta_text = "\n".join(compact_delta_lines).strip()

    stats = {
        "sections_doc_a": len(sections_a),
        "sections_doc_b": len(sections_b),
        "modified_sections": modified_count,
        "added_sections": added_count,
        "removed_sections": removed_count,
        "unchanged_sections": unchanged_count,
        "total_changed_sections": modified_count + added_count + removed_count,
        "added_lines": total_added_lines,
        "deleted_lines": total_deleted_lines
    }

    return {
        "structured_changes": structured_changes,
        "raw_unified_diff": raw_unified_diff,
        "compact_delta_text": compact_delta_text,
        "stats": stats
    }

def get_delta(text_a: str, text_b: str) -> str:
    """Backward-compatible helper returning compact delta text."""
    delta_result = extract_semantic_delta(text_a, text_b)
    return delta_result["compact_delta_text"] or delta_result["raw_unified_diff"]
