# 🚀 CRBot Production Setup - Next Steps

## État actuel ✅

- [x] **Phase 1**: Supabase + Timescale configurés
- [x] **Phase 2**: Backend auth avec user_id filtering
- [x] **Phase 3**: Frontend auth (login/register/logout)
- [x] **Phase 4**: Migration vers Supabase PostgreSQL
- [x] **Phase 5**: Docker setup pour Railway

## ⚠️ Actions Manuelles Requises

### 1️⃣ Créer les Tables dans Supabase (IMPORTANT)

**Étapes :**

1. Ouvrez https://app.supabase.com/project/opnouxerbecxofzekwpm/sql/new
2. Copiez le contenu du fichier: `database/supabase_schema.sql`
3. Collez-le dans l'éditeur SQL Supabase
4. Cliquez "Run" (ou Ctrl+Enter)
5. ✅ Attendez que toutes les tables se créent (~2-3 secondes)

**Si vous avez une erreur :**
```
relation "auth.users" does not exist
```

C'est normal - les FOREIGN KEY vers auth.users seront créées automatiquement. Vous pouvez ignorer cette erreur.

---

### 2️⃣ Tester la Connexion à Supabase

Une fois les tables créées, testez localement :

```powershell
cd c:\CRBot\backend
c:\CRBot\.venv\Scripts\python.exe test_db_connection.py
```

**Résultat attendu :**
```
✅ Connection successful!
✅ Database version: PostgreSQL 15...
✅ Found 7 tables:
   - bots
   - broker_connections
   - portfolios
   - risk_events
   - sentiment_data
   - strategy_performance
   - trades
✅ All checks passed!
```

---

### 3️⃣ Initialiser les Données de Test

```powershell
cd c:\CRBot\backend
c:\CRBot\.venv\Scripts\python.exe seed_data.py
```

**Résultat attendu :**
```
✅ Portfolio created
✅ 3 bots created
✅ 2 trades created

✅ Seed complete!
   Test user: test-user-123
   Portfolio: $100,000
   Bots: 3
   Trades: 2
```

---

### 4️⃣ Tester le Backend Localement

```powershell
cd c:\CRBot\backend
c:\CRBot\.venv\Scripts\python.exe -m uvicorn app.main:app --host localhost --port 8002 --reload
```

**Vérifications :**

Test 1 - Health check:
```bash
curl http://localhost:8002/api/health
```

Test 2 - Liste des bots (sans auth):
```bash
curl http://localhost:8002/api/bots/list
```

Test 3 - Portfolio (nécessite JWT token)
```bash
# D'abord, créez un compte Supabase dans http://localhost:3001
# Puis copiez le JWT token depuis le localStorage du navigateur
curl http://localhost:8002/api/portfolio/summary \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### 5️⃣ Déployer sur Railway

**Créer le projet Railway :**

1. Allez à https://railway.app
2. Cliquez "Create New Project"
3. Sélectionnez "Deploy from GitHub"
4. Autorisez GitHub et sélectionnez `NadDev/CRBot`
5. Railway détectera le `Dockerfile` automatiquement

**Configurer les Variables d'Environnement :**

Dans le dashboard Railway, allez à "Variables" et ajoutez :

```
ENV=production
SUPABASE_URL=https://opnouxerbecxofzekwpm.supabase.co
SUPABASE_ANON_KEY=sb_publishable_QKhstCwE2ToLugAu2gVt6w_vVO7a9nR
SUPABASE_SERVICE_KEY=sb_secret_LQUc2jVhsp359jvcf1UZBg_T4irZzlp
DATABASE_URL=postgresql://postgres:dMTGo9xJZw5yFjMG@db.opnouxerbecxofzekwpm.supabase.co:5432/postgres
TIMESCALE_HOST=idfffrs9u1.d4bmrstuve.tsdb.cloud.timescale.com
TIMESCALE_PORT=35095
TIMESCALE_DATABASE=tsdb
TIMESCALE_USER=tsdbadmin
TIMESCALE_PASSWORD=h04aqav18vv5vguc
TIMESCALE_URL=postgresql://tsdbadmin:h04aqav18vv5vguc@idfffrs9u1.d4bmrstuve.tsdb.cloud.timescale.com:35095/tsdb?sslmode=require
SECRET_KEY=change-me-in-production
API_KEY_ENCRYPTION_KEY=change-me-in-production
```

**Déployer :**

- Push le code sur GitHub
- Railway déploiera automatiquement
- Attendez 3-5 minutes pour le build
- Copiez l'URL publique (ex: `https://crbot-backend-xxxxx.railway.app`)

