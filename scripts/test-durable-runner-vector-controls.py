#!/usr/bin/env python3
"""Behavioral controls for contract: durable-runner/v0.

Declared invocation set: python3 (stdlib only). Runs
scripts/validate-durable-runner-vectors.py as a subprocess.

Asserts:
  - every vector matches the reference consistency model
  - mutation: with any one guard disabled, at least one vector fails with a
    verdict from the expectation checker (a crash or an unexecutable op does
    not count as a detected mutation)
  - every semantic reject fixture is detected with its labeled reason and its
    baseline vector passes
  - the inventory names existing vectors, every vector's covers keys are in the
    inventory, and the minimum inventory topics are all present
  - each refusal vector states the competing limits it checked
  - every guard the model uses is declared (so it is mutation-tested) and
    every declared guard is used
  - every definition a vector submits successfully, or refuses for a reason
    other than definition_invalid, is valid against the task-definition schema
  - every slot, occurrence set and coverage a vector supplies is valid against
    the supplied-slot schema
  - schema-shaped runner profiles are admitted or refused by the same
    semantic rules: examples admit; schema-valid but semantically wrong
    profiles are refused for their labeled reason
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = ROOT / "schemas/durable-runner/v0"
TOOL = ROOT / "scripts/validate-durable-runner-vectors.py"

MIN_TOPICS = [
    "identity",
    "transition",
    "cancel",
    "crash",
    "retry",
    "orphan",
    "predecessor",
    "checkpoint",
    "reconcile",
    "hold",
    "time",
    "schedule",
    "replay",
    "profile",
    "mode",
]

failures: list[str] = []

if shutil.which("goneat") is None:
    print(
        "[!!] goneat is required for the durable-runner behavioral controls",
        file=sys.stderr,
    )
    sys.exit(1)

_spec = importlib.util.spec_from_file_location("drv_model", TOOL)
model = importlib.util.module_from_spec(_spec)
sys.modules["drv_model"] = model
_spec.loader.exec_module(model)


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"[!!] {msg}", file=sys.stderr)


def valid_schema(schema: str, data: pathlib.Path) -> bool:
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


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-B", str(TOOL), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


print("    durable-runner: vectors match the reference model...")
r = run()
if r.returncode != 0:
    fail(f"vector suite failed:\n{r.stderr[-2000:]}")

print("    durable-runner: mutation controls (every guard must be tested)...")
guards = run("--list-guards").stdout.split()
if not guards:
    fail("model lists no guards")
for g in guards:
    r = run("--disable", g)
    lines = [ln for ln in r.stderr.splitlines() if ln.startswith("[!!]")]
    verdicts = [
        ln
        for ln in lines
        if "could not execute" not in ln and "vectors failed" not in ln
    ]
    if "Traceback" in r.stderr or r.returncode not in (0, 1):
        fail(f"guard {g}: model crashed when the guard was disabled")
    elif r.returncode == 0:
        fail(f"guard {g}: NOT KILLED, every vector still passes without it")
    elif not verdicts:
        fail(f"guard {g}: only unexecutable ops failed, no checker verdict")

print("    durable-runner: every refusal is isolated (its competing note is true)...")
_golden_iso = model.load_golden()
# Grammar and boundary refusals are the parser's own rules: there is no guard whose
# removal would "accept" an unparseable token, so isolation is not defined for them.
# first_not_pending has no task state in which an acceptance could be modeled.
INTRINSIC_REASONS = {
    "format",
    "syntax",
    "overflow",
    "fractional_loss",
    "nonrepresentable",
    "duration_invalid",
    "malformed",
    "zone_unavailable",
    "first_not_pending",
}
ISOLATION_EXEMPT: set[str] = set()
_acc = re.compile(r"^op (\d+) \S+: accepted, expected refusal")
_iso_vectors = {
    p_.stem: json.loads(p_.read_text(encoding="utf-8"))
    for p_ in sorted((BASE / "vectors").rglob("*.json"))
    if p_.name != "INVENTORY.json"
}
for vid, d in sorted(_iso_vectors.items()):
    refusal_ops = {
        i
        for i, op in enumerate(d["ops"])
        if "refused" in op.get("expect", {})
        and op["expect"]["refused"] not in INTRINSIC_REASONS
    }
    if not refusal_ops or vid in ISOLATION_EXEMPT:
        continue
    covered: set[int] = set()
    for g in guards:
        for err in model.run_vector(d, _golden_iso, {g}):
            hit = _acc.match(err)
            if hit:
                covered.add(int(hit.group(1)))
    missing = refusal_ops - covered
    if missing:
        fail(
            f"{vid}: refusal at op {sorted(missing)} is not isolated: no single guard removal "
            "turns it into acceptance, so a competing limit also refuses it"
        )

print("    durable-runner: guards used equal guards declared...")
used = set(
    re.findall(
        r'self\.on\(\s*"([a-z0-9_]+\.[a-z0-9_]+)"\s*\)',
        TOOL.read_text(encoding="utf-8"),
    )
)
if used != set(guards):
    fail(
        f"guards used but undeclared: {sorted(used - set(guards))}; declared but unused: {sorted(set(guards) - used)}"
    )

print("    durable-runner: semantic rejects are detected...")
rej = sorted((BASE / "rejects/semantic").glob("reject-*.json"))
if not rej:
    fail("no semantic rejects")
for p in rej:
    d = json.loads(p.read_text(encoding="utf-8"))
    base = BASE / "vectors" / d["baseline"]
    if run("--file", str(base)).returncode != 0:
        fail(f"{p.name}: baseline {d['baseline']} does not pass")
    r = run("--file", str(p))
    if r.returncode == 0:
        fail(f"{p.name}: tampered vector was accepted")
    elif d["expect_reject"] not in r.stderr:
        fail(
            f"{p.name}: rejected, but not for the labeled reason {d['expect_reject']!r}"
        )

print("    durable-runner: inventory...")
inv = json.loads((BASE / "vectors/INVENTORY.json").read_text(encoding="utf-8"))
vectors = {}
for p in sorted((BASE / "vectors").rglob("*.json")):
    if p.name != "INVENTORY.json":
        vectors[p.stem] = json.loads(p.read_text(encoding="utf-8"))
for key, ids in inv.items():
    for vid in ids:
        if vid not in vectors:
            fail(f"inventory {key}: names unknown vector {vid}")
for vid, d in vectors.items():
    for key in d.get("covers", []):
        if vid not in inv.get(key, []):
            fail(f"{vid}: covers {key} but the inventory does not list it")
    refused = any("refused" in op.get("expect", {}) for op in d["ops"])
    if refused and not any("competing" in n for n in d.get("notes", [])):
        fail(f"{vid}: refusal vector states no competing limits")
for topic in MIN_TOPICS:
    if not any(k.split(".")[0] == topic for k in inv):
        fail(f"minimum inventory topic missing: {topic}")
modes = {
    p.parent.name
    for p in (BASE / "vectors").rglob("*.json")
    if p.name != "INVENTORY.json"
}
if modes != {"basic", "retrying", "journaled", "scheduled"}:
    fail(f"vector modes present: {sorted(modes)}")

print("    durable-runner: vector definitions are schema-valid...")
golden = model.load_golden()
seen_digests: dict[str, tuple[str, str]] = {}
for vid, d in sorted(vectors.items()):
    m = model.Model(d, golden, set())
    for op in d["ops"]:
        name = op.get("definition")
        if name is None or name not in m.defs:
            continue
        if op.get("expect", {}).get("refused") in (
            "definition_invalid",
            "mode_unsupported",
        ):
            continue
        seen_digests.setdefault(
            model.dig(m.defs[name]), (json.dumps(m.defs[name]), vid)
        )
with tempfile.TemporaryDirectory(prefix="drv-defs-") as tmp:
    for i, (_dg, (body, vid)) in enumerate(sorted(seen_digests.items())):
        f = pathlib.Path(tmp) / f"def-{i}.json"
        f.write_text(body, encoding="utf-8")
        if not valid_schema("task-definition.schema.json", f):
            fail(
                f"{vid}: a definition submitted by this vector is not valid against task-definition.schema.json"
            )

print("    durable-runner: every committed transition is a valid wire record...")


def _wire_doc(mo, op, entry, idx):
    label = entry["task"]
    t = mo.tasks[label]
    tid = t["id"]
    prev = [e for e in mo.history[:idx] if e["task"] == label]
    doc = {
        "v": 0,
        "kind": "task_transition",
        "task_id": tid,
        "task_spec_digest": t["spec"],
        "prior": (
            None
            if not prev
            else {
                "stream": "s",
                "record_id": "r",
                "revision": len(prev),
                "digest": "sha256:" + "0" * 64,
            }
        ),
        "to_state": entry["to"],
        "authority_generation": mo.generation,
        "run_id": "run-1",
        "at": model.fmt_instant(mo.clock),
    }
    ha = entry.get("attempt")
    live = t["attempts"][-1]["n"] if t["attempts"] else None
    op_att = op.get("attempt") or {}
    if ha:
        att = {
            "attempt_n": ha["n"],
            "attempt_id": model.dig({"attempt_n": ha["n"], "task_id": tid, "v": 0}),
            "phase": ha["phase"],
        }
        if ha["phase"] == "start":
            att["dispatch"] = "intended"
        if ha["phase"] == "finish":
            att["result"] = ha["result"]
            att["effects"] = op_att.get("effects") or op.get("effects") or "none"
            if ha["result"] == "succeeded":
                att["outputs_verified"] = True
            if op_att.get("outcome"):
                att["outcome_code"] = op_att["outcome"]
        doc["attempt"] = att
    if entry.get("cancellation") == "requested":
        doc["cancellation"] = "requested"
        if entry["to"] == "running" and live is not None:
            doc["attempt"] = {
                "attempt_n": live,
                "attempt_id": model.dig({"attempt_n": live, "task_id": tid, "v": 0}),
                "phase": "carry",
            }
    if entry["to"] == "cancelled":
        doc["cancellation"] = "confirmed"
    if entry["to"] == "waiting" and ha:
        doc["next_eligible_at"] = op.get("next_eligible_at") or model.fmt_instant(
            mo.clock
        )
    if entry["to"] == "missed":
        doc["slot"] = model.dig({"slot": label})
    return doc


wire_docs: dict[str, tuple[dict, str]] = {}
for vid, d in sorted(_iso_vectors.items()):
    mo = model.Model(d, golden, set())
    for op in d["ops"]:
        before = len(mo.history)
        try:
            mo.preflight(op["op"])
            getattr(mo, "op_" + op["op"])(op)
        except (model.Refuse, KeyError, TypeError, ValueError, IndexError):
            continue
        for k, entry in enumerate(mo.history[before:]):
            doc = _wire_doc(mo, op, entry, before + k)
            wire_docs.setdefault(model.dig(doc), (doc, vid))
with tempfile.TemporaryDirectory(prefix="drv-wire-") as tmp:
    for i, (_dg, (doc, vid)) in enumerate(sorted(wire_docs.items())):
        f = pathlib.Path(tmp) / f"wire-{i}.json"
        f.write_text(json.dumps(doc), encoding="utf-8")
        if not valid_schema("transition.schema.json", f):
            fail(
                f"{vid}: a committed {doc['to_state']} transition is not a valid wire record "
                f"(attempt={doc.get('attempt', {}).get('phase')}, cancellation={doc.get('cancellation')})"
            )

print("    durable-runner: supplied slots and coverage are schema-valid...")
supplied: dict[str, tuple[dict, str]] = {}
for vid, d in sorted(vectors.items()):
    for op in d["ops"]:
        docs = []
        if op.get("expect", {}).get("refused") in INTRINSIC_REASONS:
            continue  # a wire-format refusal feeds an input the schema itself rejects
        if "slot" in op:
            docs.append({"v": 0, "kind": "slot", "slot": op["slot"]})
        if "occurrence_set" in op:
            docs.append(
                {"v": 0, "kind": "occurrence_set", "slots": op["occurrence_set"]}
            )
        if op.get("coverage"):
            docs.append({"v": 0, "kind": "coverage", "coverage": op["coverage"]})
        for doc in docs:
            supplied.setdefault(model.dig(doc), (doc, vid))
with tempfile.TemporaryDirectory(prefix="drv-slots-") as tmp:
    for i, (_dg, (doc, vid)) in enumerate(sorted(supplied.items())):
        f = pathlib.Path(tmp) / f"supplied-{i}.json"
        f.write_text(json.dumps(doc), encoding="utf-8")
        if not valid_schema("supplied-slot.schema.json", f):
            fail(
                f"{vid}: a supplied {doc['kind']} is not valid against supplied-slot.schema.json"
            )

print("    durable-runner: profile documents are admitted by the same rules...")
pm = model.Model({"mode": "scheduled", "definitions": {}}, golden, set())
examples = BASE / "examples"
for ex in sorted(examples.glob("runner-profile*.json")):
    try:
        pm.admit_profile_doc(json.loads(ex.read_text(encoding="utf-8")))
    except model.Refuse as r:
        fail(f"{ex.name}: golden profile refused: {r.reason}")


def mutate(doc, path, val):
    o = doc
    for k in path[:-1]:
        o = o[k]
    o[path[-1]] = val


IDEM = ["runtime", "idempotency"]
PROFILE_REJECTS = [
    (
        "ack-over-failure-model",
        [(["runtime", "journal", "failure_model"], "survives_process_loss")],
        "journal_ack_exceeds_failure_model",
    ),
    (
        "store-below-effective",
        [(IDEM + ["store_window"], "P1D")],
        "store_window_too_short",
    ),
    (
        "window-inverted",
        [(IDEM + ["window"], {"min": "P35D", "default": "P14D", "max": "P7D"})],
        "window_out_of_range",
    ),
    (
        "effective-outside-kind-range",
        [(IDEM + ["effective_window"], "P100D"), (IDEM + ["store_window"], "P100D")],
        "window_out_of_range",
    ),
    (
        "store-below-retry-horizon",
        [(IDEM + ["retry_horizon"], "P40D")],
        "store_window_too_short",
    ),
]
with tempfile.TemporaryDirectory(prefix="drv-prof-") as tmp:
    for name, edits, reason in PROFILE_REJECTS:
        doc = json.loads(
            (examples / "runner-profile.example.json").read_text(encoding="utf-8")
        )
        for path, val in edits:
            mutate(doc, path, val)
        f = pathlib.Path(tmp) / f"{name}.json"
        f.write_text(json.dumps(doc), encoding="utf-8")
        if not valid_schema("runner-profile.schema.json", f):
            fail(
                f"profile reject {name}: must be schema-valid so the semantic rule is what refuses it"
            )
        try:
            pm.admit_profile_doc(doc)
            fail(f"profile reject {name}: admitted, expected {reason}")
        except model.Refuse as r:
            if r.reason != reason:
                fail(f"profile reject {name}: refused {r.reason}, expected {reason}")

doc = json.loads(
    (examples / "runner-profile.basic.example.json").read_text(encoding="utf-8")
)
mutate(doc, ["runtime", "durability", "attempt_journal_ack"], "survives_power_loss")
with tempfile.TemporaryDirectory(prefix="drv-prof2-") as tmp:
    f = pathlib.Path(tmp) / "ack-without-journal.json"
    f.write_text(json.dumps(doc), encoding="utf-8")
    if not valid_schema("runner-profile.schema.json", f):
        fail("profile reject ack-without-journal: must be schema-valid")
    try:
        pm.admit_profile_doc(doc)
        fail(
            "profile reject ack-without-journal: admitted, expected journal_ack_exceeds_failure_model"
        )
    except model.Refuse as r:
        if r.reason != "journal_ack_exceeds_failure_model":
            fail(f"profile reject ack-without-journal: refused {r.reason}")

if failures:
    print(
        f"[!!] durable-runner behavioral controls: {len(failures)} failure(s)",
        file=sys.stderr,
    )
    sys.exit(1)
print(
    f"[ok] durable-runner behavioral controls passed ({len(vectors)} vectors, {len(guards)} guards)"
)
