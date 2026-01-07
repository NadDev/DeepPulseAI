# 📝 Todo List & Suivi du Projet

## ✅ Sprint 0: Project Foundation
- [x] Development environment setup
- [x] Docker setup
- [x] CI/CD pipeline skeleton

## ✅ Sprint 1: ML Engine
- [x] LSTM model implementation
- [x] Deep training logic
- [x] Prediction API
- [x] Progress bar integration

## ✅ ARCH 1: Market Data & Analysis
- [x] RSI, MACD, Bollinger Bands, EMA implementation
- [x] Frontend integration (TechnicalIndicators.jsx)

## ✅ Sprint 2: Advanced Technical Analysis
- [x] Elliott Wave Backend (detect_elliott_waves)
- [x] Fibonacci Backend (calculate_fibonacci_levels)
- [x] Ichimoku Backend (calculate_ichimoku)
- [x] Frontend Integration (AdvancedAnalysis.jsx)

## ✅ Sprint 3: Portfolio Management
- [x] Backend Endpoints (Summary, Positions, Orders, Trades)
- [x] Frontend Components (PortfolioSummary, ActivePositions, TradeHistory, OrderForm)
- [x] Frontend Page Integration (Portfolio.jsx fixed)
- [x] Risk metrics calculation refinement

## ✅ Sprint 4: Bot Engine
- [x] Strategy Pattern Architecture
- [x] Configurable trading bots (TrendFollowing, Breakout, MeanReversion)
- [x] Strategy execution engine (`bot_engine.py`)
- [x] Bot management API routes (`/api/bots/*`)
- [x] Frontend BotManager component
- [ ] Paper trading mode (à implémenter)

---

## 🚀 MIGRATION SUPABASE + AUTHENTIFICATION (En cours)

### 🤖 Recommandations Modèle LLM par Phase

| Phase | Complexité | Modèle Recommandé | Raison |
|-------|------------|-------------------|--------|
| Phase 1 | 🟢 Simple | **Haiku** | Config manuelle Supabase Dashboard, peu de code |
| Phase 2 | 🟡 Moyenne | **Opus 4.5** | Refactoring backend, middleware auth, dépendances croisées |
| Phase 3 | 🟡 Moyenne | **Sonnet** | Création composants React, contexte, routing |
| Phase 4 | 🟢 Simple | **Haiku/Sonnet** | Composants simples, CRUD basique |
| Phase 5 | 🟢 Simple | **Haiku** | Tests, scripts simples |

### 📦 PHASE 1 : Setup Supabase & Timescale ✅ TERMINÉE
| Étape | Description | Status |
|-------|-------------|--------|
| 1.1 | Créer compte Supabase | ✅ Fait |
| 1.2 | Créer projet "crbot" | ✅ Fait (voir .env) |
| 1.3 | Noter credentials (URL, anon key, service key) | ✅ Fait (`.env` configuré) |
| 1.4 | Créer compte Timescale Cloud | ✅ Fait |
| 1.5 | Créer service "crbot-market-data" (Performance $30) | ✅ Fait |
| 1.6 | Configurer connexion Timescale | ✅ Fait (`timescale_client.py`) |
| 1.7 | Initialiser hypertables (market_data, trade_history) | ✅ Fait |

**Architecture Hybride:**
- **Supabase FREE** → Auth + Users uniquement (0$/mois)
- **Timescale Cloud** → Market data time-series ($30/mois)

### 📦 PHASE 2 : Migration Backend FastAPI ✅ TERMINÉE
| Étape | Description | Status |
|-------|-------------|--------|
| 2.1 | Installer dépendances (supabase, asyncpg) | ✅ Fait |
| 2.2 | Créer `supabase_client.py` | ✅ Fait |
| 2.3 | Créer `supabase_auth.py` | ✅ Fait |
| 2.4 | Routes Auth (`/api/auth/*`) | ✅ Fait |
| 2.5 | Middleware Auth (get_current_user) | ✅ Fait |
| 2.6 | Adapter `/api/bots/*` → filtrer par user_id | ✅ Fait |
| 2.7 | Adapter `/api/trades/*` → filtrer par user_id | ✅ Fait |
| 2.8 | Adapter `/api/portfolio/*` → filtrer par user_id | ✅ Fait |
| 2.9 | Ajouter `user_id` aux modèles Bot et Trade | ✅ Fait |

