# Margin Analysis Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the budget-focused Margin Analysis tab with a service-line profitability view showing BT/BCBA margins by state, BCBA leverage ratios, and dollar impact.

**Architecture:** New engine function computes all metrics from `month_data["states"]` dict. New heatmap table builder in charts.py. Rewritten page function in app.py. No budget dependency — purely actuals-based analysis.

**Tech Stack:** Python, Streamlit, Plotly, SLDS HTML tables

---

### Task 1: Add `analyze_service_line_margins()` to engine

**Files:**
- Modify: `engine/margin_analysis.py` (add new function, keep existing `analyze_gross_margin` for backward compat)

**Step 1: Write the new engine function**

Add to bottom of `engine/margin_analysis.py`:

```python
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
    def _safe_div(num, den):
        return num / den if den else 0

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
```

**Step 2: Verify import works**

Run: `cd "/Users/stevenmandel/Claude Code/budget-vs-actual" && python3 -c "from engine.margin_analysis import analyze_service_line_margins; print('OK')"`

**Step 3: Commit**

```bash
git add engine/margin_analysis.py
git commit -m "feat: add analyze_service_line_margins engine function"
```

---

### Task 2: Add `html_margin_heatmap_table()` to charts.py

**Files:**
- Modify: `dashboard/charts.py` (add new function after `html_clinic_comparison_table`)

**Step 1: Write the heatmap table builder**

Add to `dashboard/charts.py` (after `html_clinic_comparison_table` function, before `# PLOTLY` section):

```python
def html_margin_heatmap_table(margin_data):
    """Render state margin comparison as a heatmap-style SLDS table.

    Args:
        margin_data: dict from analyze_service_line_margins() with "wholeco" and "states" keys
    """
    wc = margin_data["wholeco"]
    states = margin_data["states"]

    if not states:
        return "<p>No state data available.</p>"

    # Reference values for color coding
    wc_bt_margin = wc["bt_margin_pct"]
    wc_bcba_margin = wc["bcba_margin_pct"]
    wc_gm = wc["blended_gm_pct"]

    def _heatmap_cell(val, ref, is_pct=True, invert=False):
        """Color-code a cell green/red based on comparison to reference."""
        if is_pct:
            text = f"{val * 100:.1f}%"
        else:
            text = f"{val:.1f}x"
        diff = val - ref
        if invert:
            diff = -diff
        if abs(diff) < 0.005:
            bg = ""
        elif diff > 0:
            bg = f"background:{SLDS['bg_success']};"
        else:
            bg = f"background:{SLDS['bg_error']};"
        return f'<td class="num" style="{bg} font-weight:600;">{text}</td>'

    def _dollar_cell(val):
        abs_val = abs(val)
        if abs_val >= 1_000_000:
            text = f"${abs_val / 1_000_000:.1f}M"
        elif abs_val >= 1_000:
            text = f"${abs_val / 1_000:.0f}K"
        else:
            text = f"${abs_val:.0f}"
        if val < 0:
            text = f"({text})"
        return text

    def _impact_cell(val):
        text = _dollar_cell(val)
        if val > 1000:
            bg = f"background:{SLDS['bg_success']};"
            text = f"+{_dollar_cell(abs(val))}"
        elif val < -1000:
            bg = f"background:{SLDS['bg_error']};"
            text = f"-{_dollar_cell(abs(val))}"
        else:
            bg = ""
        return f'<td class="num" style="{bg} font-weight:600;">{text}</td>'

    rows_html = []
    for s in states:
        rows_html.append(f"""<tr>
            <td style="font-weight:600;">{s['state']}</td>
            <td class="num">{_dollar_cell(s['bt_rev'])}</td>
            <td class="num">{_dollar_cell(s['bt_wages'])}</td>
            {_heatmap_cell(s['bt_margin_pct'], wc_bt_margin)}
            <td class="num">{_dollar_cell(s['bcba_rev'])}</td>
            <td class="num">{_dollar_cell(s['bcba_wages'])}</td>
            {_heatmap_cell(s['bcba_margin_pct'], wc_bcba_margin)}
            {_heatmap_cell(s['blended_gm_pct'], wc_gm)}
            {_heatmap_cell(s['bcba_leverage'], wc['bcba_leverage'], is_pct=False)}
            {_impact_cell(s['dollar_impact'])}
        </tr>""")

    # WholeCo total row
    rows_html.append(f"""<tr class="total">
        <td style="font-weight:700;">WholeCo</td>
        <td class="num" style="font-weight:700;">{_dollar_cell(wc['bt_rev'])}</td>
        <td class="num" style="font-weight:700;">{_dollar_cell(wc['bt_wages'])}</td>
        <td class="num" style="font-weight:700;">{wc['bt_margin_pct']*100:.1f}%</td>
        <td class="num" style="font-weight:700;">{_dollar_cell(wc['bcba_rev'])}</td>
        <td class="num" style="font-weight:700;">{_dollar_cell(wc['bcba_wages'])}</td>
        <td class="num" style="font-weight:700;">{wc['bcba_margin_pct']*100:.1f}%</td>
        <td class="num" style="font-weight:700;">{wc['blended_gm_pct']*100:.1f}%</td>
        <td class="num" style="font-weight:700;">{wc['bcba_leverage']:.1f}x</td>
        <td class="num" style="font-weight:700;">&mdash;</td>
    </tr>""")

    header = """
    <div style="overflow-x: auto;">
    <table class="slds-table">
        <thead>
            <tr>
                <th style="min-width:60px;">State</th>
                <th class="num" style="min-width:80px;">BT Rev</th>
                <th class="num" style="min-width:80px;">BT Wages</th>
                <th class="num" style="min-width:80px;">BT Margin</th>
                <th class="num" style="min-width:80px;">BCBA Rev</th>
                <th class="num" style="min-width:80px;">BCBA Wages</th>
                <th class="num" style="min-width:90px;">BCBA Margin</th>
                <th class="num" style="min-width:80px;">Blended GM</th>
                <th class="num" style="min-width:80px;">BCBA Lev.</th>
                <th class="num" style="min-width:80px;">$ Impact</th>
            </tr>
        </thead>
        <tbody>
    """
    footer = "</tbody></table></div>"
    return header + "\n".join(rows_html) + footer
```

