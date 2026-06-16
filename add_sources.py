#!/usr/bin/env python3
"""
Add **Source:** Med XX lines between **Answer:** and **Explanation:**
for each question in the 9 final exam markdown files.
"""

import re

# Source mappings: file -> list of (question_keyword, source) tuples
# We identify questions by their position (Q1, Q2, etc.)

FILE_SOURCES = {
    "final_L8_Pharmacogenetics.md": [
        "Med 25",  # Q1
        "Med 25",  # Q2
        "Med 25",  # Q3
        "Med 25",  # Q4
        "Med 25",  # Q5
        "Med 25",  # Q6
        "Med 18",  # Q7
        "Med 18",  # Q8
        "Med 25",  # Q9
        "Med 25",  # Q10
        "Med 25",  # Q11
        "Med 25",  # Q12
        "Med 25",  # Q13
    ],
    "final_L15_Gene_Therapy.md": [
        "Med 25",  # Q1
        "Med 24",  # Q2
        "Med 24",  # Q3
        "Med 24",  # Q4
        "Med 18",  # Q5
        "Med 18",  # Q6
        "Med 25",  # Q7
        "Med 25",  # Q8
        "Med 25",  # Q9
        "Med 25",  # Q10
        "Med 15",  # Q11
        "Med 25",  # Q12
        "Med 25",  # Q13
        "Med 25",  # Q14
        "Med 25",  # Q15
        "Med 25",  # Q16
    ],
    "final_L16_Genetic_Counseling.md": [
        "Med 25",  # Q1
        "Med 25",  # Q2
        "Med 25",  # Q3
        "Med 25",  # Q4
        "Med 25",  # Q5
        "Med 24",  # Q6
        "Med 18",  # Q7
        "Med 18",  # Q8
        "Med 18",  # Q9
        "Med 18",  # Q10
        "Med 25",  # Q11
        "Med 25",  # Q12
    ],
    "final_L17_Hemoglobinopathy.md": [
        "Med 25",  # Q1
        "Med 25",  # Q2
        "Med 25",  # Q3
        "Med 24",  # Q4
        "Med 24",  # Q5
        "Med 24",  # Q6
        "Med 25",  # Q7
        "Med 25",  # Q8
        "Med 25",  # Q9
        "Med 25",  # Q10
    ],
    "final_L18_L19_IEM.md": [
        "Med 25",  # Q1
        "Med 25",  # Q2
        "Med 25",  # Q3
        "Med 25",  # Q4
        "Med 25",  # Q5
        "Med 25",  # Q6
        "Med 24",  # Q7
        "Med 24",  # Q8
        "Med 24",  # Q9
        "Med 18",  # Q10
        "Med 18",  # Q11
        "Med 18",  # Q12
        "Med 19",  # Q13
        "Med 19",  # Q14
        "Med 19",  # Q15
        "Med 19",  # Q16
        "Med 19",  # Q17
        "Med 19",  # Q18
        "Med 19",  # Q19
        "Med 19",  # Q20
        "Med 19",  # Q21
        "Med 25",  # Q22
        "Med 25",  # Q23
        "Med 25",  # Q24
    ],
    "final_L20_Oncogenetics.md": [
        "Med 25",  # Q1
        "Med 24",  # Q2
        "Med 24",  # Q3
        "Med 24",  # Q4
        "Med 25",  # Q5
        "Med 24",  # Q6
        "Med 18",  # Q7
        "Med 18",  # Q8
        "Med 18",  # Q9
        "Med 25",  # Q10
        "Med 25",  # Q11
        "Med 25",  # Q12
        "Med 25",  # Q13
        "Med 25",  # Q14
    ],
    "final_L21_Prenatal_Diagnosis.md": [
        "Med 25",  # Q1
        "Med 25",  # Q2
        "Med 25",  # Q3
        "Med 24",  # Q4
        "Med 24",  # Q5
        "Med 24",  # Q6
        "Med 24",  # Q7
        "Med 18",  # Q8
        "Med 18",  # Q9
        "Med 18",  # Q10
        "Med 18",  # Q11
        "Med 18",  # Q12
        "Med 18",  # Q13
        "Med 18",  # Q14
        "Med 25",  # Q15
        "Med 25",  # Q16
        "Med 25",  # Q17
    ],
    "final_L22_Cytomolecular.md": [
        "Med 24",  # Q1
        "Med 24",  # Q2
        "Med 24",  # Q3
        "Med 24",  # Q4
        "Med 24",  # Q5
        "Med 24",  # Q6
        "Med 24",  # Q7
        "Med 24",  # Q8
        "Med 18",  # Q9
        "Med 18",  # Q10
        "Med 25",  # Q11
        "Med 25",  # Q12
        "Med 25",  # Q13
        "Med 25",  # Q14
        "Med 25",  # Q15
        "Med 25",  # Q16
        "Med 25",  # Q17
        "Med 25",  # Q18
        "Med 25",  # Q19
        "Med 25",  # Q20
        "Med 25",  # Q21
        "Med 25",  # Q22
        "Med 25",  # Q23
    ],
    "final_L23_PS_Clinical_Genetics.md": [
        "Med 25",  # Q1
        "Med 25",  # Q2
        "Med 25",  # Q3
        "Med 25",  # Q4
        "Med 25",  # Q5
        "Med 25",  # Q6
        "Med 25",  # Q7
        "Med 25",  # Q8
        "Med 25",  # Q9
        "Med 25",  # Q10
        "Med 25",  # Q11
        "Med 25",  # Q12
        "Med 25",  # Q13
        "Med 25",  # Q14
        "Med 25",  # Q15
        "Med 25",  # Q16
        "Med 25",  # Q17
        "Med 25",  # Q18
        "Med 25",  # Q19
        "Med 25",  # Q20
        "Med 25",  # Q21
        "Med 25",  # Q22
        "Med 25",  # Q23
        "Med 25",  # Q24
        "Med 25",  # Q25
        "Med 25",  # Q26
        "Med 18",  # Q27
        "Med 18",  # Q28
        "Med 18",  # Q29
        "Med 18",  # Q30
        "Med 18",  # Q31
        "Med 18",  # Q32
        "Med 18",  # Q33
    ],
}

