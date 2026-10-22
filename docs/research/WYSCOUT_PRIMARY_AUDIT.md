# Original Figshare metadata audit — bounded work, no acquisition approval

Current environment observation: restricted network policy **enforced**;
`api.figshare.com` is absent. The original denied operation was
`GET https://api.figshare.com/v2/collections/4415000/articles`, CONNECT 403 via
the managed proxy. This turn checked current policy, not the denied operation
again. No alternative proxy, mirror, archive or blocked-domain relay was used.

The exact immediate environment action is unchanged: add **api.figshare.com** to
the managed outbound allowlist and publish/apply it. This grants metadata access,
not dataset rights or archive acquisition. No configuration write tool is exposed.

## Primary evidence inventory

| Item | Exact locator / version | Current verification |
| --- | --- | --- |
| Original collection | DOI `10.6084/m9.figshare.c.4415000`, version-2 lead | API bytes, version record and membership unverified |
| Original paper | Pappalardo et al., *A public data set of spatio-temporal match events in soccer competitions*, Scientific Data 6, 236 (2019), DOI `10.1038/s41597-019-0247-7` | Owner identifies its released-dataset CC BY 4.0 statement; primary paper text not retrievable under current policy |
| Constituent articles | Obtain original collection-version membership, article versions and DOIs | Unknown; no guessed IDs accepted |
| Individual archives/metadata files | Article-version files, original ID/name/bytes/MD5/download URL | Unknown; no archive acquired |
| Individual applicable licences | Each article's exact licence object/URL; any file-specific terms and accompanying documents | Unknown; paper statement alone does not certify every current file/version |

The existing processed-mirror README is corroborating discovery context only.
Its software licence or CC BY assertion does not substitute for original release
terms. Historical candidate file IDs remain unverified leads and are not reused
as an allowlist. The original paper's dataset licensing statement should be
cross-checked, not ignored or conflated with the paper's own open-access licence.

## Exact metadata-only procedure when access exists

1. Save original collection details, available version records and version-2
   member listing with all pages. Verify documented API endpoint/version semantics
   before treating a current `/articles` listing as historical version 2.
2. For each member save original article details, available versions, requested
   exact-version details, DOI, authors, dates, references, licence object and file
   descriptors. Record pagination completeness and any inaccessible/deleted member.
3. Store immutable original JSON responses and receipts locally: full metadata
   URL, HTTP status, retrieval UTC, response SHA-256, collection/article version
   and redirects (no automatic off-host redirect). Never request `download_url`.
4. Inventory exact file IDs/names/sizes; distinguish provider `computed_md5` from
   `supplied_md5`, and both from locally computed payload SHA-256 (still null).
   Report checksum disagreements, missing licences, conflicting versions and
   external-linked files; do not normalize them away.
5. Cross-check the publisher's primary paper (DOI above, Data Records/Usage Notes
   and dataset rights wording), exact licence URLs and original article descriptions.
   If another host is required, report that precise observed destination before
   requesting narrowly scoped access; no speculative wildcard access.
6. Attach file-level rights rows with article-inherited versus independently
   file-specific terms clearly marked. Review attribution, modification notice,
   local noncommercial analytical/model-fitting scope and any excluded material.
   Resolve conflicts before acquisition proposal acceptance.

`fil.research.figshare_metadata` implements an offline parser/validator for such
original metadata, with TEST_ONLY response regression coverage. It does not claim
that caller-supplied JSON is authenticated upstream evidence, certify complete
pagination/version membership or enable production ingestion. No archive downloader
or production registry change is added.

## Bounded future proposal — not yet executable or approvable

Proposed purpose: local noncommercial source reconciliation, provider-specific
event/possession research and transparent empirical baseline evaluation. First
scope: **2018 World Cup, only if confirmed in the original release metadata**,
only its event/match/team/player metadata files. Exact article versions, file IDs,
byte budget, checksums and licence/attribution rows must replace all unknowns in a
separate immutable proposal before owner authorization. Start with a small identity/
quality pilot; do not treat that pilot as statistically adequate validation.

No exact bounded acquisition request is made now because primary file/version/
licence inventory is unknown. A falsely precise request would defeat the source
audit. No Wyscout archive, additional competition, xT/VAEP training, model-weight
publication, redistribution, external AI upload, deployment or cross-provider
pooling is authorized. Even if CC BY 4.0 is confirmed, owner scope remains separate
and narrower; verify attribution and notice duties, exclusions and any third-party
material. No legal permission is inferred from a software library licence.
