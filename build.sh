#!/usr/bin/env bash
# Full build pipeline — run from repo root
# Requires: node/npm, python3
# Usage: bash build.sh [questions_path]

set -e
REPO="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO"

echo "── Step 1: parse questions ──"
python3 parse.py "${1:-}"

echo "── Step 2: inject JSON into app.tsx ──"
python3 inject.py

echo "── Step 3: copy injected app ──"
cp /tmp/app_injected.tsx "$REPO/app_injected.tsx"

# Write build entry that imports the injected app from local path
cat > "$REPO/entry_build.tsx" << 'EOF'
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./app_injected";
const root = createRoot(document.getElementById("root")!);
root.render(<App />);
EOF

echo "── Step 4: esbuild bundle ──"
npx esbuild entry_build.tsx \
  --bundle \
  --loader:.tsx=tsx \
  --jsx=automatic \
  --minify \
  --outfile=/tmp/bundle.js

echo "── Step 5: wrap into index.html ──"
python3 wrap.py

# Cleanup temp files
rm -f app_injected.tsx entry_build.tsx

echo ""
echo "✅  Build complete → index.html  ($(du -sh index.html | cut -f1))"
