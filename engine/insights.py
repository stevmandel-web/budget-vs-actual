"""
Rule-based insight generator.
Analyzes variance data and produces actionable insights with severity levels.
"""
from config import VARIANCE_ALERT_PCT, VARIANCE_CRITICAL_PCT, TOP_N_VARIANCES


def _fmt_dollars(val):
    """Format a dollar amount for display."""
    if val is None:
        return "$0"
    abs_val = abs(val)
    if abs_val >= 1_000_000:
        return f"${abs_val / 1_000_000:.1f}M"
    elif abs_val >= 1_000:
        return f"${abs_val / 1_000:.0f}K"
    else:
        return f"${abs_val:.0f}"


def _fmt_pct(val):
    """Format a percentage for display."""
    if val is None:
        return "0%"
    return f"{val * 100:.1f}%"


def generate_insights(wholeco_variance, home_variance=None, clinic_variance=None, has_budget=True):
    """
    Generate key insights from variance data.

    Args:
        wholeco_variance: list of variance row dicts from compute_variance()
        home_variance: optional segment variance rows
        clinic_variance: optional segment variance rows
        has_budget: if False, skip budget comparisons and show actuals-only summaries

    Returns: list of insight dicts:
        [{
            "severity": "critical" | "warning" | "positive" | "info",
            "category": "Revenue" | "Expenses" | "Profitability" | ...,
            "insight": "...",
            "dollar_impact": 12345.0,
            "action": "...",
        }, ...]
    """
    if not has_budget:
        return _generate_actuals_only_insights(wholeco_variance, home_variance, clinic_variance)

    return _generate_budget_insights(wholeco_variance, home_variance, clinic_variance)


def _generate_actuals_only_insights(wholeco_variance, home_variance=None, clinic_variance=None):
    """Generate insights when no budget is available (Oct/Nov/Dec 2025)."""
    insights = []
    row_lookup = {r["label"]: r for r in wholeco_variance
                  if r["row_type"] not in ("header", "blank") and r["label"]}

    # ── 1. EBITDA performance summary ─────────────────────────────────
    ebitda = row_lookup.get("EBITDA", {})
    rev_for_pct = row_lookup.get("Total Revenue", {}).get("actual", 0)
    if ebitda.get("actual") is not None:
        act = ebitda["actual"]
        ebitda_margin = act / rev_for_pct if rev_for_pct else 0
        sev = "positive" if act > 0 else "warning"
        insights.append({
            "severity": sev,
            "category": "Profitability",
            "insight": f"EBITDA was {_fmt_dollars(act)} ({_fmt_pct(ebitda_margin)} margin) — no budget comparison available",
            "dollar_impact": act,
            "action": "Compare to prior months for trend analysis",
        })

    # ── 2. Revenue summary ────────────────────────────────────────────
    total_rev = row_lookup.get("Total Revenue", {})
    if total_rev.get("actual"):
        act = total_rev["actual"]
        insights.append({
            "severity": "info",
            "category": "Revenue",
            "insight": f"Total Revenue was {_fmt_dollars(act)}",
            "dollar_impact": act,
            "action": "Track month-over-month trend",
        })

    # ── 3. Gross Margin summary ───────────────────────────────────────
    gp = row_lookup.get("Gross Profit", {})
    rev = row_lookup.get("Total Revenue", {})
    if gp.get("actual") and rev.get("actual") and rev["actual"] != 0:
        actual_margin = gp["actual"] / rev["actual"]
        sev = "positive" if actual_margin > 0.55 else ("warning" if actual_margin > 0.45 else "critical")
        insights.append({
            "severity": sev,
            "category": "Profitability",
            "insight": f"Gross Margin was {_fmt_pct(actual_margin)} (Gross Profit {_fmt_dollars(gp['actual'])})",
            "dollar_impact": gp["actual"],
            "action": "Monitor COGS trends and wage rates",
        })

    # ── 4. Revenue breakdown ──────────────────────────────────────────
    bt_rev = row_lookup.get("BT Revenue", {})
    bcba_rev_sup = row_lookup.get("BCBA Supervision Revenue", {})
    if bt_rev.get("actual") and rev.get("actual") and rev["actual"] != 0:
        bt_pct = bt_rev["actual"] / rev["actual"]
        insights.append({
            "severity": "info",
            "category": "Revenue",
            "insight": f"BT Revenue was {_fmt_dollars(bt_rev['actual'])} ({_fmt_pct(bt_pct)} of total)",
            "dollar_impact": bt_rev["actual"],
            "action": "Track BT revenue mix over time",
        })

    # ── 5. Segment comparison ─────────────────────────────────────────
    if home_variance and clinic_variance:
        home_lookup = {r["label"]: r for r in home_variance}
        clinic_lookup = {r["label"]: r for r in clinic_variance}
        home_ebitda = home_lookup.get("EBITDA", {})
        clinic_ebitda = clinic_lookup.get("EBITDA", {})

        if home_ebitda.get("actual") is not None:
            h_act = home_ebitda["actual"]
            h_rev = home_lookup.get("Total Revenue", {}).get("actual", 0)
            h_margin = h_act / h_rev if h_rev else 0
            insights.append({
                "severity": "positive" if h_act > 0 else "warning",
                "category": "Segments",
                "insight": f"Home segment EBITDA was {_fmt_dollars(h_act)} ({_fmt_pct(h_margin)} margin)",
                "dollar_impact": h_act,
                "action": "Track Home segment profitability trend",
            })

        if clinic_ebitda.get("actual") is not None:
            c_act = clinic_ebitda["actual"]
            c_rev = clinic_lookup.get("Total Revenue", {}).get("actual", 0)
            c_margin = c_act / c_rev if c_rev else 0
            insights.append({
                "severity": "positive" if c_act > 0 else "warning",
                "category": "Segments",
                "insight": f"Clinic segment EBITDA was {_fmt_dollars(c_act)} ({_fmt_pct(c_margin)} margin)",
                "dollar_impact": c_act,
                "action": "Monitor clinic ramp-up progress",
            })

    # ── 6. Expense summary ────────────────────────────────────────────
    total_exp = row_lookup.get("Total Expenses", {})
    if total_exp.get("actual"):
        insights.append({
            "severity": "info",
            "category": "Expenses",
            "insight": f"Total Operating Expenses were {_fmt_dollars(total_exp['actual'])}",
            "dollar_impact": total_exp["actual"],
            "action": "Compare to prior months for cost control trends",
        })

    # Sort: critical first, then warning, then positive, then info
    severity_order = {"critical": 0, "warning": 1, "positive": 2, "info": 3}
    insights.sort(key=lambda x: (severity_order.get(x["severity"], 99), -abs(x.get("dollar_impact", 0))))

    return insights


