"""Assignment 2 -- citations: bibliography entries verified against a reference database.

Concept this file teaches: the same paper is cited in many formats, and almost the same
citation can be a different claim. A citation's verdict is decided by hidden slots -- which
database record it cites and which of its graded fields (title, authors, venue, year, DOI)
were corrupted -- while the citation style (APA, IEEE, ACM, BibTeX), the way names are
written, pages, months and URL lines are free to vary. A duplicate changes only the free
parts; a hard negative changes one corruption (a year off by one, an initial, the preprint
cited as its conference twin) and so changes the verdict.

Design rules this file embodies:
  * The reference data is part of the environment. db.json is built once, in __init__, from
    the fixed seed "citations-db" (Spec methods never see the dataset seed) and published
    through reference_files(), so every seed of the stream verifies against the same database.
  * Answers follow a published rule the agent can apply itself: resolve by DOI when the cited
    DOI is in the database, else by normalised title; a corrupted DOI resolves by title and is
    then itself a wrong field. The generator asserts that every canonical and every flip
    resolves to exactly one record under that rule.
  * Formatting never changes the alphanumeric token sequence of `raw`. The three `fields`
    re-spellings are case and punctuation only (sentence-case title and lower-cased DOI;
    period-free initials and space-free commas). Full-vs-abbreviated venue names and the
    DOI's URL form are the third template unit (`extras`), so a paraphrase, which switches
    two of the three units, always reshapes the venue and DOI blocks or the whole template.
  * The pool is every distinct canonical, not a product: a record has at most four clean
    canonicals (DOI present or absent, "et al." or not), so about 40 % clean, 40 % one
    corrupted field and 20 % two fields caps the pool near 700 and the mix is the stream's.
  * The validation rule is all five normalised graded values: DOI or title alone is unsound,
    because the same paper cited with a different wrong field is a different verification.

Run from the repo root:  /usr/local/bin/python3.13 assignment2/datasets/citations/generate.py
"""

import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

from assignment2.datasets import common  # noqa: E402

# (full name, [abbreviations]); the first abbreviation is the one db.json records use
VENUES = [
    ("International Conference on Machine Learning", ["ICML"]),
    ("Conference on Neural Information Processing Systems", ["NeurIPS", "NIPS"]),
    ("International Conference on Learning Representations", ["ICLR"]),
    ("Annual Meeting of the Association for Computational Linguistics", ["ACL"]),
    ("Conference on Empirical Methods in Natural Language Processing", ["EMNLP"]),
    ("IEEE/CVF Conference on Computer Vision and Pattern Recognition", ["CVPR"]),
    ("IEEE/CVF International Conference on Computer Vision", ["ICCV"]),
    ("ACM SIGKDD Conference on Knowledge Discovery and Data Mining", ["KDD"]),
    ("ACM SIGIR Conference on Research and Development in Information Retrieval", ["SIGIR"]),
    ("International Conference on Very Large Data Bases", ["VLDB"]),
    ("ACM SIGMOD International Conference on Management of Data", ["SIGMOD"]),
    ("arXiv preprint", ["arXiv"]),
]
SIBLINGS = {"ICML": "NeurIPS", "NeurIPS": "ICML", "ACL": "EMNLP", "EMNLP": "ACL", "CVPR": "ICCV", "ICCV": "CVPR",
            "KDD": "SIGIR", "SIGIR": "KDD", "VLDB": "SIGMOD", "SIGMOD": "VLDB"}

SURNAMES = ["Nair", "Vik", "Bello", "Ortega", "Lin", "Berg", "Zahra", "Moretti", "Cole", "Haddad", "Rossi", "Sato",
            "Okafor", "Petrov", "Adeyemi", "Brennan", "Castillo", "Dubois", "Eriksen", "Fischer", "Garza", "Hoffmann",
            "Ibarra", "Jensen", "Kowalski", "Lindqvist", "Mendes", "Novak", "Oliveira", "Patel", "Quinn", "Ramos",
            "Schulz", "Tanaka", "Ueda", "Varga", "Weber", "Xu", "Yamada", "Zhou", "Ahmed", "Bauer", "Chen", "Delgado",
            "Evans", "Farah", "Gupta", "Huang", "Ivanova", "Jiang", "Kim", "Lopez", "Murphy", "Nakamura", "Osei",
            "Park", "Rahman", "Silva", "Torres", "Walsh"]
GIVEN = ["Priya", "Tomas", "Aisha", "Daniel", "Mei", "Jonas", "Fatima", "Luca", "Hannah", "Omar", "Sofia", "Kenji",
         "Grace", "Ivan", "Amara", "Bruno", "Chloe", "Dmitri", "Elena", "Farid", "Greta", "Hiro", "Ines", "Jamal",
         "Kavya", "Leon", "Marta", "Nikhil", "Olga", "Pablo", "Rosa", "Samir", "Tariq", "Uma", "Viktor", "Wen", "Yara",
         "Zoe", "Anders", "Beatriz"]

ADJ = ["Efficient", "Robust", "Scalable", "Sparse", "Adaptive", "Contrastive", "Hierarchical", "Lightweight",
       "Interpretable", "Federated", "Differentiable", "Compositional"]
NOUN = ["Transformers", "Graph Networks", "Mixture Models", "Attention", "Embeddings", "Diffusion Models",
        "Language Models", "Policies", "Autoencoders", "Kernels", "Indexes", "Query Plans"]
TASK = ["Node Classification", "Dense Retrieval", "Image Segmentation", "Machine Translation", "Anomaly Detection",
        "Question Answering", "Object Detection", "Link Prediction", "Time Series Forecasting", "Entity Resolution",
        "Join Optimization", "Speech Recognition"]
