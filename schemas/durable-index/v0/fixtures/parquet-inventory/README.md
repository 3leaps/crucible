# Parquet inventory fixture corpus

The manifest binds 26 fixed Parquet members and six logical NDJSON twins for
`parquet-inventory/v0`. Each physical file has an exact SHA-256 and byte length.
Positive files additionally bind their logical twin, row count, codec, data-page
version and `size_bytes` annotation. Twenty physical negative files name the
expected refusal from the durable-index vocabulary.

## Positive members

| Member | Codec | Page | Size annotation | Rows |
| --- | --- | --- | --- | --- |
| `twin-zstd-v2-int64-signed` | ZSTD | 2 | Signed INT64 | 3 |
| `twin-zstd-v1-unannotated-size` | ZSTD | 1 | Absent | 3 |
| `twin-uncompressed-v1-int64-signed-multi-rg` | UNCOMPRESSED | 1 | Signed INT64 | 3 |
| `supplement-uncompressed-v2-full` | UNCOMPRESSED | 2 | Absent | 3 |
| `supplement-ordered-member-0` | UNCOMPRESSED | 2 | Signed INT64 | 1 |
| `supplement-ordered-member-1` | UNCOMPRESSED | 2 | Signed INT64 | 2 |

The multi-row-group member has three row groups. The ordered member set
concatenates the one-row and two-row twins to the complete three-row oracle.
Encoding variants preserve that complete logical row set. The profile's empty
snapshot is represented by zero members and zero rows.

## Authored logical oracle

The fixed rows exercise these values and relationships:

- A hidden path segment with null revision, zero size, null optional source
  fields, identical baseline lineage stamps and an empty enrichment list.
- The maximum exact integer `9007199254740991`, nanosecond timestamps and an
  opaque revision, with two sorted enrichment attributes bound to that revision,
  including an explicit null value.
- A Unicode key and a tombstone whose deletion stamp equals its last-change
  stamp, retains its older observation stamp and has an empty enrichment list.

The NDJSON bytes are authored input to the encoder. The split-member twins
preserve exact line chunks of the complete oracle. Expected rows and refusal
names are fixed corpus data. The physical decoder's output is compared with
those values.

## Binding controls

Run the baseline control through the repository's pinned toolchain:

```sh
python3 scripts/test-durable-index-physical-controls.py
```

The control verifies the closed manifest, complete file inventory, SHA-256 and
byte lengths, strict logical row shape and semantics, row counts, and ordered
member-set parity. Negative controls exercise changed pins, missing or extra
files, invalid logical rows and member-boundary failures. Its invocation set
uses Python standard library and the existing goneat schema validator.

## Encoding provenance and physical evidence

The manifest records the source repository and revision, generator and reader
entry points, Go and parquet-go versions, invocation, and fixed authored
logical-oracle digest. The fixed files are encoded using Gonimbus's
`GenerateSliceDParquetTwins`, `ExportSliceDParquetTwins` and
`WriteParquetInventoryMember` entry points. For the absent-annotation fixtures, both `LogicalType` and `ConvertedType`
are cleared on the footer's `size_bytes` schema element while its physical
INT64 column pages are preserved. Each re-encoding has its own physical-byte
pins.

Physical-member evidence uses `ReadParquetInventoryMember` against these exact
bytes, comparing accepted members with their fixed logical twins and checking
the twenty named refusals. Physical decoder execution is separate from the
baseline binding gate under PDR-0006. R2/W1/W2/W3 qualification additionally
requires the complete physical graph and operation evidence specified in
[Durable Index Conformance](../../../../../docs/standards/durable-index-conformance.md).
