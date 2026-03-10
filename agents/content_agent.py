"""
Content & Marketing Agent
Creates content, researches markets, plans campaigns, generates ideas.
"""
import random
from datetime import datetime
from typing import Dict, List
from .base_agent import BaseAgent


SYSTEM_PROMPT = """Tu es Camille, une directrice marketing et content strategist avec 10 ans d'expérience en B2B SaaS.
Tu as fait croître des audiences de 0 à 100 000 abonnés et généré des millions d'euros de pipeline via le contenu organique.

## Ta spécialité
Créer du contenu qui convertit — pas juste du contenu qui impressionne — en combinant storytelling, SEO et psychologie de la persuasion.

## Frameworks que tu appliques systématiquement

### Copywriting
- **AIDA** : Attention → Intérêt → Désir → Action (landing pages, emails)
- **PAS** : Problème → Agitation → Solution (posts LinkedIn, publicités)
- **StoryBrand** : Le client est le héros, tu es le guide (messaging de marque)
- **4 U** : Urgent, Unique, Ultra-spécifique, Utile (titres et hooks)

### SEO & Distribution
- Keyword intent : informationnel / navigationnel / transactionnel / commercial
- Cluster de contenu : 1 pilier + 5-10 articles satellites
- Distribution 1-7-30 : republier le même contenu sous différents formats
- Meilleur moment : Mardi-Jeudi 9h-11h pour LinkedIn et email

### Formats par objectif
- **Notoriété** : Articles blog SEO, vidéos YouTube, podcasts
- **Engagement** : Posts LinkedIn storytelling, threads Twitter/X, newsletters
- **Conversion** : Landing pages, études de cas, témoignages, comparatifs

## Processus de création
1. **Brief** : Comprends le sujet, la cible, l'objectif et le canal
2. **Recherche** (research_market) : tendances, concurrents, angles inexploités
3. **Idéation** (generate_ideas) : 5-10 angles différents, choisis le plus fort
4. **Production** (write_content) : rédige avec le framework adapté
5. **Optimisation** : checklist SEO, lisibilité, CTA clair

## Règles
- Chaque livrable doit être prêt à publier, pas un brouillon
- Toujours inclure un hook puissant dans les 2 premières lignes
- Cite des données chiffrées : le contenu data-driven génère 3x plus d'engagement
- Adapte le niveau de formalisme à la plateforme et à la cible
- Réponds en français par défaut
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "write_content",
            "description": "Rédige du contenu marketing optimisé selon le type, le sujet et la cible.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content_type": {
                        "type": "string",
                        "enum": ["blog_post", "linkedin_post", "instagram_caption", "email_newsletter", "ad_copy", "landing_page_copy"],
                        "description": "Type de contenu",
                    },
                    "topic": {"type": "string", "description": "Sujet principal"},
                    "tone": {
                        "type": "string",
                        "enum": ["professional", "friendly", "urgent", "inspirational", "educational"],
                    },
                    "target_audience": {"type": "string", "description": "Audience cible"},
                    "keywords": {"type": "array", "items": {"type": "string"}, "description": "Mots-clés SEO"},
                },
                "required": ["content_type", "topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "research_market",
            "description": "Analyse les tendances du marché et la concurrence sur un sujet ou secteur.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Sujet ou secteur à analyser"},
                    "focus": {
                        "type": "string",
                        "enum": ["trends", "competitors", "audience", "keywords", "all"],
                    },
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "plan_campaign",
            "description": "Crée un plan de campagne marketing complet avec timeline, canaux et KPIs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "campaign_goal": {"type": "string", "description": "Objectif (notoriété, leads, conversion)"},
                    "product_service": {"type": "string"},
                    "duration_weeks": {"type": "integer", "description": "Durée en semaines"},
                    "budget_euros": {"type": "integer", "description": "Budget estimé"},
                    "channels": {"type": "array", "items": {"type": "string"}, "description": "Canaux marketing"},
                },
                "required": ["campaign_goal", "product_service"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_ideas",
            "description": "Génère des idées de contenu créatives et stratégiques pour un thème donné.",
            "parameters": {
                "type": "object",
                "properties": {
                    "theme": {"type": "string"},
                    "count": {"type": "integer", "description": "Nombre d'idées (3-10)"},
                    "formats": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Formats souhaités (article, vidéo, infographie, podcast...)",
                    },
                },
                "required": ["theme"],
            },
        },
    },
]


class ContentAgent(BaseAgent):
    def __init__(self, client_context: str = ""):
        super().__init__(
            name="Marketing & Contenu",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
            client_context=client_context,
        )

    def _tool_handlers(self):
        return {
            "write_content": self._write_content,
            "research_market": self._research_market,
            "plan_campaign": self._plan_campaign,
            "generate_ideas": self._generate_ideas,
        }

    # ── Simulated tools ─────────────────────────────────────────────────

    def _write_content(self, content_type: str, topic: str, tone: str = "professional",
                       target_audience: str = "professionnels", keywords: list = None) -> Dict:
        labels = {
            "blog_post": "Article de blog",
            "linkedin_post": "Post LinkedIn",
            "instagram_caption": "Caption Instagram",
            "email_newsletter": "Email newsletter",
            "ad_copy": "Texte publicitaire",
            "landing_page_copy": "Texte landing page",
        }
        lengths = {
            "blog_post": "800-1200 mots",
            "linkedin_post": "150-300 mots",
            "instagram_caption": "50-150 mots",
            "email_newsletter": "300-500 mots",
            "ad_copy": "30-80 mots",
            "landing_page_copy": "200-400 mots",
        }
        return {
            "type": labels.get(content_type, content_type),
            "topic": topic,
            "tone": tone,
            "target_audience": target_audience,
            "keywords": keywords or [],
            "estimated_length": lengths.get(content_type, "variable"),
            "seo_score": f"{random.randint(72, 96)}/100",
            "readability_score": f"{random.randint(68, 94)}/100",
            "estimated_reach": f"{random.randint(500, 15000)} vues",
            "best_posting_time": "Mardi–Jeudi 9h-11h ou 17h-19h",
            "status": "Données collectées — rédaction en cours",
        }

    def _research_market(self, topic: str, focus: str = "all") -> Dict:
        return {
            "topic": topic,
            "market_size": f"€{random.randint(2, 80)}B (2025)",
            "growth_rate": f"+{random.randint(12, 48)}%/an",
            "top_trends": [
                f"L'IA transforme le secteur {topic} à grande échelle",
                f"Les entreprises investissent 40% de plus dans {topic} vs 2023",
                f"Personnalisation et automatisation dominent les stratégies {topic}",
            ],
            "top_keywords": [f"{topic} solution", f"meilleur {topic}", f"{topic} ROI", f"automatiser {topic}"],
            "competitors": [{"name": f"Leader{i+1}.io", "strength": random.choice(["SEO", "Paid", "Social"])} for i in range(3)],
            "audience_pain_points": ["Manque d'automatisation", "ROI difficile à mesurer", "Coûts trop élevés"],
            "content_gaps": ["Tutoriels pratiques", "Études de cas chiffrées", "Comparatifs outils"],
            "analyzed_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }

    def _plan_campaign(self, campaign_goal: str, product_service: str,
                       duration_weeks: int = 4, budget_euros: int = 0, channels: list = None) -> Dict:
        channels = channels or ["LinkedIn", "Email", "SEO"]
        phases = ["Awareness", "Engagement", "Nurturing", "Conversion"]
        weekly_plan = []
        for i in range(min(duration_weeks, 4)):
            weekly_plan.append({
                "week": i + 1,
                "phase": phases[i],
                "actions": [f"Contenu {channels[j % len(channels)]}" for j in range(2)],
                "kpi_focus": ["Reach", "Clics", "Leads", "Conversions"][i],
            })
        return {
            "campaign": f"{campaign_goal} — {product_service}",
            "duration": f"{duration_weeks} semaines",
            "budget": f"€{budget_euros:,}" if budget_euros else "À définir",
            "channels": channels,
            "weekly_plan": weekly_plan,
            "kpis": ["Leads générés", "Taux de conversion", "CPL", "ROI", "Reach total"],
            "expected_results": {
                "leads": random.randint(25, 200),
                "reach": random.randint(8000, 80000),
                "conversion_rate": f"{random.uniform(2.5, 9.5):.1f}%",
                "estimated_roi": f"{random.randint(150, 400)}%",
            },
            "created_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }

    def _generate_ideas(self, theme: str, count: int = 5, formats: list = None) -> Dict:
        formats = formats or ["Article", "Post LinkedIn", "Vidéo courte", "Infographie"]
        count = min(max(count, 3), 10)
        angles = [
            "Comment", "Pourquoi", f"Les {random.randint(5,10)} erreurs",
            "Le guide complet", "Étude de cas", "Tendances 2026",
            "Checklist pratique", "Comparatif outils",
        ]
        ideas: List[Dict] = []
        for i in range(count):
            ideas.append({
                "id": i + 1,
                "title": f"{angles[i % len(angles)]} {theme.lower()} {'peut transformer votre ROI' if i % 2 == 0 else 'en 2026 : ce qui change tout'}",
                "format": formats[i % len(formats)],
                "estimated_engagement": f"{random.randint(300, 8000)} vues",
                "difficulty": random.choice(["⚡ Rapide", "🔧 Moyen", "🚀 Ambitieux"]),
                "viral_potential": f"{random.randint(3, 9)}/10",
            })
        return {
            "theme": theme,
            "ideas": ideas,
            "best_format": formats[0],
            "optimal_frequency": "3-5 contenus/semaine",
            "pro_tip": f"Les contenus sur '{theme}' avec des données chiffrées génèrent 3x plus d'engagement.",
            "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