METHOD = ["Curriculum Learning", "Self-Supervised Pretraining", "Knowledge Distillation", "Reinforcement Learning",
          "Bayesian Optimization", "Low-Rank Adaptation", "Approximate Nearest Neighbor Search", "Prompt Tuning",
          "Spectral Clustering", "Importance Sampling", "Learned Indexing", "Cardinality Estimation"]
TITLE_PATTERNS = ["{adj} {noun} for {task}", "{task} with {adj} {noun}", "{method} for {adj} {task}"]
# the ("title", "word") corruption: one whole word of the title replaced by a near miss
TITLE_SWAPS = {"Efficient": "Effective", "Robust": "Reliable", "Scalable": "Scaled", "Sparse": "Dense",
               "Adaptive": "Adapted", "Contrastive": "Contrasting", "Hierarchical": "Hierarchic", "Lightweight": "Light",
               "Interpretable": "Explainable", "Federated": "Decentralized", "Differentiable": "Differential",
               "Compositional": "Composable", "Learning": "Training", "Networks": "Network", "Models": "Model",
               "Detection": "Recognition", "Classification": "Categorization", "Retrieval": "Search",
               "Optimization": "Optimisation", "Estimation": "Prediction", "Prediction": "Forecasting",
               "Transformers": "Transformer", "Embeddings": "Embedding", "Policies": "Policy", "Kernels": "Kernel",
               "Indexes": "Indices", "Autoencoders": "Autoencoder", "Translation": "Transduction"}

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
MONTHS_IEEE = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "Jun.", "Jul.", "Aug.", "Sep.", "Oct.", "Nov.", "Dec."]
MONTHS_BIB = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
STYLES = ["apa", "ieee", "acm", "bibtex"]
NAME_FORMS = ["given_first", "surname_first", "initial_first", "surname_initial"]
# the "extras" unit: how the venue and the DOI are written; every variant differs from every other in both
EXTRAS = [{"venue": "full", "doi": "url"}, {"venue": "abbrev", "doi": "label"},
          {"venue": "abbrev_proc", "doi": "bare"}, {"venue": "abbrev_yy", "doi": "dx"}]
CLEAN_WITHOUT_DOI = 0.45  # share of records whose clean canonical also exists without a DOI (-> ~70 % carry one)
PUBLISHER = {"ICML": "PMLR", "NeurIPS": "Curran Associates", "ICLR": "OpenReview.net",
             "ACL": "Association for Computational Linguistics", "EMNLP": "Association for Computational Linguistics",
             "CVPR": "IEEE", "ICCV": "IEEE", "KDD": "ACM", "SIGIR": "ACM", "VLDB": "VLDB Endowment", "SIGMOD": "ACM"}
PUBLISHER_PLACE = {"PMLR": "PMLR", "Curran Associates": "Curran Associates, Inc., Red Hook, NY, USA",
                   "OpenReview.net": "OpenReview.net", "IEEE": "IEEE Computer Society, Los Alamitos, CA, USA",
                   "Association for Computational Linguistics": "Association for Computational Linguistics, Stroudsburg, PA, USA",
                   "ACM": "ACM, New York, NY, USA", "VLDB Endowment": "VLDB Endowment"}
ONE_TOKEN = {("year", "+1"), ("year", "-1"), ("authors", "initial"), ("authors", "spelling"), ("title", "word"),
             ("doi", "hex")}       # flips that move a single token of `raw`; the others move several

DB_SIZE = 150
TWIN_PAIRS = 15          # arXiv / conference versions of one paper: same title and authors
LONE_ARXIV = 6           # arXiv records without a conference version
DOI_SHARE = 0.70         # share of canonicals that carry the DOI (twins always do)
YEARS = (2015, 2025)
AUTHOR_COUNTS = [2, 3, 3, 3, 4, 4]


# ---------------------------------------------------------------------------
# the reference database
# ---------------------------------------------------------------------------
def build_db(rng):
    """venues + records, deterministic from `rng`; titles unique except within a twin pair."""
    venues = [{"name": name, "abbrev": list(abbrevs)} for name, abbrevs in VENUES]
    conferences = [abbrevs[0] for _, abbrevs in VENUES if abbrevs[0] != "arXiv"]
    records, titles, dois = [], set(), set()
    pairs = {}                                   # record index -> twin index, both directions

    def fresh_title():
        while True:
            pattern = common.pick(rng, TITLE_PATTERNS)
            title = pattern.format(adj=common.pick(rng, ADJ), noun=common.pick(rng, NOUN),
                                   task=common.pick(rng, TASK), method=common.pick(rng, METHOD))
            if common.norm_title(title) not in titles:
                titles.add(common.norm_title(title))
                return title

    def fresh_authors():
        count = common.pick(rng, AUTHOR_COUNTS)
        surnames = rng.sample(SURNAMES, count)
        return ["%s %s" % (common.pick(rng, GIVEN), surname) for surname in surnames]

    def conference_doi(venue, year):
        while True:
            doi = "10.5555/%s.%d.%04x" % (venue.lower(), year, rng.getrandbits(16))
            if doi not in dois:
                dois.add(doi)
                return doi

    def arxiv_doi(year):
        while True:
            doi = "10.48550/arXiv.%02d%02d.%05d" % (year % 100, rng.randrange(1, 13), rng.randrange(100000))
            if doi not in dois:
                dois.add(doi)
                return doi

    def pages():
        start = rng.randrange(1, 9000)
        return "%d-%d" % (start, start + rng.randrange(6, 15))

    n_conference = DB_SIZE - TWIN_PAIRS - LONE_ARXIV
    for i in range(n_conference):
        venue, year = common.pick(rng, conferences), rng.randrange(YEARS[0], YEARS[1] + 1)
        record = {"doi": conference_doi(venue, year), "title": fresh_title(), "authors": fresh_authors(),
                  "venue": venue, "year": year}
        if rng.random() < 0.85:
            record["pages"] = pages()
        records.append(record)
        if i < TWIN_PAIRS:                         # the first conference records get a preprint twin, a year earlier
            records.append({"doi": arxiv_doi(year - 1), "title": record["title"], "authors": list(record["authors"]),
                            "venue": "arXiv", "year": year - 1})
    for _ in range(LONE_ARXIV):
        year = rng.randrange(YEARS[0], YEARS[1] + 1)
        records.append({"doi": arxiv_doi(year), "title": fresh_title(), "authors": fresh_authors(),
                        "venue": "arXiv", "year": year})
    assert len(records) == DB_SIZE, len(records)
    order = list(range(len(records)))
    rng.shuffle(order)
    position = {old: new for new, old in enumerate(order)}
    shuffled = [records[old] for old in order]
    for i in range(TWIN_PAIRS):                   # conference record 2i sits right before its twin 2i+1
        a, b = position[2 * i], position[2 * i + 1]
        pairs[a], pairs[b] = b, a
    return {"venues": venues, "records": shuffled}, pairs


