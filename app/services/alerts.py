"""
Alert logic: overdue invoices and price spikes.
"""
from datetime import date, timedelta
from typing import Any, Dict, List

from app.database import queries
from app.database.queries import get_config
from app.utils.logger import get_logger

logger = get_logger("alerts")


def get_overdue_invoices(days_threshold: int = None) -> List[Dict[str, Any]]:
    """
    Return unpaid invoices whose due date is more than `days_threshold` days ago.
    Each item is a factures row dict with fournisseur_nom included.
    """
    if days_threshold is None:
        days_threshold = int(get_config("OVERDUE_DAYS_THRESHOLD", "30"))

    threshold_date = (date.today() - timedelta(days=days_threshold)).isoformat()
    rows = queries.get_overdue_invoices_raw(threshold_date)
    logger.info("Overdue invoices (threshold=%d days): %d found", days_threshold, len(rows))
    return rows


def get_price_spikes(pct_threshold: float = None) -> List[Dict[str, Any]]:
    """
    For each product name, compare the most recent unit price vs the previous purchase.
    Returns a list of products whose price increased by more than pct_threshold %.

    Each item:
        {
          "nom": str,
          "prix_actuel": float,
          "prix_precedent": float,
          "variation_pct": float,
          "date_actuelle": str,
          "date_precedente": str,
          "fournisseur_actuel": str,
        }
    """
    if pct_threshold is None:
        pct_threshold = float(get_config("PRICE_SPIKE_THRESHOLD", "10"))

    all_prices = queries.get_all_product_prices()

    # Group by product name
    by_product: Dict[str, List[Dict]] = {}
    for row in all_prices:
        name = (row["nom"] or "").strip().lower()
        if not name:
            continue
        by_product.setdefault(name, []).append(row)

    spikes: List[Dict[str, Any]] = []

    for name, entries in by_product.items():
        # Already sorted by date DESC from the query
        if len(entries) < 2:
            continue

        latest = entries[0]
        previous = entries[1]

        p_current = latest["prix_unitaire"]
        p_prev = previous["prix_unitaire"]

        if p_prev is None or p_prev == 0 or p_current is None:
            continue

        variation = ((p_current - p_prev) / abs(p_prev)) * 100

        if variation > pct_threshold:
            spikes.append(
                {
                    "nom": latest["nom"],
                    "prix_actuel": p_current,
                    "prix_precedent": p_prev,
                    "variation_pct": round(variation, 2),
                    "date_actuelle": latest["date_facture"],
                    "date_precedente": previous["date_facture"],
                    "fournisseur_actuel": latest.get("fournisseur_nom") or "—",
                }
            )

    spikes.sort(key=lambda x: x["variation_pct"], reverse=True)
    logger.info("Price spikes (threshold=%.1f%%): %d found", pct_threshold, len(spikes))
    return spikes
