#!/usr/bin/env python3
"""
wrap.py — wraps /tmp/bundle.js + styles.css into a self-contained index.html
Usage: python3 wrap.py
Output: index.html (in repo root)
"""
import pathlib, sys

BUNDLE = pathlib.Path("/tmp/bundle.js")
CSS    = pathlib.Path(__file__).parent / "styles.css"
OUT    = pathlib.Path(__file__).parent / "index.html"

if not BUNDLE.exists():
    sys.exit("[wrap] ❌  /tmp/bundle.js not found — run esbuild first")

bundle_js  = BUNDLE.read_text(encoding="utf-8")
styles_css = CSS.read_text(encoding="utf-8") if CSS.exists() else ""

# Strip Google Fonts import from CSS (offline mode) — keep if online desired
# styles_css = styles_css.replace("@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');", "")

html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Genetics TestBank</title>
  <style>
{styles_css}
  </style>
</head>
<body>
  <div id="root"></div>
  <script>
{bundle_js}
  </script>
</body>
</html>
"""

OUT.write_text(html, encoding="utf-8")
size_kb = OUT.stat().st_size // 1024
print(f"[wrap] ✅  wrote {OUT}  ({size_kb} KB)")
