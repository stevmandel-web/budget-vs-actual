# Publish, AI Q&A, and Excel Export Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enable multi-user access via Streamlit Cloud, add AI-powered Q&A with Claude API + Gamma 1-pager, and add Excel download button to dashboard sidebar.

**Architecture:** Three independent workstreams: (1) Git init + config refactor + password gate for Streamlit Cloud deployment, (2) New `qa_engine.py` module with Claude API context builder + rewritten Q&A tab, (3) Excel download button wiring `build_output_workbook()` through BytesIO to `st.download_button`.

**Tech Stack:** Streamlit Cloud, Anthropic Python SDK, openpyxl (existing), Gamma API (via MCP)

---

### Task 1: Initialize Git Repository

**Files:**
- Create: `.gitignore`

**Step 1: Create .gitignore**

```
__pycache__/
*.pyc
.env
*.xlsx
!requirements.txt
.streamlit/secrets.toml
.DS_Store
*.tmp
```

Note: The `*.xlsx` pattern excludes source Excel files from the repo. The `data/` directory with JSON files WILL be committed (it's the app's data layer).

**Step 2: Initialize git repo**

Run:
```bash
cd "/Users/stevenmandel/Claude Code/budget-vs-actual"
git init
git add .
git commit -m "Initial commit: Budget vs Actual dashboard"
```

Expected: Clean commit with all .py, .json, .toml, .txt, .md files. No .xlsx files.

**Step 3: Verify nothing sensitive is committed**

Run: `git ls-files | grep -E '\.(xlsx|env|secrets)'`
Expected: Empty output (no sensitive files tracked)

---

### Task 2: Refactor Config for Cloud Deployment

**Files:**
- Modify: `config.py` (lines 7-10, 220-221)
- Modify: `dashboard/app.py` (line 14, lines 78-84, lines 186-217)
- Modify: `dashboard/pipeline.py` (line 17)

**Step 1: Make file paths configurable via environment/secrets**

In `config.py`, replace the hardcoded paths (lines 7-10, 220-221) with:

```python
import os

# ── File paths (configurable via env vars for cloud deployment) ───────
DEFAULT_BUDGET_PATH = os.environ.get(
    "BUDGET_PATH",
    "/Users/stevenmandel/Downloads/MASTER 2026 Budget vBase_3.xlsx"
)
DEFAULT_ACTUALS_PATH = os.environ.get(
    "ACTUALS_PATH",
    "/Users/stevenmandel/Downloads/January Financials.xlsx"
)
DEFAULT_OUTPUT_PATH = os.environ.get(
    "OUTPUT_PATH",
    "/Users/stevenmandel/Downloads/Budget_vs_Actual_Output.xlsx"
)

# ... (later in file, lines 220-221)
DEFAULT_RAW_DATA_PATH = os.environ.get(
    "RAW_DATA_PATH",
    "/Users/stevenmandel/Downloads/Raw Data Tab .xlsx"
)
DEFAULT_MAPPING_PATH = os.environ.get(
    "MAPPING_PATH",
    "/Users/stevenmandel/Downloads/Mapping tab.xlsx"
)
```

This keeps local development working (falls back to existing paths) while allowing Streamlit Cloud to override via secrets/env vars.

**Step 2: Add `IS_CLOUD` detection**

Add to top of `config.py` (after `import os`):

```python
# Detect Streamlit Cloud deployment
IS_CLOUD = os.environ.get("STREAMLIT_CLOUD", "false").lower() == "true"
```

**Step 3: Run import verification**

Run:
```bash
cd "/Users/stevenmandel/Claude Code/budget-vs-actual"
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
python3 -c "import config; print('Config OK'); print('IS_CLOUD:', config.IS_CLOUD)"
```
Expected: `Config OK` and `IS_CLOUD: False`

**Step 4: Commit**

```bash
git add config.py
git commit -m "refactor: make file paths configurable via env vars for cloud deployment"
```

---

### Task 3: Add Password Gate

**Files:**
- Modify: `dashboard/app.py` (after `init_state()`, before sidebar)

**Step 1: Add password check function**

Insert after `init_state()` call (line 59) and before the SLDS CSS injection (line 63):

