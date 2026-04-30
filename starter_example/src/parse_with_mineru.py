"""Parse step for the offline starter.

Formal projects can replace this with MinerU API output normalization. The
starter copies a tiny parsed-text sample into the standard workflow path.
"""

from __future__ import annotations

import argparse

try:
    from .common import apply_limit, read_jsonl, read_yaml, write_jsonl
except ImportError:
    from common import apply_limit, read_jsonl, read_yaml, write_jsonl


def parse_docs(config_path: str, limit: int | None = None) -> list[dict]:
    config = read_yaml(config_path)
    paths = config["paths"]
    records = apply_limit(read_jsonl(paths["parsed_sample"]), limit)
    write_jsonl(paths["parsed_docs"], records)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy offline parsed sample to workflow input.")
    parser.add_argument("--config", default="configs/workflow.yaml")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    records = parse_docs(args.config, args.limit)
    print(f"Prepared parsed docs={len(records)}.")


if __name__ == "__main__":
    main()

