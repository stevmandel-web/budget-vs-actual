"""
Gross Margin variance decomposition.
Analyzes what is driving gross margin differences between budget and actual —
wage rates, hours, revenue mix, state mix, etc.
"""


def _safe_div(num, den):
    if den == 0:
        return 0
    return num / den


def _fmt_dollars(val):
    abs_val = abs(val)
    if abs_val >= 1_000_000:
        return f"${abs_val / 1_000_000:.1f}M"
    elif abs_val >= 1_000:
        return f"${abs_val / 1_000:.0f}K"
    else:
        return f"${abs_val:.0f}"


def analyze_gross_margin(
    budget_wholeco, actuals_wholeco,
    budget_home, actuals_home,
    budget_clinic, actuals_clinic,
    actuals_states, combined_budget_states,
    month,
):
    """
    Decompose gross margin variance into drivers.

    Returns list of analysis dicts:
        [{category, metric, budget_val, actual_val, variance, insight}, ...]
    """
    analysis = []

    def _bud(data, item):
        return data.get(item, {}).get(month, 0)

    def _act(data, item):
        return data.get(item, 0)

    # ── 1. Overall Gross Margin Bridge ──────────────────────────────────
    bud_rev = _bud(budget_wholeco, "Total Revenue")
    act_rev = _act(actuals_wholeco, "Total Revenue")
    bud_cogs = _bud(budget_wholeco, "Total COGS")
    act_cogs = _act(actuals_wholeco, "Total COGS")
    bud_gp = _bud(budget_wholeco, "Gross Profit")
    act_gp = _act(actuals_wholeco, "Gross Profit")

    bud_gm = _safe_div(bud_gp, bud_rev)
    act_gm = _safe_div(act_gp, act_rev)

    analysis.append({
        "category": "Overall",
        "metric": "Revenue",
        "budget_val": bud_rev,
        "actual_val": act_rev,
        "variance": act_rev - bud_rev,
        "insight": f"Revenue {'beat' if act_rev >= bud_rev else 'missed'} budget by {_fmt_dollars(abs(act_rev - bud_rev))}",
    })
    analysis.append({
        "category": "Overall",
        "metric": "Total COGS",
        "budget_val": bud_cogs,
        "actual_val": act_cogs,
        "variance": act_cogs - bud_cogs,
        "insight": f"COGS {'over' if act_cogs > bud_cogs else 'under'} budget by {_fmt_dollars(abs(act_cogs - bud_cogs))}",
    })
    analysis.append({
        "category": "Overall",
        "metric": "Gross Profit",
        "budget_val": bud_gp,
        "actual_val": act_gp,
        "variance": act_gp - bud_gp,
        "insight": f"GP {'above' if act_gp >= bud_gp else 'below'} budget by {_fmt_dollars(abs(act_gp - bud_gp))}",
    })
    analysis.append({
        "category": "Overall",
        "metric": "Gross Margin %",
        "budget_val": bud_gm,
        "actual_val": act_gm,
        "variance": act_gm - bud_gm,
        "insight": f"Gross Margin {act_gm:.1%} vs budget {bud_gm:.1%} ({(act_gm - bud_gm)*100:+.1f}pp)",
    })

    # ── 2. COGS Component Breakdown ─────────────────────────────────────
    cogs_items = [
        ("BT Wages", "BT wage cost"),
        ("BCBA Wages", "BCBA wage cost"),
        ("BT Bonus", "BT bonus cost"),
        ("BCBA Performance Bonus", "BCBA bonus cost"),
        ("BCBA Sign-On Bonus", "BCBA sign-on cost"),
    ]
    for item, desc in cogs_items:
        bud_val = _bud(budget_wholeco, item)
        act_val = _act(actuals_wholeco, item)
        if bud_val or act_val:
            var = act_val - bud_val
            # As % of revenue
            bud_pct = _safe_div(bud_val, bud_rev)
            act_pct = _safe_div(act_val, act_rev)
            direction = "higher" if var > 0 else "lower"
            analysis.append({
                "category": "COGS Detail",
                "metric": item,
                "budget_val": bud_val,
                "actual_val": act_val,
                "variance": var,
                "insight": f"{desc} {_fmt_dollars(abs(var))} {direction} than budget ({act_pct:.1%} vs {bud_pct:.1%} of revenue)",
            })

    # ── 3. Segment GM comparison ────────────────────────────────────────
    for seg_name, bud_data, act_data in [
        ("Home", budget_home, actuals_home),
        ("Clinic", budget_clinic, actuals_clinic),
    ]:
        s_bud_rev = _bud(bud_data, "Total Revenue")
        s_act_rev = _act(act_data, "Total Revenue")
        s_bud_gp = _bud(bud_data, "Gross Profit")
        s_act_gp = _act(act_data, "Gross Profit")
        s_bud_gm = _safe_div(s_bud_gp, s_bud_rev)
        s_act_gm = _safe_div(s_act_gp, s_act_rev)

        if s_bud_rev or s_act_rev:
            analysis.append({
                "category": "Segment Mix",
                "metric": f"{seg_name} Revenue",
                "budget_val": s_bud_rev,
                "actual_val": s_act_rev,
                "variance": s_act_rev - s_bud_rev,
                "insight": f"{seg_name} revenue {_fmt_dollars(abs(s_act_rev - s_bud_rev))} {'above' if s_act_rev >= s_bud_rev else 'below'} budget",
            })
            analysis.append({
                "category": "Segment Mix",
                "metric": f"{seg_name} Gross Margin %",
                "budget_val": s_bud_gm,
                "actual_val": s_act_gm,
                "variance": s_act_gm - s_bud_gm,
                "insight": f"{seg_name} GM {s_act_gm:.1%} vs budget {s_bud_gm:.1%} ({(s_act_gm - s_bud_gm)*100:+.1f}pp)",
            })

    # ── 4. State-level GM analysis ──────────────────────────────────────
    if actuals_states and combined_budget_states:
        for state, state_act in actuals_states.items():
            s_act_rev = state_act.get("Total Revenue", 0)
            s_act_gp = state_act.get("Gross Profit", 0)
            if s_act_rev <= 0:
                continue

            state_bud = combined_budget_states.get(state, {})
            s_bud_rev = state_bud.get("Total Revenue", {}).get(month, 0) if isinstance(state_bud.get("Total Revenue"), dict) else state_bud.get("Total Revenue", 0)
            s_bud_gp = state_bud.get("Gross Profit", {}).get(month, 0) if isinstance(state_bud.get("Gross Profit"), dict) else state_bud.get("Gross Profit", 0)

            s_act_gm = _safe_div(s_act_gp, s_act_rev)
            s_bud_gm = _safe_div(s_bud_gp, s_bud_rev) if s_bud_rev else 0
            gm_diff = s_act_gm - s_bud_gm

            if abs(gm_diff) > 0.03:  # >3pp difference worth noting
                direction = "above" if gm_diff > 0 else "below"
                analysis.append({
                    "category": "State Detail",
                    "metric": f"{state} Gross Margin %",
                    "budget_val": s_bud_gm,
                    "actual_val": s_act_gm,
                    "variance": gm_diff,
                    "insight": f"{state} GM {s_act_gm:.1%} is {abs(gm_diff)*100:.1f}pp {direction} budget ({s_bud_gm:.1%}). Rev: {_fmt_dollars(s_act_rev)}",
                })

            # Wage analysis per state
            for wage_item in ["BT Wages", "BCBA Wages"]:
                s_act_wage = state_act.get(wage_item, 0)
                s_bud_wage_data = state_bud.get(wage_item, {})
                s_bud_wage = s_bud_wage_data.get(month, 0) if isinstance(s_bud_wage_data, dict) else s_bud_wage_data
                if s_act_wage and s_bud_wage:
                    wage_var = s_act_wage - s_bud_wage
                    if abs(wage_var) > 5000:
                        analysis.append({
                            "category": "State Detail",
                            "metric": f"{state} {wage_item}",
                            "budget_val": s_bud_wage,
                            "actual_val": s_act_wage,
                            "variance": wage_var,
                            "insight": f"{state} {wage_item}: {_fmt_dollars(abs(wage_var))} {'over' if wage_var > 0 else 'under'} budget",
                        })

    # ── 5. Revenue mix impact ───────────────────────────────────────────
    # BT Revenue has different margin than BCBA Revenue
    bud_bt_pct = _safe_div(_bud(budget_wholeco, "BT Revenue"), bud_rev)
    act_bt_pct = _safe_div(_act(actuals_wholeco, "BT Revenue"), act_rev)
    if abs(act_bt_pct - bud_bt_pct) > 0.01:
        analysis.append({
            "category": "Revenue Mix",
            "metric": "BT Revenue Share",
            "budget_val": bud_bt_pct,
            "actual_val": act_bt_pct,
            "variance": act_bt_pct - bud_bt_pct,
            "insight": f"BT Revenue is {act_bt_pct:.1%} of total vs {bud_bt_pct:.1%} budget ({(act_bt_pct - bud_bt_pct)*100:+.1f}pp). BT has different margin profile than supervision.",
        })

    return analysis


