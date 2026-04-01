"""
NHANES cycle → file mapping.

Handles all naming conventions across CDC survey cycles 1999-2023:
  - 1999-2000: LAB prefix (no suffix)
  - 2001-2002: L-prefix with _B suffix
  - 2003-2004: L-prefix with _C suffix
  - 2005-2014: Standard names (BIOPRO, CBC, etc.) with _D–_H suffixes
  - 2015-2016: Standard names with _I suffix; HSCRP replaces CRP
  - 2017-2018: Standard names with _J suffix
  - 2017-2020:  P_ prefix (pre-pandemic, superset of 2017-2018)
  - 2021-2023: Standard names with _L suffix
"""

NHANES_FILES_BASE = "https://wwwn.cdc.gov/Nchs/Data/Nhanes/Public"

# Maps cycle label -> (begin_year_for_url, [xpt_filenames])
# Files listed: BIOPRO, CBC, MCQ, TRIGLY, CRP/HSCRP, HDL, GHB, DEMO
# (CRP missing for 2011-2014 cycles — not collected those years)
CYCLE_FILES: dict[str, tuple[str, list[str]]] = {
    "1999-2000": ("1999", [
        "LAB18.xpt",   # Standard Biochemistry Profile
        "LAB25.xpt",   # Complete Blood Count
        "MCQ.xpt",     # Medical Conditions
        "LAB13AM.xpt", # Triglycerides
        "LAB11.xpt",   # C-Reactive Protein
        "LAB13.xpt",   # Cholesterol - Total & HDL
        "LAB10.xpt",   # Glycohemoglobin
        "DEMO.xpt",    # Demographics
    ]),
    "2001-2002": ("2001", [
        "L40_B.xpt", "L25_B.xpt",   "MCQ_B.xpt",
        "L13AM_B.xpt", "L11_B.xpt", "L13_B.xpt",
        "L10_B.xpt", "DEMO_B.xpt",
    ]),
    "2003-2004": ("2003", [
        "L40_C.xpt", "L25_C.xpt",   "MCQ_C.xpt",
        "L13AM_C.xpt", "L11_C.xpt", "L13_C.xpt",
        "L10_C.xpt", "DEMO_C.xpt",
    ]),
    "2005-2006": ("2005", [
        "BIOPRO_D.xpt", "CBC_D.xpt", "MCQ_D.xpt",
        "TRIGLY_D.xpt", "CRP_D.xpt", "HDL_D.xpt",
        "GHB_D.xpt",    "DEMO_D.xpt",
    ]),
    "2007-2008": ("2007", [
        "BIOPRO_E.xpt", "CBC_E.xpt", "MCQ_E.xpt",
        "TRIGLY_E.xpt", "CRP_E.xpt", "HDL_E.xpt",
        "GHB_E.xpt",    "DEMO_E.xpt",
    ]),
    "2009-2010": ("2009", [
        "BIOPRO_F.xpt", "CBC_F.xpt", "MCQ_F.xpt",
        "TRIGLY_F.xpt", "CRP_F.xpt", "HDL_F.xpt",
        "GHB_F.xpt",    "DEMO_F.xpt",
    ]),
    "2011-2012": ("2011", [
        "BIOPRO_G.xpt", "CBC_G.xpt", "MCQ_G.xpt",
        "TRIGLY_G.xpt",              "HDL_G.xpt",  # No CRP this cycle
        "GHB_G.xpt",    "DEMO_G.xpt",
    ]),
    "2013-2014": ("2013", [
        "BIOPRO_H.xpt", "CBC_H.xpt", "MCQ_H.xpt",
        "TRIGLY_H.xpt",              "HDL_H.xpt",  # No CRP this cycle
        "GHB_H.xpt",    "DEMO_H.xpt",
    ]),
    "2015-2016": ("2015", [
        "BIOPRO_I.xpt", "CBC_I.xpt",   "MCQ_I.xpt",
        "TRIGLY_I.xpt", "HSCRP_I.xpt", "HDL_I.xpt",
        "GHB_I.xpt",    "DEMO_I.xpt",
    ]),
    "2017-2018": ("2017", [
        "BIOPRO_J.xpt", "CBC_J.xpt",   "MCQ_J.xpt",
        "TRIGLY_J.xpt", "HSCRP_J.xpt", "HDL_J.xpt",
        "GHB_J.xpt",    "DEMO_J.xpt",
    ]),
    "2017-2020": ("2017", [        # Pre-pandemic — superset of 2017-2018
        "P_BIOPRO.xpt", "P_CBC.xpt",   "P_MCQ.xpt",
        "P_TRIGLY.xpt", "P_HSCRP.xpt", "P_HDL.xpt",
        "P_GHB.xpt",    "P_DEMO.xpt",
    ]),
    "2021-2023": ("2021", [
        "BIOPRO_L.xpt", "CBC_L.xpt",   "MCQ_L.xpt",
        "TRIGLY_L.xpt", "HSCRP_L.xpt", "HDL_L.xpt",
        "GHB_L.xpt",    "DEMO_L.xpt",
    ]),
}

# Column renames to normalize variable names across cycles
COLUMN_RENAMES = {
    "LBXTLG":  "LBXTR",     # Triglycerides: 2021+ name → historic name
    "LBXCRP":  "LBXHSCRP",  # CRP: old name → standardized hsCRP column
}

AVAILABLE_CYCLES = list(CYCLE_FILES.keys())


def cycles_in_range(start: str, end: str) -> list[str]:
    """
    Return all cycle labels whose begin year falls within [start_year, end_year].

    Args:
        start: Begin year of range, e.g. "1999" or "1999-2000"
        end:   End year of range, e.g. "2020" or "2017-2020"

    Examples:
        cycles_in_range("2003", "2016") -> ["2003-2004", ..., "2015-2016"]
        cycles_in_range("1999-2000", "2017-2020") -> all cycles 1999-2020
    """
    start_yr = int(start.split("-")[0])
    end_yr   = int(end.split("-")[0])

    # When range includes both 2017-2018 and 2017-2020, prefer 2017-2020
    result = []
    has_2017_2020 = False
    for label in AVAILABLE_CYCLES:
        cycle_yr = int(label.split("-")[0])
        if start_yr <= cycle_yr <= end_yr:
            if label == "2017-2020":
                has_2017_2020 = True
            result.append(label)

    if has_2017_2020 and "2017-2018" in result:
        result.remove("2017-2018")

    return result
