#!/usr/bin/env python3
"""Logical fixture controls for durable-record/v1, not a storage implementation.

Validation interpreter: Python >= 3.9. Standard library only. External invocation:
goneat, the JSON Schema validator named by the contract (PDR-0006 Rule 2b).
Reuses v0 fixture/canonicalization helpers; makes no independent-reader claim.
"""

from __future__ import annotations

import copy
import hashlib
from datetime import timedelta
import importlib.util
import json
import re
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "schemas/durable-record/v1"
_spec = importlib.util.spec_from_file_location(
    "record_v0", ROOT / "scripts/validate-durable-record-fixtures.py"
)
legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(legacy)


def load(path):
    return legacy.load(str(path))


def digest(value):
    return legacy.digest(value)


def pin(entry):
    r = entry["record"]
    return dict(
        stream=r["stream"],
        record_id=r["record_id"],
        revision=r["revision"],
        digest=entry["digest"],
    )


def pin_key(p):
    return p["stream"], p["record_id"], p["revision"], p["digest"]


def require(ok, reason):
    if not ok:
        raise legacy.Reject(reason, "durable-record/v1")


class State:
    def __init__(self, window):
        require(type(window) is int and window > 0, "idempotency_window")
        self.window = window
        self.journal = []
        self.records = {}
        self.holds = {}
        self.active = set()
        self.keys = {}
        self.retired = set()
        self.stream = None
        self.failure_model = None

    def remember(self, key, identity, at, receipt):
        self.keys[key] = (identity, legacy.instant(at), copy.deepcopy(receipt))

    def live(self, key, at):
        prior = self.keys.get(key)
        if prior and timedelta(0) <= legacy.instant(at) - prior[1] < timedelta(
            milliseconds=self.window
        ):
            return prior
        return None

    def ingest(self, e):
        # The v0 journal invariants also apply to the expanded v1 vocabulary.
        require(e["v"] == 1, "journal_version")
        # Validate complete groups; partial groups cannot be observed by requests.
        if e["seq"] == e["group"] + e["group_size"] - 1:
            legacy.check_journal(self.journal + [e], "v1")
        if self.journal:
            require(
                legacy.instant(e["at"]) >= legacy.instant(self.journal[-1]["at"]),
                "journal_time",
            )
        typ = e["type"]
        if typ == "stream_opened":
            self.stream, self.failure_model = e["stream"], e["failure_model"]
        elif typ in ("appended", "revised"):
            require(e["record"]["record_id"] not in self.retired, "retired_record")
            require(
                self.live(e["idempotency_key"], e["at"]) is None, "accepted_key_reuse"
            )
            self.records[pin_key(pin(e))] = e["record"]
            receipt = dict(
                v=1,
                kind="receipt",
                stream=self.stream,
                idempotency_key=e["idempotency_key"],
                outcome=typ,
                pin=pin(e),
                seq=e["seq"],
                failure_model=self.failure_model,
            )
            if "body_status" in e:
                receipt["body_status"] = e["body_status"]
            self.remember(
                e["idempotency_key"], ("content", e["digest"]), e["at"], receipt
            )
        elif typ in ("tombstoned", "untombstoned"):
            r = e["request"]
            require(e["request_digest"] == digest(r), "request_digest")
            require(
                typ == ("tombstoned" if r["action"] == "tombstone" else "untombstoned"),
                "operation_type",
            )
            # An accepted journal line cannot be a replay of an already-live key.
            require(
                self.live(r["idempotency_key"], e["at"]) is None, "accepted_key_reuse"
            )
            reason = self.refusal(r, e["at"])
            require(reason is None, reason or "operation")
            receipt = self.receipt(r, e["seq"])
            self.apply(r, e["seq"])
            self.remember(
                r["idempotency_key"], ("protection", digest(r)), e["at"], receipt
            )
        elif typ == "retired":
            require(
                any(k[1] == e["record_id"] for k in self.records), "target_not_found"
            )
            self.retired.add(e["record_id"])
        self.journal.append(copy.deepcopy(e))

    def refusal(self, r, at):
        if r["stream"] != self.stream or r["target"]["stream"] != self.stream:
            return "target_not_found"
        record = self.records.get(pin_key(r["target"]))
        if record is None:
            return "target_not_found"
        if r["scope"] == "body" and (
            "body" not in record
            or any(record["body"][k] != r["body"][k] for k in ("digest", "length"))
        ):
            return "body_mismatch"
        if legacy.instant(r["observed_at"]) > legacy.instant(at):
            return "observation_order"
        if r["action"] == "restore":
            if r["restores"] not in self.active:
                return "hold_not_active"
            hold = self.holds[r["restores"]]
            if any(r.get(k) != hold.get(k) for k in ("target", "scope", "body")):
                return "hold_mismatch"
            if legacy.instant(r["observed_at"]) < legacy.instant(hold["observed_at"]):
                return "observation_order"
        return None

    def receipt(self, r, seq):
        return dict(
            v=1,
            stream=r["stream"],
            idempotency_key=r["idempotency_key"],
            outcome="tombstoned" if r["action"] == "tombstone" else "untombstoned",
            seq=seq,
            request_digest=digest(r),
            failure_model=self.failure_model,
        )

    def apply(self, r, seq):
        if r["action"] == "tombstone":
            self.holds[seq] = copy.deepcopy(r)
            self.active.add(seq)
        else:
            self.active.remove(r["restores"])

    def request(self, r, at):
        legacy.check_journal(self.journal, "v1")
        require(
            legacy.instant(at) >= legacy.instant(self.journal[-1]["at"]), "journal_time"
        )
        # Stream scope and live-key replay precede target/current-state checks.
        prior = (
            self.live(r["idempotency_key"], at) if r["stream"] == self.stream else None
        )
        if prior:
            if prior[0] == ("protection", digest(r)):
                return copy.deepcopy(prior[2])
            reason = "idempotency_conflict"
        else:
            reason = self.refusal(r, at)
        if reason:
            return dict(
                v=1,
                stream=r["stream"],
                idempotency_key=r["idempotency_key"],
                outcome=reason,
            )
        seq = len(self.journal) + 1
        receipt = self.receipt(r, seq)
        self.ingest(
            dict(
                v=1,
                seq=seq,
                group=seq,
                group_size=1,
                stream=self.stream,
                type=receipt["outcome"],
                at=at,
                request=copy.deepcopy(r),
                request_digest=receipt["request_digest"],
            )
        )
        return receipt

    def blocked(self, p):
        record = self.records[pin_key(p)]
        for seq in self.active:
            h = self.holds[seq]
            if h["scope"] == "record" and p["record_id"] == h["target"]["record_id"]:
                return True
            if h["scope"] == "revision" and p == h["target"]:
                return True
            if (
                h["scope"] == "body"
                and "body" in record
                and all(record["body"][k] == h["body"][k] for k in ("digest", "length"))
            ):
                return True
        return False

    def verify_receipt(self, received):
        seq = received["seq"]
        require(1 <= seq <= len(self.journal), "receipt_mismatch")
        entry = self.journal[seq - 1]
        require(entry["type"] in ("tombstoned", "untombstoned"), "receipt_mismatch")
        require(received == self.receipt(entry["request"], seq), "receipt_mismatch")
        return {"outcome": "receipt_verified"}

    def reconcile(self, key, at, attempted_at):
        legacy.check_journal(self.journal, "v1")
        require(
            legacy.instant(at) >= legacy.instant(self.journal[-1]["at"]), "journal_time"
        )
        result = dict(
            v=1,
            kind="reconciliation",
            stream=self.stream,
            idempotency_key=key,
            attempted_at=attempted_at,
            result="unknown",
            reason="coverage_unprovable",
        )
        prior = self.live(key, at)
        if prior:
            result.pop("reason")
            result.update(result="found", receipt=copy.deepcopy(prior[2]))
        # This logical interpreter has no authoritative coverage provider.
        # It never manufactures not_found from an absent cache entry.
        return result

    def use(self, r):
        legacy.check_journal(self.journal, "v1")

        def refused(reason):
            return dict(outcome="refused", reason=reason)

        if (
            r["stream"] != self.stream
            or r["protection_state"] != "verified"
            or r["protection_cut"] != len(self.journal)
            or r["current_cut"] != len(self.journal)
        ):
            return refused("protection_unavailable")
        selected = {pin_key(p) for p in r["selection"]}
        omitted = {pin_key(p) for p in r["omitted"]}
        if not (selected | omitted) <= self.records.keys():
            return refused("target_not_found")
        if selected & omitted or selected | omitted != self.records.keys():
            return refused("export_selection")
        if r["inherited_block"] or any(self.blocked(p) for p in r["selection"]):
            return refused("protected_use")
        if r["purpose"] == "serve" and any(
            p["record_id"] in self.retired for p in r["selection"]
        ):
            return refused("protected_use")
        supplied = {}
        for b in r["bodies"]:
            raw = bytes.fromhex(b["hex"])
            if (
                "sha256:" + hashlib.sha256(raw).hexdigest() != b["digest"]
                or b["digest"] in supplied
            ):
                return refused("body_closure")
            supplied[b["digest"]] = len(raw)
        needed = {}
        for key in selected:
            body = self.records[key].get("body")
            if body is not None:
                if (
                    body["digest"] in needed
                    and needed[body["digest"]] != body["length"]
                ):
                    return refused("body_closure")
                needed[body["digest"]] = body["length"]
        if any(k not in needed or needed[k] != v for k, v in supplied.items()):
            return refused("body_closure")
        if r["closure"] == "full_content" and supplied != needed:
            return refused("body_closure")
        return dict(
            outcome="allowed",
            closure=r["closure"],
            selection=r["selection"],
            omitted=r["omitted"],
            protection_cut=r["protection_cut"],
        )


