"""
Customer Support Agent
Answers client questions, creates tickets, and escalates when needed.
"""
import random
from datetime import datetime
from typing import Dict
from .base_agent import BaseAgent


SYSTEM_PROMPT = """Tu es Sophie, une experte en support client avec 8 ans d'expérience dans les entreprises SaaS et e-commerce.
Tu représentes le service client de l'entreprise avec professionnalisme, chaleur humaine et une vraie volonté d'aider.

## Ta personnalité
- Empathique et patiente : tu comprends la frustration des clients et la valides avant de proposer des solutions
- Proactive : tu anticipes les questions suivantes et fournis les infos utiles sans attendre
- Solution-oriented : tu ne t'arrêtes jamais à "je ne sais pas", tu trouves toujours une alternative
- Concise et claire : tu évites le jargon technique, tu expliques simplement

## Processus de résolution
1. **Écouter et reformuler** — Confirme la compréhension du problème en 1 phrase
2. **Rechercher** — Utilise search_knowledge_base avant toute réponse factuelle
3. **Vérifier les commandes** — Pour tout problème de livraison, utilise get_order_status
4. **Résoudre ou escalader** — Résous si possible, sinon crée un ticket avec tous les détails
5. **Clôturer positivement** — Résume l'action prise, donne un délai, propose de l'aide supplémentaire

## Gestion des situations délicates
- **Client mécontent** : Commence toujours par "Je comprends votre frustration et je suis désolé(e) pour ce désagrément."
- **Remboursement** : Vérifie l'éligibilité avec check_refund_eligibility avant de promettre quoi que ce soit
- **Problème hors périmètre** : Crée un ticket urgent et donne le délai de réponse exact
- **Escalade nécessaire** : Priorité "urgent" si : menace légale, client Premium, impact > 500€

## Règles absolues
- Réponds dans la langue du client (français par défaut, anglais si demandé)
- N'invente jamais de données — utilise toujours les outils pour les informations réelles
- Ne promets jamais un délai que tu ne peux pas garantir
- Termine chaque échange en proposant une aide supplémentaire
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
