"""
Document Parser Module
Accurately extracts text blocks and statutory headers from EY-standard tax PDFs
while stripping marginalia, running headers, footers, and page numbers to prevent
false-positive diffs.
"""
import re
from typing import Dict, Any, List
import pdfplumber

# Patterns for headers, footers, page counts, and circular disclaimers
MARGINALIA_PATTERNS = [
    r"^\s*page\s+\d+(\s+of\s+\d+)?.*$",
    r"^.*confidential.*ey\s+tax\s+advisory.*$",
    r"^.*regulatory\s+codification\s+archive.*$",
    r"^.*private\s+briefing.*circular\s+230.*$",
    r"^.*all\s+rights\s+reserved.*$",
    r"^\s*title\s+26\s*-\s*internal\s+revenue\s+statutes\s*\(revised\s+fy\d{4}\)\s*$",
    r"^\s*end\s+of\s+codified\s+statutes\s*-\s*fy\d{4}\s*$"
]

COMPILED_MARGINALIA = [re.compile(p, re.IGNORECASE) for p in MARGINALIA_PATTERNS]

def is_marginalia_line(line: str) -> bool:
    """Checks if a given line matches known running headers/footers/marginalia."""
    cleaned = line.strip()
    if not cleaned:
        return False
    for pat in COMPILED_MARGINALIA:
        if pat.match(cleaned):
            return True
    return False

def extract_document_data(pdf_path: str, strip_marginalia: bool = True) -> Dict[str, Any]:
    """
    Extracts text from a PDF with layout-aware filtering of headers/footers and marginalia.
    Returns:
        dict containing:
            - 'clean_text': Normalized text with marginalia stripped
            - 'raw_text': Raw unfiltered text
            - 'pages_count': Number of pages
            - 'marginalia_lines_filtered': Count of dropped marginalia lines
            - 'raw_char_count': Total characters in raw extraction
            - 'clean_char_count': Total characters in cleaned extraction
    """
    raw_pages: List[str] = []
    clean_pages: List[str] = []
    total_marginalia_filtered = 0

    with pdfplumber.open(pdf_path) as pdf:
        pages_count = len(pdf.pages)
        for page in pdf.pages:
            page_raw = page.extract_text() or ""
            raw_pages.append(page_raw)

            filtered_lines: List[str] = []
            for line in page_raw.splitlines():
                if strip_marginalia and is_marginalia_line(line):
                    total_marginalia_filtered += 1
                    continue
                norm_line = line.rstrip()
                if norm_line:
                    filtered_lines.append(norm_line)

            clean_page_text = "\n".join(filtered_lines)
            if clean_page_text:
                clean_pages.append(clean_page_text)

    raw_text = "\n\n".join(raw_pages)
    clean_text = "\n\n".join(clean_pages)
    # Normalize multiple newlines
    clean_text = re.sub(r"\n{3,}", "\n\n", clean_text).strip()

    return {
        "clean_text": clean_text,
        "raw_text": raw_text,
        "pages_count": pages_count,
        "marginalia_lines_filtered": total_marginalia_filtered,
        "raw_char_count": len(raw_text),
        "clean_char_count": len(clean_text)
    }

def extract_text(pdf_path: str, strip_marginalia: bool = True) -> str:
    """Convenience backward-compatible function returning just clean text."""
    data = extract_document_data(pdf_path, strip_marginalia=strip_marginalia)
    return data["clean_text"]
