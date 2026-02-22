"""
SLDS Design System: tokens, HTML component builders, Plotly theme, chart builders.
Implements Salesforce Lightning Design System patterns in Streamlit.
"""
import plotly.graph_objects as go


# ═══════════════════════════════════════════════════════════════════════
# SLDS DESIGN TOKENS
# ═══════════════════════════════════════════════════════════════════════

SLDS = {
    # Core
    "brand":         "#1589ee",
    "brand_dark":    "#0070d2",
    "success":       "#4bca81",
    "success_dark":  "#04844b",
    "error":         "#c23934",
    "error_dark":    "#870500",
    "warning":       "#ff9a3c",
    "warning_dark":  "#fe9339",
    # Backgrounds
    "bg_page":       "#f4f6f9",
    "bg_card":       "#ffffff",
    "bg_row_alt":    "#f4f6f9",
    "bg_header":     "#eef1f6",
    "bg_success":    "rgba(75,202,129,0.10)",
    "bg_error":      "rgba(194,57,52,0.10)",
    # Text
    "text_default":  "#080707",
    "text_secondary":"#706e6b",
    "text_inverse":  "#ffffff",
    # Borders
    "border":        "#e5e5e5",
    "border_focus":  "#1589ee",
    # Shadows
    "shadow_card":   "0 2px 2px 0 rgba(0,0,0,0.10)",
}

FONT_FAMILY = "'Salesforce Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"

# Chart color sequence
CHART_COLORS = [SLDS["brand"], SLDS["warning"], SLDS["success"], SLDS["error"], "#54698d", "#a8b7c7"]


# ═══════════════════════════════════════════════════════════════════════
# GLOBAL CSS STYLESHEET
# ═══════════════════════════════════════════════════════════════════════

GLOBAL_CSS = f"""
<style>
    /* Import Salesforce Sans from CDN */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Override Streamlit defaults */
    .stApp {{
        font-family: {FONT_FAMILY};
    }}
    .block-container {{
        padding-top: 1.5rem;
        padding-bottom: 1rem;
    }}

    /* SLDS Card */
    .slds-card {{
        background: {SLDS["bg_card"]};
        border: 1px solid {SLDS["border"]};
        border-radius: 4px;
        box-shadow: {SLDS["shadow_card"]};
        padding: 0.75rem 1rem;
        margin-bottom: 0.75rem;
    }}
    .slds-card-header {{
        font-size: 0.875rem;
        font-weight: 600;
        color: {SLDS["text_secondary"]};
        text-transform: uppercase;
        letter-spacing: 0.025em;
        margin-bottom: 0.5rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid {SLDS["border"]};
    }}

    /* KPI Card */
    .slds-kpi {{
        background: {SLDS["bg_card"]};
        border: 1px solid {SLDS["border"]};
        border-radius: 4px;
        box-shadow: {SLDS["shadow_card"]};
        padding: 1rem 1.25rem;
        border-left: 4px solid {SLDS["brand"]};
        min-height: 100px;
    }}
    .slds-kpi.positive {{ border-left-color: {SLDS["success"]}; }}
    .slds-kpi.negative {{ border-left-color: {SLDS["error"]}; }}
    .slds-kpi-label {{
        font-size: 0.75rem;
        font-weight: 600;
        color: {SLDS["text_secondary"]};
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.25rem;
    }}
    .slds-kpi-value {{
        font-size: 1.5rem;
        font-weight: 700;
        color: {SLDS["text_default"]};
        margin-bottom: 0.375rem;
        line-height: 1.2;
    }}

    /* Badge / Pill */
    .slds-badge {{
        display: inline-block;
        padding: 0.125rem 0.5rem;
        border-radius: 12px;
        font-size: 0.6875rem;
        font-weight: 600;
        line-height: 1.4;
    }}
    .slds-badge.success {{
        background: {SLDS["success"]};
        color: {SLDS["text_inverse"]};
    }}
    .slds-badge.error {{
        background: {SLDS["error"]};
        color: {SLDS["text_inverse"]};
    }}
    .slds-badge.warning {{
        background: {SLDS["warning"]};
        color: {SLDS["text_default"]};
    }}
    .slds-badge.brand {{
        background: {SLDS["brand"]};
        color: {SLDS["text_inverse"]};
    }}
    .slds-badge.neutral {{
        background: #ecebea;
        color: {SLDS["text_secondary"]};
    }}

    /* SLDS Table */
    .slds-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.8125rem;
        font-variant-numeric: tabular-nums;
    }}
    .slds-table th {{
        background: {SLDS["bg_header"]};
        color: {SLDS["text_secondary"]};
        font-weight: 600;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.025em;
        padding: 0.5rem 0.75rem;
        text-align: left;
        border-bottom: 1px solid {SLDS["border"]};
        position: sticky;
        top: 0;
        z-index: 1;
    }}
    .slds-table th.num {{ text-align: right; }}
    .slds-table td {{
        padding: 0.375rem 0.75rem;
        border-bottom: 1px solid {SLDS["border"]};
        color: {SLDS["text_default"]};
        line-height: 1.8;
    }}
    .slds-table td.num {{ text-align: right; }}
    .slds-table tr:nth-child(even) {{ background: {SLDS["bg_row_alt"]}; }}
    .slds-table tr:nth-child(odd) {{ background: {SLDS["bg_card"]}; }}
    .slds-table tr.section-header td {{
        background: {SLDS["bg_header"]};
        font-weight: 700;
        color: {SLDS["brand_dark"]};
        padding: 0.5rem 0.75rem;
        font-size: 0.8125rem;
    }}
    .slds-table tr.subtotal td {{
        font-weight: 700;
    }}
    .slds-table tr.total td {{
        font-weight: 700;
        border-top: 2px solid {SLDS["brand_dark"]};
    }}
    .slds-table td.favorable {{
        color: {SLDS["success_dark"]};
        background: {SLDS["bg_success"]};
    }}
    .slds-table td.unfavorable {{
        color: {SLDS["error_dark"]};
        background: {SLDS["bg_error"]};
    }}
    .slds-table td.indent {{ padding-left: 2rem; }}
    .slds-table tr.pct-row td {{ font-style: italic; }}

    /* Insight notification */
    .slds-notify {{
        background: {SLDS["bg_card"]};
        border: 1px solid {SLDS["border"]};
        border-radius: 4px;
        border-left: 4px solid {SLDS["brand"]};
        padding: 0.625rem 0.75rem;
        margin-bottom: 0.5rem;
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 0.75rem;
    }}
    .slds-notify.critical {{ border-left-color: {SLDS["error"]}; }}
    .slds-notify.warning {{ border-left-color: {SLDS["warning"]}; }}
    .slds-notify.positive {{ border-left-color: {SLDS["success"]}; }}
    .slds-notify-body {{
        flex: 1;
    }}
    .slds-notify-severity {{
        font-size: 0.6875rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.125rem;
    }}
    .slds-notify.critical .slds-notify-severity {{ color: {SLDS["error"]}; }}
    .slds-notify.warning .slds-notify-severity {{ color: {SLDS["warning_dark"]}; }}
    .slds-notify.positive .slds-notify-severity {{ color: {SLDS["success_dark"]}; }}
    .slds-notify-text {{
        font-size: 0.8125rem;
        color: {SLDS["text_default"]};
        line-height: 1.4;
    }}
    .slds-notify-action {{
        font-size: 0.75rem;
        color: {SLDS["text_secondary"]};
        font-style: italic;
        margin-top: 0.125rem;
    }}

    /* Section header */
    .slds-section {{
        font-size: 1rem;
        font-weight: 700;
        color: {SLDS["text_default"]};
        margin: 1.25rem 0 0.5rem 0;
        padding-top: 0.125rem;
        padding-bottom: 0.375rem;
        border-bottom: 2px solid {SLDS["brand"]};
        line-height: 1.5;
    }}
    .slds-page-header {{
        font-size: 1.25rem;
        font-weight: 700;
        color: {SLDS["text_default"]};
        padding-top: 0.5rem;
        margin-top: 0.25rem;
        margin-bottom: 1rem;
        line-height: 1.5;
    }}
</style>
"""


