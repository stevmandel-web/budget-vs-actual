# Margin Analysis Redesign

## Problem
The current Margin Analysis tab compares actuals to budget for BT/BCBA wages, but the budget wage data is inaccurate. It also shows misleading budget comparisons for Oct/Nov/Dec (which have no budget).

## Goal
Redesign around service-line profitability: BT margin vs BCBA margin by state, BCBA leverage ratios, and dollar impact of margin deviations. No budget dependency. Dollar-based proxies (no hours data available).

## Key Metrics

| Metric | Formula | What It Shows |
|--------|---------|---------------|
| BT Margin % | (BT Rev - BT Wages) / BT Rev | Profitability of BT service line |
| BCBA Margin % | (BCBA Rev - BCBA Wages) / BCBA Rev | Profitability of BCBA service line |
| Blended GM% | Gross Profit / Total Revenue | Overall gross margin |
| BCBA Leverage | BT Revenue / BCBA Wages | How much BT revenue each $1 of BCBA wages supports |
| BCBA Productivity | BCBA Revenue / BCBA Wages | Revenue generated per $1 of BCBA wages |
| $ Impact | (State GM% - WholeCo GM%) x State Revenue | Dollar effect of state's margin deviation |

## Layout (top to bottom)

### 1. State Margin Comparison Table (hero view)
Heatmap table, one row per state + WholeCo total row:
- Columns: State, BT Rev, BT Wages, BT Margin %, BCBA Rev, BCBA Wages, BCBA Margin %, Blended GM%, BCBA Leverage, $ Impact
- Color-coded margin cells (green = above WholeCo avg, red = below)
- Sorted by $ Impact (best first)

### 2. KPI Cards (3 across)
- WholeCo BT Margin %
- WholeCo BCBA Margin %
- WholeCo BCBA Leverage Ratio

### 3. State Margin Chart
Grouped bar: states on x-axis, BT Margin % + BCBA Margin % as grouped bars, WholeCo average line

### 4. Dollar Impact Analysis
Sorted list showing which states contribute to / drag on overall margin, with dollar amounts

### 5. Revenue Mix by State
Per-state BT vs BCBA revenue split

## Data Source
All data comes from `month_data["states"]` which has per-state BT Revenue, BCBA Supervision Revenue, BCBA Assessment Revenue, BT Wages, BCBA Wages already separated.

## Files Modified

| File | Change |
|------|--------|
| `engine/margin_analysis.py` | Add `analyze_service_line_margins(states_data, wholeco_data)` |
| `dashboard/charts.py` | Add `html_margin_heatmap_table()`, `make_margin_comparison_chart()` |
| `dashboard/app.py` | Rewrite `page_margin_analysis()` |