def analyze_service_line_margins(states_data, wholeco_data):
    """
    Compute BT/BCBA margin metrics by state for the Margin Analysis tab.

    Args:
        states_data: dict of {state_abbr: {line_item: value}} from month_data["states"]
        wholeco_data: dict of {line_item: value} from month_data["wholeco"]

    Returns:
        {
            "wholeco": {bt_rev, bt_wages, bt_margin_pct, bcba_rev, bcba_wages,
                        bcba_margin_pct, blended_gm_pct, bcba_leverage, total_rev, gross_profit},
            "states": [
                {state, bt_rev, bt_wages, bt_margin_pct, bcba_rev, bcba_wages,
                 bcba_margin_pct, blended_gm_pct, bcba_leverage, total_rev, gross_profit, dollar_impact},
                ...
            ]  # sorted by dollar_impact descending (best first)
        }
    """
    def _compute_metrics(data):
        bt_rev = data.get("BT Revenue", 0)
        bcba_sup = data.get("BCBA Supervision Revenue", 0)
        bcba_assess = data.get("BCBA Assessment Revenue", 0)
        bcba_rev = bcba_sup + bcba_assess
        bt_wages = data.get("BT Wages", 0)
        bcba_wages = data.get("BCBA Wages", 0)
        total_rev = data.get("Total Revenue", 0)
        gross_profit = data.get("Gross Profit", 0)

        return {
            "bt_rev": bt_rev,
            "bt_wages": bt_wages,
            "bt_margin_pct": _safe_div(bt_rev - bt_wages, bt_rev),
            "bcba_rev": bcba_rev,
            "bcba_wages": bcba_wages,
            "bcba_margin_pct": _safe_div(bcba_rev - bcba_wages, bcba_rev),
            "blended_gm_pct": _safe_div(gross_profit, total_rev),
            "bcba_leverage": _safe_div(bt_rev, bcba_wages),
            "total_rev": total_rev,
            "gross_profit": gross_profit,
        }

    # WholeCo metrics
    wc = _compute_metrics(wholeco_data)
    wc_gm = wc["blended_gm_pct"]

    # Per-state metrics
    state_rows = []
    for state_abbr, state_data in states_data.items():
        if state_abbr == "MGMT":
            continue  # skip management cost center
        m = _compute_metrics(state_data)
        if m["total_rev"] <= 0:
            continue
        # Dollar impact: (state GM% - WholeCo GM%) * state revenue
        m["dollar_impact"] = (m["blended_gm_pct"] - wc_gm) * m["total_rev"]
        m["state"] = state_abbr
        state_rows.append(m)

    # Sort by dollar impact descending (best performing first)
    state_rows.sort(key=lambda x: x["dollar_impact"], reverse=True)

    return {"wholeco": wc, "states": state_rows}
