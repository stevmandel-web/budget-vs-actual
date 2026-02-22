#!/usr/bin/env python3
"""
Budget vs Actual P&L Report Generator
Reads budget and actuals Excel files, produces a formatted variance report.

Usage:
    python run.py
    python run.py --month Jan
    python run.py --budget path/to/budget.xlsx --actuals path/to/actuals.xlsx --output report.xlsx
"""
import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    DEFAULT_BUDGET_PATH, DEFAULT_ACTUALS_PATH, DEFAULT_OUTPUT_PATH,
    DEFAULT_RAW_DATA_PATH, DEFAULT_MAPPING_PATH,
    ACTUALS_STATES, MONTHS, WORKING_DAYS_OVERRIDES,
)
from parsers.budget_parser import parse_budget
from parsers.actuals_parser import parse_actuals
from engine.variance import (
    compute_variance, compute_segment_variance,
    compute_state_variance, build_waterfall,
)
from engine.insights import generate_insights
from engine.margin_analysis import analyze_gross_margin
from engine.data_quality import run_data_quality_checks
from output.excel_writer import build_output_workbook


def _derive_computed_values(data, month, is_budget=True):
    """
    Derive Total COGS and Total Expenses if not present in the data.
    Budget and actuals sheets sometimes omit these — they can be computed from
    Revenue - Gross Profit (for COGS) and Gross Profit - EBITDA (for Total Expenses).
    """
    def _get(item):
        if is_budget:
            return data.get(item, {}).get(month, 0)
        else:
            return data.get(item, 0)

    def _set(item, val):
        if is_budget:
            if item not in data:
                data[item] = {}
            data[item][month] = val
        else:
            data[item] = val

    # Derive Total COGS = Total Revenue - Gross Profit
    revenue = _get("Total Revenue")
    gross_profit = _get("Gross Profit")
    current_cogs = _get("Total COGS")
    if revenue and gross_profit and (current_cogs == 0 or abs(current_cogs - (revenue - gross_profit)) > 1):
        derived_cogs = revenue - gross_profit
        _set("Total COGS", derived_cogs)

    # Derive Total Expenses = sum of all expense category subtotals
    expense_subtotals = [
        "Billing Expense",
        "Total Sales & Marketing",
        "Total StateOps Expense",
        "Total Clinic G&A",
        "Other Direct G&A Expense",
        "Total Corporate Expense",
    ]
    current_total_exp = _get("Total Expenses")
    if current_total_exp == 0:
        total_exp = sum(_get(item) for item in expense_subtotals)
        if total_exp != 0:
            _set("Total Expenses", total_exp)

    # Derive Gross Profit Net Billing = Gross Profit - Billing Expense
    billing = _get("Billing Expense")
    current_gpnb = _get("Gross Profit Net Billing")
    if gross_profit and billing and current_gpnb == 0:
        _set("Gross Profit Net Billing", gross_profit - billing)


