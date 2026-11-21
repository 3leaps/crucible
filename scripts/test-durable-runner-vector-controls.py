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

import copy
import importlib.util
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import types

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
golden = model.load_golden()
_all_vectors = {
    p_.stem: json.loads(p_.read_text(encoding="utf-8"))
    for p_ in sorted((BASE / "vectors").rglob("*.json"))
    if p_.name != "INVENTORY.json"
}
# One baseline pass records which guards each vector consults; a guard can only change
# the verdict of a vector that reads it, so only those vectors are re-run per guard.
seen_by_vector: dict[str, set[str]] = {}
for _vid, _vec in _all_vectors.items():
    _seen: set[str] = set()
    if model.run_vector(_vec, golden, set(), _seen):
        fail(f"{_vid}: fails with every guard enabled")
    seen_by_vector[_vid] = _seen
for g in guards:
    affected = [v for v in _all_vectors if g in seen_by_vector[v]]
    if not affected:
        fail(f"guard {g}: no vector ever consults it")
        continue
    killed = False
    for v in affected:
        errs = model.run_vector(_all_vectors[v], golden, {g})
        if any("could not execute" not in e for e in errs):
            killed = True
            break
    if not killed:
        fail(
            f"guard {g}: NOT KILLED by a checker verdict in any of {len(affected)} vectors that consult it"
        )

print("    durable-runner: every refusal is isolated (its competing note is true)...")
_golden_iso = model.load_golden()
# Grammar refusals of the four parser operations are the parser's own rules: no guard's
# removal would "accept" an unparseable token, so isolation is not defined for them.
PARSER_OPS = {"parse_instant", "parse_duration", "format_instant", "advance_clock"}
PARSER_REASONS = {
    "format",
    "syntax",
    "overflow",
    "fractional_loss",
    "nonrepresentable",
    "duration_invalid",
}
# Refusals where the model has no state in which an acceptance could be expressed. Each
# entry is a vector name; the type-fuzz control below covers argument shape for every op.
ISOLATION_EXEMPT = {
    "first-transition-not-pending-refused",  # no task exists to accept the transition on
    "slot-civil-time-noncanonical-refused",  # the raw civil-time grammar
    "slot-civil-time-year-unavailable-refused",  # the zone table cannot compute an instant
    # The refusal is an injected harness fault (commit_indeterminate), not a rule guard.
    "occurrence-set-commit-failure-reports-partial-progress",
    "occurrence-set-failure-after-first-item-leaves-prefix",
    "coverage-commit-failure-leaves-committed-prefix",
    "recover-missing-effects-refused",  # argument shape, covered by the type-fuzz control
    "recover-missing-owner-refused",
    "recover-unrecognized-disposition-refused",
    "occurrence-set-label-count-mismatch-refused",
    # Removing the check leaves a later, unconditional label-collision refusal; the guard
    # only moves it ahead of the first commit, which the mutation control observes.
    "coverage-duplicate-label-refused-commits-nothing",
    "definition-missing-retry-refused",  # no accepting behavior exists for a missing key
    "request-cancel-unknown-task-refused",  # no task exists to accept the request on
    # The first refusal is a grammar refusal (syntax); the others are isolated only by the
    # atomicity guard, whose mutation is observed through the committed configuration.
    "profile-admit-refused-installs-nothing",
}


def _exempt_op(op) -> bool:
    return op["op"] in PARSER_OPS and op["expect"]["refused"] in PARSER_REASONS


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
        if "refused" in op.get("expect", {}) and not _exempt_op(op)
    }
    if not refusal_ops or vid in ISOLATION_EXEMPT:
        continue
    covered: set[int] = set()
    for g in seen_by_vector[vid]:
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
            eff = op_att.get("effects") or op.get("effects")
            if eff is not None:
                att["effects"] = eff
            if op_att.get("outputs_verified") is not None:
                att["outputs_verified"] = op_att["outputs_verified"]
            if op_att.get("outcome"):
                att["outcome_code"] = op_att["outcome"]
            if op_att.get("reason") and not op_att.get("outcome"):
                att["failure_reason"] = op_att["reason"]
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
        if op.get("next_eligible_at") is not None:
            doc["next_eligible_at"] = op["next_eligible_at"]
    if entry["to"] == "missed":
        if t.get("slot_key") is not None:
            doc["slot"] = model.dig({"slot_key": t["slot_key"]})
    return doc


wire_docs: dict[str, tuple[dict, str]] = {}
for vid, d in sorted(_iso_vectors.items()):
    drv = model.Driver(d, golden, set())
    mo = drv.m
    for op in d["ops"]:
        before = len(mo.history)
        try:
            drv.step(op)
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
        if op.get("expect", {}).get("refused") in PARSER_REASONS | {
            "malformed",
            "zone_unavailable",
        }:
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


