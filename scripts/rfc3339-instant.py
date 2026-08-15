#!/usr/bin/env python3
"""Portable RFC3339 instant helper for contract: agent-wait/v0.

Standard-library only. No GNU or BSD date(1). Invalid or timezone-naive
timestamps exit nonzero immediately. Comparisons use verified numeric
instants (timezone-aware datetime, reported as integer epoch seconds).
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone


def parse_rfc3339(text: str) -> datetime:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("timestamp must be a non-empty RFC3339 string")
    if "T" not in text and "t" not in text:
        raise ValueError(f"RFC3339 timestamp must be a date-time: {text!r}")
    normalized = text
    if text.endswith(("Z", "z")):
        normalized = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"unparseable RFC3339 timestamp: {text!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"RFC3339 timestamp must include an offset: {text!r}")
    return parsed.astimezone(timezone.utc)


def epoch_seconds(text: str) -> int:
    return int(parse_rfc3339(text).timestamp())


def compare(left: str, right: str) -> int:
    a = parse_rfc3339(left)
    b = parse_rfc3339(right)
    if a < b:
        return -1
    if a > b:
        return 1
    return 0


def self_test() -> None:
    failures: list[str] = []

    def expect_reject(label: str, text: str) -> None:
        try:
            parse_rfc3339(text)
        except ValueError:
            return
        failures.append(f"{label}: expected reject of {text!r}")

    expect_reject("empty", "")
    expect_reject("whitespace", "   ")
    expect_reject("garbage", "not-a-timestamp")
    expect_reject("date-only", "2026-08-15")
    expect_reject("naive", "2026-08-15T17:00:00")
    expect_reject("space-separator", "2026-08-15 17:00:00Z")

    if epoch_seconds("1970-01-01T00:00:00Z") != 0:
        failures.append("epoch 1970-01-01T00:00:00Z must be 0")
    if epoch_seconds("1970-01-01T00:00:01Z") != 1:
        failures.append("epoch 1970-01-01T00:00:01Z must be 1")
    if epoch_seconds("1970-01-01T00:00:00+00:00") != 0:
        failures.append("epoch +00:00 must match Z")

    if compare("1970-01-01T00:00:00Z", "1970-01-01T00:00:00+00:00") != 0:
        failures.append("equality: Z vs +00:00")
    if compare("1970-01-01T01:00:00+01:00", "1970-01-01T00:00:00Z") != 0:
        failures.append("equality: +01:00 vs Z")
    if compare("1970-01-01T00:00:00Z", "1970-01-01T00:00:01Z") != -1:
        failures.append("before: 00:00:00Z < 00:00:01Z")
    if compare("1970-01-01T00:00:01Z", "1970-01-01T00:00:00Z") != 1:
        failures.append("after: 00:00:01Z > 00:00:00Z")
    if compare("2026-08-15T17:00:00Z", "2026-08-15T17:00:00Z") != 0:
        failures.append("equality: identical instants")

    if failures:
        raise ValueError("; ".join(failures))


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] == "--self-test":
        try:
            self_test()
        except ValueError as exc:
            sys.stderr.write(f"rfc3339-instant self-test failed: {exc}\n")
            return 1
        return 0
    if len(argv) == 3 and argv[1] == "--epoch":
        try:
            sys.stdout.write(f"{epoch_seconds(argv[2])}\n")
        except ValueError as exc:
            sys.stderr.write(f"rfc3339-instant: {exc}\n")
            return 1
        return 0
    if len(argv) == 4 and argv[1] == "--compare":
        try:
            sys.stdout.write(f"{compare(argv[2], argv[3])}\n")
        except ValueError as exc:
            sys.stderr.write(f"rfc3339-instant: {exc}\n")
            return 1
        return 0
    sys.stderr.write(
        "usage: rfc3339-instant.py --epoch TIMESTAMP\n"
        "       rfc3339-instant.py --compare A B\n"
        "       rfc3339-instant.py --self-test\n"
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
