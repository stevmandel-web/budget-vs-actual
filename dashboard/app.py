"""
Treetop Therapy — Budget vs Actual Dashboard
Run: streamlit run dashboard/app.py
"""
import json
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from config import DEFAULT_BUDGET_PATH, DEFAULT_MAPPING_PATH, PNL_STRUCTURE, IS_CLOUD
from dashboard.pipeline import (
    process_raw_data_upload, ensure_budget_loaded,
    compute_month_analysis, get_months_in_order,
    list_available_months, load_month, clear_budget_cache,
    has_budget_for_month, get_clinics_for_state,
    aggregate_clinics, get_all_months_chronological,
)
from engine.margin_analysis import analyze_service_line_margins
from dashboard.qa_engine import (
    is_available as qa_available, build_context as qa_build_context,
    ask as qa_ask, generate_summary_for_gamma,
)
from dashboard.charts import (
    SLDS, GLOBAL_CSS, CHART_COLORS,
    fmt_dollar, fmt_pct, fmt_compact,
    html_kpi_card, html_badge, html_section_header, html_insight,
    html_variance_table, html_simple_table,
    html_mom_table, html_clinic_comparison_table,
    html_state_comparison_table, html_entity_mom_table,
    html_margin_heatmap_table, make_service_line_margin_chart,
    make_waterfall_chart, make_dual_trend_chart, make_trend_chart,
    make_variance_bars, make_state_revenue_chart, make_clinic_revenue_chart,
)

# ── Page config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Treetop Therapy | Budget vs Actual",
    page_icon="🌳",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Initialize session state ─────────────────────────────────────────
