#!/usr/bin/env python3
"""
clean_watermarks.py — strips watermark suffixes from all question .md files
"""
import re
import pathlib

WATERMARK_PATTERNS = [
    r'\s+Med25\s+Med\s+25\b.*',
    r'\s+MED25\s+Med\s+25\b.*',
    r'\s+MCQ\s+Med\s+25\b.*',
    r'\s+Questions\s+Med\s+25\b.*',
    r'\s+Genetics\s+Final\s+Season.*',
    r'\s+\d[\d\s]*[A-D][A-D\s]*MCQ\s+Med\s+25\b.*',
    r'\s+\d[\d\s]*[A-D][A-D\s]*$',  # trailing answer keys like "1 2 3 4 A B C D"
]

COMBINED = re.compile('(' + '|'.join(WATERMARK_PATTERNS) + ')', re.IGNORECASE)

questions_dir = pathlib.Path(__file__).parent / "questions"

total_fixed = 0
for md_file in sorted(questions_dir.glob("*.md")):
    if md_file.name == "mid1_example.md":
        continue

    lines = md_file.read_text(encoding="utf-8").splitlines()
    new_lines = []
    changes = 0

    for line in lines:
        # Only clean lines that are option lines (A) B) C) D)) or could have watermarks
        # Be conservative: only clean if it's an option line
        cleaned = COMBINED.sub('', line).rstrip()
        if cleaned != line.rstrip():
            changes += 1
            new_lines.append(cleaned)
        else:
            new_lines.append(line)

    if changes:
        md_file.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')
        print(f"  {md_file.name}: cleaned {changes} line(s)")
        total_fixed += changes

print(f"\nTotal lines cleaned: {total_fixed}")
