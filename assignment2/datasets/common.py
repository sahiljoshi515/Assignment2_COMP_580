"""Assignment 2 -- common.py: the machinery shared by the four dataset generators.

Concept this file teaches: a benchmark for duplicate detection is only as honest as
its labels. Every record here is produced from a hidden *state* -- what the record is
about (the canonical), which template variant each sentence uses, which cosmetic
details were rolled, how it is formatted -- and every duplicate is a transformation of
that state, never of the text. The answer is derived from the canonical alone, so
"same canonical => same answer" holds by construction, and the ground truth that the
verifier and the scorer read is the canonical identity, written to hidden/ where the
agent cannot see it.

Design rules this file embodies:
  * Determinism by construction: one random.Random per (seed, stage, index), string
    seeds (sha512-hashed by CPython, so PYTHONHASHSEED cannot reach them), no hash(),
    no set iteration, sorted directory listings, no clocks.
  * The agent sees env/ and nothing else. Everything that could leak an answer lives
    in hidden/ or in MANIFEST.json beside it, and the tests check that boundary.
  * Transformations keep invariants the tests can check: formatting never changes the
    alphanumeric token sequence, edits never touch a protected word, paraphrases keep
    the structured fields, hard negatives flip exactly one semantic slot everywhere it
    appears and always change the answer.
  * One skeleton, four generators. A generator is data plus eight small functions (the
    Spec contract below); the stream plan, the transforms, the writers and the
    diagnostics are the same for all of them, so a property proven here holds for all.
"""

import argparse
import datetime
import hashlib
import json
import os
import random
import re
import textwrap

CHARS_PER_TOKEN = 4
BUDGET = (30_000, 50_000)        # tokens of env/ content, enforced at benchmark sizes
BENCHMARK_MAX = (160, 80)        # (history, incoming) up to which the budget is enforced
DUP_SOURCE_POOL = 120            # history-sourced duplicates draw from history[:120]
HISTORY_TWIN_RATE = 0.10         # share of history records that are flips of an earlier one
HARD_NEGATIVE_RATE = 0.20        # share of incoming tasks that are hard negatives
HN_SOURCE_ATTEMPTS = 8           # sources tried before a hard-negative slot degrades to an original
DUP_KINDS = {"exact": 0.15, "format": 0.25, "reorder": 0.15, "edit": 0.20, "paraphrase": 0.25}
SOURCE_MIX = {"history": 0.70, "task": 0.30}
PARAPHRASE_MIN_CHANGED = 0.70    # share of units that must switch template variant
STYLE_SPACE = {                  # the formatting axes a "format" duplicate can move on
    "header": ["md", "caps", "plain"],   # none of these add a token: "## X", "X:", "X"
    "bullet": ["- ", "* "],              # numbered bullets would add digits, i.e. tokens
    "wrap": [None, 60, 80, 100],
    "quote": ['"', "'"],
    "dash": ["-", "--"],
    "title_case": [False, True],
    "fields": ["as-is", "lower", "compact"],
}
HISTORY_START = datetime.date(2025, 1, 6)
TASK_START = datetime.date(2026, 1, 5)
TASK_SPAN_DAYS = 84


# ---------------------------------------------------------------------------
# randomness, ids, apportioning
# ---------------------------------------------------------------------------
def sub_rng(seed, *parts):
    """A fresh generator for one stage: history[i] depends on (seed, i) and nothing else."""
    return random.Random("%s/%s" % (seed, "/".join(str(p) for p in parts)))


def hex_id(rng, prefix, taken):
    """A random 6-hex id such as H-3fa9c2; `taken` is only ever tested for membership."""
    while True:
        candidate = "%s-%06x" % (prefix, rng.getrandbits(24))
        if candidate not in taken:
            taken.add(candidate)
            return candidate


def pick(rng, seq):
    """Choose from a list (never a set: set order is not deterministic across runs)."""
    return seq[rng.randrange(len(seq))]


def apportion(weights, n):
    """Split n into integer counts proportional to `weights`, largest remainder method."""
    keys = list(weights)
    total = float(sum(weights[k] for k in keys)) or 1.0
    raw = [n * weights[k] / total for k in keys]
    counts = [int(x) for x in raw]
    for i in sorted(range(len(keys)), key=lambda i: (-(raw[i] - counts[i]), i))[: n - sum(counts)]:
        counts[i] += 1
    return dict(zip(keys, counts))


def derange(rng, items):
    """A permutation with no fixed point (for two or more items; one item is returned as is)."""
    items = list(items)
    if len(items) < 2:
        return items
    while True:
        order = list(range(len(items)))
        rng.shuffle(order)
        if all(i != j for i, j in enumerate(order)):
            return [items[j] for j in order]


