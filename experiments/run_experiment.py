import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import distributions
from pathlib import Path
from uuid import uuid4

from cv_extraction.pipeline import run_extraction
from cv_extraction.storage import save_json
from cv_extraction.config import select_split
from cv_extraction.reporting import build_document_summaries
from cv_extraction.hardware import capture_hardware

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_output(*arguments):
    try:
        result = subprocess.run(
            ["git", *arguments],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False
        )
    except OSError:
        return None

    return result.stdout.strip() if result.returncode == 0 else None


def prepare_config(config_path: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))

    if config["method"] != "pdf_text":
        raise ValueError("Only the pdf_text method is currently supported.")

    if type(config["settings"]["sort_text"]) is not bool:
        raise ValueError("sort_text must be true or false.")

    repetitions = config["repetitions"]

    if type(repetitions) is not int or repetitions < 1:
        raise ValueError("repetitions must be a positive integer.")

    # Incase of rerun this gets skipped(because the config will already contain inputs)
    if "inputs" not in config:
        manifest_path = PROJECT_ROOT / "data" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        documents = manifest["documents"]

        split_name = config.get("split")

        if split_name is not None:
            documents = select_split(
                documents,
                PROJECT_ROOT / "data" / "splits.json",
                split_name
            )

        requested_ids = config["document_ids"]

        # Check if the requested id exists(in manifest.json)
        if requested_ids is not None:
            available_ids = {document["id"] for document in documents}
            unknown_ids = set(requested_ids) - available_ids

            if unknown_ids:
                raise ValueError("Requested IDs are unavailable in the selected dataset: "f"{sorted(unknown_ids)}")

            documents = [
                document
                for document in documents
                if document["id"] in requested_ids
            ]

        excluded_sources = config.get("exclude_sources", [])

        available_sources = set(manifest["sources"])
        unknown_sources = set(excluded_sources) - available_sources

        if unknown_sources:
            raise ValueError(f"Unknown excluded sources: {sorted(unknown_sources)}")

        config["excluded_inputs"] = [
            {
                "id": document["id"],
                "reason": f"Source excluded: {document['source']}"
            }
            for document in documents
            if document["source"] in excluded_sources
        ]

        documents = [
            document
            for document in documents
            if document["source"] not in excluded_sources
        ]
        
        config["inputs"] = []

        for document in documents:
            path = PROJECT_ROOT / "data" / document["file"]

            if not path.is_file():
                raise FileNotFoundError(f"Selected PDF is missing: {document['id']} at {path}")
            config["inputs"].append({
                "id": document["id"],
                "file": path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": file_hash(path)
            })

    if not config["inputs"]:
        raise ValueError("No documents were selected.")

    # Check if the pdf content changed during rerun from original run.
    for document in config["inputs"]:
        path = PROJECT_ROOT / document["file"]

        if not path.is_file():
            raise FileNotFoundError(f"Required rerun PDF is missing: {document['id']} at {path}")
        
        if file_hash(path) != document["sha256"]:
            raise ValueError(f"PDF contents changed for {document['id']}: {path}")

    return config


def capture_environment() -> dict:
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "hardware": capture_hardware(),
        "git_commit": git_output("rev-parse", "HEAD"),
        "git_status": git_output("status", "--porcelain"),
        "packages": {
            distribution.metadata["Name"]: distribution.version
            for distribution in distributions()
            if distribution.metadata["Name"]
        }
    }

def save_stage(attempt_directory: Path, stage_report: dict, output) -> None:
    stage_directory = attempt_directory / stage_report["name"]

    if output is not None:
        save_json(stage_directory / "extraction.json", output)

    save_json(stage_directory / "report.json", stage_report)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    arguments = parser.parse_args()

    config = prepare_config(arguments.config)
        
    started_at = datetime.now(timezone.utc)
    run_id = (
        started_at.strftime("%Y%m%dT%H%M%S")
        + "_"
        + uuid4().hex[:8]
    )
    environment = capture_environment()
    
    run_directory = PROJECT_ROOT / "results" / run_id
    run_directory.mkdir(parents=True, exist_ok=False)

    save_json(run_directory / "config.json", config)
    save_json(run_directory / "environment.json", environment)

    reports = []

    for document in config["inputs"]:
        pdf_path = PROJECT_ROOT / document["file"]

        for repetition in range(1, config["repetitions"] + 1):
            output_directory = (
                run_directory
                / "documents"
                / document["id"]
                / f"repeat_{repetition:03d}"
            )
            def on_stage_finished(stage_report, output):
                save_stage(
                    output_directory,
                    stage_report,
                    output
                )

            result = run_extraction(
                pdf_path,
                sort_text=config["settings"]["sort_text"],
                on_stage_finished=on_stage_finished
            )

            result.pop("extracted_data")

            report = {
                "document_id": document["id"],
                "repetition": repetition,
                **result
            }

            save_json(output_directory / "report.json", report)
            reports.append(report)

            print(
                f"{document['id']} "
                f"[{repetition}/{config['repetitions']}]: "
                f"{report['status']}"
            )

    document_summaries = build_document_summaries(
        reports,
        config["inputs"]
    )

    save_json(
        run_directory / "summary.json",
        {
            "run_id": run_id,
            "started_at_utc": started_at.isoformat(),
            "finished_at_utc": datetime.now(timezone.utc).isoformat(),
            "document_count": len(config["inputs"]),
            "attempt_count": len(reports),
            "documents": document_summaries
        }
    )

    print(f"Results saved to: {run_directory}")


if __name__ == "__main__":
    main()