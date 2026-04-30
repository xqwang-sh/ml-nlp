"""Offline starter metadata step.

The real CNINFO crawler is demonstrated in labs/cninfo_reduction_lab. This
starter keeps a tiny local metadata file so students can learn the workflow
shape before touching live websites.
"""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from .common import apply_limit, read_csv, read_yaml, write_csv
except ImportError:
    from common import apply_limit, read_csv, read_yaml, write_csv


def collect_sample_metadata(config_path: str, limit: int | None = None) -> list[dict]:
    config = read_yaml(config_path)
    metadata_path = Path(config["paths"]["metadata"])
    rows = apply_limit(read_csv(metadata_path), limit)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Load the offline starter metadata sample.")
    parser.add_argument("--config", default="configs/workflow.yaml")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    rows = collect_sample_metadata(args.config, args.limit)
    print(f"Loaded starter metadata rows={len(rows)}. Real CNINFO crawling is shown in labs/.")


if __name__ == "__main__":
    main()
