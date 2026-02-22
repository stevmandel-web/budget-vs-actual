"""
Q&A Engine: builds financial context and queries Claude API.
"""
import json
import streamlit as st

try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


SYSTEM_PROMPT = """You are a financial analyst for Treetop Therapy LLC, an ABA (Applied Behavior Analysis) therapy provider operating across multiple US states with Home-based and Clinic-based service segments.

You have access to the company's Budget vs Actual P&L data. Your role:
- Answer questions about financial performance concisely with specific numbers
- When comparing to budget, clearly note favorable/unfavorable variances
- Always reference margins and percentages alongside dollar amounts
- Highlight trends when multiple months of data are available
- Flag concerns proactively (e.g., negative EBITDA, declining margins)
- Keep answers concise (2-4 paragraphs) unless the user asks for detail

Key terminology:
- BT = Behavior Technician (direct care staff)
- BCBA = Board Certified Behavior Analyst (supervisory staff)
- COGS = Cost of Services (BT/BCBA wages + bonuses)
- GM = Gross Margin (Revenue - COGS)
- EBITDA = Earnings Before Interest, Taxes, Depreciation & Amortization
- Home segment = home-based therapy services
- Clinic segment = clinic-based therapy services
- States: AZ, NC, GA, UT, NM, Other, MGMT"""


def get_api_key():
    """Get Anthropic API key from Streamlit secrets or env."""
    import os
    if hasattr(st, "secrets") and "ANTHROPIC_API_KEY" in st.secrets:
        return st.secrets["ANTHROPIC_API_KEY"]
    return os.environ.get("ANTHROPIC_API_KEY")


def is_available():
    """Check if the Q&A engine can run (SDK installed + API key present)."""
    return HAS_ANTHROPIC and get_api_key() is not None


def build_context(month_abbr, analysis, month_data, budget, available_months, all_months_data=None):
    """
    Build a concise financial context string for Claude.

    Args:
        month_abbr: Current month (e.g., "Jan")
        analysis: Output of compute_month_analysis()
        month_data: Raw parsed data for this month
        budget: Full budget data dict
        available_months: List of (month_abbr, year) tuples
        all_months_data: Optional dict of {month: month_data} for trend context
    """
    from dashboard.pipeline import has_budget_for_month

    lines = []
    lines.append(f"## Current Month: {month_abbr}")

    has_budget = has_budget_for_month(month_abbr, available_months)
    lines.append(f"Has Budget Data: {'Yes' if has_budget else 'No (pre-budget year)'}")
    lines.append(f"Available Months: {', '.join(m for m, y in available_months)}")
    lines.append("")

    # WholeCo P&L summary from variance rows
    wc_var = analysis.get("wholeco_variance", [])
    lines.append("### WholeCo P&L Summary")
    for row in wc_var:
        if row["row_type"] in ("header", "blank"):
            continue
        label = row["label"]
        actual = row.get("actual")
        budget_val = row.get("budget")
        dollar_var = row.get("dollar_var")
        pct_var = row.get("pct_var")
        fav = row.get("favorable")

        if actual is None:
            continue

        parts = [f"{label}: Actual ${actual:,.0f}"]
        if budget_val is not None:
            parts.append(f"Budget ${budget_val:,.0f}")
        if dollar_var is not None and dollar_var != 0:
            direction = "favorable" if fav else "unfavorable"
            parts.append(f"Variance ${dollar_var:+,.0f} ({direction})")
        if pct_var is not None and pct_var != 0:
            parts.append(f"({pct_var*100:+.1f}%)")
        lines.append("- " + " | ".join(parts))

    # Segment summary — segment_variance is a flat list of rows with home_/clinic_ prefixed keys
    seg_rows = analysis.get("segment_variance", [])
    if seg_rows and isinstance(seg_rows, list):
        lines.append("")
        lines.append("### Segment Summary (Home vs Clinic)")
        for segment in ["home", "clinic"]:
            ebitda_row = next((r for r in seg_rows if r.get("label") == "EBITDA"), None)
            rev_row = next((r for r in seg_rows if r.get("label") == "Total Revenue"), None)
            if ebitda_row and rev_row:
                ebitda_a = ebitda_row.get(f"{segment}_actual", 0) or 0
                rev_a = rev_row.get(f"{segment}_actual", 0) or 0
                margin = ebitda_a / rev_a * 100 if rev_a else 0
                line = f"- {segment.title()}: Revenue ${rev_a:,.0f}, EBITDA ${ebitda_a:,.0f} ({margin:.1f}% margin)"
                budget_val = ebitda_row.get(f"{segment}_budget")
                if budget_val is not None:
                    line += f" | Budget EBITDA ${budget_val:,.0f}"
                lines.append(line)

    # State summary
    state_vars = analysis.get("state_variances", {})
    if state_vars:
        lines.append("")
        lines.append("### State Performance")
        for state, rows in state_vars.items():
            rev_row = next((r for r in rows if r.get("label") == "Total Revenue"), None)
            ebitda_row = next((r for r in rows if r.get("label") == "EBITDA"), None)
            if rev_row and ebitda_row:
                rev_a = rev_row.get("actual", 0)
                ebitda_a = ebitda_row.get("actual", 0)
                margin = ebitda_a / rev_a * 100 if rev_a else 0
                line = f"- {state}: Revenue ${rev_a:,.0f}, EBITDA ${ebitda_a:,.0f} ({margin:.1f}% margin)"
                if ebitda_row.get("budget") is not None:
                    line += f" | Budget EBITDA ${ebitda_row['budget']:,.0f}"
                lines.append(line)

    # Key insights
    insights = analysis.get("insights", [])
    if insights:
        lines.append("")
        lines.append("### Key Insights")
        for ins in insights[:8]:
            lines.append(f"- [{ins['severity'].upper()}] {ins['insight']}")

    # Historical trend (if available)
    if all_months_data and len(all_months_data) > 1:
        lines.append("")
        lines.append("### Historical Trend")
        for m in sorted(all_months_data.keys()):
            md = all_months_data[m]
            wc = md.get("wholeco", {})
            rev = wc.get("Total Revenue", 0)
            ebitda = wc.get("EBITDA", 0)
            margin = ebitda / rev * 100 if rev else 0
            lines.append(f"- {m}: Revenue ${rev:,.0f}, EBITDA ${ebitda:,.0f} ({margin:.1f}%)")

    return "\n".join(lines)


