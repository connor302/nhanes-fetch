"""
nhanes-fetch CLI

Usage examples:
  nhanes-fetch 1999-2020                        # all cycles 1999-2020 → parquet
  nhanes-fetch 2003-2020 2021-2023              # two separate outputs
  nhanes-fetch 2003-2020 --output data.csv      # CSV output
  nhanes-fetch 2003-2020 --age-min 20 --age-max 85
  nhanes-fetch 2003-2020 --all-participants      # include interview-only
  nhanes-fetch --list-cycles                    # show available cycles
"""

import argparse
import sys
from pathlib import Path

from .cycles import AVAILABLE_CYCLES, cycles_in_range
from .loader import fetch, DEFAULT_CACHE_DIR


def parse_cycle_arg(arg: str) -> list[str]:
    """
    Parse a cycle argument into a list of cycle labels.

    Accepts:
      "2003-2004"          → exact cycle label
      "2003-2020"          → all cycles with begin year 2003-2020
      "2003"               → cycles starting in 2003
    """
    # Exact match
    if arg in AVAILABLE_CYCLES:
        return [arg]

    # Year range like "2003-2020" — but need to distinguish from cycle label "2003-2004"
    parts = arg.split("-")
    if len(parts) == 2:
        try:
            start_yr, end_yr = int(parts[0]), int(parts[1])
            # If end year > start year + 2, it's a range (e.g. 2003-2020)
            # If end year == start year + 1 or 2, it could be a cycle label
            if end_yr > start_yr + 2:
                return cycles_in_range(str(start_yr), str(end_yr))
            elif arg in AVAILABLE_CYCLES:
                return [arg]
            else:
                return cycles_in_range(str(start_yr), str(end_yr))
        except ValueError:
            pass

    # Single year
    try:
        yr = int(arg)
        return cycles_in_range(str(yr), str(yr))
    except ValueError:
        pass

    raise ValueError(f"Cannot parse cycle argument: '{arg}'. Use a cycle label like '2003-2004' or a range like '2003-2020'.")


def main():
    parser = argparse.ArgumentParser(
        prog="nhanes-fetch",
        description="Download and merge NHANES survey cycles into a single DataFrame.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  nhanes-fetch 1999-2020
  nhanes-fetch 2003-2020 --output adults.parquet
  nhanes-fetch 2021-2023 --output val.csv --format csv
  nhanes-fetch 2003-2020 --age-min 20 --age-max 85
  nhanes-fetch 2003-2020 2021-2023           (two separate files)
  nhanes-fetch --list-cycles
        """,
    )

    parser.add_argument(
        "cycles",
        nargs="*",
        help="Cycle(s) to download. Each can be a label ('2003-2004'), a range "
             "('2003-2020'), or a single year ('2003'). Multiple args produce "
             "separate output files.",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file path. Defaults to nhanes_<cycles>.parquet. "
             "Extension determines format (.parquet or .csv).",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["parquet", "csv"],
        default=None,
        help="Output format (default: inferred from --output extension, or parquet).",
    )
    parser.add_argument(
        "--age-min",
        type=int,
        default=0,
        metavar="AGE",
        help="Minimum age to include (default: no filter).",
    )
    parser.add_argument(
        "--age-max",
        type=int,
        default=999,
        metavar="AGE",
        help="Maximum age to include (default: no filter).",
    )
    parser.add_argument(
        "--all-participants",
        action="store_true",
        help="Include interview-only participants (no blood work). "
             "Default: keep only examined participants (RIDSTATR=2).",
    )
    parser.add_argument(
        "--cache-dir",
        default=str(DEFAULT_CACHE_DIR),
        help=f"Directory for cached XPT files (default: {DEFAULT_CACHE_DIR}).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download files even if cached.",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress output.",
    )
    parser.add_argument(
        "--list-cycles",
        action="store_true",
        help="List all available NHANES cycles and exit.",
    )

    args = parser.parse_args()

    if args.list_cycles:
        print("Available NHANES cycles:")
        for c in AVAILABLE_CYCLES:
            print(f"  {c}")
        sys.exit(0)

    if not args.cycles:
        parser.print_help()
        sys.exit(1)

    # Parse each cycle argument
    cycle_groups = []
    for arg in args.cycles:
        try:
            resolved = parse_cycle_arg(arg)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        cycle_groups.append((arg, resolved))

    # Determine output format
    fmt = args.format
    if fmt is None and args.output:
        ext = Path(args.output).suffix.lower()
        fmt = "csv" if ext == ".csv" else "parquet"
    fmt = fmt or "parquet"

    for original_arg, cycles in cycle_groups:
        if not args.quiet:
            print(f"\n=== Fetching {original_arg} ({len(cycles)} cycle(s)): {cycles} ===")

        df = fetch(
            cycles=cycles,
            examined_only=not args.all_participants,
            age_min=args.age_min,
            age_max=args.age_max,
            cache_dir=args.cache_dir,
            force=args.force,
            quiet=args.quiet,
        )

        # Determine output path
        if args.output and len(cycle_groups) == 1:
            out_path = Path(args.output)
        else:
            slug = original_arg.replace(" ", "_")
            out_path = Path(f"nhanes_{slug}.{fmt}")

        # Write output
        if fmt == "csv":
            df.to_csv(out_path, index=False)
        else:
            df.to_parquet(out_path, index=False)

        print(f"\nSaved {len(df)} records × {len(df.columns)} columns → {out_path}")


if __name__ == "__main__":
    main()
