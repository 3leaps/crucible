#!/usr/bin/env python3
"""Check agent vocabulary parity and the value schema's refusal boundaries."""

import copy
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schemas/classifiers/v0/agent-interface.schema.json"
DEFINITIONS = {
    "agent-seat-class": "seatClass",
    "agent-control-surface": "controlSurface",
    "agent-transport": "transport",
    "agent-adapter-confidence": "adapterConfidence",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def parity(schema, dimensions):
    require(set(schema["properties"]) == set(DEFINITIONS), "dimension keys differ")
    for key, definition in DEFINITIONS.items():
        dimension = dimensions[key]
        require(dimension["key"] == key, f"{key}: wrong dimension identity")
        require(dimension["type"] == "categorical", f"{key}: not categorical")
        values = [v["key"] for v in dimension["categorical"]["values"]]
        require(len(values) == len(set(values)), f"{key}: duplicate values")
        require("unknown" in values, f"{key}: missing unknown")
        require(
            schema["properties"][key] == {"$ref": f"#/$defs/{definition}"},
            f"{key}: wrong reference",
        )
        require(
            schema["$defs"][definition]["enum"] == values, f"{key}: schema/config drift"
        )
        index = dimension["categorical"]["index_strategy"]
        require(index["missing_handling"] == "error", f"{key}: missing value defaults")
        require(index["default_order"] == values, f"{key}: display order differs")
        require(
            all(e["value"] in values for e in dimension["examples"]),
            f"{key}: bad example",
        )
    require('"default"' not in json.dumps(schema), "value schema inserts defaults")


def main():
    goneat = shutil.which("goneat")
    require(goneat is not None, "goneat is required")
    schema = json.loads(SCHEMA.read_text())
    dimensions = {
        key: json.loads(
            (ROOT / f"config/classifiers/dimensions/{key}.dimension.json").read_text()
        )
        for key in DEFINITIONS
    }
    parity(schema, dimensions)

    # Prove the parity control detects a one-sided schema enum addition.
    changed = copy.deepcopy(schema)
    changed["$defs"]["transport"]["enum"].append("webhook")
    try:
        parity(changed, dimensions)
    except ValueError as error:
        require(
            "schema/config drift" in str(error), "mutation failed for the wrong reason"
        )
    else:
        raise ValueError("parity control accepted a schema-only vocabulary change")

    with tempfile.TemporaryDirectory(prefix="agent-classifiers-") as directory:
        data = Path(directory) / "instance.json"

        def validate(instance, expected, label):
            data.write_text(json.dumps(instance), encoding="utf-8")
            result = subprocess.run(
                [
                    goneat,
                    "validate",
                    "data",
                    "--schema-file",
                    str(SCHEMA),
                    "--data",
                    str(data),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            require(
                (result.returncode == 0) == expected,
                f"{label}: unexpected validation result\n{result.stdout}\n{result.stderr}",
            )

        for example in sorted(SCHEMA.parent.joinpath("examples").glob("agent-*.json")):
            validate(json.loads(example.read_text()), True, example.name)
        # Every published value works alone: consumers may adopt a subset.
        for key, definition in DEFINITIONS.items():
            for value in schema["$defs"][definition]["enum"]:
                validate({key: value}, True, f"{key}={value}")
            for value in (None, 0, [], "", "invented-value"):
                validate({key: value}, False, f"reject {key}={value!r}")
        validate({}, False, "empty projection")
        validate({"agent-transport": "webhook"}, False, "mechanism is not carrier")
        validate({"agent-transport": "acp-stdio"}, False, "protocol is not carrier")
        validate(
            {"agent-adapter-confidence": "green"}, False, "color is not a machine key"
        )
        validate({"agent-adapter-confidence": 4}, False, "ordinal is not confidence")
        validate(
            {"agent-seat-class": "headless", "authorized": True},
            False,
            "no authority field",
        )
        validate(
            {
                "agent-seat-class": "live",
                "agent-connection-mechanism": "cooperative-wait",
            },
            False,
            "no combined mechanism field",
        )
    print(
        "[ok] agent classifier parity, parity mutation, values and refusal controls passed"
    )


if __name__ == "__main__":
    main()
