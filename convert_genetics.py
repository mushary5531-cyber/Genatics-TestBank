#!/usr/bin/env python3
"""
convert_genetics.py — converts genetics_answers_final.md to MCQ question files
Usage: python3 convert_genetics.py
Output: questions/mid1_*.md and questions/mid2_*.md files
"""

import re
import random
import pathlib

random.seed(42)

LETTER_TO_IDX = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
IDX_TO_LETTER = {0: 'A', 1: 'B', 2: 'C', 3: 'D'}


def parse_genetics_file(filepath):
    text = pathlib.Path(filepath).read_text(encoding='utf-8')

    markers = []

    for m in re.finditer(r'^# 🔵 الميد الأول', text, re.MULTILINE):
        markers.append((m.start(), 'exam', 'mid1'))

    for m in re.finditer(r'^# 🟢 الميد الثاني', text, re.MULTILINE):
        markers.append((m.start(), 'exam', 'mid2'))

    for m in re.finditer(r'^## 📚 (.+)', text, re.MULTILINE):
        raw = m.group(1)
        # Take English name after —, or use left part
        if ' — ' in raw:
            eng = raw.split(' — ')[1]
            # Strip Arabic in parentheses
            eng = re.sub(r'\s*\([؀-ۿ\s\+\-]+\)\s*$', '', eng).strip()
            # Take left part: strip L-number prefix if present
            lnum = re.match(r'^(L[\d\s\+\,]+)\s*', raw)
            lnum_str = lnum.group(1).replace(' ', '').replace(',', '_').replace('+', '_') if lnum else ''
            lecture_id = (lnum_str + '_' + re.sub(r'[^\w]', '_', eng)).strip('_')
        else:
            lecture_id = re.sub(r'[^\w]', '_', raw).strip('_')
        lecture_id = re.sub(r'_+', '_', lecture_id)
        markers.append((m.start(), 'lecture', lecture_id))

    for m in re.finditer(r'^### Q: .+?(?=\n### Q:|\n## |\n# |\Z)', text, re.DOTALL | re.MULTILINE):
        markers.append((m.start(), 'question', m.group(0)))

    markers.sort(key=lambda x: x[0])

    current_exam = 'mid1'
    current_lecture = 'General'
    raw_questions = []

    for _, mtype, content in markers:
        if mtype == 'exam':
            current_exam = content
        elif mtype == 'lecture':
            current_lecture = content
        elif mtype == 'question':
            q = parse_question_block(content, current_exam, current_lecture)
            if q:
                raw_questions.append(q)

    return raw_questions


def parse_question_block(block, exam, lecture):
    lines = block.strip().split('\n')

    q_match = re.match(r'^### Q: (.+)', lines[0])
    if not q_match:
        return None
    q_text = q_match.group(1).strip()

    answer_letter = None
    answer_text = None

    for line in lines[1:]:
        # Match: **الإجابة: C) Text** or **الإجابة: C) Text** (note)
        m = re.match(r'\*\*الإجابة:\s*([A-Da-d])\)\s*(.+?)(?:\*\*|$)', line)
        if m:
            answer_letter = m.group(1).upper()
            answer_text = m.group(2).strip()
            answer_text = answer_text.rstrip('*').strip()
            # Remove trailing parenthetical notes
            answer_text = re.sub(r'\s*\([^)]*\)\s*$', '', answer_text).strip()
            # Remove trailing ← notes
            answer_text = re.sub(r'\s*←.*$', '', answer_text).strip()
            break

    if not answer_letter or not answer_text or len(answer_text) < 2:
        return None

    # Extract explanation (first sentence / paragraph)
    explanation = ''
    in_exp = False
    exp_parts = []
    for line in lines[1:]:
        if re.match(r'\*\*الشرح', line):
            in_exp = True
            after = re.sub(r'\*\*الشرح[:\*\s]*', '', line).strip()
            if after:
                exp_parts.append(after)
            continue
        if in_exp:
            if line.startswith('---') or line.startswith('### ') or line.startswith('## ') or line.startswith('# '):
                break
            stripped = line.strip()
            if stripped and not stripped.startswith('!['):
                exp_parts.append(stripped)
    explanation = ' '.join(exp_parts)[:500]

    # Try to extract 4 options from bullet list in explanation
    bullet_options = try_extract_bullet_options(lines, answer_letter, answer_text)

    return {
        'exam': exam,
        'lecture': lecture,
        'q': q_text,
        'answer_letter': answer_letter,
        'answer_text': answer_text,
        'explanation': explanation,
        'bullet_options': bullet_options,
    }


