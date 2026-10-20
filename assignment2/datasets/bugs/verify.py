"""Assignment 2 -- bugs/verify.py: are the component and root cause in answer.json the verified ones?

Concept this file teaches: an agent's final message is a claim, not evidence. The only thing
graded is the file it wrote, compared with a label it never saw. A reused answer that came from
the wrong report -- the same story under a different top frame, or on a different version series
-- fails here exactly like a wrong guess would, which is what makes "incorrect reuse" measurable.

Design rules this file embodies:
  * Pure and deterministic: labels in, verdict out, no clock, no network, no model.
  * Never raise on bad input. A list, a string, a missing key or an unknown id each become a
    failed check with a reason; the runner must keep going.
  * Lenient on spelling, strict on meaning: RC-7, rc-07 and 7 are all RC-07, "Networking" and
    "networking" are one component, but RC-08 and "storage" are simply wrong.

Run from the repo root:
    /usr/local/bin/python3.13 assignment2/datasets/bugs/verify.py --tid T-xxxxxx --answer answer.json
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))

from assignment2.datasets import common  # noqa: E402

HIDDEN = os.path.join(HERE, "hidden")
CATALOGUE_SIZE = 20
COMPONENTS = ("networking", "storage", "auth", "ui", "reporting", "importer", "scheduler", "config")


def norm_component(value):
    """'Networking', ' networking ' and 'net_working' -> 'networking' / 'net-working'; unknown -> None."""
    if value is None or isinstance(value, (list, dict)):
        return None
    name = re.sub(r"[\s_]+", "-", str(value).strip().lower())
    return name if name in COMPONENTS else None


def grade(tid, answer):
    """{label: (passed, detail)} for one task; the answer is whatever was in answer.json."""
    labels = common.load_labels(HIDDEN)
    if tid not in labels:
        return {"task known": (False, "unknown task id %s" % tid)}
    expected = labels[tid]["answer"]
    checks = {"answer is object": common.check_object(answer)}
    given_component = answer.get("component") if isinstance(answer, dict) else None
    component = norm_component(given_component)
    checks["component valid"] = (component is not None, "one of %s expected, got %r" % (", ".join(COMPONENTS), given_component))
    checks["component correct"] = (component == expected["component"], "got %s, expected %s" % (component, expected["component"]))
    given_cause = answer.get("root_cause") if isinstance(answer, dict) else None
    cause = common.norm_rid(given_cause, "RC", CATALOGUE_SIZE)
    checks["root_cause valid"] = (cause is not None, "RC-01..RC-%d expected, got %r" % (CATALOGUE_SIZE, given_cause))
    checks["root_cause correct"] = (cause == expected["root_cause"], "got %s, expected %s" % (cause, expected["root_cause"]))
    return checks


def shortfall(tid, answer):
    """Failing checks only, as 'label: detail' strings."""
    return common.shortfall(grade(tid, answer))


if __name__ == "__main__":
    sys.exit(common.verifier_main(grade))
