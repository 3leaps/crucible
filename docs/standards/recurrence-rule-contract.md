# Recurrence Rule Contract

**Status: proposed.** Capability: `contract: recurrence/v0`. Schemas:
[`schemas/recurrence/v0`](../../schemas/recurrence/v0/).

## Purpose

This contract defines a canonical JSON form for a frozen subset of the RFC 5545 recurrence rule
(RRULE), the semantics for expanding it into UTC instants, and one pinned conformance corpus.
Conforming implementations must agree on expansion and canonical identity. The corpus checks
specified behaviors; passing it is not a proof of equivalence for every possible input.

The key words MUST, MUST NOT, SHOULD and MAY are used as in RFC 2119.

## Scope

In scope: one recurrence rule with `RDATE` and `EXDATE`, its JSON and RFC 5545 text forms,
normalization and digest, expansion over a bounded range, and conformance claims.

Out of scope for v0: `SECONDLY`, `BYSECOND`, `BYWEEKNO`, `BYYEARDAY`, multiple `RRULE` lines,
`EXRULE`, iCalendar components (`VEVENT`, `VTODO`), DST shift-forward policies, and non-Gregorian
calendars. A rule that uses any of these MUST be refused; it MUST NOT be accepted with the part
ignored.

## Schemas

`recurrence-rule.schema.json` is the rule itself. Contracts that carry a schedule embed it by
reference, and the rule's normalization and digest cover only that object.
`rule-document.schema.json` is the family entry: an envelope with a `capabilities` list containing
`contract: recurrence/v0` and one `rule`, for exchanging a rule on its own. The envelope never
contributes to the rule's digest.

## A1. Supported subset

| Part                 | v0 support                                                   |
| -------------------- | ------------------------------------------------------------ |
| `FREQ`               | `MINUTELY`, `HOURLY`, `DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY` |
| `INTERVAL`           | Integer >= 1, default 1                                      |
| `COUNT` / `UNTIL`    | At most one                                                  |
| `BYDAY`              | Weekdays; ordinals only with `MONTHLY` or `YEARLY`           |
| `BYMONTHDAY`         | +/-1..31; not with `WEEKLY`                                  |
| `BYMONTH`            | 1..12                                                        |
| `BYHOUR`, `BYMINUTE` | 0..23, 0..59                                                 |
| `BYSETPOS`           | +/-1..366; requires another BY-part                          |
| `WKST`               | Weekday, default `MO`                                        |
| `DTSTART`            | Local civil date-time with an IANA `TZID`                    |
| `RDATE`, `EXDATE`    | Local civil date-times in the rule's `TZID`                  |

The calendar is Gregorian. A rule without `calendar`, or with `gregorian`, is Gregorian. Any other
calendar needs a new `calendar` value with its own standard; the meaning of existing JSON never
changes.

## A2. Fields and wire types