### 📦 PHASE 3 : Authentification Frontend ✅ TERMINÉE (Sonnet)
| Étape | Description | Status |
|-------|-------------|--------|
| 3.1 | Installer SDK Supabase JS | ✅ Fait |
| 3.2 | Créer client Supabase frontend | ✅ Fait (`supabaseClient.js`) |
| 3.3 | Créer AuthContext React | ✅ Fait (`AuthContext.jsx`) |
| 3.4 | Page `/login` | ✅ Fait |
| 3.5 | Page `/register` | ✅ Fait |
| 3.6 | Page `/forgot-password` | ✅ Fait |
| 3.7 | Configuration 2FA (TOTP) | ⏳ Optionnel (à faire plus tard) |
| 3.8 | ProtectedRoute component | ✅ Fait |
| 3.9 | Header utilisateur (nom, dropdown menu) | ✅ Fait |

### 📦 PHASE 4 : Configuration Broker ⏳ À FAIRE (Haiku/Sonnet recommandé)
| Étape | Description | Status |
|-------|-------------|--------|
| 4.1 | Page `/settings` | ⏳ À faire |
| 4.2 | Composant BrokerConnections | ⏳ À faire |
| 4.3 | Table `broker_connections` Supabase | ⏳ À faire |
| 4.4 | Routes API broker (`/api/users/broker-connections/*`) | ⏳ À faire |
| 4.5 | Chiffrement clés API (AES-256) | ⏳ À faire |
| 4.6 | Test connexion Binance | ⏳ À faire |

### 📦 PHASE 5 : Tests & Finalisation ⏳ À FAIRE (Haiku recommandé)
| Étape | Description | Status |
|-------|-------------|--------|
| 5.1 | Test Register nouveau user | ⏳ À faire |
| 5.2 | Test Login/Logout | ⏳ À faire |
| 5.3 | Test 2FA activation | ⏳ À faire |
| 5.4 | Test ajout clé Binance | ⏳ À faire |
| 5.5 | Test création bot avec user_id | ⏳ À faire |
| 5.6 | Vérifier isolation données entre users | ⏳ À faire |
| 5.7 | Script migration SQLite → Supabase | ⏳ À faire |
| 5.8 | Nettoyage ancien code | ⏳ À faire |
| 5.9 | Documentation mise à jour | ⏳ À faire |

---

## 📅 Sprint 5: Risk Management
- [ ] Position sizing logic
- [ ] Stop-loss & Take-profit management
- [ ] Daily limits & Exposure limits

## 📅 Sprint 6: Reporting Dashboard
- [ ] Performance analytics
- [ ] Equity curves
- [ ] Trade reports export

## 📅 Sprint 7: Testing & Optimization
- [ ] Unit tests coverage
- [ ] Integration tests
- [ ] Performance optimization

---

## 🤖 FUTURE: Agent IA Trading Autonome

> **📄 Étude complète:** [AI_TRADING_AGENT_STUDY.md](./AI_TRADING_AGENT_STUDY.md)

### Concept
Un agent IA connecté à DeepSeek qui analyse les marchés et gère les bots de manière autonome.

### Coûts Estimés
| Type | Coût |
|------|------|
| Développement | Via agent IA (Cursor/Copilot) |
| Exploitation mensuelle | **~50€/mois** (DeepSeek + infra) |

### Agents Recommandés pour le Développement
| Agent | Usage | Coût |
|-------|-------|------|
| **Claude (Cursor)** 🏆 | Code Python/FastAPI complexe | $20/mois |
| **GitHub Copilot** | Intégration VS Code | $10/mois |
| **Devin** | Développement 100% autonome | $500/mois |

### Phases
- [ ] Phase 1: MVP Agent (analyse sans action)
- [ ] Phase 2: Contrôle des bots (start/stop automatique)
- [ ] Phase 3: Apprentissage continu
- [ ] Phase 4: Paper trading 3+ mois
- [ ] Phase 5: Production

### Status: 📋 En réflexion

---

## 📅 ARCH 5: Broker Integration
- [ ] Exchange APIs (Binance, etc.)
- [ ] Order execution layer

## 📅 ARCH 6: Production Security
- [ ] API key encryption
- [ ] Rate limiting
- [ ] Authentication (JWT) → Migré vers Supabase Auth

## 📅 ARCH 7: Production Deployment
- [ ] Docker orchestration
- [ ] Monitoring (Prometheus/Grafana)
- [ ] Backup procedures

---

## 📊 Credentials & Configuration

### Supabase (Auth)
- **Project URL**: See `backend/.env` for configuration
- **Config**: `backend/.env` et `frontend/.env`

### Timescale Cloud (Market Data)
- **Host**: See `backend/.env` for configuration
- **Port**: `35095`
- **Database**: `tsdb`
- **Tables**: `market_data` (hypertable), `trade_history` (hypertable)
- **Config**: `backend/.env`