def evaluate(case):
    s = State(case["window_ms"])
    legacy.check_journal(case["journal"], "v1")
    for e in case["journal"]:
        s.ingest(e)
    results = []
    for step in case["steps"]:
        if "request" in step:
            results.append(s.request(step["request"], step["at"]))
        elif "receipt" in step:
            results.append(s.verify_receipt(step["receipt"]))
        elif "reconcile" in step:
            results.append(s.reconcile(**step["reconcile"]))
        elif "entry" in step:
            s.ingest(step["entry"])
            results.append({"outcome": "journaled"})
        else:
            results.append(s.use(step["use"]))
    legacy.check_journal(s.journal, "v1")
    return {
        "results": results,
        "active_holds": sorted(s.active),
        "journal_size": len(s.journal),
    }


def shape(doc, name):
    with tempfile.TemporaryDirectory(prefix="record-v1-shape-") as tmp:
        p = Path(tmp) / "input.json"
        p.write_text(json.dumps(doc), encoding="utf-8")
        result = subprocess.run(
            [
                "goneat",
                "validate",
                "data",
                "--schema-file",
                str(BASE / (name + ".schema.json")),
                "--data",
                str(p),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode not in (0, 1):
            raise RuntimeError(result.stderr)
        return result.returncode == 0


def check_case(case):
    try:
        return evaluate(case)
    except legacy.Reject as e:
        return {"refusal": e.reason}


def main():
    # The content envelope is reused exactly, not a new digest-bearing version.
    original = load(BASE.parent / "v0/record.schema.json")
    assert load(BASE / "record.schema.json")["$defs"] == original["$defs"]
    definitions = {}
    for path in sorted(BASE.glob("*.schema.json")):
        for name, definition in load(path).get("$defs", {}).items():
            if name in definitions:
                assert definition == definitions[name], (path, name)
            definitions[name] = definition
    cases = sorted((BASE / "vectors").glob("*.json"))
    assert cases, "missing conformance corpus"
    rejects = sorted((BASE / "rejects/schema").glob("reject-*.json"))
    inventory = (BASE / "rejects/README.md").read_text()
    listed = re.findall(r"\]\((?:schema/|\.\./vectors/)([^)]+)\)", inventory)
    assert sorted(listed) == sorted(p.name for p in cases + rejects), (
        "fixture inventory drift"
    )
    assert rejects, "missing schema rejects"
    for path in cases:
        c = load(path)
        for e in c["journal"]:
            assert shape(e, "journal-entry"), path
        for step in c["steps"]:
            if "request" in step:
                assert shape(step["request"], "protection-request"), path
            elif "use" in step:
                assert shape(step["use"], "export-request"), path
            elif "receipt" in step:
                assert shape(step["receipt"], "protection-receipt"), path
            elif "entry" in step:
                assert shape(step["entry"], "journal-entry"), path
        got = check_case(c)
        assert got == c["expected"], (path.name, got, c["expected"])
        for result in got.get("results", []):
            if result.get("kind") == "reconciliation":
                assert shape(result, "write-receipt"), (path.name, result)
                continue
            if result["outcome"] in ("journaled", "receipt_verified"):
                continue
            name = (
                "export-result"
                if result["outcome"] in ("allowed", "refused")
                else "protection-receipt"
            )
            assert shape(result, name), (path.name, result)
        print("[ok]", path.name)
    for path in rejects:
        case = load(path)
        assert shape(case["baseline"], case["schema"]), path
        assert not shape(case["reject"], case["schema"]), path
        legacy.check_pair(case["baseline"], case["reject"], path.name)
    for path in sorted((BASE / "examples").glob("*.json")):
        assert shape(load(path), path.name.split(".")[0]), path
        if path.name.startswith("stratum-profile."):
            legacy.check_profile(load(path), path.name)
    # Fixed source mutations: each must flip a committed witness, not just hit code.
    source = Path(__file__).read_text()
    mutations = [
        (
            "return copy.deepcopy(prior[2])",
            'return {"outcome": "broken_replay"}',
            "replay-after-restore",
        ),
        (
            'self.active.remove(r["restores"])',
            "self.active.clear()",
            "independent-holds",
        ),
        ('or r["protection_cut"] != len(self.journal)', "or False", "stale-cut"),
        (
            "return True\n        return False",
            "return False\n        return False",
            "shared-body",
        ),
    ]
    for before, after, witness in mutations:
        assert before in source, before
        ns = {"__name__": "mutation", "__file__": __file__}
        exec(compile(source.replace(before, after, 1), __file__, "exec"), ns)
        c = load(BASE / "vectors" / (witness + ".json"))
        assert ns["check_case"](c) != c["expected"], witness
    print(
        f"Durable-record/v1 logical controls PASS: {len(cases)} vectors; {len(rejects)} schema rejects; 4 mutation witnesses. No store qualification."
    )


if __name__ == "__main__":
    main()