```python
# ── Password gate (Streamlit Cloud) ──────────────────────────────────
def check_password():
    """Returns True if the user has entered the correct password."""
    if not hasattr(st, "secrets") or "password" not in st.secrets:
        return True  # No password configured (local dev)

    if st.session_state.get("authenticated"):
        return True

    st.markdown(
        f"""
        <div style="text-align:center; padding: 3rem 1rem;">
            <div style="font-size:2rem; font-weight:700; color:{SLDS['brand_dark']};">
                🌳 Treetop Therapy
            </div>
            <div style="font-size:1rem; color:{SLDS['text_secondary']}; margin-top:0.5rem;">
                Budget vs Actual Dashboard
            </div>
        </div>
        """,
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
```

**Step 2: Test locally (should pass through since no secrets configured)**

Run:
```bash
cd "/Users/stevenmandel/Claude Code/budget-vs-actual"
python3 -c "import dashboard.app; print('Import OK')"
```
Expected: `Import OK`

**Step 3: Commit**

```bash
git add dashboard/app.py
git commit -m "feat: add password gate for Streamlit Cloud deployment"
```

---

### Task 4: Conditional Upload Widget (Cloud vs Local)

**Files:**
- Modify: `dashboard/app.py` — `render_sidebar()` function

**Step 1: Import IS_CLOUD and conditionally show upload**

Add to imports at top of `app.py`:
```python
from config import DEFAULT_BUDGET_PATH, DEFAULT_MAPPING_PATH, PNL_STRUCTURE, IS_CLOUD
```

In `render_sidebar()`, wrap the Data Upload section (lines 187-217) with:
```python
        # ─── Data Upload (local mode only) ──────────────────────
        if not IS_CLOUD:
            st.markdown('<div class="sidebar-section">Data Upload</div>', unsafe_allow_html=True)
            uploaded = st.file_uploader(
                "Upload Raw Data Tab",
                # ... (keep existing upload code unchanged)
            )
            # ... (keep existing upload handler unchanged)
```

When `IS_CLOUD` is True, skip the upload widget entirely. Data is pre-loaded from committed JSON files.

**Step 2: Run import verification**

Run: `python3 -c "import dashboard.app; print('Import OK')"`
Expected: `Import OK`

**Step 3: Commit**

```bash
git add dashboard/app.py config.py
git commit -m "feat: hide upload widget in cloud mode (view-only for shared users)"
```

---

### Task 5: Excel Download Button

**Files:**
- Modify: `output/excel_writer.py` — `build_output_workbook()` (line 1633)
- Modify: `dashboard/app.py` — `render_sidebar()` function

**Step 1: Add BytesIO support to `build_output_workbook()`**

Change the function signature to accept an optional `output_stream` parameter:

```python
def build_output_workbook(
    wholeco_variance,
    segment_variance,
    state_variances,
    waterfall,
    insights,
    budget_data,
    actuals_by_month,
    months_loaded,
    month,
    states,
    output_path=None,
    prior_month_actuals=None,
    working_days=None,
    clinics_detail=None,
    mgmt_actuals=None,
    mgmt_budget=None,
    margin_analysis=None,
    data_quality_issues=None,
    unmapped_transactions=None,
):
```

And at the end of the function (replacing lines 1698-1699):

```python
    if output_path:
        wb.save(output_path)
        return output_path
    else:
        # Return workbook as bytes for st.download_button
        from io import BytesIO
        stream = BytesIO()
        wb.save(stream)
        stream.seek(0)
        return stream
```

**Step 2: Verify existing CLI still works**

Run:
```bash
python3 -c "
from output.excel_writer import build_output_workbook
print('Excel writer import OK')
"
```
Expected: `Excel writer import OK`

**Step 3: Add download button to sidebar**

In `render_sidebar()`, after the Navigation section (before `return selected_month, page`), add:

