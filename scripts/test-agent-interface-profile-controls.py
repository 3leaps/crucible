#!/usr/bin/env python3
"""Controls for profile shape, cross-references and independent continuity axes."""

import copy
import importlib.util
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schemas/classifiers/v0/agent-interface-profile.schema.json"
EXAMPLES = SCHEMA.parent / "examples/profiles"
spec = importlib.util.spec_from_file_location(
    "profile_validator", ROOT / "scripts/validate-agent-interface-profile.py"
)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    goneat = shutil.which("goneat")
    require(goneat is not None, "goneat is required")
    baseline = json.loads((EXAMPLES / "resident-proxy.json").read_text())
    with tempfile.TemporaryDirectory(prefix="agent-profile-controls-") as directory:
        data = Path(directory) / "profile.json"

        def schema_accepts(profile):
            data.write_text(json.dumps(profile), encoding="utf-8")
            result = subprocess.run(
                [
                    goneat,
                    "validate",
                    "data",
                    "--schema-file",
                    str(SCHEMA),
                    "--ref-dir",
                    str(SCHEMA.parent),
                    "--data",
                    str(data),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            return result.returncode == 0

        def valid(profile, label):
            require(schema_accepts(profile), f"schema rejected valid {label}")
            validator.validate_references(profile)

        def reject_shape(profile, label):
            require(not schema_accepts(profile), f"schema accepted invalid {label}")
            # A refusal only counts if the validator remains operational.
            require(
                schema_accepts(baseline), f"validator failed baseline after {label}"
            )

        def reject_graph(profile, expected):
            require(schema_accepts(profile), "graph control failed at schema layer")
            try:
                validator.validate_references(profile)
            except ValueError as error:
                require(expected in str(error), f"wrong graph failure: {error}")
            else:
                raise ValueError(f"graph control missed: {expected}")

        for path in sorted(EXAMPLES.glob("*.json")):
            valid(json.loads(path.read_text()), path.name)

        # Neither a resident execution nor durable context alone implies resume.
        for lifetime in ("bounded", "resident", "unknown"):
            changed = copy.deepcopy(baseline)
            changed["continuity"]["execution_lifetime"] = lifetime
            valid(changed, f"durable resumable {lifetime}")
        changed = copy.deepcopy(baseline)
        changed["continuity"].update(
            context_persistence="volatile", resume="unsupported"
        )
        valid(changed, "resident volatile without resume")
        for persistence in ("volatile", "unknown"):
            changed = copy.deepcopy(baseline)
            changed["continuity"]["context_persistence"] = persistence
            reject_shape(changed, "resume without declared durable context")

        changed = copy.deepcopy(baseline)
        changed["authorized"] = True
        reject_shape(changed, "authority injection")
        changed = copy.deepcopy(baseline)
        changed["bindings"][0]["transport"] = "http-sse"
        reject_shape(changed, "protocol flattened into carrier")
        changed = copy.deepcopy(baseline)
        changed["bindings"][0]["protocol_stack"] = []
        reject_shape(changed, "empty known protocol stack")
        changed = copy.deepcopy(baseline)
        del changed["bindings"][0]["protocol_stack"][0]["protocol"]["revision"]
        reject_shape(changed, "unpinned protocol")
        changed = copy.deepcopy(baseline)
        changed["bindings"][0]["credentials"] = "not-a-credential"
        reject_shape(changed, "live attachment field")
        changed = copy.deepcopy(baseline)
        changed["delivery"]["signals"][0]["meaning"] = "accepted-and-executed"
        reject_shape(changed, "collapsed evidence")
        changed = copy.deepcopy(baseline)
        changed["delivery"]["signals"][1]["correlation"] = ["logical-session"]
        reject_shape(changed, "execution without operation correlation")
        changed = copy.deepcopy(baseline)
        changed["delivery"]["signals"][0]["meaning"] = "cursor-committed"
        reject_shape(changed, "cursor without registration/outcome")
        for capability in ("deduplication", "reconciliation", "activation"):
            changed = copy.deepcopy(baseline)
            changed["delivery"][capability] = (
                "explicit" if capability == "activation" else "supported"
            )
            changed["delivery"].pop(f"{capability}_contract", None)
            reject_shape(changed, f"{capability} missing contract")
            changed["delivery"][capability] = "unknown"
            changed["delivery"][f"{capability}_contract"] = {
                "id": "example:contract",
                "revision": "1",
            }
            reject_shape(changed, f"unknown {capability} with asserted contract")

        for collection, key in (
            ("endpoints", "endpoint_id"),
            ("bindings", "binding_id"),
        ):
            changed = copy.deepcopy(baseline)
            changed[collection].append(copy.deepcopy(changed[collection][0]))
            reject_graph(changed, f"duplicate {key}")
        changed = copy.deepcopy(baseline)
        changed["delivery"]["signals"].append(
            copy.deepcopy(changed["delivery"]["signals"][0])
        )
        reject_graph(changed, "duplicate signal_id")
        changed = copy.deepcopy(baseline)
        changed["bindings"][0]["acceptor"] = "absent"
        reject_graph(changed, "unresolved binding endpoint")
        changed = copy.deepcopy(baseline)
        changed["bindings"][0]["acceptor"] = "host"
        reject_graph(changed, "binding endpoints must be distinct")
        changed = copy.deepcopy(baseline)
        changed["endpoints"].append({"endpoint_id": "orphan", "role": "intermediary"})
        reject_graph(changed, "all endpoints must connect to the agent")
        changed = copy.deepcopy(baseline)
        changed["endpoints"][1]["role"] = "agent"
        reject_graph(changed, "exactly one agent endpoint")
        changed = copy.deepcopy(baseline)
        changed["endpoints"][0]["role"] = "intermediary"
        reject_graph(changed, "controller endpoint required")
        changed = copy.deepcopy(baseline)
        changed["delivery"]["signals"][0]["binding_ref"] = "absent"
        reject_graph(changed, "unresolved signal binding")
        changed = copy.deepcopy(baseline)
        changed["delivery"]["signals"][0]["emitter"] = "worker"
        reject_graph(changed, "signal emitter must be a binding endpoint")

        # Exercise the actual CLI: both acceptance and the normative refusal path.
        for profile, expected in ((baseline, 0), (changed, 1)):
            data.write_text(json.dumps(profile), encoding="utf-8")
            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts/validate-agent-interface-profile.py"),
                    str(data),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            require(
                result.returncode == expected, f"unexpected CLI exit: {result.stderr}"
            )
    print(
        "[ok] agent interface profile shape, continuity, evidence and reference controls passed"
    )


if __name__ == "__main__":
    main()
