#!/usr/bin/env python3
"""Standalone logical contract controls; recipes never resolve host paths.

The graph models stable-tree semantics, not native filesystem qualification.
Only the separate native helper invokes primitive OS availability probes.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import posixpath
import re
import runpy

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "schemas/filesystem-access/v0"
DIRECTORIES = {"directory", "mount_boundary"}


class Refusal(Exception):
    def __init__(self, category, reason=None):
        self.category, self.reason = category, reason
        super().__init__(category if reason is None else f"{category}:{reason}")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def strict(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON member")
            result[key] = value
        return result

    def constant(_):
        raise AssertionError("non-JSON numeric constant")

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def scalar(value):
    if not isinstance(value, str):
        raise Refusal("invalid_name")
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise Refusal("invalid_name") from None


def rooted(value):
    return value.startswith(("/", "\\")) or bool(re.match(r"^[A-Za-z]:", value))


def admitted_components(value, profile, *, link_target=False):
    """F1/F3 ordering; preserve every physical dot/parent component."""
    scalar(value)
    if "\x00" in value:
        raise Refusal("invalid_name")
    if rooted(value):
        if link_target:
            raise Refusal("policy_denied", "escape")
        raise Refusal("invalid_name")
    if not value or len(value) > 4096 or "\\" in value or ":" in value:
        raise Refusal("invalid_name")
    components = value.split("/")
    for component in components:
        if not component:
            raise Refusal("invalid_name")
        if component in (".", ".."):
            if profile == "no-links/v0":
                raise Refusal("invalid_name")
            continue
        stem = component.rstrip(" .").split(".", 1)[0].rstrip(" ")
        # Only ASCII case-insensitivity belongs to reserved-name recognition.
        stem = stem.translate(
            str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        )
        reserved = stem in {"CON", "PRN", "AUX", "NUL"} or (
            len(stem) == 4 and stem[:3] in {"COM", "LPT"} and stem[3] in "123456789¹²³"
        )
        if reserved or component.endswith((".", " ")):
            raise Refusal("invalid_name")
    return components


def parent(path):
    return path.rsplit("/", 1)[0] if "/" in path else ""


def join(current, component):
    return current + "/" + component if current else component


def recipe_tree(nodes):
    tree = {"": {"path": "", "kind": "directory"}}
    for node in nodes:
        path = node["path"]
        require(path not in tree, "duplicate recipe path")
        require(
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}", path) is not None,
            "unsafe recipe path",
        )
        require(
            all(part not in ("", ".", "..") for part in path.split("/")),
            "unsafe recipe component",
        )
        ancestor = parent(path)
        require(
            ancestor in tree and tree[ancestor]["kind"] in DIRECTORIES,
            "missing recipe parent",
        )
        item = copy.deepcopy(node)
        if tree[ancestor].get("outside_root"):
            require(item.get("outside_root", True), "in-root node below outside parent")
            item["outside_root"] = True
        tree[path] = item
    return tree


def walk(components, tree, profile, capabilities, max_hops):
    pending, current, hops = list(components), "", 0
    while pending:
        require(current in tree, "resolver lost held object")
        if tree[current]["kind"] not in DIRECTORIES:
            raise Refusal("wrong_type")
        if tree[current].get("outside_root"):
            raise Refusal("policy_denied", "escape")
        component = pending.pop(0)
        if component == ".":
            continue
        if component == "..":
            if current == "":
                raise Refusal("policy_denied", "escape")
            current = parent(current)
            continue
        next_path = join(current, component)
        node = tree.get(next_path)
        if node is None:
            raise Refusal("not_found")
        if node.get("outside_root"):
            raise Refusal("policy_denied", "escape")
        if capabilities.get("no_xdev") and node["kind"] == "mount_boundary":
            raise Refusal("policy_denied", "cross_device")
        if node["kind"] == "symlink":
            if profile == "no-links/v0":
                raise Refusal("policy_denied", "link_refused")
            if hops >= max_hops:
                raise Refusal("policy_denied", "hop_limit")
            hops += 1
            pending = (
                admitted_components(node["target"], profile, link_target=True) + pending
            )
            continue  # Expand relative to the link's containing physical directory.
        if node["kind"] == "fifo":
            raise Refusal("policy_denied", "special_file")
        current = next_path
    return current


def held_result(case):
    request = case.get("access_request")
    require(isinstance(request, dict), "held operation needs access_request")
    require(request["operation"] == case["operation"], "request/operation mismatch")
    requested = request.get("capabilities", {})
    if (
        requested.get("no_xdev")
        or requested.get("adversary") == "concurrent_rename_resistant"
    ):
        raise Refusal("unsupported_capability")
    table = {}
    for item in case.get("runtime", {}).get("live_handles", []):
        require(item["handle"] not in table, "duplicate live handle reference")
        table[item["handle"]] = item

    def lookup(ref, generation):
        item = table.get(ref)
        if item is None or item["generation"] != generation:
            raise Refusal("io_error")
        return item["object"]

    if case["operation"] == "stat":
        identity = lookup(request["handle"], request["lifetime_generation"])
        return {"outcome": "accepted", "identity": identity}
    left = lookup(request["left_handle"], request["left_generation"])
    right = lookup(request["right_handle"], request["right_generation"])
    if left["kind"] != right["kind"]:
        raise Refusal("unsupported_capability")
    return {"outcome": "accepted", "same_object": left == right}


def resolve(case, state=None):
    """Evaluate inputs only. Expected results are never consulted here."""
    operation = case["operation"]
    embedded = case.get("access_request")
    if operation in ("open_root", "stat", "same_object"):
        require(isinstance(embedded, dict), "root/held operation needs access_request")
        require(embedded["operation"] == operation, "request/operation mismatch")
        require(
            not any(
                key in case
                for key in ("request", "max_bytes", "max_entries", "max_symlink_hops")
            ),
            "duplicate root/held request fields",
        )
    else:
        require(embedded is None, "path operation uses flat request fields only")
    tree = recipe_tree(case["recipe"]) if state is None else state
    if operation in ("stat", "same_object"):
        return held_result(case)
    name, profile = case["name"], case["profile"]
    runtime = case.get("runtime", {})
    if operation == "open_root":
        requested = embedded["capabilities"]
        if (
            requested.get("no_xdev")
            or requested.get("adversary") == "concurrent_rename_resistant"
        ):
            raise Refusal("unsupported_capability")
        node = tree.get(name)
        if node is None:
            raise Refusal("not_found")
        if node["kind"] == "symlink":
            raise Refusal("policy_denied", "link_refused")
        if node["kind"] == "fifo":
            raise Refusal("policy_denied", "special_file")
        if node["kind"] not in DIRECTORIES:
            raise Refusal("wrong_type")
        expected_identity = case.get("access_request", {}).get("expected_identity")
        if (
            expected_identity is not None
            and runtime.get("root_identity") != expected_identity
        ):
            raise Refusal("io_error")
        return {"outcome": "accepted", "resolved_path": name}

    components = admitted_components(name, profile)
    capabilities = case.get("request", {})
    # This evaluator is a stable-tree model; no flag can upgrade it to a
    # concurrent native resolver or prove a larger operation's atomicity.
    if capabilities.get("adversary") == "concurrent_rename_resistant":
        raise Refusal("unsupported_capability")
    if capabilities.get("no_xdev") and not runtime.get("no_xdev_available", False):
        raise Refusal("unsupported_capability")
    max_hops = case.get("max_symlink_hops", 40)
    require(type(max_hops) is int and 1 <= max_hops <= 40, "invalid hop budget")
    if operation == "create_exclusive":
        directory = walk(components[:-1], tree, profile, capabilities, max_hops)
        if tree[directory]["kind"] not in DIRECTORIES:
            raise Refusal("wrong_type")
        leaf = components[-1]
        target = join(directory, leaf)
        if leaf in (".", "..") or target in tree:
            raise Refusal("already_exists")
        tree[target] = {"path": target, "kind": "regular_file", "byte_length": 0}
        if runtime.get("fault_after_create", False):
            raise Refusal("unknown_mutation_outcome")
        return {"outcome": "accepted", "resolved_path": target, "mutation": "created"}

    path = walk(components, tree, profile, capabilities, max_hops)
    node = tree[path]
    if operation == "read_dir":
        if node["kind"] not in DIRECTORIES:
            raise Refusal("wrong_type")
        entries = []
        for key in sorted(tree):
            if not key or parent(key) != path or tree[key].get("outside_root"):
                continue
            entry_name = key.rsplit("/", 1)[-1]
            scalar(entry_name)
            kind = tree[key]["kind"]
            entries.append(
                {
                    "name": entry_name,
                    "kind": "directory"
                    if kind == "mount_boundary"
                    else "other"
                    if kind == "fifo"
                    else kind,
                }
            )
            if len(entries) > case.get("max_entries", 65536):
                raise Refusal("bound_exceeded")
        return {"outcome": "accepted", "resolved_path": path, "entries": entries}
    require(operation == "open_read", "unknown modeled operation")
    if node["kind"] != "regular_file":
        raise Refusal("wrong_type")
    length = node.get("byte_length", 0)
    if length > case.get("max_bytes", 9007199254740991):
        raise Refusal("bound_exceeded")
    return {"outcome": "accepted", "resolved_path": path, "byte_length": length}


def same_json(left, right):
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            same_json(left[key], right[key]) for key in left
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            same_json(a, b) for a, b in zip(left, right)
        )
    return type(left) is type(right) and left == right


def check_case(case, evaluator=resolve):
    state = recipe_tree(case["recipe"])
    before = copy.deepcopy(state)
    try:
        actual = evaluator(case, state)
    except Refusal as refusal:
        actual = {"outcome": "refused", "category": refusal.category}
        if refusal.reason is not None:
            actual["reason"] = refusal.reason
    expected = case["expected"]
    for key, value in expected.items():
        if key != "preserves_nodes":
            require(same_json(actual.get(key), value), case["id"] + ": " + key)
    # All reads/refusals preserve the entire graph, including contents and
    # targets. Only successful create and explicitly ambiguous create may mutate.
    mutating = case["operation"] == "create_exclusive" and (
        actual["outcome"] == "accepted"
        or actual.get("category") == "unknown_mutation_outcome"
    )
    if not mutating or "preserves_nodes" in expected:
        require(state == before, case["id"] + ": mutation-before-refusal")
    if mutating:
        added = set(state) - set(before)
        require(len(added) == 1, case["id"] + ": create must add exactly one node")
        require(
            all(state[key] == value for key, value in before.items()),
            case["id"] + ": create changed existing node",
        )
        require(
            state[next(iter(added))]["kind"] == "regular_file",
            case["id"] + ": nonregular create",
        )
    for path in expected.get("preserves_nodes", []):
        require(path in state, case["id"] + ": missing preserved node")
    return actual


def controls():
    corpus = strict((BASE / "cases.json").read_text(encoding="utf-8"))
    schema = runpy.run_path(str(ROOT / "scripts/filesystem-access-schema-controls.py"))
    require(schema["run_schema_controls"]() > 0, "schema controls")
    native = runpy.run_path(str(ROOT / "scripts/filesystem-access-native-probes.py"))
    native["run_native_probes"]()
    require(
        len({case["id"] for case in corpus["cases"]}) == len(corpus["cases"]),
        "duplicate case id",
    )
    for case in corpus["cases"]:
        check_case(case)

    # Deliberately broken evaluators must fail the same authored expectations.
    witnesses = 0
    for case in corpus["cases"]:
        if case["expected"]["outcome"] == "refused":

            def accept_everything(value, state):
                return {"outcome": "accepted"}

            try:
                check_case(case, accept_everything)
            except AssertionError:
                witnesses += 1
            else:
                raise AssertionError("false acceptance survived corpus")
    case = next(
        value for value in corpus["cases"] if value["id"] == "create-dangling-link"
    )

    def mutate_before_refusal(value, state):
        state["a/new"]["target"] = "changed"
        raise Refusal("already_exists")

    try:
        check_case(case, mutate_before_refusal)
    except AssertionError as error:
        require(
            "mutation-before-refusal" in str(error), "mutation failed for wrong reason"
        )
        witnesses += 1
    else:
        raise AssertionError("mutation before refusal survived")

    indexed = {case["id"]: case for case in corpus["cases"]}

    def collapsed(value, state):
        changed = copy.deepcopy(value)
        changed["name"] = posixpath.normpath(value["name"])
        return resolve(changed, state)

    def unbounded(value, state):
        changed = copy.deepcopy(value)
        changed["max_bytes"] = 9007199254740991
        return resolve(changed, state)

    def ignore_mounts(value, state):
        changed = copy.deepcopy(value)
        changed["request"]["no_xdev"] = False
        return resolve(changed, state)

    for name, broken in (
        ("containment-link-dotdot", collapsed),
        ("read-byte-bound", unbounded),
        ("no-xdev-crossing", ignore_mounts),
    ):
        try:
            check_case(indexed[name], broken)
        except AssertionError:
            witnesses += 1
        else:
            raise AssertionError(name + ": broken evaluator survived")

    for bad in ("CON", "COM¹.txt", "a:stream", "a.", "a ", "a\\b", "a//b", "\ud800"):
        try:
            admitted_components(bad, "containment/v0")
        except Refusal as refusal:
            require(refusal.category == "invalid_name", "bad alias category")
        else:
            raise AssertionError("invalid name accepted")
    for raw in ('{"a":1,"a":2}', '{"x":NaN}', '{"x":Infinity}'):
        try:
            strict(raw)
        except AssertionError:
            pass
        else:
            raise AssertionError("non-JSON input accepted")
    print(
        f"[ok] filesystem-access logical controls: {len(corpus['cases'])} cases, {witnesses} mutation witnesses"
    )


if __name__ == "__main__":
    controls()