```python
        # ─── Excel Export ────────────────────────────────────────
        if selected_month and st.session_state.budget:
            st.markdown('<div class="sidebar-section">Export</div>', unsafe_allow_html=True)
            if st.button("📥 Download Excel Report", use_container_width=True):
                with st.spinner("Building Excel report..."):
                    excel_bytes = _build_excel_for_month(selected_month)
                    if excel_bytes:
                        st.session_state["excel_download"] = excel_bytes
                        st.session_state["excel_filename"] = f"Budget_vs_Actual_{selected_month}_2026.xlsx"
                        st.rerun()

            # Render download button if data is ready
            if "excel_download" in st.session_state:
                st.download_button(
                    label="💾 Save File",
                    data=st.session_state["excel_download"],
                    file_name=st.session_state.get("excel_filename", "report.xlsx"),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
```

**Step 4: Add the `_build_excel_for_month()` helper**

Add this function above `render_sidebar()`:

```python
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
```

**Step 5: Run import verification**

Run: `python3 -c "import dashboard.app; print('Import OK')"`
Expected: `Import OK`

**Step 6: Commit**

```bash
git add output/excel_writer.py dashboard/app.py
git commit -m "feat: add Excel download button to dashboard sidebar"
```

---

### Task 6: Create Q&A Engine Module

**Files:**
- Create: `dashboard/qa_engine.py`

**Step 1: Create the context builder + Claude API wrapper**

```python
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

    # Segment summary
    seg = analysis.get("segment_variance", {})
    if seg:
        lines.append("")
        lines.append("### Segment Summary (Home vs Clinic)")
        for segment in ["home", "clinic"]:
            seg_data = seg.get(segment, {})
            if seg_data:
                ebitda_row = next((r for r in seg_data if r.get("label") == "EBITDA"), None)
                rev_row = next((r for r in seg_data if r.get("label") == "Total Revenue"), None)
                if ebitda_row and rev_row:
                    ebitda_a = ebitda_row.get("actual", 0)
                    rev_a = rev_row.get("actual", 0)
                    margin = ebitda_a / rev_a * 100 if rev_a else 0
                    lines.append(f"- {segment.title()}: Revenue ${rev_a:,.0f}, EBITDA ${ebitda_a:,.0f} ({margin:.1f}% margin)")

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
                lines.append(f"- {state}: Revenue ${rev_a:,.0f}, EBITDA ${ebitda_a:,.0f} ({margin:.1f}% margin)")

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


def ask(question, context, message_history=None, model="claude-haiku-4-20250414"):
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


def generate_summary_for_gamma(month_abbr, context, model="claude-sonnet-4-20250514"):
    """
    Generate a structured 1-pager summary suitable for Gamma presentation.

    Returns a formatted text string with sections for Gamma to render.
    """
    prompt = f"""Create a concise executive summary for {month_abbr} financial performance at Treetop Therapy.

Format it as a structured 1-pager with these sections:
1. **Month at a Glance** - 3-4 bullet points of key metrics (Revenue, GM%, EBITDA, EBITDA%)
2. **Performance vs Budget** - 2-3 sentences on budget attainment (or vs prior month if no budget)
3. **Segment Highlights** - Home vs Clinic performance, 1-2 bullets each
4. **State Performance** - Top and bottom performing states
5. **Key Risks & Actions** - 2-3 items that need attention

Keep it executive-level: concise, numbers-forward, action-oriented. Use dollar amounts and percentages."""

    return ask(prompt, context, model=model)
```

**Step 2: Run import verification**

Run:
```bash
python3 -c "
from dashboard.qa_engine import is_available, build_context, SYSTEM_PROMPT
print('QA Engine import OK')
print('API available:', is_available())
print('System prompt length:', len(SYSTEM_PROMPT))
"
```
Expected: `QA Engine import OK`, `API available: False` (no key yet), system prompt length ~900+

**Step 3: Commit**

```bash
git add dashboard/qa_engine.py
git commit -m "feat: add Q&A engine with Claude API context builder"
```

---

### Task 7: Rewrite Q&A Tab

**Files:**
- Modify: `dashboard/app.py` — `page_qa()` function (lines 858-891)

**Step 1: Add import at top of app.py**

```python
from dashboard.qa_engine import is_available as qa_available, build_context, ask as qa_ask, generate_summary_for_gamma
```

**Step 2: Rewrite `page_qa()` function**

Replace the entire `page_qa()` function (lines 858-891) with:

