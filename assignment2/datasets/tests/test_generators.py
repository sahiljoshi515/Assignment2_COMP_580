"""Assignment 2 -- the generator contract, checked on every dataset that exists.

Concept this file teaches: a benchmark's labels are claims about its own data, and
claims get tested. Every property the assignment text promises -- determinism, the
token budget, the duplicate rate, "same item, same answer", "hard negative, different
answer", nothing hidden inside env/, a verifier that accepts every label and rejects
every twin -- is a unit test here, run against the files students receive.

Run from the repo root:
    /usr/local/bin/python3.13 -m unittest discover -s assignment2/datasets/tests -t .
"""

import filecmp
import importlib.util
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
DATASETS = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(DATASETS))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from assignment2.datasets import common, corpus  # noqa: E402

ID_RE = re.compile(r"^[HT]-[0-9a-f]{6}$")
HIDDEN_WORDS = ("dup_of", "dup_kind", "canonical_id", "hard_negative", "differs_in")


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def available():
    """Dataset directories that have a generate.py and generated env/ and hidden/ folders."""
    out = []
    for name in sorted(os.listdir(DATASETS)):
        folder = os.path.join(DATASETS, name)
        if all(os.path.exists(os.path.join(folder, p)) for p in ("generate.py", "env", "hidden", "verify.py")):
            out.append(name)
    return out


def tree_equal(a, b):
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return False
    return all(tree_equal(os.path.join(a, d), os.path.join(b, d)) for d in cmp.common_dirs)


def passed(checks):
    return all(p for p, _ in checks.values())


