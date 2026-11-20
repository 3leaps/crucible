#!/usr/bin/env python3
"""Reference consistency model and fixture checker for durable-runner/v0.

Executes every behavioral vector under schemas/durable-runner/v0/vectors
against an in-memory model of the rules in
docs/standards/durable-runner-contract.md, and checks that the hand-authored
expectations (op results, final task projection, exact committed history)
match the model exactly. The model is a checker for fixtures, not a
conformance oracle for implementations.

Every rule the model enforces is a named guard. `--disable GUARD` runs the
suite with one guard removed so mutation controls can prove that some vector
fails without it.

Standard library only; identity digests reuse scripts/rfc8785-canonicalize.py.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import math
import copy
import hashlib
import importlib.util
import json
import pathlib
import re
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = ROOT / "schemas/durable-runner/v0"

_spec = importlib.util.spec_from_file_location(
    "jcs", ROOT / "scripts/rfc8785-canonicalize.py"
)
jcs = importlib.util.module_from_spec(_spec)
sys.modules["jcs"] = jcs
_spec.loader.exec_module(jcs)

SAFE_MAX = 9007199254740991
TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
AUTH_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}")
LOCAL_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}")
RESERVED_KEY_PREFIXES = ("slot:", "catchup:")
KIND_PHASES = {"stall"}
FRAMEWORK_REASONS = {"timeout", "process_failure"}
EFFECTS = ("none", "resolved", "unknown")
RES_FOR = {
    "succeeded": {"succeeded"},
    "failed": {"failed"},
    "waiting": {"failed"},
    "abandoned": {"abandoned"},
}
CRASH_BLOCKED = {
    "transition",
    "checkpoint",
    "submit",
    "confirm_cancel",
    "request_cancel",
    "supply_slot",
    "evaluate_slots",
    "catch_up",
    "retire_output",
    "admission",
    "reconcile",
}


def _tok(v, pat=TOKEN_RE):
    if not isinstance(v, str) or not pat.fullmatch(v):
        raise Refuse("malformed")
    return v


def _int(v, lo=0, hi=SAFE_MAX):
    if isinstance(v, bool) or not isinstance(v, int):
        raise Refuse("malformed")
    if (lo is not None and v < lo) or (hi is not None and v > hi):
        raise Refuse("malformed")
    return v


MODES = ["basic", "retrying", "journaled", "scheduled"]
TERMINAL = {"succeeded", "failed", "cancelled", "abandoned", "missed"}
ALLOWED = {
    "pending": {"waiting", "running", "cancelled", "failed", "missed"},
    "waiting": {"running", "cancelled", "failed", "missed"},
    "running": {"succeeded", "failed", "waiting", "cancelled", "abandoned"},
}
GUARDS = [
    "profile.sealed_reserved",
    "profile.mode_prefix",
    "profile.remote_coverage",
    "profile.replication",
    "profile.journal_ack",
    "profile.authority_scope",
    "profile.store_effective",
    "profile.store_horizon",
    "profile.window_order",
    "profile.ack_model",
    "profile.window_range",
    "identity.conflict",
    "identity.expired_unresolved",
    "identity.definition_valid",
    "transition.predecessor",
    "transition.first_pending",
    "transition.table",
    "transition.terminal",
    "attempt.contiguous",
    "attempt.limit",
    "retry.reason",
    "retry.unknown_effects",
    "retry.jitter_persisted",
    "retry.horizon",
    "retry.deadline",
    "outcome.known_code",
    "success.verified",
    "success.after_cancel",
    "cancel.confirmed",
    "generation.stale",
    "recover.quiescence",
    "checkpoint.verified",
    "checkpoint.ordering",
    "checkpoint.cursor",
    "retire.hold",
    "admission.rate",
    "admission.shared",
    "admission.unsettled",
    "time.duration",
    "slot.dst",
    "slot.coverage",
    "catchup.lag",
    "catchup.permitted",
    "catchup.terminal",
    "mode.supported",
    "requirement.supported",
    "wire.instant_strict",
    "time.typed_format",
    "transition.failed_gate",
    "start.horizon",
    "recover.abandon_gate",
    "checkpoint.eligible",
    "checkpoint.held_body",
    "profile.effective_window",
    "slot.identity_rule",
    "slot.identity_changed",
    "slot.window_instant",
    "slot.window_clock",
    "slot.start_window",
    "slot.coverage_bounds",
    "outcome.class_success",
    "outcome.class_failure",
    "transition.attempt_required",
    "cancel.blocks_start",
    "cancel.blocks_retry",
    "cancel.terminal",
    "success.effects_resolved",
    "transition.retryable_failure",
    "retry.next_eligible_future",
    "counters.safe_integer",
    "recover.generation_monotonic",
    "cancel.committed_fact",
    "cancel.blocks_failure",
    "cancel.blocks_missed",
    "retry.backoff_band",
    "retry.slot_end",
    "slot.window_valid",
    "slot.missed_precedence",
    "identity.backoff_valid",
    "identity.reserved_key",
    "identity.mapping_valid",
    "identity.deadline_positive",
    "identity.phase_closed",
    "attempt.bind_live",
    "transition.result_matches",
    "outcome.required",
    "outcome.reason_match",
    "effects.required",
    "transition.start_dispatch",
    "cancel.blocks_prefailure",
    "recover.cancel_wins",
    "crash.requires_recovery",
    "slot.fold",
    "retry.feasibility_cap",
    "profile.journal_v1",
    "cancel.terminal_request",
    "retire.terminal_only",
    "recover.explicit_abandon",
    "cancel.blocks_admission",
    "time.deadline_overflow",
    "catchup.start_lag",
    "op.args_valid",
    "generation.unclaimed",
    "identity.durability_closed",
    "identity.retry_reasons_known",
    "outcome.lifecycle",
    "failed.effects_known",
    "recover.abandon_disposition",
    "retry.lag_end",
    "time.anchor_overflow",
    "slot.schedule_pinned",
    "slot.set_unique",
    "coverage.marks_existing",
    "profile.durability_closed",
    "profile.schedule_required",
    "profile.identity_history_closed",
    "generation.required",
]


class Refuse(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def dig(v) -> str:
    return "sha256:" + hashlib.sha256(jcs.jcs_dumps(v).encode()).hexdigest()


# ---------------------------------------------------------------- time
_DUR = re.compile(
    r"^P(?:(?P<w>[0-9]+)W|(?:(?P<d>[0-9]+)D)?(?:T(?:(?P<h>[0-9]+)H)?(?:(?P<m>[0-9]+)M)?(?:(?P<s>[0-9]+(?:\.[0-9]{1,6})?)S)?)?)$"
)
_PARTIAL = re.compile(r"^P(?:[0-9]+W|[0-9]+D(?:T.+)?|T.+)$")
_INSTANT = re.compile(
    r"^([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]+))?Z$"
)


def parse_duration_us(text: str, target: str = "us", on: bool = True) -> int:
    if not isinstance(text, str) or len(text) > 64:
        raise Refuse("syntax")
    m = _DUR.fullmatch(text)
    if not m or text in ("P", "PT") or text.endswith("T"):
        raise Refuse("syntax")
    if not any(m.group(g) for g in "wdhms"):
        raise Refuse("syntax")
    if m.group("w"):
        us = int(m.group("w")) * 7 * 86_400_000_000
    else:
        us = int(m.group("d") or 0) * 86_400_000_000
        us += int(m.group("h") or 0) * 3_600_000_000
        us += int(m.group("m") or 0) * 60_000_000
        if m.group("s"):
            whole, _, frac = m.group("s").partition(".")
            us += int(whole) * 1_000_000 + int((frac + "000000")[:6])
    if on and us > SAFE_MAX:
        raise Refuse("overflow")
    if target == "ms_interface" and us % 1000:
        raise Refuse("fractional_loss")
    return us


def parse_instant_us(text: str, on: bool = True) -> int:
    if not isinstance(text, str):
        raise Refuse("format")
    m = _INSTANT.fullmatch(text)
    if not m:
        raise Refuse("format")
    y, mo, d, h, mi, s, frac = m.groups()
    frac = frac or ""
    if len(frac) > 6:
        raise Refuse("nonrepresentable")
    if len(frac) < 6:
        if on:
            raise Refuse("format")
        frac = (frac + "000000")[:6]
    if int(s) > 59 or int(h) > 23 or int(mi) > 59:
        raise Refuse("nonrepresentable")
    try:
        dt = datetime(
            int(y), int(mo), int(d), int(h), int(mi), int(s), tzinfo=timezone.utc
        )
    except ValueError:
        raise Refuse("nonrepresentable")
    return int(dt.timestamp()) * 1_000_000 + int(frac)


def fmt_instant(us: int) -> str:
    dt = datetime.fromtimestamp(us // 1_000_000, tz=timezone.utc)
    return (
        f"{dt.year:04d}-{dt.month:02d}-{dt.day:02d}T{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"
        f".{us % 1_000_000:06d}Z"
    )


# ---------------------------------------------------------------- model

_fmt_raw = fmt_instant


def fmt_instant(us):
    try:
        if us < 0:
            raise ValueError("negative")
        return _fmt_raw(us)
    except (OverflowError, ValueError, OSError):
        raise Refuse("nonrepresentable")


# ---------------------------------------------------------------- op argument validation
LABEL_RE = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}")
STATE_NAMES = (
    "pending",
    "waiting",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    "abandoned",
    "missed",
)


def _bad():
    raise Refuse("malformed")


def _v_label(v):
    if not isinstance(v, str) or not LABEL_RE.fullmatch(v):
        _bad()


def _v_str(v):
    if not isinstance(v, str) or len(v) > 256:
        _bad()


def _v_any_str(v):
    if not isinstance(v, str):
        _bad()


def _v_bool(v):
    if not isinstance(v, bool):
        _bad()


def _v_int(lo=0, hi=SAFE_MAX):
    def check(v):
        if isinstance(v, bool) or not isinstance(v, int):
            _bad()
        if (lo is not None and v < lo) or (hi is not None and v > hi):
            _bad()

    return check


def _v_enum(*vals):
    def check(v):
        if not isinstance(v, str) or v not in vals:
            _bad()

    return check


def _v_dict(v):
    if not isinstance(v, dict):
        _bad()


def _closed(v, req, opt):
    if not isinstance(v, dict):
        _bad()
    for k in v:
        if k not in req and k not in opt:
            _bad()
    for k, f in req.items():
        if k not in v:
            _bad()
        f(v[k])
    for k, f in opt.items():
        if k in v:
            f(v[k])


def _v_rule(v):
    _closed(v, {"digest": _v_str, "contract": _v_str}, {})
    if not DIGEST_RE.fullmatch(v["digest"]):
        _bad()


def _v_window(v):
    _closed(v, {"not_before": _v_any_str, "not_after": _v_any_str}, {})


def _v_when(v, extra_req, extra_opt):
    """A slot or coverage entry: exactly one of instant or (local and tz)."""
    has_i, has_l, has_t = "instant" in v, "local" in v, "tz" in v
    if has_i == (has_l or has_t) or (has_l != has_t):
        _bad()
    opt = {"instant": _v_any_str, "local": _v_any_str, "tz": _v_str}
    opt.update(extra_opt)
    _closed(v, dict(extra_req), opt)


def _v_slot(v):
    if not isinstance(v, dict):
        _bad()
    _v_when(v, {"rule": _v_rule, "scope": _v_str, "window": _v_window}, {})


def _v_slots(v):
    if not isinstance(v, list) or not v:
        _bad()
    for e in v:
        _v_slot(e)


def _v_entry(v):
    if not isinstance(v, dict):
        _bad()
    _v_when(v, {"window": _v_window}, {})


def _v_coverage(v):
    _closed(
        v,
        {"rule": _v_rule, "scope": _v_str, "from": _v_any_str, "to": _v_any_str},
        {
            "expected": lambda e: (
                [_v_entry(x) for x in e] if isinstance(e, list) else _bad()
            )
        },
    )


def _v_coverage_or_none(v):
    if v is not None:
        _v_coverage(v)


def _v_attempt(v):
    _closed(
        v,
        {"n": _v_int(1)},
        {
            "phase": _v_enum("start", "finish"),
            "dispatch": _v_enum("intended", "confirmed", "unproven"),
            "result": _v_enum("succeeded", "failed", "cancelled", "abandoned"),
            "outcome": _v_str,
            "effects": _v_enum("none", "resolved", "unknown"),
            "reason": _v_str,
            "outputs_verified": _v_bool,
            "checkpoint": _v_int(1),
        },
    )


def _v_body(v):
    _closed(
        v,
        {},
        {
            "verified": _v_bool,
            "staged": _v_enum("before_record", "after_record"),
            "held": _v_bool,
        },
    )


def _v_labels(v):
    if not isinstance(v, dict):
        _bad()
    for k, x in v.items():
        _v_any_str(k)
        _v_label(x)


def _v_label_or_list(v):
    if isinstance(v, list):
        for x in v:
            _v_label(x)
    else:
        _v_label(v)


def _v_profile(v):
    strs = {
        k: _v_any_str
        for k in (
            "store_window",
            "effective_window",
            "retry_horizon",
            "attempt_journal_ack",
            "remote_sealed_coverage",
            "replication",
            "authority_scope",
            "identity_history",
            "journal_contract",
            "journal_failure_model",
        )
    }
    strs.update(
        {
            "modes": lambda m: (
                [_v_any_str(x) for x in m] if isinstance(m, list) else _bad()
            ),
            "window": _v_dict,
            "durability_extra": _v_dict,
            "task_kind_window_range": _v_dict,
            "schedule": lambda sc: _closed(
                sc, {"rule_contract": _v_rule}, {"max_lag": _v_any_str}
            ),
        }
    )
    _closed(v, {}, strs)


_GEN = _v_int(1)
OPSPEC = {
    "profile_admit": ({"profile": _v_profile}, {}, ()),
    "submit": (
        {"as": _v_label, "authority": _v_str, "key": _v_str, "definition": _v_label},
        {"generation": _GEN},
        (),
    ),
    "transition": (
        {"task": _v_label, "to": _v_enum(*STATE_NAMES)},
        {
            "attempt": _v_attempt,
            "prior": _v_enum("head", "stale", "absent"),
            "generation": _GEN,
            "reason": _v_str,
            "next_eligible_at": _v_any_str,
        },
        (),
    ),
    "request_cancel": ({"task": _v_label}, {"generation": _GEN}, ()),
    "confirm_cancel": (
        {"task": _v_label},
        {
            "quiescent": _v_bool,
            "effects": _v_enum("none", "resolved"),
            "generation": _GEN,
        },
        (),
    ),
    "advance_clock": ({"by": _v_any_str}, {}, ()),
    "inject_fault": ({"after": _v_int(0)}, {}, ()),
    "crash": (
        {
            "at": _v_enum(
                "after_start_before_dispatch",
                "after_effect_before_finish",
                "before_record_commit",
            )
        },
        {},
        (),
    ),
    "recover": (
        {
            "generation": _v_int(1, None),  # above the ceiling is counter_exhausted
            "owner": _v_str,
            "predecessor": _v_any_str,
            "effects": _v_any_str,
        },
        {"disposition": _v_enum("abandon"), "next_eligible_at": _v_any_str},
        (),
    ),
    "replay": ({}, {}, ()),
    "checkpoint": (
        {"task": _v_label, "cursor_revision": _v_int(1), "body": _v_body},
        {"generation": _GEN},
        (),
    ),
    "reconcile": (
        {"receipt": _v_enum("missing", "committed", "not_committed")},
        {},
        (),
    ),
    "retire_output": ({"task": _v_label}, {"hold": _v_enum("active", "none")}, ()),
    "admission": (
        {
            "source": _v_str,
            "scope": _v_enum("stream_local", "shared"),
            "limit_scope_declared": _v_bool,
            "action": _v_enum("reserve", "settle", "restart"),
        },
        {"limit": _v_int(0)},
        (),
    ),
    "parse_duration": (
        {"text": _v_any_str},
        {"target": _v_enum("us", "ms_interface")},
        (),
    ),
    "parse_instant": ({"text": _v_any_str}, {}, ()),
    "format_instant": (
        {},
        {"unix_us": _v_int(None, None), "unix_ns": _v_int(None, None)},
        (("unix_us", "unix_ns"),),
    ),
    "supply_slot": (
        {},
        {
            "slot": _v_slot,
            "occurrence_set": _v_slots,
            "coverage": _v_coverage,
            "as": _v_label_or_list,
            "definition": _v_label,
            "generation": _GEN,
        },
        (("slot", "occurrence_set", "coverage"),),
    ),
    "evaluate_slots": (
        {"definition": _v_label, "labels": _v_labels, "coverage": _v_coverage_or_none},
        {"generation": _GEN},
        (),
    ),
    "catch_up": (
        {"missed_task": _v_label, "as": _v_label, "definition": _v_label},
        {"generation": _GEN},
        (),
    ),
}


def validate_op(name, a):
    spec = OPSPEC.get(name)
    if spec is None:
        return
    req, opt, groups = spec
    if not isinstance(a, dict):
        _bad()
    for k in a:
        if k not in req and k not in opt and k not in ("op", "expect"):
            _bad()
    for k, f in req.items():
        if k not in a:
            _bad()
        f(a[k])
    for k, f in opt.items():
        if k in a:
            f(a[k])
    for group in groups:
        if sum(1 for k in group if k in a) != 1:
            _bad()
    if name == "supply_slot":
        if "slot" in a and (
            "as" not in a or "definition" not in a or isinstance(a["as"], list)
        ):
            _bad()
        if "occurrence_set" in a:
            if "as" not in a or "definition" not in a:
                _bad()
            labels = a["as"] if isinstance(a["as"], list) else [a["as"]]
            if len(labels) != len(a["occurrence_set"]) or len(set(labels)) != len(
                labels
            ):
                _bad()


class Model:
    def __init__(self, vector: dict, golden: dict, disabled: set[str]):
        self.dis = disabled
        self.mode = vector["mode"]
        self.golden = golden
        self.clock = parse_instant_us(
            vector.get("requires_clock", "2026-01-02T00:00:00.000000Z")
        )
        self.defs = {
            name: self._build_def(spec)
            for name, spec in vector.get("definitions", {}).items()
        }
        self.tasks: dict[str, dict] = {}
        self.ids: dict[str, str] = {}
        self.identity: dict[tuple, dict] = {}
        self.history: list[dict] = []
        self.generation = 1
        self.owner = "owner-1"
        self.store_window_us = parse_duration_us("P35D")
        self.kind_min_us, self.kind_max_us = (
            parse_duration_us("P7D"),
            parse_duration_us("P35D"),
        )
        self.history_retained = True
        self.schedule_rule = None
        self.max_lag_us = None
        self.coverage = None
        self.slots: dict[str, dict] = {}
        self.reserved = 0
        self.carried = 0
        self.crashed = False
        self.checkpoints: list[dict] = []
        self.holds: set[str] = set()
        self.seen: set[str] | None = None
        self.fault_after: int | None = None

    def on(self, g: str) -> bool:
        if self.seen is not None:
            self.seen.add(
                g
            )  # which guards a run consults: only those can change its verdict
        return g not in self.dis

    # -- definitions
    def _build_def(self, spec: dict) -> dict:
        d = copy.deepcopy(self.golden)
        for path, val in (spec.get("set", spec) or {}).items():
            cur = d
            parts = path.split(".")
            for p in parts[:-1]:
                cur = cur.setdefault(p, {})
            if val is None:
                cur.pop(parts[-1], None)
            else:
                cur[parts[-1]] = val
        return d

    def _validate_def(self, d: dict):
        dur = d.get("durability", {})
        if not isinstance(dur, dict):
            raise Refuse("definition_invalid")
        if self.on("identity.durability_closed") and set(dur) - {
            "remote_sealed_coverage",
            "replication",
        }:
            raise Refuse("definition_invalid")
        if self.on("requirement.supported") and (
            dur.get("remote_sealed_coverage", "none") != "none"
            or dur.get("replication", "none") != "none"
        ):
            raise Refuse("unsupported_requirement")
        if not self.on("identity.definition_valid"):
            return
        t = d.get("timeouts", {})
        if "attempt" not in t and "task_deadline" not in t:
            raise Refuse("definition_invalid")
        for key in ("attempt", "task_deadline", "grace"):
            if key in t:
                try:
                    v = parse_duration_us(t[key])
                except Refuse:
                    raise Refuse("definition_invalid")
                if key != "grace" and v <= 0 and self.on("identity.deadline_positive"):
                    raise Refuse("definition_invalid")
        if self.on("identity.phase_closed") and set(t.get("phases", {})) - KIND_PHASES:
            raise Refuse("definition_invalid")
        rc = d["retry"]
        ma = rc["max_attempts"]
        if isinstance(ma, bool) or not isinstance(ma, int) or not 1 <= ma <= 1000:
            raise Refuse("definition_invalid")
        try:
            for pv in t.get("phases", {}).values():
                if parse_duration_us(pv) <= 0:
                    raise Refuse("definition_invalid")
            if rc.get("horizon") is not None and self.on("identity.deadline_positive"):
                if parse_duration_us(rc["horizon"]) <= 0:
                    raise Refuse("definition_invalid")
            bo = rc.get("backoff")
            if bo is not None:
                bi, bm = parse_duration_us(bo["initial"]), parse_duration_us(bo["max"])
                if self.on("identity.backoff_valid") and bi > bm:
                    raise Refuse("definition_invalid")
                jm, mm = bo["jitter_milli"], bo.get("multiplier_milli", 1000)
                for x in (jm, mm):
                    if isinstance(x, bool) or not isinstance(x, int):
                        raise Refuse("definition_invalid")
                if not (0 <= jm <= 1000 and 1000 <= mm <= 10000):
                    raise Refuse("definition_invalid")
        except Refuse as r:
            raise (
                Refuse("definition_invalid")
                if r.reason in ("syntax", "overflow", "fractional_loss")
                else r
            )
        w = d.get("idempotency_window")
        if w is not None:
            try:
                wu = parse_duration_us(w)
            except Refuse:
                raise Refuse("definition_invalid")
            if not (self.kind_min_us <= wu <= self.kind_max_us):
                raise Refuse("definition_invalid")
        mapping = d.get("outcome_mapping")
        if not mapping:
            raise Refuse("definition_invalid")
        if self.on("identity.mapping_valid"):
            codes = [m["code"] for m in mapping]
            if len(set(codes)) != len(codes) or not any(
                m["result"] == "success" for m in mapping
            ):
                raise Refuse("definition_invalid")
        if self.on("identity.retry_reasons_known"):
            known = {
                m.get("reason")
                for m in mapping
                if m["result"] == "failure" and m.get("reason")
            } | FRAMEWORK_REASONS
            if set(rc["retryable_reasons"]) - known:
                raise Refuse("definition_invalid")

    ACK_ORDER = {"none": 0, "survives_process_loss": 1, "survives_power_loss": 2}

    @staticmethod
    def flat_to_doc(p: dict) -> dict:
        """Adapt a vector's flat profile to the runner-profile schema shape, so
        one admission function serves vectors and schema-shaped documents."""
        ack = p.get("attempt_journal_ack", "none")
        idem = {}
        if p.get("window"):
            idem["window"] = p["window"]
        for k in (
            "store_window",
            "effective_window",
            "retry_horizon",
            "identity_history",
        ):
            if p.get(k) is not None:
                idem[k] = p[k]
        runtime = {
            "authority": {"scope": p.get("authority_scope", "single_host_exclusive")},
            "durability": {
                "attempt_journal_ack": ack,
                "remote_sealed_coverage": p.get("remote_sealed_coverage", "none"),
                "replication": p.get("replication", "none"),
                **p.get("durability_extra", {}),
            },
            "journal": {
                "record_contract": {
                    "contract": p.get("journal_contract", "contract: durable-record/v1")
                },
                "failure_model": p.get("journal_failure_model", ack),
            },
            "idempotency": idem,
        }
        if p.get("schedule"):
            runtime["schedule"] = p["schedule"]
        return {"modes": p.get("modes", []), "runtime": runtime}

    def admit_profile_doc(self, doc: dict) -> dict:
        """Semantic admission of a schema-shaped runner profile document."""
        modes = doc.get("modes", [])
        rt = doc["runtime"]
        dur = rt["durability"]
        if self.on("profile.sealed_reserved") and "sealed" in modes:
            raise Refuse("sealed_mode_reserved")
        idem_h = rt.get("idempotency", {}).get("identity_history")
        core = [x for x in modes if x != "sealed"]
        if self.on("profile.mode_prefix") and (not modes or core != MODES[: len(core)]):
            raise Refuse("mode_not_cumulative")
        if (
            self.on("profile.remote_coverage")
            and dur.get("remote_sealed_coverage", "none") != "none"
        ):
            raise Refuse("remote_coverage_claimed")
        if self.on("profile.replication") and dur.get("replication", "none") != "none":
            raise Refuse("replication_claimed")
        if self.on("profile.identity_history_closed") and idem_h not in (
            None,
            "retained",
            "reconstructable",
            "discarded",
        ):
            raise Refuse("profile_invalid")
        if self.on("profile.durability_closed") and set(dur) - {
            "attempt_journal_ack",
            "remote_sealed_coverage",
            "replication",
        }:
            raise Refuse("profile_invalid")
        if (
            self.on("profile.schedule_required")
            and "scheduled" in modes
            and not rt.get("schedule")
        ):
            raise Refuse("schedule_not_configured")
        ack = dur.get("attempt_journal_ack", "none")
        if "journaled" in modes:
            j = rt.get("journal", {})
            if (
                self.on("profile.journal_v1")
                and j.get("record_contract", {}).get("contract")
                != "contract: durable-record/v1"
            ):
                raise Refuse("journal_contract_not_v1")
            if self.on("profile.journal_ack") and ack == "none":
                raise Refuse("journal_ack_insufficient")
        j = rt.get("journal") or {}
        # A missing journal stratum is failure model none; an unknown ack value is
        # treated as stronger than anything declared, so both fail closed.
        if self.on("profile.ack_model") and self.ACK_ORDER.get(
            ack, 99
        ) > self.ACK_ORDER.get(j.get("failure_model", "none"), -1):
            raise Refuse("journal_ack_exceeds_failure_model")
        if (
            self.on("profile.authority_scope")
            and rt["authority"].get("scope") != "single_host_exclusive"
        ):
            raise Refuse("authority_scope_unsupported")
        idem = rt.get("idempotency", {})
        win = idem.get("window")
        if win:
            lo, df, hi = (parse_duration_us(win[k]) for k in ("min", "default", "max"))
            if self.on("profile.window_order") and not (lo <= df <= hi):
                raise Refuse("window_out_of_range")
            if self.on("profile.window_range") and (
                lo < self.kind_min_us or hi > self.kind_max_us
            ):
                raise Refuse("window_out_of_range")
            eff = (
                parse_duration_us(idem["effective_window"])
                if idem.get("effective_window") is not None
                else df
            )
            if self.on("profile.effective_window") and not (
                self.kind_min_us <= eff <= self.kind_max_us
            ):
                raise Refuse("window_out_of_range")
            sw = idem.get("store_window")
            if sw is not None:
                swu = parse_duration_us(sw)
                if self.on("profile.store_effective") and swu < eff:
                    raise Refuse("store_window_too_short")
                if (
                    self.on("profile.store_horizon")
                    and idem.get("retry_horizon") is not None
                    and swu < parse_duration_us(idem["retry_horizon"])
                ):
                    raise Refuse("store_window_too_short")
        return {}

    def op_profile_admit(self, a):
        p = a["profile"]
        rng = p.get("task_kind_window_range")
        saved = (self.kind_min_us, self.kind_max_us)
        if rng:
            self.kind_min_us, self.kind_max_us = (
                parse_duration_us(rng["min"]),
                parse_duration_us(rng["max"]),
            )
        try:
            self.admit_profile_doc(self.flat_to_doc(p))
        except Refuse:
            self.kind_min_us, self.kind_max_us = (
                saved  # a refused admission changes nothing
            )
            raise
        sw = p.get("store_window")
        if sw:
            self.store_window_us = parse_duration_us(sw)
        if p.get("identity_history") == "discarded":
            self.history_retained = False
        sch = p.get("schedule")
        if sch:
            self.schedule_rule = sch["rule_contract"]["digest"]
            self.max_lag_us = (
                parse_duration_us(sch["max_lag"]) if sch.get("max_lag") else None
            )
        return {}

    OP_MODE = {
        "recover": "journaled",
        "replay": "journaled",
        "checkpoint": "journaled",
        "reconcile": "journaled",
        "crash": "journaled",
        "retire_output": "journaled",
        "supply_slot": "scheduled",
        "evaluate_slots": "scheduled",
        "catch_up": "scheduled",
    }

    def _need(self, mode: str):
        if self.on("mode.supported") and MODES.index(mode) > MODES.index(self.mode):
            raise Refuse("mode_unsupported")

    GEN_OPS = {
        "submit",
        "transition",
        "request_cancel",
        "confirm_cancel",
        "checkpoint",
        "supply_slot",
        "evaluate_slots",
        "catch_up",
    }

    def preflight(self, name: str, a=None):
        if a is not None and self.on("op.args_valid"):
            validate_op(name, a)
        if a is not None and name in self.GEN_OPS:
            if "generation" not in a:
                if self.on("generation.required"):
                    raise Refuse("generation_required")  # absent never means current
            else:
                g = a["generation"]
                if self.on("generation.stale") and g < self.generation:
                    raise Refuse("generation_stale")
                if self.on("generation.unclaimed") and g > self.generation:
                    raise Refuse("generation_unclaimed")
        if name in self.OP_MODE:
            self._need(self.OP_MODE[name])
        if (
            self.crashed
            and name in CRASH_BLOCKED
            and self.on("crash.requires_recovery")
        ):
            raise Refuse("recovery_required")

    def _register(
        self, label, authority, key, defname, derived=False, anchor_us=None, dry=False
    ):
        """The one path that creates a task: submit, slot, coverage-missed and catch-up."""
        d = self.defs[defname]
        self._validate_def(d)
        if d["retry"]["max_attempts"] > 1:
            self._need("retrying")
        _tok(authority, AUTH_RE)
        _tok(key)
        if (
            not derived
            and self.on("identity.reserved_key")
            and key.startswith(RESERVED_KEY_PREFIXES)
        ):
            raise Refuse("reserved_key")
        spec = dig(d)
        tid = dig({"authority": authority, "invocation_key": key, "v": 0})
        rec = self.identity.get((authority, key))
        if rec:
            expired = self.clock - rec["accepted_us"] > self.store_window_us
            if (
                expired
                and not self.history_retained
                and self.on("identity.expired_unresolved")
            ):
                raise Refuse("identity_unresolved")
            if rec["spec"] != spec and self.on("identity.conflict"):
                raise Refuse("identity_conflict")
            return tid, False  # same spec, or the conflict guard removed: observe
        tl = d["timeouts"].get("task_deadline")
        if (
            tl is not None
            and self.on("time.deadline_overflow")
            and (anchor_us if anchor_us is not None else self.clock)
            + parse_duration_us(tl)
            > SAFE_MAX
        ):
            raise Refuse("counter_exhausted")
        if label in self.tasks:
            raise Refuse("malformed")  # a label names one task; never overwritten
        if dry:
            return tid, True
        self.identity[(authority, key)] = {"spec": spec, "accepted_us": self.clock}
        self.ids[tid] = label
        self.tasks[label] = {
            "id": tid,
            "spec": spec,
            "def": d,
            "state": "pending",
            "rev": 0,
            "attempts": [],
            "started": 0,
            "cancel_req": False,
            "next_eligible": None,
            "accepted_us": self.clock if anchor_us is None else anchor_us,
            "first_start_us": None,
            "authority": authority,
        }
        self._commit(label, "pending", None)
        return tid, True

    def op_submit(self, a):
        tid, created = self._register(
            a["as"], a["authority"], a["key"], a["definition"]
        )
        t = self.tasks[self.ids[tid]]
        return {
            "disposition": "created" if created else "observed",
            "task_id": tid,
            "state": t["state"],
        }

    def _commit(self, label, to, attempt):
        t = self.tasks[label]
        t["rev"] += 1
        t["state"] = to
        h = {"task": label, "to": to}
        if attempt:
            h["attempt"] = attempt
        self.history.append(h)
        return t["rev"]

    def op_transition(self, a):
        label = a["task"]
        if label not in self.tasks:
            if self.on("transition.first_pending") and a["to"] != "pending":
                raise Refuse("first_not_pending")
            raise Refuse("predecessor_mismatch")
        t = self.tasks[label]
        d = t["def"]
        to = a["to"]
        at = a.get("attempt")
        prior = a.get("prior", "head")
        if self.on("transition.predecessor") and prior != "head":
            raise Refuse("predecessor_mismatch")
        cur = t["state"]
        if self.on("transition.terminal") and cur in TERMINAL:
            raise Refuse("terminal_resurrection")
        if (
            self.on("transition.table")
            and cur not in TERMINAL
            and to not in ALLOWED.get(cur, set())
        ):
            raise Refuse("illegal_transition")
        if to == "missed" and self.on("transition.table"):
            hi = t.get("slot_hi")
            if t["started"] > 0 or hi is None or self.clock < hi:
                raise Refuse("illegal_transition")
        if to == "missed" and t["cancel_req"] and self.on("cancel.blocks_missed"):
            raise Refuse("illegal_transition")
        if to == "cancelled" and self.on("cancel.confirmed"):
            raise Refuse("cancellation_not_confirmed")
        if (
            cur == "running"
            and not isinstance(at, dict)
            and self.on("transition.attempt_required")
        ):
            raise Refuse("attempt_required")
        if t["cancel_req"]:
            if to == "running" and self.on("cancel.blocks_start"):
                raise Refuse("cancellation_precedes_start")
            if (
                cur == "pending"
                and to == "waiting"
                and self.on("cancel.blocks_admission")
            ):
                raise Refuse("cancellation_precedes_start")
            if cur == "running" and to == "waiting" and self.on("cancel.blocks_retry"):
                raise Refuse("cancellation_precedes_start")
            if cur == "running" and to == "failed" and self.on("cancel.blocks_failure"):
                raise Refuse("cancellation_precedes_failure")
            if (
                cur in ("pending", "waiting")
                and to == "failed"
                and self.on("cancel.blocks_prefailure")
            ):
                raise Refuse("cancellation_precedes_failure")
        if (
            to == "failed"
            and cur in ("pending", "waiting")
            and self.on("transition.failed_gate")
        ):
            r = a.get("reason")
            mx = d["retry"]["max_attempts"]
            hi_s = t.get("slot_hi")
            slot_over = hi_s is not None and self.clock >= hi_s
            ok = (
                (r == "pre_execution_refusal" and cur == "pending")
                or (r == "deadline_expired" and self._past_deadline(t, d))
                or (
                    r == "retry_exhausted"
                    and cur == "waiting"
                    and (
                        t["started"] >= mx
                        or self._past_horizon(t, d, self.clock)
                        or (t["started"] > 0 and slot_over)
                    )
                )
            )
            if self.on("slot.missed_precedence") and slot_over and t["started"] == 0:
                ok = False
            if not ok:
                raise Refuse("illegal_transition")
        if to == "running":
            return self._start(label, t, d, a, at)
        if cur == "running" and isinstance(at, dict):
            return self._finish(label, t, d, a, at, to)
        rev = self._commit(label, to, None)
        return {"revision": rev, "state": to}

    def _start(self, label, t, d, a, at):
        if not isinstance(at, dict):
            if self.on("transition.attempt_required"):
                raise Refuse("attempt_required")
            at = {
                "n": t["started"] + 1
            }  # guard removed: a start without an attempt fact
        n = _int(at.get("n"), 1)
        if at.get("dispatch", "intended") != "intended" and self.on(
            "transition.start_dispatch"
        ):
            raise Refuse("dispatch_not_provable")
        cu = t.get("catchup_instant")
        if (
            cu is not None
            and self.max_lag_us is not None
            and self.on("catchup.start_lag")
            and not (0 <= self.clock - cu <= self.max_lag_us)
        ):
            raise Refuse("lag_exceeded")
        lo_s, hi_s = t.get("slot_lo"), t.get("slot_hi")
        if lo_s is not None and self.on("slot.start_window"):
            if self.clock < lo_s or self.clock >= hi_s:
                raise Refuse("illegal_transition")
        if self.on("attempt.contiguous") and n != t["started"] + 1:
            raise Refuse("attempt_not_contiguous")
        if self.on("attempt.limit") and n > d["retry"]["max_attempts"]:
            raise Refuse("attempt_limit_exhausted")
        if self.on("retry.deadline") and self._past_deadline(t, d):
            raise Refuse("deadline_exceeded")
        if self.on("start.horizon") and self._past_horizon(t, d, self.clock):
            raise Refuse("horizon_exceeded")
        cp = at.get("checkpoint")
        if cp is not None:
            rec = self.checkpoints[cp - 1] if 1 <= cp <= len(self.checkpoints) else None
            if self.on("checkpoint.eligible") and (
                rec is None or rec["task"] != label or rec["attempt"] >= n
            ):
                raise Refuse("checkpoint_not_eligible")
            if self.on("checkpoint.held_body") and rec is not None and rec["held"]:
                raise Refuse("checkpoint_body_held")
        if (
            t["next_eligible"] is not None
            and self.clock < t["next_eligible"]
            and self.on("transition.table")
        ):
            raise Refuse("illegal_transition")
        t["started"] = n
        t["attempts"].append(
            {"n": n, "result": "running", "effects": None, "dispatch": "intended"}
        )
        if t["first_start_us"] is None:
            t["first_start_us"] = self.clock
        t["next_eligible"] = None
        rev = self._commit(label, "running", {"n": n, "phase": "start"})
        return {"revision": rev, "state": "running"}

    def _finish(self, label, t, d, a, at, to):
        rc = d["retry"]
        mapping = {m["code"]: m for m in d["outcome_mapping"]}
        live = t["attempts"][-1]
        n = _int(at.get("n"), 1)
        if self.on("attempt.bind_live") and n != live["n"]:
            raise Refuse("attempt_mismatch")
        res = at.get("result")
        if (
            self.on("transition.result_matches")
            and to in RES_FOR
            and res not in RES_FOR[to]
        ):
            raise Refuse("result_state_mismatch")
        code = at.get("outcome")
        runner_timeout = (
            res == "failed" and code is None and at.get("reason") in FRAMEWORK_REASONS
        )
        if (
            res in ("succeeded", "failed")
            and code is None
            and not runner_timeout
            and self.on("outcome.required")
        ):
            raise Refuse("outcome_required")
        if code is not None and code not in mapping and self.on("outcome.known_code"):
            raise Refuse("unknown_outcome_code")
        # The retry reason comes from the pinned mapping; the one runner-owned
        # reason is a detected timeout, which has no outcome code.
        m_reason = (
            at.get("reason") if runner_timeout else mapping.get(code, {}).get("reason")
        )
        if code in mapping:
            is_ok = mapping[code]["result"] == "success"
            if res == "succeeded" and not is_ok and self.on("outcome.class_success"):
                raise Refuse("outcome_mapping_mismatch")
            if res == "failed" and is_ok and self.on("outcome.class_failure"):
                raise Refuse("outcome_mapping_mismatch")
            if (
                at.get("reason") is not None
                and at["reason"] != m_reason
                and self.on("outcome.reason_match")
            ):
                raise Refuse("outcome_mapping_mismatch")
        eff = at.get("effects")
        if eff not in EFFECTS and self.on("effects.required"):
            raise Refuse("effects_required")
        if (
            res in ("cancelled", "abandoned")
            and (code is not None or at.get("reason") is not None)
            and self.on("outcome.lifecycle")
        ):
            raise Refuse("outcome_not_allowed")
        if to == "failed" and eff == "unknown" and self.on("failed.effects_known"):
            raise Refuse("unresolved_effects_not_failed")
        if to == "succeeded":
            if self.on("success.after_cancel") and t["cancel_req"]:
                raise Refuse("cancellation_precedes_success")
            if self.on("success.effects_resolved") and eff != "resolved":
                raise Refuse("success_effects_unresolved")
            if self.on("success.verified") and at.get("outputs_verified") is not True:
                raise Refuse("success_unverified_outputs")
        if to == "failed":
            if (
                res == "failed"
                and self.on("transition.retryable_failure")
                and m_reason in rc["retryable_reasons"]
                and t["started"] < rc["max_attempts"]
                and self._retry_band(t, d, live["n"])[3]
            ):
                raise Refuse("retry_required")
        if to == "waiting":
            if eff == "unknown" and self.on("retry.unknown_effects"):
                raise Refuse("unknown_effects_not_retryable")
            if (
                self.on("retry.reason")
                and res == "failed"
                and m_reason not in rc["retryable_reasons"]
            ):
                raise Refuse("retry_not_permitted")
            if self.on("attempt.limit") and t["started"] >= rc["max_attempts"]:
                raise Refuse("attempt_limit_exhausted")
            ne = a.get("next_eligible_at")
            if self.on("retry.jitter_persisted") and ne is None:
                raise Refuse("jitter_not_persisted")
            if ne is not None:
                self._check_wait(t, d, live["n"], parse_instant_us(ne))
                t["next_eligible"] = parse_instant_us(ne)
        live["result"] = res
        live["effects"] = eff
        live["outcome"] = code
        live["dispatch"] = at.get("dispatch", live["dispatch"])
        rev = self._commit(
            label, to, {"n": live["n"], "phase": "finish", "result": res}
        )
        return {"revision": rev, "state": to}

    def _check_wait(self, t, d, n, neu):
        delay = neu - self.clock
        if neu > SAFE_MAX and self.on("time.anchor_overflow"):
            raise Refuse("counter_exhausted")
        if delay < 0 and self.on("retry.next_eligible_future"):
            raise Refuse("next_eligible_in_past")
        lo, hi, hi_f, feasible, binding = self._retry_band(t, d, n)
        if not feasible and binding is not None:
            if binding == "deadline" and self.on("retry.deadline"):
                raise Refuse("deadline_exceeded")
            if binding == "horizon" and self.on("retry.horizon"):
                raise Refuse("horizon_exceeded")
            if binding == "slot" and self.on("retry.slot_end"):
                raise Refuse("illegal_transition")
            if binding == "lag" and self.on("retry.lag_end"):
                raise Refuse("lag_exceeded")
            return
        if delay < 0:
            return
        if feasible:
            if self.on("retry.backoff_band") and not (lo <= delay <= hi):
                raise Refuse("backoff_out_of_band")
            if self.on("retry.feasibility_cap") and hi_f < hi and delay > hi_f:
                raise Refuse("backoff_out_of_band")
        elif self.on("retry.backoff_band") and not (lo <= delay <= hi):
            raise Refuse("backoff_out_of_band")

    def _past_deadline(self, t, d, at_us=None):
        tl = d["timeouts"].get("task_deadline")
        if tl is None:
            return False
        when = self.clock if at_us is None else at_us
        return when - t["accepted_us"] >= parse_duration_us(tl)

    def _past_horizon(self, t, d, at_us):
        hz = d["retry"].get("horizon")
        if hz is None or t["first_start_us"] is None:
            return False
        return at_us - t["first_start_us"] >= parse_duration_us(hz)

    def _bound_end(self, t, d):
        """Earliest exclusive execution bound as (end_us, name), or (None, None)."""
        cands = []
        tl = d["timeouts"].get("task_deadline")
        if tl is not None:
            cands.append((t["accepted_us"] + parse_duration_us(tl), "deadline"))
        hz = d["retry"].get("horizon")
        if hz is not None and t["first_start_us"] is not None:
            cands.append((t["first_start_us"] + parse_duration_us(hz), "horizon"))
        if t.get("catchup_instant") is not None and self.max_lag_us is not None:
            cands.append((t["catchup_instant"] + self.max_lag_us + 1, "lag"))
        if self.on("time.anchor_overflow") and any(c[0] > SAFE_MAX for c in cands):
            raise Refuse("counter_exhausted")
        if t.get("slot_hi") is not None:
            cands.append((t["slot_hi"], "slot"))
        if not cands:
            return None, None
        return min(cands, key=lambda c: c[0])

    def _retry_band(self, t, d, n):
        """Exact integer-microsecond backoff band for a retry after attempt n.
        Returns (lo, hi, hi_capped, feasible, binding_bound_name)."""
        bo = d["retry"].get("backoff")
        if bo is None:
            initial = ceiling = 0
            m = Fraction(1)
            j = Fraction(0)
        else:
            initial = parse_duration_us(bo["initial"])
            ceiling = parse_duration_us(bo["max"])
            m = Fraction(bo.get("multiplier_milli", 1000), 1000)
            j = Fraction(bo["jitter_milli"], 1000)
        val = Fraction(initial)
        if initial != 0 and m != 1:
            val = val * m ** max(n - 1, 0)
            if val >= ceiling:
                val = Fraction(ceiling)
        nominal = min(ceiling, math.ceil(val))
        lo = math.ceil(nominal * (1 - j))
        hi = min(ceiling, math.floor(nominal * (1 + j)))
        end, name = self._bound_end(t, d)
        hi_f = hi if end is None else min(hi, end - self.clock - 1)
        feasible = lo <= hi_f and hi_f >= 0
        return (
            lo,
            hi,
            hi_f,
            feasible,
            (name if (end is not None and not feasible) else None),
        )

    def op_request_cancel(self, a):
        t = self.tasks[a["task"]]
        if t["state"] in TERMINAL:
            if t["state"] == "succeeded":
                return {"effect": "too_late"}
            if self.on("cancel.terminal_request"):
                raise Refuse("task_terminal")
            return {"effect": "recorded"}
        if t["cancel_req"]:
            return {"effect": "recorded"}
        t["cancel_req"] = True
        if self.on("cancel.committed_fact"):
            self.history.append(
                {"task": a["task"], "to": t["state"], "cancellation": "requested"}
            )
            t["rev"] += 1
        return {"effect": "recorded"}

    def op_confirm_cancel(self, a):
        t = self.tasks[a["task"]]
        if t["state"] in TERMINAL and self.on("cancel.terminal"):
            raise Refuse("task_terminal")
        if self.on("cancel.confirmed") and not t["cancel_req"]:
            raise Refuse("cancel_not_requested")
        live = bool(t["attempts"]) and t["attempts"][-1]["result"] == "running"
        if self.on("cancel.confirmed") and live and not a.get("quiescent", False):
            raise Refuse("quiescence_not_established")
        att = None
        if (
            live
            and a.get("effects") not in ("none", "resolved")
            and self.on("effects.required")
        ):
            raise Refuse("effects_required")
        if t["attempts"] and t["attempts"][-1]["result"] == "running":
            t["attempts"][-1]["result"] = "cancelled"
            t["attempts"][-1]["effects"] = a.get("effects")
            att = {
                "n": t["attempts"][-1]["n"],
                "phase": "finish",
                "result": "cancelled",
            }
        self._commit(a["task"], "cancelled", att)
        return {"state": "cancelled"}

    def op_advance_clock(self, a):
        try:
            by = parse_duration_us(a["by"])
        except Refuse:
            raise Refuse("duration_invalid")
        if self.clock + by > SAFE_MAX and self.on("time.anchor_overflow"):
            raise Refuse("counter_exhausted")
        self.clock += by
        return {"now": fmt_instant(self.clock)}

    def op_inject_fault(self, a):
        """Test harness fault: the next batch commit fails after this many items."""
        self.fault_after = a["after"]
        return {}

    def _batch_fault(self, committed: int):
        if self.fault_after is not None and committed == self.fault_after:
            self.fault_after = None
            raise Refuse(
                "commit_indeterminate"
            )  # committed prefix stays; the rest is unattempted

    def op_crash(self, a):
        self.crashed = True
        return {"journal_head": len(self.history)}

    def op_recover(self, a):
        gen = a["generation"]
        if isinstance(gen, bool) or not isinstance(gen, int):
            raise Refuse("malformed")
        if self.on("counters.safe_integer") and gen > SAFE_MAX:
            raise Refuse("counter_exhausted")
        owner = a["owner"]
        _tok(owner)
        same_claim = gen == self.generation and owner == self.owner
        if (
            self.on("recover.generation_monotonic")
            and gen <= self.generation
            and not same_claim
        ):
            raise Refuse("generation_stale")
        pred = a["predecessor"]
        if self.on("recover.quiescence") and pred not in (
            "quiescent_proved",
            "reconciled_by_kind_rule",
        ):
            raise Refuse("predecessor_not_quiescent")
        eff = a["effects"]
        if eff not in EFFECTS and self.on("effects.required"):
            raise Refuse("effects_required")
        disposition = a.get("disposition")
        plan = []
        for label, t in self.tasks.items():
            if t["state"] != "running":
                continue
            att = t["attempts"][-1]
            rc = t["def"]["retry"]
            unresolved = eff == "unknown"
            if (
                unresolved
                and disposition != "abandon"
                and self.on("recover.explicit_abandon")
            ):
                raise Refuse("recovery_disposition_required")
            if disposition == "abandon" and self.on("recover.abandon_disposition"):
                nxt = "abandoned"
                ne = None
            elif t["cancel_req"] and self.on("recover.cancel_wins"):
                nxt = "abandoned" if unresolved else "cancelled"
                ne = None
            else:
                can_wait = (
                    not unresolved
                    and t["started"] < rc["max_attempts"]
                    and (
                        not self.on("recover.abandon_gate")
                        or rc.get("retry_after_abandonment", False)
                    )
                    and self._retry_band(t, t["def"], att["n"])[3]
                )
                nxt = "waiting" if can_wait else "abandoned"
                ne = None
                if nxt == "waiting":
                    if a.get("next_eligible_at") is None and self.on(
                        "retry.jitter_persisted"
                    ):
                        raise Refuse("jitter_not_persisted")
                    if a.get("next_eligible_at") is not None:
                        ne = parse_instant_us(a["next_eligible_at"])
                        self._check_wait(t, t["def"], att["n"], ne)
            plan.append((label, t, att, nxt, ne))
        self.generation = gen
        self.owner = owner
        self.crashed = False
        out = {}
        for label, t, att, nxt, ne in plan:
            att["result"] = "cancelled" if nxt == "cancelled" else "abandoned"
            att["effects"] = eff
            self._commit(
                label, nxt, {"n": att["n"], "phase": "finish", "result": att["result"]}
            )
            if nxt == "waiting":
                t["next_eligible"] = ne if ne is not None else self.clock
        for label, t in self.tasks.items():
            out[label] = t["state"]
        return {"task_states": out, "executed_effects": 0}

    def op_replay(self, a):
        heads = {label: t["state"] for label, t in self.tasks.items()}
        return {
            "heads": heads,
            "effects_performed": 0,
            "outcomes": {
                label: next(
                    (
                        x.get("outcome")
                        for x in reversed(t["attempts"])
                        if x.get("outcome")
                    ),
                    None,
                )
                for label, t in self.tasks.items()
            },
        }

    def op_checkpoint(self, a):
        t = self.tasks[a["task"]]
        body = a["body"]
        if self.on("checkpoint.cursor") and not (1 <= a["cursor_revision"] <= t["rev"]):
            raise Refuse("cursor_not_in_chain")
        if self.on("checkpoint.verified") and not body.get("verified", False):
            raise Refuse("body_unverified")
        if self.on("checkpoint.ordering") and body.get("staged") != "before_record":
            raise Refuse("body_after_record")
        self.checkpoints.append(
            {
                "task": a["task"],
                "rev": a["cursor_revision"],
                "held": bool(body.get("held")),
                "attempt": t["started"],
            }
        )
        return {"checkpoint_id": len(self.checkpoints)}

    def op_reconcile(self, a):
        r = a["receipt"]
        return {"status": "indeterminate" if r == "missing" else r}

    def op_retire_output(self, a):
        if self.on("retire.hold") and a.get("hold") == "active":
            raise Refuse("hold_active")
        if self.tasks[a["task"]]["state"] not in TERMINAL and self.on(
            "retire.terminal_only"
        ):
            raise Refuse("retirement_refused")
        return {}

    def op_admission(self, a):
        act = a["action"]
        limit = a.get("limit", 1)
        if act == "reserve":
            if (
                self.on("admission.shared")
                and a.get("scope") == "stream_local"
                and a.get("limit_scope_declared")
            ):
                raise Refuse("shared_quota_needs_shared_authority")
            if self.reserved >= limit:
                if self.carried > 0:
                    if self.on("admission.unsettled"):
                        raise Refuse("unsettled_reservation")
                elif self.on("admission.rate"):
                    raise Refuse("rate_denied")
            self.reserved += 1
            return {"reserved": self.reserved}
        if act == "settle":
            self.reserved = max(0, self.reserved - 1)
            self.carried = max(0, self.carried - 1)
            return {"reserved": self.reserved}
        if act == "restart":
            # Unsettled reservations survive a restart conservatively and keep counting.
            self.carried = self.reserved
            return {"reserved": self.reserved}
        raise Refuse("rate_denied")

    def op_parse_duration(self, a):
        if not self.on("time.duration"):
            return {"us": 0}
        return {"us": parse_duration_us(a["text"], a.get("target", "us"))}

    def op_parse_instant(self, a):
        us = parse_instant_us(a["text"], on=self.on("wire.instant_strict"))
        return {"canonical": fmt_instant(us)}

    def op_format_instant(self, a):
        """Typed path: an exactly representable typed instant formats canonically."""
        if "unix_ns" in a:
            if a["unix_ns"] % 1000 and self.on("time.typed_format"):
                raise Refuse("nonrepresentable")
            return {"canonical": fmt_instant(a["unix_ns"] // 1000)}
        return {"canonical": fmt_instant(a["unix_us"])}

    def _local_to_utc(self, local: str, tz: str, check_gap: bool = True) -> str:
        """Fixture-limited zone table: America/New_York in 2026 only. Anything this
        table cannot judge is refused as unavailable, never guessed."""
        if not isinstance(local, str) or not LOCAL_RE.fullmatch(local):
            raise Refuse("format")
        if tz != "America/New_York" or not local.startswith("2026-"):
            raise Refuse("zone_unavailable")
        try:
            naive = datetime.strptime(local, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            raise Refuse("format")
        if self.on("slot.fold") and datetime(2026, 11, 1, 1, 0) <= naive < datetime(
            2026, 11, 1, 2, 0
        ):
            raise Refuse("ambiguous_local_time")
        if (
            check_gap
            and naive.date().isoformat() == "2026-03-08"
            and 2 <= naive.hour < 3
        ):
            raise Refuse("dst_non_slot")
        std = naive < datetime(2026, 3, 8, 3, 0) or naive >= datetime(2026, 11, 1, 2, 0)
        us = (
            int(naive.replace(tzinfo=timezone.utc).timestamp()) * 1_000_000
            + (5 if std else 4) * 3_600_000_000
        )
        return fmt_instant(us)

    def _slot_entry(self, e, whole_window_checks=True):
        """Validate one slot or coverage entry; return (instant, lo, hi)."""
        if "local" in e:
            instant = self._local_to_utc(
                e["local"], e["tz"], check_gap=self.on("slot.dst")
            )
        else:
            instant = e["instant"]
        win = e.get("window")
        if not win:
            raise Refuse(
                "coverage_invalid" if not whole_window_checks else "slot_window_invalid"
            )
        lo, hi, at = (
            parse_instant_us(win["not_before"]),
            parse_instant_us(win["not_after"]),
            parse_instant_us(instant),
        )
        if self.on("slot.window_valid") and not lo < hi:
            raise Refuse(
                "slot_window_invalid" if whole_window_checks else "coverage_invalid"
            )
        if lo < hi and self.on("slot.window_instant") and not (lo <= at < hi):
            raise Refuse(
                "slot_outside_window" if whole_window_checks else "coverage_invalid"
            )
        return instant, lo, hi

    def _slot_key(self, scope, instant, digest):
        key_obj = {
            "domain": "slot",
            "instant": instant,
            "rule": digest,
            "scope": scope,
            "v": 0,
        }
        return "slot:" + dig(key_obj)

    def _check_rule(self, rule):
        if self.on("slot.schedule_pinned") and self.schedule_rule is None:
            raise Refuse("schedule_not_configured")
        if self.on("slot.identity_rule") and (
            rule["contract"] != "contract: recurrence/v0"
            or (self.schedule_rule and rule["digest"] != self.schedule_rule)
        ):
            raise Refuse("slot_identity_mismatch")

    def _plan_slot(self, s_, label, defname):
        instant, lo, hi = self._slot_entry(s_)
        digest = s_["rule"]["digest"]
        self._check_rule(s_["rule"])
        scope = s_["scope"]
        ident = (scope, instant)
        prev = self.slots.get(ident)
        if (
            prev
            and self.on("slot.identity_changed")
            and (prev["rule"] != digest or prev["window"] != s_["window"])
        ):
            raise Refuse("slot_identity_mismatch")
        key = self._slot_key(scope, instant, digest)
        exists = (scope, key) in self.identity
        if not exists and self.on("slot.window_clock") and self.clock >= hi:
            raise Refuse("slot_outside_window")
        if exists:
            tid = dig({"authority": scope, "invocation_key": key, "v": 0})
            self._register(
                self.ids[tid], scope, key, defname, derived=True, anchor_us=lo
            )
        else:
            self._register(
                label, scope, key, defname, derived=True, anchor_us=lo, dry=True
            )
        return {
            "ident": ident,
            "scope": scope,
            "key": key,
            "instant": instant,
            "lo": lo,
            "hi": hi,
            "digest": digest,
            "window": s_["window"],
            "label": label,
            "defname": defname,
            "exists": exists,
        }

    def _commit_slot(self, plan):
        created = False
        if not plan["exists"]:
            _tid, created = self._register(
                plan["label"],
                plan["scope"],
                plan["key"],
                plan["defname"],
                derived=True,
                anchor_us=plan["lo"],
            )
        if created:
            self.slots[plan["ident"]] = {
                "rule": plan["digest"],
                "window": plan["window"],
            }
            self.tasks[plan["label"]].update(
                slot_lo=plan["lo"],
                slot_hi=plan["hi"],
                slot_instant=parse_instant_us(plan["instant"]),
                slot_key=plan["key"],
            )
        return plan["key"], plan["lo"] <= self.clock < plan["hi"]

    def op_supply_slot(self, a):
        if "coverage" in a:
            self.coverage = a["coverage"]
            return {}
        if "occurrence_set" in a:
            labels = a["as"] if isinstance(a["as"], list) else [a["as"]]
            plans = [
                self._plan_slot(s_, label, a["definition"])
                for s_, label in zip(a["occurrence_set"], labels)
            ]
            keys = [p["key"] for p in plans]
            if len(set(keys)) != len(keys) and self.on("slot.set_unique"):
                raise Refuse("malformed")
            ids, elig = [], []
            for p in plans:
                self._batch_fault(len(ids))
                sid, e = self._commit_slot(p)
                ids.append(sid)
                elig.append(e)
            return {"slot_ids": ids, "eligible": all(elig)}
        sid, e = self._commit_slot(self._plan_slot(a["slot"], a["as"], a["definition"]))
        return {"slot_id": sid, "eligible": e}

    def op_evaluate_slots(self, a):
        if a.get("coverage") is None:
            if self.on("slot.coverage"):
                raise Refuse("coverage_not_supplied")
            return {"missed": []}
        cov = a["coverage"]
        digest = cov["rule"]["digest"]
        self._check_rule(cov["rule"])
        expected = cov.get("expected")
        if self.on("slot.coverage_bounds") and expected is None:
            raise Refuse("coverage_invalid")
        frm = parse_instant_us(cov["from"])
        to = parse_instant_us(cov["to"])
        if self.on("slot.coverage_bounds") and (not frm < to or to > self.clock):
            raise Refuse("coverage_invalid")
        scope = cov["scope"]
        plan = []
        seen = set()
        for e in expected or []:
            inst, lo, hi = self._slot_entry(e, whole_window_checks=False)
            if self.on("slot.coverage_bounds") and not (
                frm <= parse_instant_us(inst) < to
            ):
                raise Refuse("coverage_invalid")
            if inst in seen and self.on("slot.set_unique"):
                raise Refuse("malformed")
            seen.add(inst)
            win = e["window"]
            prev = self.slots.get((scope, inst))
            if (
                prev
                and self.on("slot.identity_changed")
                and (prev["rule"] != digest or prev["window"] != win)
            ):
                raise Refuse("slot_identity_mismatch")
            key = self._slot_key(scope, inst, digest)
            label = a["labels"].get(inst)
            if label is None:
                raise Refuse("malformed")
            if (scope, key) in self.identity:
                tid = dig({"authority": scope, "invocation_key": key, "v": 0})
                self._register(self.ids[tid], scope, key, a["definition"], derived=True)
                plan.append(("existing", self.ids[tid], inst, hi))
                continue
            if self.clock < hi:
                continue  # a past instant whose window is still open is not missed
            self._register(
                label,
                scope,
                key,
                a["definition"],
                derived=True,
                anchor_us=parse_instant_us(win["not_before"]),
                dry=True,
            )
            plan.append(("new", label, inst, win, key))
        missed = []
        for item in plan:
            self._batch_fault(len(missed))
            if item[0] == "existing":
                _k, label, inst, hi = item
                t = self.tasks[label]
                if (
                    self.on("coverage.marks_existing")
                    and t["state"] in ("pending", "waiting")
                    and t["started"] == 0
                    and not t["cancel_req"]
                    and t.get("slot_hi") is not None
                    and self.clock >= t["slot_hi"]
                ):
                    self._commit(label, "missed", None)
                    missed.append(inst)
                continue
            _k, label, inst, win, key = item
            self._register(
                label,
                scope,
                key,
                a["definition"],
                derived=True,
                anchor_us=parse_instant_us(win["not_before"]),
            )
            self.slots[(scope, inst)] = {"rule": digest, "window": win}
            self.tasks[label].update(slot_instant=parse_instant_us(inst), slot_key=key)
            self._commit(label, "missed", None)
            missed.append(inst)
        return {"missed": missed}

    def op_catch_up(self, a):
        m = self.tasks.get(a["missed_task"])
        if self.on("catchup.terminal") and (m is None or m["state"] != "missed"):
            raise Refuse("missed_not_terminal")
        if self.on("catchup.permitted") and self.max_lag_us is None:
            raise Refuse("catch_up_not_permitted")
        key = "catchup:" + dig({"catch_up_of": m["id"], "domain": "catch_up", "v": 0})
        lag = self.clock - m.get("slot_instant", self.clock)
        if (
            (m["authority"], key) not in self.identity
            and self.on("catchup.lag")
            and self.max_lag_us is not None
            and not (0 <= lag <= self.max_lag_us)
        ):
            raise Refuse("lag_exceeded")
        tid, created = self._register(
            a["as"], m["authority"], key, a["definition"], derived=True
        )
        if created:
            self.tasks[a["as"]]["catchup_instant"] = m.get("slot_instant")
        return {"task_id": tid}


def load_golden() -> dict:
    return json.loads(
        (BASE / "examples/task-definition.example.json").read_text(encoding="utf-8")
    )


def match(expect_ok: dict, got: dict) -> bool:
    return all(k in got and got[k] == v for k, v in expect_ok.items())


class Driver:
    """The trusted adapter: it attaches the authority handle it acquired to each
    committing operation. The handle changes only when this adapter's own recovery
    succeeds; it is never looked up from the model at commit time, so a handle that
    another owner has superseded is refused as stale. Harness meta keys (not part of
    the contract): `authority_handle: null` on a vector or `no_handle` on an op
    presents no generation; `other_owner` on a recover means a different process
    took the claim, so this adapter keeps its old handle."""

    META = ("no_handle", "other_owner")

    def __init__(self, vector, golden, disabled, seen=None):
        self.m = Model(vector, golden, disabled)
        self.m.seen = seen
        h = vector.get("authority_handle", {"generation": 1})
        self.handle = None if h is None else h["generation"]

    def step(self, op):
        a = {k: v for k, v in op.items() if k not in self.META}
        if (
            a["op"] in Model.GEN_OPS
            and self.handle is not None
            and not op.get("no_handle")
            and "generation" not in a
        ):
            a["generation"] = self.handle
        self.m.preflight(a["op"], a)
        result = getattr(self.m, "op_" + a["op"])(a)
        if a["op"] == "recover" and not op.get("other_owner"):
            self.handle = a["generation"]
        return result


def run_vector(
    vector: dict, golden: dict, disabled: set[str], seen: set[str] | None = None
) -> list[str]:
    errs: list[str] = []
    drv = Driver(vector, golden, disabled, seen)
    m = drv.m
    for i, op in enumerate(vector["ops"]):
        name = op["op"]
        exp = op["expect"]
        if not hasattr(m, f"op_{name}"):
            errs.append(f"op {i}: unknown op {name}")
            continue
        try:
            got = drv.step(op)
        except (
            KeyError,
            TypeError,
            ValueError,
            IndexError,
            OverflowError,
            AttributeError,
        ) as exc:
            errs.append(
                f"op {i} {name}: model could not execute ({type(exc).__name__}: {exc})"
            )
            continue
        except Refuse as r:
            if exp.get("refused") != r.reason:
                errs.append(f"op {i} {name}: refused {r.reason!r}, expected {exp!r}")
            continue
        if "refused" in exp:
            errs.append(f"op {i} {name}: accepted, expected refusal {exp['refused']!r}")
        elif not match(exp.get("ok", {}), got):
            errs.append(
                f"op {i} {name}: result {got!r} does not match {exp.get('ok')!r}"
            )
    ex = vector.get("expected", {})
    if "history" in ex and ex["history"] != m.history:
        errs.append(
            f"history mismatch: model {m.history!r} vs authored {ex['history']!r}"
        )
    for label, want in ex.get("tasks", {}).items():
        t = m.tasks.get(label)
        if t is None:
            errs.append(f"expected task {label} was never created")
            continue
        if want.get("state") != t["state"]:
            errs.append(
                f"task {label}: state {t['state']!r}, expected {want.get('state')!r}"
            )
        if "attempts" in want:
            got_att = [{"n": a["n"], "result": a["result"]} for a in t["attempts"]]
            want_att = [{"n": a["n"], "result": a["result"]} for a in want["attempts"]]
            if got_att != want_att:
                errs.append(
                    f"task {label}: attempts {got_att!r}, expected {want_att!r}"
                )
    return errs


def load_vectors(files: list[str] | None = None) -> list[tuple[pathlib.Path, dict]]:
    out = []
    paths = (
        [pathlib.Path(f) for f in files]
        if files
        else sorted((BASE / "vectors").rglob("*.json"))
    )
    for p in paths:
        if p.name == "INVENTORY.json":
            continue
        out.append((p, json.loads(p.read_text(encoding="utf-8"))))
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--disable", action="append", default=[], help="disable one named guard"
    )
    ap.add_argument("--list-guards", action="store_true")
    ap.add_argument(
        "--expect-fail", action="store_true", help="succeed only if some vector fails"
    )
    ap.add_argument(
        "--file",
        action="append",
        default=[],
        help="check only these vector files (fixtures outside vectors/)",
    )
    ns = ap.parse_args(argv)
    if ns.list_guards:
        print("\n".join(GUARDS))
        return 0
    bad = set(ns.disable) - set(GUARDS)
    if bad:
        print(f"unknown guard(s): {sorted(bad)}", file=sys.stderr)
        return 2
    golden = load_golden()
    failed = 0
    vectors = load_vectors(ns.file)
    if not vectors:
        print("[!!] no vectors found", file=sys.stderr)
        return 1
    for path, vec in vectors:
        if vec.get("id") != path.stem:
            print(f"[!!] {path.name}: id does not equal filename", file=sys.stderr)
            failed += 1
            continue
        if not ns.file and path.parent.name != vec.get("mode"):
            print(f"[!!] {path.name}: mode does not equal directory", file=sys.stderr)
            failed += 1
            continue
        errs = run_vector(vec, golden, set(ns.disable))
        if errs:
            failed += 1
            if not ns.expect_fail:
                for e in errs:
                    print(f"[!!] {vec['id']}: {e}", file=sys.stderr)
    if ns.expect_fail:
        return 0 if failed else 1
    if failed:
        print(f"[!!] {failed} of {len(vectors)} vectors failed", file=sys.stderr)
        return 1
    print(f"[ok] {len(vectors)} durable-runner vectors match the reference model")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