def canonical_id(canonical):
    """Hidden identity of a record: a hashlib digest of its canonical tuple, never hash()."""
    blob = json.dumps(canonical, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return "C-" + hashlib.sha1(blob).hexdigest()[:8]


def canonical_key(canonical):
    """Canonicals are dicts; this is the hashable form used for `used`/reserved bookkeeping."""
    return json.dumps(canonical, sort_keys=True, ensure_ascii=True)


# ---------------------------------------------------------------------------
# tokens and the budget
# ---------------------------------------------------------------------------
def estimate_tokens(text):
    """The same chars/4 estimate the harness uses for compaction (spartacus/context.py)."""
    return len(text) // CHARS_PER_TOKEN


def env_estimate(env_dir):
    """Tokens per group of env/ content: instructions, history, incoming, reference data."""
    groups = {"instructions": 0, "history": 0, "incoming": 0, "reference": 0}
    for name in sorted(os.listdir(env_dir)):
        path = os.path.join(env_dir, name)
        if name == "incoming":
            for task in sorted(os.listdir(path)):
                groups["incoming"] += estimate_tokens(_read(os.path.join(path, task)))
        elif name == "INSTRUCTIONS.md":
            groups["instructions"] += estimate_tokens(_read(path))
        elif name == "history.jsonl":
            groups["history"] += estimate_tokens(_read(path))
        elif os.path.isdir(path):   # a corpus dataset's scenarios/ tree: every file under it
            for base, _, files in os.walk(path):
                for file in sorted(files):
                    groups["reference"] += estimate_tokens(_read(os.path.join(base, file)))
        else:
            groups["reference"] += estimate_tokens(_read(path))
    groups["total"] = sum(groups.values())
    return groups


def _read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


# ---------------------------------------------------------------------------
# text transforms (format, edit, paraphrase)
# ---------------------------------------------------------------------------
def render_sections(sections, style):
    """Join (header, text) sections into a body under one formatting style."""
    out = []
    for number, (header, text) in enumerate(sections, 1):
        text = restyle_text(text, style)
        if header:
            out.append(render_header(header, style, number))
        out.append(text)
    body = "\n\n".join(part for part in out if part)
    return body


def render_header(header, style, number):
    """One section header in the md / caps / plain style (the number is deliberately unused)."""
    if style["header"] == "md":
        return "## " + header
    if style["header"] == "caps":
        return header.upper() + ":"
    return header


def restyle_text(text, style):
    """Bullets, quotes, dashes and wrapping; never touches an alphanumeric character."""
    lines = []
    for line in text.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("- "):
            line = style["bullet"] + stripped[2:]
        lines.append(line)
    text = "\n".join(lines)
    if style["quote"] == "'":
        text = text.replace('"', "'")
    if style["dash"] == "--":
        text = re.sub(r"(?<=\w) - (?=\w)", " -- ", text)
    if style["wrap"]:
        text = rewrap(text, style["wrap"])
    return text


def _is_bullet(line):
    return bool(re.match(r"^\s*(- |\* |\d+[.)] )", line))


def rewrap(text, width):
    """Re-flow prose paragraphs at `width`; bullet lines are wrapped with a hanging indent."""
    out = []
    for para in text.split("\n\n"):
        if any(_is_bullet(line) for line in para.split("\n")):
            for line in para.split("\n"):
                if _is_bullet(line):
                    marker = re.match(r"^\s*(- |\* |\d+[.)] )", line).group(0)
                    out.append(textwrap.fill(line, width, subsequent_indent=" " * len(marker)))
                else:
                    out.append(textwrap.fill(line, width))
            out.append("")
        else:
            out.append(textwrap.fill(" ".join(para.split()), width))
            out.append("")
    return "\n".join(out).strip()


def recase_title(rng, title):
    """A title in one of three cases; identifiers (CHG-4412, E-1042) are left alone."""
    choice = rng.randrange(3)
    words = title.split(" ")

    def is_identifier(word):
        return bool(re.search(r"[A-Z]+-?\d", word)) or bool(re.search(r"\d", word))

    if choice == 0:
        return " ".join(w if is_identifier(w) else w.lower() for w in words)
    if choice == 1:
        return " ".join(w if is_identifier(w) else (w[:1].upper() + w[1:]) for w in words)
    return title


def random_style(rng, avoid=None, min_diff=2):
    """A formatting style; with `avoid`, one that differs from it on >= min_diff axes."""
    while True:
        style = {axis: pick(rng, options) for axis, options in STYLE_SPACE.items()}
        if avoid is None or sum(style[a] != avoid[a] for a in STYLE_SPACE) >= min_diff:
            return style


def typo(rng, word):
    """One of three keyboard slips: swap two neighbours, drop a letter, double a letter."""
    if len(word) < 5:
        return word
    i = rng.randrange(1, len(word) - 2)
    choice = rng.randrange(3)
    if choice == 0:
        return word[:i] + word[i + 1] + word[i] + word[i + 2:]
    if choice == 1:
        return word[:i] + word[i + 1:]
    return word[:i] + word[i] + word[i:]


def minor_edits(rng, text, protected, k=2):
    """Introduce k typos into words of >= 5 letters that are not protected."""
    protected = {norm_text(p) for p in protected}
    words = re.findall(r"[A-Za-z]{5,}", text)
    candidates = sorted({w for w in words if norm_text(w) not in protected and not any(
        norm_text(w) in p or p in norm_text(w) for p in protected)})
    rng.shuffle(candidates)
    for word in candidates[:k]:
        text = re.sub(r"\b%s\b" % re.escape(word), typo(rng, word), text, count=1)
    return text


def synonymise(rng, text, table, protected, rate=0.6):
    """Swap words that have an entry in `table` (word -> [alternatives]) unless protected."""
    protected = {norm_text(p) for p in protected}

    def swap(match):
        word = match.group(0)
        key = word.lower()
        if key in table and norm_text(word) not in protected and rng.random() < rate:
            alt = pick(rng, table[key])
            return alt[:1].upper() + alt[1:] if word[:1].isupper() else alt
        return word

    return re.sub(r"[A-Za-z]+", swap, text)


# ---------------------------------------------------------------------------
# normalisers shared by generators, verifiers and (as a suggestion) the students
# ---------------------------------------------------------------------------
def norm_text(text):
    """Lower-case, every non-alphanumeric run becomes one space, no edge spaces."""
    return " ".join(re.findall(r"[a-z0-9]+", str(text).lower()))


def norm_code(code):
    """E-1042, e1042 and E 1042 are one code."""
    return re.sub(r"[^a-z0-9]", "", str(code).lower())


def norm_frame(frame):
    """lattice/net/http.py::fetch and lattice.net.http.fetch are one frame."""
    frame = str(frame).strip().lower()
    frame = re.sub(r"\.py::", ".", frame)
    frame = frame.replace("/", ".").replace("::", ".")
    frame = re.sub(r":\d+$", "", frame)
    return frame


def norm_version(version):
    """v3.1.2, 3.1.2 and '3.1.2 (build 77)' are all series 3.1."""
    match = re.search(r"(\d+)\.(\d+)", str(version))
    return "%s.%s" % (match.group(1), match.group(2)) if match else norm_text(version)


def norm_doi(doi):
    """DOIs are case-insensitive; resolver prefixes and a 'doi:' label are not part of them."""
    doi = str(doi or "").strip().lower()
    doi = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"^doi:\s*", "", doi)
    return doi.rstrip(". ")