class GeneratorContract(unittest.TestCase):
    """One build per dataset, shared across the checks below; each check runs per dataset as a subTest."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="a2-gen-")
        cls.built = {}
        for name in available():
            gen = load_module(os.path.join(DATASETS, name, "generate.py"), "gen_" + name)
            spec = gen.SPEC
            dataset = common.build(spec, spec.DEFAULT_SEED, spec.DEFAULT_HISTORY, spec.DEFAULT_INCOMING,
                                   spec.DEFAULT_DUP_RATE)
            out = os.path.join(cls.tmp, name)
            manifest, _ = common.write(dataset, out)
            verify = load_module(os.path.join(DATASETS, name, "verify.py"), "verify_" + name)
            cls.built[name] = {"spec": spec, "dataset": dataset, "out": out, "manifest": manifest,
                               "materialised": common.materialise(dataset), "verify": verify}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def for_each(self, check):
        self.assertTrue(self.built, "no generated dataset found under assignment2/datasets")
        for name, item in self.built.items():
            with self.subTest(dataset=name):
                check(name, item)

    def test_in_place_dataset_matches_a_fresh_build(self):
        def check(name, item):
            self.assertTrue(tree_equal(os.path.join(item["out"], "env"), os.path.join(DATASETS, name, "env")),
                            "%s: committed env/ differs from a fresh build" % name)
            self.assertTrue(tree_equal(os.path.join(item["out"], "hidden"), os.path.join(DATASETS, name, "hidden")))
        self.for_each(check)

    def test_determinism_and_seed_sensitivity(self):
        def check(name, item):
            spec = item["spec"]
            again = os.path.join(self.tmp, name + "-again")
            common.write(common.build(spec, spec.DEFAULT_SEED, spec.DEFAULT_HISTORY, spec.DEFAULT_INCOMING,
                                      spec.DEFAULT_DUP_RATE), again)
            self.assertTrue(tree_equal(item["out"], again), "%s: two builds with one seed differ" % name)
            other = common.materialise(common.build(spec, spec.DEFAULT_SEED + 1, spec.DEFAULT_HISTORY,
                                                    spec.DEFAULT_INCOMING, spec.DEFAULT_DUP_RATE))
            self.assertNotEqual(sorted(other["labels"]), sorted(item["materialised"]["labels"]))
        self.for_each(check)

    def test_token_budget(self):
        def check(name, item):
            budget = item["manifest"]["budget"]
            measured = budget.get("measured", item["manifest"]["tokens"]["total"])
            low, high = budget["range"]
            self.assertTrue(low <= measured <= high, "%s: %d tokens, budget %d-%d" % (name, measured, low, high))
            if hasattr(item["spec"], "corpus_files"):
                self.assertEqual(budget["range"], list(corpus.PER_TASK_BUDGET), name)
            else:
                self.assertEqual(budget["range"], list(common.BUDGET), name)
        self.for_each(check)

    def test_duplicate_rate_tracks_the_flag(self):
        def check(name, item):
            spec = item["spec"]
            for rate in (0.0, 0.25, 0.5, 0.75):
                labels = common.materialise(common.build(spec, spec.DEFAULT_SEED, spec.DEFAULT_HISTORY,
                                                         spec.DEFAULT_INCOMING, rate))["labels"]
                n = len(labels)
                dups = sum(1 for l in labels.values() if l["dup_of"])
                self.assertLessEqual(abs(dups / float(n) - rate), 0.05, "%s at %.2f: %d/%d" % (name, rate, dups, n))
                hns = sum(1 for l in labels.values() if l["hard_negative_of"])
                target = min(int(round(common.HARD_NEGATIVE_RATE * n)), n - dups)
                self.assertGreaterEqual(hns, int(0.7 * target),
                                        "%s at %.2f: %d hard negatives, target %d" % (name, rate, hns, target))
        self.for_each(check)

    def test_duplicates_share_answer_and_follow_their_source(self):
        def check(name, item):
            spec, dataset, labels = item["spec"], item["dataset"], item["materialised"]["labels"]
            answers = {h["hid"]: (spec.answer(h["state"]["canonical"]), h["canonical_id"], -1) for h in dataset["history"]}
            answers.update({t["tid"]: (spec.answer(t["state"]["canonical"]), t["canonical_id"], t["seq"])
                            for t in dataset["tasks"]})
            for tid, label in labels.items():
                if not label["dup_of"]:
                    continue
                src_answer, src_class, src_seq = answers[label["dup_of"]]
                self.assertEqual(label["canonical_id"], src_class, "%s %s: class differs from source" % (name, tid))
                for key, value in src_answer.items():
                    self.assertEqual(label["answer"][key], value, "%s %s: answer differs from source" % (name, tid))
                self.assertLess(src_seq, label["seq"], "%s %s: source does not precede" % (name, tid))
        self.for_each(check)

    def test_hard_negatives_change_the_answer(self):
        def check(name, item):
            spec, dataset, labels = item["spec"], item["dataset"], item["materialised"]["labels"]
            canon = {h["hid"]: h["state"]["canonical"] for h in dataset["history"]}
            canon.update({t["tid"]: t["state"]["canonical"] for t in dataset["tasks"]})
            seqs = {t["tid"]: t["seq"] for t in dataset["tasks"]}
            count = 0
            for tid, label in labels.items():
                twin = label["hard_negative_of"]
                if not twin:
                    continue
                count += 1
                self.assertNotEqual(spec.answer(canon[tid]), spec.answer(canon[twin]),
                                    "%s %s: same answer as twin" % (name, tid))
                self.assertTrue(label["differs_in"], "%s %s: differs_in empty" % (name, tid))
                self.assertLess(seqs.get(twin, -1), label["seq"])
            self.assertGreater(count, 0, "%s: no hard negatives" % name)
        self.for_each(check)

    def test_validation_tuples_are_equal_within_a_class(self):
        def check(name, item):
            spec, mat, dataset = item["spec"], item["materialised"], item["dataset"]
            records = {r["hid"]: r for r in mat["history"]}
            records.update({r["tid"]: r for r in mat["tasks"]})
            classes = {h["hid"]: h["canonical_id"] for h in dataset["history"]}
            classes.update({t["tid"]: t["canonical_id"] for t in dataset["tasks"]})
            for pair in mat["pairs"]["equivalent"]:
                self.assertEqual(classes[pair["a"]], classes[pair["b"]])
                self.assertEqual(spec.validation_tuple(records[pair["a"]]), spec.validation_tuple(records[pair["b"]]),
                                 "%s: equivalent pair %s/%s has different validation tuples" % (name, pair["a"], pair["b"]))
        self.for_each(check)

    def test_nothing_hidden_leaks_into_env(self):
        def check(name, item):
            spec, mat = item["spec"], item["materialised"]
            env = os.path.join(item["out"], "env")
            for forbidden in ("hidden", "MANIFEST.json", "skills"):
                self.assertFalse(os.path.exists(os.path.join(env, forbidden)))
            ids = set()
            for record in mat["tasks"]:
                self.assertEqual(tuple(record), tuple(spec.TASK_FIELDS), "%s: task field order" % name)
                self.assertTrue(ID_RE.match(record["tid"]))
                self.assertNotIn(record["tid"], ids)
                ids.add(record["tid"])
            for record in mat["history"]:
                self.assertEqual(tuple(record), tuple(spec.HISTORY_FIELDS))
                self.assertTrue(ID_RE.match(record["hid"]))
                self.assertNotIn(record["hid"], ids)
                ids.add(record["hid"])
            classes = {t["canonical_id"] for t in item["dataset"]["tasks"]}
            for dirpath, _, files in os.walk(env):
                for file in files:
                    with open(os.path.join(dirpath, file), encoding="utf-8") as handle:
                        text = handle.read()
                    for word in HIDDEN_WORDS:
                        self.assertNotIn(word, text, "%s: %r appears in env/%s" % (name, word, file))
                    for cid in classes:
                        self.assertNotIn(cid, text)
        self.for_each(check)

    def test_stream_order(self):
        def check(name, item):
            labels = item["materialised"]["labels"]
            seqs = sorted(l["seq"] for l in labels.values())
            self.assertEqual(seqs, list(range(1, len(labels) + 1)))
            run = 0
            for label in sorted(labels.values(), key=lambda l: l["seq"]):
                run = run + 1 if label["dup_of"] else 0
                self.assertLessEqual(run, 8, "%s: more than 8 consecutive duplicates" % name)
        self.for_each(check)

    def test_verifier_accepts_labels_and_rejects_twins(self):
        def check(name, item):
            verify, labels, dataset = item["verify"], item["materialised"]["labels"], item["dataset"]
            spec = item["spec"]
            by_id = {h["hid"]: h["state"]["canonical"] for h in dataset["history"]}
            by_id.update({t["tid"]: t["state"]["canonical"] for t in dataset["tasks"]})
            for tid, label in labels.items():
                checks = verify.grade(tid, label["answer"])
                self.assertTrue(passed(checks), "%s %s: label rejected: %s" % (name, tid, common.shortfall(checks)))
                if label["hard_negative_of"]:
                    twin_answer = dict(label["answer"])
                    twin_answer.update(spec.answer(by_id[label["hard_negative_of"]]))
                    self.assertFalse(passed(verify.grade(tid, twin_answer)), "%s %s: twin's answer accepted" % (name, tid))
            some = next(iter(labels))
            for bad in ([], "text", None, {}, {"unexpected": 1}, 42):
                self.assertFalse(passed(verify.grade(some, bad)))
            self.assertFalse(passed(verify.grade("T-000000", {})))
        self.for_each(check)

    def test_similarity_bands(self):
        def check(name, item):
            sim = item["manifest"]["similarity"]

            def stat(cls, key):
                return sim[cls][key] if sim[cls]["n"] else None

            if stat("exact", "min") is not None:
                self.assertEqual(stat("exact", "min"), 1.0)
            if stat("format", "min") is not None:
                self.assertEqual(stat("format", "min"), 1.0)
            if stat("reorder", "p50") is not None:
                self.assertGreater(stat("reorder", "p50"), 0.7, name)
            if stat("edit", "p50") is not None:
                self.assertGreater(stat("edit", "p50"), 0.5, name)
            if stat("paraphrase", "p50") is not None:
                self.assertLess(stat("paraphrase", "p50"), 0.45, name)
            self.assertLessEqual(item["manifest"]["max_answer_share"], 0.35, name)
        self.for_each(check)

    def test_history_superset_keeps_incoming_fixed(self):
        def check(name, item):
            spec = item["spec"]
            if spec.MAX_HISTORY < 400:
                self.skipTest("%s has no 400-record ablation" % name)
            bigger = common.materialise(common.build(spec, spec.DEFAULT_SEED, 400, spec.DEFAULT_INCOMING,
                                                     spec.DEFAULT_DUP_RATE))
            self.assertEqual(bigger["tasks"], item["materialised"]["tasks"],
                             "%s: incoming changed with a larger history" % name)
            self.assertEqual(bigger["labels"], item["materialised"]["labels"])
            self.assertEqual(bigger["history"][:spec.DEFAULT_HISTORY], item["materialised"]["history"])
        self.for_each(check)


if __name__ == "__main__":
    unittest.main()
