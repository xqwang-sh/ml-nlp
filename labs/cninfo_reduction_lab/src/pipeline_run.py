from __future__ import annotations

import argparse
from pathlib import Path

from check_dataset import check_dataset
from common import log_event, read_yaml
from crawl_cninfo import crawl
from download_pdfs import download_pdfs
from extract_fields import extract_fields
from parse_docs import parse_docs
from route_sections import route_sections
from validate_results import validate_results


def run_step(step: str, workflow_config: str, crawl_config: str) -> None:
    config = read_yaml(workflow_config)
    log_path = config["paths"]["run_log"]

    try:
        if step == "metadata":
            rows = crawl(crawl_config)
            message = f"metadata rows={len(rows)}"
        elif step == "download":
            rows, failures = download_pdfs(crawl_config)
            message = f"download rows={len(rows)}, failures={len(failures)}"
        elif step == "audit":
            report = check_dataset(workflow_config)
            message = f"dataset report={report}"
        elif step == "parse":
            records = parse_docs(workflow_config)
            message = f"parsed docs={len(records)}"
        elif step == "route":
            sections = route_sections(workflow_config)
            message = f"sections={len(sections)}"
        elif step == "extract":
            results = extract_fields(workflow_config)
            message = f"extract records={len(results)}"
        elif step == "validate":
            valid, errors = validate_results(workflow_config)
            message = f"valid={len(valid)}, errors={len(errors)}"
        else:
            raise ValueError(f"Unknown step: {step}")
        log_event(log_path, step, "success", message)
        print(f"[{step}] {message}")
    except Exception as exc:
        log_event(log_path, step, "failed", str(exc))
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Week 12-14 demo workflow.")
    parser.add_argument("--step", default="all")
    parser.add_argument("--config", default="configs/workflow.yaml")
    parser.add_argument("--crawl-config", default="configs/crawl.yaml")
    args = parser.parse_args()

    Path("outputs/logs").mkdir(parents=True, exist_ok=True)
    steps = ["metadata", "download", "audit", "parse", "route", "extract", "validate"]
    selected = steps if args.step == "all" else [args.step]
    for step in selected:
        run_step(step, args.config, args.crawl_config)


if __name__ == "__main__":
    main()
