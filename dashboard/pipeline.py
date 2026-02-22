"""
Pipeline: persistence + orchestration for the Streamlit dashboard.
Merges data_store.py + data_pipeline.py into one module.
"""
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from config import MONTHS, WORKING_DAYS_OVERRIDES, ACTUALS_STATES
from parsers.raw_data_parser import parse_raw_data
from parsers.budget_parser import parse_budget
from engine.variance import (
    compute_variance, compute_segment_variance,
    compute_state_variance, build_waterfall,
)
from engine.insights import generate_insights
from engine.margin_analysis import analyze_gross_margin


# ═══════════════════════════════════════════════════════════════════════
# PERSISTENCE
# ═══════════════════════════════════════════════════════════════════════

DATA_DIR = Path(__file__).parent.parent / "data"
MONTHS_DIR = DATA_DIR / "months"
BUDGET_CACHE_PATH = DATA_DIR / "budget_cache.json"

_MONTH_ABBR_TO_NUM = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}
_MONTH_NUM_TO_ABBR = {v: k for k, v in _MONTH_ABBR_TO_NUM.items()}


def _json_serializer(obj):
    if isinstance(obj, (set, frozenset)):
        return list(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _ensure_dirs():
    MONTHS_DIR.mkdir(parents=True, exist_ok=True)


def save_month(month_abbr, year, parsed_data, source_file="", parser_type="raw_data"):
    """Save parsed actuals for one month to JSON."""
    _ensure_dirs()
    month_num = _MONTH_ABBR_TO_NUM.get(month_abbr, 0)
    key = f"{year}-{month_num:02d}"
    payload = {
        "meta": {
            "month": month_abbr,
            "year": year,
            "source_file": source_file,
            "parsed_at": datetime.now().isoformat(),
            "parser": parser_type,
        },
    }
    for k, v in parsed_data.items():
        if k not in ("target_month", "historical", "historical_states"):
            payload[k] = v
    path = MONTHS_DIR / f"{key}.json"
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=_json_serializer)
    return path


def load_month(month_abbr, year):
    """Load parsed actuals for a specific month. Returns None if not found."""
    month_num = _MONTH_ABBR_TO_NUM.get(month_abbr, 0)
    key = f"{year}-{month_num:02d}"
    path = MONTHS_DIR / f"{key}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def list_available_months():
    """Return list of (month_abbr, year) tuples sorted chronologically."""
    _ensure_dirs()
    result = []
    for f in sorted(MONTHS_DIR.glob("*.json")):
        parts = f.stem.split("-")
        if len(parts) == 2:
            try:
                year = int(parts[0])
                month_num = int(parts[1])
                month_abbr = _MONTH_NUM_TO_ABBR.get(month_num)
                if month_abbr:
                    result.append((month_abbr, year))
            except ValueError:
                continue
    return result


def save_budget_cache(budget_data, source_file=""):
    _ensure_dirs()
    payload = {"meta": {"source_file": source_file, "parsed_at": datetime.now().isoformat()}}
    for k, v in budget_data.items():
        payload[k] = v
    with open(BUDGET_CACHE_PATH, "w") as f:
        json.dump(payload, f, indent=2, default=_json_serializer)


def load_budget_cache():
    if not BUDGET_CACHE_PATH.exists():
        return None
    with open(BUDGET_CACHE_PATH) as f:
        return json.load(f)


def clear_budget_cache():
    if BUDGET_CACHE_PATH.exists():
        BUDGET_CACHE_PATH.unlink()


# ═══════════════════════════════════════════════════════════════════════
# PROCESSING
# ═══════════════════════════════════════════════════════════════════════

def _derive_computed_values(data, month, is_budget=True):
    """Derive Total COGS, Total Expenses, Gross Profit Net Billing if missing."""
    def _get(item):
        return data.get(item, {}).get(month, 0) if is_budget else data.get(item, 0)

    def _set(item, val):
        if is_budget:
            if item not in data:
                data[item] = {}
            data[item][month] = val
        else:
            data[item] = val

    revenue = _get("Total Revenue")
    gross_profit = _get("Gross Profit")
    current_cogs = _get("Total COGS")
    if revenue and gross_profit and (current_cogs == 0 or abs(current_cogs - (revenue - gross_profit)) > 1):
        _set("Total COGS", revenue - gross_profit)

    expense_subtotals = [
        "Billing Expense", "Total Sales & Marketing", "Total StateOps Expense",
        "Total Clinic G&A", "Other Direct G&A Expense", "Total Corporate Expense",
    ]
    if _get("Total Expenses") == 0:
        total_exp = sum(_get(item) for item in expense_subtotals)
        if total_exp != 0:
            _set("Total Expenses", total_exp)

    billing = _get("Billing Expense")
    if gross_profit and billing and _get("Gross Profit Net Billing") == 0:
        _set("Gross Profit Net Billing", gross_profit - billing)


