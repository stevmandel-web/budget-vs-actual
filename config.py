"""
Configuration for Budget vs Actual P&L tool.
Maps line items, defines P&L structure, column positions, and thresholds.
"""
import os

# ── Cloud deployment detection ──────────────────────────────────────────────
IS_CLOUD = os.environ.get("STREAMLIT_CLOUD", "false").lower() == "true"

# ── File paths (configurable via env vars for cloud deployment) ─────────────
DEFAULT_BUDGET_PATH = os.environ.get(
    "BUDGET_PATH",
    "/Users/stevenmandel/Downloads/MASTER 2026 Budget vBase_3.xlsx"
)
DEFAULT_ACTUALS_PATH = os.environ.get(
    "ACTUALS_PATH",
    "/Users/stevenmandel/Downloads/January Financials.xlsx"
)
DEFAULT_OUTPUT_PATH = os.environ.get(
    "OUTPUT_PATH",
    "/Users/stevenmandel/Downloads/Budget_vs_Actual_Output.xlsx"
)

# ── Budget file is in $000s; multiply by this to get whole dollars ──────────
BUDGET_MULTIPLIER = 1000

# ── Month mapping ───────────────────────────────────────────────────────────
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Budget WholeCo_P&L: columns C-U map to Jun25-Dec26
# We only care about Jan 2026 - Dec 2026 (columns J-U)
BUDGET_WHOLECO_MONTH_COLS = {
    "Jan": "J", "Feb": "K", "Mar": "L", "Apr": "M", "May": "N", "Jun": "O",
    "Jul": "P", "Aug": "Q", "Sep": "R", "Oct": "S", "Nov": "T", "Dec": "U",
}

# Budget Home_P&L and Clinic_P&L: columns C-N = Jan-Dec 2026
BUDGET_SEGMENT_MONTH_COLS = {
    "Jan": "C", "Feb": "D", "Mar": "E", "Apr": "F", "May": "G", "Jun": "H",
    "Jul": "I", "Aug": "J", "Sep": "K", "Oct": "L", "Nov": "M", "Dec": "N",
}

# Budget state sheets (AZ, NC, etc.) use same C-N layout as segments
BUDGET_STATE_MONTH_COLS = BUDGET_SEGMENT_MONTH_COLS

# Actuals: the month columns shift as new months are added.
# In the January file, cols C-F = Oct, Nov, Dec, Jan
# The latest month is always the rightmost data column before the Budget column.
# We auto-detect this in the parser.

# ── P&L Structure ──────────────────────────────────────────────────────────
# Each entry: (label, row_type, is_revenue_like)
#   row_type: "header" = section header, "item" = line item, "subtotal" = subtotal,
#             "total" = major total, "blank" = empty row
#   is_revenue_like: True means favorable = actual > budget (revenue, profit)
#                    False means favorable = actual < budget (expense)

