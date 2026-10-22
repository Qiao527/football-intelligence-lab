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
`www.statsbomb.com/resource-centre` before access. On 2026-10-19 the project
owner explicitly confirmed: **"Registration completed; noncommercial research"**.
This is an owner attestation, not independent verification of a provider account
or a new provider license. No personal details were requested or submitted by
the agent. No broader permission or redistribution approval is inferred.

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
- **DATA-SOURCE: PASS for local noncommercial research**, based on the recorded
  source identity/hash/manifest checks plus the owner's registration and use
  confirmation. This applies to match 8658 at the pinned revision above.
- **DEL-SOURCE: PASS for that same limited scope**: usable source and applicable
  rights/restrictions are recorded. Redistribution and commercial use remain
  unapproved; publication still requires provider attribution/branding.
- No DATA-SCHEMA or later gate is claimed: acquisition is not normalization,
  full provider-schema validation, score reconciliation or metric calculation.

The manifest deliberately separates `source_integrity_status` from
`rights_gate_status`. The CLI does not accept a flag that silently grants
redistribution permission or claims owner registration.


## Immutable acquisition record and later confirmation

The existing local manifest was created before the owner's reply and retains
`rights_gate_status: PENDING_OWNER_CONFIRMATION`. Its warnings and timestamp
remain historical acquisition facts; neither it nor provider bytes are rewritten.
This policy and FIL-002_VERIFICATION.md record the subsequent owner confirmation
and current scoped gate decision. The CLI only reports its immutable acquisition
record and technical verification; it does not decide later rights status.
The relevant manifest SHA-256 is
`f9d1b52d9d736972df029a64480d8e2853a3cbf88f251bb2478c6e0f4da6952c`.

## Conditional World Cup corpus authorization — 22 October 2026

The owner explicitly approved PR #14's exact 126 additional event/lineup files at
revision `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`. The immutable enumeration is
`docs/research/statsbomb_corpus_proposal.json`, SHA-256
`bd9357a8bf3c87c808477308770f1e798b7f7b1d98f4468c7fc6c56e9ac17787`.
This later authorization supersedes that proposal's historical pending status;
the proposal and original 8658 manifest are not rewritten.

Acquire pilot 8649/8650/8651/8652/8655/8656 first. Expansion to the other 57
requires complete independently checked source/identity/lineup/score/missingness/
possession/spatial gates without unresolved material issues. Rights or integrity
ambiguity stops the affected acquisition/analysis. No additional provider,
competition, revision or file is approved.

Use is limited to local noncommercial football research, reconciliation,
possession/process analysis and transparent empirical baseline fitting/evaluation
consistent with the reviewed provider agreement. Owner approval does not override
provider terms. Keep raw and derived artifacts ignored, immutable and local.
No redistribution, publication, commercial use, external AI upload, deployment,
model-weight publication or xT/VAEP training. Existing registration attestation
and attribution/branding conditions remain unchanged. World Cup matches are not
proof of general football validity; 8658 is development-exposed, never untouched
validation/test. Wyscout remains separately unapproved.
