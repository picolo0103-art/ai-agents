"""
Internal Automation Agent
Handles internal business tasks: reports, data processing, notifications.
"""
import random
from datetime import datetime
from typing import Dict, List
from .base_agent import BaseAgent


SYSTEM_PROMPT = """Tu es Marc, un expert en automatisation et data intelligence avec 10 ans d'expérience en ops et Business Intelligence.
Tu as optimisé des processus dans des entreprises de 50 à 5 000 salariés, économisant des milliers d'heures par an.

## Ta mission
Transformer les données brutes en décisions actionnables et éliminer les tâches répétitives qui coûtent du temps et de l'argent.

## Méthodologie d'analyse

### Framework DELTA pour l'analyse de données
- **D**iagnostic : que montrent les chiffres bruts ?
- **E**cart : comparaison vs objectif, période précédente, benchmark secteur
- **L**eviers : quels facteurs expliquent l'écart ?
- **T**endance : la situation s'améliore-t-elle ou se détériore-t-elle ?
- **A**ction : recommandation concrète avec priorité et impact estimé

### Priorisation des anomalies
- 🚨 **Critique** : impact > 10% sur KPI principal, action immédiate
- ⚠️ **Attention** : tendance négative sur 2+ périodes, plan d'action sous 7j
- ℹ️ **Info** : variation normale, surveillance recommandée

### Automatisation — approche progressive
1. **Identifier** : cartographier les tâches répétitives (> 30 min/semaine)
2. **Prioriser** : impact × fréquence × facilité d'automatisation
3. **Implémenter** : exporter d'abord, synchroniser ensuite, orchestrer enfin
4. **Mesurer** : temps économisé, taux d'erreur avant/après

## Processus type
1. **Analyse** (analyze_data) : données + métriques clés + anomalies
2. **Rapport** (generate_report) : résumé exécutif + insights + recommandations
3. **Action** (process_task) : exécuter l'automatisation identifiée
4. **Notification** (send_notification) : alerter les équipes concernées

## Règles
- Toujours contextualiser les chiffres : un nombre seul ne dit rien
- Distinguer corrélation et causalité dans tes analyses
- Prioriser les recommandations par ROI décroissant
- Formuler chaque insight comme : "Constat → Cause probable → Action recommandée"
- Réponds en français, utilise des tableaux et listes pour la clarté
"""

# ── Groq / OpenAI tool format ─────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "analyze_data",
            "description": "Analyse un jeu de données et retourne des statistiques et insights clés.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dataset_name": {"type": "string", "description": "Nom du dataset (ex: ventes_Q1, rh_absences)"},
                    "metrics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Métriques à analyser (ex: ['revenue', 'conversion_rate'])",
                    },
                    "period": {"type": "string", "description": "Période d'analyse (ex: Q1 2026)"},
                },
                "required": ["dataset_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_report",
            "description": "Génère un rapport structuré à partir de données analysées.",
            "parameters": {
                "type": "object",
                "properties": {
                    "report_type": {
                        "type": "string",
                        "enum": ["weekly_summary", "monthly_kpis", "team_performance", "financial_overview", "custom"],
                    },
                    "department": {"type": "string", "description": "Département concerné (ventes, rh, finance, ops)"},
                    "period": {"type": "string"},
                },
                "required": ["report_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_notification",
            "description": "Envoie une notification ou alerte aux équipes concernées.",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "enum": ["email", "slack", "sms", "teams"]},
                    "recipients": {"type": "array", "items": {"type": "string"}},
                    "message": {"type": "string"},
                    "priority": {"type": "string", "enum": ["info", "warning", "critical"]},
                },
                "required": ["channel", "recipients", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "process_task",
            "description": "Exécute une tâche d'automatisation métier (export, synchro, archivage).",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_type": {
                        "type": "string",
                        "enum": ["export_csv", "sync_crm", "update_database", "archive_records", "generate_invoices"],
                    },
                    "task_params": {"type": "object", "description": "Paramètres spécifiques à la tâche"},
                },
                "required": ["task_type"],
            },
        },
    },
]


class AutomationAgent(BaseAgent):
    def __init__(self, client_context: str = ""):
        super().__init__(
            name="Automatisation Interne",
            system_prompt=SYSTEM_PROMPT,
            tools=TOOLS,
            client_context=client_context,
        )

    def _tool_handlers(self):
        return {
            "analyze_data": self._analyze_data,
            "generate_report": self._generate_report,
            "send_notification": self._send_notification,
            "process_task": self._process_task,
        }

    # ── Simulated tools ─────────────────────────────────────────────────

    def _analyze_data(self, dataset_name: str, metrics: list = None, period: str = "Période actuelle") -> Dict:
        metrics = metrics or ["revenue", "volume", "growth"]
        results = {}
        for metric in metrics:
            value = round(random.uniform(1000, 100000), 2)
            change = round(random.uniform(-15, 30), 1)
            results[metric] = {
                "value": value,
                "change_vs_previous": f"{'+' if change > 0 else ''}{change}%",
                "trend": "📈 Hausse" if change > 0 else "📉 Baisse",
                "alert": "⚠️ En dessous de l'objectif" if change < -10 else None,
            }
        anomalies = random.choice([
            ["Pic d'activité inhabituel le mardi (+45% vs moyenne)"],
            ["3 clients à risque de churn identifiés"],
            ["Coût d'acquisition en hausse de 22% ce mois"],
            [],
        ])
        return {
            "dataset": dataset_name,
            "period": period,
            "metrics": results,
            "anomalies": anomalies,
            "data_quality_score": f"{random.randint(85, 99)}%",
            "analyzed_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }

    def _generate_report(self, report_type: str, department: str = "Global", period: str = "Période actuelle") -> Dict:
        report_id = f"RPT-{random.randint(1000, 9999)}"
        templates = {
            "weekly_summary": "Résumé hebdomadaire",
            "monthly_kpis": "KPIs mensuels",
            "team_performance": "Performance équipe",
            "financial_overview": "Vue financière",
            "custom": "Rapport personnalisé",
        }
        return {
            "report_id": report_id,
            "title": f"{templates.get(report_type, report_type)} — {department} ({period})",
            "status": "Généré avec succès",
            "sections": ["Résumé exécutif", "KPIs clés", "Analyse des tendances", "Anomalies & alertes", "Recommandations"],
            "pages": random.randint(4, 12),
            "format": "PDF + Excel",
            "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "download_url": f"/reports/{report_id}.pdf",
        }

    def _send_notification(self, channel: str, recipients: list, message: str, priority: str = "info") -> Dict:
        priority_icons = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}
        return {
            "status": "Envoyé",
            "channel": channel,
            "recipients_count": len(recipients),
            "recipients": recipients,
            "priority": f"{priority_icons.get(priority, '')} {priority.upper()}",
            "message_preview": message[:100] + "..." if len(message) > 100 else message,
            "sent_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "delivery_id": f"MSG-{random.randint(10000, 99999)}",
        }

    def _process_task(self, task_type: str, task_params: dict = None) -> Dict:
        parameters = task_params or {}
        task_labels = {
            "export_csv": "Export CSV",
            "sync_crm": "Synchronisation CRM",
            "update_database": "Mise à jour base de données",
            "archive_records": "Archivage des enregistrements",
            "generate_invoices": "Génération des factures",
        }
        records = random.randint(100, 50000)
        duration = round(random.uniform(0.5, 8.5), 1)
        return {
            "task": task_labels.get(task_type, task_type),
            "status": "✅ Terminé",
            "records_processed": records,
            "duration_seconds": duration,
            "output": f"Fichier généré: {task_type}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            "errors": 0,
            "completed_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
