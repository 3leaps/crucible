#!/usr/bin/env python3
"""Recurrence-rule corpus controls: an independent verifier, not a generator.

Invocation set (PDR-0006): Python 3 stdlib and goneat JSON Schema validation.
No network requests, no host time-zone data and no instance-selected
executable or schema paths are used.

The corpus expectations are written by hand. This checker re-derives every
expectation from the normative rules and the in-repo tzdb transition evidence
and fails on any disagreement. It never writes expected values. Offsets come
only from corpus/tzdb-evidence.json, so results do not depend on the host.
"""

import calendar
import datetime as dt
import hashlib
import importlib.util
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / "schemas/recurrence/v0"
CORPUS = BASE / "corpus"
SCHEMA = BASE / "recurrence-rule.schema.json"
DOCUMENT = BASE / "rule-document.schema.json"
STANDARD = ROOT / "docs/standards/recurrence-rule-contract.md"
_jspec = importlib.util.spec_from_file_location(
    "jcs", ROOT / "scripts/rfc8785-canonicalize.py"
)
_jcs = importlib.util.module_from_spec(_jspec)
_jspec.loader.exec_module(_jcs)

WEEKDAYS = ("MO", "TU", "WE", "TH", "FR", "SA", "SU")
FREQS = ("MINUTELY", "HOURLY", "DAILY", "WEEKLY", "MONTHLY", "YEARLY")
LISTS = ("by_month", "by_month_day", "by_hour", "by_minute", "by_set_pos")
TEXT_LISTS = {
    "BYMONTH": "by_month",
    "BYMONTHDAY": "by_month_day",
    "BYHOUR": "by_hour",
    "BYMINUTE": "by_minute",
    "BYSETPOS": "by_set_pos",
}
UNSUPPORTED_PARTS = ("BYSECOND", "BYWEEKNO", "BYYEARDAY", "RSCALE", "SKIP")
LOCAL = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})$")
UTC = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z$")
TEXT_LOCAL = re.compile(r"^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})$")
TEXT_UTC = re.compile(r"^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$")
INT = re.compile(r"^[+-]?[1-9][0-9]*$|^0$")
DAY = re.compile(r"^([+-]?[1-9][0-9]?)?(MO|TU|WE|TH|FR|SA|SU)$")
MARGIN = dt.timedelta(days=2)


