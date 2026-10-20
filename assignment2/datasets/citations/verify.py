"""Assignment 2 -- citations/verify.py: is the verdict in answer.json the verified one?

Concept this file teaches: a verdict has three parts that must agree with each other and
with the label. The resolved DOI says which record was cited, `wrong_fields` says what the
citation got wrong, and `status` is a function of the second. An answer reused from a
history record that cited the same paper with a different wrong field passes the DOI check
and fails the rest, which is exactly the kind of incorrect reuse the benchmark measures.

Design rules this file embodies:
  * Pure and deterministic: labels in, verdict out, no clock, no network, no model.
  * Never raise on bad input. A list, a string, a missing key, a stray type in
    `wrong_fields` or an unknown id each become a failed check with a reason.
  * Lenient on spelling, strict on meaning: DOIs compare through common.norm_doi, status
    through lower/strip, field names through lower/strip plus the aliases author -> authors
    and DOI -> doi; a wrong year is simply wrong.

Run from the repo root:
    /usr/local/bin/python3.13 assignment2/datasets/citations/verify.py --tid T-xxxxxx --answer answer.json
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

from assignment2.datasets import common  # noqa: E402

HIDDEN = os.path.join(HERE, "hidden")
FIELD_ALIASES = {"author": "authors", "authors": "authors", "title": "title", "venue": "venue", "year": "year",
                 "doi": "doi"}


def norm_fields(value):
    """The agent's wrong_fields as a set of canonical names, or None when it is not a list of names."""
    if value is None:
        return set()
    if isinstance(value, str):
        value = [value] if value.strip() else []
    if not isinstance(value, (list, tuple)):
        return None
    names = set()
    for item in value:
        if not isinstance(item, str):
            return None
        key = item.strip().lower()
        names.add(FIELD_ALIASES.get(key, key))
    return names


def grade(tid, answer):
    """{label: (passed, detail)} for one task; the answer is whatever was in answer.json."""
    labels = common.load_labels(HIDDEN)
    if tid not in labels:
        return {"task known": (False, "unknown task id %s" % tid)}
    expected = labels[tid]["answer"]
    checks = {"answer is object": common.check_object(answer)}
    given = answer if isinstance(answer, dict) else {}
    doi = common.norm_doi(given.get("doi", ""))
    checks["doi correct"] = (doi == common.norm_doi(expected["doi"]), "got %r, expected %s" % (given.get("doi"), expected["doi"]))
    status = str(given.get("status", "")).strip().lower()
    checks["status correct"] = (status == expected["status"], "got %r, expected %s" % (given.get("status"), expected["status"]))
    fields = norm_fields(given.get("wrong_fields"))
    checks["wrong_fields correct"] = (fields is not None and fields == set(expected["wrong_fields"]),
                                      "got %r, expected %s" % (given.get("wrong_fields"), expected["wrong_fields"]))
    consistent = fields is not None and (status == "correct") == (not fields)
    checks["status/wrong_fields consistent"] = (consistent, "status %r with wrong_fields %r" % (
        given.get("status"), given.get("wrong_fields")))
    return checks


def shortfall(tid, answer):
    """Failing checks only, as 'label: detail' strings."""
    return common.shortfall(grade(tid, answer))


if __name__ == "__main__":
    sys.exit(common.verifier_main(grade))
