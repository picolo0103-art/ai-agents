"""
Sales & Prospection Agent — Enhanced
5-step workflow: Company Analysis → Market Research → BANT Qualification
                 → Email Generation → Meeting Preparation
"""
import random
from datetime import datetime, timedelta
from typing import Dict, List
from .base_agent import BaseAgent


SYSTEM_PROMPT = """Tu es Alexandre, un directeur commercial IA avec 12 ans d'expérience en prospection B2B.
Tu as généré +50M€ de pipeline pour des entreprises SaaS, conseil et industrie, et tu maîtrises les meilleures techniques de vente modernes.

## Ta mission
Transformer chaque conversation en opportunité commerciale concrète grâce à un workflow en 5 étapes éprouvé.

## Workflow structuré — toujours dans cet ordre
1. **🔍 ANALYSE ENTREPRISE** (analyze_company)
   - Offre, ICP (Ideal Customer Profile), différenciateurs, proposition de valeur unique
   - Conseil : commence toujours ici pour personnaliser tout le reste

2. **📊 ANALYSE MARCHÉ** (research_market)
   - Taille marché, segments prioritaires, signaux d'achat, concurrence
   - Identifie les entreprises avec des "buying signals" (recrutement, levée de fonds, expansion)

3. **🎯 QUALIFICATION BANT** (qualify_prospect_bant)
   - Budget : existe-t-il et est-il alloué ?
   - Autorité : parles-tu au décideur ou au champion ?
   - Besoin : douleur explicite et impact chiffré ?
   - Timeline : décision dans quel délai ?
   - Score > 75 = priorité haute, relance sous 48h

4. **✉️ GÉNÉRATION OUTREACH** (generate_outreach_email + generate_linkedin_message)
   - Email : < 150 mots, 1 seul CTA, personnalisé avec un fait réel sur le prospect
   - LinkedIn : < 300 caractères, connexion humaine avant vente
   - Teste 3 objets différents (A/B test recommandé)

5. **📅 PRÉPARATION RDV** (prepare_meeting_script)
   - Script d'ouverture, questions de découverte SPIN, pitch adapté, traitement objections
   - Toujours finir par un closing alternatif : "Mercredi ou jeudi ?"

## Principes de vente que tu appliques
- **SPIN Selling** : Situation → Problème → Implication → Need-Payoff
- **Challenger Sale** : enseigne, adapte, prends le contrôle
- **Social proof** : cite toujours des résultats clients similaires
- **Urgence réelle** : budget de fin de trimestre, contexte marché

## Règles
- Sois toujours concret avec des chiffres et des exemples actionnables
- Adapte le ton au secteur : startup (décontracté) vs grand compte (formel)
- Guide l'utilisateur étape par étape, ne saute pas d'étape
- Réponds en français par défaut, en anglais si demandé
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "analyze_company",
            "description": "Analyse l'entreprise cliente : offre, différenciateurs, ICP (Ideal Customer Profile) et proposition de valeur.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company_name": {"type": "string", "description": "Nom de l'entreprise"},
                    "website":      {"type": "string", "description": "Site web"},
                    "sector":       {"type": "string", "description": "Secteur d'activité"},
                    "services":     {"type": "array", "items": {"type": "string"}, "description": "Services/produits proposés"},
                },
                "required": ["company_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "research_market",
            "description": "Analyse le marché cible : segments prioritaires, taille, concurrents, opportunités.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sector":         {"type": "string", "description": "Secteur à analyser"},
                    "target_clients": {"type": "array", "items": {"type": "string"}, "description": "Profils de clients cibles"},
                    "geography":      {"type": "string", "description": "Zone géographique", "default": "France"},
                },
                "required": ["sector"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "qualify_prospect_bant",
            "description": "Qualifie un prospect selon le framework BANT : Budget, Autorité, Besoin, Timeline.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prospect_company":  {"type": "string", "description": "Nom de l'entreprise prospect"},
                    "contact_name":      {"type": "string", "description": "Nom du contact"},
                    "contact_role":      {"type": "string", "description": "Titre/fonction du contact"},
                    "estimated_budget":  {"type": "string", "description": "Budget estimé"},
                    "pain_point":        {"type": "string", "description": "Problème principal identifié"},
                },
                "required": ["prospect_company"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_outreach_email",
            "description": "Génère un email de prospection B2B personnalisé, court et percutant (< 150 mots).",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient_name":    {"type": "string", "description": "Prénom et nom du destinataire"},
                    "recipient_company": {"type": "string", "description": "Entreprise du destinataire"},
                    "recipient_role":    {"type": "string", "description": "Poste du destinataire"},
                    "sender_company":    {"type": "string", "description": "Entreprise de l'expéditeur"},
                    "value_proposition": {"type": "string", "description": "Proposition de valeur principale"},
                    "pain_point":        {"type": "string", "description": "Problème adressé"},
                    "cta":               {"type": "string", "description": "Appel à l'action", "default": "appel de 20 min"},
                },
                "required": ["recipient_name", "recipient_company", "value_proposition"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_linkedin_message",
            "description": "Génère un message de connexion LinkedIn personnalisé (< 300 caractères).",
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient_name":    {"type": "string"},
                    "recipient_company": {"type": "string"},
                    "common_ground":     {"type": "string", "description": "Point commun ou déclencheur"},
                    "sender_company":    {"type": "string"},
                },
                "required": ["recipient_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "prepare_meeting_script",
            "description": "Prépare un script de rendez-vous commercial : ouverture, questions de découverte, traitement objections, closing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prospect_company": {"type": "string"},
                    "contact_role":     {"type": "string"},
                    "main_pain_point":  {"type": "string"},
                    "meeting_duration": {"type": "string", "default": "30 min"},
                    "offer_presented":  {"type": "string", "description": "Offre ou solution à présenter"},
                },
                "required": ["prospect_company", "main_pain_point"],
            },
        },
    },
]


class SalesAgent(BaseAgent):
    def __init__(self, client_context: str = ""):
        super().__init__(
            name="Sales & Prospection",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
            client_context=client_context,
        )

    def _tool_handlers(self):
        return {
            "analyze_company":         self._analyze_company,
            "research_market":         self._research_market,
            "qualify_prospect_bant":   self._qualify_bant,
            "generate_outreach_email": self._gen_email,
            "generate_linkedin_message": self._gen_linkedin,
            "prepare_meeting_script":  self._prep_meeting,
        }

    # ── Simulated tools ───────────────────────────────────────────────────────

    def _analyze_company(self, company_name: str, website: str = "", sector: str = "", services: list = None) -> Dict:
        services = services or []
        icps = [
            "Directeurs commerciaux de PME (50-200 salariés)",
            "Responsables marketing de startups SaaS",
            "Gérants de PME industrielles cherchant à digitaliser",
            "DRH de moyennes entreprises (100-500 salariés)",
        ]
        differentiators = [
            "Déploiement rapide (< 2 semaines)", "ROI mesurable dès le premier mois",
            "Support dédié et onboarding inclus", "Intégration native avec les outils existants",
        ]
        return {
            "company": company_name,
            "sector": sector or "Non précisé",
            "icp": random.choice(icps),
            "value_proposition": f"Aide les {sector or 'entreprises'} à gagner du temps et générer plus de revenus",
            "key_differentiators": random.sample(differentiators, 2),
            "positioning": "Solution premium à ROI rapide pour PME ambitieuses",
            "recommended_segments": ["PME 20-200 salariés", "Scale-ups en croissance", "ETI en transformation digitale"],
            "analyzed_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }

    def _research_market(self, sector: str, target_clients: list = None, geography: str = "France") -> Dict:
        market_sizes = {"SaaS": "4.2 Md€", "E-commerce": "12.5 Md€", "Immobilier": "8.1 Md€",
                        "RH": "3.7 Md€", "Finance": "9.8 Md€"}
        companies = [
            {"name": "TechCorp Solutions", "size": "85 salariés", "signal": "Recrutement commercial en cours"},
            {"name": "RetailPlus", "size": "210 salariés", "signal": "Levée de fonds récente (2M€)"},
            {"name": "GrowthMakers", "size": "42 salariés", "signal": "Expansion sur 3 nouveaux marchés"},
            {"name": "DataVision", "size": "130 salariés", "signal": "Changement de direction commerciale"},
        ]
        return {
            "sector": sector,
            "geography": geography,
            "market_size": market_sizes.get(sector, f"{random.randint(2, 15)}.{random.randint(1,9)} Md€"),
            "growth_rate": f"+{random.randint(8, 22)}% / an",
            "key_trends": [
                "Digitalisation accélérée post-2023",
                "Budget IA en forte hausse (+45% en 2025)",
                "Pression sur la réduction des coûts opérationnels",
            ],
            "top_prospects": random.sample(companies, 3),
            "best_timing": "T2-T3 (budgets encore disponibles)",
            "recommended_channels": ["LinkedIn Sales Navigator", "Email cold outreach", "Partenariats"],
        }

    def _qualify_bant(self, prospect_company: str, contact_name: str = "Inconnu",
                      contact_role: str = "", estimated_budget: str = "", pain_point: str = "") -> Dict:
        score = random.randint(55, 95)
        return {
            "prospect": prospect_company,
            "contact": f"{contact_name} ({contact_role})" if contact_role else contact_name,
            "bant": {
                "budget":    {"status": "✅ Confirmé" if estimated_budget else "⚠️ À qualifier", "detail": estimated_budget or "Budget annuel estimé 10-50k€"},
                "authority":  {"status": "✅ Décideur" if "DG" in contact_role or "DIR" in contact_role.upper() else "⚠️ Champion", "detail": contact_role},
                "need":       {"status": "✅ Identifié", "detail": pain_point or "Besoin de croissance commerciale"},
                "timeline":   {"status": "🟡 Moyen terme", "detail": "Décision dans 1-3 mois"},
            },
            "qualification_score": f"{score}/100",
            "priority": "🔥 Haute" if score > 75 else "🟡 Moyenne",
            "next_action": "Planifier un appel découverte de 30 min cette semaine" if score > 75 else "Nurturer via newsletter + LinkedIn",
        }

    def _gen_email(self, recipient_name: str, recipient_company: str, recipient_role: str = "",
                   sender_company: str = "notre entreprise", value_proposition: str = "",
                   pain_point: str = "", cta: str = "appel de 20 min") -> Dict:
        subject_lines = [
            f"[{recipient_company}] Comment réduire vos coûts de 30% en 90 jours",
            f"Question rapide sur votre croissance, {recipient_name.split()[0]}",
            f"3 entreprises comme {recipient_company} ont déjà testé ça",
            f"Idée pour {recipient_company} — 2 min de votre temps ?",
        ]
        return {
            "subject": random.choice(subject_lines),
            "body": f"""Bonjour {recipient_name.split()[0]},