PNL_STRUCTURE = [
    # REVENUE
    ("REVENUE", "header", True),
    ("BT Revenue", "item", True),
    ("BCBA Supervision Revenue", "item", True),
    ("BCBA Assessment Revenue", "item", True),
    ("Other Revenue", "item", True),
    ("Total Revenue", "total", True),
    ("", "blank", None),

    # COGS
    ("COST OF SERVICES", "header", False),
    ("BT Wages", "item", False),
    ("BCBA Wages", "item", False),
    ("BT Bonus", "item", False),
    ("BCBA Performance Bonus", "item", False),
    ("BCBA Sign-On Bonus", "item", False),
    ("Total COGS", "subtotal", False),
    ("", "blank", None),

    # GROSS PROFIT
    ("Gross Profit", "total", True),
    ("Gross Margin, %", "pct_row", True),
    ("", "blank", None),

    # BILLING
    ("BILLING", "header", False),
    ("Billing Expense", "item", False),
    ("Billing Expense, %", "pct_row", False),
    ("Gross Profit Net Billing", "subtotal", True),
    ("Gross Margin Net Billing, %", "pct_row", True),
    ("", "blank", None),

    # S&M
    ("SALES & MARKETING", "header", False),
    ("Advertising Expense", "item", False),
    ("Marketing Expense", "item", False),
    ("Referrals Expense", "item", False),
    ("Total Sales & Marketing", "subtotal", False),
    ("", "blank", None),

    # STATE OPS
    ("STATE OPERATIONS", "header", False),
    ("State Director Wages", "item", False),
    ("RCD Wages", "item", False),
    ("Clinic Director Wages", "item", False),
    ("Ops Manager Wages", "item", False),
    ("StateOps Bonus", "item", False),
    ("Total StateOps Expense", "subtotal", False),
    ("", "blank", None),

    # CLINIC G&A
    ("CLINIC G&A", "header", False),
    ("Clinic Rent", "item", False),
    ("Clinic Utilities", "item", False),
    ("Other Clinic Expense", "item", False),
    ("Total Clinic G&A", "subtotal", False),
    ("", "blank", None),

    # OTHER G&A
    ("OTHER G&A", "header", False),
    ("Benefits & Insurance", "item", False),
    ("Payroll Expense", "item", False),
    ("Recruiting Expenses", "item", False),
    ("Background Checks", "item", False),
    ("Consulting & Contract", "item", False),
    ("IT & Technology", "item", False),
    ("Dues & Subscriptions", "item", False),
    ("Travel & Entertainment", "item", False),
    ("Supplies", "item", False),
    ("Lobbying", "item", False),
    ("Bad Debt Expense", "item", False),
    ("Other G&A", "item", False),
    ("Other Direct G&A Expense", "subtotal", False),
    ("", "blank", None),

    # CORPORATE
    ("CORPORATE", "header", False),
    ("Corporate Overhead Wages", "item", False),
    ("Corporate Overhead Bonus", "item", False),
    ("Corporate Rent", "item", False),
    ("Corporate Office Expense", "item", False),
    ("Total Corporate Expense", "subtotal", False),
    ("", "blank", None),

    # TOTALS
    ("Total Expenses", "subtotal", False),
    ("", "blank", None),
    ("EBITDA", "total", True),
    ("EBITDA, %", "pct_row", True),
]

# Line items that hold data (excludes headers, blanks, and pct_rows which are computed)
DATA_LINE_ITEMS = [label for label, rtype, _ in PNL_STRUCTURE
                   if rtype in ("item", "subtotal", "total") and label]

# Percentage rows that are computed from other values (not parsed from files)
PCT_ROW_LABELS = [label for label, rtype, _ in PNL_STRUCTURE if rtype == "pct_row"]

# ── Name aliases: actuals name → canonical name ────────────────────────────
# Handles naming differences between budget and actuals files
LINE_ITEM_ALIASES = {
    "Payroll Fees": "Payroll Expense",
    "Payroll fees": "Payroll Expense",
    "BCBA Family Guidance Revenue": "Other Revenue",
    "Case Management Revenue": "Other Revenue",
    "Group Care Revenue": "Other Revenue",
    "Total Cost of Services": "Total COGS",
    "Total Cost of Goods Sold": "Total COGS",
    "Total S&M": "Total Sales & Marketing",
    "Total S & M": "Total Sales & Marketing",
    "Sales & Marketing": "Total Sales & Marketing",
    "Total Sales & Marketing Expense": "Total Sales & Marketing",
    "Total State Ops": "Total StateOps Expense",
    "Total State Operations": "Total StateOps Expense",
    "StateOps": "Total StateOps Expense",
    "Total Clinic": "Total Clinic G&A",
    "Total Clinic G&A Expense": "Total Clinic G&A",
    "Total Other G&A": "Other Direct G&A Expense",
    "Total Other Direct G&A": "Other Direct G&A Expense",
    "Total Corp": "Total Corporate Expense",
    "Total Corporate": "Total Corporate Expense",
    "Corp Overhead Wages": "Corporate Overhead Wages",
    "Corp Overhead Bonus": "Corporate Overhead Bonus",
    "Corporate Bonus": "Corporate Overhead Bonus",
    "Corp Rent": "Corporate Rent",
    "Corp Office Expense": "Corporate Office Expense",
}

