#!/usr/bin/env python3
"""
Classify questions by lecture and generate .md question files with slide-based explanations.
Steps:
1. Load extracted questions from /tmp/testbank_questions.json
2. Classify each question into a lecture using keyword matching
3. Read slide PDFs to extract relevant explanations
4. Generate question .md files in questions/ directory
5. One file per exam per lecture
"""

import fitz, re, json, pathlib, os, sys

QUESTIONS_JSON = pathlib.Path("/tmp/testbank_questions.json")
QUESTIONS_DIR = pathlib.Path("/home/user/Genatics-TestBank/questions")
SLIDES_DIR = pathlib.Path("/home/user/Genatics-TestBank")

LECTURE_MAP = {
    "L1_Introduction": [
        "allele", "genome", "syndrome", "pleiotropy", "gene variant", "locus",
        "genotype", "phenotype", "penetrance", "expressivity", "consanguinity",
        "karyotype definition", "hereditary unit", "definition of a gene",
        "alternative form", "alternative forms", "homologous chromosome",
        "somatic mosaicism", "gonadal mosaicism", "mosaicism",
        "sex-influenced", "sex-limited", "codominant", "codominance",
    ],
    "L2_Chromosomes_Structure": [
        "centromere", "metacentric", "telocentric", "acrocentric", "submetacentric",
        "heterochromatin", "euchromatin", "banding", "giemsa", "p arm", "q arm",
        "satellite", "telomere", "normal karyotype", "46,xy", "46,xx", "46,XY", "46,XX",
        "chromosome structure", "chromatin", "nucleosome", "histone",
        "karyotype", "sister chromatid", "chromatid",
    ],
    "L3_Central_Dogma": [
        "dna replication", "transcription", "translation", "codon", "anticodon",
        "mrna", "trna", "ribosome", "protein synthesis", "rna polymerase",
        "central dogma", "nucleotide", "amino acid", "rna processing",
        "poly-a tail", "5' cap", "splicing", "exon", "intron", "spliceosome",
        "start codon", "stop codon", "reading frame", "open reading frame",
        "template strand", "coding strand", "complementary", "base pairing",
        "adenine", "thymine", "guanine", "cytosine", "uracil",
        "elongation stage", "ribosomal binding", "primer", "dna polymerase",
        "exonuclease", "okazaki", "leading strand", "lagging strand",
        "dna primase", "rna primer",
    ],
    "L4_Chromosomal_Aberrations": [
        "trisomy", "monosomy", "deletion", "duplication inversion", "translocation",
        "isochromosome", "down syndrome", "turner", "klinefelter", "edwards",
        "patau", "cri du chat", "robertsonian", "reciprocal translocation",
        "47,", "45,x", "del(", "dup(", "inv(", "rob(", "triploidy",
        "aneuploidy", "nondisjunction", "fragile x", "prader", "angelman",
        "ring chromosome", "ring x", "inversion", "balanced translocation",
        "unbalanced translocation", "marker chromosome", "supernumerary",
        "mosaicism karyotype", "46,xy,del", "46,xx,del",
    ],
    "L5_L6_Mendelian": [
        "autosomal dominant", "autosomal recessive", "x-linked", "pedigree",
        "recurrence risk", "carrier", "de novo", "gonadal mosaicism",
        "inheritance pattern", "heterozygous", "homozygous", "dominant", "recessive",
        "sex-linked", "hemophilia", "duchenne", "cystic fibrosis", "sickle cell",
        "50%", "25%", "inheritance", "vertical transmission",
        "horizontal transmission", "affected male", "affected female",
        "obligate carrier", "mendelian", "mendel", "generation",
    ],
    "L7_Non_Mendelian": [
        "genomic imprinting", "prader-willi", "angelman", "upd",
        "uniparental disomy", "mitochondrial", "anticipation", "cag repeat",
        "huntington", "trinucleotide", "heteroplasmy", "maternal inheritance",
        "lyonization", "x-inactivation", "repeat expansion", "dynamic mutation",
        "homoplasmy", "mitochondrial dna", "imprinting",
    ],
    "L9_Dysmorphology": [
        "brachycephaly", "dolichocephaly", "micrognathia", "hypertelorism",
        "polydactyly", "syndactyly", "philtrum", "major anomaly", "minor anomaly",
        "dysmorphology", "clinodactyly", "brachydactyly", "arachnodactyly",
        "microcephaly", "macrocephaly", "epicanthic", "epicanthal",
        "dysmorphic", "dysmorphic features", "plagiocephaly", "trigonocephaly",
        "macrognathia", "retrognathia", "prognathia",
        "anteroposterior dimension", "shortened anteroposterior",
    ],
    "L10_Birth_Defects": [
        "malformation", "disruption", "deformation", "dysplasia", "vacterl",
        "vater", "potter", "ectodermal dysplasia", "cleft lip", "cleft palate",
        "neural tube", "anencephaly", "spina bifida", "birth defect", "congenital",
        "sequence", "association", "amniotic band", "congenital heart",
        "folic acid", "vitamin b12", "alpha fetoprotein", "afp",
    ],
    "L11_DNA_Repair": [
        "base excision repair", "nucleotide excision repair", "mismatch repair",
        "dna glycosylase", "atm", "brca", "xeroderma pigmentosum",
        "uv light", "pyrimidine dimer", "dna repair", "ner", "ber", "mmr",
        "repair mechanism", "double strand break", "homologous recombination",
        "non-homologous end joining",
    ],
    "L12_Gene_Variants": [
        "missense", "nonsense", "frameshift", "splice site", "loss of function",
        "gain of function", "silent mutation", "indel", "premature stop",
        "variant", "mutation type", "haploinsufficiency", "dominant negative",
        "benign variant", "pathogenic variant", "variant of uncertain significance",
        "vus", "germline", "somatic mutation", "point mutation",
        "substitution", "insertion", "deletion mutation",
        "smn1", "dmd", "duchene muscular dystrophy", "neurofibromatosis",
        "marfan", "fbn1", "nf1", "cafe-au-lait",
    ],
    "L13_Molecular_Techniques": [
        "pcr", "fish", "microarray", "cgh", "snp", "southern blot",
        "sanger sequencing", "wes", "wgs", "rflp", "gel electrophoresis",
        "dna fingerprinting", "molecular technique", "sequencing", "hybridization",
        "fluorescence", "array", "mlpa", "chromosomal microarray", "qf-pcr",
        "next generation sequencing", "ngs", "karyotyping technique",
    ],
    "L14_Approach_Patients": [
        "genetic counseling", "family history", "three-generation pedigree",
        "referral", "genetic clinic", "approach to patient", "risk assessment",
        "genetic testing", "prenatal diagnosis",
    ],
}