class Refusal(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def load(path):
    return _jcs.jcs_loads(pathlib.Path(path).read_text(encoding="utf-8"))


# --- tzdb evidence -----------------------------------------------------------


def parse_offset(text):
    sign = -1 if text[0] == "-" else 1
    return sign * dt.timedelta(hours=int(text[1:3]), minutes=int(text[4:6]))


class Zones:
    def __init__(self, evidence):
        self.version = evidence["tzdb_version"]
        self.accepted = set(evidence["accepted_names"])
        lo, hi = evidence["window"]["from"], evidence["window"]["to"]
        self.window = (utc_instant(lo), utc_instant(hi))
        self.zones = {}
        for name, z in evidence["zones"].items():
            segments = [(self.window[0], parse_offset(z["initial_offset"]))]
            for t in z["transitions"]:
                segments.append((utc_instant(t["at"]), parse_offset(t["offset"])))
            assert all(a[0] < b[0] for a, b in zip(segments, segments[1:])), name
            self.zones[name] = segments
        for name, link in evidence["links"].items():
            assert name in self.accepted and link["target"] in self.zones, name
            self.zones[name] = self.zones[link["target"]]
        # Recorded so a checker that wrongly accepted them would still expand.
        for name, alias in evidence["deprecated_aliases"].items():
            assert name not in self.accepted and alias["target"] in self.zones, name
            self.zones[name] = self.zones[alias["target"]]

    def check(self, tzid):
        require(tzid in self.accepted, "invalid_tzid")

    def resolve(self, tzid, local, explicit):
        """Map a civil time to UTC. Generated gap instances return None;
        explicit gap times use the pre-gap offset; overlaps take the earlier
        instant."""
        assert tzid in self.zones, ("no transition evidence for", tzid)
        segments = self.zones[tzid]
        found = []
        for i, (start, offset) in enumerate(segments):
            end = segments[i + 1][0] if i + 1 < len(segments) else self.window[1]
            instant = local - offset
            if start <= instant < end:
                found.append(instant)
        assert (
            self.window[0] + MARGIN <= local - segments[0][1] < self.window[1] - MARGIN
        ), (
            "outside evidence window",
            tzid,
            local,
        )
        if found:
            return min(found)
        if not explicit:
            return None
        for i in range(1, len(segments)):
            start, offset = segments[i]
            prior = segments[i - 1][1]
            if offset > prior and start + prior <= local < start + offset:
                return local - prior
        raise AssertionError(("unresolvable local time", tzid, local))


# --- value parsing -----------------------------------------------------------


def civil(match):
    y, mo, d, h, mi, s = (int(g) for g in match.groups())
    require(y >= 1, "invalid_date")
    require(1 <= mo <= 12 and 1 <= d <= calendar.monthrange(y, mo)[1], "invalid_date")
    require(h <= 23 and mi <= 59 and s <= 59, "invalid_date")
    return dt.datetime(y, mo, d, h, mi, s)


def local_time(text):
    match = LOCAL.match(text)
    assert match, ("schema admitted a non-local time", text)
    return civil(match)


def utc_instant(text):
    match = UTC.match(text)
    assert match, ("not a UTC instant", text)
    return civil(match)


def fmt_local(value):
    return value.strftime("%Y-%m-%dT%H:%M:%S")


def fmt_utc(value):
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


# --- normalization and digest (A5) --------------------------------------------


def day_key(entry):
    return (WEEKDAYS.index(entry["day"]), "ordinal" in entry, entry.get("ordinal", 0))


def normalize(rule):
    out = {}
    for key, value in rule.items():
        if key in LISTS:
            value = sorted(set(value))
        elif key == "by_day":
            unique = {json.dumps(e, sort_keys=True): e for e in value}
            value = sorted(unique.values(), key=day_key)
        elif key in ("rdate", "exdate"):
            value = sorted(set(value))
        if value == [] or (key, value) in (
            ("interval", 1),
            ("wkst", "MO"),
            ("calendar", "gregorian"),
        ):
            continue
        out[key] = value
    return out


def canonical_bytes(rule):
    return _jcs.jcs_dumps(normalize(rule)).encode("utf-8")


def digest(rule):
    return "sha256:" + hashlib.sha256(canonical_bytes(rule)).hexdigest()


# --- RFC 5545 text form --------------------------------------------------------


def serialize(rule):
    r = normalize(rule)
    lines = [
        "DTSTART;TZID=%s:%s"
        % (r["tzid"], r["dtstart"].replace("-", "").replace(":", ""))
    ]
    parts = ["FREQ=" + r["freq"]]
    if "interval" in r:
        parts.append("INTERVAL=%d" % r["interval"])
    if "count" in r:
        parts.append("COUNT=%d" % r["count"])
    if "until" in r:
        parts.append("UNTIL=" + r["until"].replace("-", "").replace(":", ""))
    for part, key in (("BYMONTH", "by_month"), ("BYMONTHDAY", "by_month_day")):
        if key in r:
            parts.append(part + "=" + ",".join(str(n) for n in r[key]))
    if "by_day" in r:
        parts.append(
            "BYDAY="
            + ",".join(str(e.get("ordinal", "")) + e["day"] for e in r["by_day"])
        )
    for part, key in (
        ("BYHOUR", "by_hour"),
        ("BYMINUTE", "by_minute"),
        ("BYSETPOS", "by_set_pos"),
    ):
        if key in r:
            parts.append(part + "=" + ",".join(str(n) for n in r[key]))
    if "wkst" in r:
        parts.append("WKST=" + r["wkst"])
    lines.append("RRULE:" + ";".join(parts))
    for prop, key in (("RDATE", "rdate"), ("EXDATE", "exdate")):
        if key in r:
            values = ",".join(v.replace("-", "").replace(":", "") for v in r[key])
            lines.append("%s;TZID=%s:%s" % (prop, r["tzid"], values))
    return lines


def text_int(value):
    require(INT.match(value) is not None, "invalid_text")
    return int(value)


def text_local(value):
    if TEXT_UTC.match(value):
        raise Refusal("invalid_text")
    match = TEXT_LOCAL.match(value)
    require(match is not None, "invalid_text")
    civil(match)
    y, mo, d, h, mi, s = match.groups()
    return f"{y}-{mo}-{d}T{h}:{mi}:{s}"


def parse_text(lines):
    """Parse the supported RFC 5545 subset into the JSON model (not normalized)."""
    require(
        isinstance(lines, list) and all(isinstance(x, str) for x in lines),
        "invalid_text",
    )
    rule, seen_rrule, tzid = {}, False, None
    dates = {"RDATE": [], "EXDATE": []}
    for line in lines:
        head, sep, value = line.partition(":")
        require(sep == ":" and value != "", "invalid_text")
        name, *params = head.split(";")
        if name in ("EXRULE",) or (name == "RRULE" and seen_rrule):
            raise Refusal("unsupported_part")
        if name == "RRULE":
            require(not params, "invalid_text")
            seen_rrule = True
            parse_rrule(value, rule)
            continue
        if name not in ("DTSTART", "RDATE", "EXDATE"):
            raise Refusal("unsupported_part")
        # Floating (no TZID) and UTC DTSTART values are not the v0 local form.
        require(len(params) == 1, "invalid_text" if not params else "unsupported_part")
        pname, eq, pvalue = params[0].partition("=")
        require(eq == "=", "invalid_text")
        if pname != "TZID":
            raise Refusal("unsupported_part")
        if name == "DTSTART":
            require(tzid is None, "invalid_text")
            tzid = pvalue
            rule["dtstart"] = text_local(value)
        else:
            dates[name].append((pvalue, [text_local(v) for v in value.split(",")]))
    require(tzid is not None and seen_rrule, "invalid_text")
    rule["tzid"] = tzid
    for name, key in (("RDATE", "rdate"), ("EXDATE", "exdate")):
        for ptz, values in dates[name]:
            require(ptz == tzid, "invalid_text")
            rule.setdefault(key, []).extend(values)
    return rule


def parse_rrule(value, rule):
    seen = set()
    for part in value.split(";"):
        name, eq, v = part.partition("=")
        require(eq == "=" and v != "" and name not in seen, "invalid_text")
        seen.add(name)
        if name in UNSUPPORTED_PARTS:
            raise Refusal("unsupported_part")
        if name == "FREQ":
            if v == "SECONDLY":
                raise Refusal("unsupported_part")
            require(v in FREQS, "invalid_text")
            rule["freq"] = v
        elif name in ("INTERVAL", "COUNT"):
            rule[name.lower()] = text_int(v)
        elif name == "UNTIL":
            match = TEXT_UTC.match(v)
            require(match is not None, "invalid_text")
            civil(match)
            y, mo, d, h, mi, s = match.groups()
            rule["until"] = f"{y}-{mo}-{d}T{h}:{mi}:{s}Z"
        elif name == "WKST":
            require(v in WEEKDAYS, "invalid_text")
            rule["wkst"] = v
        elif name == "BYDAY":
            entries = []
            for item in v.split(","):
                match = DAY.match(item)
                require(match is not None, "invalid_text")
                entry = {"day": match.group(2)}
                if match.group(1):
                    entry["ordinal"] = int(match.group(1))
                entries.append(entry)
            rule["by_day"] = entries
        elif name in TEXT_LISTS:
            rule[TEXT_LISTS[name]] = [text_int(n) for n in v.split(",")]
        else:
            raise Refusal("unsupported_part")
    require("freq" in rule, "invalid_text")


# --- schema and semantic validation (A6) -------------------------------------


def shape(doc, schema=SCHEMA):
    with tempfile.TemporaryDirectory(prefix="recurrence-shape-") as tmp:
        p = pathlib.Path(tmp) / "input.json"
        p.write_text(json.dumps(doc), encoding="utf-8")
        result = subprocess.run(
            [
                "goneat",
                "validate",
                "data",
                "--schema-file",
                str(schema),
                "--ref-dir",
                str(BASE),
                "--data",
                str(p),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode not in (0, 1):
            raise RuntimeError(result.stderr)
        return result.returncode == 0


def validate(rule, zones):
    """Semantic checks after schema acceptance, on the normalized rule so that
    duplicates cannot shift BYSETPOS positions during synchronization."""
    zones.check(rule["tzid"])
    start = civil(LOCAL.match(rule["dtstart"]))
    for key in ("rdate", "exdate"):
        for value in rule.get(key, []):
            civil(LOCAL.match(value))
    if "until" in rule:
        civil(UTC.match(rule["until"]))
    seeds = period_candidates(rule, zones, start, 0)
    require(start in seeds, "dtstart_not_synchronized")
    return rule


# --- expansion (A3) ------------------------------------------------------------


def month_add(year, month, n):
    index = year * 12 + month - 1 + n
    return index // 12, index % 12 + 1


def period_span(rule, start, k):
    """Days covered by period k, plus the fixed hour/minute for sub-daily."""
    step = k * rule.get("interval", 1)
    freq = rule["freq"]
    if freq == "YEARLY":
        y = start.year + step
        first = dt.date(y, 1, 1)
        return [
            first + dt.timedelta(days=i)
            for i in range((dt.date(y + 1, 1, 1) - first).days)
        ], None
    if freq == "MONTHLY":
        y, m = month_add(start.year, start.month, step)
        return [
            dt.date(y, m, d) for d in range(1, calendar.monthrange(y, m)[1] + 1)
        ], None
    if freq == "WEEKLY":
        wkst = WEEKDAYS.index(rule.get("wkst", "MO"))
        week = start.date() - dt.timedelta(days=(start.weekday() - wkst) % 7)
        week += dt.timedelta(weeks=step)
        return [week + dt.timedelta(days=i) for i in range(7)], None
    if freq == "DAILY":
        return [start.date() + dt.timedelta(days=step)], None
    base = start.replace(minute=0 if freq == "HOURLY" else start.minute, second=0)
    unit = dt.timedelta(hours=1) if freq == "HOURLY" else dt.timedelta(minutes=1)
    slot = base + step * unit
    return [slot.date()], slot


def day_matches(rule, start, d):
    freq = rule["freq"]
    by_month, by_month_day, by_day = (
        rule.get(k) or [] for k in ("by_month", "by_month_day", "by_day")
    )
    if by_month and d.month not in by_month:
        return False
    if by_month_day:
        last = calendar.monthrange(d.year, d.month)[1]
        if not any(
            n == d.day or (n < 0 and last + 1 + n == d.day) for n in by_month_day
        ):
            return False
    if by_day:
        ok = False
        for entry in by_day:
            if d.weekday() != WEEKDAYS.index(entry["day"]):
                continue
            if "ordinal" not in entry:
                ok = True
                break
            if freq == "MONTHLY" or by_month:
                last = calendar.monthrange(d.year, d.month)[1]
                scope = [dt.date(d.year, d.month, i) for i in range(1, last + 1)]
            else:
                first = dt.date(d.year, 1, 1)
                scope = [
                    first + dt.timedelta(days=i)
                    for i in range((dt.date(d.year + 1, 1, 1) - first).days)
                ]
            same = [x for x in scope if x.weekday() == d.weekday()]
            n = entry["ordinal"]
            index = same.index(d)
            if (n > 0 and index == n - 1) or (n < 0 and index - len(same) == n):
                ok = True
                break
        if not ok:
            return False
    # Values inherited from DTSTART when no BY-part narrows the day.
    if freq == "YEARLY" and not (by_month_day or by_day):
        if not by_month and d.month != start.month:
            return False
        if d.day != start.day:
            return False
    if freq == "MONTHLY" and not (by_month_day or by_day) and d.day != start.day:
        return False
    if freq == "WEEKLY" and not by_day and d.weekday() != start.weekday():
        return False
    return True


def period_candidates(rule, zones, start, k):
    days, slot = period_span(rule, start, k)
    by_hour, by_minute = rule.get("by_hour") or [], rule.get("by_minute") or []
    if slot is None:
        hours, minutes = by_hour or [start.hour], by_minute or [start.minute]
    elif rule["freq"] == "HOURLY":
        hours = [slot.hour] if not by_hour or slot.hour in by_hour else []
        minutes = by_minute or [start.minute]
    else:
        hours = [slot.hour] if not by_hour or slot.hour in by_hour else []
        minutes = [slot.minute] if not by_minute or slot.minute in by_minute else []
    out = sorted(
        dt.datetime(d.year, d.month, d.day, h, m, start.second)
        for d in days
        if day_matches(rule, start, d)
        for h in hours
        for m in minutes
    )
    positions = rule.get("by_set_pos") or []
    if positions:
        # Gap times are removed before selection, so BYSETPOS never picks one.
        # The explicit DTSTART stays as the first period's seed even in a gap.
        out = [x for x in out if x == start or exists(zones, rule["tzid"], x)]
        picked = set()
        for n in positions:
            i = n - 1 if n > 0 else len(out) + n
            if 0 <= i < len(out):
                picked.add(out[i])
        out = sorted(picked)
    return out


def exists(zones, tzid, local):
    return zones.resolve(tzid, local, explicit=False) is not None


def generate(rule, zones, horizon):
    """RRULE instances in generation order, up to a civil-time horizon."""
    start = local_time(rule["dtstart"])
    tzid = rule["tzid"]
    until = utc_instant(rule["until"]) if "until" in rule else None
    count = rule.get("count")
    seed = zones.resolve(tzid, start, explicit=True)
    produced, k = [], 0
    while True:
        cands = period_candidates(rule, zones, start, k)
        days, _ = period_span(rule, start, k)
        if dt.datetime.combine(days[0], dt.time()) > horizon:
            return produced, False
        if (
            until is not None
            and dt.datetime.combine(days[0], dt.time()) > until + MARGIN
        ):
            return produced, True
        for local in cands:
            if local == start:
                instant = seed
            else:
                instant = zones.resolve(tzid, local, explicit=False)
                if instant is None:
                    continue  # DST gap: a non-slot that consumes no COUNT
                if instant <= seed:
                    continue  # DTSTART bounds generation in UTC, not civil order
            if until is not None and instant > until:
                continue
            produced.append(instant)
            if count is not None and len(produced) == count:
                return produced, True
        k += 1
        assert k < 2_000_000, "unbounded expansion"


def occurrence_set(rule, zones, horizon):
    instants, finished = generate(rule, zones, horizon)

    def resolve(value):
        return zones.resolve(rule["tzid"], local_time(value), explicit=True)

    found = set(instants) | {resolve(v) for v in rule.get("rdate", [])}
    found -= {resolve(v) for v in rule.get("exdate", [])}
    return sorted(found), finished


def expand(rule, zones, lo, hi, limit):
    occurrences, _ = occurrence_set(rule, zones, hi + MARGIN)
    return [fmt_utc(x) for x in occurrences if lo <= x < hi][:limit]


def next_after(rule, zones, after):
    """First occurrence strictly after `after`, or None when the set ends."""
    for days in (2, 40, 400, 2000):
        horizon = after + dt.timedelta(days=days)
        occurrences, finished = occurrence_set(rule, zones, horizon)
        # A finished set is complete; otherwise trust only the covered span.
        cutoff = None if finished else horizon - MARGIN
        later = [x for x in occurrences if x > after and (cutoff is None or x < cutoff)]
        if later:
            return fmt_utc(later[0])
        if finished:
            return None
    raise AssertionError(("next_after horizon exhausted", after))


# --- corpus --------------------------------------------------------------------


def evaluate(vector, zones):
    """Return the vector's observable outcome, or {'refusal': reason}."""
    try:
        if "input_text" in vector:
            rule = parse_text(vector["input_text"])
            if not shape(rule):
                raise Refusal("invalid_rule")
        else:
            rule = vector["rule"]
            if not shape(rule):
                raise Refusal("invalid_rule")
        rule = normalize(rule)
        validate(rule, zones)
    except Refusal as e:
        return {"refusal": e.reason}
    # Text round trip is lossless on the subset: model -> text -> model.
    assert normalize(parse_text(serialize(rule))) == normalize(rule), (
        "round trip",
        rule,
    )
    out = {
        "canonical": normalize(rule),
        "digest": digest(rule),
        "text": serialize(rule),
        "queries": [],
        "next_after": [],
    }
    for q in vector.get("queries", []):
        lo, hi, limit = utc_instant(q["from"]), utc_instant(q["to"]), q["limit"]
        # Query arguments are API preconditions, not rule refusals.
        assert type(limit) is int and limit >= 1, ("query limit", q)
        assert lo <= hi, ("reversed query range", q)
        out["queries"].append(expand(rule, zones, lo, hi, limit))
    for q in vector.get("next_after", []):
        after = utc_instant(q["after"])
        out["next_after"].append(next_after(rule, zones, after))
    return out


def expected_of(vector):
    if "reason" in vector:
        return {"refusal": vector["reason"]}
    return {
        "canonical": vector["canonical"],
        "digest": vector["digest"],
        "text": vector["text"],
        "queries": [q["expected"] for q in vector.get("queries", [])],
        "next_after": [q["expected"] for q in vector.get("next_after", [])],
    }


def check_manifest():
    manifest = load(CORPUS / "MANIFEST.json")
    files = sorted(
        p.relative_to(CORPUS).as_posix()
        for p in CORPUS.rglob("*")
        if p.is_file() and p.name != "MANIFEST.json"
    )
    assert sorted(manifest["files"]) == files, ("corpus manifest drift", files)
    for name, pin in manifest["files"].items():
        got = "sha256:" + hashlib.sha256((CORPUS / name).read_bytes()).hexdigest()
        assert got == pin, ("corpus file digest mismatch", name)
    evidence = load(CORPUS / "tzdb-evidence.json")
    assert manifest["tzdb_version"] == evidence["tzdb_version"] == "2026e"
    assert manifest["tzdb_artifact"] == evidence["artifact"]["sha256"]
    corpus_digest = (
        "sha256:" + hashlib.sha256((CORPUS / "MANIFEST.json").read_bytes()).hexdigest()
    )
    readme = (BASE / "README.md").read_text(encoding="utf-8")
    assert corpus_digest in readme, (
        "README does not name corpus digest",
        corpus_digest,
    )
    return corpus_digest, evidence


def reason_table():
    text = STANDARD.read_text(encoding="utf-8").split("## Refusal reasons", 1)[1]
    text = text.split("\n## ", 1)[0]
    return re.findall(r"^\| `([a-z_]+)` +\|", text, re.M)


def run_corpus(zones, quiet=False):
    vectors = sorted((CORPUS / "vectors").glob("*.json"))
    rejects = sorted((CORPUS / "rejects").glob("*.json"))
    assert vectors and rejects, "missing conformance corpus"
    for path in vectors + rejects:
        vector = load(path)
        got = evaluate(vector, zones)
        want = expected_of(vector)
        assert got == want, (path.name, got, want)
        if not quiet:
            print("[ok]", path.relative_to(CORPUS).as_posix())
    return vectors, rejects


def check_rejects(rejects):
    rows = reason_table()
    assert len(rows) == len(set(rows)), "reason_table_drift: duplicate row"
    used = set()
    for path in rejects:
        vector = load(path)
        reason, sep, _ = path.stem.partition("--")
        assert sep and reason == vector["reason"], ("reject name drift", path.name)
        assert ("rule" in vector) != ("input_text" in vector), path.name
        if "rule" in vector:
            # Schema rejects must fail the schema; every other JSON reject passes it.
            assert shape(vector["rule"]) == (reason != "invalid_rule"), path.name
        used.add(reason)
    assert used == set(rows), ("reason_table_drift", set(rows) - used, used - set(rows))


def check_input_edges():
    # Calendar edges refuse by name rather than raising from the date library.
    for text in ("0000-01-01T00:00:00", "2026-02-29T00:00:00", "2026-01-01T24:00:00"):
        try:
            local_time(text)
        except Refusal as e:
            assert e.reason == "invalid_date", text
        else:
            raise AssertionError(("calendar edge accepted", text))
    for text in ("0000-01-01T00:00:00Z", "2026-04-31T00:00:00Z"):
        try:
            civil(UTC.match(text))
        except Refusal as e:
            assert e.reason == "invalid_date", text
        else:
            raise AssertionError(("UNTIL edge accepted", text))


def check_schema_keywords():
    # The pinned validator ignores these 2020-12 keywords, so a rule written
    # with them would pass every reject silently. Use if/then instead.
    text = SCHEMA.read_text(encoding="utf-8")
    for keyword in ("dependentSchemas", "dependentRequired"):
        assert f'"{keyword}"' not in text, (
            "keyword not enforced by validator",
            keyword,
        )


def check_documents():
    # The entry envelope carries the capability; the rule digest never covers it.
    good = load(BASE / "documents/first-thursday-monthly.json")
    assert shape(good, DOCUMENT) and shape(good["rule"])
    assert good["rule"] == load(BASE / "examples/first-thursday-monthly.json")
    assert not shape(load(BASE / "documents/reject-missing-capability.json"), DOCUMENT)
    broken = dict(good, rule=dict(good["rule"], by_set_pos=[1], by_day=[]))
    del broken["rule"]["by_day"]
    assert not shape(broken, DOCUMENT), "envelope does not apply the rule schema"


def check_examples(zones):
    readme = (BASE / "README.md").read_text(encoding="utf-8")
    examples = sorted((BASE / "examples").glob("*.json"))
    assert examples
    for path in examples:
        rule = load(path)
        assert shape(rule), path.name
        validate(rule, zones)
        assert rule == normalize(rule), ("example not in normal form", path.name)
        assert f"`{path.name}` | `{digest(rule)}`" in readme, (
            "README digest drift",
            path.name,
        )
    return examples


# --- mutation controls ---------------------------------------------------------

# Fixed source edits. Each must match exactly once and make its witness disagree
# with the corpus: a reject must become accepted, an accept vector must produce
# a different, still-accepted outcome.
MUTATIONS = [
    (
        "generation gap skips",
        "                if instant is None:\n                    continue  # DST gap",
        "                if instant is None:\n                    instant = zones.resolve(tzid, local, explicit=True)  # DST gap",
        "vectors/dst-gap-count-new-york.json",
    ),
    (
        "gap consumes COUNT",
        "                    continue  # DST gap: a non-slot that consumes no COUNT",
        "                    count = count and count - 1\n                    continue",
        "vectors/dst-gap-count-new-york.json",
    ),
    (
        "overlap takes first",
        "            return min(found)",
        "            return max(found)",
        "vectors/dst-overlap-first-new-york.json",
    ),
    (
        "EXDATE removes RDATE",
        '    found -= {resolve(v) for v in rule.get("exdate", [])}',
        '    found -= {resolve(v) for v in rule.get("exdate", [])} - {resolve(v) for v in rule.get("rdate", [])}',
        "vectors/exdate-over-rdate.json",
    ),
    (
        "UNTIL inclusive",
        "            if until is not None and instant > until:",
        "            if until is not None and instant >= until:",
        "vectors/until-inclusive-vs-half-open.json",
    ),
    (
        "query half-open",
        "if lo <= x < hi][:limit]",
        "if lo <= x <= hi][:limit]",
        "vectors/until-inclusive-vs-half-open.json",
    ),
    (
        "negative month day",
        "(n < 0 and last + 1 + n == d.day)",
        "(n < 0 and last + n == d.day)",
        "vectors/monthly-first-and-last-day.json",
    ),
    (
        "negative set position",
        "            i = n - 1 if n > 0 else len(out) + n",
        "            i = n - 1 if n > 0 else -n - 1",
        "vectors/monthly-first-last-weekday-setpos.json",
    ),
    (
        "month-end skip",
        "and not (by_month_day or by_day) and d.day != start.day:",
        "and not (by_month_day or by_day) and d.day != min(start.day, calendar.monthrange(d.year, d.month)[1]):",
        "vectors/monthly-31st-skips.json",
    ),
    (
        "synchronized DTSTART",
        '    require(start in seeds, "dtstart_not_synchronized")',
        "    pass",
        "rejects/dtstart_not_synchronized--weekly-tuesday-from-monday.json",
    ),
    (
        "tz alias refused",
        '        require(tzid in self.accepted, "invalid_tzid")',
        "        pass",
        "rejects/invalid_tzid--backward-alias.json",
    ),
    (
        "calendar validity",
        '    require(1 <= mo <= 12 and 1 <= d <= calendar.monthrange(y, mo)[1], "invalid_date")',
        '    require(1 <= mo <= 12 and 1 <= d <= 31, "invalid_date"); d = min(d, calendar.monthrange(y, mo)[1])',
        "rejects/invalid_date--february-30.json",
    ),
    (
        "gap removed before BYSETPOS",
        '        out = [x for x in out if x == start or exists(zones, rule["tzid"], x)]',
        "        out = out",
        "vectors/setpos-after-gap-removal-new-york.json",
    ),
    (
        "DTSTART bounds generation in UTC",
        "                if instant <= seed:",
        "                if local < start:",
        "vectors/explicit-gap-dtstart-minutely-new-york.json",
    ),
    (
        "RDATE outside RRULE bounds",
        '    found = set(instants) | {resolve(v) for v in rule.get("rdate", [])}',
        '    found = set(instants) | {resolve(v) for v in rule.get("rdate", []) if not instants or instants[0] <= resolve(v) <= instants[-1]}',
        "vectors/rdate-before-dtstart.json",
    ),
    (
        "list dedup",
        '            value = sorted(set(value))\n        elif key == "by_day":',
        '            value = sorted(value)\n        elif key == "by_day":',
        "vectors/normalization-equivalence.json",
    ),
    (
        "default omission",
        '            ("interval", 1),',
        '            ("interval", 0),',
        "vectors/normalization-equivalence.json",
    ),
    (
        "unsupported part refused",
        '        if name in UNSUPPORTED_PARTS:\n            raise Refusal("unsupported_part")',
        "        if name in UNSUPPORTED_PARTS:\n            continue",
        "rejects/unsupported_part--text-byweekno.json",
    ),
    (
        "wall-clock WEEKLY interval",
        "        week += dt.timedelta(weeks=step)",
        "        week += dt.timedelta(weeks=k)",
        "vectors/weekly-interval-wkst.json",
    ),
    (
        "ordinal scope by month",
        '            if freq == "MONTHLY" or by_month:',
        '            if freq == "MONTHLY":',
        "vectors/yearly-bymonth-ordinal.json",
    ),
]


def mutation_controls(zones):
    source = (
        pathlib.Path(__file__)
        .read_text(encoding="utf-8")
        .split("# --- mutation controls", 1)[0]
    )
    for label, old, new, witness in MUTATIONS:
        assert source.count(old) == 1, ("mutation does not match exactly once", label)
        ns = {"__file__": __file__, "__name__": "recurrence_mutation"}
        exec(compile(source.replace(old, new), __file__, "exec"), ns)
        vector = load(CORPUS / witness)
        mutant_zones = ns["Zones"](load(CORPUS / "tzdb-evidence.json"))
        try:
            got = ns["evaluate"](vector, mutant_zones)
        except Exception as e:  # noqa: BLE001 - a crash is not a detection
            raise AssertionError(("mutation crashed instead of disagreeing", label, e))
        want = expected_of(vector)
        assert got != want, ("mutation ineffective", label, witness)
        assert "refusal" not in got, ("mutation still refused", label, got)
        print("[ok] mutation:", label, "->", witness)
    return len(MUTATIONS)


def main():
    check_schema_keywords()
    check_input_edges()
    corpus_digest, evidence = check_manifest()
    zones = Zones(evidence)
    examples = check_examples(zones)
    check_documents()
    vectors, rejects = run_corpus(zones)
    check_rejects(rejects)
    count = mutation_controls(zones)
    print(
        f"Recurrence controls PASS: {len(examples)} examples; {len(vectors)} vectors; "
        f"{len(rejects)} rejects; {count} mutation witnesses; corpus {corpus_digest}; "
        f"tzdb {zones.version}."
    )


if __name__ == "__main__":
    sys.exit(main())
