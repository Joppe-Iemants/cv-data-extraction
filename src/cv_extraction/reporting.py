from collections import Counter
from statistics import median


def summarize_timings(durations: list[float]) -> dict:
    return {
        "count": len(durations),
        "minimum": min(durations) if durations else None,
        "median": median(durations) if durations else None,
        "maximum": max(durations) if durations else None
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
        "completed_timing_seconds": summarize_timings(
            completed_durations
        ),
        "failed_timing_seconds": summarize_timings(
            failed_durations
        )
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