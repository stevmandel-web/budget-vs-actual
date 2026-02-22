"""
Parses the Raw Data Tab Excel file — transaction-level data.
Maps GL accounts to P&L line items using the Mapping Tab, aggregates by
month/segment/state/clinic, and produces the same output structure as parse_actuals().
"""
import openpyxl
from collections import defaultdict
from config import (
    RAW_DATA_SHEET, RAW_DATA_START_ROW,
    RAW_COL_DATE, RAW_COL_TXN_TYPE, RAW_COL_ACCOUNT,
    RAW_COL_ITEM_CLASS, RAW_COL_AMOUNT, RAW_COL_FULL_NAME,
    RAW_COL_DIST_TYPE, DATA_LINE_ITEMS,
)
from parsers.mapping_parser import parse_mapping
from parsers.item_class_mapper import resolve_item_class
from parsers.line_item_mapper import canonical_name


# Month number → abbreviation
_MONTH_NUM_TO_ABBR = {
    1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}


def _parse_month(date_str):
    """Extract month abbreviation from a date string like '01/15/2026'."""
    if not date_str or not isinstance(date_str, str):
        return None
    parts = date_str.strip().split("/")
    if len(parts) < 2:
        return None
    try:
        month_num = int(parts[0])
        return _MONTH_NUM_TO_ABBR.get(month_num)
    except ValueError:
        return None


