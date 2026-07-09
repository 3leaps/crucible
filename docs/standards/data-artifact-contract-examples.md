---
title: "Portable Data Artifact Contract Examples"
description: "Source-neutral stress cases and adoption preview template for the portable data artifact contract"
category: "standards"
status: "draft"
version: "0.0.0"
lastUpdated: "2026-07-09"
maintainer: "core-standards"
reviewers: ["architecture", "security", "data-engineering"]
approvers: ["lead-maintainer"]
tags: ["data", "artifact", "examples", "interoperability"]
content_license: "CC0"
relatedDocs:
  - "docs/standards/data-artifact-contract.md"
audience: "implementers"
---

# Portable Data Artifact Contract Examples

These examples are review evidence for
[Portable Data Artifact Contract](data-artifact-contract.md). They are
source-neutral and intentionally synthetic.

Schema fixtures under `schemas/data-artifact/v0/examples/` include:

- `profile-extension.descriptor.json` — profile-qualified extension values for
  grain `kind`, representation `role`, and representation `format`. Base
  vocabulary values stay closed; extension values carry a `/` so validators can
  distinguish an intentional profile term from a typo.
- `fully-withheld-catalog.descriptor.json` — a field catalog with `fields: []`
  and a positive `withheld_field_count` (fully withheld under default-deny).
- `raw-archival-no-catalog.descriptor.json` — a raw archival grain that omits
  `field_catalog_ref` because it is not meant to be rendered or queried.

An empty `fields` array without a positive `withheld_field_count` MUST fail
closed at structural validation.

## Producer Adoption Preview Template

Use this five-part preview when mapping a producer to the portable contract.

### 1. What Stays The Same

Describe producer-native behavior that does not change. The portable contract
should attach at an export, discovery, validation, or hydrate boundary. It
should not force local storage, internal tables, or native payloads to become
the shared standard.

### 2. What Is Net New

List additive, opt-in surfaces:

- artifact descriptor;
- field catalog;
- representation descriptors;
- validation ladder;
- lifecycle mapping;
- protection metadata;
- guarded diagnostics.

### 3. What Becomes Possible

Explain what a generic consumer can do without producer-specific knowledge:

- discover the artifact;
- choose a representation by scale;
- understand field semantics;
- validate protection posture;
- refuse unsafe reads;
- map provenance and accounting links.

### 4. Objection Check

Name what would make the model producer-centric or unsafe. Examples:

- base fields that only one producer owns;
- source-file or document-order assumptions;
- local database layouts in the portable base;
- credentials or endpoints in descriptors;
- predicate pushdown over protected fields;
- split boundaries that disclose restricted structure.

### 5. Result

State whether the artifact maps cleanly. If not, state the smallest contract
change needed before freeze.

## Stress Case: Record Stream Extract

### Scenario

A producer emits a record stream plus a tabular projection. The stream contains
rich audit context. The projection is optimized for analytic scans.

### Mapping

```json
{
  "capabilities": ["contract: data-artifact/v0"],
  "artifact_id": "urn:uuid:00000000-0000-7000-8000-000000000001",
  "lifecycle": "complete",
  "producer": {
    "name": "record-extractor",
    "version": "1.0.0",
    "profile": "record-extract.artifact/v0",
    "run_id": "00000000-0000-7000-8000-000000000101"
  },
  "grains": [
    {
      "id": "records",
      "kind": "record_stream",
      "record_kind": "extract_record",
      "row_count": 3,
      "semantic_order": "source_order",
      "field_catalog_ref": "fields/records.fields.json"
    }
  ],
  "representations": [
    {
      "id": "records_ndjson",
      "grain": "records",
      "role": "audit_stream",
      "format": "ndjson",
      "uri": "records/records.jsonl",
      "row_count": 3,
      "read_path": {
        "range_readable": true,
        "appendable": false,
        "scan_capabilities": [],
        "read_path_granularity": "row",
        "gateable_unit_granularity": "row",
        "sidecar_required": true,
        "physical_ordering": "line_order"
      },
      "protection_enforceable_granularity": "row"
    },
    {
      "id": "records_parquet",
      "grain": "records",
      "role": "analytics_scan",
      "format": "parquet",
      "uri": "records/records.parquet",
      "row_count": 3,
      "field_catalog_ref": "fields/records.fields.json",
      "read_path": {
        "range_readable": true,
        "partitioned": false,
        "sharded": false,
        "scan_capabilities": ["columnar_scan", "predicate_pushdown"],
        "read_path_granularity": "column",
        "gateable_unit_granularity": "column",
        "pushdown_withheld": ["restricted_note"],
        "sidecar_required": true,
        "physical_ordering": "not_promised"
      },
      "protection_enforceable_granularity": "column"
    }
  ],
  "protection": {
    "default_action": "block_export",
    "default_export_class": "internal",
    "profile_ref": "profile:record-extract-review"
  }
}
```

