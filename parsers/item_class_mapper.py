"""
Maps "Item class" values from the Raw Data Tab to state, segment, and clinic.

State-named classes = home-based services.
Clinic-named classes = clinic-based services.
"Management" = corporate overhead.
"""

# All 29 observed Item class values mapped to state/segment/clinic
ITEM_CLASS_MAP = {
    # State names → home-based services
    "Arizona":        {"state": "AZ", "segment": "home"},
    "North Carolina": {"state": "NC", "segment": "home"},
    "Georgia":        {"state": "GA", "segment": "home"},
    "Utah":           {"state": "UT", "segment": "home"},
    "New Mexico":     {"state": "NM", "segment": "home"},
    "Virginia":       {"state": "Other", "segment": "home"},
    "Colorado":       {"state": "Other", "segment": "home"},
    "Nevada":         {"state": "Other", "segment": "home"},
    "Massachusetts":  {"state": "Other", "segment": "home"},
    "Oklahoma":       {"state": "Other", "segment": "home"},
    "Tennessee":      {"state": "Other", "segment": "home"},
    "Texas":          {"state": "Other", "segment": "home"},
    "Indiana":        {"state": "Other", "segment": "home"},
    "New Jersey":     {"state": "Other", "segment": "home"},

    # Clinic names → clinic-based services
    "Phoenix Clinic":       {"state": "AZ", "segment": "clinic", "clinic": "AZ-Phoenix"},
    "Mesa Clinic":          {"state": "AZ", "segment": "clinic", "clinic": "AZ-Mesa"},
    "Thunderbird Clinic":   {"state": "AZ", "segment": "clinic", "clinic": "AZ-Thunderbird"},
    "Scottsdale Clinic":    {"state": "AZ", "segment": "clinic", "clinic": "AZ-Scottsdale"},
    "Glendale Clinic":      {"state": "AZ", "segment": "clinic", "clinic": "AZ-Glendale"},
    "Tucson Clinic":        {"state": "AZ", "segment": "clinic", "clinic": "AZ-Tucson"},
    "Charlotte Clinic":     {"state": "NC", "segment": "clinic", "clinic": "NC-Charlotte"},
    "Raeford Clinic":       {"state": "NC", "segment": "clinic", "clinic": "NC-Raeford"},
    "Pinehurst Clinic":     {"state": "NC", "segment": "clinic", "clinic": "NC-Pinehurst"},
    "Winston Salem Clinic": {"state": "NC", "segment": "clinic", "clinic": "NC-WinstonSalem"},
    "Savannah Clinic":      {"state": "GA", "segment": "clinic", "clinic": "GA-Savannah"},
    "Jordan Clinic":        {"state": "UT", "segment": "clinic", "clinic": "UT-Jordan"},
    "Provo Clinic":         {"state": "UT", "segment": "clinic", "clinic": "UT-Provo"},
    "Albuquerque Clinic":   {"state": "NM", "segment": "clinic", "clinic": "NM-Albuquerque"},
    "Killeen Clinic":       {"state": "Other", "segment": "clinic", "clinic": "Killeen-Clinic"},

    # Management → corporate overhead
    "Management":           {"state": "MGMT", "segment": "mgmt"},
}

_DEFAULT = {"state": "Other", "segment": "home", "clinic": None}


def resolve_item_class(item_class):
    """
    Resolve an Item class string to state, segment, and clinic.

    Returns: {"state": "AZ", "segment": "home"|"clinic"|"mgmt", "clinic": "AZ-Mesa" or None}
    """
    if not item_class:
        return dict(_DEFAULT)

    key = str(item_class).strip()
    entry = ITEM_CLASS_MAP.get(key)
    if entry:
        return {"state": entry["state"], "segment": entry["segment"],
                "clinic": entry.get("clinic")}

    return dict(_DEFAULT)