def norm_title(title):
    """Alphanumeric tokens only, so punctuation and case differences do not matter."""
    return norm_text(title)


def norm_author(name):
    """'Priya Raman', 'Raman, P.' and 'P Raman' -> ('raman', 'p')."""
    name = str(name).strip()
    if "," in name:
        surname, given = [part.strip() for part in name.split(",", 1)]
    else:
        parts = name.split()
        surname, given = (parts[-1], " ".join(parts[:-1])) if len(parts) > 1 else (name, "")
    initial = norm_text(given)[:1]
    return (norm_text(surname), initial)


def norm_rid(value, prefix, count):
    """R-7, r-07, '7' and 'R07' -> 'R-07' when 1 <= 7 <= count; otherwise None."""
    match = re.search(r"\d+", str(value or ""))
    if not match:
        return None
    number = int(match.group(0))
    if not 1 <= number <= count:
        return None
    return "%s-%02d" % (prefix, number)


def null_ish(value):
    """None, '', 'null', 'none' and 'n/a' all mean 'no value'."""
    return value is None or str(value).strip().lower() in ("", "null", "none", "n/a")


# ---------------------------------------------------------------------------
# similarity diagnostics (what the report uses to say where a threshold will land)
# ---------------------------------------------------------------------------
def tokens(text):
    return re.findall(r"[a-z0-9]+", str(text).lower())


_DIGITS = re.compile(r"\d+")
_HEXISH = re.compile(r"^[0-9a-f]+$")


def content_tokens(text, mask_numbers=True):
    """The content layer's tokens: `tokens()` with every number collapsed to "0".

    Two log files of the same service differ in every timestamp and request id and
    agree on everything else; two copies of a config file differ in a port number. For
    *task* identity digits carry meaning (E-1042 is not E-1043), so `tokens()` keeps
    them; for *content* reuse the question is "is this the same text up to the numbers",
    and the exact diff that follows a fold shows the numbers anyway. A token made only
    of hex digits that contains at least one digit (a request id, a build hash) is a
    number for this purpose: repetitive text has few distinct shingles, so one unique
    id per line would otherwise dominate the Jaccard of two near-identical logs.
    """
    toks = tokens(text)
    if mask_numbers:
        toks = ["0" if _HEXISH.match(t) and any(c.isdigit() for c in t) else _DIGITS.sub("0", t) for t in toks]
    return toks


def shingles(text, k=3):
    toks = tokens(text)
    return {" ".join(toks[i:i + k]) for i in range(max(0, len(toks) - k + 1))}


def content_shingles(text, k=3, mask_numbers=True):
    toks = content_tokens(text, mask_numbers)
    return {" ".join(toks[i:i + k]) for i in range(max(0, len(toks) - k + 1))}


def jaccard_content(text_a, text_b, mask_numbers=True):
    """Exact Jaccard of 3-shingles over content tokens: what the content layer estimates."""
    return jaccard(content_shingles(text_a, 3, mask_numbers), content_shingles(text_b, 3, mask_numbers))


def jaccard(a, b):
    if not a and not b:
        return 1.0
    return len(a & b) / float(len(a | b))


def jaccard_3shingles(text_a, text_b):
    """Exact Jaccard of word 3-shingles over normalised tokens: the quantity MinHash estimates."""
    return jaccard(shingles(text_a), shingles(text_b))


