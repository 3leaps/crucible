#!/usr/bin/env python3
"""RFC 8785 JSON Canonicalization Scheme (JCS).

Standard-library only. Reads one JSON document from stdin or a file path
and writes canonical UTF-8 bytes to stdout with no trailing newline.

This is conformance-gate materialization for contract: service-job/v0.
It is not a consumer library. jq -S is not JCS and must not be used as
the digest oracle.
"""

from __future__ import annotations

import json
import math
import sys
from typing import Any


def jcs_dumps(value: Any) -> str:
    return _encode(value)


def _encode(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite numbers are not permitted in JCS")
        if value == 0.0:
            return "0"
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ",".join(_encode(item) for item in value) + "]"
    if isinstance(value, dict):
        keys = sorted(value.keys(), key=lambda key: key.encode("utf-16-be"))
        parts = [
            json.dumps(key, ensure_ascii=False) + ":" + _encode(value[key]) for key in keys
        ]
        return "{" + ",".join(parts) + "}"
    raise TypeError(f"unsupported type for JCS: {type(value)!r}")


def main(argv: list[str]) -> int:
    if len(argv) > 2 or (len(argv) == 2 and argv[1] in {"-h", "--help"}):
        sys.stderr.write("usage: rfc8785-canonicalize.py [input.json]\n")
        return 2
    raw = sys.stdin.read() if len(argv) == 1 else open(argv[1], encoding="utf-8").read()
    document = json.loads(raw)
    sys.stdout.write(jcs_dumps(document))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