**Step 2: Verify import**

Run: `cd "/Users/stevenmandel/Claude Code/budget-vs-actual" && python3 -c "from dashboard.charts import html_margin_heatmap_table; print('OK')"`

**Step 3: Commit**

```bash
git add dashboard/charts.py
git commit -m "feat: add html_margin_heatmap_table for service-line margin comparison"
```

---

### Task 3: Add `make_service_line_margin_chart()` to charts.py

**Files:**
- Modify: `dashboard/charts.py` (add after `make_state_margin_chart`)

**Step 1: Write the grouped bar chart**

Add at end of `dashboard/charts.py`:

```python
def make_service_line_margin_chart(margin_data):
    """Grouped bar chart: BT Margin % + BCBA Margin % by state with WholeCo avg lines."""
    states = margin_data["states"]
    wc = margin_data["wholeco"]
    if not states:
        return None

    labels = [s["state"] for s in states]
    bt_margins = [s["bt_margin_pct"] * 100 for s in states]
    bcba_margins = [s["bcba_margin_pct"] * 100 for s in states]

    fig = go.Figure(data=[
        go.Bar(name="BT Margin %", x=labels, y=bt_margins, marker_color=SLDS["brand"]),
        go.Bar(name="BCBA Margin %", x=labels, y=bcba_margins, marker_color=SLDS["warning"]),
    ])

    # WholeCo average reference lines
    fig.add_hline(y=wc["bt_margin_pct"] * 100, line_dash="dash",
                  line_color=SLDS["brand_dark"], line_width=1.5,
                  annotation_text=f"WholeCo BT {wc['bt_margin_pct']*100:.0f}%",
                  annotation_position="top right")
    fig.add_hline(y=wc["bcba_margin_pct"] * 100, line_dash="dash",
                  line_color=SLDS["warning_dark"], line_width=1.5,
                  annotation_text=f"WholeCo BCBA {wc['bcba_margin_pct']*100:.0f}%",
                  annotation_position="bottom right")

    fig.update_layout(**_slds_layout(
        height=360, barmode="group",
        yaxis=dict(title="Margin %", ticksuffix="%", gridcolor=SLDS["border"]),
    ))
    return fig
```

