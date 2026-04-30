from __future__ import annotations

import argparse

from pipeline_run import run_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="CNINFO financial text intelligence starter.")
    subparsers = parser.add_subparsers(dest="command")

    commands = ["collect", "download", "audit", "parse", "route", "extract", "validate", "report", "all"]
    for command in commands:
        cmd = subparsers.add_parser(command)
        cmd.add_argument("--config", default="configs/workflow.yaml")
        cmd.add_argument("--limit", type=int, default=None)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return
    run_workflow(args.command, args.config, args.limit)


if __name__ == "__main__":
    main()

