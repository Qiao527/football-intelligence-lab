# StatsBomb source usage assessment — FIL-002

## Reviewed source and scope

Official repository: https://github.com/hudl/open-data

Reviewed immutable revision: `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`.
The source README and LICENSE.pdf were fetched and read before match acquisition.
The PDF identifies itself as the StatsBomb Public Data User Agreement, last
updated 8 September 2023. The pinned file identities are in
`src/fil/ingestion/statsbomb_source.json`; no provider documents or JSON datasets
are committed. FIL's MIT license does not relicense StatsBomb data.

Pinned terms:

- [README](https://raw.githubusercontent.com/hudl/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/README.md)
- [LICENSE.pdf](https://raw.githubusercontent.com/hudl/open-data/4b73468fc5b0f1950f9f66fada70ad3a4f9327cb/LICENSE.pdf)

## Observed terms and controls

The README describes research projects and genuine interest in football
analytics. It asks published/shared analysis to credit StatsBomb and use its
logo, linking the provider's [media pack](https://statsbomb.com/media-pack/).
The license §1.1 permits access for analysis/research/shared understanding.
Sections 1.2.1 and 7 restrict editing, reproduction and distribution/provision
of data to third parties; §1.2.2 forbids commercial exploitation of the data or
derived analysis. Section 1.4 requires branding on publications.

Sections 1/2.2 ask users to register their name and email via
`www.statsbomb.com/resource-centre` before access. Owner registration has **not
been verified by this implementation**. No personal details were submitted by
the agent. No registration endpoint or broader license permission is assumed
to be available. The owner must confirm registration/terms compliance and the
noncommercial research purpose before the rights gate can close.

Current acquisition is limited to the user's requested local historical research
fixture and its source terms/metadata. All provider bytes and the actual
manifest remain in ignored `data/raw/`; they are excluded from Git and package
artifacts. Do not attach raw files to issues/PRs or include them in public
snapshots, wheels, releases, dashboards or environment images offered to third
parties. Publishing analysis would additionally require the source attribution
and logo; no analysis is published by this task.

Raw-data redistribution and commercial use are **not approved**. Future public
or commercial use requires a separate rights review and, where necessary,
explicit written provider consent. No raw datasets may be committed until both
rights and explicit user approval are established.

## Gate assessment

- Technical source integrity: independently verify the pinned URLs, file hashes,
  metadata identity and event IDs using the acquisition/verification commands.
- **DATA-SOURCE: PENDING** while owner registration/terms compliance remains
  unconfirmed, even if the technical checks pass.
- **DEL-SOURCE: PENDING** for the same unresolved rights condition. Recording
  restrictions is not evidence that this condition was fulfilled.
- No DATA-SCHEMA or later gate is claimed: acquisition is not normalization,
  full provider-schema validation, score reconciliation or metric calculation.

The manifest deliberately separates `source_integrity_status` from
`rights_gate_status`. The CLI does not accept a flag that silently grants
redistribution permission or claims owner registration.