### What This Proves

- A record stream can coexist with a projection without forcing one physical
  format to become the base model.
- Semantic order belongs to the grain; line order belongs to the representation.
- NDJSON cannot claim column/cell protection unless the gate parses and enforces
  at that finer unit.
- Predicate pushdown over protected fields must be withheld or evaluated behind
  a row/cell boundary.

## Stress Case: Object Index

### Scenario

A producer scans an object store and emits a sharded, queryable index. The
object key is sensitive content because it can encode project, dataset, person,
or workflow structure. Access-control fields are sensitive because they reveal
who can access what.

### Mapping

```json
{
  "capabilities": ["contract: data-artifact/v0"],
  "artifact_id": "urn:uuid:00000000-0000-7000-8000-000000000002",
  "lifecycle": "complete",
  "producer": {
    "name": "object-indexer",
    "version": "1.0.0",
    "profile": "object-index.artifact/v0",
    "run_id": "00000000-0000-7000-8000-000000000102"
  },
  "grains": [
    {
      "id": "objects",
      "kind": "object_index",
      "record_kind": "object",
      "row_count": 8,
      "primary_keys": ["object_key"],
      "field_catalog_ref": "fields/objects.fields.json"
    }
  ],
  "representations": [
    {
      "id": "objects_parquet_shards",
      "grain": "objects",
      "role": "object_index",
      "format": "parquet",
      "profile": "tabular-projection/v0",
      "uri": "objects/shards/manifest.json",
      "row_count": 8,
      "field_catalog_ref": "fields/objects.fields.json",
      "read_path": {
        "range_readable": true,
        "partitioned": true,
        "sharded": true,
        "appendable": false,
        "scan_capabilities": ["columnar_scan", "predicate_pushdown", "random_access"],
        "read_path_granularity": "column",
        "gateable_unit_granularity": "column",
        "pushdown_withheld": ["object_key", "access_owner"],
        "sidecar_required": true,
        "physical_ordering": "manifest_order",
        "split_strategy": "manifest_list",
        "shard_ids_opaque": true
      },
      "protection_enforceable_granularity": "column"
    }
  ],
  "protection": {
    "default_action": "block_export",
    "profile_ref": "profile:object-index-review"
  }
}
```

Field catalog excerpt:

```json
{
  "grain": "objects",
  "fields": [
    {
      "name": "object_key",
      "type": "string",
      "required": true,
      "semantic_role": "identifier",
      "sensitivity": "restricted",
      "protection_tags": ["direct_identifier", "source_structure"]
    },
    {
      "name": "size_bytes",
      "type": "integer",
      "semantic_role": "measure",
      "sensitivity": "internal",
      "protection_tags": ["measure", "safe_to_profile"]
    },
    {
      "name": "access_owner",
      "type": "string",
      "semantic_role": "access_control",
      "sensitivity": "restricted",
      "protection_tags": ["access_control_metadata", "quasi_identifier"]
    }
  ]
}
```

### What This Proves

- Primary keys are not automatically safe; sensitivity lives in the field
  catalog.
- An object index fits the same artifact/grain/representation model as other
  produced data artifacts.
- Protection must be enforceable at the units consumers can actually read.
- Predicate pushdown over a protected key is an inference channel. A column
  floor alone does not close it because the leak is row existence, not column
  visibility.
- Split metadata is metadata content. Shard ids are opaque when partition
  boundaries are based on restricted or source-structure fields.
- `value_profile` must not enumerate keys, access owners, or reconstructive
  shape templates unless the field is explicitly safe to profile.

## Stress Case: Database Or API Aggregation

### Scenario

A producer reads from a database or API through a connection handle, applies a
bounded aggregation, and emits a small analytics-ready result plus provenance.
There may be no source files and no source-document order.

