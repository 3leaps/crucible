#!/usr/bin/env python3
"""RFC 8785 JSON Canonicalization Scheme (JCS).

Standard-library only. Reads one JSON document from stdin or a file path
and writes canonical UTF-8 bytes to stdout with no trailing newline.

Numbers follow ECMA-262 Number::toString (RFC 8785 §3.2.2.3) and are
restricted to the I-JSON numeric domain (RFC 7493): finite IEEE 754
binary64 values that convert without precision loss. Non-finite values
and integers that are not exactly representable as binary64 are rejected.

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
        return _encode_string(value)
    if isinstance(value, int) and not isinstance(value, bool):
        return _encode_number(value)
    if isinstance(value, float):
        return _encode_number(value)
    if isinstance(value, list):
        return "[" + ",".join(_encode(item) for item in value) + "]"
    if isinstance(value, dict):
        keys = sorted(value.keys(), key=lambda key: key.encode("utf-16-be"))
        parts = [_encode_string(key) + ":" + _encode(value[key]) for key in keys]
        return "{" + ",".join(parts) + "}"
    raise TypeError(f"unsupported type for JCS: {type(value)!r}")


def _encode_string(value: str) -> str:
    # ECMA-262 QuoteJSONString / JSON.stringify (RFC 8785 §3.2.2.2).
    chunks = ['"']
    for char in value:
        code = ord(char)
        if char == '"':
            chunks.append('\\"')
        elif char == "\\":
            chunks.append("\\\\")
        elif char == "\b":
            chunks.append("\\b")
        elif char == "\f":
            chunks.append("\\f")
        elif char == "\n":
            chunks.append("\\n")
        elif char == "\r":
            chunks.append("\\r")
        elif char == "\t":
            chunks.append("\\t")
        elif code < 0x20 or code == 0x2028 or code == 0x2029:
            chunks.append(f"\\u{code:04x}")
        else:
            chunks.append(char)
    chunks.append('"')
    return "".join(chunks)


def _require_ijson_number(value: int | float) -> float:
    if isinstance(value, bool):
        raise TypeError("bool is not a JCS number")
    if isinstance(value, int):
        as_float = float(value)
        if not math.isfinite(as_float) or as_float != value:
            raise ValueError("integer is outside the I-JSON IEEE 754 binary64 domain")
        return as_float
    if not math.isfinite(value):
        raise ValueError("non-finite numbers are not permitted in JCS")
    return value


def _encode_number(value: int | float) -> str:
    """ECMA-262 Number::toString as required by RFC 8785 §3.2.2.3.

    Digit sequences come from Python's shortest round-trip str(float);
    exponent zero-padding and the 1e-6 / 1e21 notation thresholds are
    then applied so the result matches ES6/V8, not json.dumps(float).
    """
    number = _require_ijson_number(value)
    if number == 0.0:
        return "0"

    rendered = str(number)
    if "n" in rendered:
        raise ValueError("non-finite numbers are not permitted in JCS")

    sign = ""
    if rendered[0] == "-":
        sign = "-"
        rendered = rendered[1:]

    exp_str = ""
    exp_val = 0
    exp_at = rendered.find("e")
    if exp_at > 0:
        exp_str = rendered[exp_at:]
        # Python writes e-07; ECMAScript writes e-7.
        if exp_str[2:3] == "0":
            exp_str = exp_str[:2] + exp_str[3:]
        rendered = rendered[:exp_at]
        exp_val = int(exp_str[1:])

    first = rendered
    dot = ""
    last = ""
    dot_at = rendered.find(".")
    if dot_at > 0:
        dot = "."
        first = rendered[:dot_at]
        last = rendered[dot_at + 1 :]
    if last == "0":
        dot = ""
        last = ""

    # k <= n <= 21: integer decimal, no exponent.
    if 0 < exp_val < 21:
        first += last
        last = ""
        dot = ""
        exp_str = ""
        pad = exp_val - len(first)
        while pad >= 0:
            pad -= 1
            first += "0"
    # -6 < n <= 0: 0.000... form (1e-6 threshold).
    elif -7 < exp_val < 0:
        last = first + last
        first = "0"
        dot = "."
        exp_str = ""
        lead = exp_val
        while lead < -1:
            lead += 1
            last = "0" + last

    return sign + first + dot + last + exp_str


def main(argv: list[str]) -> int:
    if len(argv) > 2 or (len(argv) == 2 and argv[1] in {"-h", "--help"}):
        sys.stderr.write("usage: rfc8785-canonicalize.py [input.json]\n")
        return 2
    raw = sys.stdin.read() if len(argv) == 1 else open(argv[1], encoding="utf-8").read()
    try:
        document = json.loads(raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"jcs: invalid JSON: {exc}\n")
        return 1
    try:
        sys.stdout.write(jcs_dumps(document))
    except ValueError as exc:
        sys.stderr.write(f"jcs: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
