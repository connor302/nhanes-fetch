"""
Core NHANES download and merge logic.
"""

import warnings
from pathlib import Path

import pandas as pd
import requests

from .cycles import CYCLE_FILES, COLUMN_RENAMES, NHANES_FILES_BASE

DEFAULT_CACHE_DIR = Path.home() / ".cache" / "nhanes_fetch"


def _download_xpt(url: str, dest: Path) -> bool:
    """Download one XPT file; return True if successful XPT content received."""
    try:
        r = requests.get(url, stream=True, timeout=120)
        if r.status_code != 200:
            return False
        dest.write_bytes(r.content)
        # Verify it's actually an XPT file (CDC sometimes returns HTML 404 pages)
        if not dest.read_bytes()[:8].startswith(b"HEADER R"):
            dest.unlink(missing_ok=True)
            return False
        return True
    except Exception as e:
        warnings.warn(f"Download failed for {url}: {e}")
        return False


def fetch_cycle(
    cycle_label: str,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    force: bool = False,
    quiet: bool = False,
) -> pd.DataFrame | None:
    """
    Download and merge all XPT files for one NHANES cycle.

    Returns a merged DataFrame (outer join on SEQN) with all available columns,
    or None if no files could be loaded.

    Applies COLUMN_RENAMES to normalize variable names across cycles.
    """
    if cycle_label not in CYCLE_FILES:
        raise ValueError(f"Unknown cycle '{cycle_label}'. Available: {list(CYCLE_FILES)}")

    begin_year, fnames = CYCLE_FILES[cycle_label]
    cycle_dir = cache_dir / cycle_label
    cycle_dir.mkdir(parents=True, exist_ok=True)

    merged = None
    for fname in fnames:
        fpath = cycle_dir / fname
        url = f"{NHANES_FILES_BASE}/{begin_year}/DataFiles/{fname}"

        if not fpath.exists() or force:
            if not quiet:
                print(f"  Downloading {fname} ...", end=" ", flush=True)
            ok = _download_xpt(url, fpath)
            if not quiet:
                print("ok" if ok else "MISSING")

        if not fpath.exists():
            continue

        try:
            df = pd.read_sas(str(fpath), format="xport")
        except Exception as e:
            warnings.warn(f"Failed to read {fpath.name}: {e}")
            continue

        if "SEQN" not in df.columns:
            continue

        if merged is None:
            merged = df
        else:
            overlap = set(merged.columns) & set(df.columns) - {"SEQN"}
            df = df.drop(columns=list(overlap), errors="ignore")
            merged = merged.merge(df, on="SEQN", how="outer")

    if merged is not None:
        merged = merged.rename(
            columns={k: v for k, v in COLUMN_RENAMES.items() if k in merged.columns}
        )
        merged["_cycle"] = cycle_label

    return merged


def fetch(
    cycles: list[str],
    examined_only: bool = True,
    age_min: int = 0,
    age_max: int = 999,
    cache_dir: Path | str = DEFAULT_CACHE_DIR,
    force: bool = False,
    quiet: bool = False,
) -> pd.DataFrame:
    """
    Download and merge NHANES data across multiple cycles.

    Args:
        cycles:        List of cycle labels, e.g. ["2003-2004", "2005-2006"]
        examined_only: If True (default), keep only participants who completed
                       the physical examination (RIDSTATR=2). Drops interview-only
                       participants who have no blood work — critical for lab data.
        age_min:       Minimum age to include (default 0 = no filter)
        age_max:       Maximum age to include (default 999 = no filter)
        cache_dir:     Directory for caching downloaded XPT files
        force:         Re-download even if cached files exist
        quiet:         Suppress download progress messages

    Returns:
        Combined DataFrame across all cycles with a `_cycle` column.
    """
    cache_dir = Path(cache_dir)
    all_dfs = []

    for cycle_label in cycles:
        if not quiet:
            print(f"\nLoading {cycle_label}...")

        df = fetch_cycle(cycle_label, cache_dir=cache_dir, force=force, quiet=quiet)
        if df is None:
            warnings.warn(f"Skipping {cycle_label} — no data loaded")
            continue

        # Keep examined participants only
        if examined_only and "RIDSTATR" in df.columns:
            n_before = len(df)
            df = df[df["RIDSTATR"] == 2.0]
            if not quiet:
                print(f"  Kept {len(df)}/{n_before} examined participants (RIDSTATR=2)")

        # Age filter
        if "RIDAGEYR" in df.columns:
            if age_min > 0:
                df = df[df["RIDAGEYR"] >= age_min]
            if age_max < 999:
                df = df[df["RIDAGEYR"] <= age_max]

        if not quiet:
            print(f"  → {len(df)} records, {len(df.columns)} columns")

        all_dfs.append(df)

    if not all_dfs:
        raise RuntimeError("No cycles could be loaded.")

    combined = pd.concat(all_dfs, ignore_index=True)
    if not quiet:
        print(f"\nTotal: {len(combined)} records across {len(all_dfs)} cycles")
    return combined
