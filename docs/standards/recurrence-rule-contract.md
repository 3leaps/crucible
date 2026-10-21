# Recurrence Rule Contract

**Status: proposed.** Capability: `contract: recurrence/v0`.
Schemas: [`schemas/recurrence/v0`](../../schemas/recurrence/v0/).

## Purpose

This contract defines a canonical JSON form for a frozen subset of the RFC 5545
recurrence rule (RRULE), the semantics for expanding it into UTC instants, and
one pinned conformance corpus. Implementations in different languages that
pass the corpus expand the same rule to the same instants. They also compute
the same canonical digest, so identifiers derived from an occurrence and its
rule agree.

The key words MUST, MUST NOT, SHOULD and MAY are used as in RFC 2119.

## Scope

In scope: one recurrence rule with `RDATE` and `EXDATE`, its JSON and RFC 5545
text forms, normalization and digest, expansion over a bounded range, and
conformance claims.

Out of scope for v0: `SECONDLY`, `BYSECOND`, `BYWEEKNO`, `BYYEARDAY`, multiple
`RRULE` lines, `EXRULE`, iCalendar components (`VEVENT`, `VTODO`), DST
shift-forward policies, and non-Gregorian calendars. A rule that uses any of
these MUST be refused; it MUST NOT be accepted with the part ignored.

## Schemas

`recurrence-rule.schema.json` is the rule itself. Contracts that carry a
schedule embed it by reference, and the rule's normalization and digest cover
only that object. `rule-document.schema.json` is the family entry: an envelope
with a `capabilities` list containing `contract: recurrence/v0` and one `rule`,
for exchanging a rule on its own. The envelope never contributes to the rule's
digest.

## A1. Supported subset

| Part | v0 support |
| --- | --- |
| `FREQ` | `MINUTELY`, `HOURLY`, `DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY` |
| `INTERVAL` | Integer >= 1, default 1 |
| `COUNT` / `UNTIL` | At most one |
| `BYDAY` | Weekdays; ordinals only with `MONTHLY` or `YEARLY` |
| `BYMONTHDAY` | +/-1..31; not with `WEEKLY` |
| `BYMONTH` | 1..12 |
| `BYHOUR`, `BYMINUTE` | 0..23, 0..59 |
| `BYSETPOS` | +/-1..366; requires another BY-part |
| `WKST` | Weekday, default `MO` |
| `DTSTART` | Local civil date-time with an IANA `TZID` |
| `RDATE`, `EXDATE` | Local civil date-times in the rule's `TZID` |

The calendar is Gregorian. A rule without `calendar`, or with `gregorian`, is
Gregorian. Any other calendar needs a new `calendar` value with its own
standard; the meaning of existing JSON never changes.

## A2. Fields and wire types

