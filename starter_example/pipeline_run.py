from __future__ import annotations

import argparse

from src.check_dataset import check_dataset
from src.common import log_event, read_yaml
from src.crawl_cninfo import collect_sample_metadata
from src.download_pdfs import prepare_sample_pdfs
from src.extract_fields import extract_fields
from src.parse_with_mineru import parse_docs
from src.report_results import generate_report
from src.route_sections import route_sections
from src.validate_results import validate_results


STEP_ORDER = ["collect", "download", "audit", "parse", "route", "extract", "validate", "report"]


def run_step(step: str, config_path: str, limit: int | None = None) -> str:
    config = read_yaml(config_path)
    log_path = config["paths"]["run_log"]
    try:
        if step == "collect":
            rows = collect_sample_metadata(config_path, limit)
            message = f"metadata rows={len(rows)}"
        elif step == "download":
            rows, failures = prepare_sample_pdfs(config_path, limit)
            message = f"sample rows={len(rows)}, failures={len(failures)}"
        elif step == "audit":
            report = check_dataset(config_path)
            message = f"dataset report={report}"
        elif step == "parse":
            records = parse_docs(config_path, limit)
            message = f"parsed docs={len(records)}"
        elif step == "route":
            sections = route_sections(config_path)
            message = f"sections={len(sections)}"
        elif step == "extract":
            results = extract_fields(config_path)
            message = f"extract records={len(results)}"
        elif step == "validate":
            valid, errors = validate_results(config_path)
            message = f"valid={len(valid)}, errors={len(errors)}"
        elif step == "report":
            report = generate_report(config_path)
            message = f"summary report={report}"
        else:
            raise ValueError(f"Unknown step: {step}")
        log_event(log_path, step, "success", message)
        print(f"[{step}] {message}")
        return message
    except Exception as exc:
        log_event(log_path, step, "failed", str(exc))
        raise


def run_workflow(step: str, config_path: str, limit: int | None = None) -> None:
    selected = STEP_ORDER if step == "all" else [step]
    for selected_step in selected:
        run_step(selected_step, config_path, limit)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the offline starter workflow.")
    parser.add_argument("--config", default="configs/workflow.yaml")
    parser.add_argument("--step", default="all")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    run_workflow(args.step, args.config, args.limit)


if __name__ == "__main__":
    main()