| Field                                                            | Type                                                                  |
| ---------------------------------------------------------------- | --------------------------------------------------------------------- |
| `dtstart`                                                        | Local civil date-time `YYYY-MM-DDTHH:MM:SS`, whole seconds, no offset |
| `tzid`                                                           | IANA time-zone name (see [Time-zone names](#time-zone-names))         |
| `freq`                                                           | Enumeration above                                                     |
| `interval`, `count`                                              | Integer >= 1                                                          |
| `until`                                                          | UTC instant `YYYY-MM-DDTHH:MM:SSZ`, whole seconds, inclusive          |
| `wkst`                                                           | `MO` .. `SU`                                                          |
| `by_day`                                                         | Objects `{"day": "TH"}` or `{"day": "TH", "ordinal": -1}`             |
| `by_month`, `by_month_day`, `by_hour`, `by_minute`, `by_set_pos` | Integer lists                                                         |
| `rdate`, `exdate`                                                | Local civil date-time lists, same format as `dtstart`                 |
| `calendar`                                                       | `gregorian` only                                                      |

`dtstart` is not an RFC 3339 instant, and no field reuses a `Z`-only instant type for civil time.
Inputs are whole seconds, so the text round trip is lossless. Expansion output is RFC 3339 UTC `Z`
instants. A runner MAY carry them at its own finer precision; v0 occurrences always have zero
fractional seconds. Calendar dates use years 0001 through 9999; hour, minute, and second values are
00..23, 00..59, and 00..59. Leap-second labels are outside this profile. Every explicit date-time,
including `until`, must name a valid Gregorian date.

## A3. Expansion semantics

This family defines one Gregorian recurrence rule and its explicit inclusion and exclusion dates.
Calendar fields are interpreted in the rule's named timezone using the declared tzdb release.
Implementations MUST NOT substitute host timezone data. RFC 5545
[section 3.3.10](https://www.rfc-editor.org/rfc/rfc5545.html#section-3.3.10) supplies the
recurrence-part semantics, subject to this family's frozen subset and the explicit rules below. The
corrected yearly BYDAY interpretation in
[verified erratum 3779](https://www.rfc-editor.org/errata/eid3779) applies.

### Civil periods and candidate selection

An interval advances local civil periods: minutes, hours, days, weeks, months, or years according to
`freq`. It does not add a fixed UTC duration to the preceding occurrence. Weeks begin on `wkst`; the
week containing `dtstart` is the first weekly period. Monthly periods are complete calendar months
and yearly periods are complete calendar years. An implementation MUST preserve the period anchored
by `dtstart` when a query begins later.

The supported BY-parts are evaluated in this order: month, month-day, weekday, hour, minute,
set-position. Different BY-parts constrain one another; entries within one list are alternatives.
Missing calendar components come from `dtstart` where the recurrence expansion rules require them.
The second component always comes from `dtstart`, because BYSECOND is outside this family.
Implementations MUST NOT treat an omitted BY-part as an explicit list of every possible value:
omission can inherit a component that an explicit list would expand.

Ordinal weekdays are valid only for monthly and yearly rules. A monthly ordinal is relative to that
month. A yearly ordinal is relative to each selected month when `by_month` is nonempty, and to the
year otherwise. A weekly rule MUST NOT contain a nonempty `by_month_day`. An ordinal has no zero
value. Unsupported combinations are errors, not ignored filters.

Generated invalid calendar dates are discarded. The candidate set for each selected period contains
unique valid local date-times, ordered chronologically. Generated times in a timezone gap are
discarded before set-position selection. An ambiguous candidate maps to its first occurrence only. A
positive set-position selects from the beginning of this period's candidate set and a negative
position selects from its end. Positions outside the candidate set select nothing. Position
selection operates on the complete period before the query range is applied; shortening the query
MUST NOT change which positions are selected. A nonempty `by_set_pos` requires another nonempty
BY-part.

`dtstart` MUST be synchronized with the rule's local recurrence pattern, including its position in
the first complete period when `by_set_pos` is present. Unsynchronized rules are refused rather than
adopting the undefined behavior described in RFC 5545 section 3.8.5.3. An explicit gap-valued start
needs the first-period treatment stated below; it is not rewritten to a different wall-clock anchor.

### Timezone gaps, overlaps, and explicit dates

Generated recurrence instances use RFC 5545 section 3.3.10: a local time that does not exist is
skipped and consumes no `count`. Invalid month-days likewise do not consume count. A daily 02:30
rule remains a 02:30 rule after a spring-forward gap.

Explicit `dtstart`, `rdate`, and `exdate` values use the zoned DATE-TIME interpretation in
[section 3.3.5](https://www.rfc-editor.org/rfc/rfc5545.html#section-3.3.5): a gap value uses the
offset before the gap, and an overlap value selects the earlier instant. This distinction applies to
explicit dates even when the same local label would be discarded as a generated candidate. There is
no configurable shift policy in this family.

For a gap-valued `dtstart`, retain its explicit local value as the first-period seed for pattern and
position validation. Resolve it using the pre-gap offset. Generated RRULE candidates mapping before
the resolved start are ineligible, and a candidate equal to the seed instant is not counted twice.
For example, a minutely rule starting at `2026-03-08T02:59:00` in `America/New_York` with count two
produces `2026-03-08T07:59:00Z` and `2026-03-08T08:00:00Z`. This explicit-start boundary is part of
this profile; it MUST NOT be inferred from civil ordering alone.

Explicit invalid calendar dates are errors; the skip rule applies to generated dates only. Timezone
conversion and exclusion compare resolved instants, not spellings of local labels. This matters when
an explicit gap label and an ordinary local label resolve to the same instant.

### Rule bounds, inclusion, and exclusion

`count` bounds unique RRULE occurrences from the start, before query filtering and before
exclusions. The start consumes the first count. Excluding an occurrence does not replace it with a
later one. `until` is an inclusive UTC bound on the RRULE. Count and until cannot both be present.
Generated gaps and invalid calendar dates consume neither a count nor an occurrence.

The recurrence set is the union of the bounded RRULE occurrences and resolved `rdate` values, with
resolved `exdate` values removed afterward. Equal instants appear once. Exclusion wins regardless of
whether the same instant came from the rule, an explicit inclusion, or both. The RRULE's count and
until do not bound explicit inclusion dates.

An `rdate` may explicitly include an instant before `dtstart`: the start bounds RRULE generation,
not the explicit union. If `until` precedes the resolved start, the RRULE contributes no
occurrences; explicit inclusions and exclusions still apply. This is an empty rule expansion, not an
invalid calendar input.

Querying applies a half-open UTC interval `[from, to)` to the final set. An occurrence at `from` is
included; one at `to` is excluded, even if it equals the inclusive RRULE `until`. Equal query bounds
produce an empty result. Reversed bounds are invalid. Results are unique and strictly increasing UTC
instants; a positive integer result limit is required and selects the earliest matching instants.
`next_after` is strictly after its argument. Implementations MUST distinguish a resource-limit
failure from proof that no further occurrence exists.

## A4. Conformance corpus and tzdb identity

The corpus lives in [`schemas/recurrence/v0/corpus`](../../schemas/recurrence/v0/corpus/).
`MANIFEST.json` pins every corpus file by SHA-256, and the corpus digest is the SHA-256 of
`MANIFEST.json`, recorded in the family README.

- **tzdb identity.** The expected values were derived with IANA tzdb **2026e**. The manifest names
  the release and the SHA-256 of its upstream artifact `tzdata2026e.tar.gz`. `tzdb-evidence.json`
  records, for each zone the vectors use, the UTC offset transitions within the evidence window and
  the source lines in the release that produce them. Host time-zone installations are not evidence.
  The recorded window bounds verification evidence, not the dates supported by a production
  implementation. Verification MUST cover the history from `dtstart`, explicit inclusion/exclusion
  values, and complete selected periods needed for BYSETPOS. It MUST fail if required timezone
  evidence lies outside the window; it MUST NOT extrapolate the last offset or substitute host data.
  A search horizon or resource cap is not proof that no later occurrence exists.
- **Hand-derived expectations.** Expected values were derived by hand from the rules above and the
  recorded transitions. No implementation is the oracle. The repository's control script re-derives
  them independently and fails on any disagreement; it never writes expected values.
- **Claim.** An implementation claims conformance per pair `(corpus digest, tzdb version)`. It MUST
  report the tzdb version it expands with and MUST pass every accept and reject vector for that
  pair. A tzdb update is a new pair with refreshed vectors.

Each accept vector carries an input (`rule` as JSON, or `input_text` as RFC 5545 lines) and the
expected canonical JSON, digest, text form, query results and `next_after` results. Each reject
vector carries an input and the refusal reason that its file name also states.

## A5. Normalization and digest

The accepted model and its canonical representation have different roles. Accepted input may contain
unsorted lists, duplicate list entries, explicit defaults, and empty lists. Normalization produces
one representation for these syntactic variations. Invalid values and unsupported fields are refused
before they can be removed as defaults; normalization MUST NOT silently repair an invalid rule.

Normalization performs these operations:

1. Sort each numeric BY-list in ascending numeric order and remove duplicate values.
2. Sort `by_day` by weekday in the order MO, TU, WE, TH, FR, SA, SU. Within one weekday put an
   unqualified entry first, followed by entries with explicit ordinals in ascending numeric order.
   Remove only identical weekday/ordinal pairs. An absent ordinal is not ordinal zero.
3. Sort `rdate` and `exdate` separately by their fixed-format local date-time strings and remove
   duplicates within each list. Preserve the two lists independently; an inclusion that is also
   excluded is not removed from the normalized model.
4. Omit empty lists and the defaults `interval: 1`, `wkst: "MO"`, and `calendar: "gregorian"`.
   Effective dependency checks require a nonempty companion BY-part when set-position is nonempty.
5. Preserve the remaining valid values exactly. Do not remove redundant predicates or rewrite
   explicit local dates to resolved UTC instants as a digest optimization.

Weekdays and frequency values use the schema's uppercase vocabulary. BYDAY uses objects with a
required `day` and an optional nonzero integer `ordinal`. Textual positive ordinals may include a
plus sign when parsed; JSON canonicalization represents the resulting integer, without preserving
that spelling.

### Time-zone names

Timezone names are exact, case-sensitive identities. The accepted roster is the union of `Zone`
names in the pinned upstream release's `africa`, `antarctica`, `asia`, `australasia`, `europe`,
`northamerica`, `southamerica`, and `etcetera` source files, plus the location names in that
release's `zone.tab`. The profile does not add names found only in `backward`, `backzone`, or
`factory`.

Names are preserved, never mapped to a Link target for normalization. `Europe/Oslo` is a location in
`zone.tab` and remains a distinct rule identity from `Europe/Berlin`, even when the pinned tzdb
implements it as a Link. Other Link-only aliases, including `US/Eastern`, `Asia/Calcutta`, and
`UTC`, are refused with `invalid_tzid`. Use `Etc/UTC` for UTC. A runtime's alias resolution behavior
MUST NOT determine roster membership. The pinned 2026e corpus records all 446 names in this source
profile.

### Canonical bytes and text

Serialize the normalized model as UTF-8 using
[JSON Canonicalization Scheme, RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html). The digest is
`sha256:` followed by the lowercase hexadecimal SHA-256 of those bytes, with no BOM or appended line
terminator. This is a digest of the normalized model, not of the original JSON text or RFC text. A
conforming decoder MUST reject duplicate JSON member names before object construction can discard
them.

The model digest does not replace timezone provenance. Expansion and conformance claims identify the
model digest together with the declared tzdb version and corpus identity. A different timezone
release may produce different occurrences from the same normalized model.

Text round-tripping preserves the normalized model's meaning, not original whitespace, property
ordering, duplicates, or explicit default spellings. Canonical text writes `DTSTART`, then `RRULE`,
then nonempty `RDATE` and `EXDATE`. RRULE parts have this order: `FREQ`, `INTERVAL`, `COUNT` or
`UNTIL`, `BYMONTH`, `BYMONTHDAY`, `BYDAY`, `BYHOUR`, `BYMINUTE`, `BYSETPOS`, `WKST`. List entries
use normalized order, and positive ordinal text omits the plus sign. Parsers refuse unsupported
recurrence parts and repeated singleton rule parts. Serialization MUST use the family's supported
local-time/TZID forms and UTC UNTIL form; it MUST NOT introduce unsupported properties as a
convenience.

## A6. Schema checks and semantic checks

The JSON Schema enforces:

- the field set, with no additional properties;
- `count` and `until` mutually exclusive;
- nonempty `by_set_pos` only with another nonempty BY-part;
- numeric bounds: `by_month` 1..12, `by_month_day` +/-1..31 non-zero, `by_hour` 0..23, `by_minute`
  0..59, `by_set_pos` +/-1..366 non-zero, `interval` and `count` >= 1, `ordinal` +/-1..53 non-zero;
- `by_day` ordinals only with `MONTHLY` or `YEARLY`, and no nonempty `by_month_day` with `WEEKLY`;
- the frozen enumerations and the civil and UTC date-time formats.

Semantic checks, required of every implementation after schema acceptance:

- `tzid` is in the accepted set of the pinned tzdb;
- `dtstart`, `rdate`, `exdate`, and `until` are valid Gregorian date-times;
- the normalized rule synchronizes `dtstart` with its first-period local pattern, using the
  explicit-gap seed rule and independently of `until`.

## Refusal reasons

| Reason                     | Meaning                                                                                            |
| -------------------------- | -------------------------------------------------------------------------------------------------- |
| `invalid_rule`             | The JSON model fails the schema                                                                    |
| `invalid_text`             | RFC 5545 text is malformed or uses a non-local `DTSTART` form                                      |
| `unsupported_part`         | Text uses a part or property outside the frozen subset                                             |
| `invalid_tzid`             | The `tzid` is not an accepted name in the pinned tzdb                                              |
| `invalid_date`             | A civil date-time names a date or time that does not exist in the calendar                         |
| `dtstart_not_synchronized` | `dtstart` does not match the normalized first-period pattern, including the explicit-gap seed rule |

## Promotion

`recurrence/v0` stays proposed until two independent implementations pass the corpus for the same
`(corpus digest, tzdb version)` pair and a promotion decision is recorded.