print("    durable-runner: source-level mutants (arithmetic, anchors, boundaries)...")

SRC = TOOL.read_text(encoding="utf-8")
SOURCE_MUTANTS = [
    ("nominal-rounds-down", "math.ceil(val)", "math.floor(val)"),
    ("lower-bound-rounds-down", "math.ceil(nominal", "math.floor(nominal"),
    ("upper-bound-rounds-up", "math.floor(nominal", "math.ceil(nominal"),
    (
        "multiplier-through-float",
        'bo.get("multiplier_milli", 1000), 1000)',
        'bo.get("multiplier_milli", 1000) / 1000)',
    ),
    (
        "slot-start-lower-bound-exclusive",
        "self.clock < lo_s or self.clock >= hi_s",
        "self.clock <= lo_s or self.clock >= hi_s",
    ),
    (
        "catch-up-start-lag-exclusive",
        "0 <= self.clock - cu <= self._lag_limit(t)",
        "0 <= self.clock - cu < self._lag_limit(t)",
    ),
    (
        "horizon-anchored-at-acceptance",
        'return at_us - t["first_start_us"]',
        'return at_us - t["accepted_us"]',
    ),
    (
        "identity-expiry-inclusive",
        'rec["accepted_us"] > self.store_window_us',
        'rec["accepted_us"] >= self.store_window_us',
    ),
    (
        "coverage-missed-at-window-end-late",
        "if self.clock < hi:",
        "if self.clock <= hi:",
    ),
    ("catch-up-key-without-domain", '"domain": "catch_up", ', ""),
    (
        "slot-key-without-scope",
        '            "scope": scope,\n            "v": 0,\n        }\n        return "slot:"',
        '            "v": 0,\n        }\n        return "slot:"',
    ),
    (
        "cancel-on-failed-too-late",
        'if t["state"] == "succeeded":',
        'if t["state"] in ("succeeded", "failed"):',
    ),
    (
        "catch-up-deadline-anchored-at-missed-instant",
        'a["as"], m["authority"], key, a["definition"], derived=True',
        'a["as"], m["authority"], key, a["definition"], derived=True, anchor_us=m.get("slot_instant")',
    ),
    (
        "deadline-bound-inclusive",
        'return when - t["accepted_us"] >= parse_duration_us(tl)',
        'return when - t["accepted_us"] > parse_duration_us(tl)',
    ),
    ("feasibility-cap-off-by-one", "end - self.clock - 1", "end - self.clock"),
    (
        "missed-before-window-end",
        't["started"] > 0 or hi is None or self.clock < hi',
        't["started"] > 0 or hi is None or self.clock <= hi',
    ),
]
_mut_vectors = sorted(
    (p_.stem, json.loads(p_.read_text(encoding="utf-8")))
    for p_ in (BASE / "vectors").rglob("*.json")
    if p_.name != "INVENTORY.json"
)
for name, old, new in SOURCE_MUTANTS:
    if SRC.count(old) != 1:
        fail(
            f"source mutant {name}: anchor occurs {SRC.count(old)} times (want 1); the model changed, update the mutant"
        )
        continue
    mod = types.ModuleType("drv_mutant")
    mod.__file__ = str(TOOL)
    try:
        exec(compile(SRC.replace(old, new, 1), str(TOOL), "exec"), mod.__dict__)
        golden_m = mod.load_golden()
        killed = any(mod.run_vector(vec, golden_m, set()) for _vid, vec in _mut_vectors)
    except Exception:  # a mutant that crashes the whole checker is still a kill
        killed = True
    if not killed:
        fail(f"source mutant {name}: SURVIVES, every vector still passes")

print("    durable-runner: type-fuzz of every operation's arguments...")

FUZZ_JUNK = {
    bool: ["false", "true", 1, 0, None, []],
    int: [None, True, "1", 1.5, -1, 10**30],
    str: [None, True, 1, 1.5, [], {}, "", "a b", "A" * 300],
    dict: [None, "x", 1, [], ["a"]],
    list: [None, "x", 1, {}],
}
# Genuinely free-form fields: any string is a legal value.
FUZZ_FREEFORM = {
    ("transition", "reason"),
    ("transition", "attempt.reason"),
    ("admission", "source"),
}


def _sites(op):
    for k, v in op.items():
        if k in ("op", "expect"):
            continue
        yield (k,), v
        if isinstance(v, dict):
            for k2, v2 in v.items():
                yield (k, k2), v2


def _set(op, site, val):
    o = copy.deepcopy(op)
    cur = o
    for k in site[:-1]:
        cur = cur[k]
    cur[site[-1]] = val
    return o