QUESTIONS_DIR = "/home/user/Genatics-TestBank/questions"

def process_file(filename, sources):
    filepath = f"{QUESTIONS_DIR}/{filename}"

    with open(filepath, 'r') as f:
        content = f.read()

    # Check if sources already added
    if "**Source:**" in content:
        print(f"  WARNING: {filename} already contains **Source:** lines. Skipping to avoid duplicates.")
        return 0

    # Find all Answer lines and their positions
    # Pattern: **Answer:** X (possibly on its own line)
    answer_pattern = re.compile(r'(\*\*Answer:\*\* .+?\n)(\*\*Explanation:\*\*)', re.DOTALL)

    # We need to process question by question
    # Find all question boundaries: **Q1.**, **Q2.**, etc.
    question_starts = list(re.finditer(r'\*\*Q(\d+)\.\*\*', content))

    if len(question_starts) != len(sources):
        print(f"  ERROR: {filename} has {len(question_starts)} questions but {len(sources)} sources provided!")
        return 0

    # Process in reverse order to preserve positions
    result = content
    replacements = 0

    # Find all Answer+Explanation pairs in order
    answer_exp_pattern = re.compile(r'(\*\*Answer:\*\* [A-Ea-e\w,/\s\(\)]+?\n)(\*\*Explanation:\*\*)')
    matches = list(answer_exp_pattern.finditer(content))

    if len(matches) != len(sources):
        print(f"  ERROR: Found {len(matches)} Answer/Explanation pairs but {len(sources)} sources in {filename}")
        # Try a simpler approach
        return 0

    # Replace in reverse order
    for i in range(len(matches) - 1, -1, -1):
        match = matches[i]
        source = sources[i]
        answer_line = match.group(1)
        expl_start = match.group(2)
        replacement = f"{answer_line}**Source:** {source}\n{expl_start}"
        result = result[:match.start()] + replacement + result[match.end():]
        replacements += 1

    with open(filepath, 'w') as f:
        f.write(result)

    print(f"  Added {replacements} source tags to {filename}")
    return replacements


def main():
    total = 0
    for filename, sources in FILE_SOURCES.items():
        print(f"Processing {filename} ({len(sources)} questions)...")
        count = process_file(filename, sources)
        total += count

    print(f"\nTotal source tags added: {total}")


if __name__ == "__main__":
    main()
