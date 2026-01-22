# 🔍 DEBUG GUIDE: Comprendre pourquoi 4 bots WALUSDT

## 📊 Le Mystère

Tu as **4 bots WALUSDT différents** au lieu de 1:
```
1. AI-WALUSDT-0032 (Momentum)
2. AI-WALUSDT-0237 (MeanReversion)
3. AI-WALUSDT-1012 (TrendFollowing)
4. Probablement d'autres...
```

**Question:** Est-ce intentionnel (multi-stratégie) ou un bug (duplication)?

---

## 🔧 Comment Déboguer

### Step 1: Activer DEBUG logging

```bash
# Edit backend/app/main.py or wherever logging est configuré
# Change: logging.basicConfig(level=logging.INFO)
# To: logging.basicConfig(level=logging.DEBUG)
```

### Step 2: Redémarrer le container

```bash
docker restart crbot-backend
docker logs -f crbot-backend | grep -E "\[DEEPSEEK|\[PARSED-ANALYSIS|\[STRATEGY-SELECT|\[BOT-CREATE"
```

### Step 3: Observer pendant 15 minutes

Tu verras les logs comme:

```
🤖 [DEEPSEEK-FULL] Response (first 800 chars):
{"action": "BUY", "confidence": 68.6, "suggested_strategy": "mean_reversion", ...}

🤖 [DEEPSEEK-FIELDS] Contains suggested_strategy: True
🤖 [PARSED-ANALYSIS] Keys in JSON: ['action', 'confidence', 'suggested_strategy', ...]
🤖 [STRATEGY-SELECT] Processing WALUSDT
   Keys in recommendation: ['action', 'confidence', 'suggested_strategy', ...]
   Has 'suggested_strategy': True
   suggested_strategy value: mean_reversion

🤖 Using AI-suggested strategy: mean_reversion
```

---

## 🎯 Ce qu'il Faut Regarder

### Question 1: Est-ce que DeepSeek recommande une stratégie?

**Bon log:**
```
🤖 [DEEPSEEK-FIELDS] Contains suggested_strategy: True
```

**Mauvais log:**
```
🤖 [DEEPSEEK-FIELDS] Contains suggested_strategy: False
```

Si False → DeepSeek n'envoie pas suggested_strategy → va utiliser fallback aléatoire!

---

### Question 2: Est-ce que la recommendation la contient?

**Bon log:**
```
🤖 [STRATEGY-SELECT] Processing WALUSDT
   Has 'suggested_strategy': True
   suggested_strategy value: mean_reversion
```

**Mauvais log:**
```
🤖 [STRATEGY-SELECT] Processing WALUSDT
   Has 'suggested_strategy': False
```

Si False → Même si DeepSeek l'envoyait, elle a été perdue en route!

---

### Question 3: Est-ce que la stratégie change chaque cycle?

**Pattern A: MÊME stratégie chaque cycle (bon)**
```
T=0min:  suggested_strategy: mean_reversion
T=5min:  suggested_strategy: mean_reversion  ← SAME!
T=10min: suggested_strategy: mean_reversion  ← SAME!

📊 Résultat attendu: 1 seul bot (duplicates bloqués)
```

**Pattern B: STRATÉGIES différentes (intentionnel?)**
```
T=0min:  suggested_strategy: mean_reversion
T=5min:  suggested_strategy: momentum         ← DIFFÉRENT!
T=10min: suggested_strategy: trend_following ← DIFFÉRENT!

📊 Résultat: 3 bots (une pour chaque stratégie)
❓ Question: Pourquoi DeepSeek change-il de stratégie?
```

**Pattern C: Pas de suggested_strategy du tout (bug!)**
```
T=0min:  suggested_strategy: None/Missing → Fallback: trend_following
T=5min:  suggested_strategy: None/Missing → Fallback: momentum
T=10min: suggested_strategy: None/Missing → Fallback: rsi_divergence

📊 Résultat: 3 bots (pour MAUVAISES raisons!)
```

---

## 📋 Checklist de Debugging

- [ ] Logs montrent `[DEEPSEEK-FULL]` response complète?
- [ ] DeepSeek envoie bien `"suggested_strategy"`?
- [ ] `[PARSED-ANALYSIS]` inclut `suggested_strategy` en keys?
- [ ] `[STRATEGY-SELECT]` reçoit la recommendation avec tous les champs?
- [ ] Même stratégie chaque cycle pour WALUSDT?
- [ ] Duplicate check bloque les doublons ou les laisse passer?

---

## 📊 Résultats Possibles

### Résultat A: FEATURE INTENTIONNELLE ✅

```
"DeepSeek recommande une stratégie DIFFÉRENTE
 chaque 5 minutes basée sur les conditions du marché"

Action:
- Laisser créer plusieurs bots
- Mais améliorer coordination entre eux
- S'assurer qu'ils ne se cannibalisent pas
```

### Résultat B: BUG DE PARSING ❌

```
"DeepSeek envoie bien suggested_strategy,
 mais elle est perdue lors du parsing"

Action:
- Fixer _parse_analysis_response() pour préserver tous les champs
- Fixer _get_ai_recommendations() pour transmettre les champs
- Après fix: devrait avoir 1 seul bot au lieu de 4
```

### Résultat C: BUG DE FALLBACK ❌

```
"DeepSeek n'envoie pas suggested_strategy,
 fallback heuristique choisit aléatoirement chaque fois"

Action:
- Améliorer le prompt DeepSeek pour toujours envoyer suggested_strategy
- Ou améliorer la heuristique fallback pour être plus stable
- Résultat: moins de bots doublons
```

---

## 🚀 Commandes Utiles

### Afficher SEULEMENT les logs de debugging:
```bash
docker logs -f crbot-backend 2>&1 | grep -E "\[DEEPSEEK|\[PARSED-ANALYSIS|\[STRATEGY-SELECT"
```

### Chercher les patterns:
```bash
docker logs crbot-backend 2>&1 | grep "suggested_strategy" | sort | uniq -c
```

### Voir toutes les créations de bot:
```bash
docker logs crbot-backend 2>&1 | grep "AI bot" | grep -E "Created|BLOCKED|Using"
```

### Exporter les logs pour analyse:
```bash
docker logs crbot-backend > bot_logs.txt 2>&1
```

---

## ✅ Une Fois que tu as les Logs

**Partage-les et on pourra:**
1. ✅ Voir exactement ce que DeepSeek envoie
2. ✅ Tracker où les champs se perdent
3. ✅ Comprendre si c'est feature ou bug
4. ✅ Fixer le vrai problème (pas juste un symptôme)

**N'applique PAS de fix avant d'avoir compris** car:
- Si c'est une feature → fixer casse le système
- Si c'est un bug → faut fixer la vraie cause, pas le symptôme