def venue_aliases(db):
    """Normalised full name or abbreviation -> the canonical abbreviation."""
    table = {}
    for venue in db["venues"]:
        table[common.norm_text(venue["name"])] = venue["abbrev"][0]
        for abbrev in venue["abbrev"]:
            table[common.norm_text(abbrev)] = venue["abbrev"][0]
    return table


def norm_venue(aliases, venue):
    return aliases.get(common.norm_text(venue), common.norm_text(venue))


def authors_match(cited, expected):
    """The published author rule: (surname, initial) pairs in order; 'et al.' after >= 3 when the record has >= 4."""
    cited = [str(a) for a in cited]
    if cited and common.norm_text(cited[-1]) == "et al":
        listed = cited[:-1]
        if len(listed) < 3 or len(expected) < 4 or len(listed) > len(expected):
            return False
        return [common.norm_author(a) for a in listed] == [common.norm_author(a) for a in expected[:len(listed)]]
    return [common.norm_author(a) for a in cited] == [common.norm_author(a) for a in expected]


def judge(db, aliases, citation):
    """The published rule: (record index, sorted wrong fields); raises if the title resolves to != 1 record."""
    records = db["records"]
    doi = common.norm_doi(citation.get("doi", ""))
    by_doi = [i for i, r in enumerate(records) if common.norm_doi(r["doi"]) == doi] if doi else []
    if by_doi:
        index = by_doi[0]
    else:
        by_title = [i for i, r in enumerate(records) if common.norm_title(r["title"]) == common.norm_title(citation["title"])]
        if len(by_title) != 1:
            raise ValueError("title %r resolves to %d records" % (citation["title"], len(by_title)))
        index = by_title[0]
    record = records[index]
    wrong = []
    if common.norm_title(citation["title"]) != common.norm_title(record["title"]):
        wrong.append("title")
    if not authors_match(citation["authors"], record["authors"]):
        wrong.append("authors")
    if norm_venue(aliases, citation["venue"]) != record["venue"]:
        wrong.append("venue")
    if str(citation["year"]) != str(record["year"]):
        wrong.append("year")
    if doi and doi != common.norm_doi(record["doi"]):
        wrong.append("doi")
    return index, sorted(wrong)


# ---------------------------------------------------------------------------
# corruptions, rendering helpers
# ---------------------------------------------------------------------------
def misspell(rng, word):
    """A surname with one letter swapped, dropped or doubled; always normalises differently."""
    options = []
    for i in range(1, len(word) - 1):
        if word[i] != word[i + 1]:
            options.append(word[:i] + word[i + 1] + word[i] + word[i + 2:])
        options.append(word[:i] + word[i + 1:])
    options += [word[:i] + word[i] + word[i:] for i in range(1, len(word))]
    options = sorted({o for o in options if common.norm_text(o) != common.norm_text(word)})
    return common.pick(rng, options) if options else word + "e"


def corrupt_doi(rng, doi, taken):
    """One character of the DOI's suffix changed; never another record's DOI."""
    alphabet = "0123456789" if "arXiv" in doi else "0123456789abcdef"
    head, tail = doi.rsplit(".", 1)
    while True:
        i = rng.randrange(len(tail))
        char = common.pick(rng, [c for c in alphabet if c != tail[i]])
        candidate = "%s.%s%s%s" % (head, tail[:i], char, tail[i + 1:])
        if common.norm_doi(candidate) not in taken:
            return candidate


def swap_title_word(rng, title):
    words = title.split(" ")
    slots = [i for i, w in enumerate(words) if w in TITLE_SWAPS]
    i = common.pick(rng, slots)
    words[i] = TITLE_SWAPS[words[i]]
    return " ".join(words)


def render_name(name, form):
    if common.norm_text(name) == "et al":
        return name
    given, surname = name.split(" ", 1)
    if form == "given_first":
        return "%s %s" % (given, surname)
    if form == "surname_first":
        return "%s, %s" % (surname, given)
    if form == "initial_first":
        return "%s. %s" % (given[0], surname)
    return "%s, %s." % (surname, given[0])