SLIDE_FILES = {
    "L1_Introduction": "(L1)Introduction of Medical Genetics 26-compressed.pdf",
    "L2_Chromosomes_Structure": "(L2)chromosomes structure .pptx final-compressed.pdf",
    "L3_Central_Dogma": "(L3)Central Dogma lecture QandA 2026.pdf",
    "L4_Chromosomal_Aberrations": "(L4)chromosomes and their  disorders   .pptx 2026 -compressed.pdf",
    "L5_L6_Mendelian": "(L5,6)Mandelian  inheritance 2025.pdf",
    "L7_Non_Mendelian": "(L7)Non-Mendelian Pattern of Inheritance 2026pdf-compressed.pdf",
    "L9_Dysmorphology": "(L9)dysmorphology lecture -compressed.pdf",
    "L10_Birth_Defects": "(L10)Birth defect .pdf",
    "L11_DNA_Repair": "(L11)DNA repair-handout_OJ26-compressed.pdf",
    "L12_Gene_Variants": "(L12)Genetic_variants_2_yr_MBBS_2026 WH-compressed.pdf",
    "L13_Molecular_Techniques": "(L13 part1) MolecularTechniques-handouts_2026_OJ-compressed.pdf",
    "L14_Approach_Patients": "(L14)Approach to patients and families with genetic disorders for 2nd med student 2026-compressed.pdf",
}

# Cache for slide text
slide_cache = {}