def _generate_budget_insights(wholeco_variance, home_variance=None, clinic_variance=None):
    """Generate insights when budget is available (standard budget vs actual)."""
    insights = []
    row_lookup = {r["label"]: r for r in wholeco_variance
                  if r["row_type"] not in ("header", "blank") and r["label"]}

    # ── 1. Overall EBITDA performance ───────────────────────────────────
    ebitda = row_lookup.get("EBITDA", {})
    rev_act = row_lookup.get("Total Revenue", {}).get("actual", 0)
    rev_bud = row_lookup.get("Total Revenue", {}).get("budget", 0)
    if ebitda.get("budget") and ebitda.get("actual") is not None:
        bud = ebitda["budget"]
        act = ebitda["actual"]
        var = ebitda["dollar_var"]
        pct = ebitda["pct_var"]
        ebitda_margin_act = act / rev_act if rev_act else 0
        ebitda_margin_bud = bud / rev_bud if rev_bud else 0
        margin_str = f" | Margin {_fmt_pct(ebitda_margin_act)} vs {_fmt_pct(ebitda_margin_bud)} budget"
        if ebitda["favorable"]:
            insights.append({
                "severity": "positive",
                "category": "Profitability",
                "insight": f"EBITDA of {_fmt_dollars(act)} exceeded budget of {_fmt_dollars(bud)} by {_fmt_dollars(var)} ({_fmt_pct(pct)}){margin_str}",
                "dollar_impact": var,
                "action": "Strong performance — identify drivers to sustain",
            })
        else:
            sev = "critical" if abs(pct) > VARIANCE_CRITICAL_PCT else "warning"
            insights.append({
                "severity": sev,
                "category": "Profitability",
                "insight": f"EBITDA of {_fmt_dollars(act)} missed budget of {_fmt_dollars(bud)} by {_fmt_dollars(abs(var))} ({_fmt_pct(pct)}){margin_str}",
                "dollar_impact": var,
                "action": "Investigate root causes across revenue and expense lines",
            })

    # ── 2. Revenue performance ──────────────────────────────────────────
    total_rev = row_lookup.get("Total Revenue", {})
    if total_rev.get("budget"):
        var = total_rev.get("dollar_var", 0)
        pct = total_rev.get("pct_var", 0)
        if total_rev["favorable"]:
            insights.append({
                "severity": "positive",
                "category": "Revenue",
                "insight": f"Total Revenue of {_fmt_dollars(total_rev['actual'])} beat budget by {_fmt_dollars(var)} ({_fmt_pct(pct)})",
                "dollar_impact": var,
                "action": "Analyze which revenue streams drove the upside",
            })
        else:
            sev = "critical" if abs(pct) > VARIANCE_ALERT_PCT else "warning"
            insights.append({
                "severity": sev,
                "category": "Revenue",
                "insight": f"Total Revenue of {_fmt_dollars(total_rev['actual'])} missed budget by {_fmt_dollars(abs(var))} ({_fmt_pct(abs(pct))})",
                "dollar_impact": var,
                "action": "Review client pipeline and billing utilization",
            })

    # ── 3. Gross Margin analysis ────────────────────────────────────────
    gp = row_lookup.get("Gross Profit", {})
    rev = row_lookup.get("Total Revenue", {})
    if gp.get("actual") and rev.get("actual") and rev["actual"] != 0:
        actual_margin = gp["actual"] / rev["actual"]
        budget_margin = gp["budget"] / rev["budget"] if rev.get("budget") and rev["budget"] != 0 else 0
        margin_diff = actual_margin - budget_margin
        if abs(margin_diff) > 0.02:  # >2pp difference
            direction = "above" if margin_diff > 0 else "below"
            sev = "positive" if margin_diff > 0 else "warning"
            insights.append({
                "severity": sev,
                "category": "Profitability",
                "insight": f"Gross Margin of {_fmt_pct(actual_margin)} is {abs(margin_diff)*100:.1f}pp {direction} budget ({_fmt_pct(budget_margin)})",
                "dollar_impact": gp.get("dollar_var", 0),
                "action": "Review COGS mix — wage rates, utilization, and bonus spending",
            })

    # ── 4. Top unfavorable variances ────────────────────────────────────
    # Exclude wage items — budget wage data is known to be inaccurate
    EXCLUDE_LABELS = {"BT Wages", "BCBA Wages", "BT Bonus", "BCBA Performance Bonus", "BCBA Sign-On Bonus"}
    line_items = [r for r in wholeco_variance
                  if r["row_type"] == "item" and r["dollar_var"] is not None
                  and not r["favorable"] and r["dollar_var"] != 0
                  and r["label"] not in EXCLUDE_LABELS]
    # Sort by absolute dollar variance (worst first)
    unfavorable = sorted(line_items, key=lambda x: abs(x["dollar_var"]), reverse=True)
    for item in unfavorable[:TOP_N_VARIANCES]:
        pct = abs(item["pct_var"])
        sev = "critical" if pct > VARIANCE_CRITICAL_PCT else "warning"
        if item["is_revenue_like"]:
            desc = f"below budget by {_fmt_dollars(abs(item['dollar_var']))}"
        else:
            desc = f"over budget by {_fmt_dollars(abs(item['dollar_var']))}"
        insights.append({
            "severity": sev,
            "category": "Expenses" if not item["is_revenue_like"] else "Revenue",
            "insight": f"{item['label']} is {desc} ({_fmt_pct(pct)})",
            "dollar_impact": item["dollar_var"],
            "action": f"Review {item['label']} drivers and run-rate implications",
        })

    # ── 5. Top favorable variances ──────────────────────────────────────
    favorable = [r for r in wholeco_variance
                 if r["row_type"] == "item" and r["dollar_var"] is not None
                 and r["favorable"] and r["dollar_var"] != 0
                 and r["label"] not in EXCLUDE_LABELS]
    favorable_sorted = sorted(favorable, key=lambda x: abs(x["dollar_var"]), reverse=True)
    for item in favorable_sorted[:3]:
        if item["is_revenue_like"]:
            desc = f"above budget by {_fmt_dollars(abs(item['dollar_var']))}"
        else:
            desc = f"under budget by {_fmt_dollars(abs(item['dollar_var']))}"
        insights.append({
            "severity": "positive",
            "category": "Expenses" if not item["is_revenue_like"] else "Revenue",
            "insight": f"{item['label']} is {desc} ({_fmt_pct(abs(item['pct_var']))})",
            "dollar_impact": item["dollar_var"],
            "action": f"Validate if {item['label']} savings are sustainable or timing-related",
        })

    # ── 6. Segment comparison (Home vs Clinic) ──────────────────────────
    if home_variance and clinic_variance:
        home_lookup = {r["label"]: r for r in home_variance}
        clinic_lookup = {r["label"]: r for r in clinic_variance}
        home_ebitda = home_lookup.get("EBITDA", {})
        clinic_ebitda = clinic_lookup.get("EBITDA", {})

        if home_ebitda.get("budget") is not None and home_ebitda.get("actual") is not None:
            hvar = home_ebitda.get("dollar_var", 0)
            h_rev = home_lookup.get("Total Revenue", {}).get("actual", 0)
            h_margin = home_ebitda["actual"] / h_rev if h_rev else 0
            h_margin_str = f" ({_fmt_pct(h_margin)} margin)"
            if home_ebitda.get("favorable"):
                insights.append({
                    "severity": "positive",
                    "category": "Segments",
                    "insight": f"Home segment EBITDA beat budget by {_fmt_dollars(hvar)}{h_margin_str}",
                    "dollar_impact": hvar,
                    "action": "Home segment driving outperformance",
                })
            elif hvar != 0:
                insights.append({
                    "severity": "warning",
                    "category": "Segments",
                    "insight": f"Home segment EBITDA missed budget by {_fmt_dollars(abs(hvar))}{h_margin_str}",
                    "dollar_impact": hvar,
                    "action": "Investigate Home segment underperformance",
                })

        if clinic_ebitda.get("budget") is not None and clinic_ebitda.get("actual") is not None:
            cvar = clinic_ebitda.get("dollar_var", 0)
            c_rev = clinic_lookup.get("Total Revenue", {}).get("actual", 0)
            c_margin = clinic_ebitda["actual"] / c_rev if c_rev else 0
            c_margin_str = f" ({_fmt_pct(c_margin)} margin)"
            if clinic_ebitda.get("favorable"):
                insights.append({
                    "severity": "positive",
                    "category": "Segments",
                    "insight": f"Clinic segment EBITDA beat budget by {_fmt_dollars(cvar)}{c_margin_str}",
                    "dollar_impact": cvar,
                    "action": "Clinic expansion on track",
                })
            elif cvar != 0:
                insights.append({
                    "severity": "warning",
                    "category": "Segments",
                    "insight": f"Clinic segment EBITDA missed budget by {_fmt_dollars(abs(cvar))}{c_margin_str}",
                    "dollar_impact": cvar,
                    "action": "Review clinic ramp-up pace and census targets",
                })

    # ── 7. Expense control summary ──────────────────────────────────────
    total_exp = row_lookup.get("Total Expenses", {})
    if total_exp.get("budget"):
        var = total_exp.get("dollar_var", 0)
        pct = total_exp.get("pct_var", 0)
        if total_exp["favorable"]:
            insights.append({
                "severity": "positive",
                "category": "Expenses",
                "insight": f"Total Expenses of {_fmt_dollars(total_exp['actual'])} came in {_fmt_dollars(abs(var))} under budget ({_fmt_pct(abs(pct))})",
                "dollar_impact": var,
                "action": "Good cost discipline — ensure not deferring needed spend",
            })
        else:
            insights.append({
                "severity": "warning",
                "category": "Expenses",
                "insight": f"Total Expenses of {_fmt_dollars(total_exp['actual'])} exceeded budget by {_fmt_dollars(abs(var))} ({_fmt_pct(abs(pct))})",
                "dollar_impact": var,
                "action": "Review expense categories for corrective actions",
            })

    # Sort: critical first, then warning, then positive, then info
    severity_order = {"critical": 0, "warning": 1, "positive": 2, "info": 3}
    insights.sort(key=lambda x: (severity_order.get(x["severity"], 99), -abs(x.get("dollar_impact", 0))))

    return insights