def main():
    parser = argparse.ArgumentParser(description="Budget vs Actual P&L Report Generator")
    parser.add_argument("--budget", default=DEFAULT_BUDGET_PATH,
                        help="Path to budget Excel file")
    parser.add_argument("--actuals", default=DEFAULT_ACTUALS_PATH,
                        help="Path to actuals Excel file")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH,
                        help="Path for output Excel file")
    parser.add_argument("--month", default="Jan",
                        help="Target month (e.g., Jan, Feb, Mar)")
    parser.add_argument("--raw-data", default=None,
                        help="Path to Raw Data Tab Excel file (use instead of --actuals)")
    parser.add_argument("--mapping", default=DEFAULT_MAPPING_PATH,
                        help="Path to Mapping Tab Excel file (used with --raw-data)")
    args = parser.parse_args()

    month = args.month
    print(f"Budget vs Actual Report — {month} 2026")
    print(f"{'='*50}")

    # ── 1. Parse budget ─────────────────────────────────────────────────
    print(f"Reading budget file: {args.budget}")
    budget = parse_budget(args.budget, months=[month])

    budget_wholeco = budget["wholeco"]
    budget_home = budget["home"]
    budget_clinic = budget["clinic"]
    working_days = budget.get("working_days", {})

    # Apply hardcoded working days overrides (official counts)
    for m, wd in WORKING_DAYS_OVERRIDES.items():
        working_days[m] = wd

    # Derive computed values for budget
    _derive_computed_values(budget_wholeco, month, is_budget=True)
    _derive_computed_values(budget_home, month, is_budget=True)
    _derive_computed_values(budget_clinic, month, is_budget=True)

    # Quick sanity check
    rev = budget_wholeco.get("Total Revenue", {}).get(month, 0)
    cogs = budget_wholeco.get("Total COGS", {}).get(month, 0)
    gp = budget_wholeco.get("Gross Profit", {}).get(month, 0)
    print(f"  Budget Total Revenue ({month}): ${rev:,.0f}")
    print(f"  Budget Total COGS ({month}): ${cogs:,.0f}")
    print(f"  Budget Gross Profit ({month}): ${gp:,.0f}")
    if working_days.get(month):
        print(f"  Working Days ({month}): {working_days[month]}")

    # ── 2. Parse actuals ────────────────────────────────────────────────
    unmapped_transactions = []
    if args.raw_data:
        from parsers.raw_data_parser import parse_raw_data
        print(f"Reading raw data: {args.raw_data}")
        print(f"Using mapping: {args.mapping}")
        actuals, unmapped_transactions = parse_raw_data(
            args.raw_data, args.mapping, target_month=month
        )
        if unmapped_transactions:
            from collections import Counter
            acct_counts = Counter(u["account"] for u in unmapped_transactions)
            print(f"  Unmapped accounts ({len(acct_counts)} distinct):")
            for acct, cnt in acct_counts.most_common(10):
                total_amt = sum(u["amount"] for u in unmapped_transactions if u["account"] == acct)
                print(f"    {acct}: {cnt} txns, ${total_amt:,.2f}")
    else:
        print(f"Reading actuals file: {args.actuals}")
        actuals = parse_actuals(args.actuals, target_month=month)

    actuals_wholeco = actuals["wholeco"]
    actuals_home = actuals["home"]
    actuals_clinic = actuals["clinic"]
    actuals_states = actuals["states"]
    actuals_mgmt = actuals.get("mgmt", {})
    actuals_clinics_detail = actuals.get("clinics_detail", {})
    historical = actuals.get("historical", {})

    # Derive computed values for actuals
    _derive_computed_values(actuals_wholeco, month, is_budget=False)
    _derive_computed_values(actuals_home, month, is_budget=False)
    _derive_computed_values(actuals_clinic, month, is_budget=False)
    for state_name, state_data in actuals_states.items():
        _derive_computed_values(state_data, month, is_budget=False)
    if actuals_mgmt:
        _derive_computed_values(actuals_mgmt, month, is_budget=False)

    # Derive computed values for individual clinic actuals
    for clinic_name, clinic_data in actuals_clinics_detail.items():
        _derive_computed_values(clinic_data, month, is_budget=False)

    # Derive computed values for historical months
    for hist_month, hist_data in historical.items():
        _derive_computed_values(hist_data, hist_month, is_budget=False)

    rev_act = actuals_wholeco.get("Total Revenue", 0)
    cogs_act = actuals_wholeco.get("Total COGS", 0)
    gp_act = actuals_wholeco.get("Gross Profit", 0)
    print(f"  Actual Total Revenue ({month}): ${rev_act:,.0f}")
    print(f"  Actual Total COGS ({month}): ${cogs_act:,.0f}")
    print(f"  Actual Gross Profit ({month}): ${gp_act:,.0f}")
    print(f"  MGMT data: {'yes' if actuals_mgmt else 'no'}")
    print(f"  Individual clinics: {len(actuals_clinics_detail)} active")
    print(f"  Historical months: {list(historical.keys())}")

    # ── 3. Compute variances ────────────────────────────────────────────
    print("Computing variances...")

    # WholeCo variance
    wholeco_variance = compute_variance(budget_wholeco, actuals_wholeco, month)

    # Segment variance (Home vs Clinic)
    segment_variance = compute_segment_variance(
        {"home": budget_home, "clinic": budget_clinic},
        {"home": actuals_home, "clinic": actuals_clinic},
        month,
    )

    # State variance — combine budget home + clinic states
    combined_budget_states = {}
    for state, data in budget.get("home_states", {}).items():
        combined_budget_states[state] = data
    for state, data in budget.get("clinic_states", {}).items():
        if state in combined_budget_states:
            for item, months_data in data.items():
                if item not in combined_budget_states[state]:
                    combined_budget_states[state][item] = months_data
                else:
                    for m, val in months_data.items():
                        if m in combined_budget_states[state][item]:
                            combined_budget_states[state][item][m] += val
                        else:
                            combined_budget_states[state][item][m] = val
        else:
            combined_budget_states[state] = data

    active_states = [s for s in ACTUALS_STATES if s in actuals_states]
    state_variances = compute_state_variance(
        combined_budget_states, actuals_states, month, active_states
    )

    # ── 4. Build waterfall ──────────────────────────────────────────────
    waterfall = build_waterfall(wholeco_variance)

    # ── 5. Generate insights ────────────────────────────────────────────
    print("Generating insights...")
    home_var_rows = compute_variance(budget_home, actuals_home, month)
    clinic_var_rows = compute_variance(budget_clinic, actuals_clinic, month)
    insights = generate_insights(wholeco_variance, home_var_rows, clinic_var_rows)

    print(f"  Generated {len(insights)} insights")
    for ins in insights[:5]:
        print(f"    [{ins['severity'].upper()}] {ins['insight']}")

    # ── 6. Gross margin analysis ──────────────────────────────────────
    print("Analyzing gross margin drivers...")
    margin_analysis = analyze_gross_margin(
        budget_wholeco, actuals_wholeco,
        budget_home, actuals_home,
        budget_clinic, actuals_clinic,
        actuals_states, combined_budget_states,
        month,
    )
    print(f"  Generated {len(margin_analysis)} margin analysis items")

    # ── 7. Data quality checks ────────────────────────────────────────
    print("Running data quality checks...")
    data_quality_issues = run_data_quality_checks(
        budget_wholeco, actuals_wholeco,
        budget_home, actuals_home,
        budget_clinic, actuals_clinic,
        actuals_states, actuals_mgmt,
        actuals_clinics_detail, month,
    )
    print(f"  Found {len(data_quality_issues)} data quality issues")
    for iss in data_quality_issues[:3]:
        print(f"    [{iss['severity'].upper()}] {iss['issue']}")

    # ── 8. Prepare historical data for monthly trends ─────────────────
    # Build actuals_by_month from historical data
    actuals_by_month = {}
    for hist_month, hist_data in historical.items():
        actuals_by_month[hist_month] = hist_data
    # Ensure current month is included
    actuals_by_month[month] = actuals_wholeco

    # Determine prior month actuals for MoM
    month_idx = MONTHS.index(month) if month in MONTHS else 0
    # For Jan (idx 0), prior month is Dec (idx 11) from the prior year
    prior_month_name = MONTHS[month_idx - 1]  # Python negative indexing wraps correctly
    prior_month_actuals = None
    if prior_month_name in actuals_by_month:
        prior_month_actuals = actuals_by_month[prior_month_name]

    # ── 9. Prepare MGMT budget data ──────────────────────────────────
    # The MGMT cost center doesn't have a separate budget sheet.
    # Corporate costs in WholeCo budget represent MGMT spending.
    # We extract the corporate/management line items from the WholeCo budget.
    mgmt_budget = {}
    mgmt_budget_items = [
        "Corporate Overhead Wages", "Corporate Overhead Bonus",
        "Corporate Rent", "Corporate Office Expense",
        "Total Corporate Expense",
        "Advertising Expense", "Marketing Expense", "Referrals Expense",
        "Total Sales & Marketing",
        "Benefits & Insurance", "Payroll Expense", "Recruiting Expenses",
        "Background Checks", "Consulting & Contract", "IT & Technology",
        "Dues & Subscriptions", "Travel & Entertainment", "Supplies",
        "Lobbying", "Bad Debt Expense", "Other G&A",
        "Other Direct G&A Expense",
    ]
    for item in mgmt_budget_items:
        if item in budget_wholeco:
            mgmt_budget[item] = budget_wholeco[item]

    # ── 10. Build output workbook ─────────────────────────────────────
    print(f"Writing output: {args.output}")

    # Parse budget for all months (for monthly trends)
    budget_all = parse_budget(args.budget)
    budget_all_wholeco = budget_all["wholeco"]
    for m in MONTHS:
        _derive_computed_values(budget_all_wholeco, m, is_budget=True)

    build_output_workbook(
        wholeco_variance=wholeco_variance,
        segment_variance=segment_variance,
        state_variances=state_variances,
        waterfall=waterfall,
        insights=insights,
        budget_data=budget_all_wholeco,
        actuals_by_month=actuals_by_month,
        months_loaded=list(actuals_by_month.keys()),
        month=month,
        states=active_states,
        output_path=args.output,
        prior_month_actuals=prior_month_actuals,
        working_days=working_days,
        clinics_detail=actuals_clinics_detail,
        mgmt_actuals=actuals_mgmt,
        mgmt_budget=mgmt_budget,
        margin_analysis=margin_analysis,
        data_quality_issues=data_quality_issues,
        unmapped_transactions=unmapped_transactions,
    )

    print(f"\nDone! Output saved to: {args.output}")
    print(f"{'='*50}")

    # Summary
    ebitda_bud = budget_wholeco.get("EBITDA", {}).get(month, 0)
    ebitda_act = actuals_wholeco.get("EBITDA", 0)
    print(f"EBITDA: ${ebitda_act:,.0f} actual vs ${ebitda_bud:,.0f} budget "
          f"(${ebitda_act - ebitda_bud:+,.0f})")


if __name__ == "__main__":
    main()
