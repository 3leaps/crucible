#!/usr/bin/env python3
"""Fixture-integrity checker for contract: durable-record/v0.

Standard-library only. Reuses scripts/rfc8785-canonicalize.py for revision
digests. This is conformance-gate material for the contract's fixtures, not a
consumer library or a store implementation.

Usage:
  validate-durable-record-fixtures.py pair <baseline.json> <reject.json>
  validate-durable-record-fixtures.py journal <journal.ndjson>
  validate-durable-record-fixtures.py entry <journal-entry.json>
  validate-durable-record-fixtures.py profile <stratum-profile.json>
  validate-durable-record-fixtures.py receipt-pin <receipt.json> <journal.ndjson>

journal checks: seq gap-free from 1, stream_opened first and only first, one
stream per file, atomic groups contiguous with a consistent final cut, every
digest equals SHA-256 over RFC 8785 bytes of its record, record.stream equals
the line stream, revision chain linear (appended at 1, revised at head + 1 with
supersedes equal to the current head pin), single_revision streams contain no
revised entries, conflicted.current equals the head at that point.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "rfc8785", _here / "rfc8785-canonicalize.py"
)
_jcs = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_jcs)


def fail(reason: str, detail: str) -> None:
    print(f"[!!] {reason}: {detail}", file=sys.stderr)
    sys.exit(1)


def load(path: str):
    try:
        return _jcs.jcs_loads(Path(path).read_text(encoding="utf-8"))
    except ValueError as e:
        fail("ingest", f"{path}: {e}")


def digest(record) -> str:
    return (
        "sha256:" + hashlib.sha256(_jcs.jcs_dumps(record).encode("utf-8")).hexdigest()
    )


def leaf_diff(a, b, path="") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        out: list[str] = []
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                out.append(f"{path}/{k}")
            else:
                out.extend(leaf_diff(a[k], b[k], f"{path}/{k}"))
        return out
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        out = []
        for i, (x, y) in enumerate(zip(a, b)):
            out.extend(leaf_diff(x, y, f"{path}/{i}"))
        return out
    return [] if a == b and type(a) is type(b) else [path or "/"]


def cmd_pair(baseline: str, reject: str) -> None:
    d = leaf_diff(load(baseline), load(reject))
    # A reject that renames a member shows as one removed plus one added path.
    if len(d) != 1 and not (
        len(d) == 2 and d[0].rsplit("/", 1)[0] == d[1].rsplit("/", 1)[0]
    ):
        fail("pair", f"{reject} differs from its baseline at {d}")


def check_entry(e, where: str) -> None:
    if e.get("type") in ("appended", "revised"):
        rec = e["record"]
        if rec.get("stream") != e.get("stream"):
            fail("stream_mismatch", where)
        if digest(rec) != e.get("digest"):
            fail(
                "digest", f"{where}: recorded {e.get('digest')} computed {digest(rec)}"
            )
        sup = rec.get("supersedes")
        if sup is not None and sup["revision"] != rec["revision"] - 1:
            fail("supersedes_revision", where)


def cmd_entry(path: str) -> None:
    check_entry(load(path), path)


def cmd_journal(path: str) -> None:
    lines = [
        ln for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.strip()
    ]
    if not lines:
        fail("empty", path)
    heads: dict[str, dict] = {}
    mode = None
    stream = None
    for i, ln in enumerate(lines, start=1):
        try:
            e = _jcs.jcs_loads(ln)
        except ValueError as ex:
            fail("ingest", f"{path}:{i}: {ex}")
        where = f"{path}:{i}"
        if e["seq"] != i:
            fail("seq_gap", f"{where}: expected seq {i}, found {e['seq']}")
        if stream is None:
            stream = e["stream"]
        elif e["stream"] != stream:
            fail("stream_mismatch", where)
        if (e["type"] == "stream_opened") != (i == 1):
            fail("stream_opened_position", where)
        if e["type"] == "stream_opened":
            mode = e["mode"]
        if not (e["group"] <= e["seq"] < e["group"] + e["group_size"]):
            fail("group", where)
        check_entry(e, where)
        if e["type"] in ("appended", "revised"):
            rec = e["record"]
            rid = rec["record_id"]
            head = heads.get(rid)
            if e["type"] == "appended":
                if head is not None or rec["revision"] != 1:
                    fail("revision_chain", f"{where}: appended over an existing head")
            else:
                if mode == "single_revision":
                    fail("mode_violation", where)
                if (
                    head is None
                    or rec["revision"] != head["revision"] + 1
                    or rec["supersedes"] != head
                ):
                    fail(
                        "revision_chain", f"{where}: supersedes is not the current head"
                    )
            heads[rid] = {"revision": rec["revision"], "digest": e["digest"]}
        elif e["type"] == "conflicted":
            cur = e.get("current")
            if cur is not None and cur != heads.get(e["record_id"]):
                fail(
                    "conflict_current",
                    f"{where}: current is not the head at this point",
                )
            if cur is None and e["record_id"] in heads:
                fail(
                    "conflict_current", f"{where}: current omitted while a head exists"
                )
    last = _jcs.jcs_loads(lines[-1])
    if last["seq"] - last["group"] + 1 != last["group_size"]:
        fail("inconsistent_cut", f"{path}: final group truncated")


def cmd_profile(path: str) -> None:
    p = load(path)
    extra = set(p["runtime"]["enabled_capabilities"]) - set(
        p["build"]["compiled_capabilities"]
    )
    if extra:
        fail("capability_not_compiled", f"{path}: {sorted(extra)}")
    if p["runtime"]["stratum"] not in p["build"]["compiled_strata"]:
        fail("stratum_not_compiled", path)


def cmd_receipt_pin(receipt: str, journal: str) -> None:
    r = load(receipt)
    if r.get("kind") == "reconciliation":
        r = r.get("receipt") or {}
    pin = r.get("pin")
    if pin is None:
        return
    for ln in Path(journal).read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        e = _jcs.jcs_loads(ln)
        if e["seq"] == r["seq"]:
            rec = e.get("record") or {}
            got = {
                "stream": e["stream"],
                "record_id": rec.get("record_id"),
                "revision": rec.get("revision"),
                "digest": e.get("digest"),
            }
            if got != pin:
                fail(
                    "receipt_pin",
                    f"{receipt}: pin does not match journal seq {r['seq']}",
                )
            return
    fail("receipt_pin", f"{receipt}: seq {r['seq']} not in {journal}")


def main(argv: list[str]) -> None:
    cmds = {
        "pair": (cmd_pair, 2),
        "journal": (cmd_journal, 1),
        "entry": (cmd_entry, 1),
        "profile": (cmd_profile, 1),
        "receipt-pin": (cmd_receipt_pin, 2),
    }
    if len(argv) < 2 or argv[1] not in cmds or len(argv) - 2 != cmds[argv[1]][1]:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    cmds[argv[1]][0](*argv[2:])


if __name__ == "__main__":
    main(sys.argv)