# ── Row positions ───────────────────────────────────────────────────────────
# Both budget and actuals are parsed by scanning column B for line item names
# rather than using hardcoded row positions, since row numbers differ across
# sheets and the WholeCo_P&L omits COGS detail entirely.
# since row positions can shift. The parser scans column B for matches.

# ── Actuals sheet column layout ─────────────────────────────────────────────
# The actuals files have a rolling window of months.
# In the January file: C=Oct, D=Nov, E=Dec, F=Jan, (G empty), H=Budget, I=Variance
# The target month column and budget column are detected by the parser.

# ── State lists ─────────────────────────────────────────────────────────────
# States in the actuals StatebyState/January sheet
ACTUALS_STATES = ["AZ", "NC", "GA", "UT", "NM", "Other", "MGMT"]

# Budget home state sheets
BUDGET_HOME_STATES = ["AZ", "NC", "GA", "UT", "NM", "VA", "NV", "CO", "OK"]

# Budget clinic state sheets (suffixed with _)
BUDGET_CLINIC_STATES = ["AZ_", "NC_", "GA_", "UT_", "NM_", "VA_", "MD_", "TX_"]

# ── Insight thresholds ──────────────────────────────────────────────────────
VARIANCE_ALERT_PCT = 0.10       # Flag line items with >10% variance
VARIANCE_CRITICAL_PCT = 0.20    # Critical alert for >20% variance
TOP_N_VARIANCES = 5             # Show top N favorable/unfavorable variances

# ── Working days overrides ────────────────────────────────────────────────────
# Hardcoded official working day counts (takes precedence over budget file values)
# Oct-25, Nov-25, Dec-25 official counts
WORKING_DAYS_OVERRIDES = {
    "Oct": 23,
    "Nov": 18,
    "Dec": 22,
}

# ── Budget year ──────────────────────────────────────────────────────────────
# Budget covers this fiscal year only; actuals from prior years have no budget match
BUDGET_YEAR = 2026

# Clinic names that don't follow the "{STATE}-{City}" naming convention
CLINIC_STATE_OVERRIDES = {
    "Killeen-Clinic": "Other",
}

# ── Raw Data Tab configuration ───────────────────────────────────────────────
DEFAULT_RAW_DATA_PATH = os.environ.get(
    "RAW_DATA_PATH",
    "/Users/stevenmandel/Downloads/Raw Data Tab .xlsx"
)
DEFAULT_MAPPING_PATH = os.environ.get(
    "MAPPING_PATH",
    "/Users/stevenmandel/Downloads/Mapping tab.xlsx"
)

# Raw Data Tab layout
RAW_DATA_SHEET = "Raw Data Tab (2)"
RAW_DATA_START_ROW = 7
RAW_COL_DATE = 2         # B - Transaction date (string "MM/DD/YYYY")
RAW_COL_CUSTOMER = 3     # C - Customer name
RAW_COL_TXN_TYPE = 4     # D - Transaction type
RAW_COL_ACCOUNT = 5      # E - Account full name (GL account)
RAW_COL_ITEM_CLASS = 6   # F - Item class (state/clinic/management)
RAW_COL_AMOUNT = 7       # G - Dollar amount
RAW_COL_FULL_NAME = 8    # H - Account display name
RAW_COL_DIST_TYPE = 9    # I - Distribution account type

# Mapping Tab layout
MAPPING_SHEET = "Mapping"
MAPPING_START_ROW = 3
MAPPING_SIMPLE_GL_COL = 2    # B - Simple GL name
MAPPING_SIMPLE_PNL_COL = 3   # C - Mapped P&L category
MAPPING_HIER_GL_COL = 10     # J - Hierarchical GL code
MAPPING_HIER_PNL_COL = 11    # K - Mapped P&L category
