from pathlib import Path
import re

for f in Path("backend").rglob("*.py"):
    content = f.read_text(encoding="utf-8", errors="ignore")
    for idx, line in enumerate(content.splitlines(), 1):
        if "Messages" in line or "messages.create" in line or "def create" in line:
            print(f"{f}:{idx} -> {line.strip()}")
