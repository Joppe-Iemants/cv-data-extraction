from pathlib import Path
from time import perf_counter

from .stages import STAGE_METHODS
from ..monitoring.memory import MemoryMonitor

def validate_stage_output(output) -> None:
    if not isinstance(output, dict):
        raise TypeError("Stage output must be a dictionary.")

    required_keys = {"data", "outcome", "metrics"}
    missing_keys = required_keys - set(output)

    if missing_keys:
        raise ValueError(
            f"Stage output is missing keys: {sorted(missing_keys)}"
        )

    if not isinstance(output["data"], dict):
        raise TypeError("Stage output data must be a dictionary.")

    outcome = output["outcome"]

    if not isinstance(outcome, str) or not outcome.strip():
        raise ValueError(
            "Stage outcome must be a nonempty string."
        )

    metrics = output["metrics"]

    if not isinstance(metrics, dict):
        raise TypeError("Stage metrics must be a dictionary.")

    reserved_keys = {"duration_seconds", "memory"}
    conflicting_keys = reserved_keys & set(metrics)

    if conflicting_keys:
        raise ValueError(
            "Stage metrics cannot overwrite shared measurements: "
            f"{sorted(conflicting_keys)}"
        )
    
    if "artifacts" in output:
        if not isinstance(output["artifacts"], dict):
            raise TypeError("Stage artifacts must be a dictionary.")
        
def execute_stage(name: str, method: str, function, *args, monitoring: dict | None = None, **kwargs) -> dict:
    settings = monitoring or {}

    monitor = MemoryMonitor(
        enabled=settings.get("memory", False),
        sample_interval_ms=settings.get("sample_interval_ms", 10)
    )

    output = None
    error_details = None
    artifacts = None
    execution_status = "completed"

    monitor.start()
    start = perf_counter()

    try:
        output = function(*args, **kwargs)
        validate_stage_output(output)
        artifacts = output.get("artifacts")
    except Exception as error:
        output = None
        execution_status = "error"
        artifacts = getattr(error, "artifacts", None)
        error_details = {
            "type": type(error).__name__,
            "message": str(error)
        }
    finally:
        duration = perf_counter() - start
        monitor.stop()

    return {
        "report": {
            "name": name,
            "method": method,
            "execution_status": execution_status,
            "outcome": None,
            "metrics": {
                "duration_seconds": duration,
                "memory": monitor.report()
            },
            "error": error_details,
            "artifacts": artifacts
        },
        "output": output
    }

def run_extraction(pdf_path: Path, stages: list[dict], on_stage_finished=None, monitoring: dict | None = None) -> dict:
    current_input = pdf_path
    last_output = None
    stage_reports = []

    status = "completed"
    stop_reason = None

    for stage_config in stages:
        name = stage_config["name"]
        method = stage_config["method"]

        if stop_reason is not None:
            stage_report = {
                "name": name,
                "method": method,
                "execution_status": "skipped",
                "outcome": None,
                "metrics": {},
                "error": None,
                "skip_reason": stop_reason
            }

            stage_reports.append(stage_report)

            if on_stage_finished is not None:
                on_stage_finished(stage_report, None)

            continue

        definition = STAGE_METHODS[method]

        stage = execute_stage(
            name,
            method,
            definition["function"],
            current_input,
            monitoring=monitoring,
            **stage_config["settings"]
        )

        stage_report = stage["report"]
        output = None

        if stage_report["execution_status"] == "error":
            status = "error"
            stop_reason = f"Previous stage failed: {name}"
        else:
            stage_output = stage["output"]

            output = stage_output["data"]
            stage_report["outcome"] = stage_output["outcome"]
            stage_report["metrics"].update(stage_output["metrics"])

            current_input = output
            last_output = output

            if stage_report["outcome"] == "empty_text":
                status = "empty_text"
                stop_reason = f"Previous stage returned no text: {name}"
            elif stage_report["outcome"] == "partial_text":
                status = "partial_text"

        stage_reports.append(stage_report)

        if on_stage_finished is not None:
            on_stage_finished(stage_report, output)

    processing_seconds = sum(
        report["metrics"].get("duration_seconds", 0)
        for report in stage_reports
    )

    return {
        "status": status,
        "metrics": {
            "processing_seconds": processing_seconds
        },
        "stages": stage_reports,
        "extracted_data": last_output
    }