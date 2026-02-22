"""
Variance engine: computes $ and % variances between budget and actuals.
Handles favorable/unfavorable classification based on line item type.
Computes percentage rows (Gross Margin %, etc.) from dollar values.
"""
from config import PNL_STRUCTURE, DATA_LINE_ITEMS


def _safe_div(numerator, denominator):
    """Safe division, returns 0 if denominator is 0."""
    if denominator == 0:
        return 0.0
    return numerator / denominator


# Map pct_row labels to their numerator line item and special names
_PCT_ROW_MAP = {
    "Gross Margin, %": "Gross Profit",
    "Gross Margin Net Billing, %": "Gross Profit Net Billing",
}


def _pct_numerator_label(label):
    """Return the numerator line item for a pct_row label.

    Handles special names (Gross Margin → Gross Profit) and the generic
    pattern where 'X, %' → 'X'.
    """
    if label in _PCT_ROW_MAP:
        return _PCT_ROW_MAP[label]
    # Generic: strip ', %' suffix → base line item
    if label.endswith(", %"):
        return label[:-3]
    return label


def _compute_pct_row(label, computed_values):
    """
    Compute a percentage row value based on previously computed dollar values.
    Returns: (budget_pct, actual_pct)
    """
    rev_bud = computed_values.get("Total Revenue", {}).get("budget", 0)
    rev_act = computed_values.get("Total Revenue", {}).get("actual", 0)

    base_label = _pct_numerator_label(label)
    num_bud = computed_values.get(base_label, {}).get("budget", 0)
    num_act = computed_values.get(base_label, {}).get("actual", 0)
    return _safe_div(num_bud, rev_bud), _safe_div(num_act, rev_act)


def compute_variance(budget_data, actuals_data, month):
    """
    Compute variance for each P&L line item.

    Args:
        budget_data: {line_item: {month: value, ...}, ...} (from budget parser)
        actuals_data: {line_item: value, ...} (from actuals parser, single month)
        month: The month string (e.g., "Jan")

    Returns: list of dicts, one per P&L line
    """
    rows = []
    computed = {}  # Track computed values for pct_row lookups

    for label, row_type, is_revenue_like in PNL_STRUCTURE:
        if row_type in ("header", "blank"):
            rows.append({
                "label": label,
                "row_type": row_type,
                "is_revenue_like": is_revenue_like,
                "budget": None,
                "actual": None,
                "dollar_var": None,
                "pct_var": None,
                "favorable": None,
            })
            continue

        if row_type == "pct_row":
            # Compute percentage from previously seen dollar values
            bud_pct, act_pct = _compute_pct_row(label, computed)
            pp_diff = act_pct - bud_pct  # percentage point difference
            favorable = pp_diff >= 0 if is_revenue_like else pp_diff <= 0

            rows.append({
                "label": label,
                "row_type": "pct_row",
                "is_revenue_like": is_revenue_like,
                "budget": bud_pct,
                "actual": act_pct,
                "dollar_var": pp_diff,  # pp difference
                "pct_var": None,
                "favorable": favorable,
            })
            continue

        # Standard dollar row
        budget_val = 0.0
        if label in budget_data and month in budget_data[label]:
            budget_val = budget_data[label][month]

        actual_val = actuals_data.get(label, 0.0)

        dollar_var = actual_val - budget_val
        pct_var = _safe_div(dollar_var, abs(budget_val)) if budget_val != 0 else 0.0

        if is_revenue_like:
            favorable = dollar_var >= 0
        else:
            favorable = dollar_var <= 0

        rows.append({
            "label": label,
            "row_type": row_type,
            "is_revenue_like": is_revenue_like,
            "budget": budget_val,
            "actual": actual_val,
            "dollar_var": dollar_var,
            "pct_var": pct_var,
            "favorable": favorable,
        })

        # Store for pct_row lookups
        computed[label] = {"budget": budget_val, "actual": actual_val}

    return rows


def compute_segment_variance(budget_data, actuals_data, month):
    """
    Compute side-by-side variance for Home and Clinic segments.
    """
    rows = []
    computed = {"home": {}, "clinic": {}}

    for label, row_type, is_revenue_like in PNL_STRUCTURE:
        if row_type in ("header", "blank"):
            rows.append({
                "label": label,
                "row_type": row_type,
                "is_revenue_like": is_revenue_like,
            })
            continue

        entry = {
            "label": label,
            "row_type": row_type,
            "is_revenue_like": is_revenue_like,
        }

        if row_type == "pct_row":
            for seg in ["home", "clinic"]:
                bud_pct, act_pct = _compute_pct_row(label, computed[seg])
                pp_diff = act_pct - bud_pct
                favorable = pp_diff >= 0 if is_revenue_like else pp_diff <= 0
                entry[f"{seg}_budget"] = bud_pct
                entry[f"{seg}_actual"] = act_pct
                entry[f"{seg}_dollar_var"] = pp_diff
                entry[f"{seg}_pct_var"] = None
                entry[f"{seg}_favorable"] = favorable
            rows.append(entry)
            continue

        for seg in ["home", "clinic"]:
            bud = budget_data.get(seg, {})
            act = actuals_data.get(seg, {})

            budget_val = 0.0
            if label in bud and month in bud[label]:
                budget_val = bud[label][month]

            actual_val = act.get(label, 0.0)
            dollar_var = actual_val - budget_val
            pct_var = _safe_div(dollar_var, abs(budget_val)) if budget_val != 0 else 0.0

            if is_revenue_like:
                favorable = dollar_var >= 0
            else:
                favorable = dollar_var <= 0

            entry[f"{seg}_budget"] = budget_val
            entry[f"{seg}_actual"] = actual_val
            entry[f"{seg}_dollar_var"] = dollar_var
            entry[f"{seg}_pct_var"] = pct_var
            entry[f"{seg}_favorable"] = favorable

            computed[seg][label] = {"budget": budget_val, "actual": actual_val}

        rows.append(entry)

    return rows