# ═══════════════════════════════════════════════════════════════════════
# FORMATTING HELPERS
# ═══════════════════════════════════════════════════════════════════════

def fmt_dollar(val, show_sign=False):
    if val is None:
        return "\u2014"
    if show_sign:
        return f"${val:+,.0f}"
    if val < 0:
        return f"(${abs(val):,.0f})"
    return f"${val:,.0f}"


def fmt_pct(val, show_sign=False):
    if val is None:
        return "\u2014"
    if show_sign:
        return f"{val * 100:+.1f}pp"
    return f"{val * 100:.1f}%"


def fmt_compact(val):
    if val is None:
        return "\u2014"
    abs_val = abs(val)
    sign = "-" if val < 0 else ""
    if abs_val >= 1_000_000:
        return f"{sign}${abs_val / 1_000_000:.1f}M"
    if abs_val >= 1_000:
        return f"{sign}${abs_val / 1_000:.0f}K"
    return f"{sign}${abs_val:,.0f}"


def _pct_value(label, data_dict):
    """Compute a pct_row value from a flat {line_item: value} dict.

    Returns numerator / Total Revenue for any pct_row label.
    Handles special names (Gross Margin → Gross Profit) and the generic
    pattern where 'X, %' → X / Total Revenue.
    """
    from engine.variance import _pct_numerator_label
    rev = data_dict.get("Total Revenue", 0)
    if not rev:
        return 0
    base_label = _pct_numerator_label(label)
    return data_dict.get(base_label, 0) / rev


# ═══════════════════════════════════════════════════════════════════════
# HTML COMPONENT BUILDERS
# ═══════════════════════════════════════════════════════════════════════

def html_kpi_card(label, value, delta_text, delta_positive=True):
    """Render an SLDS KPI card as HTML."""
    cls = "positive" if delta_positive else "negative"
    badge_cls = "success" if delta_positive else "error"
    return f"""
    <div class="slds-kpi {cls}">
        <div class="slds-kpi-label">{label}</div>
        <div class="slds-kpi-value">{value}</div>
        <span class="slds-badge {badge_cls}">{delta_text}</span>
    </div>
    """


def html_badge(text, variant="brand"):
    """Render an SLDS badge/pill."""
    return f'<span class="slds-badge {variant}">{text}</span>'


def html_section_header(title):
    """Render an SLDS section header."""
    return f'<div class="slds-section">{title}</div>'


def html_insight(severity, text, action="", impact_text=""):
    """Render an SLDS scoped notification for an insight."""
    sev_cls = severity if severity in ("critical", "warning", "positive") else ""
    impact_html = f'<span class="slds-badge {"error" if "over" in impact_text.lower() or "-" in impact_text else "success"}">{impact_text}</span>' if impact_text else ""
    action_html = f'<div class="slds-notify-action">{action}</div>' if action else ""
    return f"""
    <div class="slds-notify {sev_cls}">
        <div class="slds-notify-body">
            <div class="slds-notify-severity">{severity}</div>
            <div class="slds-notify-text">{text}</div>
            {action_html}
        </div>
        {impact_html}
    </div>
    """


