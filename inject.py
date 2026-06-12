#!/usr/bin/env python3
"""
inject.py — reads /tmp/questions.json and injects into app.tsx
Usage: python3 inject.py
Output: /tmp/app_injected.tsx
"""
import json, pathlib, sys

SRC    = pathlib.Path(__file__).parent / "app.tsx"
JSON   = pathlib.Path("/tmp/questions.json")
OUT    = pathlib.Path("/tmp/app_injected.tsx")
MARKER = "// INJECT_MARKER"

if not JSON.exists():
    sys.exit(f"[inject] ❌  {JSON} not found — run parse.py first")

questions = json.loads(JSON.read_text(encoding="utf-8"))
print(f"[inject] loaded {len(questions)} questions from {JSON}")

src = SRC.read_text(encoding="utf-8")

if MARKER not in src:
    sys.exit(f"[inject] ❌  marker '{MARKER}' not found in app.tsx")

# Build replacement: replace empty array + marker with populated array
old_block = "const ALL_QUESTIONS: Question[] = [];\n// INJECT_MARKER"
new_block  = "const ALL_QUESTIONS: Question[] = " + json.dumps(questions, ensure_ascii=False, indent=2) + ";"

if old_block not in src:
    # Fallback: just replace the marker line
    new_block2 = f"const ALL_QUESTIONS: Question[] = {json.dumps(questions, ensure_ascii=False)};"
    src = src.replace(
        "const ALL_QUESTIONS: Question[] = [];",
        new_block2
    ).replace(MARKER, "")
else:
    src = src.replace(old_block, new_block)

OUT.write_text(src, encoding="utf-8")
print(f"[inject] ✅  wrote {OUT}")