def _safe_float(val):
    """Convert a cell value to float, treating None/empty as 0."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _lookup_pnl_item(account, mapping):
    """
    Look up a GL account name in the mapping.
    Returns the canonical P&L line item name, or None if unmapped.

    Matching priority:
    1. Exact match in hierarchical mappings
    2. If hierarchical maps to None (non-P&L), try simple mapping as fallback
    3. Leaf-node match in simple mappings
    4. canonical_name() fallback (catches items already in DATA_LINE_ITEMS)
    """
    if not account:
        return None

    hier = mapping["hierarchical"]
    simple = mapping["simple"]
    non_pnl = mapping["non_pnl"]

    # 1. Exact hierarchical match
    if account in hier:
        return hier[account]

    # 2. Non-P&L but check simple fallback
    if account in non_pnl:
        # Try simple map with the raw account name
        if account in simple:
            return simple[account]
        # Try leaf node
        leaf = account.split(":")[-1].strip()
        if leaf in simple:
            return simple[leaf]
        return None  # Genuinely non-P&L

    # 3. Leaf-node match in simple mappings
    leaf = account.split(":")[-1].strip()
    if leaf in simple:
        return simple[leaf]

    # 4. canonical_name() fallback
    canon = canonical_name(leaf)
    if canon and canon in DATA_LINE_ITEMS:
        return canon

    # Also try canonical_name on the full account string
    canon_full = canonical_name(account)
    if canon_full and canon_full in DATA_LINE_ITEMS:
        return canon_full

    return None


def _compute_subtotals(data):
    """
    Add computed subtotal/total line items to a flat {line_item: value} dict.
    Must be called AFTER all individual items are aggregated.
    """
    data["Total Revenue"] = (
        data.get("BT Revenue", 0) +
        data.get("BCBA Supervision Revenue", 0) +
        data.get("BCBA Assessment Revenue", 0) +
        data.get("Other Revenue", 0)
    )
    data["Total COGS"] = (
        data.get("BT Wages", 0) +
        data.get("BCBA Wages", 0) +
        data.get("BT Bonus", 0) +
        data.get("BCBA Performance Bonus", 0) +
        data.get("BCBA Sign-On Bonus", 0)
    )
    data["Gross Profit"] = data["Total Revenue"] - data["Total COGS"]
    data["Gross Profit Net Billing"] = data["Gross Profit"] - data.get("Billing Expense", 0)
    data["Total Sales & Marketing"] = (
        data.get("Advertising Expense", 0) +
        data.get("Marketing Expense", 0) +
        data.get("Referrals Expense", 0)
    )
    data["Total StateOps Expense"] = (
        data.get("State Director Wages", 0) +
        data.get("RCD Wages", 0) +
        data.get("Clinic Director Wages", 0) +
        data.get("Ops Manager Wages", 0) +
        data.get("StateOps Bonus", 0)
    )
    data["Total Clinic G&A"] = (
        data.get("Clinic Rent", 0) +
        data.get("Clinic Utilities", 0) +
        data.get("Other Clinic Expense", 0)
    )
    data["Other Direct G&A Expense"] = sum(
        data.get(item, 0) for item in [
            "Benefits & Insurance", "Payroll Expense", "Recruiting Expenses",
            "Background Checks", "Consulting & Contract", "IT & Technology",
            "Dues & Subscriptions", "Travel & Entertainment", "Supplies",
            "Lobbying", "Bad Debt Expense", "Other G&A",
        ]
    )
    data["Total Corporate Expense"] = (
        data.get("Corporate Overhead Wages", 0) +
        data.get("Corporate Overhead Bonus", 0) +
        data.get("Corporate Rent", 0) +
        data.get("Corporate Office Expense", 0)
    )
    data["Total Expenses"] = (
        data.get("Billing Expense", 0) +
        data["Total Sales & Marketing"] +
        data["Total StateOps Expense"] +
        data["Total Clinic G&A"] +
        data["Other Direct G&A Expense"] +
        data["Total Corporate Expense"]
    )
    data["EBITDA"] = data["Gross Profit"] - data["Total Expenses"]


def parse_raw_data(raw_data_path, mapping_path, target_month="Jan"):
    """
    Parse the Raw Data Tab, map GL accounts, aggregate, and return
    the same structure as parse_actuals().

    Args:
        raw_data_path: Path to Raw Data Tab Excel file
        mapping_path: Path to Mapping Tab Excel file
        target_month: Month to extract (e.g., "Jan"), or None for ALL months.

    Returns:
        If target_month is a string:
            (actuals_dict, unmapped_transactions) — single month, same as parse_actuals()
        If target_month is None:
            (all_months_dict, unmapped_transactions) — keyed by month abbreviation.
            Each value is a dict with: wholeco, home, clinic, states, mgmt, clinics_detail
    """
    # Load mapping
    mapping = parse_mapping(mapping_path)
    print(f"  Loaded mapping: {len(mapping['simple'])} simple, "
          f"{len(mapping['hierarchical'])} hierarchical, "
          f"{len(mapping['non_pnl'])} non-P&L")

    # Accumulators by month
    wholeco = defaultdict(lambda: defaultdict(float))
    home = defaultdict(lambda: defaultdict(float))
    clinic = defaultdict(lambda: defaultdict(float))
    mgmt = defaultdict(lambda: defaultdict(float))
    states = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    clinics_detail = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

    # GL account-level accumulators: month → gl_account → total amount
    gl_accounts = defaultdict(lambda: defaultdict(float))
    # GL account to P&L item mapping (for labeling)
    gl_to_pnl = {}

    unmapped = []
    stats = {"total": 0, "skipped": 0, "mapped": 0, "unmapped": 0, "non_pnl": 0}

    # Read raw data
    wb = openpyxl.load_workbook(raw_data_path, data_only=True, read_only=True)
    ws = wb[RAW_DATA_SHEET]

    for row in ws.iter_rows(min_row=RAW_DATA_START_ROW, values_only=False):
        stats["total"] += 1

        date_val = row[RAW_COL_DATE - 1].value
        account = row[RAW_COL_ACCOUNT - 1].value
        item_class = row[RAW_COL_ITEM_CLASS - 1].value
        amount = row[RAW_COL_AMOUNT - 1].value

        # Skip rows with no account or no meaningful amount
        if not account or not str(account).strip():
            stats["skipped"] += 1
            continue
        amount_f = _safe_float(amount)
        if amount_f == 0:
            stats["skipped"] += 1
            continue

        account = str(account).strip()

        # Parse month from date
        month_abbr = _parse_month(str(date_val) if date_val else "")
        if not month_abbr:
            stats["skipped"] += 1
            continue

        # Look up P&L line item
        pnl_item = _lookup_pnl_item(account, mapping)
        if pnl_item is None:
            stats["unmapped"] += 1
            unmapped.append({
                "date": str(date_val) if date_val else "",
                "account": account,
                "item_class": str(item_class) if item_class else "",
                "amount": amount_f,
                "transaction_type": str(row[RAW_COL_TXN_TYPE - 1].value or ""),
                "full_name": str(row[RAW_COL_FULL_NAME - 1].value or ""),
            })
            continue

        # Verify the mapped item is a recognized P&L line item
        if pnl_item not in DATA_LINE_ITEMS:
            stats["unmapped"] += 1
            unmapped.append({
                "date": str(date_val) if date_val else "",
                "account": account,
                "item_class": str(item_class) if item_class else "",
                "amount": amount_f,
                "transaction_type": str(row[RAW_COL_TXN_TYPE - 1].value or ""),
                "full_name": str(row[RAW_COL_FULL_NAME - 1].value or ""),
            })
            continue

        stats["mapped"] += 1

        # Resolve location
        location = resolve_item_class(item_class)
        state = location["state"]
        segment = location["segment"]
        clinic_name = location.get("clinic")

        # Accumulate
        wholeco[month_abbr][pnl_item] += amount_f

        if segment == "home":
            home[month_abbr][pnl_item] += amount_f
        elif segment == "clinic":
            clinic[month_abbr][pnl_item] += amount_f
            if clinic_name:
                clinics_detail[month_abbr][clinic_name][pnl_item] += amount_f
        elif segment == "mgmt":
            mgmt[month_abbr][pnl_item] += amount_f

        states[month_abbr][state][pnl_item] += amount_f

        # Track GL account-level detail
        # Use leaf account name for cleaner display
        gl_leaf = account.split(":")[-1].strip() if ":" in account else account
        gl_accounts[month_abbr][gl_leaf] += amount_f
        if gl_leaf not in gl_to_pnl:
            gl_to_pnl[gl_leaf] = pnl_item

    wb.close()

    print(f"  Processed {stats['total']} rows: "
          f"{stats['mapped']} mapped, {stats['skipped']} skipped, "
          f"{stats['unmapped']} unmapped")

    # Compute subtotals for all aggregated dicts
    for m in wholeco:
        _compute_subtotals(wholeco[m])
    for m in home:
        _compute_subtotals(home[m])
    for m in clinic:
        _compute_subtotals(clinic[m])
    for m in mgmt:
        _compute_subtotals(mgmt[m])
    for m in states:
        for st in states[m]:
            _compute_subtotals(states[m][st])
    for m in clinics_detail:
        for cl in clinics_detail[m]:
            _compute_subtotals(clinics_detail[m][cl])

    # Build GL account summaries per month: list of {account, pnl_item, amount}
    # sorted by absolute amount descending
    gl_summaries = {}
    for m, accts in gl_accounts.items():
        gl_list = []
        for acct, total in accts.items():
            gl_list.append({
                "account": acct,
                "pnl_item": gl_to_pnl.get(acct, "Unknown"),
                "amount": round(total, 2),
            })
        # Sort by absolute amount descending, keep top 50
        gl_list.sort(key=lambda x: abs(x["amount"]), reverse=True)
        gl_summaries[m] = gl_list[:50]

    # ── All-months mode: return every month in one shot ──
    if target_month is None:
        all_months_result = {}
        for m in wholeco:
            all_months_result[m] = {
                "wholeco": dict(wholeco.get(m, {})),
                "home": dict(home.get(m, {})),
                "clinic": dict(clinic.get(m, {})),
                "states": {
                    st: dict(items)
                    for st, items in states.get(m, {}).items()
                },
                "mgmt": dict(mgmt.get(m, {})),
                "clinics_detail": {
                    cl: dict(items)
                    for cl, items in clinics_detail.get(m, {}).items()
                    if items.get("Total Revenue", 0) != 0 or items.get("BT Revenue", 0) != 0
                },
                "gl_detail": gl_summaries.get(m, []),
            }
        return all_months_result, unmapped

    # ── Single-month mode: match parse_actuals() format ──
    result = {
        "target_month": target_month,
        "wholeco": dict(wholeco.get(target_month, {})),
        "home": dict(home.get(target_month, {})),
        "clinic": dict(clinic.get(target_month, {})),
        "states": {
            st: dict(items)
            for st, items in states.get(target_month, {}).items()
        },
        "mgmt": dict(mgmt.get(target_month, {})),
        "clinics_detail": {
            cl: dict(items)
            for cl, items in clinics_detail.get(target_month, {}).items()
            if items.get("Total Revenue", 0) != 0 or items.get("BT Revenue", 0) != 0
        },
        "gl_detail": gl_summaries.get(target_month, []),
        "historical": {
            m: dict(items) for m, items in wholeco.items()
        },
        "historical_states": {
            m: {st: dict(items) for st, items in state_data.items()}
            for m, state_data in states.items()
        },
    }

    return result, unmapped
