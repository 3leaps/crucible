#!/usr/bin/env python3
"""Write a copy of the durable-queue validator with the old ts() formatting.

Mutation control for scripts/test-durable-queue-controls.sh. The old reference
Model took the timestamp fraction from at_ms alone, so a fractional clock_start
lost its fraction. This restores that formatting in a copy; the control requires
the copy to reject the fractional clock_start vector.

Usage: mutate-durable-queue-ts.py SOURCE DEST
"""

import sys

FIXED = (
    "    frac = d.microsecond // 1000\n"
    '    return s + (".%03d" % frac if frac else "") + "Z"\n'
)
OLD = '    return s + (".%03d" % (ms % 1000) if ms % 1000 else "") + "Z"\n'


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[1], encoding="utf-8") as f:
        text = f.read()
    if text.count(FIXED) != 1:
        print(
            "error: ts() fraction lines not found; update the mutation control",
            file=sys.stderr,
        )
        return 1
    with open(argv[2], "w", encoding="utf-8") as f:
        f.write(text.replace(FIXED, OLD))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