---

### 6️⃣ Déployer le Frontend sur Vercel

**Étapes :**

1. Allez à https://vercel.com
2. Cliquez "Add New" → "Project"
3. Importez le repo GitHub `NadDev/CRBot`
4. Sélectionnez le répertoire racine: `frontend`
5. Ajoutez les variables d'environnement:

```
VITE_SUPABASE_URL=https://opnouxerbecxofzekwpm.supabase.co
VITE_SUPABASE_ANON_KEY=sb_publishable_QKhstCwE2ToLugAu2gVt6w_vVO7a9nR
VITE_API_URL=https://crbot-backend-xxxxx.railway.app
```

6. Cliquez "Deploy"
7. Attendez 2-3 minutes

---

## 🎯 Architecture Finale

```
┌─────────────────────────────────────────────────────────┐
│ FRONTEND (Vercel)                                       │
│ React App - https://crbot-prod.vercel.app             │
└─────────────────────┬─────────────────────────────────┘
                      │ HTTPS API Calls
                      ▼
┌─────────────────────────────────────────────────────────┐
│ BACKEND (Railway)                                       │
│ FastAPI - https://crbot-backend-xxxxx.railway.app     │
└─────────────────────┬─────────────────────────────────┘
                      │ SQL Queries
                      ▼
┌─────────────────────────────────────────────────────────┐
│ SUPABASE PostgreSQL                                     │
│ opnouxerbecxofzekwpm.supabase.co                       │
│ Tables: users, bots, trades, portfolios, etc.          │
└─────────────────────┬─────────────────────────────────┘
                      │ Auth & Users
                      ▼
┌─────────────────────────────────────────────────────────┐
│ SUPABASE Auth                                           │
│ Email/password registration & JWT tokens                │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ TIMESCALE Cloud                                         │
│ idfffrs9u1.d4bmrstuve.tsdb.cloud (Market Data)         │
│ Hypertables: candles, price_ticks, sentiment           │
└─────────────────────────────────────────────────────────┘
```

---

## 💰 Coûts Estimés (Production)

| Service | Tier | Coût/mois | Usage |
|---------|------|-----------|-------|
| **Vercel** | Pro | $20 | Frontend hosting |
| **Railway** | Pay-as-you-go | $5-15 | Backend container |
| **Supabase** | Free | $0 | Database + Auth (500MB) |
| **Timescale** | Performance | $30 | Market data (optional) |
| **Total** | | **$55-65** | Fully production |

---

## ✅ Checklist de Déploiement

- [ ] 1. Tables créées dans Supabase SQL Editor
- [ ] 2. `test_db_connection.py` réussit
- [ ] 3. `seed_data.py` réussit
- [ ] 4. Backend local fonctionne (test_db_connection + API tests)
- [ ] 5. Projet Railway créé et déployé
- [ ] 6. Frontend Vercel déployé
- [ ] 7. Tests end-to-end (register → login → créer bot → voir données)

---

## 🆘 Troubleshooting

### "relation does not exist" error
→ Allez dans Supabase SQL Editor et exécutez `supabase_schema.sql`

### "connection refused" error  
→ Vérifiez DATABASE_URL dans .env
→ Testez: `python test_db_connection.py`

### Frontend shows 401 errors
→ Vérifiez que VITE_API_URL pointe vers Railway (pas localhost)
→ Vérifiez que le JWT token est inclus dans les requêtes

### Railway build fails
→ Testez localement: `docker build -f backend/Dockerfile -t crbot-backend .`
→ Vérifiez requirements.txt

---

## 📚 Documentation Complète

- Backend API: http://localhost:8002/docs (Swagger UI)
- Supabase Docs: https://supabase.com/docs
- Railway Docs: https://docs.railway.app
- FastAPI Docs: https://fastapi.tiangolo.com

---

**Questions ?** Demandez ! 🚀