def process_raw_data_upload(raw_data_bytes, mapping_path, filename="upload.xlsx"):
    """
    Parse an uploaded Raw Data Tab in ONE pass, extract ALL months, save each.
    Returns: (dict of {month_abbr: parsed_data}, list of unmapped transactions)
    """
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        tmp.write(raw_data_bytes)
        tmp_path = tmp.name

    try:
        # Single-pass: get all months at once
        all_months, unmapped = parse_raw_data(tmp_path, mapping_path, target_month=None)

        saved_months = {}
        for month_abbr, month_data in all_months.items():
            # Derive computed values for each segment
            _derive_computed_values(month_data["wholeco"], month_abbr, is_budget=False)
            _derive_computed_values(month_data["home"], month_abbr, is_budget=False)
            _derive_computed_values(month_data["clinic"], month_abbr, is_budget=False)
            for state_data in month_data.get("states", {}).values():
                _derive_computed_values(state_data, month_abbr, is_budget=False)
            if month_data.get("mgmt"):
                _derive_computed_values(month_data["mgmt"], month_abbr, is_budget=False)
            for clinic_data in month_data.get("clinics_detail", {}).values():
                _derive_computed_values(clinic_data, month_abbr, is_budget=False)

            year = 2025 if month_abbr in ("Oct", "Nov", "Dec") else 2026
            save_month(month_abbr, year, month_data, filename, "raw_data")
            saved_months[month_abbr] = month_data

        return saved_months, unmapped
    finally:
        os.unlink(tmp_path)


@st.cache_data(ttl=3600, show_spinner="Loading budget...")
def ensure_budget_loaded(budget_path):
    """Load budget from cache or parse and cache it."""
    cached = load_budget_cache()
    if cached and "wholeco" in cached:
        return cached

    budget = parse_budget(budget_path)
    for m in MONTHS:
        _derive_computed_values(budget["wholeco"], m, is_budget=True)
        _derive_computed_values(budget["home"], m, is_budget=True)
        _derive_computed_values(budget["clinic"], m, is_budget=True)

    working_days = budget.get("working_days", {})
    for m, wd in WORKING_DAYS_OVERRIDES.items():
        working_days[m] = wd
    budget["working_days"] = working_days

    save_budget_cache(budget, os.path.basename(budget_path))
    return budget


def combine_budget_states(budget):
    """Merge home_states + clinic_states into combined budget states."""
    combined = {}
    for state, data in budget.get("home_states", {}).items():
        combined[state] = dict(data)
    for state, data in budget.get("clinic_states", {}).items():
        if state in combined:
            for item, months_data in data.items():
                if item not in combined[state]:
                    combined[state][item] = months_data
                elif isinstance(months_data, dict) and isinstance(combined[state][item], dict):
                    for m, val in months_data.items():
                        combined[state][item][m] = combined[state][item].get(m, 0) + val
        else:
            combined[state] = dict(data)
    return combined


@st.cache_data(ttl=3600, show_spinner=False)
def compute_month_analysis(_month_abbr, _month_data_json, _budget_json, has_budget=True):
    """
    Run full variance + waterfall + insights for one month.
    Args are JSON strings so Streamlit can hash them for caching.
    has_budget: whether this month has budget data (Oct/Nov/Dec 2025 don't).
    """
    month_abbr = _month_abbr
    month_data = json.loads(_month_data_json)
    budget = json.loads(_budget_json)

    actuals_wholeco = month_data.get("wholeco", {})
    actuals_home = month_data.get("home", {})
    actuals_clinic = month_data.get("clinic", {})
    actuals_states = month_data.get("states", {})

    budget_wholeco = budget.get("wholeco", {})
    budget_home = budget.get("home", {})
    budget_clinic = budget.get("clinic", {})

    wholeco_variance = compute_variance(budget_wholeco, actuals_wholeco, month_abbr)
    segment_variance = compute_segment_variance(
        {"home": budget_home, "clinic": budget_clinic},
        {"home": actuals_home, "clinic": actuals_clinic},
        month_abbr,
    )
    combined_budget_states = combine_budget_states(budget)
    active_states = [s for s in ACTUALS_STATES if s in actuals_states]
    state_variances = compute_state_variance(
        combined_budget_states, actuals_states, month_abbr, active_states
    )
    waterfall = build_waterfall(wholeco_variance)
    home_var = compute_variance(budget_home, actuals_home, month_abbr)
    clinic_var = compute_variance(budget_clinic, actuals_clinic, month_abbr)
    insights = generate_insights(wholeco_variance, home_var, clinic_var, has_budget=has_budget)

    margin_analysis = []
    try:
        margin_analysis = analyze_gross_margin(
            budget_wholeco, actuals_wholeco,
            budget_home, actuals_home,
            budget_clinic, actuals_clinic,
            actuals_states, combined_budget_states,
            month_abbr,
        )
    except Exception:
        pass

    return {
        "wholeco_variance": wholeco_variance,
        "segment_variance": segment_variance,
        "state_variances": state_variances,
        "waterfall": waterfall,
        "insights": insights,
        "margin_analysis": margin_analysis,
        "active_states": active_states,
        "combined_budget_states": combined_budget_states,
        "working_days": budget.get("working_days", {}),
    }