def html_variance_table(variance_rows, compact=False, show_budget=True):
    """Render a full P&L variance table as SLDS HTML.

    When show_budget=False, only Line Item + Actual columns are shown (no budget/variance).
    """
    ncols = 5 if show_budget else 2
    rows_html = []
    for vr in variance_rows:
        rt = vr.get("row_type", "")
        label = vr.get("label", "")

        if rt == "blank":
            continue

        if rt == "header":
            rows_html.append(f'<tr class="section-header"><td colspan="{ncols}">{label}</td></tr>')
            continue

        is_pct = rt == "pct_row"
        fav = vr.get("favorable")
        actual = vr.get("actual")
        budget_val = vr.get("budget")
        dollar_var = vr.get("dollar_var")
        pct_var = vr.get("pct_var")

        # Format values
        if is_pct:
            act_str = fmt_pct(actual) if actual is not None else "\u2014"
            bud_str = fmt_pct(budget_val) if budget_val is not None else "\u2014"
            var_str = fmt_pct(dollar_var, show_sign=True) if dollar_var is not None else "\u2014"
            pct_str = ""
        else:
            act_str = fmt_dollar(actual) if actual is not None else "\u2014"
            bud_str = fmt_dollar(budget_val) if budget_val is not None else "\u2014"
            var_str = fmt_dollar(dollar_var, show_sign=True) if dollar_var is not None else "\u2014"
            pct_str = f"{pct_var * 100:+.1f}%" if pct_var is not None else "\u2014"

        # Row class
        row_cls_parts = []
        if rt == "total":
            row_cls_parts.append("total")
        elif rt == "subtotal":
            row_cls_parts.append("subtotal")
        if is_pct:
            row_cls_parts.append("pct-row")
        row_cls = " ".join(row_cls_parts)

        # Variance cell class
        var_cls = ""
        if fav is True:
            var_cls = "favorable"
        elif fav is False:
            var_cls = "unfavorable"

        # Indent items
        td_cls = ' class="indent"' if rt == "item" else ""

        if compact and actual is None and budget_val is None:
            continue

        if show_budget:
            rows_html.append(f"""
            <tr class="{row_cls}">
                <td{td_cls}>{label}</td>
                <td class="num">{act_str}</td>
                <td class="num">{bud_str}</td>
                <td class="num {var_cls}">{var_str}</td>
                <td class="num {var_cls}">{pct_str}</td>
            </tr>""")
        else:
            rows_html.append(f"""
            <tr class="{row_cls}">
                <td{td_cls}>{label}</td>
                <td class="num">{act_str}</td>
            </tr>""")

    if show_budget:
        header = """
        <div style="overflow-y: auto;">
        <table class="slds-table">
            <thead>
                <tr>
                    <th>Line Item</th>
                    <th class="num">Actual</th>
                    <th class="num">Budget</th>
                    <th class="num">$ Variance</th>
                    <th class="num">% Variance</th>
                </tr>
            </thead>
            <tbody>
        """
    else:
        header = """
        <div style="overflow-y: auto;">
        <table class="slds-table">
            <thead>
                <tr>
                    <th>Line Item</th>
                    <th class="num">Actual</th>
                </tr>
            </thead>
            <tbody>
        """
    footer = "</tbody></table></div>"
    return header + "\n".join(rows_html) + footer


def html_simple_table(rows, columns):
    """Render a simple data table as SLDS HTML.
    rows: list of dicts, columns: list of (key, label, is_numeric)
    """
    header_cells = "".join(
        f'<th class="{"num" if is_num else ""}">{label}</th>'
        for _, label, is_num in columns
    )
    body_rows = []
    for row in rows:
        cells = "".join(
            f'<td class="{"num" if is_num else ""}">{row.get(key, "")}</td>'
            for key, _, is_num in columns
        )
        body_rows.append(f"<tr>{cells}</tr>")

    return f"""
    <table class="slds-table">
        <thead><tr>{header_cells}</tr></thead>
        <tbody>{"".join(body_rows)}</tbody>
    </table>
    """