### Mapping

```json
{
  "capabilities": ["contract: data-artifact/v0"],
  "artifact_id": "urn:uuid:00000000-0000-7000-8000-000000000003",
  "lifecycle": "complete",
  "producer": {
    "name": "aggregation-producer",
    "version": "1.0.0",
    "profile": "aggregation.artifact/v0",
    "run_id": "00000000-0000-7000-8000-000000000103"
  },
  "grains": [
    {
      "id": "daily_summary",
      "kind": "aggregation",
      "record_kind": "summary_row",
      "row_count": 3,
      "primary_keys": ["summary_date", "segment"],
      "field_catalog_ref": "fields/daily_summary.fields.json",
      "disclosure_control": {
        "method": "small_cell_suppression",
        "min_cell_size": 5,
        "applied": true
      }
    }
  ],
  "representations": [
    {
      "id": "daily_summary_ndjson",
      "grain": "daily_summary",
      "role": "audit_stream",
      "format": "ndjson",
      "uri": "daily-summary/records.jsonl",
      "row_count": 3,
      "read_path": {
        "range_readable": true,
        "partitioned": false,
        "sharded": false,
        "appendable": false,
        "sidecar_required": true,
        "physical_ordering": "not_promised",
        "read_path_granularity": "artifact",
        "gateable_unit_granularity": "artifact"
      },
      "protection_enforceable_granularity": "artifact"
    },
    {
      "id": "daily_summary_parquet",
      "grain": "daily_summary",
      "role": "analytics_scan",
      "format": "parquet",
      "profile": "tabular-projection/v0",
      "uri": "daily-summary/records.parquet",
      "row_count": 3,
      "field_catalog_ref": "fields/daily_summary.fields.json",
      "read_path": {
        "range_readable": true,
        "partitioned": false,
        "sharded": false,
        "scan_capabilities": ["columnar_scan", "predicate_pushdown"],
        "read_path_granularity": "column",
        "gateable_unit_granularity": "column",
        "pushdown_withheld": ["segment"],
        "sidecar_required": true,
        "physical_ordering": "not_promised"
      },
      "protection_enforceable_granularity": "column"
    }
  ],
  "provenance": {
    "job_ref": "jobs/sanitized-job.json",
    "source_refs": [
      {
        "kind": "connection_handle",
        "ref": "connection:source-system-readonly"
      }
    ]
  },
  "protection": {
    "default_action": "block_export",
    "profile_ref": "profile:aggregation-review"
  }
}
```

Field catalog excerpt:

```json
{
  "grain": "daily_summary",
  "fields": [
    {
      "name": "summary_date",
      "type": "date",
      "required": true,
      "semantic_role": "time",
      "sensitivity": "internal"
    },
    {
      "name": "segment",
      "type": "string",
      "required": true,
      "semantic_role": "category",
      "sensitivity": "controlled",
      "protection_tags": ["quasi_identifier"]
    },
    {
      "name": "amount_total",
      "type": "number",
      "semantic_role": "measure",
      "sensitivity": "controlled",
      "protection_tags": ["measure"]
    }
  ]
}
```

### What This Proves

- The portable base does not require files, document order, or source record
  numbers.
- Provenance uses connection handles, not DSNs, URLs, tokens, or raw query text.
- Aggregation results still need field catalogs because they are queryable.
- Grouped dimensions can be sensitive even when aggregate payload values look
  small or harmless.
- The reserved `disclosure_control` slot lets an aggregate declare suppression
  posture without making the portable contract own the aggregation algorithm.

## Consumer Witness Checklist

Before freezing the draft, at least one non-producer consumer should demonstrate:

- it resolves `contract: data-artifact/v0` without relying on a host embedded in
  the artifact;
- it validates the descriptor before opening a representation;
- it chooses a representation based on capabilities;
- it reads a safe representation and field catalog;
- it refuses an `unknown`-sensitivity field through an export gate it did not
  author;
- it refuses invalid predicate pushdown over a protected field;
- it treats metadata objects as export-classed content.

Reference producer: [fulmenhq/sumpter](https://github.com/fulmenhq/sumpter) is
an intentionally cited public producer for the portable contract; its concrete
schemas remain non-normative unless shared-profile convergence justifies
promotion.
