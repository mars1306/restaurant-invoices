import json
import re
from datetime import date, datetime
from typing import Any, Optional


def safe_json_loads(text: str) -> Optional[dict]:
    """
    Try to parse JSON from text.
    First attempt direct json.loads; if that fails, extract JSON block via regex.
    Returns None if all attempts fail.
    """
    # Direct parse
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass

    # Try to extract JSON block from surrounding text
    pattern = r"\{[\s\S]*\}"
    match = re.search(pattern, text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # Try to extract fenced code block
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass

    return None


def parse_date(value: Any) -> Optional[date]:
    """
    Convert a string (or date) to a date object.
    Supports YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY.
    Returns None if unparseable.
    """
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()

    value = str(value).strip()
    if not value or value.lower() == "null":
        return None

    formats = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%m/%d/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def safe_float(value: Any) -> Optional[float]:
    """Convert value to float, handling commas as decimal separators. Returns None on failure."""
    if value is None:
        return None
    try:
        return float(str(value).replace(",", ".").replace(" ", "").replace(" ", ""))
    except (ValueError, TypeError):
        return None


def format_currency(amount: Optional[float], currency: str = "€") -> str:
    """Format a float as a currency string."""
    if amount is None:
        return "—"
    return f"{amount:,.2f} {currency}".replace(",", " ").replace(".", ",")


def date_to_str(d: Optional[date]) -> str:
    """Return ISO string from date or empty string."""
    if d is None:
        return ""
    return d.isoformat()


def today_iso() -> str:
    """Return today's date as ISO string."""
    return date.today().isoformat()