**Step 2: Verify import**

Run: `python3 -c "from dashboard.charts import make_service_line_margin_chart; print('OK')"`

**Step 3: Commit**

```bash
git add dashboard/charts.py
git commit -m "feat: add make_service_line_margin_chart Plotly chart"
```

---

### Task 4: Rewrite `page_margin_analysis()` in app.py

**Files:**
- Modify: `dashboard/app.py` lines 611-815 (replace entire `page_margin_analysis` + `_render_segment_card`)

**Step 1: Update imports**

Add to the imports in `dashboard/app.py` (around line 11-13):
- `from engine.margin_analysis import analyze_service_line_margins`
- `from dashboard.charts import html_margin_heatmap_table, make_service_line_margin_chart`

**Step 2: Replace page_margin_analysis and _render_segment_card**

Replace lines 611-815 (from `# PAGE: MARGIN ANALYSIS` through `_render_segment_card`) with:

```python
# ══════════════════════════════════════════════════════════════════════
# PAGE: MARGIN ANALYSIS (SERVICE-LINE PROFITABILITY)
# ══════════════════════════════════════════════════════════════════════
def page_margin_analysis(month, analysis):
    render_inline(f'<div class="slds-page-header">Margin Analysis &mdash; {month}</div>')

    month_data = get_month_data(month) or {}
    states_data = month_data.get("states", {})
    wholeco_data = month_data.get("wholeco", {})

    if not states_data or not wholeco_data:
        st.info("No data available for margin analysis.")
        return

    margin_data = analyze_service_line_margins(states_data, wholeco_data)
    wc = margin_data["wholeco"]
    states = margin_data["states"]

    if not states:
        st.info("No state data available for margin analysis.")
        return

    # ── KPI Cards ──────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        render_html(
            html_kpi_card(
                "BT Margin",
                f"{wc['bt_margin_pct'] * 100:.1f}%",
                f"Rev {fmt_compact(wc['bt_rev'])} | Wages {fmt_compact(wc['bt_wages'])}",
                wc["bt_margin_pct"] > 0.60,
            ),
        )
    with c2:
        render_html(
            html_kpi_card(
                "BCBA Margin",
                f"{wc['bcba_margin_pct'] * 100:.1f}%",
                f"Rev {fmt_compact(wc['bcba_rev'])} | Wages {fmt_compact(wc['bcba_wages'])}",
                wc["bcba_margin_pct"] > 0.10,
            ),
        )
    with c3:
        render_html(
            html_kpi_card(
                "BCBA Leverage",
                f"{wc['bcba_leverage']:.1f}x",
                f"BT Rev per $1 BCBA Wages",
                wc["bcba_leverage"] > 4.0,
            ),
        )

    # ── State Margin Comparison Table ──────────────────────────────
    render_inline(html_section_header("State Margin Comparison"))
    render_html(html_margin_heatmap_table(margin_data))

    # ── State Margin Chart ─────────────────────────────────────────
    render_inline(html_section_header("BT vs BCBA Margin by State"))
    fig = make_service_line_margin_chart(margin_data)
    if fig:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ── Dollar Impact Analysis ─────────────────────────────────────
    render_inline(html_section_header("Dollar Impact vs WholeCo Average"))
    st.caption("How each state's margin deviation translates to dollars (positive = above-average contribution)")
    for s in states:
        impact = s["dollar_impact"]
        if abs(impact) < 100:
            continue
        abs_impact = abs(impact)
        if abs_impact >= 1_000_000:
            impact_str = f"${abs_impact / 1_000_000:.1f}M"
        elif abs_impact >= 1_000:
            impact_str = f"${abs_impact / 1_000:.0f}K"
        else:
            impact_str = f"${abs_impact:.0f}"

        sign = "+" if impact >= 0 else "-"
        badge_type = "success" if impact >= 0 else "error"
        gm_diff = (s["blended_gm_pct"] - wc["blended_gm_pct"]) * 100

        render_html(f"""
        <div class="slds-card" style="padding: 0.75rem 1rem; display:flex; justify-content:space-between; align-items:center;">
            <div>
                <strong>{s['state']}</strong>
                <span style="color:{SLDS['text_secondary']}; font-size:0.8125rem; margin-left:0.5rem;">
                    GM {s['blended_gm_pct']*100:.1f}% ({gm_diff:+.1f}pp vs avg) | Rev {fmt_compact(s['total_rev'])}
                </span>
            </div>
            <div>{html_badge(f"{sign}{impact_str}", badge_type)}</div>
        </div>
        """)

    # ── Revenue Mix by State ───────────────────────────────────────
    render_inline(html_section_header("Revenue Mix by State"))
    mix_rows = []
    for s in states:
        total = s["total_rev"]
        if total <= 0:
            continue
        bt_pct = s["bt_rev"] / total * 100
        bcba_pct = s["bcba_rev"] / total * 100
        other_pct = 100 - bt_pct - bcba_pct
        mix_rows.append({
            "state": s["state"],
            "bt_pct": f"{bt_pct:.1f}%",
            "bcba_pct": f"{bcba_pct:.1f}%",
            "other_pct": f"{other_pct:.1f}%",
            "total": fmt_compact(total),
        })
    if mix_rows:
        render_html(
            html_simple_table(mix_rows, [
                ("state", "State", False),
                ("bt_pct", "BT %", True),
                ("bcba_pct", "BCBA %", True),
                ("other_pct", "Other %", True),
                ("total", "Total Rev", True),
            ]),
        )
```