| Field | Type |
| --- | --- |
| `dtstart` | Local civil date-time `YYYY-MM-DDTHH:MM:SS`, whole seconds, no offset |
| `tzid` | IANA time-zone name (see [Time-zone names](#time-zone-names)) |
| `freq` | Enumeration above |
| `interval`, `count` | Integer >= 1 |
| `until` | UTC instant `YYYY-MM-DDTHH:MM:SSZ`, whole seconds, inclusive |
| `wkst` | `MO` .. `SU` |
| `by_day` | Objects `{"day": "TH"}` or `{"day": "TH", "ordinal": -1}` |
| `by_month`, `by_month_day`, `by_hour`, `by_minute`, `by_set_pos` | Integer lists |
| `rdate`, `exdate` | Local civil date-time lists, same format as `dtstart` |
| `calendar` | `gregorian` only |

`dtstart` is not an RFC 3339 instant, and no field reuses a `Z`-only instant
type for civil time. Inputs are whole seconds, so the text round trip is
lossless. Expansion output is RFC 3339 UTC `Z` instants. A runner MAY carry them
at its own finer precision; v0 occurrences always have zero fractional seconds.

## A3. Expansion semantics

### Generation

Expansion follows RFC 5545 section 3.3.10, with verified errata 3747 and 3779. A rule is evaluated in **local civil
time** in its `tzid`. Each `FREQ` and `INTERVAL` step advances the civil
calendar or clock. `HOURLY` and `MINUTELY` steps count wall-clock hours and
minutes, not elapsed time. Within each period:

1. BY-parts that are expanded for the frequency (RFC 5545 section 3.3.10 table)
   produce candidate civil date-times. BY-parts that limit the frequency filter
   them. When no BY-part sets the day, month, hour or minute, it is taken from
   `dtstart`.
2. A `BYDAY` ordinal counts within the month when `FREQ=MONTHLY` or when
   `BYMONTH` is present, and otherwise within the year.
3. `BYSETPOS` selects from the period's ordered candidate set, counting from
   the start (positive) or the end (negative). Candidates whose local time
   does not exist (see the gap rule below) are removed before selection, so a
   position never selects a skipped time. Selection uses the complete period;
   a query range never changes which positions are selected.
4. Candidates that are not valid Gregorian dates, such as the 31st of a 30-day
   month or February 29 in a common year, do not exist. They are skipped and
   never clamped to a nearby date.
5. The explicit `dtstart` is the first instance. Generated candidates whose
   UTC instant is at or before the resolved `dtstart` are discarded. The bound
   is in UTC, not civil order. For example, a `MINUTELY` rule from a gap
   `dtstart` of `2026-03-08T02:59:00` in `America/New_York` resolves to
   `07:59Z`, so the generated `03:00`..`03:59` EDT candidates are discarded
   and the next instance is `08:00Z`.

`dtstart` MUST be an instance the rule itself generates (the first instance).
A rule whose `dtstart` does not match its own BY-parts is refused with
`dtstart_not_synchronized`. RFC 5545 leaves that case undefined, so v0 refuses
it rather than choosing a reading.

### Time-zone mapping

Each civil candidate maps to UTC through the pinned tzdb:

- **Gap, generated instance.** A generated candidate whose local time does not
  exist (spring-forward gap) is skipped. It does not count toward `COUNT`, and
  it is not an occurrence. Consumers that assign identifiers or "missed"
  states to occurrences MUST NOT assign them to a skipped candidate. A daily
  02:30 `America/New_York` rule has no occurrence on the spring-forward day; it
  does not move to 03:30.
- **Gap, explicit time.** An explicitly supplied local time that falls in a gap
  (`dtstart`, `rdate` or `exdate`) is interpreted with the offset in effect
  before the gap (RFC 5545 section 3.3.5).
- **Overlap.** A local time that occurs twice (fall-back) resolves to the
  earlier UTC instant only, for generated and explicit times alike. It never
  yields both.

No shift-forward policy exists in v0. If one is ever added, it is a separately
named field that is part of the rule's identity and digest.

### Bounds and the occurrence set

- `COUNT` counts generated instances that survive the time-zone mapping, in
  order. An instance later removed by `exdate` still counts.
- `UNTIL` is inclusive. A generated instance whose UTC instant equals `until`
  is an occurrence. If `until` is earlier than the resolved `dtstart`, the
  rule generates nothing; this is an empty expansion, not an error.
- `dtstart`, `COUNT` and `UNTIL` bound the generated instances only. `rdate`
  values are added regardless of them and MAY precede `dtstart`.
- The occurrence set is the union of generated instances and `rdate` instances,
  minus every instance that equals an `exdate` instance. Comparison is by
  resolved UTC instant. `exdate` therefore removes `rdate` instances as well as
  generated ones, and duplicates collapse.

### Queries

- `expand(rule, [from, to), limit)` returns the occurrences `x` with
  `from <= x < to` in ascending order, at most `limit` of them. The range is
  half-open, so an occurrence exactly at `to` is excluded even when it equals
  an inclusive `until`. Equal bounds return nothing. A limit is required.
- `next_after(rule, t)` returns the first occurrence strictly after `t`, or none
  when the set has no later occurrence.

## A4. Conformance corpus and tzdb identity

The corpus lives in [`schemas/recurrence/v0/corpus`](../../schemas/recurrence/v0/corpus/).
`MANIFEST.json` pins every corpus file by SHA-256, and the corpus digest is the
SHA-256 of `MANIFEST.json`, recorded in the family README.

- **tzdb identity.** The expected values were derived with IANA tzdb **2026e**.
  The manifest names the release and the SHA-256 of its upstream artifact
  `tzdata2026e.tar.gz`. `tzdb-evidence.json` records, for each zone the vectors
  use, the UTC offset transitions within the evidence window and the source
  lines in the release that produce them. Host time-zone installations are not
  evidence.
- **Hand-derived expectations.** Expected values were derived by hand from the
  rules above and the recorded transitions. No implementation is the oracle.
  The repository's control script re-derives them independently and fails on
  any disagreement; it never writes expected values.
- **Claim.** An implementation claims conformance per pair
  `(corpus digest, tzdb version)`. It MUST report the tzdb version it expands
  with and MUST pass every accept and reject vector for that pair. A tzdb
  update is a new pair with refreshed vectors.

Each accept vector carries an input (`rule` as JSON, or `input_text` as RFC
5545 lines) and the expected canonical JSON, digest, text form, query results
and `next_after` results. Each reject vector carries an input and the refusal
reason that its file name also states.

## A5. Normalization and digest

The canonical form is produced in two steps: normalize the model, then
serialize with JCS (RFC 8785). The digest is `sha256:` followed by the
lowercase hex SHA-256 of the JCS bytes.

Normalization:

- Integer lists (`by_month`, `by_month_day`, `by_hour`, `by_minute`,
  `by_set_pos`) are sorted ascending and deduplicated.
- `by_day` is deduplicated and ordered by weekday from `MO` to `SU`; a plain
  weekday precedes ordinal entries for that weekday, which are ordered by
  ordinal ascending.
- `rdate` and `exdate` are sorted ascending and deduplicated.
- Defaults are omitted: `interval: 1`, `wkst: "MO"`, `calendar: "gregorian"`.
- Empty lists are omitted. An empty list and an absent list are the same rule.
- An ordinal is a signed integer in the `ordinal` member, never zero. The text
  form writes it without a `+` sign (`1MO`, `-1FR`).
- `tzid` is kept exactly as written (see below).

Two accepted rules that normalize to the same JSON are the same rule and share
one digest. The RFC 5545 text form is derived from the normalized model with
parts in a fixed order: `FREQ`, `INTERVAL`, `COUNT` or `UNTIL`, `BYMONTH`,
`BYMONTHDAY`, `BYDAY`, `BYHOUR`, `BYMINUTE`, `BYSETPOS`, `WKST`. Text, then
model, then canonical JSON, then model, then text is lossless on the subset.

### Time-zone names

The accepted `tzid` set is every `Zone` name in the pinned tzdb plus every
location name in its `zone.tab`. Matching is exact and case-sensitive. Names
are not mapped to a link target: `Europe/Oslo` and `Europe/Berlin` are
different rules with different digests, even when a tzdb release implements
one as a link to the other. Backward-compatibility aliases that are neither
(`US/Eastern`, `Asia/Calcutta`, `UTC`) are refused with `invalid_tzid`; UTC is
written `Etc/UTC`.

## A6. Schema checks and semantic checks

The JSON Schema enforces:

- the field set, with no additional properties;
- `count` and `until` mutually exclusive;
- `by_set_pos` only with another BY-part;
- numeric bounds: `by_month` 1..12, `by_month_day` +/-1..31 non-zero, `by_hour`
  0..23, `by_minute` 0..59, `by_set_pos` +/-1..366 non-zero, `interval` and
  `count` >= 1, `ordinal` +/-1..53 non-zero (+/-1..5 when counted within a
  month);
- `by_day` ordinals only with `MONTHLY` or `YEARLY`, and no `by_month_day` with
  `WEEKLY`;
- the frozen enumerations and the civil and UTC date-time formats.

The schema is written with `if`/`then` rather than `dependentSchemas`, because
the validator the repository pins does not enforce `dependentSchemas` or
`dependentRequired`. The controls refuse a schema that uses them.

Semantic checks, required of every implementation after schema acceptance:

- `tzid` is in the accepted set of the pinned tzdb;
- `dtstart`, `rdate` and `exdate` are valid Gregorian date-times;
- `dtstart` is generated by the rule.

## Refusal reasons

| Reason | Meaning |
| --- | --- |
| `invalid_rule` | The JSON model fails the schema |
| `invalid_text` | RFC 5545 text is malformed or uses a non-local `DTSTART` form |
| `unsupported_part` | Text uses a part or property outside the frozen subset |
| `invalid_tzid` | The `tzid` is not an accepted name in the pinned tzdb |
| `invalid_date` | A civil date-time names a date or time that does not exist in the calendar |
| `dtstart_not_synchronized` | `dtstart` is not an instance the rule generates |

## Promotion

`recurrence/v0` stays proposed until two independent implementations pass the
corpus for the same `(corpus digest, tzdb version)` pair and a promotion
decision is recorded.
