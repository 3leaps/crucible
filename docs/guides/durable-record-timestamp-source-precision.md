# Adopter Guide: Timestamp Source Precision with `durable-record/v1`

**Status:** Non-normative adopter guide.

This guide gives practical recipes for recording upstream timestamp precision
when writing [`durable-record/v1`](../../schemas/durable-record/v1/README.md)
records. It introduces **no** new standard envelope field, **no** accepted
`durable-record/v1` wire spelling, and **no** change to
`schemas/durable-record/v1/` or its validators.

## Why This Matters

`durable-record/v1` requires `produced_at.instant` to carry six fractional
digits in UTC (`YYYY-MM-DDTHH:MM:SS.ffffffZ`). Upstream producers frequently
supply timestamps at a different resolution:

- **Coarser sources** (whole seconds or milliseconds) must be zero-padded to
  microseconds to satisfy the envelope format, making `.000000Z` or `.123000Z`
  indistinguishable from a genuine microsecond reading.
- **Finer sources** (nanoseconds) must discard the sub-microsecond remainder
  (never round) when populating `produced_at.instant`.

Adding an extra field directly inside `produced_at` is **invalid**: the
`durable-record/v1` envelope schema sets `additionalProperties: false`, so
unknown envelope fields fail closed validation. Instead, adopters that need to
preserve source resolution or discarded remainders carry that metadata inside
their **own versioned payload** (or an explicit companion record).

## Recipe 1: Coarser Source (Seconds or Milliseconds)

Populate `produced_at.instant` by zero-padding to six fractional digits, and
declare the source resolution and conversion rule inside your own versioned
payload contract. The field names below are illustrative only; each adopter
owns its payload schema. The JSON blocks below are **record excerpts** (omitting
required `durable-record/v1` envelope fields such as `v`, `stream`, `record_id`,
`revision`, `provenance`, and `classification` for brevity) and are not
standalone complete envelopes.

`declared_precision` is a declaration from a known source or clock profile:
three or six fractional digits in an input string establish only the supplied
spelling, not physical clock resolution. When device resolution is unknown,
retain the raw input or supplied granularity and leave physical resolution
unknown rather than asserting a device precision you did not observe.

### Whole-second source (record excerpt)

```json
{
  "produced_at": {
    "instant": "2026-11-23T14:30:00.000000Z",
    "source": "producer_clock"
  },
  "payload_contract": "contract: example-adopter/v0",
  "payload": {
    "event_id": "evt-001",
    "source_timestamp": {
      "raw": "2026-11-23T14:30:00Z",
      "declared_precision": "second",
      "envelope_conversion": "zero_pad_to_microsecond"
    }
  }
}
```

### Millisecond source (record excerpt)

```json
{
  "produced_at": {
    "instant": "2026-11-23T14:30:00.123000Z",
    "source": "producer_clock"
  },
  "payload_contract": "contract: example-adopter/v0",
  "payload": {
    "event_id": "evt-002",
    "source_timestamp": {
      "raw": "2026-11-23T14:30:00.123Z",
      "declared_precision": "millisecond",
      "envelope_conversion": "zero_pad_to_microsecond"
    }
  }
}
```

Downstream readers checking `payload.source_timestamp` can distinguish a
zero-padded second or millisecond reading from a native microsecond reading
without modifying the `durable-record/v1` envelope.

## Recipe 2: Finer Source with a Discarded Remainder (Nanoseconds)

A producer may refuse sub-microsecond input outright; a conforming
`durable-record/v1` store refuses an instant that is not exactly representable
at microseconds and never rounds or truncates it. When an adopter chooses
explicit conversion instead, that conversion happens in adopter code **before**
invoking any strict microsecond envelope helper (which does not round). A zero
sub-microsecond remainder (for example `.123456000Z`) loses no value.

When an upstream clock reports a nonzero sub-microsecond remainder (for example
`2026-11-23T14:30:00.123456789Z`), truncate (floor) to microseconds for
`produced_at.instant` and record the original reading, conversion rule, and
discarded remainder in your versioned payload (record excerpt):

```json
{
  "produced_at": {
    "instant": "2026-11-23T14:30:00.123456Z",
    "source": "producer_clock"
  },
  "payload_contract": "contract: example-adopter/v0",
  "payload": {
    "event_id": "evt-003",
    "source_timestamp": {
      "raw": "2026-11-23T14:30:00.123456789Z",
      "declared_precision": "nanosecond",
      "envelope_conversion": "truncate_floor_to_microsecond",
      "discarded_remainder_ns": 789
    }
  }
}
```

Recording the raw value, conversion rule, and discarded remainder keeps the
envelope compliant while preserving auditability when two events differ only in
their sub-microsecond digits.

## Practical Guidance

- **Do not use `produced_at.instant` as a total order.** Coarser zero-padded
  sources and truncated nanosecond sources regularly produce ties. When order
  matters, rely on explicit ordered structures (such as a
  [`record-collection/v0`](../../schemas/record-collection/v0/README.md) `list`)
  or store journal sequence rather than sorting by `produced_at.instant`.
- **Keep conversion rules deterministic.** Choose one conversion rule per
  payload version (for example, floor truncation rather than half-even
  rounding) so writers do not disagree on the microsecond value for the same
  input.
- **Optional store clock profiles.** A store may separately document its
  effective clock resolution and conversion policy per epoch in an external
  store profile, but that profile requires its own explicit binding and does
  not change the closed `durable-record/v1` envelope.