def html_mom_table(all_months_data, budget_segment, months_chrono,
                   segment_key, selected_month, available_months):
    """Render month-over-month P&L table with MoM and budget deltas.

    Args:
        all_months_data: {month_abbr: full_month_dict} for all loaded months
        budget_segment: budget dict for segment, e.g. {line_item: {month: val}}
        months_chrono: [(month_abbr, year), ...] sorted chronologically
        segment_key: "wholeco" | "home" | "clinic"
        selected_month: sidebar-selected month (used for budget column)
        available_months: raw available months list for budget check
    """
    from config import PNL_STRUCTURE
    from dashboard.pipeline import has_budget_for_month

    DASH = "\u2014"
    month_abbrs = [m for m, y in months_chrono]
    has_bud = has_budget_for_month(selected_month, available_months)

    # Build header row
    month_ths = "".join(f'<th class="num">{m}</th>' for m in month_abbrs)
    header_html = f"""
    <div style="overflow-x: auto; overflow-y: auto;">
    <table class="slds-table" style="min-width: {200 + len(month_abbrs) * 100 + 400}px;">
      <thead><tr>
        <th style="position:sticky;left:0;z-index:3;background:{SLDS['bg_header']};">Line Item</th>
        {month_ths}
        <th class="num">MoM $&Delta;</th>
        <th class="num">MoM %</th>
        <th class="num">Budget</th>
        <th class="num">Bud $&Delta;</th>
        <th class="num">Bud %</th>
      </tr></thead>
      <tbody>
    """

    rows = []
    ncols = len(month_abbrs) + 6  # months + 5 delta/budget cols
    computed_by_month = {m: {} for m in month_abbrs}
    computed_budget = {}

    for label, row_type, is_revenue_like in PNL_STRUCTURE:
        if row_type == "blank":
            continue
        if row_type == "header":
            rows.append(
                f'<tr class="section-header">'
                f'<td style="position:sticky;left:0;z-index:2;background:{SLDS["bg_header"]};" '
                f'colspan="{ncols + 1}">{label}</td></tr>'
            )
            continue

        is_pct = row_type == "pct_row"

        # Get value for each month
        month_vals = []
        for m in month_abbrs:
            md = all_months_data.get(m, {}).get(segment_key, {})
            if is_pct:
                val = _pct_value(label, computed_by_month[m])
            else:
                val = md.get(label, 0)
                computed_by_month[m][label] = val
            month_vals.append(val)

        # MoM delta (last - second-to-last)
        if len(month_vals) >= 2 and month_vals[-2] is not None:
            mom_dollar = month_vals[-1] - month_vals[-2]
            mom_pct = mom_dollar / abs(month_vals[-2]) if month_vals[-2] != 0 else 0
        else:
            mom_dollar = None
            mom_pct = None

        # Budget values
        if has_bud and not is_pct:
            bud_val = budget_segment.get(label, {}).get(selected_month, 0)
            computed_budget[label] = bud_val
            bud_dollar = month_vals[-1] - bud_val if month_vals else None
            bud_pct = bud_dollar / abs(bud_val) if bud_val else 0
        elif has_bud and is_pct:
            bud_val = _pct_value(label, computed_budget)
            bud_dollar = month_vals[-1] - bud_val if month_vals else None
            bud_pct = None  # pct of pct not meaningful
        else:
            bud_val = None
            bud_dollar = None
            bud_pct = None

        # Row class
        row_cls_parts = []
        if row_type == "total":
            row_cls_parts.append("total")
        elif row_type == "subtotal":
            row_cls_parts.append("subtotal")
        if is_pct:
            row_cls_parts.append("pct-row")
        row_cls = " ".join(row_cls_parts)
        td_cls = ' class="indent"' if row_type == "item" else ""
        sticky = f'style="position:sticky;left:0;z-index:2;background:{SLDS["bg_card"]};"'

        # Favorable/unfavorable helpers
        def _var_cls(delta, is_rev_like):
            if delta is None or delta == 0:
                return ""
            if is_rev_like:
                return "favorable" if delta > 0 else "unfavorable"
            else:
                return "favorable" if delta < 0 else "unfavorable"

        # Build cells
        cells = f'<td{td_cls} {sticky}>{label}</td>'

        # Month value cells
        for val in month_vals:
            cells += f'<td class="num">{fmt_pct(val) if is_pct else fmt_dollar(val)}</td>'

        # MoM delta cells (with highlighting)
        if mom_dollar is not None:
            mcls = _var_cls(mom_dollar, is_revenue_like)
            if is_pct:
                cells += f'<td class="num {mcls}">{mom_dollar * 100:+.1f}pp</td>'
                cells += f'<td class="num">{DASH}</td>'
            else:
                cells += f'<td class="num {mcls}">{fmt_dollar(mom_dollar, show_sign=True)}</td>'
                cells += f'<td class="num {mcls}">{mom_pct * 100:+.1f}%</td>'
        else:
            cells += f'<td class="num">{DASH}</td><td class="num">{DASH}</td>'

        # Budget cells (with highlighting)
        if bud_val is not None:
            bcls = _var_cls(bud_dollar, is_revenue_like) if bud_dollar else ""
            if is_pct:
                cells += f'<td class="num">{fmt_pct(bud_val)}</td>'
                cells += f'<td class="num {bcls}">{bud_dollar * 100:+.1f}pp</td>' if bud_dollar is not None else f'<td class="num">{DASH}</td>'
                cells += f'<td class="num">{DASH}</td>'
            else:
                cells += f'<td class="num">{fmt_dollar(bud_val)}</td>'
                cells += f'<td class="num {bcls}">{fmt_dollar(bud_dollar, show_sign=True)}</td>' if bud_dollar is not None else f'<td class="num">{DASH}</td>'
                cells += f'<td class="num {bcls}">{bud_pct * 100:+.1f}%</td>' if bud_pct else f'<td class="num">{DASH}</td>'
        else:
            cells += f'<td class="num">{DASH}</td>' * 3

        rows.append(f'<tr class="{row_cls}">{cells}</tr>')

    footer = "</tbody></table></div>"
    return header_html + "\n".join(rows) + footer