**Step 3: Remove old margin helpers from app.py**

Delete `_render_segment_card()` function and remove unused imports:
- Remove `categorize_margin_items, get_margin_kpis` from pipeline import line
- Remove `make_cogs_breakdown_chart, make_state_margin_chart` from charts import line

**Step 4: Verify import**

Run: `python3 -c "import dashboard.app; print('OK')"`

**Step 5: Verify CLI regression**

Run: `python3 run.py --raw-data "/Users/stevenmandel/Downloads/Raw Data Tab .xlsx" --mapping "/Users/stevenmandel/Downloads/Mapping tab.xlsx" --budget "/Users/stevenmandel/Downloads/MASTER 2026 Budget vBase_3.xlsx" 2>&1 | tail -3`

Expected: EBITDA $56,201

**Step 6: Commit**

```bash
git add dashboard/app.py
git commit -m "feat: rewrite Margin Analysis tab for service-line profitability"
```

---

### Task 5: End-to-end verification

**Step 1: Clear caches and test import**

```bash
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
python3 -c "import dashboard.app; print('Import OK')"
```

**Step 2: Launch dashboard**

```bash
python3 -m streamlit run dashboard/app.py
```

**Step 3: Verify in browser**

1. Navigate to Margin Analysis tab
2. Select January (has budget) — verify KPI cards show BT/BCBA margin + leverage
3. Verify state comparison heatmap table renders with color coding
4. Verify grouped bar chart shows BT/BCBA margins by state
5. Verify dollar impact section shows positive/negative contributions
6. Verify revenue mix table shows BT/BCBA/Other %
7. Select October (no budget) — verify same layout works (no budget references)
8. Verify Executive Summary, P&L Detail, Q&A tabs all still work