def load_slide_text(lecture):
    """Load and cache full text from a lecture slide PDF."""
    if lecture in slide_cache:
        return slide_cache[lecture]

    slide_file = SLIDE_FILES.get(lecture)
    if not slide_file:
        slide_cache[lecture] = ""
        return ""

    slide_path = SLIDES_DIR / slide_file
    if not slide_path.exists():
        print(f"  WARNING: slide not found: {slide_path}")
        slide_cache[lecture] = ""
        return ""

    try:
        doc = fitz.open(str(slide_path))
        all_text = []
        for page in doc:
            raw = page.get_text()
            # Remove Arabic-heavy lines
            lines = raw.split("\n")
            clean_lines = []
            for l in lines:
                arabic = sum(1 for c in l if '؀' <= c <= 'ۿ')
                if arabic > 3 and len(l.strip()) < 80:
                    continue
                clean_lines.append(l)
            all_text.append("\n".join(clean_lines))
        doc.close()
        text = "\n\n".join(all_text)
        slide_cache[lecture] = text
        print(f"  Loaded slide: {slide_file} ({len(text)} chars)")
    except Exception as e:
        print(f"  ERROR loading {slide_file}: {e}")
        slide_cache[lecture] = ""

    return slide_cache[lecture]

def get_explanation(q_text, options, lecture):
    """Find relevant explanation from slide text."""
    slide_text = load_slide_text(lecture)
    if not slide_text:
        return f"From {lecture.replace('_', ' ')}: See lecture slides for detailed explanation."

    # Extract key terms from question
    q_lower = (q_text + " " + " ".join(options)).lower()

    # Find sentences in slide that contain keywords from the question
    sentences = re.split(r'(?<=[.!?])\s+', slide_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    # Score each sentence
    scored = []
    for sent in sentences:
        sent_lower = sent.lower()
        # Count keyword matches
        score = 0
        words = re.findall(r'\b\w{4,}\b', q_lower)
        for word in words:
            if word in sent_lower:
                score += 1
        if score > 0:
            scored.append((score, sent))

    if not scored:
        # Fall back to lecture-specific generic explanation
        return generate_generic_explanation(lecture, q_text)

    # Sort by score, take top 2 sentences
    scored.sort(key=lambda x: -x[0])
    best = scored[0][1]

    # Try to get a second sentence if available
    explanation = best.strip()
    if len(explanation) > 300:
        explanation = explanation[:300] + "..."

    # Try to add a second relevant sentence
    if len(scored) > 1:
        second = scored[1][1].strip()
        if len(explanation) + len(second) < 400:
            explanation = explanation + " " + second

    return f"From {lecture.replace('_', ' ')}: {explanation}"

def generate_generic_explanation(lecture, q_text):
    """Generate a generic explanation when slide text doesn't match."""
    explanations = {
        "L1_Introduction": "Genetics introduces core concepts: alleles are alternative forms of a gene at a locus; genotype is the genetic makeup while phenotype is the observable expression; penetrance refers to the proportion of individuals with a genotype who show the phenotype.",
        "L2_Chromosomes_Structure": "Human chromosomes are classified by centromere position: metacentric (centromere central), acrocentric (centromere near end), telocentric (centromere terminal). Banding patterns (G-banding with Giemsa) allow individual chromosome identification.",
        "L3_Central_Dogma": "The central dogma: DNA is transcribed to mRNA (by RNA polymerase), and mRNA is translated to protein (by ribosomes). A codon is a triplet of nucleotides encoding one amino acid; the anticodon on tRNA is complementary.",
        "L4_Chromosomal_Aberrations": "Chromosomal aberrations include numerical (aneuploidy: trisomy, monosomy) and structural (deletion, duplication, inversion, translocation) changes. Trisomy 21 causes Down syndrome (47,XX/XY,+21); 45,X causes Turner syndrome.",
        "L5_L6_Mendelian": "Autosomal dominant inheritance shows vertical transmission (affected in every generation), 50% recurrence risk. Autosomal recessive shows horizontal patterns with 25% recurrence when both parents are carriers. X-linked recessive affects males predominantly.",
        "L7_Non_Mendelian": "Genomic imprinting: gene expression depends on parental origin. Mitochondrial inheritance is maternal. Anticipation: disease worsens in successive generations due to trinucleotide repeat expansion (e.g., Huntington: CAG>40).",
        "L9_Dysmorphology": "Dysmorphology describes abnormal physical features. Brachycephaly = shortened anteroposterior skull dimension; Dolichocephaly = elongated skull. Major anomalies have medical/functional significance; minor anomalies are variations.",
        "L10_Birth_Defects": "Birth defects are classified as: malformation (intrinsic developmental error), disruption (external interference, e.g., amniotic bands), deformation (mechanical force), or dysplasia (abnormal tissue organization).",
        "L11_DNA_Repair": "DNA repair mechanisms include: Base Excision Repair (BER) for small base damage, Nucleotide Excision Repair (NER) for bulky lesions like UV-induced pyrimidine dimers (defective in Xeroderma Pigmentosum), and Mismatch Repair (MMR) for replication errors.",
        "L12_Gene_Variants": "Mutation types: missense (amino acid change), nonsense (premature stop codon), frameshift (insertion/deletion shifting reading frame), splice site (affects mRNA processing). Loss-of-function vs gain-of-function determines inheritance pattern.",
        "L13_Molecular_Techniques": "Molecular techniques: PCR amplifies specific DNA sequences; Sanger sequencing detects point mutations; MLPA detects copy number variants; FISH detects chromosomal rearrangements; Chromosomal Microarray detects genome-wide copy number changes.",
        "L14_Approach_Patients": "The approach to genetic patients includes: taking a 3-generation family history/pedigree, identifying inheritance pattern, calculating recurrence risk, ordering appropriate genetic tests, and providing genetic counseling.",
    }
    return f"From {lecture.replace('_', ' ')}: {explanations.get(lecture, 'See lecture slides for details.')}"

def classify(q_text, options):
    """Classify a question into the most relevant lecture."""
    text = (q_text + " " + " ".join(options)).lower()
    scores = {}
    for lec, keywords in LECTURE_MAP.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[lec] = score
    if not scores:
        return "L1_Introduction"  # default
    return max(scores, key=scores.get)

# ── MAIN ──────────────────────────────────────────────────────────────────────

print("Loading questions...")
questions = json.loads(QUESTIONS_JSON.read_text(encoding="utf-8"))
print(f"Loaded {len(questions)} questions")

# Step 1: Classify all questions
print("\nClassifying questions by lecture...")
for q in questions:
    q["lecture"] = classify(q["q"], q["options"])

# Summary
from collections import Counter
lec_counts = Counter(q["lecture"] for q in questions)
exam_counts = Counter(q["exam"] for q in questions)
print("\nLecture distribution:")
for lec, count in sorted(lec_counts.items()):
    print(f"  {lec}: {count}")
print("\nExam distribution:")
for exam, count in exam_counts.items():
    print(f"  {exam}: {count}")

# Step 2: Pre-load all slide texts
print("\nLoading slide PDFs...")
for lec in LECTURE_MAP:
    load_slide_text(lec)

# Step 3: Delete old auto-generated files (keep mid1_example.md)
print("\nCleaning old question files...")
for f in QUESTIONS_DIR.glob("*.md"):
    if f.name != "mid1_example.md":
        f.unlink()
        print(f"  Deleted: {f.name}")

# Step 4: Generate .md files (one per exam per lecture)
print("\nGenerating question files...")

# Group questions by (exam, lecture)
from collections import defaultdict
grouped = defaultdict(list)
for q in questions:
    key = (q["exam"], q["lecture"])
    grouped[key].append(q)

generated_count = 0
for (exam, lecture), qs in sorted(grouped.items()):
    filename = f"{exam}_{lecture}.md"
    filepath = QUESTIONS_DIR / filename

    lines = []
    for i, q in enumerate(qs, start=1):
        q_text = q["q"]
        opts = q["options"]
        answer_letter = q["answer_letter"]
        explanation = get_explanation(q_text, opts, lecture)

        # Build question block
        lines.append(f"**Q{i}.** {q_text}")
        lines.append("")
        for j, opt in enumerate(opts):
            if opt:  # skip empty options
                letter = "ABCD"[j]
                lines.append(f"{letter}) {opt}")
        lines.append("")
        lines.append(f"**Answer:** {answer_letter}")
        lines.append(f"**Explanation:** {explanation}")
        if q.get("image"):
            lines.append(f"**Image:** {q['image']}")
        lines.append("")

    filepath.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Generated: {filename} ({len(qs)} questions)")
    generated_count += len(qs)

# Save enriched questions JSON
enriched_out = pathlib.Path("/tmp/testbank_classified.json")
enriched_out.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nEnriched JSON saved to {enriched_out}")

print(f"\nDone! Generated {len(grouped)} files with {generated_count} questions total")
