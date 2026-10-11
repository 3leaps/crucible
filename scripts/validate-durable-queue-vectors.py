#!/usr/bin/env python3
"""Fixture-integrity checker for contract: durable-queue/v0.

Standard library plus the repository's RFC 8785 materializer (strict loader
and encoder). Executes each vector's op script against a small reference
consistency model, an in-memory fold of the normative rules under the virtual
clock, and requires the hand-authored expectations and ledger to match the
model exactly: receipts, delivery counts, lease outcomes, every ledger event
and every atomic group. The model is a checker for fixtures. It is not a
conformance oracle for implementations and not a queue; the executing harness
lives in the adopting repository.

Modes:
  vectors <base>               required inventory plus every vector under <base>/vectors
  vector  <base> <file>        one vector; exit 1 and print 'reject:<reason>' on the first defect
  pair    <baseline> <reject>  the two documents differ in exactly one path (a subtree counts once)
  profile <file>               runtime.enabled_capabilities subset of build.compiled_capabilities
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
from datetime import datetime, timedelta, timezone
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
    "fanout": [
        "atomic-fanout",
        "fanout-stale-parent",
        "fanout-repeat-dedup",
        "fanout-mixed-children",
    ],
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
OPS = {
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
}
MODELED = {
    "enqueue",
    "claim",
    "extend",
    "ack",
    "nack",
    "fail",
    "fan_out",
    "stats",
    "redrive",
    "sweep",
    "purge",
}
BIND_RE = re.compile(r"^\$[a-z][a-z0-9_]*$")
PATH_RE = re.compile(r"^deliveries\[(\d+)\]\.(lease|message)$")


class Reject(Exception):
    pass


def rej(reason: str, detail: str) -> None:
    raise Reject(f"reject:{reason} {detail}")


def load_strict(path: str):
    try:
        return jcs.jcs_loads(open(path, encoding="utf-8").read())
    except ValueError as e:
        rej("ingest", f"{path}: {e}")


def goneat_validate(schema: str, doc) -> bool:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(doc, f, ensure_ascii=False)
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
    try:
        return "sha256:" + hashlib.sha256(jcs.jcs_dumps(o).encode("utf-8")).hexdigest()
    except ValueError as e:
        rej("payload_domain", f"payload outside the I-JSON domain: {e}")


def ts(start: datetime, ms: int) -> str:
    d = start + timedelta(milliseconds=ms)
    s = d.strftime("%Y-%m-%dT%H:%M:%S")
    return s + (".%03d" % (ms % 1000) if ms % 1000 else "") + "Z"


class Model:
    """Reference consistency model: the normative fold, driven by ops."""

    def __init__(self, queue: str, start: datetime, window_ms):
        self.queue = queue
        self.start = start
        self.window_ms = window_ms
        self.msgs: dict = {}  # id -> record
        self.keys: dict = {}  # (queue, key) -> (id, digest, enqueued_ms)
        self.ledger: list = []
        self.seq = 0
        self.next_id = 1
        self.tokens = 0
        self.names: dict = {}  # $name -> concrete id / lease
        self.other: dict = {}  # (queue, id) for messages on queues the vector does not model

    # ---- ledger
    def group(self, events: list, ms: int) -> None:
        g = self.seq + 1
        for e in events:
            self.seq += 1
            self.ledger.append(
                {
                    "v": 0,
                    "seq": self.seq,
                    "group": g,
                    "group_size": len(events),
                    "queue": self.queue,
                    "at": ts(self.start, ms),
                    **e,
                }
            )

    # ---- admission
    def admit(self, m: dict, ms: int, parent_id=None):
        k = m.get("idempotency_key")
        d = identity_digest(m)
        if k is not None:
            live = self.keys.get((self.queue, k))
            if live and (
                self.window_ms == "unbounded" or ms - live[2] < self.window_ms
            ):
                if live[1] == d:
                    return (
                        live[0],
                        "deduplicated",
                        {
                            "type": "deduplicated",
                            "message_id": live[0],
                            "idempotency_key": k,
                        },
                    )
                return (
                    live[0],
                    "conflict",
                    {
                        "type": "conflicted",
                        "message_id": live[0],
                        "idempotency_key": k,
                        "payload_digest": d,
                    },
                )
        mid = f"m{self.next_id}"
        self.next_id += 1
        stored = {"v": 0, "id": mid, "queue": self.queue, **m}
        if parent_id:
            stored["parent_id"] = parent_id
        rec = {
            "id": mid,
            "stored": stored,
            "state": "delayed" if m.get("not_before") else "ready",
            "not_before_ms": None,
            "max_attempts": m.get("max_attempts", 5),
            "attempt": 0,
            "lease": None,
            "payload": m.get("payload"),
            "key": k,
        }
        if m.get("not_before"):
            rec["not_before_ms"] = int(
                (
                    datetime.fromisoformat(m["not_before"].replace("Z", "+00:00"))
                    - self.start.replace(tzinfo=timezone.utc)
                ).total_seconds()
                * 1000
            )
        self.msgs[mid] = rec
        if k is not None:
            self.keys[(self.queue, k)] = (mid, d, ms)
        ev = {"type": "enqueued", "message_id": mid, "payload_digest": d}
        if k is not None:
            ev["idempotency_key"] = k
        if parent_id:
            ev["parent_id"] = parent_id
        if m.get("not_before"):
            ev["not_before"] = m["not_before"]
        return mid, "accepted", ev

    def expire_due(self, ms: int) -> list:
        out = []
        for rec in self.msgs.values():
            if rec["state"] == "leased" and rec["lease"]["until_ms"] <= ms:
                evs = [
                    {
                        "type": "lease_expired",
                        "message_id": rec["id"],
                        "attempt": rec["attempt"],
                    }
                ]
                rec["lease"] = None
                if rec["attempt"] >= rec["max_attempts"]:
                    rec["state"] = "dead"
                    evs.append(
                        {
                            "type": "dead_lettered",
                            "message_id": rec["id"],
                            "reason": "max_attempts",
                        }
                    )
                else:
                    rec["state"] = "ready"
                out.append(evs)
        return out

    def check_lease(self, lease: dict):
        if not isinstance(lease, dict):
            rej("binding", f"lease is not a lease value: {lease!r}")
        rec = self.msgs.get(lease.get("message_id"))
        if rec is None or lease.get("queue") != self.queue:
            return None, "stale_lease" if rec is not None or lease.get(
                "queue"
            ) != self.queue else "unknown_message"
        if rec["state"] != "leased" or rec["lease"]["token"] != lease.get("token"):
            return rec, "stale_lease"
        return rec, "ok"

    # ---- ops
    def run(self, op: dict, idx: int) -> dict:
        ms = op["at_ms"]
        p = copy.deepcopy(op["params"])
        name = op["op"]
        if name == "enqueue":
            if p["queue"] != self.queue:
                # a second queue exists only so wrong-queue leases can be exercised;
                # its history is out of scope for the vector's ledger
                receipts = []
                for _m in p["messages"]:
                    mid = f"m{self.next_id}"
                    self.next_id += 1
                    receipts.append({"message_id": mid, "outcome": "accepted"})
                return {"receipts": receipts}
            receipts, evs = [], []
            for m in p["messages"]:
                mid, outc, ev = self.admit(m, ms)
                receipts.append({"message_id": mid, "outcome": outc})
                evs.append(ev)
            self.group(evs, ms)
            return {"receipts": receipts}
        if name == "claim":
            if p["queue"] != self.queue:
                rej("vector_shape", f"ops[{idx}] claim on unmodeled queue")
            # invariant 4: a claim that finds expired leases appends their expiry
            # (and any dead-lettering) in the same atomic group as the new leases
            evs = [e for grp in self.expire_due(ms) for e in grp]
            ready = [
                r
                for r in self.msgs.values()
                if r["state"] == "ready"
                or (
                    r["state"] == "delayed"
                    and r["not_before_ms"] is not None
                    and r["not_before_ms"] <= ms
                )
            ]
            ready = [
                r
                for r in ready
                if r["not_before_ms"] is None or r["not_before_ms"] <= ms
            ]
            ready.sort(key=lambda r: int(r["id"][1:]))
            deliveries = []
            for rec in ready[: p["max"]]:
                rec["attempt"] += 1
                self.tokens += 1
                rec["lease"] = {
                    "token": f"t{self.tokens}",
                    "until_ms": ms + p["lease_ms"],
                }
                rec["state"] = "leased"
                lease = {
                    "queue": self.queue,
                    "message_id": rec["id"],
                    "token": rec["lease"]["token"],
                    "attempt": rec["attempt"],
                    "until": ts(self.start, rec["lease"]["until_ms"]),
                }
                deliveries.append(
                    {"message": copy.deepcopy(rec["stored"]), "lease": lease}
                )
                evs.append(
                    {
                        "type": "leased",
                        "message_id": rec["id"],
                        "attempt": rec["attempt"],
                        "worker": p["worker"],
                        "lease_until": lease["until"],
                    }
                )
            if evs:
                self.group(evs, ms)
            return {"deliveries": deliveries}
        if name in ("ack", "nack", "extend", "fail"):
            outcomes, evs = [], []
            for lease in p["leases"]:
                rec, st = self.check_lease(lease)
                outcomes.append(st)
                if st != "ok":
                    continue
                if name == "ack":
                    rec["state"] = "done"
                    rec["lease"] = None
                    evs.append(
                        {
                            "type": "acked",
                            "message_id": rec["id"],
                            "attempt": rec["attempt"],
                        }
                    )
                elif name == "extend":
                    rec["lease"]["until_ms"] = ms + p["lease_ms"]
                    evs.append(
                        {
                            "type": "extended",
                            "message_id": rec["id"],
                            "attempt": rec["attempt"],
                            "lease_until": ts(self.start, rec["lease"]["until_ms"]),
                        }
                    )
                elif name == "nack":
                    rec["lease"] = None
                    ev = {
                        "type": "nacked",
                        "message_id": rec["id"],
                        "attempt": rec["attempt"],
                        "reason": p["reason"],
                    }
                    if rec["attempt"] >= rec["max_attempts"]:
                        rec["state"] = "dead"
                        evs.append(ev)
                        evs.append(
                            {
                                "type": "dead_lettered",
                                "message_id": rec["id"],
                                "reason": "max_attempts",
                            }
                        )
                    else:
                        rec["state"] = "delayed" if p["retry_after_ms"] > 0 else "ready"
                        rec["not_before_ms"] = (
                            ms + p["retry_after_ms"]
                            if p["retry_after_ms"] > 0
                            else None
                        )
                        if p["retry_after_ms"] > 0:
                            ev["not_before"] = ts(self.start, rec["not_before_ms"])
                        evs.append(ev)
                else:
                    rec["state"] = "dead"
                    rec["lease"] = None
                    evs.append(
                        {
                            "type": "dead_lettered",
                            "message_id": rec["id"],
                            "reason": p["reason"],
                        }
                    )
            if evs:
                self.group(evs, ms)
            return {"outcomes": outcomes}
        if name == "fan_out":
            rec, st = self.check_lease(p["parent"])
            if st != "ok":
                return {"outcome": st, "receipts": []}
            receipts, evs = [], []
            for m in p["children"]:
                mid, outc, ev = self.admit(m, ms, parent_id=rec["id"])
                receipts.append({"message_id": mid, "outcome": outc})
                evs.append(ev)
            rec["state"] = "done"
            rec["lease"] = None
            evs.append(
                {"type": "acked", "message_id": rec["id"], "attempt": rec["attempt"]}
            )
            self.group(evs, ms)
            return {"outcome": "ok", "receipts": receipts}
        if name == "sweep":
            n = 0
            for evs in self.expire_due(ms):
                self.group(evs, ms)
                n += 1
            return {"expired": n, "purged": 0}
        if name == "stats":
            c = {"ready": 0, "delayed": 0, "leased": 0, "dead": 0}
            for r in self.msgs.values():
                if r["state"] == "delayed" and (
                    r["not_before_ms"] is None or r["not_before_ms"] <= ms
                ):
                    c["ready"] += 1
                elif r["state"] in c:
                    c[r["state"]] += 1
            return c
        if name == "redrive":
            outs, evs = [], []
            for mid in p["message_ids"]:
                rec = self.msgs.get(mid)
                if rec is None:
                    outs.append("unknown_message")
                elif rec["state"] != "dead":
                    outs.append("not_dead")
                else:
                    rec["state"] = "ready"
                    rec["max_attempts"] = rec["attempt"] + rec["max_attempts"]
                    rec["not_before_ms"] = None
                    outs.append("ok")
                    evs.append({"type": "redriven", "message_id": mid})
            if evs:
                self.group(evs, ms)
            return {"outcomes": outs}
        if name == "purge":
            n, evs = 0, []
            for mid in p["message_ids"]:
                rec = self.msgs.get(mid)
                if rec and rec["state"] not in ("done", "gone"):
                    rec["state"] = "gone"
                    rec["lease"] = None
                    n += 1
                    evs.append(
                        {"type": "purged", "message_id": mid, "reason": p["reason"]}
                    )
            if evs:
                self.group(evs, ms)
            return {"purged": n}
        rej(
            "unmodeled_op",
            f"ops[{idx}] {name} is not covered by the consistency model; vectors may not expect on it",
        )


def resolve(obj, names: dict):
    """Replace $name tokens and $rebind forms with bound concrete values."""
    if isinstance(obj, str) and BIND_RE.match(obj):
        if obj not in names:
            rej("unbound_binding", obj)
        return names[obj]
    if isinstance(obj, dict):
        if "$rebind" in obj:
            src = obj["$rebind"]
            if src not in names or not isinstance(names[src], dict):
                rej("unbound_binding", f"{src} is not a bound lease")
            out = copy.deepcopy(names[src])
            for k, v in obj.items():
                if k != "$rebind":
                    out[k] = v
            return out
        return {k: resolve(v, names) for k, v in obj.items()}
    if isinstance(obj, list):
        return [resolve(v, names) for v in obj]
    return obj


def match(expected, actual, names: dict, where: str) -> None:
    """Structural match where $name in expected binds-or-compares to actual."""
    if isinstance(expected, str) and BIND_RE.match(expected):
        if expected in names:
            if names[expected] != actual:
                rej(
                    "expectation_mismatch",
                    f"{where}: {expected} bound to {names[expected]!r} but model produced {actual!r}",
                )
        else:
            names[expected] = actual
        return
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            rej(
                "expectation_mismatch",
                f"{where}: expected object, model produced {actual!r}",
            )
        for k, v in expected.items():
            if k not in actual:
                rej("expectation_mismatch", f"{where}.{k}: not produced by the model")
            match(v, actual[k], names, f"{where}.{k}")
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(expected) != len(actual):
            rej(
                "expectation_mismatch",
                f"{where}: expected {len(expected) if isinstance(expected, list) else '?'} items, model produced {len(actual) if isinstance(actual, list) else actual!r}",
            )
        for i, (e, a) in enumerate(zip(expected, actual)):
            match(e, a, names, f"{where}[{i}]")
        return
    if expected != actual:
        rej(
            "expectation_mismatch",
            f"{where}: expected {expected!r}, model produced {actual!r}",
        )


def check_vector(base: str, path: str) -> None:
    v = load_strict(path)
    for k in (
        "name",
        "requires",
        "min_idempotency_window_ms",
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
    if "virtual_clock" not in v["requires"]:
        rej("vector_shape", "deterministic vectors require virtual_clock")
    w = v["min_idempotency_window_ms"]
    if w != "unbounded" and (not isinstance(w, int) or w < 1):
        rej("vector_shape", "min_idempotency_window_ms")
    ce = os.path.join(base, "control-exchange.schema.json")
    le = os.path.join(base, "ledger-event.schema.json")
    start = datetime.fromisoformat(v["clock_start"].replace("Z", "+00:00")).replace(
        tzinfo=None
    )
    model = Model(v["queue"], start, w)
    names: dict = {}
    last_ms = -1
    for i, op in enumerate(v["ops"]):
        if set(op) - {"at_ms", "op", "params", "expect", "bind"}:
            rej(
                "vector_shape",
                f"ops[{i}] unknown keys {sorted(set(op) - {'at_ms', 'op', 'params', 'expect', 'bind'})}",
            )
        if op.get("op") not in OPS:
            rej("op_schema", f"ops[{i}] unknown op {op.get('op')!r}")
        if not isinstance(op.get("at_ms"), int) or op["at_ms"] < last_ms:
            rej("vector_shape", f"ops[{i}] at_ms must be a non-decreasing integer")
        last_ms = op["at_ms"]
        params = copy.deepcopy(op.get("params", {}))
        if "leases" in params:
            params["leases"] = [resolve(x, names) for x in params["leases"]]
        if "parent" in params:
            params["parent"] = resolve(params["parent"], names)
        if "message_ids" in params:
            params["message_ids"] = [resolve(x, names) for x in params["message_ids"]]
        # queue names, worker, messages, children and payloads are data and are never substituted
        if not goneat_validate(ce, {"id": str(i), "op": op["op"], "params": params}):
            rej("op_schema", f"ops[{i}] {op['op']} params invalid")
        if op["op"] not in MODELED:
            if "expect" in op or "bind" in op:
                rej("unmodeled_op", f"ops[{i}] {op['op']} cannot carry expect or bind")
            continue
        result = model.run({**op, "params": params}, i)
        if op["op"] == "claim":
            exp = dict(op.get("expect") or {})
            if "delivery_count" not in exp:
                rej("expect_shape", f"ops[{i}] claim needs expect.delivery_count")
            if exp.pop("delivery_count") != len(result["deliveries"]):
                rej(
                    "expectation_mismatch",
                    f"ops[{i}] delivery_count: model produced {len(result['deliveries'])}",
                )
            match(exp, result, names, f"ops[{i}].expect")
        else:
            if "expect" not in op:
                rej("expect_shape", f"ops[{i}] {op['op']} needs expect")
            match(op["expect"], result, names, f"ops[{i}].expect")
        # typed response validation of the model's own result (guards the schema, not the vector)
        if not goneat_validate(
            ce, {"id": str(i), "op": op["op"], "ok": True, "result": result}
        ):
            rej(
                "expect_schema",
                f"ops[{i}] model result does not validate as a typed result (schema drift)",
            )
        for b, pth in (op.get("bind") or {}).items():
            if not BIND_RE.match(b):
                rej("vector_shape", f"bad bind name {b}")
            m = PATH_RE.match(pth)
            if not m or op["op"] != "claim":
                rej(
                    "binding",
                    f"ops[{i}] bind path {pth!r} is not deliveries[n].lease|message on a claim",
                )
            n = int(m.group(1))
            if n >= len(result["deliveries"]):
                rej(
                    "binding",
                    f"ops[{i}] bind path {pth!r} out of range ({len(result['deliveries'])} deliveries)",
                )
            names[b] = result["deliveries"][n][m.group(2)]
    # ---- ledger: hand-authored must equal the model's, event for event, with $name binding
    L = v["ledger"]
    if len(L) != len(model.ledger):
        rej(
            "ledger_mismatch",
            f"vector has {len(L)} events, model produced {len(model.ledger)}",
        )
    for i, (e, m) in enumerate(zip(L, model.ledger)):
        if not goneat_validate(le, e):
            rej("ledger_schema", f"ledger[{i}]")
        if set(e) != set(m):
            rej(
                "ledger_mismatch",
                f"ledger[{i}] fields {sorted(set(e) ^ set(m))} differ from model",
            )
        for k in m:
            if k in ("message_id", "parent_id"):
                if isinstance(e[k], str) and BIND_RE.match(e[k]) and e[k] not in names:
                    rej(
                        "unbound_binding",
                        f"ledger[{i}].{k} {e[k]} was never bound by an op",
                    )
                match(e[k], m[k], names, f"ledger[{i}].{k}")
            elif e[k] != m[k]:
                rej(
                    "ledger_mismatch",
                    f"ledger[{i}].{k}: vector {e[k]!r}, model {m[k]!r}",
                )
    print(
        f"[ok] vector {v['name']}: {len(v['ops'])} ops, {len(L)} events, model-consistent"
    )


def check_pair(a_path: str, b_path: str) -> None:
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

    n = len(list(diff(load_strict(a_path), load_strict(b_path))))
    if n != 1:
        print(
            f"[!!] {b_path} differs from {a_path} in {n} fields, expected 1",
            file=sys.stderr,
        )
        sys.exit(1)


def check_profile(path: str) -> None:
    p = load_strict(path)
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
                    if not os.path.isfile(
                        os.path.join(base, "vectors", group, n + ".json")
                    ):
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
