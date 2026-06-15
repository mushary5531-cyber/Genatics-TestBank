#!/usr/bin/env python3
"""Extract MCQ questions from genetics test bank PDF - comprehensive version."""
import fitz, re, json, pathlib, os

TESTBANK = pathlib.Path("/home/user/Genatics-TestBank/نسخة من Genetics (1)_compressed.pdf")
OUT = pathlib.Path("/tmp/testbank_questions.json")
IMG_DIR = pathlib.Path("/home/user/Genatics-TestBank/images")
IMG_DIR.mkdir(exist_ok=True)

LETTER = {"A":0,"B":1,"C":2,"D":3,"E":4,"a":0,"b":1,"c":2,"d":3,"e":4}

def clean(t):
    """Remove Arabic watermark lines."""
    lines = t.split("\n")
    clean_lines = []
    for l in lines:
        # Skip Arabic-heavy lines (watermark)
        arabic = sum(1 for c in l if '؀' <= c <= 'ۿ')
        if arabic > 5 and len(l.strip()) < 120:
            continue
        clean_lines.append(l)
    return "\n".join(clean_lines)

def parse_answer_key_from_lines(lines, max_lines=None):
    """
    Extract answer key mapping from lines.
    Handles both top-of-page and bottom-of-page keys.
    Pattern: standalone digit lines followed by standalone letter lines.
    """
    if max_lines:
        lines = lines[:max_lines]

    key = {}
    nums_found = []
    lets_found = []

    for line in lines:
        stripped = line.strip()
        if re.match(r'^\d+$', stripped):
            nums_found.append(int(stripped))
        elif re.match(r'^[A-Ea-e]$', stripped):
            lets_found.append(stripped.upper())
        elif stripped and nums_found and lets_found:
            # Non-key content found after we've started collecting - try to finalize
            if len(nums_found) == len(lets_found) and len(nums_found) >= 1:
                break
            # Reset if we got confused
            if len(nums_found) > 0 and len(lets_found) == 0:
                pass  # still collecting nums
            elif len(lets_found) > 0 and len(nums_found) > len(lets_found):
                break  # done collecting

    # Match nums to letters
    if nums_found and lets_found:
        # If counts differ, try to match what we can
        pairs = min(len(nums_found), len(lets_found))
        for n, l in zip(nums_found[:pairs], lets_found[:pairs]):
            key[n] = l

    return key

def parse_answer_key(text):
    """Extract answer key from top OR bottom of page text."""
    lines = [l for l in text.split("\n")]
    stripped_lines = [l.strip() for l in lines]

    # Try top first (first 25 lines)
    key = parse_answer_key_from_lines(stripped_lines[:25])

    # If not found at top, try bottom (last 25 lines)
    if not key:
        key = parse_answer_key_from_lines(stripped_lines[-25:])

    return key

