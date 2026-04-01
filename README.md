# nhanes-fetch

Download and merge NHANES survey cycles into a single DataFrame with one command.

```bash
nhanes-fetch 1999-2020
nhanes-fetch 2003-2020 --age-min 20 --age-max 85 --output adults.parquet
nhanes-fetch 2021-2023 --output val.csv --format csv
```

## Why

The CDC NHANES website restructured its URLs in 2024, breaking most existing NHANES loaders. Variable names also change across survey cycles (e.g. `LAB18` → `BIOPRO_D` → `P_BIOPRO` → `BIOPRO_L` for the same biochemistry profile). This tool handles all of it automatically.

Key features:
- **Auto-resolves filenames** across all cycles 1999–2023 (legacy `LAB*`, `L*_B/C`, standard `BIOPRO_*`, `P_` prefix, `*_L` suffix)
- **Exam-only filter** by default (`RIDSTATR=2`) — drops interview-only participants who have no blood work, preventing garbage imputed values
- **Column normalization** across cycles (e.g. `LBXTLG` → `LBXTR` for triglycerides in 2021+)
- **Automatic caching** of downloaded XPT files to `~/.cache/nhanes_fetch/`
- **Python API** for use in notebooks and pipelines

## Install

```bash
pip install nhanes-fetch
```

Or from source:
```bash
git clone https://github.com/yourusername/nhanes-fetch
cd nhanes-fetch
pip install -e .
```

## CLI usage

```bash
# Download all cycles 1999-2020, save as parquet
nhanes-fetch 1999-2020

# Specify output path and format
nhanes-fetch 2003-2020 --output data.parquet
nhanes-fetch 2003-2020 --output data.csv --format csv

# Filter to adults 20-85
nhanes-fetch 2003-2020 --age-min 20 --age-max 85

# Multiple ranges → separate output files
nhanes-fetch 2003-2020 2021-2023

# Include interview-only participants (not recommended for lab data)
nhanes-fetch 2003-2020 --all-participants

# Force re-download (ignore cache)
nhanes-fetch 2003-2020 --force

# List all available cycles
nhanes-fetch --list-cycles
```

## Python API

```python
import nhanes_fetch as nf

# Fetch a list of specific cycles
df = nf.fetch(["2003-2004", "2005-2006", "2007-2008"])

# Fetch a range of cycles
cycles = nf.cycles_in_range("2003", "2020")
df = nf.fetch(cycles, age_min=20, age_max=85)

# Fetch a single cycle
df = nf.fetch_cycle("2021-2023")

print(df.shape)          # (n_records, n_columns)
print(df["_cycle"].unique())  # cycle labels
print(df["RIDAGEYR"].describe())  # age distribution
```

## Available cycles

| Cycle | Records (approx.) | Notes |
|-------|-------------------|-------|
| 1999-2000 | ~4,400 | LAB prefix filenames |
| 2001-2002 | ~5,000 | L*_B filenames |
| 2003-2004 | ~4,700 | L*_C filenames |
| 2005-2006 | ~4,800 | Standard names (_D) |
| 2007-2008 | ~5,700 | Standard names (_E) |
| 2009-2010 | ~6,100 | Standard names (_F) |
| 2011-2012 | ~5,300 | Standard names (_G), no CRP |
| 2013-2014 | ~5,600 | Standard names (_H), no CRP |
| 2015-2016 | ~5,500 | Standard names (_I), HSCRP |
| 2017-2018 | ~5,000 | Standard names (_J) |
| 2017-2020 | ~8,500 | P_ prefix (pre-pandemic, superset of 2017-2018) |
| 2021-2023 | ~6,000 | Standard names (_L) |

> **Note:** 2017-2018 and 2017-2020 overlap. When fetching a range that includes both, `nhanes-fetch` automatically uses 2017-2020 (the superset) and drops 2017-2018 to avoid double-counting.

## Output columns

The merged DataFrame contains all NHANES variables from the downloaded files, plus a `_cycle` column indicating the source cycle. Key columns include:

- `SEQN` — respondent sequence number
- `RIDAGEYR` — age in years
- `RIAGENDR` — gender (1=male, 2=female)
- `RIDSTATR` — exam status (2=examined, 1=interview-only)
- `LBXGH` — HbA1c / glycohemoglobin
- `LBXMCVSI` — mean cell volume
- `LBXSCR` — creatinine
- ... (hundreds of NHANES variables)

## Caching

Downloaded XPT files are cached to `~/.cache/nhanes_fetch/<cycle>/`. First download of all cycles takes ~5 minutes and ~300MB. Subsequent runs load from cache instantly.

Change the cache location:
```bash
nhanes-fetch 2003-2020 --cache-dir /path/to/cache
```

## License

MIT
