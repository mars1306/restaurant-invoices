"""
Supabase-based query functions. 
Replaces the SQLite version for multi-tenant SaaS support.
"""
import json
import streamlit as st
from typing import Any, Dict, List, Optional
from app.services.supabase_client import supabase

def get_current_user_id():
    if "user" in st.session_state and st.session_state.user:
        return st.session_state.user.id
    return None

# ---------------------------------------------------------------------------
# Fournisseurs
# ---------------------------------------------------------------------------

def get_or_create_fournisseur(nom: str) -> int:
    user_id = get_current_user_id()
    # Try to find existing
    res = supabase.table("fournisseurs").select("id").eq("user_id", user_id).eq("nom", nom).execute()
    if res.data:
        return res.data[0]["id"]
    
    # Create new
    res = supabase.table("fournisseurs").insert({"user_id": user_id, "nom": nom}).execute()
    return res.data[0]["id"]

def list_fournisseurs() -> List[Dict]:
    user_id = get_current_user_id()
    res = supabase.table("fournisseurs").select("*").eq("user_id", user_id).order("nom").execute()
    return res.data

# ---------------------------------------------------------------------------
# Factures
# ---------------------------------------------------------------------------

def insert_facture_with_produits(data: Dict[str, Any], fichier_path: str) -> int:
    user_id = get_current_user_id()
    fournisseur_nom = (data.get("fournisseur") or "Inconnu").strip() or "Inconnu"
    fournisseur_id = get_or_create_fournisseur(fournisseur_nom)

    facture_data = {
        "user_id": user_id,
        "fournisseur_id": fournisseur_id,
        "numero_facture": data.get("numero_facture"),
        "date_facture": data.get("date_facture"),
        "date_echeance": data.get("date_echeance"),
        "total_ht": _to_float(data.get("total_ht")),
        "total_ttc": _to_float(data.get("total_ttc")),
        "tva": _to_float(data.get("tva")),
        "statut": data.get("statut") or "non payé",
        "fichier_path": fichier_path,
        "raw_json": data
    }
    
    res_f = supabase.table("factures").insert(facture_data).execute()
    facture_id = res_f.data[0]["id"]

    for p in data.get("produits") or []:
        prod_data = {
            "user_id": user_id,
            "facture_id": facture_id,
            "nom": p.get("nom"),
            "quantite": _to_float(p.get("quantite")),
            "prix_unitaire": _to_float(p.get("prix_unitaire")),
            "prix_total": _to_float(p.get("prix_total"))
        }
        supabase.table("produits").insert(prod_data).execute()

    return facture_id

def list_factures(statut=None, fournisseur_id=None, date_from=None, date_to=None) -> List[Dict]:
    user_id = get_current_user_id()
    query = supabase.table("factures").select("*, fournisseurs(nom)").eq("user_id", user_id)
    
    if statut: query = query.eq("statut", statut)
    if fournisseur_id: query = query.eq("fournisseur_id", fournisseur_id)
    if date_from: query = query.gte("date_facture", date_from)
    if date_to: query = query.lte("date_facture", date_to)
    
    res = query.order("date_facture", desc=True).execute()
    
    # Flatten the join result
    output = []
    for r in res.data:
        r["fournisseur_nom"] = r["fournisseurs"]["nom"] if r.get("fournisseurs") else "Inconnu"
        output.append(r)
    return output

def get_facture_by_id(facture_id: int) -> Optional[Dict]:
    user_id = get_current_user_id()
    res = supabase.table("factures").select("*, fournisseurs(nom)").eq("id", facture_id).eq("user_id", user_id).execute()
    if res.data:
        r = res.data[0]
        r["fournisseur_nom"] = r["fournisseurs"]["nom"] if r.get("fournisseurs") else "Inconnu"
        return r
    return None

def mark_paid(facture_id: int, date_paiement: str) -> None:
    user_id = get_current_user_id()
    supabase.table("factures").update({"statut": "payé", "date_paiement": date_paiement}).eq("id", facture_id).eq("user_id", user_id).execute()