def extract_questions(text, page_num, exam, answer_key, doc_page):
    """Extract questions from page text."""
    questions = []

    # Find all question starts:
    # - "1. " or "1) " or "1. Text" (period or paren, optional space)
    # - "1- " (hyphen style for MED18 etc.)
    # Supports optional leading whitespace
    q_pattern = re.compile(r'^\s*(\d+)[.\)-]\s*(.)', re.MULTILINE)
    q_starts = list(q_pattern.finditer(text))

    # Filter: q_num should be reasonable (1-100)
    q_starts = [m for m in q_starts if 1 <= int(m.group(1)) <= 100]

    for i, m in enumerate(q_starts):
        q_num = int(m.group(1))

        # Get text block for this question
        start = m.start()
        end = q_starts[i+1].start() if i+1 < len(q_starts) else len(text)
        block = text[start:end].strip()

        # Extract question text (before first option A. A) a. a))
        # Options: "A)" "A." "A-" "a)" "a." preceded by newline
        opt_match = re.search(r'\n\s*[A-Ea-e][.\)-]\s', block)
        if not opt_match:
            # Also try options starting with whitespace on own line
            opt_match = re.search(r'\n\s{1,4}[A-Ea-e][.\)]\s', block)
        if not opt_match:
            continue  # No options found, skip

        q_text = block[:opt_match.start()].strip()
        # Remove leading question number/punctuation
        q_text = re.sub(r'^\s*\d+[.\)-]\s*', '', q_text).strip()

        # Skip if question text is too short
        if len(q_text) < 15:
            continue

        # Extract options
        opts_text = block[opt_match.start():]
        opts = re.findall(r'[A-Ea-e][.\)-]\s*(.+?)(?=\n\s*[A-Ea-e][.\)-]\s|\Z)', opts_text, re.DOTALL)
        opts = [o.strip().replace('\n', ' ').strip() for o in opts]
        # Clean up double spaces
        opts = [re.sub(r'\s+', ' ', o) for o in opts]

        if len(opts) < 2:
            continue  # Need at least 2 options

        # Keep first 4 (skip E option for 5-option questions, take first 4)
        opts = opts[:4]
        while len(opts) < 4:
            opts.append("")

        # Get answer from key
        answer_letter = answer_key.get(q_num)
        if not answer_letter:
            # Try local 1-based index
            local_num = q_starts.index(m) + 1
            answer_letter = answer_key.get(local_num)

        if not answer_letter:
            continue  # No answer found

        answer_idx = LETTER.get(answer_letter, 0)
        # Clamp to valid range for 4 options
        answer_idx = min(answer_idx, 3)

        # Check if question requires an image
        img_keywords = ['karyogram', 'pedigree', 'figure', 'below', 'chart', 'image',
                       'following karyotype', 'following pedigree', 'shown', 'picture',
                       'identify the syndrome', 'interpret', 'following result',
                       'following diagram', 'following photo']
        needs_image = any(kw in q_text.lower() for kw in img_keywords)

        img_path = None
        if needs_image:
            img_filename = f"tb_p{page_num:02d}_q{q_num}.png"
            img_filepath = IMG_DIR / img_filename
            if not img_filepath.exists():
                mat = fitz.Matrix(2, 2)
                pix = doc_page.get_pixmap(matrix=mat)
                pix.save(str(img_filepath))
            img_path = f"images/{img_filename}"

        questions.append({
            "page": page_num,
            "q_num": q_num,
            "exam": exam,
            "q": q_text,
            "options": opts,
            "answer": answer_idx,
            "answer_letter": answer_letter,
            "image": img_path,
            "lecture": None
        })

    return questions

doc = fitz.open(str(TESTBANK))
print(f"Total pages: {len(doc)}")

all_questions = []
current_exam = "mid1"

for page_num in range(len(doc)):
    page = doc[page_num]
    raw_text = page.get_text()

    # Detect exam section headers
    text_lower = raw_text.lower()
    if "second mid" in text_lower or "2nd mid" in text_lower:
        current_exam = "mid2"
        print(f"  [Page {page_num+1}] Switched to mid2")

    text = clean(raw_text)

    # Skip pages with no numbered questions
    if not re.search(r'^\s*\d+[.\)-]\s*\w', text, re.MULTILINE):
        continue

    # Skip short-answer/essay pages
    skip_keywords = ['True or false', 'Short answer', 'Draw a', 'Draw the',
                     'Short Essay', 'Essay', 'Ans:', 'MCQ + Short']
    if sum(1 for kw in skip_keywords if kw in raw_text) >= 2:
        continue

    answer_key = parse_answer_key(text)

    if not answer_key:
        # Try to extract from raw text (before cleaning)
        answer_key = parse_answer_key(raw_text)

    qs = extract_questions(text, page_num + 1, current_exam, answer_key, page)
    if qs:
        all_questions.extend(qs)
        print(f"Page {page_num+1} ({current_exam}): {len(qs)} Qs (key: {answer_key})")
    else:
        # Debug: check if page had questions but no answers
        has_q = bool(re.search(r'^\s*\d+[.\)-]\s*\w', text, re.MULTILINE))
        if has_q and answer_key:
            pass  # silently skip
        elif has_q:
            print(f"Page {page_num+1} ({current_exam}): has questions but NO answer key")

# De-duplicate (same page + q_num combo)
seen = set()
unique_questions = []
for q in all_questions:
    key = (q["page"], q["q_num"])
    if key not in seen:
        seen.add(key)
        unique_questions.append(q)

print(f"\nTotal extracted: {len(unique_questions)} unique questions (from {len(all_questions)} total)")
OUT.write_text(json.dumps(unique_questions, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Saved to {OUT}")
