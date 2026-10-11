#!/usr/bin/env python3
"""Fixture-integrity checker for contract: durable-queue/v0.

Standard library plus the repository's RFC 8785 materializer. Validates that a
behavioral vector is a well-formed, internally consistent claim about the
contract. It does not execute a queue; the executing harness lives in the
adopting repository.

Modes:
  vectors <base>            check the required inventory and every vector under <base>/vectors
  vector  <base> <file>     check one vector; exit 1 and print 'reject:<reason>' on the first defect
  pair    <baseline> <reject>   assert the two JSON documents differ in exactly one scalar path
  profile <file>            assert runtime.enabled_capabilities is a subset of build.compiled_capabilities
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.abspath(__file__))
jcs = SourceFileLoader(
    "jcs", os.path.join(HERE, "rfc8785-canonicalize.py")
).load_module()

REQUIRED_VECTORS = {
    "core": [
        "enqueue-claim-ack",
        "lease-expiry-redelivery",
        "expiry-on-claim-without-sweep",
        "stale-lease-ack",
        "wrong-queue-lease",
        "idempotent-enqueue",
        "changed-content-conflict",
        "post-terminal-dedup",
        "nack-to-dead-letter",
        "expiry-counts-toward-max-attempts",
        "redrive-resets-budget",
    ],
    "fanout": ["atomic-fanout", "fanout-stale-parent", "fanout-repeat-dedup"],
    "canonicalization": ["payload-digest"],
}
CAPS = {
    "transactional_enqueue",
    "atomic_fanout",
    "delay",
    "ordering_key",
    "priority",
    "payload_ref",
    "long_poll",
    "virtual_clock",
}
TRANSITIONS = {
    # type: (allowed prior states, resulting state)
    "enqueued": ({None}, "ready"),
    "leased": ({"ready"}, "leased"),
    "extended": ({"leased"}, "leased"),
    "acked": ({"leased"}, "done"),
    "nacked": ({"leased"}, "ready"),
    "lease_expired": ({"leased"}, "ready"),
    "dead_lettered": ({"ready", "leased"}, "dead"),
    "redriven": ({"dead"}, "ready"),
    "purged": ({"ready", "leased", "dead"}, "gone"),
}
AUDIT = {"deduplicated", "conflicted"}
TERMINAL = {"done", "gone"}


class Reject(Exception):
    pass


def rej(reason: str, detail: str) -> None:
    raise Reject(f"reject:{reason} {detail}")


def goneat_validate(schema: str, doc: object) -> bool:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(doc, f)
        path = f.name
    try:
        r = subprocess.run(
            ["goneat", "validate", "data", "--schema-file", schema, "--data", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return r.returncode == 0
    finally:
        os.unlink(path)


def identity_digest(msg: dict) -> str:
    if "payload" in msg:
        o = {"payload_contract": msg["payload_contract"], "payload": msg["payload"]}
    else:
        o = {
            "payload_contract": msg["payload_contract"],
            "payload_ref": {
                "artifact_id": msg["payload_ref"]["artifact_id"],
                "digest": msg["payload_ref"]["digest"],
            },
        }
    return "sha256:" + hashlib.sha256(jcs.jcs_dumps(o).encode("utf-8")).hexdigest()


BIND_RE = re.compile(r"^\$[a-z][a-z0-9_]*$")


def substitute(obj, names: dict, placeholder_lease: dict):
    """Replace $name tokens with concrete stand-ins so the op can be schema-validated."""
    if isinstance(obj, str) and BIND_RE.match(obj):
        if obj not in names:
            rej("unbound_binding", obj)
        return names[obj]
    if isinstance(obj, dict):
        if "$rebind" in obj:
            src = obj["$rebind"]
            if src not in names:
                rej("unbound_binding", src)
            out = copy.deepcopy(names[src])
            for k, v in obj.items():
                if k != "$rebind":
                    out[k] = v
            return out
        return {k: substitute(v, names, placeholder_lease) for k, v in obj.items()}
    if isinstance(obj, list):
        return [substitute(v, names, placeholder_lease) for v in obj]
    return obj


def check_vector(base: str, path: str) -> None:
    v = json.load(open(path, encoding="utf-8"))
    for k in (
        "name",
        "requires",
        "clock_start",
        "queue",
        "description",
        "ops",
        "ledger",
    ):
        if k not in v:
            rej("vector_shape", f"missing {k}")
    if not v["ops"] or not v["ledger"]:
        rej("empty_vector", v["name"])
    for cap in v["requires"]:
        if cap not in CAPS:
            rej("unknown_capability", cap)
    ce = os.path.join(base, "control-exchange.schema.json")
    le = os.path.join(base, "ledger-event.schema.json")

    # ---- ops: validate as requests (bindings replaced by stand-ins), expectations as responses
    names: dict = {}
    stand_lease = {
        "queue": v["queue"],
        "message_id": "stand-in",
        "token": "stand-in",
        "attempt": 1,
        "until": v["clock_start"],
    }
    key_digest: dict = {}  # idempotency_key -> identity digest (first enqueue wins)
    rejected_digests: dict = {}
    seen_ops = 0
    for i, op in enumerate(v["ops"]):
        if op.get("op") not in (
            "enqueue",
            "claim",
            "extend",
            "ack",
            "nack",
            "fail",
            "fan_out",
            "stats",
            "peek",
            "redrive",
            "purge",
            "sweep",
            "export_ledger",
            "capabilities",
            "advance_clock",
        ):
            rej("op_schema", f"ops[{i}] unknown op {op.get('op')!r}")
        # pre-register bindings this op will produce so later ops can reference them
        names_for_validation = dict(names)
        for b in op.get("bind") or {}:
            names_for_validation.setdefault(b, stand_lease)
        exp = op.get("expect") or {}
        for rc in exp.get("receipts", []) or []:
            if isinstance(rc.get("message_id"), str) and BIND_RE.match(
                rc["message_id"]
            ):
                names_for_validation.setdefault(rc["message_id"], "stand-in")
        params = substitute(op.get("params", {}), names_for_validation, stand_lease)
        req = {"id": str(i), "op": op["op"], "params": params}
        if not goneat_validate(ce, req):
            rej("op_schema", f"ops[{i}] {op['op']} params invalid")
        seen_ops += 1
        # expectation: must validate as a successful response when fully specified
        if op["op"] in ("enqueue", "fan_out"):
            if "receipts" not in exp:
                rej("expect_shape", f"ops[{i}] {op['op']} needs expect.receipts")
            msgs = params.get("messages") or params.get("children") or []
            if op["op"] == "enqueue" and len(exp["receipts"]) != len(msgs):
                rej("expect_shape", f"ops[{i}] receipts count != messages count")
            if op["op"] == "fan_out":
                outc_fo = exp.get("outcome", "ok")
                if outc_fo == "stale_lease":
                    if exp["receipts"]:
                        rej(
                            "expect_shape",
                            f"ops[{i}] stale fan_out must have empty receipts",
                        )
                    msgs = []
                elif len(exp["receipts"]) != len(msgs):
                    rej("expect_shape", f"ops[{i}] receipts count != children count")
            for m, rc in zip(msgs, exp["receipts"]):
                mid = rc["message_id"]
                outc = rc.get("outcome")
                if outc not in ("accepted", "deduplicated", "conflict"):
                    rej("expect_shape", f"ops[{i}] receipt outcome {outc!r}")
                if isinstance(mid, str) and BIND_RE.match(mid):
                    names.setdefault(mid, mid)
                k = m.get("idempotency_key")
                if k is not None:
                    k = (params.get("queue") or v["queue"], k)  # key scope is the queue
                d = identity_digest(m)
                if outc == "accepted":
                    if k is not None:
                        if k in key_digest:
                            rej("expect_shape", f"ops[{i}] key {k} accepted twice")
                        key_digest[k] = d
                elif outc == "deduplicated":
                    if k is None or key_digest.get(k) != d:
                        rej(
                            "expect_shape",
                            f"ops[{i}] deduplicated receipt without matching live key/digest",
                        )
                else:
                    if k is None or k not in key_digest or key_digest[k] == d:
                        rej(
                            "expect_shape",
                            f"ops[{i}] conflict receipt needs a live key with a different digest",
                        )
                    rejected_digests[k] = d
            resp = {
                "id": str(i),
                "op": op["op"],
                "ok": True,
                "result": substitute(
                    {k2: v2 for k2, v2 in exp.items()},
                    {**names, **{n: "stand-in" for n in names}},
                    stand_lease,
                ),
            }
            if op["op"] == "fan_out":
                resp["result"].setdefault("outcome", "ok")
            if not goneat_validate(ce, resp):
                rej(
                    "expect_schema",
                    f"ops[{i}] {op['op']} expect does not validate as a result",
                )
        elif op["op"] in ("ack", "nack", "extend", "fail"):
            outs = exp.get("outcomes")
            if not isinstance(outs, list) or len(outs) != len(params["leases"]):
                rej("expect_shape", f"ops[{i}] outcomes must be positional with leases")
            if not goneat_validate(
                ce,
                {
                    "id": str(i),
                    "op": op["op"],
                    "ok": True,
                    "result": {"outcomes": outs},
                },
            ):
                rej("expect_schema", f"ops[{i}] outcome vocabulary")
        elif op["op"] == "claim":
            if "delivery_count" not in exp:
                rej("expect_shape", f"ops[{i}] claim needs expect.delivery_count")
            if exp["delivery_count"] > params["max"]:
                rej("expect_shape", f"ops[{i}] delivery_count exceeds max")
        elif op["op"] in (
            "stats",
            "sweep",
            "redrive",
            "purge",
            "export_ledger",
            "advance_clock",
            "peek",
            "capabilities",
        ):
            if "expect" in op and op["op"] in ("stats", "sweep"):
                if not goneat_validate(
                    ce, {"id": str(i), "op": op["op"], "ok": True, "result": exp}
                ):
                    rej(
                        "expect_schema",
                        f"ops[{i}] {op['op']} expect does not validate as a result",
                    )
        for b in op.get("bind") or {}:
            if not BIND_RE.match(b):
                rej("vector_shape", f"bad bind name {b}")
            names[b] = stand_lease
    if seen_ops == 0:
        rej("empty_vector", v["name"])

    # ---- ledger: schema, seq, groups, bindings, fold, attempts, digests
    L = v["ledger"]
    for i, e in enumerate(L):
        if not goneat_validate(le, e):
            rej("ledger_schema", f"ledger[{i}]")
        if "token" in e or "fence_token" in e:
            rej("ledger_schema", "fencing token in ledger")
        if e["queue"] != v["queue"]:
            rej("ledger_schema", f"ledger[{i}] queue {e['queue']} != vector queue")
    seqs = [e["seq"] for e in L]
    if seqs != list(range(1, len(L) + 1)):
        rej("seq_gap", str(seqs))
    # atomic groups contiguous, sized correctly, and complete at the end
    i = 0
    while i < len(L):
        g = L[i]["group"]
        n = L[i]["group_size"]
        if g != L[i]["seq"]:
            rej("truncated_group", f"seq {L[i]['seq']} starts mid-group (group={g})")
        members = L[i : i + n]
        if len(members) != n or any(
            m["group"] != g or m["group_size"] != n for m in members
        ):
            rej("truncated_group", f"group {g} size {n} is not contiguous and complete")
        i += n
    state: dict = {}
    live_attempt: dict = {}
    max_attempt: dict = {}
    for i, e in enumerate(L):
        mid = e["message_id"]
        if BIND_RE.match(mid) and mid not in names:
            rej("unbound_binding", f"ledger[{i}] {mid}")
        t = e["type"]
        cur = state.get(mid)
        if t in AUDIT:
            if (
                t == "deduplicated"
                and (e["queue"], e["idempotency_key"]) not in key_digest
            ):
                rej("illegal_transition", f"ledger[{i}] deduplicated for unknown key")
            if t == "conflicted":
                if (e["queue"], e["idempotency_key"]) not in rejected_digests:
                    rej(
                        "illegal_transition",
                        f"ledger[{i}] conflicted without a conflict receipt",
                    )
                if (
                    e["payload_digest"]
                    != rejected_digests[(e["queue"], e["idempotency_key"])]
                ):
                    rej("digest_mismatch", f"ledger[{i}] conflicted digest")
            continue
        allowed, nxt = TRANSITIONS[t]
        if cur in TERMINAL:
            rej("post_terminal_transition", f"ledger[{i}] {t} after {cur}")
        if cur not in allowed:
            rej("illegal_transition", f"ledger[{i}] {t} from {cur}")
        if t == "enqueued":
            k = e.get("idempotency_key")
            if k is not None:
                k = (e["queue"], k)
                if k not in key_digest:
                    rej(
                        "digest_mismatch",
                        f"ledger[{i}] enqueued key {k} has no accepting op",
                    )
                if e["payload_digest"] != key_digest[k]:
                    rej("digest_mismatch", f"ledger[{i}] key {k}")
            max_attempt[mid] = 0
        if t == "leased":
            if e["attempt"] != max_attempt.get(mid, 0) + 1:
                rej(
                    "attempt_mismatch",
                    f"ledger[{i}] leased attempt {e['attempt']} expected {max_attempt.get(mid, 0) + 1}",
                )
            max_attempt[mid] = e["attempt"]
            live_attempt[mid] = e["attempt"]
        if t in ("extended", "acked", "nacked", "lease_expired"):
            if live_attempt.get(mid) != e["attempt"]:
                rej(
                    "attempt_mismatch",
                    f"ledger[{i}] {t} attempt {e['attempt']} but live lease is {live_attempt.get(mid)}",
                )
            if t != "extended":
                live_attempt.pop(mid, None)
        state[mid] = nxt
    print(f"[ok] vector {v['name']}: {len(v['ops'])} ops, {len(L)} events")


def check_pair(a_path: str, b_path: str) -> None:
    """Exactly one differing path, where an added or removed subtree counts once."""

    def diff(a, b, path=()):
        if isinstance(a, dict) and isinstance(b, dict):
            for k in set(a) | set(b):
                if k not in a or k not in b:
                    yield path + (k,)
                else:
                    yield from diff(a[k], b[k], path + (k,))
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                yield path
            else:
                for i, (x, y) in enumerate(zip(a, b)):
                    yield from diff(x, y, path + (i,))
        elif a != b:
            yield path

    n = len(list(diff(json.load(open(a_path)), json.load(open(b_path)))))
    if n != 1:
        print(
            f"[!!] {b_path} differs from {a_path} in {n} fields, expected 1",
            file=sys.stderr,
        )
        sys.exit(1)


def check_profile(path: str) -> None:
    p = json.load(open(path))
    en = set(p["runtime"]["enabled_capabilities"])
    co = set(p["build"]["compiled_capabilities"])
    if not en <= co:
        print(
            f"[!!] enabled capabilities not compiled: {sorted(en - co)}",
            file=sys.stderr,
        )
        sys.exit(1)
    if p["runtime"]["selected_backend"] not in p["build"]["compiled_backends"]:
        print("[!!] selected backend not compiled", file=sys.stderr)
        sys.exit(1)


def main(argv: list[str]) -> int:
    mode = argv[1]
    try:
        if mode == "vector":
            check_vector(argv[2], argv[3])
        elif mode == "vectors":
            base = argv[2]
            for group, names in REQUIRED_VECTORS.items():
                for n in names:
                    p = os.path.join(base, "vectors", group, n + ".json")
                    if not os.path.isfile(p):
                        print(f"reject:missing_inventory {group}/{n}", file=sys.stderr)
                        return 1
            for group in sorted(os.listdir(os.path.join(base, "vectors"))):
                d = os.path.join(base, "vectors", group)
                for f in sorted(os.listdir(d)):
                    if f.endswith(".json"):
                        check_vector(base, os.path.join(d, f))
        elif mode == "pair":
            check_pair(argv[2], argv[3])
        elif mode == "profile":
            check_profile(argv[2])
        else:
            print(__doc__)
            return 2
    except Reject as r:
        print(str(r), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
