---
name: fil-source-audit
description: Audit football event source files, provider provenance, match identity, legal-use notes, SHA-256 and normalization traceability. Use when importing or refreshing StatsBomb or other legally obtained event datasets; do not invent metadata.
---
# FIL Source Audit
1. Identify exact event source URL/local file, source license/usage constraints, competition/season/match identity, retrieved date, SHA-256 and source schema revision if available.
2. Inspect a sample plus all keys/type frequencies and edge cases without mutating raw bytes.
3. Check event UUID uniqueness, provider sequence/index, match periods, related own-goal records and required optional fields.
4. Generate a manifest and QC report with explicit PASS/FAIL/WARN per check.
5. Validate a reverse lookup for sampled derived rows to their raw event ID and JSON object.
6. Distinguish verified source facts from inference; list unavailable documents as blockers.
