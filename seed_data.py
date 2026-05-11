"""
seed_data.py — Generate 80 realistic restaurant supplier invoices and insert
them into the SQLite database at invoices.db.

Idempotent: aborts if any seeded invoice numbers already exist.
"""

import random
import sqlite3
import sys
from datetime import date, timedelta

# Make sure the app package is importable from the repo root
sys.path.insert(0, "/Users/louis/restaurant-invoices")

from app.database.models import get_db_path, init_db

# ---------------------------------------------------------------------------
# Random seed for reproducibility
# ---------------------------------------------------------------------------
random.seed(42)

TVA_RATE = 0.055  # 5.5% food VAT

# ---------------------------------------------------------------------------
# Supplier catalogue
# ---------------------------------------------------------------------------
SUPPLIERS = {
    "Metro": {
        "prefix": "MTR",
        "products": [
            {"nom": "Poulet (kg)",         "base_price": 6.80,  "qty_range": (5, 15)},
            {"nom": "Bœuf haché (kg)",     "base_price": 12.50, "qty_range": (3, 10)},
            {"nom": "Crème fraîche (L)",   "base_price": 3.20,  "qty_range": (5, 15)},
            {"nom": "Beurre (kg)",         "base_price": 8.90,  "qty_range": (2, 8)},
            {"nom": "Farine (kg)",         "base_price": 1.10,  "qty_range": (10, 30)},
            {"nom": "Huile d'olive (L)",   "base_price": 7.40,  "qty_range": (3, 10)},
        ],
        "order_size": (5, 8),   # number of line items per invoice
    },
    "Pomona": {
        "prefix": "PMN",
        "products": [
            {"nom": "Tomates (kg)",        "base_price": 2.10,  "qty_range": (10, 30)},
            {"nom": "Tomates grappe (kg)", "base_price": 2.80,  "qty_range": (8, 20)},
            {"nom": "Courgettes (kg)",     "base_price": 1.90,  "qty_range": (5, 15)},
            {"nom": "Salade verte (pièce)","base_price": 0.85,  "qty_range": (10, 30)},
            {"nom": "Oranges (kg)",        "base_price": 1.60,  "qty_range": (5, 15)},
            {"nom": "Pommes (kg)",         "base_price": 1.80,  "qty_range": (5, 15)},
            {"nom": "Citrons (kg)",        "base_price": 2.20,  "qty_range": (3, 10)},
            {"nom": "Carottes (kg)",       "base_price": 0.90,  "qty_range": (5, 20)},
        ],
        "order_size": (4, 7),
    },
    "Transgourmet": {
        "prefix": "TGM",
        "products": [
            {"nom": "Lait entier (L)",     "base_price": 1.15,  "qty_range": (10, 30)},
            {"nom": "Crème liquide (L)",   "base_price": 2.80,  "qty_range": (5, 15)},
            {"nom": "Œufs (boîte 12)",     "base_price": 3.60,  "qty_range": (2, 6)},
            {"nom": "Fromage râpé (kg)",   "base_price": 9.20,  "qty_range": (2, 6)},
            {"nom": "Sel (kg)",            "base_price": 0.55,  "qty_range": (5, 15)},
            {"nom": "Sucre (kg)",          "base_price": 1.20,  "qty_range": (5, 15)},
        ],
        "order_size": (4, 6),
    },
    "Au Marché Local": {
        "prefix": "AML",
        "products": [
            {"nom": "Tomates (kg)",            "base_price": 2.40,  "qty_range": (5, 15)},
            {"nom": "Herbes fraîches (botte)", "base_price": 1.80,  "qty_range": (5, 15)},
            {"nom": "Champignons (kg)",        "base_price": 5.50,  "qty_range": (2, 8)},
            {"nom": "Pommes de terre (kg)",    "base_price": 0.95,  "qty_range": (10, 25)},
        ],
        "order_size": (4, 6),
    },
    "La Criée": {
        "prefix": "CRE",
        "products": [
            {"nom": "Saumon (kg)",    "base_price": 18.50, "qty_range": (3, 10)},
            {"nom": "Cabillaud (kg)", "base_price": 14.80, "qty_range": (3, 10)},
            {"nom": "Crevettes (kg)", "base_price": 22.00, "qty_range": (2, 6)},
        ],
        "order_size": (2, 3),
    },
}