def html_clinic_comparison_table(clinics_detail, clinic_names, budget_gm_pct=None):
    """Render a wide horizontally scrolling table with one column per clinic.

    Args:
        clinics_detail: {clinic_name: {line_item: value, ...}}
        clinic_names: ordered list of clinic names to display
        budget_gm_pct: optional GM% benchmark from clinic segment budget
    """
    from config import PNL_STRUCTURE

    DASH = "\u2014"
    ncols = 1 + len(clinic_names)  # Line Item + clinics

    # Header
    clinic_ths = "".join(
        f'<th class="num" style="min-width:90px;">{c.split("-")[-1] if "-" in c else c}</th>'
        for c in clinic_names
    )
    header_html = f"""
    <div style="overflow-x: auto; overflow-y: auto;">
    <table class="slds-table" style="min-width: {200 + len(clinic_names) * 100}px;">
      <thead><tr>
        <th style="position:sticky;left:0;z-index:3;background:{SLDS['bg_header']};min-width:180px;">Line Item</th>
        {clinic_ths}
      </tr></thead>
      <tbody>
    """

    rows = []
    # Track computed values per clinic for pct rows
    computed = {c: {} for c in clinic_names}

    for label, row_type, is_revenue_like in PNL_STRUCTURE:
        if row_type == "blank":
            continue
        if row_type == "header":
            rows.append(
                f'<tr class="section-header">'
                f'<td style="position:sticky;left:0;z-index:2;background:{SLDS["bg_header"]};" '
                f'colspan="{ncols}">{label}</td></tr>'
            )
            continue

        is_pct = row_type == "pct_row"

        # Get values for each clinic
        vals = []
        all_zero = True
        for c in clinic_names:
            cd = clinics_detail.get(c, {})
            if is_pct:
                val = _pct_value(label, computed[c])
            else:
                val = cd.get(label, 0)
                computed[c][label] = val
            if val != 0:
                all_zero = False
            vals.append(val)

        # Skip rows where all clinics have zero (except totals/subtotals)
        if all_zero and row_type == "item":
            continue

        row_cls_parts = []
        if row_type == "total":
            row_cls_parts.append("total")
        elif row_type == "subtotal":
            row_cls_parts.append("subtotal")
        if is_pct:
            row_cls_parts.append("pct-row")
        row_cls = " ".join(row_cls_parts)
        td_cls = ' class="indent"' if row_type == "item" else ""
        sticky = f'style="position:sticky;left:0;z-index:2;background:{SLDS["bg_card"]};"'

        cells = f'<td{td_cls} {sticky}>{label}</td>'
        for val in vals:
            if is_pct:
                # Color GM% cells relative to budget benchmark
                cell_cls = "num"
                if budget_gm_pct is not None and "Gross Margin" in label and val != 0:
                    cell_cls += " favorable" if val >= budget_gm_pct else " unfavorable"
                cells += f'<td class="{cell_cls}">{fmt_pct(val)}</td>'
            else:
                cells += f'<td class="num">{fmt_dollar(val) if val != 0 else DASH}</td>'

        rows.append(f'<tr class="{row_cls}">{cells}</tr>')

    # Add budget GM% benchmark row if available
    if budget_gm_pct is not None:
        sticky = f'style="position:sticky;left:0;z-index:2;background:{SLDS["bg_header"]};"'
        cells = f'<td {sticky}><strong>Budget GM% Benchmark</strong></td>'
        for _ in clinic_names:
            cells += f'<td class="num"><strong>{fmt_pct(budget_gm_pct)}</strong></td>'
        rows.append(f'<tr class="subtotal">{cells}</tr>')

    footer = "</tbody></table></div>"
    return header_html + "\n".join(rows) + footer


def html_state_comparison_table(states_data, state_names, budget_states=None, month=None):
    """Render a wide horizontally scrolling table with one column per state.

    Args:
        states_data: {state_abbr: {line_item: value, ...}}
        state_names: ordered list of state abbreviations to display
        budget_states: optional {state: {line_item: {month: val}}} for GM% benchmark
        month: current month abbreviation (for budget lookup)
    """
    from config import PNL_STRUCTURE

    DASH = "\u2014"
    ncols = 1 + len(state_names)

    # Compute WholeCo GM% benchmark from budget if available
    budget_gm_pct = None
    if budget_states and month:
        total_bud_rev = sum(
            budget_states.get(s, {}).get("Total Revenue", {}).get(month, 0)
            for s in state_names
        )
        total_bud_gp = sum(
            budget_states.get(s, {}).get("Gross Profit", {}).get(month, 0)
            for s in state_names
        )
        budget_gm_pct = total_bud_gp / total_bud_rev if total_bud_rev else None

    # Header
    state_ths = "".join(
        f'<th class="num" style="min-width:90px;">{s}</th>'
        for s in state_names
    )
    header_html = f"""
    <div style="overflow-x: auto; overflow-y: auto;">
    <table class="slds-table" style="min-width: {200 + len(state_names) * 100}px;">
      <thead><tr>
        <th style="position:sticky;left:0;z-index:3;background:{SLDS['bg_header']};min-width:180px;">Line Item</th>
        {state_ths}
      </tr></thead>
      <tbody>
    """

    rows = []
    computed = {s: {} for s in state_names}

    for label, row_type, is_revenue_like in PNL_STRUCTURE:
        if row_type == "blank":
            continue
        if row_type == "header":
            rows.append(
                f'<tr class="section-header">'
                f'<td style="position:sticky;left:0;z-index:2;background:{SLDS["bg_header"]};" '
                f'colspan="{ncols}">{label}</td></tr>'
            )
            continue

        is_pct = row_type == "pct_row"

        vals = []
        all_zero = True
        for s in state_names:
            sd = states_data.get(s, {})
            if is_pct:
                val = _pct_value(label, computed[s])
            else:
                val = sd.get(label, 0)
                computed[s][label] = val
            if val != 0:
                all_zero = False
            vals.append(val)

        if all_zero and row_type == "item":
            continue

        row_cls_parts = []
        if row_type == "total":
            row_cls_parts.append("total")
        elif row_type == "subtotal":
            row_cls_parts.append("subtotal")
        if is_pct:
            row_cls_parts.append("pct-row")
        row_cls = " ".join(row_cls_parts)
        td_cls = ' class="indent"' if row_type == "item" else ""
        sticky = f'style="position:sticky;left:0;z-index:2;background:{SLDS["bg_card"]};"'

        cells = f'<td{td_cls} {sticky}>{label}</td>'
        for val in vals:
            if is_pct:
                cell_cls = "num"
                if budget_gm_pct is not None and "Gross Margin" in label and val != 0:
                    cell_cls += " favorable" if val >= budget_gm_pct else " unfavorable"
                cells += f'<td class="{cell_cls}">{fmt_pct(val)}</td>'
            else:
                cells += f'<td class="num">{fmt_dollar(val) if val != 0 else DASH}</td>'

        rows.append(f'<tr class="{row_cls}">{cells}</tr>')

    footer = "</tbody></table></div>"
    return header_html + "\n".join(rows) + footer