```python
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
    month_data = get_month_data(month)
    budget = st.session_state.budget or {}
    available = st.session_state.available
    months_order = get_months_in_order(available)
    all_months_data = get_all_months_data(months_order)

    context = build_context(
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
                st.session_state["gamma_summary"] = summary
                st.rerun()
    with c2:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.qa_messages = []
            st.session_state.pop("gamma_summary", None)
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
                response = qa_ask(prompt, context, message_history=history[:-1])  # Exclude current question
                st.markdown(response)

        st.session_state.qa_messages.append({"role": "assistant", "content": response})

    # Context expander (debug/transparency)
    with st.expander("📋 Data context sent to Claude"):
        st.code(context, language="markdown")
```

**Step 3: Run import verification**

Run: `python3 -c "import dashboard.app; print('Import OK')"`
Expected: `Import OK`

**Step 4: Commit**

```bash
git add dashboard/app.py
git commit -m "feat: rewrite Q&A tab with Claude API integration and 1-pager generation"
```

---

### Task 8: Add `anthropic` to Requirements

**Files:**
- Modify: `requirements.txt`

**Step 1: Add anthropic SDK**

```
openpyxl>=3.1.0
streamlit>=1.32.0
plotly>=5.18.0
pandas>=2.0.0
anthropic>=0.40.0
```

**Step 2: Install locally**

Run: `pip install anthropic`
Expected: Successfully installed anthropic

**Step 3: Commit**

```bash
git add requirements.txt
git commit -m "deps: add anthropic SDK for Q&A feature"
```

---

### Task 9: Full Integration Verification

**Step 1: Clear cache and verify import**

Run:
```bash
cd "/Users/stevenmandel/Claude Code/budget-vs-actual"
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
python3 -c "import dashboard.app; print('Import OK')"
```
Expected: `Import OK`

**Step 2: Launch dashboard and smoke test**

Run: `cd "/Users/stevenmandel/Claude Code/budget-vs-actual" && python3 -m streamlit run dashboard/app.py`

Verify:
- Dashboard loads without password gate (no secrets configured locally)
- Upload widget still appears (IS_CLOUD is False)
- Excel Download button appears in sidebar when a month is selected
- Q&A tab shows API key warning (no key configured yet)
- All existing pages render correctly

**Step 3: Commit any fixes**

```bash
git add -A
git commit -m "fix: integration fixes from smoke testing"
```

---

### Task 10: GitHub Setup + Streamlit Cloud Deployment (Interactive with User)

This task requires walking the user through account creation. Steps:

**Step 1: Create GitHub account**
- Go to github.com → Sign Up
- Use email, create username, verify

**Step 2: Create private repository**
- Click "+" → New repository
- Name: `budget-vs-actual`
- Visibility: Private
- Don't initialize with README (we have our own code)

**Step 3: Push code to GitHub**

Run (user will need to authenticate — GitHub CLI or HTTPS token):
```bash
cd "/Users/stevenmandel/Claude Code/budget-vs-actual"
git remote add origin https://github.com/USERNAME/budget-vs-actual.git
git branch -M main
git push -u origin main
```

**Step 4: Deploy to Streamlit Cloud**
- Go to share.streamlit.io → Sign in with GitHub
- New app → Select `budget-vs-actual` repo → Branch: `main` → File: `dashboard/app.py`
- Go to Settings → Secrets → Add:
```toml
password = "your-chosen-password"
STREAMLIT_CLOUD = "true"
ANTHROPIC_API_KEY = "sk-ant-..."
```

**Step 5: Verify deployment**
- Open the Streamlit Cloud URL
- Enter password → dashboard loads
- Verify all pages work
- Share URL with other users

---

## Summary of All Commits

1. `Initial commit: Budget vs Actual dashboard`
2. `refactor: make file paths configurable via env vars for cloud deployment`
3. `feat: add password gate for Streamlit Cloud deployment`
4. `feat: hide upload widget in cloud mode`
5. `feat: add Excel download button to dashboard sidebar`
6. `feat: add Q&A engine with Claude API context builder`
7. `feat: rewrite Q&A tab with Claude API integration and 1-pager generation`
8. `deps: add anthropic SDK for Q&A feature`
9. `fix: integration fixes from smoke testing`
