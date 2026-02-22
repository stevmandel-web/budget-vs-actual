"""
Data quality and anomaly detection engine.
Scans parsed data for issues, inconsistencies, and anomalies that suggest
data entry errors or missing information.
"""


def _fmt_dollars(val):
    if val is None:
        return "$0"
    abs_val = abs(val)
    if abs_val >= 1_000_000:
        return f"${abs_val / 1_000_000:.1f}M"
    elif abs_val >= 1_000:
        return f"${abs_val / 1_000:.0f}K"
    else:
        return f"${abs_val:.0f}"


def run_data_quality_checks(
    budget_wholeco, actuals_wholeco,
    budget_home, actuals_home,
    budget_clinic, actuals_clinic,
    actuals_states, actuals_mgmt,
    actuals_clinics_detail, month,
):
    """
    Run comprehensive data quality checks.
    Returns list of issue dicts:
        [{severity, category, issue, detail}, ...]
    """
    issues = []

    def _get_bud(item):
        return budget_wholeco.get(item, {}).get(month, 0)

    def _get_act(item):
        return actuals_wholeco.get(item, 0)

    # ── 1. Revenue sanity checks ────────────────────────────────────────
    total_rev = _get_act("Total Revenue")
    bt_rev = _get_act("BT Revenue")
    bcba_rev = _get_act("BCBA Supervision Revenue")
    assess_rev = _get_act("BCBA Assessment Revenue")
    other_rev = _get_act("Other Revenue")
    computed_rev = bt_rev + bcba_rev + assess_rev + other_rev
    if total_rev and abs(computed_rev - total_rev) > 100:
        issues.append({
            "severity": "warning",
            "category": "Revenue Tie-Out",
            "issue": "Revenue components don't sum to Total Revenue",
            "detail": f"Components sum to {_fmt_dollars(computed_rev)} but Total Revenue = {_fmt_dollars(total_rev)}. Difference: {_fmt_dollars(computed_rev - total_rev)}",
        })

    # ── 2. COGS / Gross Profit tie-out ──────────────────────────────────
    total_cogs = _get_act("Total COGS")
    gp = _get_act("Gross Profit")
    if total_rev and gp:
        implied_cogs = total_rev - gp
        if total_cogs and abs(implied_cogs - total_cogs) > 100:
            issues.append({
                "severity": "warning",
                "category": "COGS Tie-Out",
                "issue": "Total COGS doesn't tie to Revenue - Gross Profit",
                "detail": f"Total COGS = {_fmt_dollars(total_cogs)}, but Revenue ({_fmt_dollars(total_rev)}) - GP ({_fmt_dollars(gp)}) = {_fmt_dollars(implied_cogs)}",
            })

    # ── 3. Segment reconciliation ───────────────────────────────────────
    home_rev = actuals_home.get("Total Revenue", 0)
    clinic_rev = actuals_clinic.get("Total Revenue", 0)
    mgmt_rev = actuals_mgmt.get("Total Revenue", 0) if actuals_mgmt else 0
    segment_total = home_rev + clinic_rev + mgmt_rev
    if total_rev and abs(segment_total - total_rev) > 500:
        issues.append({
            "severity": "critical",
            "category": "Segment Reconciliation",
            "issue": "Home + Clinic + MGMT Revenue doesn't equal WholeCo Revenue",
            "detail": f"Home ({_fmt_dollars(home_rev)}) + Clinic ({_fmt_dollars(clinic_rev)}) + MGMT ({_fmt_dollars(mgmt_rev)}) = {_fmt_dollars(segment_total)} vs WholeCo {_fmt_dollars(total_rev)}",
        })

    # Check EBITDA reconciliation
    home_ebitda = actuals_home.get("EBITDA", 0)
    clinic_ebitda = actuals_clinic.get("EBITDA", 0)
    mgmt_ebitda = actuals_mgmt.get("EBITDA", 0) if actuals_mgmt else 0
    wholeco_ebitda = _get_act("EBITDA")
    segment_ebitda = home_ebitda + clinic_ebitda + mgmt_ebitda
    if wholeco_ebitda and abs(segment_ebitda - wholeco_ebitda) > 500:
        issues.append({
            "severity": "critical",
            "category": "Segment Reconciliation",
            "issue": "Segment EBITDA doesn't reconcile to WholeCo EBITDA",
            "detail": f"Home ({_fmt_dollars(home_ebitda)}) + Clinic ({_fmt_dollars(clinic_ebitda)}) + MGMT ({_fmt_dollars(mgmt_ebitda)}) = {_fmt_dollars(segment_ebitda)} vs WholeCo {_fmt_dollars(wholeco_ebitda)}",
        })

    # ── 4. State-level reconciliation ───────────────────────────────────
    if actuals_states:
        state_rev_total = sum(
            s.get("Total Revenue", 0) for s in actuals_states.values()
        )
        if total_rev and abs(state_rev_total - total_rev) > 1000:
            issues.append({
                "severity": "warning",
                "category": "State Reconciliation",
                "issue": "State-level revenues don't sum to WholeCo",
                "detail": f"State total {_fmt_dollars(state_rev_total)} vs WholeCo {_fmt_dollars(total_rev)}. Difference: {_fmt_dollars(state_rev_total - total_rev)}",
            })

    # ── 5. Clinic detail reconciliation ─────────────────────────────────
    if actuals_clinics_detail:
        clinic_detail_rev = sum(
            c.get("Total Revenue", 0) or c.get("BT Revenue", 0)
            for c in actuals_clinics_detail.values()
        )
        if clinic_rev and abs(clinic_detail_rev - clinic_rev) > 500:
            issues.append({
                "severity": "warning",
                "category": "Clinic Reconciliation",
                "issue": "Individual clinic revenues don't sum to Clinic total",
                "detail": f"Clinic tabs total {_fmt_dollars(clinic_detail_rev)} vs Clinics sheet {_fmt_dollars(clinic_rev)}. Difference: {_fmt_dollars(clinic_detail_rev - clinic_rev)}",
            })

    # ── 5b. BT Wages cross-check: Combined vs sum of sub-tabs ────────
    # Validate that BT Wages on the Combined sheet matches the sum from
    # individual clinic + Home + MGMT sub-tabs
    wholeco_bt = _get_act("BT Wages")
    if wholeco_bt and actuals_clinics_detail:
        subtab_bt = 0
        subtab_detail = []
        # Sum BT Wages from individual clinic tabs
        for cname, cdata in actuals_clinics_detail.items():
            clinic_bt = cdata.get("BT Wages", 0)
            subtab_bt += clinic_bt
            if clinic_bt:
                subtab_detail.append(f"{cname}: {_fmt_dollars(clinic_bt)}")
        # Add Home BT Wages (home-based BT wages not in clinic tabs)
        home_bt = actuals_home.get("BT Wages", 0) if actuals_home else 0
        # Add MGMT BT Wages (should be 0, but check)
        mgmt_bt = actuals_mgmt.get("BT Wages", 0) if actuals_mgmt else 0

        # The Clinics sheet BT Wages should match sum of clinic tabs
        clinics_sheet_bt = actuals_clinic.get("BT Wages", 0) if actuals_clinic else 0
        if clinics_sheet_bt and abs(subtab_bt - clinics_sheet_bt) > 500:
            issues.append({
                "severity": "warning",
                "category": "BT Wages Reconciliation",
                "issue": "Clinic sub-tab BT Wages don't match Clinics sheet total",
                "detail": (
                    f"Sum of clinic tabs: {_fmt_dollars(subtab_bt)} vs Clinics sheet: {_fmt_dollars(clinics_sheet_bt)}. "
                    f"Diff: {_fmt_dollars(subtab_bt - clinics_sheet_bt)}. "
                    f"Breakdown: {'; '.join(subtab_detail[:5])}"
                    + (f" (+{len(subtab_detail) - 5} more)" if len(subtab_detail) > 5 else "")
                ),
            })

        # Also check Combined/WholeCo vs segments (Home + Clinic + MGMT)
        segment_bt = home_bt + clinics_sheet_bt + mgmt_bt
        if abs(segment_bt - wholeco_bt) > 500:
            issues.append({
                "severity": "warning",
                "category": "BT Wages Reconciliation",
                "issue": "BT Wages segments don't reconcile to Combined total",
                "detail": (
                    f"Home ({_fmt_dollars(home_bt)}) + Clinics ({_fmt_dollars(clinics_sheet_bt)}) + MGMT ({_fmt_dollars(mgmt_bt)}) = "
                    f"{_fmt_dollars(segment_bt)} vs Combined {_fmt_dollars(wholeco_bt)}. "
                    f"Diff: {_fmt_dollars(segment_bt - wholeco_bt)}"
                ),
            })

        # Per-clinic BT Wages anomaly check: flag any clinic with BT Wages > Revenue
        for cname, cdata in actuals_clinics_detail.items():
            clinic_bt = cdata.get("BT Wages", 0)
            clinic_rev = cdata.get("Total Revenue", 0) or cdata.get("BT Revenue", 0)
            if clinic_bt and clinic_rev and clinic_bt > clinic_rev * 0.80:
                issues.append({
                    "severity": "warning",
                    "category": "BT Wages Anomaly",
                    "issue": f"{cname}: BT Wages are {clinic_bt/clinic_rev:.0%} of revenue",
                    "detail": f"BT Wages: {_fmt_dollars(clinic_bt)}, Revenue: {_fmt_dollars(clinic_rev)}. Unusually high — check for misallocation.",
                })

    # ── 6. Zero-value anomalies ─────────────────────────────────────────
    key_items = [
        ("BT Revenue", True), ("BCBA Supervision Revenue", True),
        ("BT Wages", False), ("BCBA Wages", False),
        ("Billing Expense", False), ("Benefits & Insurance", False),
    ]
    for item, is_rev in key_items:
        act = _get_act(item)
        bud = _get_bud(item)
        if bud > 10000 and act == 0:
            issues.append({
                "severity": "critical",
                "category": "Missing Data",
                "issue": f"{item} is $0 in actuals but budgeted at {_fmt_dollars(bud)}",
                "detail": "This likely indicates missing data in the actuals file rather than a true zero.",
            })
        elif act > 10000 and bud == 0:
            issues.append({
                "severity": "warning",
                "category": "Missing Budget",
                "issue": f"{item} has {_fmt_dollars(act)} actual but $0 budget",
                "detail": "This may indicate a missing budget line or a new/unplanned expense.",
            })

    # ── 7. Extreme variances (>100%) ────────────────────────────────────
    from config import DATA_LINE_ITEMS
    for item in DATA_LINE_ITEMS:
        act = _get_act(item)
        bud = _get_bud(item)
        if bud != 0 and act != 0:
            pct = abs(act - bud) / abs(bud)
            if pct > 1.0:  # >100% variance
                issues.append({
                    "severity": "warning",
                    "category": "Extreme Variance",
                    "issue": f"{item} has {pct:.0%} variance",
                    "detail": f"Actual {_fmt_dollars(act)} vs Budget {_fmt_dollars(bud)}. Variance this large may indicate data issues.",
                })

    # ── 8. Negative values that shouldn't be negative ───────────────────
    revenue_items = ["BT Revenue", "BCBA Supervision Revenue",
                     "BCBA Assessment Revenue", "Other Revenue", "Total Revenue"]
    for item in revenue_items:
        val = _get_act(item)
        if val < -100:  # Allow small rounding negatives
            issues.append({
                "severity": "critical",
                "category": "Negative Revenue",
                "issue": f"{item} is negative ({_fmt_dollars(val)})",
                "detail": "Revenue should never be negative. Check for reversal entries or data errors.",
            })

    # ── 9. Gross margin reasonableness ──────────────────────────────────
    if total_rev and total_rev > 0 and gp:
        gm = gp / total_rev
        if gm < 0.30:
            issues.append({
                "severity": "warning",
                "category": "Margin Check",
                "issue": f"Gross Margin of {gm:.1%} is unusually low for ABA services",
                "detail": "ABA therapy typically has 45-55% gross margins. Check COGS for misclassification.",
            })
        elif gm > 0.75:
            issues.append({
                "severity": "warning",
                "category": "Margin Check",
                "issue": f"Gross Margin of {gm:.1%} is unusually high for ABA services",
                "detail": "Check if some COGS items are missing or misclassified as G&A.",
            })

    # ── 10. State-level anomalies ───────────────────────────────────────
    if actuals_states:
        for state, state_data in actuals_states.items():
            s_rev = state_data.get("Total Revenue", 0)
            s_gp = state_data.get("Gross Profit", 0)
            if s_rev and s_rev > 0 and s_gp:
                s_gm = s_gp / s_rev
                if s_gm < 0.20 or s_gm > 0.80:
                    issues.append({
                        "severity": "warning",
                        "category": "State Anomaly",
                        "issue": f"{state} has unusual Gross Margin of {s_gm:.1%}",
                        "detail": f"{state} Revenue: {_fmt_dollars(s_rev)}, GP: {_fmt_dollars(s_gp)}. Check for data issues.",
                    })

    # Sort: critical first
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    issues.sort(key=lambda x: severity_order.get(x["severity"], 99))

    return issues