def similarity_report(samples):
    """samples: class -> list of Jaccard values. Returns summary stats and a printable table."""
    summary = {}
    lines = ["%-14s %5s %6s %6s %6s %6s %6s  histogram (0..1 in 10 bins)" % (
        "class", "n", "min", "p10", "p50", "p90", "max")]
    for name in samples:
        values = sorted(samples[name])
        if not values:
            summary[name] = {"n": 0}
            lines.append("%-14s %5d" % (name, 0))
            continue

        def q(p):
            return values[min(len(values) - 1, int(p * len(values)))]

        bins = [0] * 10
        for v in values:
            bins[min(9, int(v * 10))] += 1
        peak = max(bins) or 1
        hist = "".join(" .:-=+*#%@"[min(9, int(9 * b / peak))] for b in bins)
        summary[name] = {"n": len(values), "min": round(values[0], 3), "p10": round(q(0.1), 3),
                         "p50": round(q(0.5), 3), "p90": round(q(0.9), 3), "max": round(values[-1], 3)}
        lines.append("%-14s %5d %6.3f %6.3f %6.3f %6.3f %6.3f  [%s]" % (
            name, len(values), values[0], q(0.1), q(0.5), q(0.9), values[-1], hist))
    return summary, "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON writers
# ---------------------------------------------------------------------------
def ordered(record, fields):
    """Re-key a record in the declared field order; the key set must match exactly."""
    missing = [f for f in fields if f not in record]
    extra = [k for k in record if k not in fields]
    if missing or extra:
        raise ValueError("record fields mismatch: missing %s, extra %s" % (missing, extra))
    return {f: record[f] for f in fields}


