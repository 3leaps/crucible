#!/usr/bin/env python3
"""Validate a profile's schema and local graph references; never resolve remote pins."""

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schemas/classifiers/v0/agent-interface-profile.schema.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unique_by(items, key):
    result = {}
    for item in items:
        identity = item[key]
        require(identity not in result, f"duplicate {key}: {identity}")
        result[identity] = item
    return result


def validate_references(profile):
    """Requires schema-valid input. Enforces the standard's local graph rules."""
    endpoints = unique_by(profile["endpoints"], "endpoint_id")
    bindings = unique_by(profile["bindings"], "binding_id")
    unique_by(profile["delivery"]["signals"], "signal_id")
    agents = [key for key, value in endpoints.items() if value["role"] == "agent"]
    require(len(agents) == 1, "exactly one agent endpoint required")
    require(
        any(value["role"] == "controller" for value in endpoints.values()),
        "controller endpoint required",
    )
    neighbors = {key: set() for key in endpoints}
    for binding in bindings.values():
        left, right = binding["initiator"], binding["acceptor"]
        require(left in endpoints and right in endpoints, "unresolved binding endpoint")
        require(left != right, "binding endpoints must be distinct")
        neighbors[left].add(right)
        neighbors[right].add(left)
    seen = set()
    pending = [agents[0]]
    while pending:
        node = pending.pop()
        if node not in seen:
            seen.add(node)
            pending.extend(neighbors[node] - seen)
    require(seen == set(endpoints), "all endpoints must connect to the agent")
    for signal in profile["delivery"]["signals"]:
        require(signal["binding_ref"] in bindings, "unresolved signal binding")
        binding = bindings[signal["binding_ref"]]
        require(
            signal["emitter"] in (binding["initiator"], binding["acceptor"]),
            "signal emitter must be a binding endpoint",
        )


def validate_file(path):
    goneat = shutil.which("goneat")
    require(goneat is not None, "goneat is required")
    subprocess.run(
        [
            goneat,
            "validate",
            "data",
            "--schema-file",
            str(SCHEMA),
            "--ref-dir",
            str(SCHEMA.parent),
            "--data",
            str(path),
        ],
        check=True,
    )
    validate_references(json.loads(path.read_text(encoding="utf-8")))


def main():
    if len(sys.argv) != 2:
        print(
            "usage: validate-agent-interface-profile.py PROFILE.json", file=sys.stderr
        )
        return 2
    try:
        validate_file(Path(sys.argv[1]))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"invalid agent interface profile: {error}", file=sys.stderr)
        return 1
    print("[ok] agent interface profile schema and references passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
