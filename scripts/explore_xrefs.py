"""Print statistics of the cross reference, for a first look at it.

Reads lr_xrefs.csv and prints four tables: the rows and accesses of each
kind; the instructions with the most accesses; the pairs of instruction
and target with the most effective addresses; and the memory pages with
the most accesses. --top N sets how many rows the last three show
(default 5).

Run from the repo root:

    make xrefs-overview

which shows the top 10.
"""

import argparse
from pathlib import Path

import pandas as pd


def explore_xrefs(csv_path: str, top_n: int = 5) -> None:
    """Print cross-reference statistics for a CSV file."""
    if top_n < 1:
        raise ValueError("top_n must be greater than zero.")

    df = pd.read_csv(csv_path)

    print("--- 1. OVERALL DISTRIBUTION ---")
    kind_stats = (
        df.groupby("kind")
        .agg(
            rows=("count", "count"),
            total_accesses=("count", "sum"),
        )
        .sort_values("total_accesses", ascending=False)
    )
    print(kind_stats, "\n")

    print(f"--- 2. TOP {top_n} INSTRUCTION HOTSPOTS ---")
    hotspots = (
        df.groupby("instruction_address")
        .agg(
            total_accesses=("count", "sum"),
            kinds=("kind", "unique"),
        )
        .sort_values("total_accesses", ascending=False)
        .head(top_n)
    )
    print(hotspots, "\n")

    print(f"--- 3. TOP {top_n} INSTRUCTION/TARGET PAIRS BY FAN-OUT ---")
    # Count distinct effective addresses accessed by each instruction/target pair.
    fan_out = (
        df.groupby(["instruction_address", "target"])
        .agg(
            distinct_addresses=("effective_address", "nunique"),
            total_accesses=("count", "sum"),
        )
        .sort_values("distinct_addresses", ascending=False)
        .head(top_n)
    )
    print(fan_out, "\n")

    print(f"--- 4. TOP {top_n} MEMORY PAGES ---")
    # Preserve the original grouping: pad address strings to at least four
    # characters, then use the first two characters as the page identifier.
    df["page"] = df["effective_address"].astype(str).str.zfill(4).str[:2]

    page_stats = (
        df.groupby("page")
        .agg(
            total_accesses=("count", "sum"),
            rows=("count", "count"),
        )
        .sort_values("total_accesses", ascending=False)
        .head(top_n)
    )
    print(page_stats)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Explore cross-reference statistics from a CSV file."
    )
    parser.add_argument(
        "csv_path",
        help="Path to the cross-reference CSV file (absolute or relative).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        metavar="N",
        help="Number of entries to display in each top list (default: 5).",
    )

    args = parser.parse_args()

    if args.top < 1:
        parser.error("--top must be greater than zero.")

    csv_path = Path(args.csv_path).expanduser()
    if not csv_path.is_file():
        parser.error(f"CSV file not found: {csv_path}")

    explore_xrefs(str(csv_path), top_n=args.top)


if __name__ == "__main__":
    main()