def try_extract_bullet_options(lines, answer_letter, answer_text):
    """Extract 4 options from bullet list in explanation if available."""
    items = []
    in_exp = False
    bullet_started = False

    for line in lines:
        if re.match(r'\*\*الشرح', line):
            in_exp = True
            continue
        if not in_exp:
            continue

        m = re.match(r'^\s*[-•]\s*([A-Za-z][A-Za-z0-9\s\-\(\)\'\./]+?)(?:\s*[=\(].+)?$', line)
        if m:
            term = m.group(1).strip()
            # Only short terms (likely answer choices, not long sentences)
            if 2 < len(term) < 55 and len(term.split()) <= 6:
                items.append(term)
                bullet_started = True
        elif bullet_started and line.strip() and not re.match(r'^\s*[-•]', line):
            # Non-bullet after bullets started — stop
            if len(items) >= 3:
                break

    if len(items) < 4:
        return None

    ans_clean = answer_text.lower()
    found_idx = None
    for i, item in enumerate(items[:4]):
        if ans_clean in item.lower() or item.lower() in ans_clean:
            found_idx = i
            break

    if found_idx is None:
        return None

    target_pos = LETTER_TO_IDX[answer_letter]
    options = list(items[:4])
    if found_idx != target_pos:
        options[found_idx], options[target_pos] = options[target_pos], options[found_idx]

    return options


def generate_mcq_options(questions):
    """Add final 4-option MCQ choices to each question."""

    # Build distractor pools
    lecture_pool = {}
    exam_pool = {'mid1': [], 'mid2': []}
    all_answers = []

    for q in questions:
        lec = q['lecture']
        lecture_pool.setdefault(lec, [])
        lecture_pool[lec].append(q['answer_text'])
        exam_pool.setdefault(q['exam'], [])
        exam_pool[q['exam']].append(q['answer_text'])
        all_answers.append(q['answer_text'])

    all_unique = list(dict.fromkeys(all_answers))

    result = []
    for q in questions:
        if q['bullet_options']:
            result.append({**q, 'options': q['bullet_options'], 'answer_idx': LETTER_TO_IDX[q['answer_letter']]})
            continue

        ans = q['answer_text']
        target_pos = LETTER_TO_IDX[q['answer_letter']]

        # Build candidate distractors: same lecture > same exam > all
        candidates = []
        for pool in [lecture_pool.get(q['lecture'], []), exam_pool.get(q['exam'], []), all_unique]:
            for a in pool:
                if a != ans and a not in candidates:
                    candidates.append(a)
            if len(candidates) >= 9:
                break

        # Shuffle candidates (seeded for reproducibility)
        random.shuffle(candidates)
        distractors = candidates[:3]

        # Pad if still not enough
        fallbacks = ["All of the above", "None of the above", "Cannot be determined", "Both A and B"]
        for f in fallbacks:
            if len(distractors) < 3 and f not in distractors:
                distractors.append(f)

        options = [''] * 4
        options[target_pos] = ans
        for i, dist in zip([p for p in range(4) if p != target_pos], distractors):
            options[i] = dist

        result.append({**q, 'options': options, 'answer_idx': target_pos})

    return result


def write_question_files(questions, output_dir):
    output_dir = pathlib.Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # Remove old auto-generated files (keep mid1_example.md)
    for f in output_dir.glob('*.md'):
        if f.name != 'mid1_example.md':
            f.unlink()

    groups = {}
    for q in questions:
        key = (q['exam'], q['lecture'])
        groups.setdefault(key, []).append(q)

    total = 0
    for (exam, lecture), qs in sorted(groups.items()):
        # Sanitize lecture name for filename
        lec_clean = re.sub(r'[^\w\-]', '_', lecture).strip('_')
        lec_clean = re.sub(r'_+', '_', lec_clean)
        filename = f"{exam}_{lec_clean}.md"
        filepath = output_dir / filename

        lines = []
        for i, q in enumerate(qs):
            lines.append(f"**Q{i+1}.** {q['q']}")
            lines.append('')
            for j, opt in enumerate(q['options']):
                lines.append(f"{IDX_TO_LETTER[j]}) {opt}")
            lines.append('')
            lines.append(f"**Answer:** {IDX_TO_LETTER[q['answer_idx']]}")
            lines.append(f"**Explanation:** {q['explanation']}")
            lines.append('')

        filepath.write_text('\n'.join(lines), encoding='utf-8')
        print(f"  {filename}: {len(qs)} questions")
        total += len(qs)

    return total


def main():
    repo = pathlib.Path(__file__).parent
    src = repo / "genetics_answers_final.md"
    out_dir = repo / "questions"

    print(f"[convert] Parsing {src.name} ...")
    raw = parse_genetics_file(src)
    print(f"[convert] Parsed {len(raw)} questions with valid answers")

    questions = generate_mcq_options(raw)
    print(f"[convert] Generated MCQ options for {len(questions)} questions")
    print(f"[convert] Writing to {out_dir}/")

    total = write_question_files(questions, out_dir)
    print(f"\n[convert] ✅  Done — {total} questions in {out_dir}/")


if __name__ == "__main__":
    main()
