from collections import Counter
from statistics import median


def summarize_values(values: list) -> dict:
    return {
        "count": len(values),
        "minimum": min(values) if values else None,
        "median": median(values) if values else None,
        "maximum": max(values) if values else None
    }

def summarize_memory(stage_reports: list[dict]) -> dict:
    collection_counts = Counter()
    completed_peaks = []
    failed_peaks = []
    boundary_only_measurements = 0

    for report in stage_reports:
        if report["execution_status"] == "skipped":
            collection_counts["skipped"] += 1
            continue
        memory = report["metrics"].get("memory")

        if memory is None:
            collection_counts["not_recorded"] += 1
            continue

        if not memory.get("enabled", False):
            collection_counts["disabled"] += 1
            continue

        if memory.get("collection_status") != "completed":
            collection_counts["error"] += 1
            continue

        peak = memory.get("sampled_peak_rss_bytes")

        if peak is None:
            collection_counts["invalid"] += 1
            continue

        collection_counts["completed"] += 1

        if memory["sample_count"] <= 2:
            boundary_only_measurements += 1

        if report["execution_status"] == "completed":
            completed_peaks.append(peak)
        elif report["execution_status"] == "error":
            failed_peaks.append(peak)

    return {
        "collection_counts": dict(collection_counts),
        "completed_stage_peak_rss_bytes": summarize_values(
            completed_peaks
        ),
        "failed_stage_peak_rss_bytes": summarize_values(
            failed_peaks
        ),
        "boundary_only_measurements": boundary_only_measurements
    }

def summarize_stage(stage_reports: list[dict]) -> dict:
    completed_durations = [
        report["metrics"]["duration_seconds"]
        for report in stage_reports
        if report["execution_status"] == "completed"
    ]

    failed_durations = [
        report["metrics"]["duration_seconds"]
        for report in stage_reports
        if report["execution_status"] == "error"
    ]

    execution_counts = Counter(
        report["execution_status"]
        for report in stage_reports
    )

    outcome_counts = Counter(
        report["outcome"]
        for report in stage_reports
        if report["outcome"] is not None
    )

    return {
        "method": stage_reports[0]["method"],
        "execution_counts": dict(execution_counts),
        "outcome_counts": dict(outcome_counts),
        "completed_timing_seconds": summarize_values(
            completed_durations
        ),
        "failed_timing_seconds": summarize_values(
            failed_durations
        ),
        "memory": summarize_memory(stage_reports)
    }

def build_document_summaries(reports: list[dict], inputs: list[dict]) -> list[dict]:
    document_summaries = []

    for document in inputs:
        document_reports = [
            report
            for report in reports
            if report["document_id"] == document["id"]
        ]

        stage_names = sorted({
            stage["name"]
            for report in document_reports
            for stage in report["stages"]
        })

        stage_summaries = {}

        for stage_name in stage_names:
            stage_reports = [
                stage
                for report in document_reports
                for stage in report["stages"]
                if stage["name"] == stage_name
            ]

            stage_summaries[stage_name] = summarize_stage(
                stage_reports
            )

        outcomes = Counter(
            report["status"]
            for report in document_reports
        )

        document_summaries.append({
            "document_id": document["id"],
            "attempt_count": len(document_reports),
            "outcome_counts": dict(outcomes),
            "stages": stage_summaries
        })

    return document_summaries