"""Prepare a local, unlabelled analyst feasibility packet; never contact participants."""

import csv
import hashlib
import json
import sys
from pathlib import Path


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def write_csv(path, fields, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def prepare(study: Path, destination: Path) -> Path:
    m = json.loads((study / "manifest.json").read_bytes())
    if any(sha(study / p) != h for p, h in m["files"].items()):
        raise ValueError("Study artifact changed")
    if any(sha(p) != h for p, h in m["protected_inputs"].items()):
        raise ValueError("Source provenance changed")
    rows = json.loads((study / "evidence.json").read_bytes())["primary"]
    summary = json.loads((study / "summary.json").read_bytes())["variants"]["primary"]
    comparable = {
        tuple(k) for s in summary["team_match_context"]["shared_strata"] for k in s["source_units"]
    }
    pools = [
        [r for r in rows if r["feature"] is True],
        [
            r
            for r in rows
            if r["feature"] is False and (r["match_id"], r["possession_id"]) in comparable
        ],
        [r for r in rows if r["feature"] is None or r["outcome"] is None],
    ]

    def key(r):
        return hashlib.sha256(f"{r['match_id']}:{r['possession_id']}".encode()).hexdigest()

    chosen, used = [], set()
    for category, pool in enumerate(pools):
        n = 0
        for r in sorted(pool, key=key):
            if r["match_id"] in used:
                continue
            chosen.append((category, r))
            used.add(r["match_id"])
            n += 1
            if n == 4:
                break
    # Identity-derived display order, independent of outcome and example persuasiveness.
    chosen.sort(key=lambda item: key(item[1]))
    sources = {s["match_id"]: s for s in json.loads((study / "source-inputs.json").read_bytes())}
    destination.mkdir(parents=True, exist_ok=False)
    for name in ("source-only-adjudication", "conditions", "private-design"):
        (destination / name).mkdir()
    tasks, allocation, private, judgments = [], [], [], []
    ledger_fields = [
        "event_id",
        "provider_index",
        "period",
        "timestamp",
        "event_type",
        "team_id",
        "possession_team_id",
        "player_id",
        "location_json",
        "original_record_json",
        "source_manifest_sha256",
    ]
    for i, (category, r) in enumerate(chosen):
        task_id = f"TASK_{i + 1:02d}"
        source = sources[r["match_id"]]
        raw = json.loads(Path(source["events"]).read_bytes())
        by = {e["id"]: e for e in raw}
        ledger = []
        for eid in r["source_event_ids"]:
            e = by[eid]
            ledger.append(
                dict(
                    event_id=eid,
                    provider_index=e["index"],
                    period=e["period"],
                    timestamp=e["timestamp"],
                    event_type=e["type"]["name"],
                    team_id=e["team"]["id"],
                    possession_team_id=e.get("possession_team", {}).get("id"),
                    player_id=e.get("player", {}).get("id"),
                    location_json=json.dumps(e.get("location")),
                    original_record_json=json.dumps(e, sort_keys=True),
                    source_manifest_sha256=source["source_manifest_sha256"],
                )
            )
        source_path = destination / "source-only-adjudication" / f"{task_id}.csv"
        write_csv(source_path, ledger_fields, ledger)
        write_csv(destination / "conditions" / f"{task_id}-ledger.csv", ledger_fields, ledger)
        selected = [r["entry_event_id"]] if r.get("entry_event_id") else []
        selected += r.get("landmark_window_ids", [])
        card = [
            f"# {task_id}: selected source records",
            "",
            "LOCAL ONLY. Use the complete ledger.",
            "These records are an algorithmic selection, not an independent relevance judgment.",
            "Native coordinates do not certify physical direction or tactical intention.",
            "",
        ]
        for eid in selected:
            card += [
                f"## Original event {eid}",
                "",
                "```json",
                json.dumps(by[eid], indent=2),
                "```",
                "",
            ]
        if not selected:
            card += [
                "No source prefix selected. Review the complete ledger and report uncertainty."
            ]
        (destination / "conditions" / f"{task_id}-card.md").write_text("\n".join(card) + "\n")
        tasks.append(
            dict(
                task_id=task_id,
                question=(
                    "Identify evidence for and against a recorded retreat followed by re-entry "
                    "after an upper-native-x entry. Would this route distinction be useful for "
                    "comparing buildup? Return at most ten original action IDs, explain "
                    "counterevidence and uncertainty; "
                    "do not infer intent, pressure or player ability."
                ),
            )
        )
        private.append(
            dict(
                task_id=task_id,
                selection_category=category,
                match_id=r["match_id"],
                possession_id=r["possession_id"],
                machine_feature=r["feature"],
                exclusion_reasons=r["exclusion_reasons"],
            )
        )
        for slot in (1, 2):
            allocation.append(
                dict(
                    planning_slot=f"ANALYST_SLOT_{slot}",
                    participant_id="",
                    task_id=task_id,
                    condition="ledger" if (i + slot) % 2 else "card",
                    actual_start_time="",
                    actual_end_time="",
                    completed="",
                )
            )
            judgments.append(
                dict(
                    planning_slot=f"ADJUDICATOR_SLOT_{slot}",
                    participant_id="",
                    task_id=task_id,
                    relevant_event_ids_json="",
                    counterevidence_ids_json="",
                    uncertain_event_ids_json="",
                    relevance_rationale="",
                    disagreements="",
                )
            )
    write_csv(destination / "tasks.csv", ["task_id", "question"], tasks)
    write_csv(
        destination / "assignment-template.csv",
        list(allocation[0]) if allocation else [],
        allocation,
    )
    write_csv(
        destination / "judgment-template.csv", list(judgments[0]) if judgments else [], judgments
    )
    write_csv(
        destination / "analyst-response-template.csv",
        [
            "participant_id",
            "task_id",
            "condition",
            "event_ids_json",
            "answer",
            "uncertainty",
            "elapsed_seconds",
            "decision_relevance",
            "unsupported_claims",
            "reviewer_notes",
        ],
        [],
    )
    (destination / "private-design" / "case-map.json").write_text(
        json.dumps(private, indent=2) + "\n"
    )
    (destination / "README.md").write_text(
        "# LOCAL ONLY — unrun analyst feasibility study\n\n"
        "No participants recruited; planning slots are not people. No labels collected.\n"
        "STOP: third-party provider-data access is not cleared. Do not send externally.\n"
        "Provider restrictions apply even to local viewing by an outside analyst.\n\n"
        "Two separate adjudicator slots inspect only source-only-adjudication and tasks.csv.\n"
        "Hide private-design, algorithmic cards and analyst condition allocation from them.\n"
        "Record disagreements and unknown relevance; machine features are not gold labels.\n"
        "Analyst slots use the assignment template: ledger condition gets the complete searchable\n"
        "CSV; card condition gets the identical CSV plus selected source records. No added source\n"
        "information. No analyst sees one match/task twice. Do not interpret a balanced case set\n"
        "as prevalence or independent replication. Interface blinding is incomplete.\n\n"
        "Retrieve at most ten IDs. Compute recall only with independently adjudicated\n"
        "relevance set exists; empty/uncertain gold has no fabricated perfect score. Report claim\n"
        "support and uncertainty. Later confirmatory endpoint, worthwhile effect and sample size\n"
        "remain pending independent analyst input and a distinct pilot. No significance from\n"
        "dependent task/event rows. No new model, prediction or football discovery is validated.\n"
    )
    protected = dict(m["protected_inputs"])
    protected[str((study / "manifest.json").resolve())] = sha(study / "manifest.json")
    manifest = dict(
        version="fil-reentry-analyst-feasibility-packet-1",
        study=str(study.resolve()),
        study_manifest_sha256=sha(study / "manifest.json"),
        preparer_sha256=sha(__file__),
        tasks=len(tasks),
        distinct_matches=len(used),
        participants=0,
        collected_labels=0,
        external_review_access_cleared=False,
        protected_inputs=protected,
        files={
            str(p.relative_to(destination)): sha(p) for p in destination.rglob("*") if p.is_file()
        },
    )
    (destination / "manifest.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    )
    return destination


if __name__ == "__main__":
    print(json.dumps(dict(packet=str(prepare(*map(Path, sys.argv[1:])).resolve()))))
