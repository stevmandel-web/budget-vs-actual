# Design: Multi-User Publishing, AI Q&A, and Excel Export

**Date:** 2026-02-22
**Status:** Approved

## Problem

The Budget vs Actual dashboard is currently single-user (local Streamlit). Need to:
1. Share with 2-3 viewers via Streamlit Cloud
2. Add AI-powered Q&A for data analysis questions + Gamma 1-pager generation
3. Add Excel report download button (reuse existing excel_writer.py)

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Hosting | Streamlit Cloud (free) | Free, reliable, auto-deploys from GitHub |
| Source control | GitHub (free private repo) | Required by Streamlit Cloud; user needs walkthrough |
| Auth | Single shared password | Simple; only 2-3 users, all trusted |
| User roles | View-only viewers; admin pushes data via git | Controlled data flow, no conflicts |
| Q&A engine | Claude API (Anthropic SDK) | Natural language questions + 1-pager generation |
| 1-pager format | Gamma presentation | Professional output, user has Gamma connector |
| Excel export | Full workbook via st.download_button | Reuse existing build_output_workbook() |

## Workstream 1: Streamlit Cloud Deployment

### Changes
- Init git repo, create `.gitignore`
- Create private GitHub repo (walkthrough for user)
- Refactor `config.py`: replace hardcoded paths with `st.secrets` / env vars
- Add password gate at top of `app.py` using `st.secrets["password"]`
- Remove file upload widget in deployed mode (detect via env var or secret)
- Data committed to `data/months/` in repo; user pushes new months via git
- Add `requirements.txt` validation (anthropic SDK added)

### .gitignore
```
__pycache__/
*.pyc
.env
*.xlsx
!data/
.streamlit/secrets.toml
```

### Secrets (set in Streamlit Cloud dashboard)
```toml
password = "shared-viewer-password"
ANTHROPIC_API_KEY = "sk-ant-..."
```

## Workstream 2: AI-Powered Q&A

### New file: `dashboard/qa_engine.py`

**Context serializer:** Converts current month's analysis into a concise prompt context:
- Month name + year
- WholeCo summary: Revenue, COGS, Gross Profit, GM%, Expenses, EBITDA, EBITDA%
- Budget vs Actual deltas (if budget month)
- Segment summary: Home EBITDA + margin, Clinic EBITDA + margin
- State highlights: top/bottom performing states
- Pre-generated insights list (from insights.py)
- Available historical months for trend context

**System prompt:**
```
You are a financial analyst for Treetop Therapy LLC, an ABA therapy provider
operating across multiple states with Home and Clinic service segments.
You have access to the company's Budget vs Actual P&L data.
Answer questions concisely with specific numbers. When comparing to budget,
note favorable/unfavorable. Reference margins and percentages alongside dollars.
```

**Chat interface (rewrite Q&A tab in app.py):**
- `st.chat_message` / `st.chat_input` for conversational UI
- Session state message history
- "Generate 1-Pager" button → AI creates structured summary → Gamma API call
- Model selection: Haiku for quick questions, Sonnet for deep analysis

**Cost:** ~$0.01-0.03/question (Haiku), ~$0.05-0.15/question (Sonnet). <$5/month expected.

## Workstream 3: Excel Download Button

### Changes to `dashboard/app.py`
- Add sidebar `st.download_button` with label "Download Excel Report"
- Generate workbook in-memory via `BytesIO` + `build_output_workbook()`
- Available on all pages, generates for currently selected month
- Pass all available data (wholeco, segments, states, clinics, insights, waterfall, margin analysis)

### Changes to `output/excel_writer.py`
- Modify `build_output_workbook()` to accept optional `output_stream` parameter (BytesIO)
- If stream provided, save to stream instead of file path
- Return the stream for st.download_button consumption

## Files Touched

| File | Change |
|------|--------|
| `config.py` | Secrets-based config, remove hardcoded paths |
| `dashboard/app.py` | Password gate, Q&A rewrite, Excel button, conditional upload |
| `dashboard/pipeline.py` | Minor cloud data loading adjustments |
| `output/excel_writer.py` | Add BytesIO output support |
| **New:** `dashboard/qa_engine.py` | Context builder + Claude API integration |
| **New:** `.gitignore` | Standard Python + project-specific ignores |
| `requirements.txt` | Add `anthropic` SDK |

## Setup Walkthrough (for user)

1. Create GitHub account at github.com
2. Create new private repository "budget-vs-actual"
3. Generate Anthropic API key at console.anthropic.com
4. Deploy to Streamlit Cloud at share.streamlit.io
5. Configure secrets in Streamlit Cloud dashboard
