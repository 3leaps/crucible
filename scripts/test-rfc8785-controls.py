#!/usr/bin/env python3
"""Conformance and CLI controls for scripts/rfc8785-canonicalize.py."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts/rfc8785-canonicalize.py"

_spec = importlib.util.spec_from_file_location("jcs", SCRIPT)
assert _spec is not None and _spec.loader is not None
jcs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(jcs)


def run_cli(
    *args: str, stdin_bytes: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    cmd = [sys.executable, str(SCRIPT), *args]
    with subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE if stdin_bytes is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        out, err = proc.communicate(stdin_bytes)
        return subprocess.CompletedProcess(cmd, proc.returncode, out, err)


def all_66_noncharacters() -> list[int]:
    cps = list(range(0xFDD0, 0xFDF0))
    for plane in range(17):
        cps.append((plane << 16) | 0xFFFE)
        cps.append((plane << 16) | 0xFFFF)
    assert len(cps) == 66
    return cps


def json_u_escape(cp: int) -> str:
    if cp <= 0xFFFF:
        return f"\\u{cp:04x}"
    offset = cp - 0x10000
    high = 0xD800 | (offset >> 10)
    low = 0xDC00 | (offset & 0x3FF)
    return f"\\u{high:04x}\\u{low:04x}"


def test_noncharacters() -> None:
    nonchars = all_66_noncharacters()
    for neighbor in (
        0xFDCF,
        0xFDF0,
        0xFFFD,
        0x10000,
        0x1FFFD,
        0x20000,
        0x10FFFD,
    ):
        assert not jcs.is_unicode_noncharacter(neighbor), (
            f"U+{neighbor:04X} must be scalar"
        )
        ch = chr(neighbor)
        raw = f'{{"{ch}":"{ch}"}}'
        loaded = jcs.jcs_loads(raw)
        assert jcs.jcs_dumps(loaded) == raw

    for cp in nonchars:
        assert jcs.is_unicode_noncharacter(cp), f"U+{cp:04X} must be noncharacter"
        ch = chr(cp)
        esc = json_u_escape(cp)

        # 1. Raw UTF-8 string value and object member key via jcs_loads
        for raw_doc in (f'"{ch}"', f'{{"{ch}":1}}'):
            try:
                jcs.jcs_loads(raw_doc)
            except ValueError as exc:
                assert "noncharacter" in str(exc), f"U+{cp:04X}: unexpected error {exc}"
            else:
                raise AssertionError(f"jcs_loads accepted raw noncharacter U+{cp:04X}")

        # 2. Escaped \uXXXX / surrogate-pair string value and object key via jcs_loads
        for esc_doc in (
            f'"{esc}"',
            f'{{"{esc}":1}}',
            f'"{esc.upper().replace("U", "u")}"',
        ):
            try:
                jcs.jcs_loads(esc_doc)
            except ValueError as exc:
                assert "noncharacter" in str(exc), f"U+{cp:04X}: unexpected error {exc}"
            else:
                raise AssertionError(
                    f"jcs_loads accepted escaped noncharacter U+{cp:04X}"
                )

        # 3. Direct in-memory jcs_dumps on string values and dict keys
        for obj in (ch, {ch: 1}, {"v": ch}):
            try:
                jcs.jcs_dumps(obj)
            except ValueError as exc:
                assert "noncharacter" in str(exc), f"U+{cp:04X}: unexpected error {exc}"
            else:
                raise AssertionError(f"jcs_dumps accepted noncharacter U+{cp:04X}")

    # 4. Subprocess CLI spot-checks across BMP and supplementary planes
    for sample_cp in (
        0xFDD0,
        0xFDEF,
        0xFFFE,
        0xFFFF,
        0x1FFFE,
        0x1FFFF,
        0x10FFFE,
        0x10FFFF,
    ):
        for payload in (
            f'"{chr(sample_cp)}"'.encode("utf-8"),
            f'"{json_u_escape(sample_cp)}"'.encode("ascii"),
            f'{{"{json_u_escape(sample_cp)}":true}}'.encode("ascii"),
        ):
            proc = run_cli(stdin_bytes=payload)
            assert proc.returncode == 1, f"CLI accepted U+{sample_cp:04X}"
            assert proc.stdout == b"", f"CLI wrote stdout on rejected U+{sample_cp:04X}"


def test_integer_domain() -> None:
    # Admitted exact binary64 integers and canonical ES6 round-trip forms
    admitted = [
        ("0", "0"),
        ("-0", "0"),
        ("9007199254740991", "9007199254740991"),
        ("-9007199254740991", "-9007199254740991"),
        ("9007199254740992", "9007199254740992"),
        ("-9007199254740992", "-9007199254740992"),
        ("18446744073709551616", "18446744073709552000"),
        ("18446744073709552000", "18446744073709552000"),
        ("-18446744073709552000", "-18446744073709552000"),
        (str(2**100), "1.2676506002282294e+30"),
    ]
    for raw_tok, want_canon in admitted:
        val = jcs.jcs_loads(raw_tok)
        assert jcs.jcs_dumps(val) == want_canon, (
            f"{raw_tok} -> {jcs.jcs_dumps(val)} != {want_canon}"
        )

    # --check accepts canonical ES6 spelling of 2^64 and rejects uncanonical 2^64
    assert run_cli("--check", stdin_bytes=b"18446744073709552000").returncode == 0
    assert run_cli("--check", stdin_bytes=b"18446744073709551616").returncode == 1

    # Refused imprecise or overflowing integer tokens (including >4300 digits)
    refused = [
        "9007199254740993",
        "-9007199254740993",
        "18446744073709551615",
        "18446744073709552001",
        "9" * 310,
        "-" + "9" * 310,
        "1" + "0" * 5000,
    ]
    for raw_tok in refused:
        try:
            jcs.jcs_loads(raw_tok)
        except ValueError as exc:
            assert "integer_outside_binary64" in str(exc), f"{raw_tok}: {exc}"
        else:
            raise AssertionError(
                f"jcs_loads accepted out-of-domain integer {raw_tok[:32]}..."
            )

    proc = run_cli(stdin_bytes=("1" + "0" * 5000).encode("ascii"))
    assert proc.returncode == 1 and proc.stdout == b""

    # Direct in-memory huge Python int must raise ValueError, not OverflowError
    try:
        jcs.jcs_dumps(10**400)
    except ValueError as exc:
        assert "integer_outside_binary64" in str(exc)
    else:
        raise AssertionError("jcs_dumps accepted 10**400")


def test_cli_modes() -> None:
    sample_in = b'{"b": 2, "a": [1.0, 1e21]}'
    want_canon = b'{"a":[1,1e+21],"b":2}'
    want_digest = "sha256:" + hashlib.sha256(want_canon).hexdigest()

    # Default mode
    proc = run_cli(stdin_bytes=sample_in)
    assert proc.returncode == 0 and proc.stdout == want_canon
    proc_dash = run_cli("-", stdin_bytes=sample_in)
    assert proc_dash.returncode == 0 and proc_dash.stdout == want_canon

    # --check
    assert run_cli("--check", stdin_bytes=want_canon).returncode == 0
    assert run_cli("--check", stdin_bytes=sample_in).returncode == 1
    assert run_cli("--check", stdin_bytes=want_canon + b"\n").returncode == 1
    assert run_cli("--check", stdin_bytes=b"-0").returncode == 1

    # --digest
    proc_dig = run_cli("--digest", stdin_bytes=sample_in)
    assert proc_dig.returncode == 0
    assert proc_dig.stdout == f"{want_digest}\n".encode("ascii")

    # --vector
    proc_vec = run_cli("--vector", stdin_bytes=sample_in)
    assert proc_vec.returncode == 0
    assert proc_vec.stdout.endswith(b"\n")
    vec_line = proc_vec.stdout[:-1]
    assert run_cli("--check", stdin_bytes=vec_line).returncode == 0
    vec_doc = json.loads(vec_line.decode("utf-8"))
    assert list(vec_doc.keys()) == ["byte_length", "canonical", "digest", "scheme"]
    assert vec_doc["byte_length"] == len(want_canon)
    assert vec_doc["canonical"].encode("utf-8") == want_canon
    assert vec_doc["digest"] == want_digest
    assert vec_doc["scheme"] == "jcs/rfc8785"

    # --ndjson-array and --head N
    ndjson_valid = b'{"b":2,"a":1}\n{"d":4,"c":3}\n{"e":5}\n'
    proc_nd = run_cli("--ndjson-array", stdin_bytes=ndjson_valid)
    assert proc_nd.returncode == 0
    assert proc_nd.stdout == b'[{"a":1,"b":2},{"c":3,"d":4},{"e":5}]'

    # --ndjson-array --head 2 ignores torn/corrupted bytes after line 2
    damaged_tail = b'{"b":2,"a":1}\n{"d":4,"c":3}\n{"torn":\xff'
    proc_head = run_cli("--ndjson-array", "--head", "2", stdin_bytes=damaged_tail)
    assert proc_head.returncode == 0
    assert proc_head.stdout == b'[{"a":1,"b":2},{"c":3,"d":4}]'

    proc_head_dig = run_cli(
        "--ndjson-array", "--head=2", "--digest", stdin_bytes=damaged_tail
    )
    assert proc_head_dig.returncode == 0
    expected_prefix_dig = (
        "sha256:" + hashlib.sha256(b'[{"a":1,"b":2},{"c":3,"d":4}]').hexdigest() + "\n"
    ).encode("ascii")
    assert proc_head_dig.stdout == expected_prefix_dig

    # NDJSON framing refusals (exit 1)
    for bad_ndjson in (
        b"",
        b'{"a":1}',
        b'{"a":1}\r\n',
        b'{"a":1}\n\n',
        b'{"a":1}\n   \n',
    ):
        p = run_cli("--ndjson-array", stdin_bytes=bad_ndjson)
        assert p.returncode == 1 and p.stdout == b""

    # --head exceeding available lines -> exit 1
    p_short = run_cli("--ndjson-array", "--head", "4", stdin_bytes=ndjson_valid)
    assert p_short.returncode == 1 and p_short.stdout == b""

    # --sort-set
    unsorted_set = b'[{"stream":"b","seq":2},{"stream":"a","seq":1}]'
    sorted_set = b'[{"seq":1,"stream":"a"},{"seq":2,"stream":"b"}]'
    proc_set = run_cli("--sort-set", stdin_bytes=unsorted_set)
    assert proc_set.returncode == 0 and proc_set.stdout == sorted_set
    assert run_cli("--sort-set", "--check", stdin_bytes=sorted_set).returncode == 0
    assert run_cli("--sort-set", "--check", stdin_bytes=unsorted_set).returncode == 1

    # --sort-set duplicate refusals (including reordered keys and numeric equivalents)
    for dup_set in (
        b'[{"a":1,"b":2},{"b":2,"a":1}]',
        b"[1, 1.0]",
        b'["x","x"]',
    ):
        p_dup = run_cli("--sort-set", stdin_bytes=dup_set)
        assert p_dup.returncode == 1 and p_dup.stdout == b""
        assert b"duplicate_set_element" in p_dup.stderr

    # --sort-set non-array top-level refusals
    for non_arr in (b"{}", b"123", b'"s"', b"null", b"true"):
        p_na = run_cli("--sort-set", stdin_bytes=non_arr)
        assert p_na.returncode == 1 and p_na.stdout == b""

    # Composing --ndjson-array + --sort-set + --vector
    ndjson_set = b'{"id":"b"}\n{"id":"a"}\n'
    p_comp = run_cli("--ndjson-array", "--sort-set", "--vector", stdin_bytes=ndjson_set)
    assert p_comp.returncode == 0
    comp_doc = json.loads(p_comp.stdout.decode("utf-8"))
    assert comp_doc["canonical"] == '[{"id":"a"},{"id":"b"}]'

    # Limits (--max-bytes, --max-depth, --max-object-members, --max-string-bytes)
    assert run_cli("--max-bytes", "2", stdin_bytes=b"{}").returncode == 0
    assert run_cli("--max-bytes", "1", stdin_bytes=b"{}").returncode == 1
    assert run_cli("--max-depth", "2", stdin_bytes=b"[[]]").returncode == 0
    assert run_cli("--max-depth", "1", stdin_bytes=b"[[]]").returncode == 1
    assert run_cli("--max-object-members", "1", stdin_bytes=b'{"a":1}').returncode == 0
    assert (
        run_cli("--max-object-members", "1", stdin_bytes=b'{"a":1,"b":2}').returncode
        == 1
    )
    assert run_cli("--max-string-bytes", "3", stdin_bytes=b'"abc"').returncode == 0
    assert run_cli("--max-string-bytes", "2", stdin_bytes=b'"abc"').returncode == 1

    # Usage errors (exit 2) and missing file (exit 4)
    for bad_args in (
        ("--check", "--digest"),
        ("--check", "--vector"),
        ("--digest", "--vector"),
        ("--ndjson-array", "--check"),
        ("--head", "1"),
        ("--ndjson-array", "--head", "0"),
        ("--ndjson-array", "--head", "-1"),
        ("--ndjson-array", "--head", "abc"),
        ("--ndjson-array", "--head", "1_0"),
        ("--max-bytes", "1_000"),
        ("--max-bytes", " 5"),
        ("--max-depth", "+5"),
        ("--unknown-flag",),
        ("a.json", "b.json"),
    ):
        p_use = run_cli(*bad_args, stdin_bytes=b"{}")
        assert p_use.returncode == 2, (
            f"expected exit 2 for {bad_args}, got {p_use.returncode}"
        )

    with tempfile.TemporaryDirectory() as tmp:
        missing = Path(tmp) / "does-not-exist.json"
        p_miss = run_cli(str(missing))
        assert p_miss.returncode == 4


def test_durable_record_cut_digest_parity() -> None:
    """Verify --ndjson-array --head N --digest matches durable-record/v1 cut_digest."""
    vec_path = ROOT / "schemas/durable-record/v1/vectors/continuation-reviewed.json"
    vec = json.loads(vec_path.read_text(encoding="utf-8"))
    source_journal = vec["source_journal"]
    ndjson_bytes = (
        "\n".join(json.dumps(entry) for entry in source_journal) + "\n"
    ).encode("utf-8")
    dest_open = vec["journal"][0]
    continues = dest_open["continues"]
    cut_seq = continues["cut_seq"]
    want_cut_digest = continues["cut_digest"]

    proc = run_cli(
        "--ndjson-array",
        "--head",
        str(cut_seq),
        "--digest",
        stdin_bytes=ndjson_bytes,
    )
    assert proc.returncode == 0
    assert proc.stdout.decode("ascii").strip() == want_cut_digest


def test_deep_nesting_and_refusal_codes() -> None:
    for depth in (600, 1500):
        arr_bytes = (b"[" * depth) + (b"]" * depth)
        p_ok = run_cli("--max-depth", "5000", stdin_bytes=arr_bytes)
        assert p_ok.returncode == 0, (
            f"depth {depth} failed: {p_ok.stderr.decode('utf-8', 'replace')}"
        )
        assert p_ok.stdout == arr_bytes

        p_lim = run_cli("--max-depth", str(depth - 1), stdin_bytes=arr_bytes)
        assert p_lim.returncode == 1 and p_lim.stdout == b""
        assert p_lim.stderr.startswith(b"jcs: too_deep:")
        assert b"Traceback" not in p_lim.stderr

        # Direct in-memory tree for jcs_dumps and jcs_loads
        obj_tree: object = 1
        for _ in range(depth):
            obj_tree = {"b": 0, "a": obj_tree}
        dumped = jcs.jcs_dumps(obj_tree)
        reloaded = jcs.jcs_loads(dumped, max_depth=5000)
        assert jcs.jcs_dumps(reloaded) == dumped

    precedence_cases: list[tuple[tuple[str, ...], bytes, bytes]] = [
        ((), b"NaN", b"jcs: invalid_json:"),
        ((), b"Infinity", b"jcs: invalid_json:"),
        ((), b"-Infinity", b"jcs: invalid_json:"),
        ((), b'"\\uD800', b"jcs: lone_surrogate:"),
        ((), b'"\\uD800\\u12"', b"jcs: invalid_json:"),
        ((), b'{"a":1,"a":2,"b":01}', b"jcs: duplicate_member:"),
        ((), b'{"a":01,"a":2}', b"jcs: invalid_json:"),
        (("--max-object-members", "2"), b'{"a":1,"b":2,"a":3}', b"jcs: too_large:"),
        (("--max-object-members", "2"), b'{"a":1,"b":2,}', b"jcs: invalid_json:"),
    ]
    for extra_args, payload, want_prefix in precedence_cases:
        proc = run_cli(*extra_args, stdin_bytes=payload)
        assert proc.returncode == 1 and proc.stdout == b"", (
            f"expected refusal on {payload!r}"
        )
        assert proc.stderr.startswith(want_prefix), (
            f"{payload!r}: expected stderr prefix {want_prefix!r}, got {proc.stderr!r}"
        )


def test_optional_conformance_corpus() -> None:
    corpus_env = os.environ.get("JCS_CONFORMANCE_DIR", "").strip()
    if not corpus_env:
        return
    corpus_dir = Path(corpus_env)
    manifest = json.loads((corpus_dir / "cases.json").read_text(encoding="utf-8"))
    cases = manifest["cases"]
    code_re = re.compile(r"^jcs: ([a-z_0-9]+)")
    for case in cases:
        if "generate" in case:
            gen = case["generate"]
            data = (gen["prefix"] + gen["unit"] * gen["count"] + gen["suffix"]).encode(
                "utf-8"
            )
        else:
            data = (corpus_dir / case["input"]).read_bytes()
        cli_args: list[str] = []
        for k, v in case.get("limits", {}).items():
            cli_args.extend(["--" + k.replace("_", "-"), str(v)])
        proc = run_cli(*cli_args, stdin_bytes=data)
        expect = case["expect"]
        if expect == "ok":
            assert proc.returncode == 0, (
                f"{case['id']}: expected ok, got {proc.stderr!r}"
            )
            want_out = (
                data
                if case["output"] == "=input"
                else (corpus_dir / case["output"]).read_bytes()
            )
            assert proc.stdout == want_out, f"{case['id']}: canonical bytes mismatch"
        else:
            assert proc.returncode == 1 and proc.stdout == b"", (
                f"{case['id']}: expected refusal {expect}, got rc={proc.returncode}"
            )
            err_text = proc.stderr.decode("utf-8", "replace")
            assert "Traceback" not in err_text, f"{case['id']}: traceback: {err_text}"
            m = code_re.match(err_text)
            got_code = m.group(1) if m else ""
            assert got_code == expect, (
                f"{case['id']}: expected code {expect!r}, got {got_code!r} ({err_text!r})"
            )
    print(f"    [ok] JCS conformance corpus passed ({len(cases)}/{len(cases)} cases)")


def main() -> int:
    test_noncharacters()
    test_integer_domain()
    test_cli_modes()
    test_deep_nesting_and_refusal_codes()
    test_durable_record_cut_digest_parity()
    test_optional_conformance_corpus()
    print(
        "    [ok] RFC 8785 domain (66 noncharacters, binary64 ints), deep nesting, and CLI modes passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