def ask(question, context, message_history=None, model="claude-haiku-4-5-20251001"):
    """
    Send a question to Claude with financial context.

    Args:
        question: User's question string
        context: Financial context from build_context()
        message_history: Optional list of prior {"role": ..., "content": ...} dicts
        model: Claude model to use

    Returns:
        str: Claude's response text
    """
    api_key = get_api_key()
    if not api_key:
        return "**API key not configured.** Add `ANTHROPIC_API_KEY` to `.streamlit/secrets.toml` or set as environment variable."

    if not HAS_ANTHROPIC:
        return "**Anthropic SDK not installed.** Run: `pip install anthropic`"

    client = Anthropic(api_key=api_key)

    system = f"{SYSTEM_PROMPT}\n\n---\n\n{context}"

    messages = []
    if message_history:
        # Include recent history for conversational context (last 10 exchanges)
        for msg in message_history[-20:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": question})

    try:
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            system=system,
            messages=messages,
        )
        return response.content[0].text
    except Exception as e:
        return f"**Error querying Claude:** {str(e)}"


def generate_summary_for_gamma(month_abbr, context, model="claude-sonnet-4-5-20250929"):
    """
    Generate a structured 1-pager summary suitable for Gamma presentation.

    Returns a formatted text string with sections for Gamma to render.
    """
    prompt = (
        f"Create a concise executive summary for {month_abbr} financial performance "
        f"at Treetop Therapy.\n\n"
        f"Format it as a structured 1-pager with these sections:\n"
        f"1. **Month at a Glance** - 3-4 bullet points of key metrics "
        f"(Revenue, GM%, EBITDA, EBITDA%)\n"
        f"2. **Performance vs Budget** - 2-3 sentences on budget attainment "
        f"(or vs prior month if no budget)\n"
        f"3. **Segment Highlights** - Home vs Clinic performance, 1-2 bullets each\n"
        f"4. **State Performance** - Top and bottom performing states\n"
        f"5. **Key Risks & Actions** - 2-3 items that need attention\n\n"
        f"Keep it executive-level: concise, numbers-forward, action-oriented. "
        f"Use dollar amounts and percentages."
    )

    return ask(prompt, context, model=model)