def html_entity_mom_table(current_data, prior_data, current_label, prior_label,
                          budget_data=None, month=None):
    """Render a P&L table comparing current period vs prior period with deltas.

    Shows: Line Item | Current | Prior | MoM $ | MoM % | (optional: Budget | Bud $ | Bud %)

    Args:
        current_data: {line_item: value} for current period
        prior_data: {line_item: value} for prior period (or empty dict)
        current_label: column header for current period (e.g. "Jan")
        prior_label: column header for prior period (e.g. "Dec")
        budget_data: optional {line_item: {month: val}} or {line_item: val} for budget
        month: month abbreviation for budget lookup
    """
    from config import PNL_STRUCTURE

    DASH = "\u2014"
    has_prior = bool(prior_data)
    has_bud = budget_data is not None and month is not None

    # Build header
    cols = [f'<th class="num">{current_label}</th>']
    if has_prior:
        cols += [
            f'<th class="num">{prior_label}</th>',
            '<th class="num">MoM $&Delta;</th>',
            '<th class="num">MoM %</th>',
        ]
    if has_bud:
        cols += [
            '<th class="num">Budget</th>',
            '<th class="num">Bud $&Delta;</th>',
            '<th class="num">Bud %</th>',
        ]
    ncols = 1 + len(cols)  # Line Item + data columns

    header_html = f"""
    <div style="overflow-x: auto; overflow-y: auto;">
    <table class="slds-table">
      <thead><tr>
        <th style="min-width:180px;">Line Item</th>
        {"".join(cols)}
      </tr></thead>
      <tbody>
    """

    rows = []
    computed_cur = {}
    computed_prior = {}
    computed_bud = {}

    for label, row_type, is_revenue_like in PNL_STRUCTURE:
        if row_type == "blank":
            continue
        if row_type == "header":
            rows.append(f'<tr class="section-header"><td colspan="{ncols}">{label}</td></tr>')
            continue

        is_pct = row_type == "pct_row"

        # Current value
        if is_pct:
            cur_val = _pct_value(label, computed_cur)
        else:
            cur_val = current_data.get(label, 0)
            computed_cur[label] = cur_val

        # Prior value
        if has_prior:
            if is_pct:
                pri_val = _pct_value(label, computed_prior)
            else:
                pri_val = prior_data.get(label, 0)
                computed_prior[label] = pri_val
        else:
            pri_val = 0

        # Budget value
        if has_bud:
            if is_pct:
                bud_val = _pct_value(label, computed_bud)
            else:
                raw = budget_data.get(label, {})
                bud_val = raw.get(month, 0) if isinstance(raw, dict) else raw
                computed_bud[label] = bud_val
        else:
            bud_val = 0

        # Row styling
        row_cls_parts = []
        if row_type == "total":
            row_cls_parts.append("total")
        elif row_type == "subtotal":
            row_cls_parts.append("subtotal")
        if is_pct:
            row_cls_parts.append("pct-row")
        row_cls = " ".join(row_cls_parts)
        td_cls = ' class="indent"' if row_type == "item" else ""

        # Highlighting helper
        def _var_cls(delta):
            if delta is None or delta == 0 or is_revenue_like is None:
                return ""
            favorable = (delta > 0) == is_revenue_like
            return "favorable" if favorable else "unfavorable"

        # Build cells
        cells = f'<td{td_cls}>{label}</td>'

        # Current
        cells += f'<td class="num">{fmt_pct(cur_val) if is_pct else fmt_dollar(cur_val)}</td>'

        # Prior + MoM deltas
        if has_prior:
            cells += f'<td class="num">{fmt_pct(pri_val) if is_pct else fmt_dollar(pri_val)}</td>'
            mom = cur_val - pri_val
            mcls = _var_cls(mom)
            if is_pct:
                cells += f'<td class="num {mcls}">{mom * 100:+.1f}pp</td>'
                cells += f'<td class="num">{DASH}</td>'
            else:
                mom_pct = mom / abs(pri_val) if pri_val else 0
                cells += f'<td class="num {mcls}">{fmt_dollar(mom, show_sign=True)}</td>'
                cells += f'<td class="num {mcls}">{mom_pct * 100:+.1f}%</td>' if pri_val else f'<td class="num">{DASH}</td>'

        # Budget + deltas
        if has_bud:
            cells += f'<td class="num">{fmt_pct(bud_val) if is_pct else fmt_dollar(bud_val)}</td>'
            bud_delta = cur_val - bud_val
            bcls = _var_cls(bud_delta)
            if is_pct:
                cells += f'<td class="num {bcls}">{bud_delta * 100:+.1f}pp</td>'
                cells += f'<td class="num">{DASH}</td>'
            else:
                bud_pct = bud_delta / abs(bud_val) if bud_val else 0
                cells += f'<td class="num {bcls}">{fmt_dollar(bud_delta, show_sign=True)}</td>'
                cells += f'<td class="num {bcls}">{bud_pct * 100:+.1f}%</td>' if bud_val else f'<td class="num">{DASH}</td>'

        rows.append(f'<tr class="{row_cls}">{cells}</tr>')

    footer = "</tbody></table></div>"
    return header_html + "\n".join(rows) + footer


# ═══════════════════════════════════════════════════════════════════════
# PLOTLY THEME
# ═══════════════════════════════════════════════════════════════════════

