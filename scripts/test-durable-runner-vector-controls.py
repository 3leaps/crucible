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
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

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


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"[!!] {msg}", file=sys.stderr)


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

print("    durable-runner: semantic rejects are detected...")
rej = sorted((BASE / "rejects/semantic").glob("reject-*.json"))
if not rej:
    fail("no semantic rejects")
for p in rej:
    d = json.loads(p.read_text())
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
inv = json.loads((BASE / "vectors/INVENTORY.json").read_text())
vectors = {}
for p in sorted((BASE / "vectors").rglob("*.json")):
    if p.name != "INVENTORY.json":
        vectors[p.stem] = json.loads(p.read_text())
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

if failures:
    print(
        f"[!!] durable-runner behavioral controls: {len(failures)} failure(s)",
        file=sys.stderr,
    )
    sys.exit(1)
print(
    f"[ok] durable-runner behavioral controls passed ({len(vectors)} vectors, {len(guards)} guards)"
)