# ---------------------------------------------------------------------------
# Price-spike configuration
# Products that receive a >15% spike starting from a given day offset
# day_offset is measured from the start of the 90-day window (0 = oldest)
# ---------------------------------------------------------------------------
PRICE_SPIKES = [
    # (supplier_name, product_nom,          day_offset_start, multiplier)
    ("Metro",       "Beurre (kg)",           45, 1.22),
    ("Pomona",      "Tomates (kg)",          30, 1.18),
    ("La Criée",    "Saumon (kg)",           60, 1.20),
]


def apply_spike(supplier: str, product_nom: str, base_price: float,
                day_offset: int) -> float:
    """Return the potentially spiked price for a given product on a given day."""
    for s, p, start, mult in PRICE_SPIKES:
        if s == supplier and p == product_nom and day_offset >= start:
            return base_price * mult
    return base_price


def jitter(price: float, pct: float = 0.08) -> float:
    """Apply a small random variation of ±pct to a price."""
    return price * (1 + random.uniform(-pct, pct))


# ---------------------------------------------------------------------------
# Date generation — ~80 invoices over 90 days, fewer on weekends
# ---------------------------------------------------------------------------
def build_invoice_dates(n: int = 80, days: int = 90) -> list[date]:
    """
    Generate n dates spread over the last `days` days.
    Weekday probability is higher than weekend (3:1 ratio).
    """
    today = date.today()
    start = today - timedelta(days=days)

    candidate_dates: list[tuple[float, date]] = []
    for i in range(days):
        d = start + timedelta(days=i)
        weight = 1.0 if d.weekday() >= 5 else 3.0   # Sat/Sun vs Mon-Fri
        candidate_dates.append((weight, d))

    weights = [w for w, _ in candidate_dates]
    dates = [d for _, d in candidate_dates]

    chosen = random.choices(dates, weights=weights, k=n)
    return sorted(chosen)


# ---------------------------------------------------------------------------
# Assign invoices to suppliers — Metro/Pomona/Transgourmet get more volume
# ---------------------------------------------------------------------------
SUPPLIER_WEIGHTS = {
    "Metro":          30,
    "Pomona":         25,
    "Transgourmet":   20,
    "Au Marché Local": 10,
    "La Criée":       15,
}

SUPPLIER_NAMES = list(SUPPLIER_WEIGHTS.keys())
SUPPLIER_W_LIST = [SUPPLIER_WEIGHTS[s] for s in SUPPLIER_NAMES]


def assign_suppliers(n: int) -> list[str]:
    return random.choices(SUPPLIER_NAMES, weights=SUPPLIER_W_LIST, k=n)


# ---------------------------------------------------------------------------
# Main seeding logic
# ---------------------------------------------------------------------------

