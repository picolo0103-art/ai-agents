#!/bin/bash
# ── AgentAI — Script de déploiement GitHub + Render ──────────
# Exécute ce script APRÈS avoir :
#   1. Ajouté la clé SSH à GitHub (voir instructions ci-dessous)
#   2. Créé le repo GitHub "ai-agents"
#   3. Rempli TON_USERNAME ci-dessous

GITHUB_USER="TON_USERNAME"   # ← change ici

REPO_URL="git@github.com:${GITHUB_USER}/ai-agents.git"

echo ""
echo "🚀 AgentAI — Déploiement sur GitHub"
echo "======================================"
echo "Repo : $REPO_URL"
echo ""

# Go to project dir
cd /Users/jb/Downloads/ai-agents || exit 1

# Add remote (ignore if already set)
git remote remove origin 2>/dev/null || true
git remote add origin "$REPO_URL"

# Push to GitHub
echo "📤 Push vers GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
  echo ""
  echo "✅ Code poussé sur GitHub !"
  echo ""
  echo "👉 Prochaine étape — Render :"
  echo "   1. Va sur https://render.com"
  echo "   2. Clique 'New +' → 'Blueprint'"
  echo "   3. Sélectionne le repo : ${GITHUB_USER}/ai-agents"
  echo "   4. Render détecte render.yaml automatiquement"
  echo "   5. Ajoute ta GROQ_API_KEY dans les variables d'env"
  echo "   6. Clique 'Apply' et attends ~5 min 🎉"
else
  echo ""
  echo "❌ Erreur lors du push."
  echo "   → Vérifie que la clé SSH est ajoutée à GitHub"
  echo "   → Vérifie que le repo '${GITHUB_USER}/ai-agents' existe"
fi