def dump_json(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(obj, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def dump_jsonl(records, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


# ---------------------------------------------------------------------------
# verifier helpers: each dataset's verify.py supplies grade(tid, answer) and reuses these
# ---------------------------------------------------------------------------
_LABELS = {}


def load_labels(hidden_dir):
    """hidden/labels.json, read once per process; the verifier is the only reader besides metrics."""
    path = os.path.join(hidden_dir, "labels.json")
    if path not in _LABELS:
        with open(path, encoding="utf-8") as handle:
            _LABELS[path] = json.load(handle)
    return _LABELS[path]


def check_object(answer):
    """The first check of every verifier: the answer must be a JSON object."""
    return (isinstance(answer, dict), "got %s" % type(answer).__name__)


def shortfall(checks):
    """Failing checks only, as 'label: detail' strings (the shape day5_verify.py uses)."""
    return ["%s: %s" % (label, detail) for label, (passed, detail) in checks.items() if not passed]


def report(tid, checks):
    """Print one result card and return whether every check passed."""
    ok = all(passed for passed, _ in checks.values())
    print("%s %s" % ("PASS" if ok else "FAIL", tid))
    for label, (passed, detail) in checks.items():
        print("  [%s] %s: %s" % ("x" if passed else " ", label, detail))
    return ok


def verifier_main(grade, argv=None):
    """`python3 verify.py --tid T-xxxxxx --answer path/to/answer.json`; exit 0 on pass."""
    parser = argparse.ArgumentParser(description="Grade one answer.json against the hidden labels.")
    parser.add_argument("--tid", required=True)
    parser.add_argument("--answer", required=True, help="path to the agent's answer.json")
    args = parser.parse_args(argv)
    try:
        with open(args.answer, encoding="utf-8") as handle:
            answer = json.load(handle)
    except (OSError, ValueError) as error:
        answer = None
        print("could not read %s: %s" % (args.answer, error))
    return 0 if report(args.tid, grade(args.tid, answer)) else 1


# ---------------------------------------------------------------------------
# the Spec contract and the generator skeleton
# ---------------------------------------------------------------------------
class Spec:
    """What a dataset must supply. Subclass it in <name>/generate.py and fill in the data.

    Attributes
      NAME, HISTORY_FIELDS, TASK_FIELDS, DATE_FIELD (history), TASK_DATE_FIELD,
      UNITS (ordered unit names), VARIANTS (int, variants per unit), SYNONYMS (word -> [alts]),
      MAX_HISTORY, MAX_INCOMING (reserved pool ranges), REORDERABLE (bool).
    Methods
      pool_size()                      -> int, how many canonicals canonical_at can produce
      canonical_at(k)                  -> dict, the k-th canonical of a fixed seeded permutation
      flip(rng, canonical)             -> list of candidate canonicals that change the answer
      answer(canonical)                -> dict of answer fields
      cosmetic(rng)                    -> dict of cosmetic slot values
      compose(state)                   -> {"fields": {...}, "title": str, "sections": [(header, text)]}
      recase_fields(fields, style)     -> fields as the format transform would re-spell them
      protected(state)                 -> list of words that typos and synonyms must not touch
      validation_tuple(record)         -> hashable normalised visible fields
      text_for_similarity(record)      -> the text the diagnostics measure
      instructions()                   -> INSTRUCTIONS.md text
    """

    NAME = ""
    FILE = __file__                  # subclasses set FILE = __file__ so --out defaults beside them
    HISTORY_FIELDS = ()
    TASK_FIELDS = ()
    DATE_FIELD = "filed"
    TASK_DATE_FIELD = "received"
    UNITS = ()
    VARIANTS = 3
    SYNONYMS = {}
    MAX_HISTORY = 160
    MAX_INCOMING = 80
    REORDERABLE = True
    DEFAULT_SEED = 1
    DEFAULT_DUP_RATE = 0.40
    DEFAULT_HISTORY = 120
    DEFAULT_INCOMING = 60
    TEXT_FOR_SIMILARITY = "see generate.py"

    def differs_in(self, canonical, other):
        """Names of the canonical slots that differ between a hard negative and its twin."""
        return sorted(k for k in canonical if canonical.get(k) != other.get(k))

    def history_answer_fields(self, answer):
        """How a history record carries the answer. Default: the answer's own keys, flattened
        into the record. A dataset whose record nests it (citations: `verdict`) overrides this;
        labels, the verifier and the oracle agent always use the flat `answer()` shape."""
        return dict(answer)

    def new_state(self, rng, canonical):
        return {"canonical": canonical,
                "variants": {unit: rng.randrange(self.VARIANTS) for unit in self.UNITS},
                "cosmetic": self.cosmetic(rng),
                "style": random_style(rng),
                "order": None}

    def budget_for(self, groups, env_dir):
        """(range, measured) the token budget is judged on. Default: BUDGET over all of env/.

        A corpus dataset overrides this: its env/ holds every scenario, but one task's
        working directory holds only one, so the number that matters is per task."""
        return list(BUDGET), groups["total"]


def plan_stream(rng, n, dup_rate):
    """The incoming sequence as slots: ('orig',), ('dup', kind, source), ('hn', source)."""
    n_dup = int(round(dup_rate * n))
    n_hn = min(int(round(HARD_NEGATIVE_RATE * n)), n - n_dup)
    n_orig = n - n_dup - n_hn
    kinds = apportion(DUP_KINDS, n_dup)
    dup_sources = apportion(SOURCE_MIX, n_dup)
    hn_sources = apportion(SOURCE_MIX, n_hn)
    slots = [("orig",)] * n_orig
    kind_list = [k for k in DUP_KINDS for _ in range(kinds[k])]
    src_list = [s for s in SOURCE_MIX for _ in range(dup_sources[s])]
    rng.shuffle(kind_list)
    rng.shuffle(src_list)
    slots += [("dup", k, s) for k, s in zip(kind_list, src_list)]
    hn_src = [s for s in SOURCE_MIX for _ in range(hn_sources[s])]
    rng.shuffle(hn_src)
    slots += [("hn", s) for s in hn_src]
    rng.shuffle(slots)
    for i, slot in enumerate(slots):                 # position 1 can never be task-sourced
        if slot[-1] == "task":
            continue
        slots[0], slots[i] = slots[i], slots[0]
        break
    return slots


def copy_state(state):
    """A deep-enough copy: dict-valued slots are copied, scalars (and typo seeds) carried over."""
    return {k: (dict(v) if isinstance(v, dict) else v) for k, v in state.items()}


def transform(spec, rng, state, kind):
    """A duplicate's state from its source's state; the canonical never changes here.

    The whole source state is carried over, typo and synonym seeds included, so an exact
    duplicate of an edited task reproduces the edited text byte for byte.
    """
    new = copy_state(state)
    if kind == "exact":
        return new
    if kind == "format":
        new["style"] = random_style(rng, avoid=state["style"])
        return new
    if kind == "reorder":
        new["order"] = "derange"
        return new
    if kind == "edit":
        fresh = spec.cosmetic(rng)              # re-roll about half of the cosmetic slots, not all
        keys = sorted(fresh)
        rng.shuffle(keys)
        for key in keys[:max(1, len(keys) // 2)]:
            new["cosmetic"][key] = fresh[key]
        new["typos"] = rng.getrandbits(32)
        return new
    if kind == "paraphrase":
        units = list(spec.UNITS)
        need = max(1, int(round(PARAPHRASE_MIN_CHANGED * len(units))))
        rng.shuffle(units)
        for unit in units[:need]:
            options = [v for v in range(spec.VARIANTS) if v != state["variants"][unit]]
            new["variants"][unit] = pick(rng, options)
        new["synonyms"] = rng.getrandbits(32)
        return new
    raise ValueError(kind)


def render(spec, state, rng=None):
    """Text fields of a record from its state (the only place text is produced)."""
    parts = spec.compose(state)
    sections = list(parts["sections"])
    if state.get("order") == "derange" and spec.REORDERABLE and len(sections) > 1:
        sections = derange(random.Random("order/%s" % json.dumps(state["variants"], sort_keys=True)), sections)
    style = state["style"]
    body = render_sections(sections, style)
    title = parts.get("title", "")
    if style["title_case"] and title:
        title = recase_title(random.Random("title/%s" % title), title)
    fields = spec.recase_fields(dict(parts["fields"]), style)
    protected = spec.protected(state)
    if "typos" in state:
        body = minor_edits(random.Random(state["typos"]), body, protected)
    if "synonyms" in state:
        body = synonymise(random.Random(state["synonyms"]), body, spec.SYNONYMS, protected)
    return fields, title, body


def build(spec, seed, history_size, incoming, dup_rate):
    """Everything a dataset consists of, in memory, from a seed and three sizes."""
    if history_size > spec.MAX_HISTORY or incoming > spec.MAX_INCOMING:
        raise ValueError("%s supports at most %d history and %d incoming records" % (
            spec.NAME, spec.MAX_HISTORY, spec.MAX_INCOMING))
    pool_n = spec.pool_size()
    if pool_n < spec.MAX_HISTORY + spec.MAX_INCOMING:
        raise ValueError("%s: canonical pool (%d) smaller than MAX_HISTORY + MAX_INCOMING" % (spec.NAME, pool_n))
    reserved = {canonical_key(spec.canonical_at(k)) for k in range(spec.MAX_HISTORY)}
    reserved |= {canonical_key(spec.canonical_at(pool_n - 1 - k)) for k in range(spec.MAX_INCOMING)}
    used = set()
    taken_ids = set()
    # The history is always planned at MAX_HISTORY and then sliced, so that a bigger
    # --history-size is a strict superset: the same prefix of records, the same incoming
    # tasks and the same labels. Task-level flips avoid every canonical the full history
    # would use (`used` below), whichever size is written out.
    history = []
    for i in range(spec.MAX_HISTORY):
        rng = sub_rng(seed, "history", i)
        twin_of, state = None, None
        if i > 0 and rng.random() < HISTORY_TWIN_RATE:
            source = history[rng.randrange(min(i, DUP_SOURCE_POOL))]
            flipped = _flip(spec, rng, source["state"], used, reserved)
            if flipped is not None:
                state, twin_of = flipped, source["hid"]
        if state is None:
            canonical = spec.canonical_at(i)
            state = spec.new_state(rng, canonical)
        used.add(canonical_key(state["canonical"]))
        hid = hex_id(sub_rng(seed, "hid", i), "H", taken_ids)
        date = HISTORY_START + datetime.timedelta(days=int(348 * i / spec.MAX_HISTORY))
        history.append({"hid": hid, "state": state, "twin_of": twin_of, "date": date.isoformat(),
                        "canonical_id": canonical_id(state["canonical"])})
    history = history[:history_size]
    stream = plan_stream(sub_rng(seed, "stream", incoming, dup_rate), incoming, dup_rate)
    tasks = []
    n_orig_used = 0
    for seq, slot in enumerate(stream, 1):
        rng = sub_rng(seed, "task", seq, slot[0])
        label = {"dup_of": None, "dup_kind": "none", "hard_negative_of": None, "differs_in": []}
        if slot[0] == "orig":
            canonical = spec.canonical_at(pool_n - 1 - n_orig_used)
            n_orig_used += 1
            state = spec.new_state(rng, canonical)
        else:
            source_kind = slot[-1]

            def draw_source():
                if source_kind == "task" and tasks:
                    item = tasks[rng.randrange(len(tasks))]
                    return item["tid"], item["state"]
                item = history[rng.randrange(min(len(history), DUP_SOURCE_POOL))]
                return item["hid"], item["state"]

            source_id, source_state = draw_source()
            if slot[0] == "dup":
                state = transform(spec, rng, source_state, slot[1])
                label.update({"dup_of": source_id, "dup_kind": slot[1]})
            else:
                state = _flip(spec, rng, source_state, used, reserved)
                for _ in range(HN_SOURCE_ATTEMPTS - 1):      # another source may have a legal flip
                    if state is not None:
                        break
                    source_id, source_state = draw_source()
                    state = _flip(spec, rng, source_state, used, reserved)
                if state is None:                 # no legal flip anywhere: fall back to a fresh original
                    canonical = spec.canonical_at(pool_n - 1 - n_orig_used)
                    n_orig_used += 1
                    state = spec.new_state(rng, canonical)
                else:
                    label["hard_negative_of"] = source_id
        if slot[0] != "dup":
            used.add(canonical_key(state["canonical"]))
        tid = hex_id(sub_rng(seed, "tid", seq), "T", taken_ids)
        date = TASK_START + datetime.timedelta(days=int(TASK_SPAN_DAYS * (seq - 1) / max(1, incoming)))
        tasks.append({"tid": tid, "seq": seq, "state": state, "date": date.isoformat(), "label": label,
                      "canonical_id": canonical_id(state["canonical"])})
    return {"spec": spec, "seed": seed, "history": history, "tasks": tasks,
            "args": {"history_size": history_size, "incoming": incoming, "dup_rate": dup_rate}}


def _flip(spec, rng, state, used, reserved):
    """A hard-negative state: one semantic slot flipped so the answer changes, or None.

    `spec.flip` returns its options in priority order (the most similar-looking flips
    first); the first legal one wins, so a spec that wants variety shuffles within a group.
    """
    for canonical in spec.flip(rng, state["canonical"]):
        key = canonical_key(canonical)
        if key in used or key in reserved:
            continue
        if spec.answer(canonical) == spec.answer(state["canonical"]):
            continue
        new = copy_state(state)
        new["canonical"] = canonical
        return new
    return None


def materialise(dataset):
    """Records, labels and pairs from the in-memory build; this is what gets written."""
    spec = dataset["spec"]
    history_records, history_meta = [], {}
    by_canonical = {}
    for item in dataset["history"]:
        fields, title, body = render(spec, item["state"])
        record = dict(fields)
        record.update(spec.history_answer_fields(spec.answer(item["state"]["canonical"])))
        record.update({"hid": item["hid"], spec.DATE_FIELD: item["date"]})
        if "title" in spec.HISTORY_FIELDS:
            record["title"] = title
        if "body" in spec.HISTORY_FIELDS:
            record["body"] = body
        history_records.append(ordered(record, spec.HISTORY_FIELDS))
        history_meta[item["hid"]] = {"canonical_id": item["canonical_id"], "twin_of": item["twin_of"]}
        by_canonical.setdefault(item["canonical_id"], []).append(item["hid"])
    task_records, labels, equivalent, hard_negative = [], {}, [], []
    for item in dataset["tasks"]:
        fields, title, body = render(spec, item["state"])
        record = dict(fields)
        record.update({"tid": item["tid"], "seq": item["seq"], spec.TASK_DATE_FIELD: item["date"]})
        if "title" in spec.TASK_FIELDS:
            record["title"] = title
        if "body" in spec.TASK_FIELDS:
            record["body"] = body
        task_records.append(ordered(record, spec.TASK_FIELDS))
        answer = spec.answer(item["state"]["canonical"])
        if hasattr(spec, "finalise_answer"):
            answer = spec.finalise_answer(answer, item["canonical_id"], by_canonical)
        label = dict(item["label"])
        label.update({"answer": answer, "canonical_id": item["canonical_id"], "seq": item["seq"]})
        if label["hard_negative_of"]:
            label["differs_in"] = spec.differs_in(item["state"]["canonical"], _state_of(dataset, label["hard_negative_of"])["canonical"])
            hard_negative.append({"a": label["hard_negative_of"], "b": item["tid"], "differs_in": label["differs_in"]})
        labels[item["tid"]] = label
        for other in by_canonical.get(item["canonical_id"], []):
            equivalent.append({"a": other, "b": item["tid"], "kind": label["dup_kind"] if label["dup_of"] == other else "class"})
        by_canonical.setdefault(item["canonical_id"], []).append(item["tid"])
    return {"history": history_records, "tasks": task_records, "labels": labels,
            "pairs": {"equivalent": equivalent, "hard_negative": hard_negative}, "history_meta": history_meta}


def _state_of(dataset, record_id):
    for item in dataset["history"]:
        if item["hid"] == record_id:
            return item["state"]
    for item in dataset["tasks"]:
        if item["tid"] == record_id:
            return item["state"]
    raise KeyError(record_id)


def diagnostics(dataset, materialised):
    """Jaccard of 3-shingles per class: exact, format, reorder, edit, paraphrase, hard_negative, confusable, random."""
    spec = dataset["spec"]
    text = {}
    for record in materialised["history"]:
        text[record["hid"]] = spec.text_for_similarity(record)
    for record in materialised["tasks"]:
        text[record["tid"]] = spec.text_for_similarity(record)
    samples = {k: [] for k in ("exact", "format", "reorder", "edit", "paraphrase", "hard_negative", "confusable", "random")}
    for tid, label in materialised["labels"].items():
        if label["dup_of"]:
            samples[label["dup_kind"]].append(jaccard_3shingles(text[tid], text[label["dup_of"]]))
        if label["hard_negative_of"]:
            samples["hard_negative"].append(jaccard_3shingles(text[tid], text[label["hard_negative_of"]]))
    records = materialised["history"] + materialised["tasks"]
    ids = [r.get("hid") or r.get("tid") for r in records]
    canon = {item["hid"]: item["canonical_id"] for item in dataset["history"]}
    canon.update({item["tid"]: item["canonical_id"] for item in dataset["tasks"]})
    vt = {}
    for record, rid in zip(records, ids):
        vt.setdefault(spec.validation_tuple(record), []).append(rid)
    for group in vt.values():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                if canon[group[i]] != canon[group[j]]:
                    samples["confusable"].append(jaccard_3shingles(text[group[i]], text[group[j]]))
    rng = random.Random("diagnostics")
    for _ in range(min(300, len(ids) * 2)):
        a, b = pick(rng, ids), pick(rng, ids)
        if a != b and canon[a] != canon[b]:
            samples["random"].append(jaccard_3shingles(text[a], text[b]))
    return similarity_report(samples)


def write(dataset, out):
    """Write env/, hidden/ and MANIFEST.json; returns the manifest."""
    spec = dataset["spec"]
    materialised = materialise(dataset)
    env = os.path.join(out, "env")
    os.makedirs(os.path.join(env, "incoming"), exist_ok=True)
    for name in sorted(os.listdir(os.path.join(env, "incoming"))):
        os.remove(os.path.join(env, "incoming", name))
    with open(os.path.join(env, "INSTRUCTIONS.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(spec.instructions())
    dump_jsonl(materialised["history"], os.path.join(env, "history.jsonl"))
    for record in materialised["tasks"]:
        dump_json(record, os.path.join(env, "incoming", record["tid"] + ".json"))
    if hasattr(spec, "reference_files"):
        for name, obj in spec.reference_files().items():
            dump_json(obj, os.path.join(env, name))
    if hasattr(spec, "corpus_files"):
        # A corpus dataset: plain text files under env/scenarios/<id>/...; the tree is
        # rebuilt from scratch so a renamed file does not leave its old name behind.
        scenarios_dir = os.path.join(env, "scenarios")
        if os.path.isdir(scenarios_dir):
            import shutil
            shutil.rmtree(scenarios_dir)
        for rel, text in sorted(spec.corpus_files().items()):
            path = os.path.join(env, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
    dump_json(materialised["labels"], os.path.join(out, "hidden", "labels.json"))
    dump_json(materialised["pairs"], os.path.join(out, "hidden", "pairs.json"))
    dump_json(materialised["history_meta"], os.path.join(out, "hidden", "history_meta.json"))
    if hasattr(spec, "hidden_extra"):
        for name, obj in spec.hidden_extra(materialised).items():
            dump_json(obj, os.path.join(out, "hidden", name))
    groups = env_estimate(env)
    args = dataset["args"]
    enforced = args["history_size"] <= BENCHMARK_MAX[0] and args["incoming"] <= BENCHMARK_MAX[1]
    budget_range, measured = spec.budget_for(groups, env)
    summary, table = diagnostics(dataset, materialised)
    labels = materialised["labels"]
    counts = {"history": len(materialised["history"]), "incoming": len(materialised["tasks"]),
              "duplicates": sum(1 for l in labels.values() if l["dup_of"]),
              "hard_negatives": sum(1 for l in labels.values() if l["hard_negative_of"]),
              "by_kind": {k: sum(1 for l in labels.values() if l["dup_kind"] == k) for k in DUP_KINDS},
              "dup_of_history": sum(1 for l in labels.values() if l["dup_of"] and l["dup_of"].startswith("H-")),
              "dup_of_task": sum(1 for l in labels.values() if l["dup_of"] and l["dup_of"].startswith("T-")),
              "history_twins": sum(1 for m in materialised["history_meta"].values() if m["twin_of"])}
    answers = {}
    for label in labels.values():
        key = json.dumps(label["answer"], sort_keys=True)
        answers[key] = answers.get(key, 0) + 1
    manifest = {"dataset": spec.NAME, "seed": dataset["seed"], "args": args, "counts": counts,
                "tokens": groups, "budget": {"range": budget_range, "enforced": enforced,
                                             "ok": budget_range[0] <= measured <= budget_range[1]},
                "similarity": summary, "text_for_similarity": getattr(spec, "TEXT_FOR_SIMILARITY", "see generate.py"),
                "answer_histogram": dict(sorted(answers.items(), key=lambda kv: (-kv[1], kv[0]))[:12]),
                "max_answer_share": round(max(answers.values()) / float(len(labels)), 3) if labels else 0}
    if measured != groups["total"]:
        manifest["budget"]["measured"] = measured   # a corpus dataset: the per-task figure
    if hasattr(spec, "manifest_extra"):
        manifest.update(spec.manifest_extra(dataset, materialised, env))
    dump_json(manifest, os.path.join(out, "MANIFEST.json"))
    if enforced and not manifest["budget"]["ok"]:
        raise SystemExit("token budget violated: %s tokens, expected %s-%s" % (measured, budget_range[0], budget_range[1]))
    return manifest, table


def main(spec, argv=None):
    """The argparse front end every generate.py shares."""
    parser = argparse.ArgumentParser(description="Generate the %s dataset deterministically." % spec.NAME)
    parser.add_argument("--seed", type=int, default=spec.DEFAULT_SEED)
    parser.add_argument("--dup-rate", type=float, default=spec.DEFAULT_DUP_RATE)
    parser.add_argument("--history-size", type=int, default=spec.DEFAULT_HISTORY)
    parser.add_argument("--incoming", type=int, default=spec.DEFAULT_INCOMING)
    parser.add_argument("--out", default=os.path.dirname(os.path.abspath(spec.FILE)))
    args = parser.parse_args(argv)
    dataset = build(spec, args.seed, args.history_size, args.incoming, args.dup_rate)
    manifest, table = write(dataset, args.out)
    counts, tok = manifest["counts"], manifest["tokens"]
    print("%s: %d history, %d incoming (%d duplicates = %.0f %%, %d hard negatives), seed %d" % (
        spec.NAME, counts["history"], counts["incoming"], counts["duplicates"],
        100.0 * counts["duplicates"] / max(1, counts["incoming"]), counts["hard_negatives"], args.seed))
    print("tokens (chars/4): instructions %d, history %d, incoming %d, reference %d, total %d [budget %s]" % (
        tok["instructions"], tok["history"], tok["incoming"], tok["reference"], tok["total"],
        "ok" if manifest["budget"]["ok"] else ("not enforced" if not manifest["budget"]["enforced"] else "VIOLATED")))
    print("max answer share %.2f" % manifest["max_answer_share"])
    print(table)
    return 0
