import os
import re
from pathlib import Path

code_files = list(Path("backend").rglob("*.py")) + list(Path("frontend/src").rglob("*.jsx")) + list(Path("frontend/src").rglob("*.js"))

audit_items = []

for f in code_files:
    content = f.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()
    for idx, line in enumerate(lines, 1):
        line_str = line.strip()
        # 1. Filename checks
        if any(term in line_str for term in ["fname in", "in fname", ".name.lower()", "filename.lower()", "image_path.lower()"]):
            audit_items.append((f, idx, "Filename check / string matching on path", line_str))
        # 2. Hardcoded keyword checks in query / router
        if any(term in line_str for term in ['"receipt" in', '"note" in', '"business card" in', '"form" in', '"patient" in', '"meeting" in', '"spent" in', '"expense" in']):
            audit_items.append((f, idx, "Keyword heuristic matching on user question", line_str))
        # 3. Static keyword dictionaries (MATH_KEYWORDS, VISUAL_KEYWORDS)
        if "MATH_KEYWORDS" in line_str or "VISUAL_KEYWORDS" in line_str:
            audit_items.append((f, idx, "Static keyword dictionary / rule-based intent parsing", line_str))
        # 4. Fallback placeholder strings
        if any(term in line_str for term in ["Analyzed document", "relevant details matching your inquiry", "Scanned content of", "No salient document fields detected"]):
            audit_items.append((f, idx, "Hardcoded fallback / placeholder template string", line_str))
        # 5. Mock methods and simulated outputs
        if "_mock_classify" in line_str or "_mock_extract" in line_str:
            audit_items.append((f, idx, "Mock / simulated classification or extraction branch", line_str))
        # 6. Specific document type hardcoding in field checks
        if any(term in line_str for term in ['doc.document_type == "receipt"', 'doc.document_type == "handwritten_note"', 'doc.document_type == "business_card"']):
            audit_items.append((f, idx, "Specific document_type branching", line_str))

print(f"Total audit findings: {len(audit_items)}")
for f, idx, category, text in audit_items:
    print(f"{f}:{idx} [{category}]\n   -> {text}\n")
