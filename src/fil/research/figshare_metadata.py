"""Offline primary-metadata inventory. No archive downloader or rights allowlist."""

import hashlib
import json
import re
from urllib.parse import urlsplit

VERSION = "fil-figshare-primary-metadata-inventory-1"
COLLECTION_ID = 4415000


def read_response(url: str, body: bytes) -> dict | list:
    """Accept only original metadata API responses, not downloads or processed mirrors.

    This validates a response's recorded origin, not authenticity of caller-supplied
    bytes. A future network acquisition receipt must bind TLS request/response,
    retrieval time, URL and SHA-256 before claiming primary-source verification.
    """
    u = urlsplit(url)
    if (
        u.scheme != "https"
        or u.netloc != "api.figshare.com"
        or u.fragment
        or not re.fullmatch(
            r"/v2/(collections/4415000(?:/versions(?:/\d+)?)?(?:/articles)?"
            r"|articles/\d+(?:/versions(?:/\d+)?)?)",
            u.path,
        )
    ):
        raise ValueError("Original collection/article metadata URL required; no archive URLs")
    return json.loads(body)


def inventory(collection: dict, articles: list[dict]) -> dict:
    """List exact per-version files and article licences, with unresolved rights explicit.

    Article licences are the recorded inheritance scope; never invent individual
    file-specific overrides. File payload hashes are unverified until separately
    authorized acquisition; provider MD5 is not a computed local SHA-256.
    """
    if collection.get("id") != COLLECTION_ID or collection.get("version") != 2:
        raise ValueError("Original collection 4415000 version 2 required")
    rows, seen = [], set()
    for a in articles:
        aid, version = a.get("id"), a.get("version")
        if type(aid) is not int or type(version) is not int or aid <= 0 or version <= 0:
            raise ValueError("Explicit original article identity/version required")
        for f in a.get("files", []):
            fid, size = f.get("id"), f.get("size")
            if type(fid) is not int or fid in seen or type(size) is not int or size < 0:
                raise ValueError("Duplicate/malformed original file identity/size")
            seen.add(fid)
            computed, supplied = f.get("computed_md5"), f.get("supplied_md5")
            license_record = a.get("license")
            reasons = []
            if not computed or not re.fullmatch("[0-9a-fA-F]{32}", computed):
                reasons.append("missing_or_invalid_provider_computed_md5")
            if supplied and computed and supplied.lower() != computed.lower():
                reasons.append("provider_checksum_fields_disagree")
            if not isinstance(license_record, dict) or not license_record.get("url"):
                reasons.append("missing_article_license")
            rows.append(
                dict(
                    article_id=aid,
                    article_version=version,
                    article_doi=a.get("doi"),
                    article_title=a.get("title"),
                    authors=a.get("authors"),
                    file_id=fid,
                    filename=f.get("name"),
                    size_bytes=size,
                    download_url=f.get("download_url"),
                    provider_computed_md5=computed,
                    provider_supplied_md5=supplied,
                    acquired_payload_sha256=None,
                    license_record=license_record,
                    license_scope="article_metadata_inheritance",
                    individually_verified_file_terms=False,
                    acquired=False,
                    metadata_issues=reasons,
                )
            )
    return dict(
        version=VERSION,
        collection_id=COLLECTION_ID,
        collection_version=2,
        collection_doi=collection.get("doi"),
        files=rows,
        snapshot_sha256=hashlib.sha256(
            json.dumps(dict(collection=collection, articles=articles), sort_keys=True).encode()
        ).hexdigest(),
        inventory_complete=False,
        completeness_status="requires_version_membership_and_pagination_audit",
        primary_network_receipts_verified=False,
        paper_license_crosscheck="PENDING",
        rights_review_status="PENDING_SOURCE_SPECIFIC_REVIEW",
        acquisition_authorized=False,
        training_authorized=False,
    )
