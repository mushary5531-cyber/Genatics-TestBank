#!/usr/bin/env python3
"""
parse.py — converts a Markdown question file to /tmp/questions.json

Expected Markdown format per question block:
---
**Q1.** نص السؤال هنا

A) الخيار الأول
B) الخيار الثاني
C) الخيار الثالث
D) الخيار الرابع

**Answer:** B
**Explanation:** شرح الإجابة هنا
---

File naming convention (or set EXAM / LECTURE env vars):
  mid1_LectureName.md
  mid2_LectureName.md
  final_LectureName.md

Usage:
  python3 parse.py path/to/file.md [exam] [lecture_name]
  python3 parse.py questions/          ← processes all .md files in folder
  python3 parse.py                     ← processes questions/ folder
"""

import re, json, sys, pathlib, os

OUT = pathlib.Path("/tmp/questions.json")

LETTER_MAP = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4,
              "a": 0, "b": 1, "c": 2, "d": 3, "e": 4}


def parse_file(path: pathlib.Path, exam: str = "", lecture: str = "") -> list[dict]:
    text = path.read_text(encoding="utf-8")

    # Auto-detect exam from filename: mid1_*, mid2_*, final_*
    if not exam:
        stem = path.stem.lower()
        if stem.startswith("mid1"):   exam = "mid1"
        elif stem.startswith("mid2"): exam = "mid2"
        elif stem.startswith("final"):exam = "final"
        else:                         exam = "general"

    # Auto-detect lecture from filename (part after first _)
    if not lecture:
        parts = path.stem.split("_", 1)
        lecture = parts[1].replace("_", " ") if len(parts) > 1 else path.stem

    questions = []

    # Split into blocks by blank lines between questions
    # Each question starts with a bold number like **Q1.** or **1.** or just a number
    # We use a flexible regex to find question starts
    blocks = re.split(r'\n(?=\*{0,2}[Qq]?\d+[\.\)]\*{0,2})', text.strip())

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        lines = [l.rstrip() for l in block.split('\n') if l.strip()]
        if len(lines) < 6:
            continue

        # Extract question number and text (first line)
        q_line = re.sub(r'^\*{0,2}[Qq]?\d+[\.\)]\*{0,2}\s*', '', lines[0]).strip()
        if not q_line:
            # question text might be on next line
            q_line = lines[1].strip() if len(lines) > 1 else ""

        # Collect option lines
        options = []
        answer_idx = None
        explanation = ""
        image = ""

        for line in lines[1:]:
            # Option line: A) ... or A. ... or **A)** ...
            m = re.match(r'^\*{0,2}([A-Ea-e])[\)\.][\*]{0,2}\s*(.*)', line)
            if m:
                options.append(m.group(2).strip())
                continue

            # Answer line
            m = re.match(r'^\*{0,2}[Aa]nswer[:\s\*]*([A-Ea-e])\b', line)
            if m:
                answer_idx = LETTER_MAP.get(m.group(1))
                continue

            # Image line
            m = re.match(r'^\*{0,2}[Ii]mage[:\s\*]*(.*)', line)
            if m:
                image = m.group(1).strip()
                continue

            # Explanation line
            m = re.match(r'^\*{0,2}[Ee]xplanation[:\s\*]*(.*)', line)
            if m:
                explanation = m.group(1).strip()
                continue

            # Continuation of explanation
            if answer_idx is not None and explanation is not None and not re.match(r'^\*{0,2}[A-Da-d][\)\.]', line):
                if explanation:
                    explanation += " " + line.strip()

        if len(options) < 2 or answer_idx is None:
            continue

        # Pad options to at least 4 if needed (allow up to 5)
        while len(options) < 4:
            options.append("")

        q_id = f"{exam}_{path.stem}_{len(questions)+1}"
        q_obj = {
            "id": q_id,
            "exam": exam,
            "lecture": lecture,
            "q": q_line,
            "options": options[:4],
            "answer": answer_idx,
            "explanation": explanation or "",
        }
        if image:
            q_obj["image"] = image
        questions.append(q_obj)

    return questions


def main():
    args = sys.argv[1:]

    # Determine input path
    if args:
        target = pathlib.Path(args[0])
    else:
        target = pathlib.Path(__file__).parent / "questions"

    exam_override    = args[1] if len(args) > 1 else ""
    lecture_override = args[2] if len(args) > 2 else ""

    all_questions = []

    if target.is_file():
        all_questions = parse_file(target, exam_override, lecture_override)
        print(f"[parse] {target.name}: {len(all_questions)} questions")
    elif target.is_dir():
        md_files = sorted(
            f for f in target.glob("**/*.md")
            if f.name.upper() not in ("README.MD", "CHANGELOG.MD")
        )
        if not md_files:
            print(f"[parse] No .md files found in {target}")
            sys.exit(1)
        for f in md_files:
            qs = parse_file(f)
            print(f"[parse] {f.name}: {len(qs)} questions")
            all_questions.extend(qs)
    else:
        sys.exit(f"[parse] ❌  Path not found: {target}")

    OUT.write_text(json.dumps(all_questions, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[parse] ✅  Total {len(all_questions)} questions → {OUT}")


if __name__ == "__main__":
    main()
