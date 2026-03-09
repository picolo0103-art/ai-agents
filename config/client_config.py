"""Client configuration loader — reads per-client JSON files from clients/ directory."""
import json
import os
from typing import Dict, List, Optional

CLIENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "clients")


def list_clients() -> List[Dict]:
    """Return all available client configs as lightweight summaries."""
    clients = []
    if not os.path.isdir(CLIENTS_DIR):
        return clients
    for filename in sorted(os.listdir(CLIENTS_DIR)):
        if filename.endswith(".json"):
            path = os.path.join(CLIENTS_DIR, filename)
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                clients.append({
                    "id": data.get("id", filename.replace(".json", "")),
                    "company": data.get("company", ""),
                    "sector": data.get("sector", ""),
                })
            except Exception:
                pass
    return clients


def load_client(client_id: str) -> Optional[Dict]:
    """Load a client config by its id. Returns None if not found."""
    if not os.path.isdir(CLIENTS_DIR):
        return None
    for filename in os.listdir(CLIENTS_DIR):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(CLIENTS_DIR, filename)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("id") == client_id or filename == f"{client_id}.json":
                return data
        except Exception:
            pass
    return None


def build_context(config: Dict) -> str:
    """Format a client config dict into a system prompt context block."""
    lines = [
        "━━━ CONTEXTE CLIENT ━━━",
        f"Entreprise : {config.get('company', 'N/A')}",
        f"Secteur : {config.get('sector', 'N/A')}",
        f"Ton à adopter : {config.get('tone', 'professionnel')}",
    ]

    products = config.get("products")
    if products:
        lines.append(f"Produits/Services : {', '.join(products)}")

    price_range = config.get("price_range")
    if price_range:
        lines.append(f"Gamme de prix : {price_range}")

    policies = config.get("policies")
    if policies:
        lines.append("Politiques :")
        for key, value in policies.items():
            lines.append(f"  - {key} : {value}")

    faq = config.get("faq")
    if faq:
        lines.append("Informations clés à connaître :")
        for item in faq:
            lines.append(f"  • {item}")

    rules = config.get("rules")
    if rules:
        lines.append("Règles impératives :")
        for rule in rules:
            lines.append(f"  ⚠ {rule}")

    promo_codes = config.get("promo_codes")
    if promo_codes:
        lines.append(f"Codes promo actifs : {', '.join(promo_codes)}")

    contact = config.get("contact")
    if contact:
        lines.append("Contacts :")
        for key, value in contact.items():
            lines.append(f"  - {key} : {value}")

    lines.append("━━━ FIN CONTEXTE CLIENT ━━━")
    return "\n".join(lines)