def get_months_in_order(available_months):
    """Sort available months chronologically."""
    month_order = {m: i for i, m in enumerate(MONTHS)}
    sorted_months = sorted(
        available_months,
        key=lambda x: (x[1], month_order.get(x[0], 0))
    )
    return [m for m, y in sorted_months]


# ═══════════════════════════════════════════════════════════════════════
# CONSOLIDATED P&L HELPERS
# ═══════════════════════════════════════════════════════════════════════

def has_budget_for_month(month_abbr, available_months):
    """Return True if this month has corresponding budget data.

    Oct/Nov/Dec are from 2025 and have no budget match.
    Jan+ are from 2026 and match the budget file.
    """
    from config import BUDGET_YEAR
    for m, y in available_months:
        if m == month_abbr:
            return y == BUDGET_YEAR
    return False


def get_clinics_for_state(clinics_detail, state):
    """Return sorted list of clinic names belonging to a state.

    Uses prefix matching: 'AZ-Phoenix' -> state 'AZ'.
    Exception: 'Killeen-Clinic' -> state 'Other' (via CLINIC_STATE_OVERRIDES).
    """
    from config import CLINIC_STATE_OVERRIDES
    result = []
    for clinic_name in sorted(clinics_detail.keys()):
        if clinic_name in CLINIC_STATE_OVERRIDES:
            if CLINIC_STATE_OVERRIDES[clinic_name] == state:
                result.append(clinic_name)
        elif clinic_name.startswith(f"{state}-"):
            result.append(clinic_name)
    return result


def aggregate_clinics(clinics_detail, clinic_names):
    """Sum P&L values across specified clinics into one combined dict.

    Returns: {line_item: summed_value, ...}
    """
    combined = {}
    for name in clinic_names:
        clinic = clinics_detail.get(name, {})
        for item, val in clinic.items():
            if isinstance(val, (int, float)):
                combined[item] = combined.get(item, 0) + val
    return combined


def get_all_months_chronological(available_months):
    """Return list of (month_abbr, year) tuples sorted chronologically."""
    month_order = {m: i for i, m in enumerate(MONTHS)}
    return sorted(available_months, key=lambda x: (x[1], month_order.get(x[0], 0)))


# ═══════════════════════════════════════════════════════════════════════
# MARGIN ANALYSIS HELPERS
# ═══════════════════════════════════════════════════════════════════════

def categorize_margin_items(margin_items):
    """Group margin analysis items by category for rendering.

    Returns dict: {category_name: [items...]}
    Categories: Overall, COGS Detail, Segment Mix, State Detail, Revenue Mix
    """
    cats = {}
    for item in margin_items:
        cat = item.get("category", "Other")
        cats.setdefault(cat, []).append(item)
    return cats


def get_margin_kpis(margin_items):
    """Extract headline KPIs from margin analysis for the KPI card row.

    Returns dict with keys: gm_pct_actual, gm_pct_budget, gm_pct_delta,
    gp_actual, gp_budget, gp_delta, revenue_actual, revenue_budget, revenue_delta
    """
    kpis = {}
    for item in margin_items:
        if item["category"] != "Overall":
            continue
        m = item["metric"]
        if m == "Gross Margin %":
            kpis["gm_pct_actual"] = item["actual_val"]
            kpis["gm_pct_budget"] = item["budget_val"]
            kpis["gm_pct_delta"] = item["variance"]
        elif m == "Gross Profit":
            kpis["gp_actual"] = item["actual_val"]
            kpis["gp_budget"] = item["budget_val"]
            kpis["gp_delta"] = item["variance"]
        elif m == "Revenue":
            kpis["revenue_actual"] = item["actual_val"]
            kpis["revenue_budget"] = item["budget_val"]
            kpis["revenue_delta"] = item["variance"]
        elif m == "Total COGS":
            kpis["cogs_actual"] = item["actual_val"]
            kpis["cogs_budget"] = item["budget_val"]
            kpis["cogs_delta"] = item["variance"]
    return kpis