def compute_state_variance(budget_states, actuals_states, month, states):
    """
    Compute variance for each state.
    """
    result = {}
    for state in states:
        bud = budget_states.get(state, {})
        act = actuals_states.get(state, {})

        rows = []
        computed = {}
        for label, row_type, is_revenue_like in PNL_STRUCTURE:
            if row_type in ("header", "blank"):
                rows.append({
                    "label": label,
                    "row_type": row_type,
                    "is_revenue_like": is_revenue_like,
                    "budget": None,
                    "actual": None,
                    "dollar_var": None,
                    "pct_var": None,
                    "favorable": None,
                })
                continue

            if row_type == "pct_row":
                bud_pct, act_pct = _compute_pct_row(label, computed)
                pp_diff = act_pct - bud_pct
                favorable = pp_diff >= 0 if is_revenue_like else pp_diff <= 0
                rows.append({
                    "label": label,
                    "row_type": "pct_row",
                    "is_revenue_like": is_revenue_like,
                    "budget": bud_pct,
                    "actual": act_pct,
                    "dollar_var": pp_diff,
                    "pct_var": None,
                    "favorable": favorable,
                })
                continue

            budget_val = 0.0
            if label in bud and isinstance(bud[label], dict) and month in bud[label]:
                budget_val = bud[label][month]
            elif label in bud and not isinstance(bud[label], dict):
                budget_val = bud[label]

            actual_val = act.get(label, 0.0)
            dollar_var = actual_val - budget_val
            pct_var = _safe_div(dollar_var, abs(budget_val)) if budget_val != 0 else 0.0

            if is_revenue_like:
                favorable = dollar_var >= 0
            else:
                favorable = dollar_var <= 0

            rows.append({
                "label": label,
                "row_type": row_type,
                "is_revenue_like": is_revenue_like,
                "budget": budget_val,
                "actual": actual_val,
                "dollar_var": dollar_var,
                "pct_var": pct_var,
                "favorable": favorable,
            })

            computed[label] = {"budget": budget_val, "actual": actual_val}

        result[state] = rows

    return result


def build_waterfall(variance_rows):
    """
    Build an EBITDA waterfall bridge from budget to actual.
    Uses subtotal-level variances to ensure the bridge reconciles.

    The bridge is:
        Budget EBITDA
        + Revenue Variance (Total Revenue actual - budget)
        - COGS Variance (Total COGS actual - budget)
        - Billing Variance
        - S&M Variance
        - State Ops Variance
        - Clinic G&A Variance
        - Other G&A Variance
        - Corporate Variance
        = Actual EBITDA
    """
    row_lookup = {r["label"]: r for r in variance_rows
                  if r.get("dollar_var") is not None and r["row_type"] != "pct_row"}

    budget_ebitda = 0
    actual_ebitda = 0
    for row in variance_rows:
        if row["label"] == "EBITDA":
            budget_ebitda = row["budget"] or 0
            actual_ebitda = row["actual"] or 0
            break

    # Use subtotals (which reconcile properly) instead of individual line items
    # Each entry: (display_name, subtotal_label, is_revenue_like)
    bridge_items = [
        ("Revenue", "Total Revenue", True),
        ("COGS", "Total COGS", False),
        ("Billing", "Billing Expense", False),
        ("Sales & Marketing", "Total Sales & Marketing", False),
        ("State Operations", "Total StateOps Expense", False),
        ("Clinic G&A", "Total Clinic G&A", False),
        ("Other G&A", "Other Direct G&A Expense", False),
        ("Corporate", "Total Corporate Expense", False),
    ]

    waterfall = [("Budget EBITDA", budget_ebitda)]

    running_check = budget_ebitda
    for display_name, label, is_revenue_like in bridge_items:
        if label in row_lookup:
            var = row_lookup[label]["dollar_var"]
            # EBITDA impact: revenue variance flows through directly,
            # expense variance flows inversely (lower expense = higher EBITDA)
            impact = var if is_revenue_like else -var
            if impact != 0:
                waterfall.append((display_name, impact))
                running_check += impact

    waterfall.append(("Actual EBITDA", actual_ebitda))

    return waterfall
