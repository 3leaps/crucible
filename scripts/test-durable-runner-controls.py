#!/usr/bin/env python3
"""Controls for contract: durable-runner/v0 (schema layer).

Declared invocation set: python3 (stdlib only), goneat (JSON Schema validation
the contract names). Identity digests reuse scripts/rfc8785-canonicalize.py.

Asserts:
  - every example validates against the schema its filename prefix names
  - the task-definition schema is mirrored exactly inside task-submission
  - shared definitions are identical wherever they appear
  - task_id, task_spec_digest and attempt_id in examples equal the values
    derived from RFC 8785 canonical bytes
  - baseline-* reject fixtures pass, reject-* fail, and each pair differs in
    exactly one leaf; the index and the files agree
  - fixtures carry no machine-local paths or credential-shaped strings
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = ROOT / "schemas/durable-runner/v0"

_spec = importlib.util.spec_from_file_location(
    "jcs", ROOT / "scripts/rfc8785-canonicalize.py"
)
jcs = importlib.util.module_from_spec(_spec)
sys.modules["jcs"] = jcs
_spec.loader.exec_module(jcs)

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"[!!] {msg}", file=sys.stderr)


def digest(value) -> str:
    return "sha256:" + hashlib.sha256(jcs.jcs_dumps(value).encode()).hexdigest()


def valid(schema: str, data: pathlib.Path) -> bool:
    r = subprocess.run(
        [
            "goneat",
            "validate",
            "data",
            "--schema-file",
            str(BASE / schema),
            "--data",
            str(data),
        ],
        capture_output=True,
    )
    return r.returncode == 0


def load(p: pathlib.Path):
    return json.loads(p.read_text())


PREFIX_SCHEMA = {
    "task-definition": "task-definition.schema.json",
    "task-submission": "task-submission.schema.json",
    "runner-profile": "runner-profile.schema.json",
    "transition": "transition.schema.json",
    "checkpoint": "checkpoint.schema.json",
    "supplied-slot": "supplied-slot.schema.json",
}


def diff_count(a, b) -> int:
    """Differences between two JSON values: a differing scalar, an added or
    removed member (whole subtree) or a changed list length counts as one."""
    if isinstance(a, dict) and isinstance(b, dict):
        n = 0
        for k in set(a) | set(b):
            if k not in a or k not in b:
                n += 1
            else:
                n += diff_count(a[k], b[k])
        return n
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return 1
        return sum(diff_count(x, y) for x, y in zip(a, b))
    return 0 if (a == b and type(a) is type(b)) else 1


print("    durable-runner: golden examples...")
examples = sorted((BASE / "examples").glob("*.json"))
if not examples:
    fail("no examples found")
for ex in examples:
    prefix = next((p for p in PREFIX_SCHEMA if ex.name.startswith(p)), None)
    if prefix is None:
        fail(f"{ex.name}: filename prefix names no schema")
        continue
    if not valid(PREFIX_SCHEMA[prefix], ex):
        fail(f"{ex.name}: does not validate against {PREFIX_SCHEMA[prefix]}")

print("    durable-runner: submission mirrors the task-definition schema...")
definition = load(BASE / "task-definition.schema.json")
submission = load(BASE / "task-submission.schema.json")
mirror = submission["$defs"]["taskDefinition"]
want = {
    k: v for k, v in definition.items() if k not in ("$schema", "$id", "title", "$defs")
}
if mirror != want:
    fail(
        "task-submission $defs.taskDefinition drifted from task-definition.schema.json"
    )

print("    durable-runner: shared definitions are identical...")
seen: dict[str, tuple[str, object]] = {}
for sp in sorted(BASE.glob("*.schema.json")):
    for name, body in load(sp).get("$defs", {}).items():
        if name == "taskDefinition":
            continue
        if name in seen and seen[name][1] != body:
            fail(f"$defs.{name} differs between {seen[name][0]} and {sp.name}")
        seen.setdefault(name, (sp.name, body))

print("    durable-runner: identities equal RFC 8785 derivations...")
sub = load(BASE / "examples/task-submission.example.json")
want_spec = digest(sub["definition"])
if sub["task_spec_digest"] != want_spec:
    fail(
        "task-submission example: task_spec_digest is not the digest of the canonical definition"
    )
want_tid = digest(
    {"authority": sub["authority"], "invocation_key": sub["invocation_key"], "v": 0}
)
if sub["task_id"] != want_tid:
    fail(
        "task-submission example: task_id is not derived from authority and invocation_key"
    )
if load(BASE / "examples/task-definition.example.json") != sub["definition"]:
    fail("task-definition example and the submission's embedded definition differ")
for tp in sorted((BASE / "examples").glob("transition.*.json")):
    t = load(tp)
    if t["task_id"] != want_tid or t["task_spec_digest"] != want_spec:
        fail(f"{tp.name}: task identity does not match the submission example")
    a = t.get("attempt")
    if a and a["attempt_id"] != digest(
        {"attempt_n": a["attempt_n"], "task_id": t["task_id"], "v": 0}
    ):
        fail(f"{tp.name}: attempt_id is not derived from attempt_n and task_id")

print("    durable-runner: schema reject pairs...")
rej = BASE / "rejects/schema"
index = load(rej / "index.json")
names = {p.name[len("baseline-") : -len(".json")] for p in rej.glob("baseline-*.json")}
rnames = {p.name[len("reject-") : -len(".json")] for p in rej.glob("reject-*.json")}
if names != rnames or names != set(index):
    fail("rejects/schema: baselines, rejects and index.json do not name the same cases")
for name in sorted(names & rnames & set(index)):
    schema = index[name]["schema"]
    b, r = rej / f"baseline-{name}.json", rej / f"reject-{name}.json"
    if not valid(schema, b):
        fail(f"baseline-{name}: baseline does not validate")
    if valid(schema, r):
        fail(f"reject-{name}: reject validates but must fail")
    if diff_count(load(b), load(r)) != 1:
        fail(
            f"{name}: pair differs in {diff_count(load(b), load(r))} leaves, want exactly 1"
        )

print("    durable-runner: fixtures carry no local paths or credentials...")
pat = re.compile(
    r"(/Users/|/home/|C:\\\\|BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,})"
)
for p in sorted(BASE.rglob("*.json")):
    if pat.search(p.read_text()):
        fail(f"{p.relative_to(ROOT)}: machine-local path or credential-shaped string")

if failures:
    print(f"[!!] durable-runner controls: {len(failures)} failure(s)", file=sys.stderr)
    sys.exit(1)
print("[ok] durable-runner controls passed")
