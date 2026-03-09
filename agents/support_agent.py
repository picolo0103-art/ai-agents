"""
Customer Support Agent
Answers client questions, creates tickets, and escalates when needed.
"""
import random
from datetime import datetime
from typing import Dict
from .base_agent import BaseAgent


SYSTEM_PROMPT = """Tu es un agent de support client expert et empathique.
Ton rôle est d'aider les clients avec leurs questions, problèmes et demandes.

Règles :
- Réponds toujours en français sauf si le client écrit dans une autre langue.
- Sois professionnel, chaleureux et efficace.
- Utilise les outils disponibles pour chercher des informations précises avant de répondre.
- Si tu ne peux pas résoudre le problème, crée un ticket et explique les prochaines étapes.
- N'invente jamais d'informations — utilise toujours les outils pour les données réelles.
"""

# ── Groq / OpenAI tool format ─────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Recherche dans la base de connaissances de l'entreprise pour trouver des réponses aux questions fréquentes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "La question ou le sujet à rechercher"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Récupère le statut d'une commande client.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "L'identifiant de la commande (ex: CMD-12345)"}
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "Crée un ticket de support pour les problèmes qui nécessitent une intervention humaine.",
            "parameters": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string", "description": "Sujet du ticket"},
                    "description": {"type": "string", "description": "Description détaillée du problème"},
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "urgent"],
                        "description": "Niveau de priorité",
                    },
                },
                "required": ["subject", "description", "priority"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_refund_eligibility",
            "description": "Vérifie si un client est éligible à un remboursement.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "ID de la commande"},
                    "reason": {"type": "string", "description": "Raison de la demande de remboursement"},
                },
                "required": ["order_id", "reason"],
            },
        },
    },
]


class SupportAgent(BaseAgent):
    def __init__(self, client_context: str = ""):
        super().__init__(
            name="Support Client",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
            client_context=client_context,
        )

    def _tool_handlers(self):
        return {
            "search_knowledge_base": self._search_knowledge_base,
            "get_order_status": self._get_order_status,
            "create_ticket": self._create_ticket,
            "check_refund_eligibility": self._check_refund_eligibility,
        }

    # ── Simulated tools (replace with real integrations) ───────────────

    def _search_knowledge_base(self, query: str) -> Dict:
        kb = {
            "livraison": "La livraison standard prend 3-5 jours ouvrés. La livraison express (24h) est disponible pour 9,99€.",
            "retour": "Vous pouvez retourner tout article dans les 30 jours suivant la réception. L'article doit être intact et dans son emballage d'origine.",
            "remboursement": "Les remboursements sont traités sous 5-10 jours ouvrés après réception du retour.",
            "garantie": "Tous nos produits bénéficient d'une garantie de 2 ans contre les défauts de fabrication.",
            "contact": "Notre équipe est disponible du lundi au vendredi de 9h à 18h. Email: support@entreprise.com",
        }
        query_lower = query.lower()
        for keyword, answer in kb.items():
            if keyword in query_lower:
                return {"found": True, "answer": answer, "keyword": keyword}
        return {
            "found": False,
            "answer": "Aucune information trouvée pour cette requête. Création d'un ticket recommandée.",
        }

    def _get_order_status(self, order_id: str) -> Dict:
        statuses = ["En préparation", "Expédié", "En transit", "Livré", "En attente de paiement"]
        status = random.choice(statuses)
        return {
            "order_id": order_id,
            "status": status,
            "estimated_delivery": "12 mars 2026" if status != "Livré" else "Livré le 8 mars 2026",
            "carrier": "Colissimo",
            "tracking_number": f"FR{random.randint(100000000, 999999999)}",
        }

    def _create_ticket(self, subject: str, description: str, priority: str) -> Dict:
        ticket_id = f"TKT-{random.randint(10000, 99999)}"
        return {
            "ticket_id": ticket_id,
            "status": "Créé",
            "priority": priority,
            "subject": subject,
            "message": f"Ticket {ticket_id} créé avec succès. Notre équipe vous contactera dans les 24h.",
            "created_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }

    def _check_refund_eligibility(self, order_id: str, reason: str) -> Dict:
        eligible = random.choice([True, True, False])
        return {
            "order_id": order_id,
            "eligible": eligible,
            "reason": reason,
            "message": (
                "Cette commande est éligible au remboursement. Un ticket de retour vous sera envoyé par email."
                if eligible
                else "Cette commande n'est pas éligible au remboursement car elle dépasse la période de 30 jours."
            ),
        }
