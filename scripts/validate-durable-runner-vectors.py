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
    "profile.journal_v1",
    "profile.authority_scope",
    "profile.store_window",
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
    "slot.identity",
    "slot.window",
    "slot.dst",
    "slot.coverage",
    "catchup.lag",
    "catchup.permitted",
    "catchup.terminal",
    "mode.supported",
    "outcome.class_match",
    "requirement.supported",
    "wire.instant_strict",
    "time.typed_format",
    "transition.failed_gate",
    "start.horizon",
    "recover.abandon_gate",
    "checkpoint.eligible",
    "checkpoint.held_body",
    "profile.effective_window",
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
    m = _DUR.match(text)
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
    m = _INSTANT.match(text)
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
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + f".{us % 1_000_000:06d}Z"


# ---------------------------------------------------------------- model
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

    def on(self, g: str) -> bool:
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
                    parse_duration_us(t[key])
                except Refuse:
                    raise Refuse("definition_invalid")
        if d["retry"]["max_attempts"] < 1:
            raise Refuse("definition_invalid")
        w = d.get("idempotency_window")
        if w is not None:
            try:
                wu = parse_duration_us(w)
            except Refuse:
                raise Refuse("definition_invalid")
            if not (self.kind_min_us <= wu <= self.kind_max_us):
                raise Refuse("definition_invalid")
        if not d.get("outcome_mapping"):
            raise Refuse("definition_invalid")

    # -- ops
    def op_profile_admit(self, a):
        p = a["profile"]
        modes = p.get("modes", [])
        if self.on("profile.sealed_reserved") and "sealed" in modes:
            raise Refuse("sealed_mode_reserved")
        if self.on("profile.mode_prefix") and modes != MODES[: len(modes)]:
            raise Refuse("mode_not_cumulative")
        if (
            self.on("profile.remote_coverage")
            and p.get("remote_sealed_coverage", "none") != "none"
        ):
            raise Refuse("remote_coverage_claimed")
        if self.on("profile.replication") and p.get("replication", "none") != "none":
            raise Refuse("replication_claimed")
        if "journaled" in modes:
            if (
                self.on("profile.journal_v1")
                and p.get("journal_contract", "contract: durable-record/v1")
                != "contract: durable-record/v1"
            ):
                raise Refuse("journal_contract_not_v1")
            if (
                self.on("profile.journal_ack")
                and p.get("attempt_journal_ack", "none") == "none"
            ):
                raise Refuse("journal_ack_insufficient")
        if (
            self.on("profile.authority_scope")
            and p.get("authority_scope", "single_host_exclusive")
            != "single_host_exclusive"
        ):
            raise Refuse("authority_scope_unsupported")
        win = p.get("window")
        if win:
            lo, df, hi = (parse_duration_us(win[k]) for k in ("min", "default", "max"))
            rng = p.get("task_kind_window_range")
            klo, khi = (
                (parse_duration_us(rng["min"]), parse_duration_us(rng["max"]))
                if rng
                else (0, SAFE_MAX)
            )
            if self.on("profile.window_range") and rng:
                if lo < klo or hi > khi or not (lo <= df <= hi):
                    raise Refuse("window_out_of_range")
            sw = p.get("store_window")
            eff = (
                parse_duration_us(p["effective_window"])
                if p.get("effective_window")
                else df
            )
            if self.on("profile.effective_window") and rng:
                if not (klo <= eff <= khi):
                    raise Refuse("window_out_of_range")
            need = max(
                eff,
                parse_duration_us(p["retry_horizon"]) if p.get("retry_horizon") else 0,
            )
            if self.on("profile.store_window") and sw and parse_duration_us(sw) < need:
                raise Refuse("store_window_too_short")
        sw = p.get("store_window")
        if sw:
            self.store_window_us = parse_duration_us(sw)
        if p.get("identity_history") == "discarded":
            self.history_retained = False
        rng = p.get("task_kind_window_range")
        if rng:
            self.kind_min_us, self.kind_max_us = (
                parse_duration_us(rng["min"]),
                parse_duration_us(rng["max"]),
            )
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

    def op_submit(self, a):
        d = self.defs[a["definition"]]
        self._validate_def(d)
        if d["retry"]["max_attempts"] > 1:
            self._need("retrying")
        spec = dig(d)
        k = (a["authority"], a["key"])
        tid = dig({"authority": a["authority"], "invocation_key": a["key"], "v": 0})
        rec = self.identity.get(k)
        if rec:
            expired = self.clock - rec["accepted_us"] > self.store_window_us
            if (
                expired
                and not self.history_retained
                and self.on("identity.expired_unresolved")
            ):
                raise Refuse("identity_unresolved")
            if rec["spec"] != spec:
                if self.on("identity.conflict"):
                    raise Refuse("identity_conflict")
            else:
                label = self.ids.get(tid)
                t = self.tasks[label]
                return {"disposition": "observed", "task_id": tid, "state": t["state"]}
        label = a["as"]
        self.identity[k] = {"spec": spec, "accepted_us": self.clock}
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
            "accepted_us": self.clock,
            "first_start_us": None,
            "catch_up_of": None,
        }
        self._commit(label, "pending", None)
        return {"disposition": "created", "task_id": tid, "state": "pending"}

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
        if a["task"] not in self.tasks:
            if self.on("transition.first_pending") and a["to"] != "pending":
                raise Refuse("first_not_pending")
            raise Refuse("predecessor_mismatch")
        t = self.tasks[a["task"]]
        d = t["def"]
        to = a["to"]
        at = a.get("attempt")
        if (
            self.on("generation.stale")
            and a.get("generation", self.generation) < self.generation
        ):
            raise Refuse("generation_stale")
        prior = a.get("prior", "head")
        if self.on("transition.predecessor") and prior != "head":
            raise Refuse("predecessor_mismatch")
        cur = t["state"]
        if self.on("transition.terminal") and cur in TERMINAL:
            raise Refuse("terminal_resurrection")
        if self.on("transition.table") and to not in ALLOWED.get(cur, set()):
            raise Refuse("illegal_transition")
        if to == "missed" and self.on("transition.table"):
            hi = t.get("slot_hi")
            if t["started"] > 0 or hi is None or self.clock <= hi:
                raise Refuse("illegal_transition")
        if to == "cancelled" and self.on("cancel.confirmed"):
            raise Refuse("cancellation_not_confirmed")
        if (
            to == "failed"
            and cur in ("pending", "waiting")
            and self.on("transition.failed_gate")
        ):
            r = a.get("reason")
            mx = d["retry"]["max_attempts"]
            ok = (
                (r == "pre_execution_refusal" and cur == "pending")
                or (r == "deadline_expired" and self._past_deadline(t, d))
                or (
                    r == "retry_exhausted"
                    and cur == "waiting"
                    and (t["started"] >= mx or self._past_horizon(t, d, self.clock))
                )
            )
            if not ok:
                raise Refuse("illegal_transition")
        retry_cfg = d["retry"]
        mapping = {m["code"]: m for m in d["outcome_mapping"]}
        if to == "running":
            n = at["n"]
            if self.on("attempt.contiguous") and n != t["started"] + 1:
                raise Refuse("attempt_not_contiguous")
            if self.on("attempt.limit") and n > retry_cfg["max_attempts"]:
                raise Refuse("attempt_limit_exhausted")
            if self.on("retry.deadline") and self._past_deadline(t, d):
                raise Refuse("deadline_exceeded")
            if self.on("start.horizon") and self._past_horizon(t, d, self.clock):
                raise Refuse("horizon_exceeded")
            cp = at.get("checkpoint")
            if cp is not None:
                rec = (
                    self.checkpoints[cp - 1]
                    if 1 <= cp <= len(self.checkpoints)
                    else None
                )
                if self.on("checkpoint.eligible") and (
                    rec is None or rec["task"] != a["task"] or rec["attempt"] >= n
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
                {
                    "n": n,
                    "result": "running",
                    "effects": None,
                    "dispatch": at.get("dispatch", "intended"),
                }
            )
            if t["first_start_us"] is None:
                t["first_start_us"] = self.clock
            t["next_eligible"] = None
            rev = self._commit(a["task"], "running", {"n": n, "phase": "start"})
            return {"revision": rev, "state": "running"}
        if cur == "running" and at:
            att = t["attempts"][-1]
            code = at.get("outcome")
            if (
                code is not None
                and code not in mapping
                and self.on("outcome.known_code")
            ):
                raise Refuse("unknown_outcome_code")
            if code in mapping and self.on("outcome.class_match"):
                claimed_ok = at.get("result") == "succeeded" or (
                    at.get("result") is None and to == "succeeded"
                )
                claimed_bad = at.get("result") == "failed" or (
                    at.get("result") is None and to in ("failed", "waiting")
                )
                is_ok = mapping[code]["result"] == "success"
                if (claimed_ok and not is_ok) or (claimed_bad and is_ok):
                    raise Refuse("outcome_mapping_mismatch")
            if to == "succeeded":
                if self.on("success.after_cancel") and t["cancel_req"]:
                    raise Refuse("cancellation_precedes_success")
                if self.on("success.verified") and not at.get(
                    "outputs_verified", False
                ):
                    raise Refuse("success_unverified_outputs")
            if to == "waiting":
                if at.get("effects") == "unknown" and self.on("retry.unknown_effects"):
                    raise Refuse("unknown_effects_not_retryable")
                reason = at.get("reason")
                if (
                    self.on("retry.reason")
                    and reason not in retry_cfg["retryable_reasons"]
                ):
                    raise Refuse("retry_not_permitted")
                if (
                    self.on("attempt.limit")
                    and t["started"] >= retry_cfg["max_attempts"]
                ):
                    raise Refuse("attempt_limit_exhausted")
                ne = a.get("next_eligible_at")
                if self.on("retry.jitter_persisted") and ne is None:
                    raise Refuse("jitter_not_persisted")
                if ne is not None:
                    neu = parse_instant_us(ne)
                    if self.on("retry.deadline") and self._past_deadline(t, d, neu):
                        raise Refuse("deadline_exceeded")
                    if self.on("retry.horizon") and self._past_horizon(t, d, neu):
                        raise Refuse("horizon_exceeded")
                    t["next_eligible"] = neu
            att["result"] = at.get(
                "result",
                {
                    "succeeded": "succeeded",
                    "failed": "failed",
                    "waiting": "failed",
                    "abandoned": "abandoned",
                }.get(to, "failed"),
            )
            att["effects"] = at.get("effects")
            att["outcome"] = code
            att["dispatch"] = at.get("dispatch", att["dispatch"])
            rev = self._commit(
                a["task"],
                to,
                {"n": att["n"], "phase": "finish", "result": att["result"]},
            )
            return {"revision": rev, "state": to}
        rev = self._commit(a["task"], to, None)
        return {"revision": rev, "state": to}

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

    def op_request_cancel(self, a):
        t = self.tasks[a["task"]]
        if t["state"] in TERMINAL:
            if t["state"] == "succeeded":
                return {"effect": "too_late"}
            raise Refuse("task_terminal")
        t["cancel_req"] = True
        return {"effect": "recorded"}

    def op_confirm_cancel(self, a):
        t = self.tasks[a["task"]]
        if self.on("cancel.confirmed") and not t["cancel_req"]:
            raise Refuse("cancel_not_requested")
        if self.on("cancel.confirmed") and not a.get("quiescent", False):
            raise Refuse("quiescence_not_established")
        att = None
        if t["attempts"] and t["attempts"][-1]["result"] == "running":
            t["attempts"][-1]["result"] = "cancelled"
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
        self.clock += by
        return {"now": fmt_instant(self.clock)}

    def op_crash(self, a):
        self.crashed = True
        return {"journal_head": len(self.history)}

    def op_recover(self, a):
        pred = a["predecessor"]
        if self.on("recover.quiescence") and pred == "unproven":
            raise Refuse("predecessor_not_quiescent")
        self.generation = a["generation"]
        self.crashed = False
        out = {}
        for label, t in self.tasks.items():
            if t["state"] == "running":
                eff = a.get("effects", "none")
                att = t["attempts"][-1]
                att["result"] = "abandoned"
                att["effects"] = eff
                rc = t["def"]["retry"]
                expired = self._past_deadline(t, t["def"]) or self._past_horizon(
                    t, t["def"], self.clock
                )
                can_wait = (
                    eff != "unknown"
                    and t["started"] < rc["max_attempts"]
                    and (
                        not self.on("recover.abandon_gate")
                        or (rc.get("retry_after_abandonment", False) and not expired)
                    )
                )
                nxt = "waiting" if can_wait else "abandoned"
                self._commit(
                    label,
                    nxt,
                    {"n": att["n"], "phase": "finish", "result": "abandoned"},
                )
                if nxt == "waiting":
                    t["next_eligible"] = self.clock
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
        if self.tasks[a["task"]]["state"] not in TERMINAL:
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
                if self.on("admission.unsettled") and self.carried > 0:
                    raise Refuse("unsettled_reservation")
                if self.on("admission.rate"):
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
        """Fixture-limited tz table: America/New_York, 2026 (spring gap 02:00-03:00 on 2026-03-08)."""
        if tz != "America/New_York":
            raise ValueError(f"model has no rule table for {tz}")
        naive = datetime.strptime(local, "%Y-%m-%dT%H:%M:%S")
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

    def _create(self, label, authority, key_obj, d):
        spec = dig(d)
        key = dig(key_obj)
        tid = dig({"authority": authority, "invocation_key": key, "v": 0})
        if (authority, key) in self.identity:
            return tid, False
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
            "accepted_us": self.clock,
            "first_start_us": None,
        }
        self._commit(label, "pending", None)
        return tid, True

    def _one_slot(self, s, label, defname):
        if "local" in s:
            instant = self._local_to_utc(
                s["local"], s["tz"], check_gap=self.on("slot.dst")
            )
        else:
            if self.on("slot.dst") and s.get("dst_skipped"):
                raise Refuse("dst_non_slot")
            instant = s["instant"]
        digest = s["rule"]["digest"]
        if (
            self.on("slot.identity")
            and self.schedule_rule
            and digest != self.schedule_rule
        ):
            raise Refuse("slot_identity_mismatch")
        lo, hi, at = (
            parse_instant_us(s["window"]["not_before"]),
            parse_instant_us(s["window"]["not_after"]),
            parse_instant_us(instant),
        )
        ident = (s["scope"], instant)
        prev = self.slots.get(ident)
        if (
            prev
            and self.on("slot.identity")
            and (prev["rule"] != digest or prev["window"] != s["window"])
        ):
            raise Refuse("slot_identity_mismatch")
        if self.on("slot.window") and (not (lo <= at <= hi) or self.clock > hi):
            raise Refuse("slot_outside_window")
        key_obj = {"instant": instant, "rule": digest, "scope": s["scope"]}
        self.slots[ident] = {"rule": digest, "window": s["window"]}
        tid, _ = self._create(label, s["scope"], key_obj, self.defs[defname])
        self.tasks[label]["slot_hi"] = hi
        return dig(key_obj), self.clock >= lo

    def op_supply_slot(self, a):
        if "coverage" in a:
            self.coverage = a["coverage"]
            return {}
        if "occurrence_set" in a:
            labels = a["as"] if isinstance(a["as"], list) else [a["as"]]
            ids, elig = [], []
            for s, label in zip(a["occurrence_set"], labels):
                sid, e = self._one_slot(s, label, a["definition"])
                ids.append(sid)
                elig.append(e)
            return {"slot_ids": ids, "eligible": all(elig)}
        sid, e = self._one_slot(a["slot"], a["as"], a["definition"])
        return {"slot_id": sid, "eligible": e}

    def op_evaluate_slots(self, a):
        if self.on("slot.coverage") and a.get("coverage") is None:
            raise Refuse("coverage_not_supplied")
        cov = a.get("coverage") or {"expected": [], "rule": {"digest": ""}, "scope": ""}
        missed = []
        for inst in cov["expected"]:
            key_obj = {
                "instant": inst,
                "rule": cov["rule"]["digest"],
                "scope": cov["scope"],
            }
            if (cov["scope"], dig(key_obj)) in self.identity or parse_instant_us(
                inst
            ) > self.clock:
                continue
            self._create(
                a["labels"][inst], cov["scope"], key_obj, self.defs[a["definition"]]
            )
            self._commit(a["labels"][inst], "missed", None)
            missed.append(inst)
        return {"missed": missed}

    def op_catch_up(self, a):
        m = self.tasks.get(a["missed_task"])
        if self.on("catchup.terminal") and (m is None or m["state"] != "missed"):
            raise Refuse("missed_not_terminal")
        if self.on("catchup.permitted") and self.max_lag_us is None:
            raise Refuse("catch_up_not_permitted")
        if self.on("catchup.lag") and parse_duration_us(a["lag"]) > (
            self.max_lag_us or 0
        ):
            raise Refuse("lag_exceeded")
        tid, _ = self._create(
            a["as"],
            "catch-up",
            {"catch_up_of": m["id"], "v": 0},
            self.defs[a["definition"]],
        )
        return {"task_id": tid}


# ---------------------------------------------------------------- driver
def load_golden() -> dict:
    return json.loads((BASE / "examples/task-definition.example.json").read_text())


def match(expect_ok: dict, got: dict) -> bool:
    return all(k in got and got[k] == v for k, v in expect_ok.items())


def run_vector(vector: dict, golden: dict, disabled: set[str]) -> list[str]:
    errs: list[str] = []
    m = Model(vector, golden, disabled)
    for i, op in enumerate(vector["ops"]):
        name = op["op"]
        fn = getattr(m, f"op_{name}", None)
        exp = op["expect"]
        if name in Model.OP_MODE:
            _orig = fn

            def fn(a, _orig=_orig, _name=name):
                m._need(Model.OP_MODE[_name])
                return _orig(a)

        if fn is None:
            errs.append(f"op {i}: unknown op {name}")
            continue
        try:
            got = fn(op)
        except (KeyError, TypeError, ValueError, IndexError) as exc:
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
        out.append((p, json.loads(p.read_text())))
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