def _run_tail(vec, idx, op):
    drv = model.Driver(vec, golden, set())
    for prior in vec["ops"][:idx]:
        try:
            drv.step(prior)
        except (
            model.Refuse,
            KeyError,
            TypeError,
            ValueError,
            IndexError,
            OverflowError,
            AttributeError,
        ):
            pass
    try:
        drv.step(op)
        return "accepted"
    except model.Refuse:
        return "refused"
    except Exception as exc:
        return type(exc).__name__


reps = {}
for vid, d in sorted(vectors.items()):
    for i, op in enumerate(d["ops"]):
        if "ok" in op.get("expect", {}) and op["op"] != "profile_admit":
            n_keys = sum(1 for _ in _sites(op))
            if op["op"] not in reps or n_keys > reps[op["op"]][2]:
                reps[op["op"]] = (vid, i, n_keys)
        if op["op"] == "profile_admit" and "ok" in op.get("expect", {}):
            n_keys = sum(1 for _ in _sites(op))
            if op["op"] not in reps or n_keys > reps[op["op"]][2]:
                reps[op["op"]] = (vid, i, n_keys)
trials = 0
for opname, (vid, idx, _n) in sorted(reps.items()):
    vec = vectors[vid]
    op = vec["ops"][idx]
    for site, val in _sites(op):
        pool = FUZZ_JUNK.get(bool if isinstance(val, bool) else type(val), [])
        for junk in pool:
            if junk == val and type(junk) is type(val):
                continue
            trials += 1
            res = _run_tail(vec, idx, _set(op, site, junk))
            label = ".".join(site)
            if res == "accepted" and (opname, label) not in FUZZ_FREEFORM:
                fail(
                    f"fuzz {opname}.{label} = {junk!r}: accepted junk (fail-open) in {vid}"
                )
            elif res not in ("accepted", "refused"):
                fail(
                    f"fuzz {opname}.{label} = {junk!r}: model raised {res} instead of refusing ({vid})"
                )
print(f"    durable-runner: {trials} fuzz trials over {len(reps)} operations")

print(
    "    durable-runner: malformed input is refused without crashes or side effects..."
)
_base_vec = vectors["slot-supplied-eligible"]


def _drv():
    return model.Driver(copy.deepcopy(_base_vec), golden, set())


_bad_defs = [
    {"retry.retry_after_abandonment": "false"},
    {"retry.retry_after_abandonment": 1},
    {"v": 99},
    {"retry": None},
    {"retry.backoff": {}},
    {"outcome_mapping": [{"code": "x"}]},
    {"outcome_mapping": "x"},
    {"timeouts": []},
]
for _spec in _bad_defs:
    _d = _drv()
    _d.m.defs = {"d1": _d.m._build_def(_spec)}
    try:
        _d.step(
            {
                "op": "submit",
                "as": "t",
                "authority": "a",
                "key": "k",
                "definition": "d1",
            }
        )
        fail(f"malformed definition {_spec!r} was accepted")
    except model.Refuse as _r:
        if _r.reason != "definition_invalid":
            fail(
                f"malformed definition {_spec!r}: refused {_r.reason!r}, want definition_invalid"
            )
    except Exception as _e:  # noqa: BLE001 - any crash is the finding
        fail(f"malformed definition {_spec!r} crashed the model: {type(_e).__name__}")


def _cfg(m_):
    return {k: getattr(m_, k) for k in m_.CONFIG}


for _prof in (
    {
        "modes": ["basic"],
        "task_kind_window_range": {"min": "P1D", "max": "P40D"},
        "window": {"min": "P7D"},
    },
    {
        "modes": ["basic"],
        "schedule": {
            "rule_contract": {"digest": "sha256:" + "0" * 64},
            "max_lag": "bad",
        },
    },
    {"modes": ["basic"], "schedule": {"max_lag": "PT1H"}},
):
    _d = _drv()
    _before = _cfg(_d.m)
    try:
        _d.step({"op": "profile_admit", "profile": _prof})
        fail(f"malformed profile {_prof!r} was admitted")
    except model.Refuse:
        pass
    except Exception as _e:  # noqa: BLE001
        fail(f"malformed profile {_prof!r} crashed the model: {type(_e).__name__}")
    if _cfg(_d.m) != _before:
        fail(f"a refused profile {_prof!r} changed the configuration")
with tempfile.TemporaryDirectory() as _td:
    _dup = pathlib.Path(_td) / "dup.json"
    _dup.write_text('{"v": 0, "v": 0, "id": "dup", "mode": "basic"}', encoding="utf-8")
    _res = subprocess.run(
        [sys.executable, "-B", str(TOOL), "--file", str(_dup)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if _res.returncode == 0:
        fail("a vector with a duplicate JSON member was accepted")

if failures:
    print(
        f"[!!] durable-runner behavioral controls: {len(failures)} failure(s)",
        file=sys.stderr,
    )
    sys.exit(1)
print(
    f"[ok] durable-runner behavioral controls passed ({len(vectors)} vectors, {len(guards)} guards)"
)