def mark_unpaid(facture_id: int) -> None:
    user_id = get_current_user_id()
    supabase.table("factures").update({"statut": "non payé", "date_paiement": None}).eq("id", facture_id).eq("user_id", user_id).execute()

# ---------------------------------------------------------------------------
# Dashboard & Analytics (Ported to Supabase)
# ---------------------------------------------------------------------------

def kpi_total_period(date_from: str, date_to: str) -> float:
    user_id = get_current_user_id()
    res = supabase.table("factures").select("total_ttc").eq("user_id", user_id).gte("date_facture", date_from).lte("date_facture", date_to).execute()
    return sum(r["total_ttc"] or 0 for r in res.data)

def kpi_unpaid() -> Dict[str, Any]:
    user_id = get_current_user_id()
    res = supabase.table("factures").select("total_ttc").eq("user_id", user_id).eq("statut", "non payé").execute()
    return {"count": len(res.data), "total": sum(r["total_ttc"] or 0 for r in res.data)}

def spend_by_supplier_last_n_days(days: int = 30) -> List[Dict]:
    user_id = get_current_user_id()
    from datetime import date, timedelta
    start_date = (date.today() - timedelta(days=days)).isoformat()
    
    # Simple aggregation in Python for the proto
    res = supabase.table("factures").select("total_ttc, fournisseurs(nom)").eq("user_id", user_id).gte("date_facture", start_date).execute()
    
    from collections import defaultdict
    summary = defaultdict(float)
    for r in res.data:
        name = r["fournisseurs"]["nom"] if r.get("fournisseurs") else "Inconnu"
        summary[name] += (r["total_ttc"] or 0)
    
    return [{"fournisseur": k, "total": v} for k, v in summary.items()]

def weekly_spend_last_n_weeks(weeks: int = 8) -> List[Dict]:
    user_id = get_current_user_id()
    from datetime import date, timedelta
    start_date = (date.today() - timedelta(weeks=weeks)).isoformat()
    
    res = supabase.table("factures").select("date_facture, total_ttc").eq("user_id", user_id).gte("date_facture", start_date).execute()
    
    from collections import defaultdict
    summary = defaultdict(float)
    for r in res.data:
        if r["date_facture"]:
            # Convert to YYYY-WW format
            from datetime import datetime
            dt = datetime.strptime(r["date_facture"], "%Y-%m-%d")
            week = dt.strftime("%Y-W%W")
            summary[week] += (r["total_ttc"] or 0)
            
    sorted_weeks = sorted(summary.items())
    return [{"semaine": k, "total": v} for k, v in sorted_weeks]

def top_products_by_spend(limit: int = 15) -> List[Dict]:
    user_id = get_current_user_id()
    res = supabase.table("produits").select("nom, prix_total, prix_unitaire, factures(fournisseurs(nom))").eq("user_id", user_id).execute()
    
    from collections import defaultdict
    summary = defaultdict(lambda: {"total_depense": 0, "nb_achats": 0, "prix_unitaire_somme": 0, "fournisseurs": set()})
    for r in res.data:
        name = (r["nom"] or "Inconnu").strip().lower()
        summary[name]["total_depense"] += (r["prix_total"] or 0)
        summary[name]["nb_achats"] += 1
        summary[name]["prix_unitaire_somme"] += (r["prix_unitaire"] or 0)
        if r.get("factures") and r["factures"].get("fournisseurs"):
            summary[name]["fournisseurs"].add(r["factures"]["fournisseurs"]["nom"])
    
    sorted_items = sorted(summary.items(), key=lambda x: x[1]["total_depense"], reverse=True)[:limit]
    return [{
        "nom": k, 
        "total_depense": v["total_depense"], 
        "nb_achats": v["nb_achats"],
        "prix_unitaire_moyen": v["prix_unitaire_somme"] / v["nb_achats"] if v["nb_achats"] > 0 else 0,
        "fournisseurs": ", ".join(list(v["fournisseurs"]))
    } for k, v in sorted_items]

