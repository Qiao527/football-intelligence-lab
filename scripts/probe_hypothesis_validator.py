"""Synthetic-only, offline component probe; never installs third-party skills.

Usage: python scripts/probe_hypothesis_validator.py REVIEWED_SOURCE_ROOT OUTPUT_DIR
See docs/research/CAPABILITY_POC_PROTOCOL.md. The upstream files retain their MIT
license in the locally reviewed source inventory; no upstream implementation is
vendored into FIL. This runner is not a security sandbox for arbitrary code.
"""

import copy
import hashlib
import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def bounded_child():
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (4 * 1024 * 1024, 4 * 1024 * 1024))


def main():
    source, output = map(Path, sys.argv[1:])
    output.mkdir(parents=True, exist_ok=False)
    base = source / "skills/hypothesis-generation"
    paths = [base / "scripts" / n for n in ("validate_hypothesis_schema.py", "_common.py")]
    template = base / "assets/hypothesis_record_template.json"
    paths.append(template)
    paths.append(source / "LICENSE.md")
    hashes = {str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    expected = {
        "LICENSE.md": "09b02a3c9df3053c55531d503357a9c7cde275970e6c3ceaa1ddf5f0e90b40c1",
        "validate_hypothesis_schema.py": (
            "63bc1b7752d20042c2845ecb2457448ec8e2d9bc8fe1337003b222f8f4620608"
        ),
        "_common.py": "7a41a5f9b97092ee188d45959f38f92a4215d4f298dd04fd0f2817e9f607e74e",
        "hypothesis_record_template.json": (
            "73f080a6696c415f228b38100bb7b0f6bc89ad2c7997bf50d62b585b0bc8fe0c"
        ),
    }
    if {Path(p).name: h for p, h in hashes.items()} != expected:
        raise ValueError("Reviewed upstream file identity changed; refuse execution")
    control = json.loads(template.read_text())
    cases = {
        n: copy.deepcopy(control)
        for n in (
            "control",
            "missing_falsifier",
            "dangling_prediction",
            "causal_no_estimand",
            "undeclared_source",
            "external_sensitive",
            "blocked_gate",
            "invented_provenance",
            "wrong_independent_unit",
            "tautological_falsifier",
        )
    }
    del cases["missing_falsifier"]["predictions"][0]["falsifier"]
    cases["dangling_prediction"]["hypotheses"][0]["prediction_ids"] = ["ABSENT"]
    cases["causal_no_estimand"]["causal_estimands"] = []
    cases["undeclared_source"]["observation"]["source_ids"] = ["ABSENT"]
    cases["external_sensitive"]["ai_use"]["sensitive_or_unpublished_data_sent_externally"] = True
    gate = cases["blocked_gate"]["ethics_and_feasibility"]
    gate["data_governance_gate"] = "blocked"
    gate["unresolved_blocks"] = ["Synthetic fixture: acquisition permission has not been granted."]
    cases["invented_provenance"]["observation"]["provenance"] = (
        "Unsupported assertion: these invented observations prove all football abilities."
    )
    cases["wrong_independent_unit"]["analysis_plan"]["analyses"][0]["method"] = (
        "Treat repeated events from the same player and match as independent iid observations."
    )
    cases["tautological_falsifier"]["predictions"][0]["falsifier"] = (
        "Every possible result supports this hypothesis; no observation can contradict it."
    )
    samples = []
    with tempfile.TemporaryDirectory(prefix="fil-hypothesis-probe-") as task_dir:
        task = Path(task_dir)
        for p in paths:
            shutil.copyfile(p, task / p.name)
        for name, record in cases.items():
            text = json.dumps(record, sort_keys=True, indent=2) + "\n"
            (task / f"{name}.json").write_text(text)
            (output / f"{name}.json").write_text(text)
        names = list(cases)
        for repetition in range(3):
            for name in names if repetition != 1 else reversed(names):
                begin = time.perf_counter()
                result = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        "-S",
                        str(task / paths[0].name),
                        str(task / f"{name}.json"),
                    ],
                    cwd=task,
                    env={"LANG": "C.UTF-8", "PYTHONHASHSEED": "0"},
                    capture_output=True,
                    text=True,
                    timeout=10,
                    preexec_fn=bounded_child,
                    check=False,
                )
                samples.append(
                    {
                        "case": name,
                        "repetition": repetition,
                        "elapsed_seconds": time.perf_counter() - begin,
                        "returncode": result.returncode,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "json_parser_accepts": True,
                    }
                )
    receipt = {
        "version": "fil-hypothesis-component-probe-1",
        "upstream_commit": "593377bb048752abb0152deab9fbb1083a6087df",
        "source_sha256": hashes,
        "protocol_sha256": hashlib.sha256(
            Path("docs/research/CAPABILITY_POC_PROTOCOL.md").read_bytes()
        ).hexdigest(),
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python": sys.version,
        "platform": sys.platform,
        "network_permission_requested": False,
        "provider_data_used": False,
        "packages_installed": [],
        "samples": samples,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    os.chmod(output / "receipt.json", 0o600)
    print(json.dumps({"receipt": str(output / "receipt.json"), "samples": len(samples)}))


if __name__ == "__main__":
    main()