def seed(conn: sqlite3.Connection) -> None:
    today = date.today()
    start_of_window = today - timedelta(days=90)
    threshold_recent = today - timedelta(days=30)

    # --- Insert suppliers ---
    supplier_ids: dict[str, int] = {}
    for name in SUPPLIER_NAMES:
        row = conn.execute(
            "SELECT id FROM fournisseurs WHERE nom = ?", (name,)
        ).fetchone()
        if row:
            supplier_ids[name] = row[0]
        else:
            cur = conn.execute(
                "INSERT INTO fournisseurs (nom) VALUES (?)", (name,)
            )
            supplier_ids[name] = cur.lastrowid

    # --- Build invoice schedule ---
    invoice_dates = build_invoice_dates(80, 90)
    supplier_sequence = assign_suppliers(80)

    # Counters per supplier for sequential numbering
    seq_counters: dict[str, int] = {s: 0 for s in SUPPLIER_NAMES}

    total_factures = 0
    total_produits = 0

    for inv_date, supplier_name in zip(invoice_dates, supplier_sequence):
        config = SUPPLIERS[supplier_name]
        prefix = config["prefix"]
        seq_counters[supplier_name] += 1
        seq = seq_counters[supplier_name]
        numero = f"{prefix}-{inv_date.year}-{seq:04d}"

        # Day offset from start of window (for price spike lookup)
        day_offset = (inv_date - start_of_window).days

        # Choose products for this invoice
        min_items, max_items = config["order_size"]
        n_items = random.randint(min_items, max_items)
        products_pool = config["products"]
        chosen_products = random.sample(
            products_pool, k=min(n_items, len(products_pool))
        )

        # Build line items
        line_items = []
        for prod in chosen_products:
            base = apply_spike(supplier_name, prod["nom"], prod["base_price"], day_offset)
            unit_price = round(jitter(base), 4)
            qty_min, qty_max = prod["qty_range"]
            qty = round(random.uniform(qty_min, qty_max), 2)
            total = round(unit_price * qty, 2)
            line_items.append({
                "nom": prod["nom"],
                "quantite": qty,
                "prix_unitaire": round(unit_price, 2),
                "prix_total": total,
            })

        total_ht = round(sum(li["prix_total"] for li in line_items), 2)
        total_ttc = round(total_ht * (1 + TVA_RATE), 2)

        # Payment status
        is_recent = inv_date >= threshold_recent
        if is_recent:
            # Recent invoices: ~40% paid, ~60% unpaid
            paid = random.random() < 0.40
        else:
            # Older invoices: ~75% paid
            paid = random.random() < 0.75

        statut = "payé" if paid else "non payé"
        date_echeance = inv_date + timedelta(days=30)

        date_paiement = None
        if paid:
            pay_delay = random.randint(5, 20)
            date_paiement = inv_date + timedelta(days=pay_delay)

        cur = conn.execute(
            """
            INSERT INTO factures
                (fournisseur_id, numero_facture, date_facture, date_echeance,
                 total_ht, total_ttc, tva, statut, date_paiement,
                 fichier_path, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
            """,
            (
                supplier_ids[supplier_name],
                numero,
                inv_date.isoformat(),
                date_echeance.isoformat(),
                total_ht,
                total_ttc,
                TVA_RATE,
                statut,
                date_paiement.isoformat() if date_paiement else None,
            ),
        )
        facture_id = cur.lastrowid
        total_factures += 1

        for li in line_items:
            conn.execute(
                """
                INSERT INTO produits (facture_id, nom, quantite, prix_unitaire, prix_total)
                VALUES (?, ?, ?, ?, ?)
                """,
                (facture_id, li["nom"], li["quantite"], li["prix_unitaire"], li["prix_total"]),
            )
            total_produits += 1

    conn.commit()

    # --- Summary ---
    print("\n=== Seed complete ===")
    print(f"  Fournisseurs : {len(SUPPLIER_NAMES)}")
    print(f"  Factures     : {total_factures}")
    print(f"  Produits     : {total_produits}")
    row = conn.execute(
        "SELECT COUNT(*) FROM factures WHERE statut = 'payé'"
    ).fetchone()
    print(f"  Payées       : {row[0]}")
    row = conn.execute(
        "SELECT COUNT(*) FROM factures WHERE statut = 'non payé'"
    ).fetchone()
    print(f"  Non payées   : {row[0]}")
    print()

    # Per-supplier breakdown
    print("  Factures par fournisseur:")
    rows = conn.execute(
        """
        SELECT fo.nom, COUNT(*) AS n
        FROM factures f
        JOIN fournisseurs fo ON fo.id = f.fournisseur_id
        GROUP BY fo.nom
        ORDER BY n DESC
        """
    ).fetchall()
    for r in rows:
        print(f"    {r[0]:<22} {r[1]}")

    # Spike confirmation
    print("\n  Price spikes inserted for:")
    for s, p, offset, mult in PRICE_SPIKES:
        print(f"    {s} / {p}  (+{round((mult-1)*100)}% from day {offset})")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    # Idempotency check — look for any of our known prefixes
    prefixes = [SUPPLIERS[s]["prefix"] for s in SUPPLIER_NAMES]
    placeholders = ",".join("?" * len(prefixes))
    existing = conn.execute(
        f"SELECT COUNT(*) FROM factures WHERE SUBSTR(numero_facture,1,3) IN ({placeholders})",
        prefixes,
    ).fetchone()[0]

    if existing > 0:
        print(
            f"Seed data already present ({existing} seeded invoices found). "
            "Nothing inserted. Remove existing data first if you want to re-seed."
        )
        conn.close()
        return

    try:
        seed(conn)
    except Exception:
        conn.rollback()
        conn.close()
        raise

    conn.close()


if __name__ == "__main__":
    main()
