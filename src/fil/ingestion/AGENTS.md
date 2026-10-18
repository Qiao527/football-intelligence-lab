# Ingestion-specific rules
- Keep raw provider input immutable and source-preserving; fail closed on malformed IDs/schema.
- Never silently drop events, remap `event_id`, or infer match/team metadata from file paths.
- Record raw count, output count, unknown type count, nullable values and source hash.
- When adapter mappings change, update fixtures, schema version and migration notes; tests must prove source ID traceability.
- Mark source fetching separately from data normalization; avoid network calls in deterministic unit tests.