def product_price_history(nom: str) -> List[Dict]:
    user_id = get_current_user_id()
    res = supabase.table("produits").select("prix_unitaire, quantite, factures(id, date_facture, fournisseurs(nom))").eq("user_id", user_id).ilike("nom", f"%{nom}%").execute()
    
    history = []
    for r in res.data:
        if r.get("factures"):
            history.append({
                "date_facture": r["factures"]["date_facture"],
                "prix_unitaire": r["prix_unitaire"],
                "fournisseur_nom": r["factures"]["fournisseurs"]["nom"] if r["factures"].get("fournisseurs") else "Inconnu",
                "facture_id": r["factures"]["id"],
                "quantite": r["quantite"]
            })
    return sorted(history, key=lambda x: x["date_facture"] or "")

def product_price_by_supplier(nom: str) -> List[Dict]:
    user_id = get_current_user_id()
    res = supabase.table("produits").select("prix_unitaire, factures(fournisseurs(nom))").eq("user_id", user_id).ilike("nom", f"%{nom}%").execute()
    
    from collections import defaultdict
    summary = defaultdict(list)
    for r in res.data:
        if r.get("factures") and r["factures"].get("fournisseurs"):
            f_nom = r["factures"]["fournisseurs"]["nom"]
            summary[f_nom].append(r["prix_unitaire"] or 0)
            
    results = []
    for f_nom, prices in summary.items():
        results.append({
            "fournisseur_nom": f_nom,
            "prix_unitaire_moyen": sum(prices) / len(prices),
            "prix_unitaire_min": min(prices),
            "prix_unitaire_max": max(prices),
            "nb_achats": len(prices)
        })
    return sorted(results, key=lambda x: x["prix_unitaire_moyen"])

def supplier_price_index() -> List[Dict]:
    user_id = get_current_user_id()
    # 1. Get all products and their suppliers
    res = supabase.table("produits").select("nom, prix_unitaire, factures(fournisseurs(nom))").eq("user_id", user_id).execute()
    
    from collections import defaultdict
    prod_prices = defaultdict(list)
    sup_prod_prices = defaultdict(lambda: defaultdict(list))
    
    for r in res.data:
        if not r["nom"] or not r.get("factures") or not r["factures"].get("fournisseurs"): continue
        name = r["nom"].strip().lower()
        f_nom = r["factures"]["fournisseurs"]["nom"]
        price = r["prix_unitaire"] or 0
        prod_prices[name].append(price)
        sup_prod_prices[f_nom][name].append(price)
        
    # 2. Calc market average per product
    market_avg = {name: sum(p)/len(p) for name, p in prod_prices.items()}
    
    # 3. Calc per-supplier deviation
    results = []
    for f_nom, prods in sup_prod_prices.items():
        diffs = []
        for name, prices in prods.items():
            avg_sup_price = sum(prices) / len(prices)
            avg_mkt_price = market_avg[name]
            if avg_mkt_price > 0:
                diffs.append(((avg_sup_price - avg_mkt_price) / avg_mkt_price) * 100)
        
        if diffs:
            results.append({
                "fournisseur": f_nom,
                "nb_produits": len(diffs),
                "surprix_moyen_pct": round(sum(diffs) / len(diffs), 2)
            })
            
    return sorted(results, key=lambda x: x["surprix_moyen_pct"], reverse=True)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def get_config(key: str, default: Optional[str] = None) -> Optional[str]:
    user_id = get_current_user_id()
    if not user_id: return default
    res = supabase.table("config").select("value").eq("user_id", user_id).eq("key", key).execute()
    return res.data[0]["value"] if res.data else default

def set_config(key: str, value: str) -> None:
    user_id = get_current_user_id()
    supabase.table("config").upsert({"user_id": user_id, "key": key, "value": value}).execute()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_float(value: Any) -> Optional[float]:
    if value is None: return None
    try:
        return float(str(value).replace(",", ".").replace(" ", ""))
    except:
        return None