def _slds_layout(**overrides):
    """Base SLDS Plotly layout."""
    base = dict(
        font=dict(family=FONT_FAMILY, size=12, color=SLDS["text_default"]),
        plot_bgcolor=SLDS["bg_card"],
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=10, b=30, l=50, r=20),
        showlegend=True,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
            font=dict(size=11),
        ),
        xaxis=dict(gridcolor=SLDS["border"], gridwidth=0.5, zeroline=False),
        yaxis=dict(gridcolor=SLDS["border"], gridwidth=0.5, zeroline=False,
                   tickformat="$,.0f"),
    )
    base.update(overrides)
    return base


# ═══════════════════════════════════════════════════════════════════════
# CHART BUILDERS
# ═══════════════════════════════════════════════════════════════════════

def make_waterfall_chart(waterfall_data, month):
    labels = [w[0] for w in waterfall_data]
    values = [w[1] for w in waterfall_data]
    measures = ["absolute"] + ["relative"] * (len(values) - 2) + ["total"]

    fig = go.Figure(go.Waterfall(
        orientation="v", measure=measures, x=labels, y=values,
        connector={"line": {"color": SLDS["border"], "width": 1}},
        increasing={"marker": {"color": SLDS["success"]}},
        decreasing={"marker": {"color": SLDS["error"]}},
        totals={"marker": {"color": SLDS["brand"]}},
        text=[f"${v:+,.0f}" if 0 < i < len(values) - 1 else f"${v:,.0f}"
              for i, v in enumerate(values)],
        textposition="outside", textfont={"size": 10},
    ))
    fig.update_layout(**_slds_layout(height=380, showlegend=False))
    return fig


def make_dual_trend_chart(all_months_data, budget_data, months_order, available_months=None):
    from dashboard.pipeline import has_budget_for_month

    rev_actual, rev_budget, ebitda_actual, ebitda_budget = [], [], [], []
    ebitda_pct_actual, ebitda_pct_budget = [], []
    for m in months_order:
        wc = all_months_data.get(m, {}).get("wholeco", {})
        rev_a = wc.get("Total Revenue", 0)
        ebitda_a = wc.get("EBITDA", 0)
        rev_actual.append(rev_a)
        ebitda_actual.append(ebitda_a)
        ebitda_pct_actual.append(ebitda_a / rev_a * 100 if rev_a else 0)
        # Only show budget for months that actually have budget data
        if available_months and not has_budget_for_month(m, available_months):
            rev_budget.append(None)
            ebitda_budget.append(None)
            ebitda_pct_budget.append(None)
        else:
            rev_b = budget_data.get("wholeco", {}).get("Total Revenue", {}).get(m, 0)
            ebitda_b = budget_data.get("wholeco", {}).get("EBITDA", {}).get(m, 0)
            rev_budget.append(rev_b)
            ebitda_budget.append(ebitda_b)
            ebitda_pct_budget.append(ebitda_b / rev_b * 100 if rev_b else 0)

    # EBITDA % hover text for the EBITDA lines
    ebitda_hover = [f"${v:,.0f} ({p:.1f}%)" if v else "" for v, p in zip(ebitda_actual, ebitda_pct_actual)]
    ebitda_bud_hover = [f"${v:,.0f} ({p:.1f}%)" if v else "" for v, p in zip(ebitda_budget, ebitda_pct_budget)]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=months_order, y=rev_actual, name="Revenue (Actual)",
                         marker_color=SLDS["brand"], opacity=0.8))
    fig.add_trace(go.Bar(x=months_order, y=rev_budget, name="Revenue (Budget)",
                         marker_color=SLDS["warning"], opacity=0.5))
    fig.add_trace(go.Scatter(x=months_order, y=ebitda_actual, name="EBITDA (Actual)",
                             line=dict(color=SLDS["success"], width=3),
                             mode="lines+markers+text", yaxis="y2",
                             text=[f"{p:.1f}%" for p in ebitda_pct_actual],
                             textposition="top center",
                             textfont=dict(size=10, color=SLDS["success"]),
                             customdata=ebitda_hover,
                             hovertemplate="%{customdata}<extra>EBITDA (Actual)</extra>"))
    fig.add_trace(go.Scatter(x=months_order, y=ebitda_budget, name="EBITDA (Budget)",
                             line=dict(color=SLDS["success"], width=2, dash="dash"),
                             mode="lines+markers", yaxis="y2",
                             customdata=ebitda_bud_hover,
                             hovertemplate="%{customdata}<extra>EBITDA (Budget)</extra>"))
    fig.update_layout(**_slds_layout(
        height=380, barmode="group",
        yaxis=dict(title="Revenue ($)", tickformat="$,.0f", gridcolor=SLDS["border"]),
        yaxis2=dict(title="EBITDA ($)", tickformat="$,.0f", overlaying="y", side="right",
                    gridcolor=SLDS["border"]),
    ))
    return fig


def make_trend_chart(all_months_data, budget_data, metric, months_order, title=None):
    actuals, budgets, labels = [], [], []
    for m in months_order:
        labels.append(m)
        wc = all_months_data.get(m, {}).get("wholeco", {})
        actuals.append(wc.get(metric, 0))
        budgets.append(budget_data.get("wholeco", {}).get(metric, {}).get(m, 0))

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=labels, y=actuals, name="Actual",
                             line=dict(color=SLDS["brand"], width=3),
                             mode="lines+markers", marker=dict(size=8)))
    fig.add_trace(go.Scatter(x=labels, y=budgets, name="Budget",
                             line=dict(color=SLDS["warning"], width=2, dash="dash"),
                             mode="lines+markers", marker=dict(size=6)))
    fig.update_layout(**_slds_layout(height=320, hovermode="x unified"))
    return fig


