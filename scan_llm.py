from pathlib import Path
import re

code_files = list(Path("backend").rglob("*.py"))
print("=== SCANNING FOR ALL LLM CALLS AND WRAPPERS ===")
for f in code_files:
    content = f.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()
    for idx, line in enumerate(lines, 1):
        if any(term in line for term in ["messages.create", "_call_claude", "call_claude", "call_llm", "client.messages"]):
            print(f"{f}:{idx} -> {line.strip()}")