def join_names(names, conjunction):
    """'A, B, and C' / 'A and B' / 'A, B, C, et al.' -- the author strings appear verbatim."""
    if names and common.norm_text(names[-1]) == "et al":
        return ", ".join(names)
    if len(names) <= 1:
        return "".join(names)
    if len(names) == 2:
        return "%s %s %s" % (names[0], conjunction, names[1])
    return "%s, %s %s" % (", ".join(names[:-1]), conjunction, names[-1])


def end(text, mark="."):
    """Append a full stop unless the text already ends with one ('et al.' / 'Nair, P.')."""
    return text if text.endswith(mark) else text + mark


def sentence_case(title):
    words = title.split(" ")
    return " ".join([words[0]] + [w.lower() for w in words[1:]])


def compact_name(name):
    """'P. Nair' -> 'P Nair', 'Nair, P.' -> 'Nair,P', 'Nair, Priya' -> 'Nair,Priya'; same tokens."""
    name = re.sub(r"\b([A-Z])\. ", r"\1 ", name)
    name = re.sub(r"\b([A-Z])\.$", r"\1", name)
    return name.replace(", ", ",")


class CitationsSpec(common.Spec):
    NAME = "citations"
    FILE = __file__
    HISTORY_FIELDS = ("hid", "verdict", "citation", "raw", "filed")
    TASK_FIELDS = ("tid", "seq", "citation", "raw", "received")
    DATE_FIELD = "filed"
    TASK_DATE_FIELD = "received"
    UNITS = ("style", "name_form", "extras")
    VARIANTS = 4                      # four citation styles, four name forms, four extras combinations
    SYNONYMS = {}                     # nothing to paraphrase in a citation: the style change is the paraphrase
    MAX_HISTORY = 160
    MAX_INCOMING = 80
    REORDERABLE = False               # no sections: reorder permutes BibTeX fields / trailing extras in compose()
    DEFAULT_SEED = 53
    DEFAULT_DUP_RATE = 0.40
    DEFAULT_HISTORY = 140
    DEFAULT_INCOMING = 70
    TEXT_FOR_SIMILARITY = "raw"

    def __init__(self):
        self.db, self.twin_of = build_db(common.sub_rng("citations-db", "db"))
        self.records = self.db["records"]
        self.aliases = venue_aliases(self.db)
        self.doi_set = {common.norm_doi(r["doi"]) for r in self.records}
        self.venue_name = {abbrevs[0]: name for name, abbrevs in VENUES}
        self.venue_abbrevs = {abbrevs[0]: list(abbrevs) for _, abbrevs in VENUES}
        self._pool = self._enumerate_pool(common.sub_rng("citations-pool"))

    # -- the canonical pool ------------------------------------------------------------------
    def _applicable(self, record, has_doi, twin):
        """Every (field, variant) corruption this record admits under the has_doi / twin constraints."""
        options = [["year", "+1"], ["year", "-1"], ["authors", "initial"], ["authors", "spelling"],
                   ["authors", "dropped"], ["authors", "swapped"]]
        if record["venue"] in SIBLINGS:
            options.append(["venue", "sibling"])
        if has_doi:                                   # the title is never corrupted when the DOI is absent
            options.append(["title", "word"])
        if has_doi and not twin:                      # a twin's corrupted DOI would resolve by an ambiguous title
            options.append(["doi", "hex"])
        return options

    def _enumerate_pool(self, rng):
        """record x seeded corruption signatures: about 40 % clean, 40 % one field, 20 % two fields."""
        pool, seen = [], set()

        def add(canonical):
            key = common.canonical_key(canonical)
            if key in seen:
                return False
            seen.add(key)
            pool.append(canonical)
            return True

        for index, record in enumerate(self.records):
            twin = index in self.twin_of
            etal_options = [False, True] if len(record["authors"]) >= 4 else [False]
            doi_options = [True] if twin or rng.random() >= CLEAN_WITHOUT_DOI else [True, False]
            clean = [(d, e) for d in doi_options for e in etal_options]
            # a preprint twin enters the pool only corrupted: its clean citation is reached by the
            # twin flip from the conference version, which keeps that hard negative legal
            if not (twin and record["venue"] == "arXiv"):
                for has_doi, etal in clean:
                    add({"record": index, "corruption": [], "has_doi": has_doi, "etal": etal})
            for count, k in ((len(clean), 1), (max(1, len(clean) // 2), 2)):
                made, attempts = 0, 0
                while made < count and attempts < 60:
                    attempts += 1
                    has_doi = True if twin else rng.random() < DOI_SHARE
                    etal = len(record["authors"]) >= 4 and rng.random() < 0.5
                    options = self._applicable(record, has_doi, twin)
                    fields = sorted({field for field, _ in options})
                    rng.shuffle(fields)
                    chosen = fields[:k]
                    if "doi" in chosen and "title" in chosen:
                        continue
                    corruption = sorted(common.pick(rng, [o for o in options if o[0] == field]) for field in chosen)
                    if add({"record": index, "corruption": corruption, "has_doi": has_doi, "etal": etal}):
                        made += 1
        rng.shuffle(pool)
        return pool

    def pool_size(self):
        return len(self._pool)

    def canonical_at(self, k):
        return json.loads(json.dumps(self._pool[k]))

    # -- answers and flips -----------------------------------------------------------------------
    def answer(self, canonical):
        record = self.records[canonical["record"]]
        wrong = sorted({field for field, _ in canonical["corruption"]})
        return {"doi": record["doi"], "status": "correct" if not wrong else "incorrect", "wrong_fields": wrong}

    def history_answer_fields(self, answer):
        """History records nest the flat answer under `verdict`; labels and the verifier see it flat."""
        return {"verdict": dict(answer)}

    def flip(self, rng, canonical):
        """The arXiv/conference twin first when the record has one, then one-token flips
        (shuffled), then several-token flips.

        The twin flip keeps title and authors but changes venue, year and DOI: the same paper,
        the other record. Its clean form is often consumed by an earlier flip, so the twin with
        one added one-token corruption follows as a fallback. A one-token flip (year, initial,
        spelling, title word, DOI digit) keeps `raw` almost identical.
        """
        record = self.records[canonical["record"]]
        twin = self.twin_of.get(canonical["record"])
        present = sorted({field for field, _ in canonical["corruption"]})

        def with_corruption(corruption):
            return {"record": canonical["record"], "corruption": sorted(corruption),
                    "has_doi": canonical["has_doi"], "etal": canonical["etal"]}

        one_token, several = [], []
        options = self._applicable(record, canonical["has_doi"], twin is not None)
        for field in sorted({field for field, _ in options}):
            if field in present or len(present) >= 2:
                continue
            if ("doi" in present and field == "title") or ("title" in present and field == "doi"):
                continue
            variant = common.pick(rng, [o for o in options if o[0] == field])
            group = one_token if tuple(variant) in ONE_TOKEN else several
            group.append(with_corruption(canonical["corruption"] + [variant]))
        for field, variant in canonical["corruption"]:
            group = one_token if (field, variant) in ONE_TOKEN else several
            group.append(with_corruption([p for p in canonical["corruption"] if p[0] != field]))
        rng.shuffle(one_token)
        rng.shuffle(several)
        twins = []
        if twin is not None:
            twin_record = self.records[twin]
            keep = [p for p in canonical["corruption"]
                    if p[0] != "doi" and not (p[0] == "venue" and twin_record["venue"] == "arXiv")]
            twins.append({"record": twin, "corruption": sorted(keep), "has_doi": True, "etal": canonical["etal"]})
            fallbacks = []
            for variant in self._applicable(twin_record, True, True):
                if tuple(variant) in ONE_TOKEN and variant[0] not in {p[0] for p in keep} and len(keep) < 2:
                    fallbacks.append({"record": twin, "corruption": sorted(keep + [variant]), "has_doi": True,
                                      "etal": canonical["etal"]})
            rng.shuffle(fallbacks)
            twins += fallbacks
        return twins + one_token + several

    # -- what the citation says --------------------------------------------------------------
    def cited_values(self, canonical):
        """The graded values as cited: the record's, with the canonical's corruptions applied."""
        record = self.records[canonical["record"]]
        authors = list(record["authors"])
        title, venue, year, doi = record["title"], record["venue"], record["year"], record["doi"]
        visible = 3 if canonical["etal"] else len(authors)
        for field, variant in canonical["corruption"]:
            # seeded per (record, etal, field, variant): a flip of another slot keeps this one's rendering
            rng = common.sub_rng("citations-corrupt", canonical["record"], canonical["etal"], field, variant)
            if field == "year":
                year += 1 if variant == "+1" else -1
            elif field == "authors":
                if variant == "initial":
                    i = rng.randrange(visible)
                    given, surname = authors[i].split(" ", 1)
                    authors[i] = "%s %s" % (common.pick(rng, [g for g in GIVEN if g[0] != given[0]]), surname)
                elif variant == "spelling":
                    i = rng.randrange(visible)
                    given, surname = authors[i].split(" ", 1)
                    authors[i] = "%s %s" % (given, misspell(rng, surname))
                elif variant == "dropped":
                    del authors[rng.randrange(visible)]
                else:
                    i = rng.randrange(visible - 1)
                    authors[i], authors[i + 1] = authors[i + 1], authors[i]
            elif field == "venue":
                venue = SIBLINGS[venue]
            elif field == "title":
                title = swap_title_word(rng, title)
            else:
                doi = corrupt_doi(rng, doi, self.doi_set)
        if canonical["etal"]:
            authors = authors[:3] + ["et al."]
        return {"authors": authors, "title": title, "venue": venue, "year": year,
                "doi": doi if canonical["has_doi"] else None, "pages": record.get("pages")}

    def cosmetic(self, rng):
        """Presence of pages, a month and a URL line, plus the small spellings an edit may re-roll."""
        return {"show_pages": rng.random() < 0.8, "month": rng.randrange(12) if rng.random() < 0.5 else None,
                "url": rng.random() < 0.35, "paper_no": rng.randrange(100, 1000), "alias": rng.randrange(2),
                "key_form": rng.randrange(2), "conj": rng.randrange(2), "pages_label": rng.randrange(2)}

    def compose(self, state):
        c, v, cos = state["canonical"], state["variants"], state["cosmetic"]
        cited = self.cited_values(c)
        style, form, extras = STYLES[v["style"]], NAME_FORMS[v["name_form"]], EXTRAS[v["extras"]]
        names = [render_name(a, form) for a in cited["authors"]]
        abbrevs = self.venue_abbrevs[cited["venue"]]
        abbrev = abbrevs[cos["alias"] % len(abbrevs)]
        full_name = self.venue_name[cited["venue"]]
        arxiv = cited["venue"] == "arXiv"
        pages = cited["pages"] if cited["pages"] and cos["show_pages"] else None
        url = None
        if cos["url"]:
            if arxiv:
                url = "https://arxiv.org/abs/%s" % cited["doi"].split("arXiv.")[1] if cited["doi"] else \
                    "https://arxiv.org/abs/%02d%02d.%05d" % (cited["year"] % 100, cos["paper_no"] % 12 + 1, cos["paper_no"] * 37)
            else:
                url = "https://proceedings.example.org/%s/%d" % (abbrev.lower(), cos["paper_no"])
        venue = full_name if extras["venue"] == "full" and not arxiv else abbrev
        citation = {"authors": names, "title": cited["title"], "venue": "arXiv preprint" if arxiv else venue,
                    "year": cited["year"]}
        if cited["doi"]:
            citation["doi"] = cited["doi"]
        if pages:
            citation["pages"] = pages
        parts = {"names": names, "abbrev": abbrev, "full": full_name, "arxiv": arxiv, "month": cos["month"],
                 "url": url, "doi_form": extras["doi"], "venue_form": extras["venue"], "order": state.get("order")}
        raw = self._render_raw(style, citation, parts, cos)
        return {"fields": {"citation": citation, "raw": raw}, "title": "", "sections": []}

    def _venue_text(self, style, p, year):
        """The venue block per style and extras form; forms differ in their token sequence."""
        if p["arxiv"]:
            return "arXiv preprint"
        abbrev, full, form, yy = p["abbrev"], p["full"], p["venue_form"], year % 100
        if style == "apa":
            table = {"full": "In Proceedings of the %s" % full, "abbrev": "In Proceedings of %s" % abbrev,
                     "abbrev_proc": "In Proc. of %s" % abbrev, "abbrev_yy": "In %s '%02d" % (abbrev, yy)}
        elif style == "ieee":
            table = {"full": "in Proc. %s" % full, "abbrev": "in Proc. %s" % abbrev,
                     "abbrev_proc": "in Proceedings of %s" % abbrev, "abbrev_yy": "in Proc. %s '%02d" % (abbrev, yy)}
        elif style == "acm":
            table = {"full": "In %s (%s '%02d)" % (full, abbrev, yy), "abbrev": "In %s" % abbrev,
                     "abbrev_proc": "In Proc. %s" % abbrev, "abbrev_yy": "In %s '%02d" % (abbrev, yy)}
        else:
            table = {"full": "Proceedings of the %s" % full, "abbrev": abbrev,
                     "abbrev_proc": "Proc. of %s" % abbrev, "abbrev_yy": "Proc. %s '%02d" % (abbrev, yy)}
        return table[form]

    def _doi_text(self, style, p, doi):
        """The DOI block per style and extras form (BibTeX knows only doi = {} and url = {})."""
        if not doi:
            return "" if style != "bibtex" else None
        form = p["doi_form"]
        url, dx = "https://doi.org/%s" % doi, "http://dx.doi.org/%s" % doi
        if style == "bibtex":
            return {"url": ("url", url), "label": ("doi", doi), "bare": ("doi", doi), "dx": ("url", dx)}[form]
        if style == "apa":
            return {"url": " " + url, "label": " doi:%s" % doi, "bare": " " + doi, "dx": " " + dx}[form]
        if style == "ieee":
            return {"url": ", " + url, "label": ", doi: %s" % doi, "bare": ", " + doi, "dx": ", " + dx}[form]
        return {"url": " " + url, "label": " DOI:%s" % doi, "bare": " " + doi, "dx": " DOI:%s" % dx}[form]

    def _render_raw(self, style, citation, p, cos):
        """One citation string per style; every author string of the object appears verbatim."""
        title, year, doi, pages = citation["title"], citation["year"], citation.get("doi"), citation.get("pages")
        names, month, url, arxiv = p["names"], p["month"], p["url"], p["arxiv"]
        conj = ["and", "&"][cos["conj"]]
        pages_label = ["pp. ", "pages "][cos["pages_label"]]
        venue = self._venue_text(style, p, year)
        doi_text = self._doi_text(style, p, doi)
        publisher = "" if arxiv else PUBLISHER[p["abbrev"] if p["abbrev"] in PUBLISHER else self._canonical_abbrev(p["abbrev"])]
        if style == "apa":
            date = "(%d, %s)" % (year, MONTHS[month]) if month is not None else "(%d)" % year
            tail = [doi_text, " Retrieved from %s" % url if url else ""]
            if p["order"] == "derange":
                tail.reverse()
            return "%s %s. %s. %s%s.%s%s" % (join_names(names, conj), date, title, venue,
                                            " (%s%s)" % (pages_label, pages) if pages else "",
                                            " %s." % publisher if publisher else "", "".join(tail))
        if style == "ieee":
            date = "%s %d" % (MONTHS_IEEE[month], year) if month is not None else "%d" % year
            tail = [", %s%s" % (pages_label, pages) if pages else "", doi_text]
            if p["order"] == "derange":
                tail.reverse()
            return '%s, "%s," %s, %s%s.%s' % (join_names(names, conj), title, venue, date, "".join(tail),
                                              " [Online]. Available: %s" % url if url else "")
        if style == "acm":
            date = "%s %d" % (MONTHS[month], year) if month is not None else "%d" % year
            tail = [doi_text, " %s" % url if url else ""]
            if p["order"] == "derange":
                tail.reverse()
            where = venue + ("." if not publisher else ". %s" % PUBLISHER_PLACE[publisher])
            if pages:
                where += ", %s%s" % (pages_label if cos["pages_label"] else "", pages)
            return "%s %s. %s. %s%s" % (end(join_names(names, conj)), date, title, end(where), "".join(tail))
        first_surname = citation["authors"][0].split(",")[0].split(" ")[-1].lower() if citation["authors"] else "anon"
        first_word = title.split(" ")[0].lower()
        key = "%s%d%s" % (first_surname, year, first_word) if cos["key_form"] == 0 else "%s:%s" % (first_surname, first_word)
        plain = [n for n in names if common.norm_text(n) != "et al"]
        author = " and ".join(plain) + (" and others" if len(plain) < len(names) else "")
        where = ("journal", venue) if arxiv else ("booktitle", venue)
        fields = [("author", author), ("title", title), where, ("year", str(year))]
        if publisher:
            fields.append(("publisher", publisher))
        if month is not None:
            fields.append(("month", MONTHS_BIB[month]))
        if pages:
            fields.append(("pages", pages.replace("-", "--")))
        if doi_text:
            fields.append(doi_text)
        if url:
            fields.append(("note", "Available at %s" % url))
        if p["order"] == "derange":
            fields = common.derange(random.Random("order/%s" % key), fields)
        return "@%s{%s,\n%s}" % ("article" if arxiv else "inproceedings", key,
                                 "".join("  %s = {%s},\n" % (name, value) for name, value in fields))

    def _canonical_abbrev(self, abbrev):
        return self.aliases[common.norm_text(abbrev)]

    def recase_fields(self, fields, style):
        """Case and punctuation only, so the alphanumeric token sequence of `raw` never changes."""
        citation, raw = dict(fields["citation"]), fields["raw"]
        if style["fields"] == "lower":
            new_title = sentence_case(citation["title"])
            raw = raw.replace(citation["title"], new_title)
            citation["title"] = new_title
            if "doi" in citation:
                raw = raw.replace(citation["doi"], citation["doi"].lower()).replace("DOI:", "doi:")
                citation["doi"] = citation["doi"].lower()
        elif style["fields"] == "compact":
            for name in sorted(citation["authors"], key=len, reverse=True):
                if compact_name(name) != name:
                    raw = raw.replace(name, compact_name(name))
            citation["authors"] = [compact_name(name) for name in citation["authors"]]
            raw = raw.replace("pp. ", "pp.")
        fields["citation"], fields["raw"] = citation, raw
        return fields

    def protected(self, state):
        cited = self.cited_values(state["canonical"])
        words = [a.split(" ")[-1] for a in cited["authors"]] + self.venue_name[cited["venue"]].split()
        return words + self.venue_abbrevs[cited["venue"]] + [str(cited["year"])] + ([cited["doi"]] if cited["doi"] else [])

    def validation_tuple(self, record):
        c = record["citation"]
        return (common.norm_doi(c.get("doi", "")), common.norm_title(c["title"]),
                tuple(common.norm_author(a) for a in c["authors"]), norm_venue(self.aliases, c["venue"]), str(c["year"]))

    def text_for_similarity(self, record):
        return record["raw"]

    def reference_files(self):
        return {"db.json": self.db}

    def instructions(self):
        lines = ["# Citation verification", "",
                 "You verify citation metadata against a reference database. One citation is in `task.json`; your",
                 "job is to check its five graded fields against the record it cites in `db.json` and write the",
                 "verdict to `answer.json`.", "",
                 "## Files in this directory", "",
                 "- `INSTRUCTIONS.md`: this file.",
                 "- `db.json`: the reference data. `venues` lists every venue as `{\"name\", \"abbrev\": [...]}`;",
                 "  `records` lists every known paper as `{\"doi\", \"title\", \"authors\", \"venue\", \"year\"}` plus `pages`",
                 "  where known. `authors` are \"Given Surname\" strings in order; `venue` is the first listed abbreviation.",
                 "- `history.jsonl`: one JSON object per line, every one a verified citation: fields `hid`, `verdict`",
                 "  (the verified answer: `{\"doi\", \"status\", \"wrong_fields\"}`), `citation`, `raw`, `filed`.",
                 "- `task.json`: the citation to verify: `tid`, `seq`, `citation`, `raw`, `received`.", "",
                 "`citation` is the structured form: `authors` (a list, possibly ending in \"et al.\"), `title`, `venue`,",
                 "`year`, and `doi` and `pages` when the citing text gave them. `raw` is the same citation as it appeared",
                 "in print (APA, IEEE, ACM or BibTeX form). The two always agree, so grade the structured form.", "",
                 "`history.jsonl` contains verified answers. If `task.json` describes the same underlying item as a",
                 "history record (the same citation, not merely a similar one), you may reuse that record's answer.",
                 "Before you do, check the fields under Validation below; near-identical records with a different",
                 "value there are different items with different answers.", "",
                 "## The five graded fields", "",
                 "- `title`: correct when the alphanumeric tokens agree, case-insensitively; punctuation and",
                 "  capitalisation are free.",
                 "- `authors`: compared as (surname, first initial) pairs, in order. \"Priya Nair\", \"Nair, Priya\",",
                 "  \"P. Nair\" and \"Nair, P.\" are one author. A trailing \"et al.\" is correct only after three or more",
                 "  correct authors when the record has four or more authors. A missing, extra, misspelled or",
                 "  reordered author is wrong.",
                 "- `venue`: the record's venue written as its full name or as any abbreviation listed under `venues`,",
                 "  case-insensitively (NIPS and NeurIPS are the same venue).",
                 "- `year`: exact.",
                 "- `doi`: case-insensitive, with or without a `doi:` label or `https://doi.org/` prefix. A citation that",
                 "  gives no DOI is not wrong on `doi`.", "",
                 "## Resolving the cited record", "",
                 "1. If the citation carries a DOI and that DOI (normalised as above) belongs to a record in `db.json`,",
                 "   it cites that record.",
                 "2. Otherwise it cites the record whose normalised title equals the cited title. A DOI that is not in",
                 "   `db.json` is a wrong DOI: resolve by title and report `doi` among the wrong fields.", "",
                 "`wrong_fields` is the sorted list of graded fields whose cited value differs from the record;",
                 "`status` is `correct` when that list is empty and `incorrect` otherwise; `doi` is the resolved",
                 "record's DOI, which is the cited one unless the cited one was wrong.", "",
                 "## How to verify a fresh citation", "",
                 "- Normalise the cited DOI and look it up; if it is absent or unknown, look the title up instead.",
                 "- Compare the five fields with the rules above. Pages, months, URL lines, the citation style and the",
                 "  way names are written carry no information.",
                 "- The same paper can exist twice, as a preprint and as a conference paper, with the same title and",
                 "  authors but a different venue, year and DOI. The cited DOI decides which version is cited; grade",
                 "  against that version only.",
                 "- Grade what was cited; never repair the citation first.", "",
                 "Worked example: `{\"authors\": [\"Nair, P.\", \"Vik, T.\"], \"title\": \"Efficient Transformers for Dense",
                 "Retrieval\", \"venue\": \"ICML\", \"year\": 2022, \"doi\": \"10.5555/icml.2021.a3f9\"}` with a record",
                 "`{\"doi\": \"10.5555/icml.2021.a3f9\", \"title\": \"Efficient Transformers for Dense Retrieval\", \"authors\":",
                 "[\"Priya Nair\", \"Tomas Vik\"], \"venue\": \"ICML\", \"year\": 2021}` resolves by DOI; title, authors, venue",
                 "and DOI agree, the year does not, so the verdict is `{\"doi\": \"10.5555/icml.2021.a3f9\", \"status\":",
                 "\"incorrect\", \"wrong_fields\": [\"year\"]}`.", "",
                 "## Validation (when is a history record the same citation?)", "",
                 "A history record is the same citation only when all five normalised graded values are equal: DOI",
                 "(empty when absent), title, author pairs, venue abbreviation and year. DOI or title alone is unsound:",
                 "the same paper cited with a different wrong field is a different verification with a different",
                 "verdict.", "",
                 "## Output", "",
                 "Write `answer.json` in this directory:", "", "```json",
                 '{"doi": "10.5555/icml.2021.a3f9", "status": "incorrect", "wrong_fields": ["year"]}', "```", "",
                 "`status` is `correct` or `incorrect` in lower case; `wrong_fields` names come from `title`, `authors`,",
                 "`venue`, `year`, `doi` and the list is empty when the status is `correct`. Extra keys are ignored.", "",
                 "## Rules", "",
                 "- Do not modify `db.json`, `history.jsonl` or `task.json`; write nothing except `answer.json`.",
                 "- Only `answer.json` is graded. Your final message is not."]
        return "\n".join(lines) + "\n"

    # -- self-checks: every canonical and every flip resolves to its record under the published rule
    def check_canonical(self, canonical):
        cited = self.cited_values(canonical)
        citation = {"authors": cited["authors"], "title": cited["title"], "venue": cited["venue"], "year": cited["year"]}
        if cited["doi"]:
            citation["doi"] = cited["doi"]
            if canonical["record"] in self.twin_of or not any(f == "doi" for f, _ in canonical["corruption"]):
                assert common.norm_doi(cited["doi"]) in self.doi_set
            else:
                assert common.norm_doi(cited["doi"]) not in self.doi_set, "corrupted DOI collides with a record"
        index, wrong = judge(self.db, self.aliases, citation)
        expected = self.answer(canonical)["wrong_fields"]
        assert index == canonical["record"], (canonical, index)
        assert wrong == expected, (canonical, wrong, expected)

    def self_check(self):
        for k in range(self.pool_size()):
            canonical = self.canonical_at(k)
            self.check_canonical(canonical)
            for flipped in self.flip(random.Random("check/%d" % k), canonical):
                self.check_canonical(flipped)
        twins = sum(1 for i in self.twin_of if self.records[i]["venue"] == "arXiv")
        assert twins == TWIN_PAIRS, twins
        return self.pool_size()


def check_written(spec, out):
    """Re-read env/ and hidden/: the visible citation of every record must grade to its verdict."""
    env = os.path.join(out, "env")
    labels = json.load(open(os.path.join(out, "hidden", "labels.json"), encoding="utf-8"))
    checked = 0
    for record in common.load_jsonl(os.path.join(env, "history.jsonl")):
        index, wrong = judge(spec.db, spec.aliases, record["citation"])
        verdict = record["verdict"]
        assert verdict == {"doi": spec.records[index]["doi"], "status": "correct" if not wrong else "incorrect",
                           "wrong_fields": wrong}, record["hid"]
        checked += 1
    for name in sorted(os.listdir(os.path.join(env, "incoming"))):
        record = json.load(open(os.path.join(env, "incoming", name), encoding="utf-8"))
        index, wrong = judge(spec.db, spec.aliases, record["citation"])
        expected = labels[record["tid"]]["answer"]
        assert expected == {"doi": spec.records[index]["doi"], "status": "correct" if not wrong else "incorrect",
                            "wrong_fields": wrong}, record["tid"]
        checked += 1
    return checked


SPEC = CitationsSpec()

if __name__ == "__main__":
    pool = SPEC.self_check()
    status = common.main(SPEC)
    out = os.path.dirname(os.path.abspath(__file__))
    for i, arg in enumerate(sys.argv[1:], 1):
        if arg == "--out" and i < len(sys.argv) - 1:
            out = sys.argv[i + 1]
        elif arg.startswith("--out="):
            out = arg.split("=", 1)[1]
    print("self-check: %d pool canonicals and their flips resolve under the rule; %d written records re-graded" % (
        pool, check_written(SPEC, out)))
    sys.exit(status)
