import os
import sqlite3
from contextlib import contextmanager
from typing import Generator

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "invoices.db")

DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS fournisseurs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nom         TEXT    NOT NULL UNIQUE,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS factures (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    fournisseur_id   INTEGER REFERENCES fournisseurs(id) ON DELETE SET NULL,
    numero_facture   TEXT,
    date_facture     DATE,
    date_echeance    DATE,
    total_ht         REAL,
    total_ttc        REAL,
    tva              REAL,
    statut           TEXT DEFAULT 'non payé',
    date_paiement    DATE,
    fichier_path     TEXT,
    raw_json         TEXT,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS produits (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    facture_id     INTEGER REFERENCES factures(id) ON DELETE CASCADE,
    nom            TEXT,
    quantite       REAL,
    prix_unitaire  REAL,
    prix_total     REAL
);

CREATE TABLE IF NOT EXISTS config (
    key            TEXT PRIMARY KEY,
    value          TEXT,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def get_db_path() -> str:
    return os.path.abspath(DB_PATH)


def init_db() -> None:
    """Create tables if they do not exist."""
    path = get_db_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(DDL)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Context manager that yields a sqlite3 connection with row_factory set."""
    path = get_db_path()
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