J'ai vu que {recipient_company} {pain_point or 'cherche à accélérer sa croissance commerciale'}.

Chez {sender_company}, on aide des entreprises comme la vôtre à {value_proposition or 'générer plus de prospects qualifiés'} — souvent avec des résultats visibles sous 30 jours.

Seriez-vous disponible pour un {cta} cette semaine ?

Cordialement,
[Votre nom]""",
            "word_count": 65,
            "open_rate_estimate": f"{random.randint(28, 42)}%",
            "tips": [
                "Envoyer mardi ou jeudi matin (9h-11h)",
                "Personnaliser le 'j'ai vu que' avec un fait réel",
                "Tester 2-3 objets différents (A/B test)",
            ],
        }

    def _gen_linkedin(self, recipient_name: str, recipient_company: str = "",
                      common_ground: str = "", sender_company: str = "") -> Dict:
        first = recipient_name.split()[0]
        msgs = [
            f"Bonjour {first}, j'ai vu votre post sur {common_ground or 'la croissance B2B'} — très pertinent. Je travaille sur des sujets similaires chez {sender_company or 'mon entreprise'}. Heureux de vous avoir dans mon réseau !",
            f"Bonjour {first}, vos retours sur {common_ground or 'la transformation digitale'} m'ont inspiré. On a aidé des profils comme le vôtre à {recipient_company or 'leur entreprise'} à accélérer. Ravi de se connecter !",
        ]
        msg = random.choice(msgs)
        return {
            "message": msg,
            "char_count": len(msg),
            "connection_rate_estimate": f"{random.randint(30, 55)}%",
            "follow_up_delay": "3-5 jours après l'acceptation",
        }

    def _prep_meeting(self, prospect_company: str, main_pain_point: str,
                      contact_role: str = "", meeting_duration: str = "30 min",
                      offer_presented: str = "") -> Dict:
        greeting = contact_role if contact_role else "je suis ravi(e) d'échanger avec vous"
        return {
            "duration": meeting_duration,
            "script": {
                "opening": f"Merci de prendre ce temps, {greeting}. En {meeting_duration}, je voudrais comprendre votre situation sur {main_pain_point}, puis vous montrer comment on a aidé des entreprises similaires à {prospect_company}. Ça vous convient ?",
                "discovery_questions": [
                    f"Comment gérez-vous actuellement {main_pain_point} chez {prospect_company} ?",
                    "Quelle est votre priorité #1 pour les 6 prochains mois ?",
                    "Qu'avez-vous déjà essayé ? Qu'est-ce qui n'a pas fonctionné ?",
                    "Quel serait l'impact si ce problème était résolu ?",
                    "Qui d'autre est impliqué dans cette décision ?",
                ],
                "pitch": f"Vu ce que vous m'avez partagé, {offer_presented or 'notre solution'} vous permettrait de [résultat concret]. D'autres entreprises comme {prospect_company} ont obtenu [résultat] en [délai].",
                "objection_handling": {
                    "Trop cher":       "Je comprends. Parlons ROI : si on vous aide à [résultat], quel serait le gain pour vous ?",
                    "Pas le bon moment": "Totalement. Quand serait le bon moment ? Et que doit-il se passer d'ici là ?",
                    "Déjà un prestataire": "C'est très bien. Qu'est-ce qui vous satisfait le moins chez eux ?",
                },
                "closing": "Si ce qu'on a vu correspond à vos attentes, quelle serait la prochaine étape logique pour vous ?",
            },
            "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