def make_variance_bars(variance_rows, top_n=5, favorable=False):
    # Exclude wage items — budget wage data is known to be inaccurate
    _EXCLUDE_LABELS = {"BT Wages", "BCBA Wages", "BT Bonus", "BCBA Performance Bonus", "BCBA Sign-On Bonus"}
    items = [r for r in variance_rows
             if r.get("row_type") == "item" and r.get("dollar_var") is not None
             and r["dollar_var"] != 0 and r.get("favorable") == favorable
             and r.get("label") not in _EXCLUDE_LABELS]
    items.sort(key=lambda x: abs(x["dollar_var"]), reverse=True)
    items = items[:top_n]
    if not items:
        return None

    labels = [i["label"] for i in items]
    values = [i["dollar_var"] for i in items]
    color = SLDS["success"] if favorable else SLDS["error"]

    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h", marker_color=color,
        text=[f"${v:+,.0f}" for v in values], textposition="auto",
    ))
    fig.update_layout(**_slds_layout(
        height=max(180, 48 * len(items) + 60),
        showlegend=False,
        yaxis=dict(autorange="reversed", gridcolor=SLDS["border"]),
        xaxis=dict(tickformat="$,.0f", gridcolor=SLDS["border"]),
        margin=dict(t=10, b=20, l=140, r=20),
    ))
    return fig


def make_state_revenue_chart(states_data, budget_states, month):
    states = sorted([s for s in states_data.keys() if s != "MGMT"])
    actuals = [states_data[s].get("Total Revenue", 0) for s in states]
    budgets = []
    for s in states:
        bud = budget_states.get(s, {})
        rev = bud.get("Total Revenue", {})
        budgets.append(rev.get(month, 0) if isinstance(rev, dict) else 0)

    fig = go.Figure(data=[
        go.Bar(name="Actual", x=states, y=actuals, marker_color=SLDS["brand"]),
        go.Bar(name="Budget", x=states, y=budgets, marker_color=SLDS["warning"]),
    ])
    fig.update_layout(**_slds_layout(height=340, barmode="group"))
    return fig


def make_clinic_revenue_chart(clinics_detail):
    pairs = sorted(
        [(c, clinics_detail[c].get("Total Revenue", 0)) for c in clinics_detail],
        key=lambda x: x[1], reverse=True,
    )
    clinics = [p[0] for p in pairs]
    revenues = [p[1] for p in pairs]

    fig = go.Figure(go.Bar(
        x=revenues, y=clinics, orientation="h", marker_color=SLDS["brand"],
        text=[f"${v:,.0f}" for v in revenues], textposition="auto",
    ))
    fig.update_layout(**_slds_layout(
        height=max(220, 36 * len(clinics) + 60),
        showlegend=False,
        yaxis=dict(autorange="reversed", gridcolor=SLDS["border"]),
        xaxis=dict(tickformat="$,.0f", gridcolor=SLDS["border"]),
        margin=dict(t=10, b=20, l=120, r=20),
    ))
    return fig


# ── Margin Analysis Charts ────────────────────────────────────────────

def make_cogs_breakdown_chart(margin_items):
    """Horizontal grouped bar: COGS components actual vs budget."""
    cogs = [m for m in margin_items if m["category"] == "COGS Detail"]
    if not cogs:
        return None
    labels = [m["metric"] for m in cogs]
    actuals = [m["actual_val"] for m in cogs]
    budgets = [m["budget_val"] for m in cogs]

    fig = go.Figure(data=[
        go.Bar(name="Actual", y=labels, x=actuals, orientation="h", marker_color=SLDS["brand"]),
        go.Bar(name="Budget", y=labels, x=budgets, orientation="h", marker_color=SLDS["warning"]),
    ])
    fig.update_layout(**_slds_layout(
        height=max(200, 50 * len(labels) + 60),
        barmode="group",
        yaxis=dict(autorange="reversed", gridcolor=SLDS["border"]),
        xaxis=dict(tickformat="$,.0f", gridcolor=SLDS["border"]),
        margin=dict(t=10, b=20, l=160, r=20),
    ))
    return fig


def make_state_margin_chart(margin_items):
    """Bar chart: GM% by state, actual vs budget."""
    states = [m for m in margin_items if m["category"] == "State Detail" and "Gross Margin" in m["metric"]]
    if not states:
        return None
    labels = [m["metric"].replace(" Gross Margin %", "") for m in states]
    actuals = [m["actual_val"] * 100 for m in states]
    budgets = [m["budget_val"] * 100 for m in states]

    fig = go.Figure(data=[
        go.Bar(name="Actual GM%", x=labels, y=actuals, marker_color=SLDS["brand"]),
        go.Bar(name="Budget GM%", x=labels, y=budgets, marker_color=SLDS["warning"]),
    ])
    fig.update_layout(**_slds_layout(
        height=320, barmode="group",
        yaxis=dict(title="Gross Margin %", ticksuffix="%", gridcolor=SLDS["border"]),
    ))
    return fig


# ═══════════════════════════════════════════════════════════════════════
# SERVICE-LINE MARGIN ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

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

    def _heatmap_cell(val, ref, is_pct=True):
        """Color-code a cell green/red based on comparison to reference."""
        if is_pct:
            text = f"{val * 100:.1f}%"
        else:
            text = f"{val:.1f}x"
        diff = val - ref
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
        text = _dollar_cell(abs(val))
        if val > 1000:
            bg = f"background:{SLDS['bg_success']};"
            text = f"+{text}"
        elif val < -1000:
            bg = f"background:{SLDS['bg_error']};"
            text = f"-{text}"
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