def init_state():
    defaults = {
        "budget": None,
        "available": [],
        "analysis_cache": {},
        "loaded_months": {},
        "qa_messages": [],
        "last_uploaded_file": None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


init_state()


# ── Password gate (Streamlit Cloud) ──────────────────────────────────
def check_password():
    """Returns True if the user has entered the correct password."""
    if not hasattr(st, "secrets") or "password" not in st.secrets:
        return True  # No password configured (local dev)

    if st.session_state.get("authenticated"):
        return True

    st.markdown(
        '<div style="text-align:center; padding: 3rem 1rem;">'
        '<div style="font-size:2rem; font-weight:700; color:#0070d2;">🌳 Treetop Therapy</div>'
        '<div style="font-size:1rem; color:#706e6b; margin-top:0.5rem;">Budget vs Actual Dashboard</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    pwd = st.text_input("Enter password to continue", type="password")
    if pwd:
        if pwd == st.secrets["password"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")
    return False


if not check_password():
    st.stop()


# ── Inject SLDS global stylesheet ───────────────────────────────────
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


# ── HTML rendering helpers ────────────────────────────────────────────
def render_html(html_content):
    """Render complex HTML (tables, cards) via st.html with embedded CSS."""
    st.html(GLOBAL_CSS + html_content)


def render_inline(html_content):
    """Render simple inline HTML (headers, badges) via st.markdown."""
    st.markdown(html_content, unsafe_allow_html=True)


# ── Load data helpers ────────────────────────────────────────────────
def load_budget():
    if st.session_state.budget is None:
        try:
            st.session_state.budget = ensure_budget_loaded(DEFAULT_BUDGET_PATH)
        except Exception as e:
            st.sidebar.error(f"Could not load budget: {e}")


def get_month_data(month_abbr):
    if month_abbr in st.session_state.loaded_months:
        return st.session_state.loaded_months[month_abbr]
    available = st.session_state.available
    year = None
    for m, y in available:
        if m == month_abbr:
            year = y
            break
    if year is None:
        return None
    data = load_month(month_abbr, year)
    if data:
        st.session_state.loaded_months[month_abbr] = data
    return data


def get_all_months_data(months_order):
    result = {}
    for m in months_order:
        data = get_month_data(m)
        if data:
            result[m] = data
    return result


def get_analysis(month_abbr):
    if month_abbr in st.session_state.analysis_cache:
        return st.session_state.analysis_cache[month_abbr]
    month_data = get_month_data(month_abbr)
    if not month_data or not st.session_state.budget:
        return None
    month_json = json.dumps(month_data, sort_keys=True, default=str)
    budget_json = json.dumps(st.session_state.budget, sort_keys=True, default=str)
    available = st.session_state.get("available", [])
    month_has_budget = has_budget_for_month(month_abbr, available)
    result = compute_month_analysis(month_abbr, month_json, budget_json, month_has_budget)
    st.session_state.analysis_cache[month_abbr] = result
    return result


# ══════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════
SIDEBAR_CSS = f"""
<style>
    [data-testid="stSidebar"] {{
        background: {SLDS["bg_card"]};
        border-right: 1px solid {SLDS["border"]};
    }}
    [data-testid="stSidebar"] .block-container {{
        padding-top: 1rem;
    }}
    .sidebar-logo {{
        font-size: 1.375rem;
        font-weight: 700;
        color: {SLDS["brand_dark"]};
        margin-bottom: 0.125rem;
    }}
    .sidebar-caption {{
        font-size: 0.8125rem;
        color: {SLDS["text_secondary"]};
        margin-bottom: 0.75rem;
    }}
    .sidebar-section {{
        font-size: 0.75rem;
        font-weight: 600;
        color: {SLDS["text_secondary"]};
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin: 1rem 0 0.375rem 0;
    }}
    .status-pill {{
        display: inline-block;
        padding: 0.125rem 0.5rem;
        border-radius: 12px;
        font-size: 0.6875rem;
        font-weight: 600;
        margin: 0.125rem 0;
    }}
    .status-loaded {{
        background: {SLDS["bg_success"]};
        color: {SLDS["success_dark"]};
    }}
    .status-missing {{
        background: {SLDS["bg_error"]};
        color: {SLDS["error_dark"]};
    }}
</style>
"""


def _build_excel_for_month(month_abbr):
    """Build the full Excel workbook for the selected month and return as BytesIO."""
    from output.excel_writer import build_output_workbook

    analysis = get_analysis(month_abbr)
    if not analysis:
        return None

    month_data = get_month_data(month_abbr)
    budget = st.session_state.budget or {}
    available = st.session_state.available
    months_order = get_months_in_order(available)
    all_months_data = get_all_months_data(months_order)

    # Get prior month actuals
    chronological = get_all_months_chronological(available)
    prior_actuals = None
    for i, (m, y) in enumerate(chronological):
        if m == month_abbr and i > 0:
            prior_m, prior_y = chronological[i - 1]
            prior_data = get_month_data(prior_m)
            if prior_data:
                prior_actuals = prior_data.get("wholeco", {})
            break

    return build_output_workbook(
        wholeco_variance=analysis["wholeco_variance"],
        segment_variance=analysis["segment_variance"],
        state_variances=analysis["state_variances"],
        waterfall=analysis["waterfall"],
        insights=analysis["insights"],
        budget_data=budget,
        actuals_by_month={m: d.get("wholeco", {}) for m, d in all_months_data.items()},
        months_loaded=months_order,
        month=month_abbr,
        states=analysis["active_states"],
        output_path=None,  # Return BytesIO stream
        prior_month_actuals=prior_actuals,
        working_days=analysis.get("working_days"),
        clinics_detail=month_data.get("clinics_detail") if month_data else None,
        mgmt_actuals=month_data.get("mgmt") if month_data else None,
        margin_analysis=analysis.get("margin_analysis"),
    )


def render_sidebar():
    with st.sidebar:
        st.markdown(SIDEBAR_CSS, unsafe_allow_html=True)

        # Logo / branding
        st.markdown('<div class="sidebar-logo">Treetop Therapy</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-caption">Budget vs Actual Dashboard</div>', unsafe_allow_html=True)

        # ─── Data Upload (local mode only) ────────────────────
        if not IS_CLOUD:
            st.markdown('<div class="sidebar-section">Data Upload</div>', unsafe_allow_html=True)
            uploaded = st.file_uploader(
                "Upload Raw Data Tab",
                type=["xlsx"],
                help="Upload your monthly Raw Data Tab. All months will be parsed.",
                label_visibility="collapsed",
            )
            if uploaded:
                file_id = f"{uploaded.name}_{uploaded.size}"
                if file_id != st.session_state.last_uploaded_file:
                    with st.spinner("Parsing raw data..."):
                        try:
                            saved, unmapped = process_raw_data_upload(
                                uploaded.getvalue(), DEFAULT_MAPPING_PATH, uploaded.name
                            )
                            months_saved = list(saved.keys())
                            st.session_state.last_uploaded_file = file_id
                            st.session_state.analysis_cache = {}
                            st.session_state.loaded_months = {}
                            st.session_state.available = list_available_months()
                            st.success(f"Parsed {len(months_saved)} months: {', '.join(months_saved)}")
                            if unmapped:
                                st.warning(f"{len(unmapped)} unmapped transactions")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Parse error: {e}")
                else:
                    st.markdown(
                        '<span class="status-pill status-loaded">Data loaded</span>',
                        unsafe_allow_html=True,
                    )

        # ─── Month Selector ─────────────────────────────────────
        st.markdown('<div class="sidebar-section">Select Month</div>', unsafe_allow_html=True)
        available = st.session_state.available
        if available:
            options = [f"{m} {y}" for m, y in available]
            idx = len(options) - 1
            selected = st.selectbox("Month", options, index=idx, label_visibility="collapsed")
            selected_month = selected.split()[0]
        else:
            st.info("Upload a Raw Data Tab to begin.")
            selected_month = None

        # ─── Data Status ────────────────────────────────────────
        st.markdown('<div class="sidebar-section">Data Status</div>', unsafe_allow_html=True)
        if available:
            pills = " ".join(
                f'<span class="status-pill status-loaded">{m} {y}</span>'
                for m, y in available
            )
            st.markdown(pills, unsafe_allow_html=True)

        bud_loaded = st.session_state.budget is not None
        bud_html = (
            '<span class="status-pill status-loaded">Budget loaded</span>'
            if bud_loaded
            else '<span class="status-pill status-missing">Budget not loaded</span>'
        )
        st.markdown(bud_html, unsafe_allow_html=True)

        if st.button("Re-parse Budget", use_container_width=True):
            clear_budget_cache()
            st.session_state.budget = None
            st.session_state.analysis_cache = {}
            st.rerun()

        # ─── Navigation ─────────────────────────────────────────
        st.markdown('<div class="sidebar-section">Navigate</div>', unsafe_allow_html=True)
        page = st.radio(
            "Page",
            ["Executive Summary", "P&L Detail", "Margin Analysis", "Q&A"],
            label_visibility="collapsed",
        )

        # ─── Excel Export ────────────────────────────────────────
        if selected_month and st.session_state.budget:
            st.markdown('<div class="sidebar-section">Export</div>', unsafe_allow_html=True)
            if st.button("📥 Build Excel Report", use_container_width=True):
                with st.spinner("Building Excel report..."):
                    excel_bytes = _build_excel_for_month(selected_month)
                    if excel_bytes:
                        st.session_state["excel_download"] = excel_bytes
                        st.session_state["excel_filename"] = f"Budget_vs_Actual_{selected_month}_2026.xlsx"
                        st.rerun()

            if "excel_download" in st.session_state:
                st.download_button(
                    label="💾 Save Excel File",
                    data=st.session_state["excel_download"],
                    file_name=st.session_state.get("excel_filename", "report.xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

        return selected_month, page


# ══════════════════════════════════════════════════════════════════════
# PAGE: EXECUTIVE SUMMARY
# ══════════════════════════════════════════════════════════════════════
def page_executive_summary(month, analysis):
    render_inline(f'<div class="slds-page-header">Executive Summary &mdash; {month}</div>')

    wc = get_month_data(month)
    if not wc:
        return
    wc = wc.get("wholeco", {})
    budget = st.session_state.budget or {}
    bud_wc = budget.get("wholeco", {})
    available = st.session_state.available
    show_budget = has_budget_for_month(month, available)

    revenue = wc.get("Total Revenue", 0)
    gp = wc.get("Gross Profit", 0)
    ebitda = wc.get("EBITDA", 0)
    gm_pct = gp / revenue if revenue else 0

    # KPI Cards row
    c1, c2, c3, c4 = st.columns(4)
    if show_budget:
        rev_bud = bud_wc.get("Total Revenue", {}).get(month, 0)
        ebitda_bud = bud_wc.get("EBITDA", {}).get(month, 0)
        gm_bud = bud_wc.get("Gross Profit", {}).get(month, 0) / rev_bud if rev_bud else 0

        rev_delta = revenue - rev_bud
        with c1:
            render_html(
                html_kpi_card("Total Revenue", fmt_compact(revenue),
                              f"{fmt_compact(rev_delta)} vs Budget",
                              rev_delta >= 0),
            )
        with c2:
            gm_delta_pp = (gm_pct - gm_bud) * 100
            render_html(
                html_kpi_card("Gross Margin", f"{gm_pct * 100:.1f}%",
                              f"{gm_delta_pp:+.1f}pp vs Budget",
                              gm_delta_pp >= 0),
            )
        with c3:
            ebitda_delta = ebitda - ebitda_bud
            ebitda_pct = ebitda / revenue * 100 if revenue else 0
            render_html(
                html_kpi_card("EBITDA", fmt_compact(ebitda),
                              f"{ebitda_pct:.1f}% margin · {fmt_compact(ebitda_delta)} vs Budget",
                              ebitda_delta >= 0),
            )
        with c4:
            ebitda_bud_pct = ebitda_bud / rev_bud * 100 if rev_bud else 0
            ebitda_pct_delta = ebitda_pct - ebitda_bud_pct
            render_html(
                html_kpi_card("EBITDA Margin", f"{ebitda_pct:.1f}%",
                              f"{ebitda_pct_delta:+.1f}pp vs Budget ({ebitda_bud_pct:.1f}%)",
                              ebitda_pct_delta >= 0),
            )
    else:
        with c1:
            render_html(
                html_kpi_card("Total Revenue", fmt_compact(revenue),
                              "No budget for this month", True),
            )
        with c2:
            render_html(
                html_kpi_card("Gross Margin", f"{gm_pct * 100:.1f}%",
                              f"GP {fmt_compact(gp)}", gm_pct > 0.55),
            )
        with c3:
            ebitda_pct = ebitda / revenue * 100 if revenue else 0
            render_html(
                html_kpi_card("EBITDA", fmt_compact(ebitda),
                              f"{ebitda_pct:.1f}% margin", ebitda > 0),
            )
        with c4:
            render_html(
                html_kpi_card("EBITDA Margin", f"{ebitda_pct:.1f}%",
                              f"EBITDA / Revenue", ebitda_pct > 5),
            )

    # Charts row 1: Trend + Waterfall
    months_order = get_months_in_order(st.session_state.available)
    all_months_data = get_all_months_data(months_order)

    col1, col2 = st.columns(2)
    with col1:
        render_inline(html_section_header("Revenue & EBITDA Trend"))
        fig = make_dual_trend_chart(all_months_data, budget, months_order, st.session_state.available)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with col2:
        waterfall = analysis.get("waterfall", [])
        if waterfall:
            ebitda_margin_pct = ebitda / revenue * 100 if revenue else 0
            render_inline(html_section_header(f"EBITDA Waterfall ({ebitda_margin_pct:.1f}% margin)"))
            fig = make_waterfall_chart(waterfall, month)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # Charts row 2: Top variances (only when budget is available)
    if show_budget:
        variance = analysis.get("wholeco_variance", [])
        col1, col2 = st.columns(2)
        with col1:
            render_inline(html_section_header("Top Unfavorable Variances"))
            fig = make_variance_bars(variance, top_n=5, favorable=False)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.caption("No unfavorable variances found.")
        with col2:
            render_inline(html_section_header("Top Favorable Variances"))
            fig = make_variance_bars(variance, top_n=5, favorable=True)
            if fig:
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.caption("No favorable variances found.")

    # Insights
    render_inline(html_section_header("Key Insights"))
    insights = analysis.get("insights", [])
    if insights:
        visible = insights[:8]
        for ins in visible:
            sev = ins.get("severity", "info")
            impact = ins.get("dollar_impact", 0)
            impact_text = fmt_compact(impact) if impact else ""
            render_html(
                html_insight(sev, ins["insight"], ins.get("action", ""), impact_text),
            )
        if len(insights) > 8:
            with st.expander(f"Show {len(insights) - 8} more insights"):
                for ins in insights[8:]:
                    sev = ins.get("severity", "info")
                    impact = ins.get("dollar_impact", 0)
                    impact_text = fmt_compact(impact) if impact else ""
                    render_html(
                        html_insight(sev, ins["insight"], ins.get("action", ""), impact_text),
                    )
    else:
        st.caption("No insights generated for this month.")


# ══════════════════════════════════════════════════════════════════════
# PAGE: P&L DETAIL (CONSOLIDATED — 4 SUB-VIEWS)
# ══════════════════════════════════════════════════════════════════════
def page_pnl_detail(month, analysis):
    render_inline(f'<div class="slds-page-header">P&L Detail &mdash; {month}</div>')

    view = st.radio(
        "View",
        ["Segment P&L", "Month-over-Month", "State Drill-Down", "Clinic Comparison"],
        horizontal=True,
        key="pnl_detail_view",
    )

    if view == "Segment P&L":
        _view_segment_pnl(month, analysis)
    elif view == "Month-over-Month":
        _view_month_over_month(month, analysis)
    elif view == "State Drill-Down":
        _view_state_drilldown(month, analysis)
    elif view == "Clinic Comparison":
        _view_clinic_comparison(month, analysis)


def _build_actuals_only_rows(actuals_data):
    """Build P&L rows with actuals only (no budget/variance) for months without budget."""
    rows = []
    computed = {}
    for label, row_type, is_revenue_like in PNL_STRUCTURE:
        if row_type in ("header", "blank"):
            rows.append({
                "label": label, "row_type": row_type,
                "is_revenue_like": is_revenue_like,
                "budget": None, "actual": None,
                "dollar_var": None, "pct_var": None, "favorable": None,
            })
            continue
        if row_type == "pct_row":
            from dashboard.charts import _pct_value
            act_pct = _pct_value(label, computed)
            rows.append({
                "label": label, "row_type": "pct_row",
                "is_revenue_like": is_revenue_like,
                "budget": None, "actual": act_pct,
                "dollar_var": None, "pct_var": None, "favorable": None,
            })
            continue
        actual_val = actuals_data.get(label, 0.0)
        rows.append({
            "label": label, "row_type": row_type,
            "is_revenue_like": is_revenue_like,
            "budget": None, "actual": actual_val,
            "dollar_var": None, "pct_var": None, "favorable": None,
        })
        computed[label] = actual_val
    return rows


# ── Sub-view: Segment P&L ────────────────────────────────────────────
def _view_segment_pnl(month, analysis):
    segment = st.radio("Segment", ["WholeCo", "Home", "Clinic"], horizontal=True,
                       key="segment_pnl_segment")

    month_data = get_month_data(month) or {}
    budget = st.session_state.budget or {}
    available = st.session_state.available
    show_budget = has_budget_for_month(month, available)

    seg_key = segment.lower() if segment != "WholeCo" else "wholeco"

    if show_budget:
        if segment == "WholeCo":
            variance_rows = analysis.get("wholeco_variance", [])
        else:
            from engine.variance import compute_variance
            variance_rows = compute_variance(
                budget.get(seg_key, {}), month_data.get(seg_key, {}), month
            )
    else:
        variance_rows = _build_actuals_only_rows(month_data.get(seg_key, {}))

    render_html(html_variance_table(variance_rows, show_budget=show_budget))


# ── Sub-view: Month-over-Month ────────────────────────────────────────
def _view_month_over_month(month, analysis):
    segment_label = st.radio("Segment", ["WholeCo", "Home", "Clinic"],
                             horizontal=True, key="mom_segment")
    segment_key = segment_label.lower() if segment_label != "WholeCo" else "wholeco"

    available = st.session_state.available
    months_chrono = get_all_months_chronological(available)
    months_order = [m for m, y in months_chrono]
    all_data = get_all_months_data(months_order)

    budget = st.session_state.budget or {}
    budget_segment = budget.get(segment_key, {})

    render_inline(html_section_header("Month-over-Month P&L"))
    render_html(
        html_mom_table(all_data, budget_segment, months_chrono,
                       segment_key, month, available)
    )


# ── Sub-view: State Drill-Down ────────────────────────────────────────
def _view_state_drilldown(month, analysis):
    month_data = get_month_data(month) or {}
    states_data = month_data.get("states", {})
    clinics_detail = month_data.get("clinics_detail", {})
    budget_states = analysis.get("combined_budget_states", {})
    active_states = analysis.get("active_states", [])
    available = st.session_state.available
    show_budget = has_budget_for_month(month, available)

    if not active_states:
        st.caption("No state data available.")
        return

    # ── Get prior month data for MoM comparison ──────────────────────
    months_chrono = get_all_months_chronological(available)
    months_order = [m for m, y in months_chrono]
    cur_idx = months_order.index(month) if month in months_order else -1
    prior_month = months_order[cur_idx - 1] if cur_idx > 0 else None
    prior_month_data = get_month_data(prior_month) if prior_month else None

    # ── Cascading filters: State → Clinic ────────────────────────────
    filter_states = ["All States"] + [s for s in active_states if s != "MGMT"]
    col1, col2 = st.columns(2)
    with col1:
        selected_state = st.selectbox("State", filter_states, key="state_drill_state")
    with col2:
        if selected_state != "All States":
            clinics_for_state = get_clinics_for_state(clinics_detail, selected_state)
            clinic_options = ["All Clinics"] + clinics_for_state
            selected_clinic = st.selectbox("Clinic", clinic_options, key="state_drill_clinic")
        else:
            selected_clinic = None
            st.selectbox("Clinic", ["—"], disabled=True, key="state_drill_clinic_disabled")

    # ── Revenue comparison chart ─────────────────────────────────────
    render_inline(html_section_header("State Revenue Comparison"))
    if states_data:
        fig = make_state_revenue_chart(states_data, budget_states, month)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # ═════════════════════════════════════════════════════════════════
    # VIEW: ALL STATES SIDE-BY-SIDE
    # ═════════════════════════════════════════════════════════════════
    if selected_state == "All States":
        display_states = [s for s in active_states if s != "MGMT"]
        render_inline(html_section_header("All States — Side by Side"))
        render_html(
            html_state_comparison_table(
                states_data, display_states,
                budget_states if show_budget else None,
                month if show_budget else None,
            )
        )

    # ═════════════════════════════════════════════════════════════════
    # VIEW: SINGLE STATE (with prior month comparison)
    # ═════════════════════════════════════════════════════════════════
    elif selected_clinic is None or selected_clinic == "All Clinics":
        state_actuals = states_data.get(selected_state, {})
        prior_states = prior_month_data.get("states", {}) if prior_month_data else {}
        prior_state_actuals = prior_states.get(selected_state, {})

        # Budget for this state
        state_budget = budget_states.get(selected_state) if show_budget else None

        label = f"{selected_state} — {month}" + (f" vs {prior_month}" if prior_month else "")
        render_inline(html_section_header(label))
        render_html(
            html_entity_mom_table(
                state_actuals, prior_state_actuals,
                month, prior_month or "—",
                budget_data=state_budget, month=month if show_budget else None,
            )
        )

        # Also show clinics for this state side-by-side below
        clinics_for_state = get_clinics_for_state(clinics_detail, selected_state)
        if clinics_for_state:
            # Compute clinic segment budget GM% benchmark
            clinic_budget_gm = None
            if show_budget:
                budget = st.session_state.budget or {}
                cb = budget.get("clinic", {})
                cb_rev = cb.get("Total Revenue", {}).get(month, 0)
                cb_gp = cb.get("Gross Profit", {}).get(month, 0)
                clinic_budget_gm = cb_gp / cb_rev if cb_rev else None

            render_inline(html_section_header(f"{selected_state} — Clinics"))
            render_html(
                html_clinic_comparison_table(
                    clinics_detail, clinics_for_state, clinic_budget_gm
                )
            )

    # ═════════════════════════════════════════════════════════════════
    # VIEW: SINGLE CLINIC (with prior month comparison)
    # ═════════════════════════════════════════════════════════════════
    else:
        clinic_data = clinics_detail.get(selected_clinic, {})
        prior_clinics = prior_month_data.get("clinics_detail", {}) if prior_month_data else {}
        prior_clinic_data = prior_clinics.get(selected_clinic, {})

        # GM% benchmark badge
        if show_budget:
            budget = st.session_state.budget or {}
            clinic_budget = budget.get("clinic", {})
            bud_rev = clinic_budget.get("Total Revenue", {}).get(month, 0)
            bud_gp = clinic_budget.get("Gross Profit", {}).get(month, 0)
            budget_gm_pct = bud_gp / bud_rev if bud_rev else 0
            actual_rev = clinic_data.get("Total Revenue", 0)
            actual_gp = clinic_data.get("Gross Profit", 0)
            actual_gm = actual_gp / actual_rev if actual_rev else 0
            delta = actual_gm - budget_gm_pct
            badge = html_badge(
                f"GM {actual_gm * 100:.1f}% ({delta * 100:+.1f}pp vs Clinic Budget)",
                "success" if delta >= 0 else "error",
            )
            render_inline(f'<div style="margin-bottom:0.5rem;">{badge}</div>')

        label = f"{selected_clinic} — {month}" + (f" vs {prior_month}" if prior_month else "")
        render_inline(html_section_header(label))
        render_html(
            html_entity_mom_table(
                clinic_data, prior_clinic_data,
                month, prior_month or "—",
            )
        )


def _render_clinic_pnl_enhanced(clinic_data, clinic_name, month, show_budget):
    """Render P&L for a single clinic with optional GM% benchmark."""
    rows = _build_actuals_only_rows(clinic_data)

    # Show budget GM% benchmark if available
    if show_budget:
        budget = st.session_state.budget or {}
        clinic_budget = budget.get("clinic", {})
        bud_rev = clinic_budget.get("Total Revenue", {}).get(month, 0)
        bud_gp = clinic_budget.get("Gross Profit", {}).get(month, 0)
        budget_gm_pct = bud_gp / bud_rev if bud_rev else 0

        actual_rev = clinic_data.get("Total Revenue", 0)
        actual_gp = clinic_data.get("Gross Profit", 0)
        actual_gm = actual_gp / actual_rev if actual_rev else 0
        delta = actual_gm - budget_gm_pct

        badge = html_badge(
            f"GM {actual_gm * 100:.1f}% ({delta * 100:+.1f}pp vs Clinic Budget)",
            "success" if delta >= 0 else "error",
        )
        render_inline(f'<div style="margin-bottom:0.5rem;">{badge}</div>')

    render_html(html_variance_table(rows, show_budget=True))


# ── Sub-view: Clinic Comparison ───────────────────────────────────────
def _view_clinic_comparison(month, analysis):
    month_data = get_month_data(month) or {}
    clinics_detail = month_data.get("clinics_detail", {})
    active_states = analysis.get("active_states", [])
    available = st.session_state.available
    show_budget = has_budget_for_month(month, available)

    if not clinics_detail:
        st.caption("No clinic detail data available.")
        return

    # Optional state filter
    state_filter = st.selectbox(
        "Filter by State",
        ["All States"] + [s for s in active_states if s not in ("MGMT", "Other")],
        key="clinic_compare_state",
    )

    if state_filter == "All States":
        clinic_names = sorted(clinics_detail.keys())
    else:
        clinic_names = get_clinics_for_state(clinics_detail, state_filter)

    if not clinic_names:
        st.caption(f"No clinics found for {state_filter}.")
        return

    # Compute budget GM% benchmark
    budget_gm_pct = None
    if show_budget:
        budget = st.session_state.budget or {}
        clinic_budget = budget.get("clinic", {})
        rev = clinic_budget.get("Total Revenue", {}).get(month, 0)
        gp = clinic_budget.get("Gross Profit", {}).get(month, 0)
        budget_gm_pct = gp / rev if rev else None

    render_inline(html_section_header(f"Clinic Comparison — {month}"))

    # Clinic revenue chart
    if clinics_detail:
        fig = make_clinic_revenue_chart(
            {c: clinics_detail[c] for c in clinic_names if c in clinics_detail}
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    render_html(html_clinic_comparison_table(clinics_detail, clinic_names, budget_gm_pct))


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
    ebitda_val = wholeco_data.get("EBITDA", 0)
    total_rev = wholeco_data.get("Total Revenue", 0)
    ebitda_margin = ebitda_val / total_rev * 100 if total_rev else 0
    c1, c2, c3, c4 = st.columns(4)
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
                "BT Rev per $1 BCBA Wages",
                wc["bcba_leverage"] > 4.0,
            ),
        )
    with c4:
        render_html(
            html_kpi_card(
                "EBITDA Margin",
                f"{ebitda_margin:.1f}%",
                f"EBITDA {fmt_compact(ebitda_val)} / Rev {fmt_compact(total_rev)}",
                ebitda_margin > 5,
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


# ══════════════════════════════════════════════════════════════════════
# PAGE: Q&A (Claude API)
# ══════════════════════════════════════════════════════════════════════
def page_qa(month):
    render_inline(f'<div class="slds-page-header">Financial Q&A &mdash; {month}</div>')

    if not qa_available():
        st.warning(
            "**Q&A requires an Anthropic API key.**\n\n"
            "Add to `.streamlit/secrets.toml`:\n"
            "```\nANTHROPIC_API_KEY = \"sk-ant-...\"\n```\n\n"
            "Or set the `ANTHROPIC_API_KEY` environment variable."
        )
        return

    # Build financial context for this month
    analysis = get_analysis(month)
    if not analysis:
        st.info("No analysis data available for this month.")
        return

    month_data = get_month_data(month)
    budget = st.session_state.budget or {}
    available = st.session_state.available
    months_order = get_months_in_order(available)
    all_months_data = get_all_months_data(months_order)

    context = qa_build_context(
        month, analysis, month_data, budget, available, all_months_data
    )

    # Action buttons row
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        if st.button("📊 Generate 1-Pager", use_container_width=True):
            with st.spinner("Generating executive summary..."):
                summary = generate_summary_for_gamma(month, context)
                st.session_state.qa_messages.append(
                    {"role": "assistant", "content": f"**Executive Summary — {month}**\n\n{summary}"}
                )
                st.rerun()
    with c2:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.qa_messages = []
            st.rerun()

    st.divider()

    # Chat history
    for msg in st.session_state.qa_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask about your financials..."):
        st.session_state.qa_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                # Pass message history for conversational context
                history = [m for m in st.session_state.qa_messages if m["role"] in ("user", "assistant")]
                response = qa_ask(prompt, context, message_history=history[:-1])
                st.markdown(response)

        st.session_state.qa_messages.append({"role": "assistant", "content": response})

    # Context expander (debug/transparency)
    with st.expander("📋 Data context sent to Claude"):
        st.code(context, language="markdown")


# ══════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════
def main():
    load_budget()
    st.session_state.available = list_available_months()
    selected_month, page = render_sidebar()

    if not selected_month or not st.session_state.available:
        # Welcome screen
        render_html("""
        <div style="text-align:center; padding:4rem 2rem;">
            <div style="font-size:2.5rem; font-weight:700; color:#0070d2; margin-bottom:0.5rem;">
                Treetop Therapy
            </div>
            <div style="font-size:1.125rem; color:#706e6b; margin-bottom:2rem;">
                Budget vs Actual Dashboard
            </div>
            <div style="max-width:480px; margin:0 auto; text-align:left;">
                <div class="slds-card" style="padding:1.25rem;">
                    <div style="font-weight:600; margin-bottom:0.75rem; color:#080707;">
                        Get Started
                    </div>
                    <div style="color:#706e6b; font-size:0.875rem; line-height:1.6;">
                        Upload a Raw Data Tab (.xlsx) in the sidebar to begin.
                        The dashboard will parse your financial data and show:
                    </div>
                    <ul style="color:#706e6b; font-size:0.875rem; margin-top:0.5rem; line-height:1.8;">
                        <li>Executive Summary with KPI cards and charts</li>
                        <li>Full P&L with segment, state, and clinic drill-downs</li>
                        <li>Month-over-month trending with budget variance</li>
                        <li>Gross margin analysis</li>
                        <li>AI-powered Q&A (coming soon)</li>
                    </ul>
                </div>
            </div>
        </div>
        """)
        return

    analysis = get_analysis(selected_month)
    if not analysis:
        st.error(f"Could not compute analysis for {selected_month}")
        return

    if page == "Executive Summary":
        page_executive_summary(selected_month, analysis)
    elif page == "P&L Detail":
        page_pnl_detail(selected_month, analysis)
    elif page == "Margin Analysis":
        page_margin_analysis(selected_month, analysis)
    elif page == "Q&A":
        page_qa(selected_month)


if __name__ == "__main__":
    main()
